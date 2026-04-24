"""
pi-matrix Platform Gateway — multi-tenant Hermes gateway.

Single shared service that:
1. Receives Feishu messages via Hermes FeishuAdapter (WebSocket)
2. Manages sessions (transcript, compression, reset)
3. Routes agent execution to stateless per-user executors via HTTP
4. Delivers replies back via FeishuAdapter (text) + lark_oapi (files)

Feishu credentials NEVER leave this service.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, Form, HTTPException, Header

# Hermes public API — FeishuAdapter for receive + send
from gateway.config import Platform, PlatformConfig
from gateway.platforms.feishu import FeishuAdapter
from gateway.platforms.base import MessageEvent

from config import settings
from session_store import SimpleSessionStore
from delivery import FeishuDelivery
import r2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="pi-matrix message", version="0.2.0")

# ------------------------------------------------------------------
# Components
# ------------------------------------------------------------------
_session_store = SimpleSessionStore(Path(settings.sessions_dir))
_delivery = FeishuDelivery(settings.feishu_app_id, settings.feishu_app_secret)
_adapter: FeishuAdapter | None = None
_adapter_task: asyncio.Task | None = None
_cleanup_task: asyncio.Task | None = None

# ------------------------------------------------------------------
# Simple metrics (in-memory counters)
# ------------------------------------------------------------------
class _Metrics:
    messages_received = 0
    messages_sent = 0
    executor_errors = 0
    executor_timeouts = 0
    sessions_compressed = 0
    latencies_sec: list[float] = []

_metrics = _Metrics()


# ------------------------------------------------------------------
# Supabase helpers
# ------------------------------------------------------------------
def _get_executor_endpoint(open_id: str) -> str | None:
    """Resolve open_id → user_id → container endpoint. Cached in-memory for 30s."""
    # Simple in-memory cache to avoid hammering Supabase
    now = datetime.now().timestamp()
    cache_key = f"ep:{open_id}"
    cached = _ep_cache.get(cache_key)
    if cached and (now - cached["ts"]) < 30:
        return cached["url"]

    try:
        from supabase import create_client

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        binding = (
            sb.table("pi_matrix_feishu_bindings")
            .select("user_id")
            .eq("open_id", open_id)
            .maybe_single()
            .execute()
        )
        if not binding or not binding.data:
            return None
        user_id = binding.data["user_id"]

        device = (
            sb.table("pi_matrix_devices")
            .select("endpoint")
            .eq("user_id", user_id)
            .eq("instance_type", "cloud")
            .maybe_single()
            .execute()
        )
        if not device or not device.data:
            return None
        url = str(device.data["endpoint"] or "").strip().rstrip("/")
        # Backward compatibility for legacy device endpoints.
        if url.endswith("/inbox"):
            url = url[:-6]
        elif url.endswith("/execute"):
            url = url[:-8]
        if not url:
            return None
        _ep_cache[cache_key] = {"url": url, "ts": now}
        return url
    except Exception:
        logger.exception("resolve endpoint failed open_id=%s", open_id)
        return None


_ep_cache: dict[str, dict[str, Any]] = {}
_drive_cache: dict[str, dict[str, Any]] = {}
_user_tokens_cache: dict[str, dict[str, Any]] = {}
_uid_cache: dict[str, dict[str, Any]] = {}


# ------------------------------------------------------------------
# Typing indicator helpers
# ------------------------------------------------------------------
async def _start_typing(chat_id: str) -> None:
    if _adapter is None:
        return
    try:
        await _adapter.start_typing(chat_id)
    except AttributeError:
        pass  # older FeishuAdapter without typing support
    except Exception:
        logger.debug("start_typing failed", exc_info=True)


async def _stop_typing(chat_id: str) -> None:
    if _adapter is None:
        return
    try:
        await _adapter.stop_typing(chat_id)
    except AttributeError:
        pass
    except Exception:
        logger.debug("stop_typing failed", exc_info=True)


def _get_drive_token(open_id: str) -> str | None:
    """Return valid Feishu Drive access token for open_id, else None."""
    tokens = _get_user_tokens(open_id)
    token = (tokens.get("feishu_access_token") or "").strip() if tokens else ""
    if token:
        return token

    now = datetime.now(timezone.utc)
    cache_key = f"drive:{open_id}"
    cached = _drive_cache.get(cache_key)
    if cached:
        expires_at = cached.get("expires_at")
        token = cached.get("access_token")
        if isinstance(expires_at, datetime) and isinstance(token, str):
            if now + timedelta(minutes=2) < expires_at:
                return token

    try:
        from supabase import create_client

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        rows = []
        try:
            row = (
                sb.table("pi_matrix_user_credentials")
                .select("credential_key,credential_value")
                .eq("provider", "feishu_drive")
                .eq("external_id", open_id)
                .in_("credential_key", ["access_token", "expires_at"])
                .execute()
            )
            rows = row.data if row and row.data else []
        except Exception:
            rows = []
        if not rows:
            # Transitional fallback before DB migration is applied.
            legacy = (
                sb.table("pi_matrix_feishu_drive_tokens")
                .select("access_token,expires_at")
                .eq("open_id", open_id)
                .maybe_single()
                .execute()
            )
            if legacy and legacy.data:
                rows = [
                    {"credential_key": "access_token", "credential_value": legacy.data.get("access_token")},
                    {"credential_key": "expires_at", "credential_value": legacy.data.get("expires_at")},
                ]
        if not rows:
            return None
        kv = {str(r.get("credential_key")): str(r.get("credential_value") or "") for r in rows}
        token = (kv.get("access_token") or "").strip()
        expires_at_raw = (kv.get("expires_at") or "").strip()
        if not token or not expires_at_raw:
            return None
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        if now + timedelta(minutes=2) >= expires_at:
            return None
        _drive_cache[cache_key] = {"access_token": token, "expires_at": expires_at}
        return token
    except Exception:
        logger.exception("resolve drive token failed open_id=%s", open_id)
        return None


def _get_user_tokens(open_id: str) -> dict[str, str]:
    """Return user-scoped tokens to forward into the user's executor container."""
    now = datetime.now().timestamp()
    cache_key = f"tok:{open_id}"
    cached = _user_tokens_cache.get(cache_key)
    if cached and (now - cached["ts"]) < 30:
        return dict(cached["tokens"])

    try:
        from supabase import create_client

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        rows = []
        try:
            row = (
                sb.table("pi_matrix_user_credentials")
                .select("credential_key,credential_value")
                .eq("provider", "feishu_drive")
                .eq("external_id", open_id)
                .in_("credential_key", ["access_token", "refresh_token", "expires_at"])
                .execute()
            )
            rows = row.data if row and row.data else []
        except Exception:
            rows = []
        if not rows:
            # Transitional fallback before DB migration is applied.
            legacy = (
                sb.table("pi_matrix_feishu_drive_tokens")
                .select("access_token,refresh_token,expires_at")
                .eq("open_id", open_id)
                .maybe_single()
                .execute()
            )
            if legacy and legacy.data:
                rows = [
                    {"credential_key": "access_token", "credential_value": legacy.data.get("access_token")},
                    {"credential_key": "refresh_token", "credential_value": legacy.data.get("refresh_token")},
                    {"credential_key": "expires_at", "credential_value": legacy.data.get("expires_at")},
                ]
        data = {str(r.get("credential_key")): str(r.get("credential_value") or "") for r in rows}
        tokens = {
            "feishu_access_token": str(data.get("access_token") or ""),
            "feishu_refresh_token": str(data.get("refresh_token") or ""),
            "feishu_expires_at": str(data.get("expires_at") or ""),
        }
        _user_tokens_cache[cache_key] = {"tokens": tokens, "ts": now}
        return tokens
    except Exception:
        logger.exception("resolve user tokens failed open_id=%s", open_id)
        return {}


def _get_user_id(open_id: str) -> str | None:
    """Resolve open_id -> user_id with short-lived cache."""
    now = datetime.now().timestamp()
    cache_key = f"uid:{open_id}"
    cached = _uid_cache.get(cache_key)
    if cached and (now - cached["ts"]) < 30:
        return str(cached["user_id"])

    try:
        from supabase import create_client

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        binding = (
            sb.table("pi_matrix_feishu_bindings")
            .select("user_id")
            .eq("open_id", open_id)
            .maybe_single()
            .execute()
        )
        if not binding or not binding.data:
            return None
        user_id = str(binding.data.get("user_id") or "").strip()
        if not user_id:
            return None
        _uid_cache[cache_key] = {"user_id": user_id, "ts": now}
        return user_id
    except Exception:
        logger.exception("resolve user_id failed open_id=%s", open_id)
        return None


async def _sync_memory_to_db(executor_url: str, user_id: str) -> None:
    """Pull USER.md and MEMORY.md from executor and upsert to Supabase DB."""
    _PROVIDER_MAP = {"USER": "memory_user_md", "MEMORY": "memory_md"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for file_key, provider in _PROVIDER_MAP.items():
                try:
                    resp = await client.get(f"{executor_url}/files/{file_key}")
                    if resp.status_code != 200:
                        continue
                    content = resp.json().get("content") or ""
                except Exception:
                    continue
                try:
                    from supabase import create_client
                    sb = create_client(settings.supabase_url, settings.supabase_service_key)
                    sb.table("pi_matrix_user_credentials").upsert(
                        {"user_id": user_id, "provider": provider, "credential_value": content},
                        on_conflict="user_id,provider",
                    ).execute()
                except Exception:
                    logger.exception("memory db sync failed user_id=%s file=%s", user_id, file_key)
    except Exception:
        logger.exception("memory sync failed user_id=%s", user_id)


def _log_execution(
    *,
    open_id: str,
    session_id: str,
    request_text: str,
    status: str,
    error_code: str = "",
    error_message: str = "",
    response_text: str = "",
    files_count: int = 0,
) -> None:
    user_id = _get_user_id(open_id)
    if not user_id:
        return
    try:
        from supabase import create_client

        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        sb.table("pi_matrix_execution_logs").insert(
            {
                "user_id": user_id,
                "open_id": open_id,
                "session_id": session_id,
                "request_text": (request_text or "")[:1000],
                "status": status,
                "error_code": error_code or None,
                "error_message": (error_message or "")[:500] or None,
                "response_preview": (response_text or "")[:1000],
                "files_count": int(max(files_count, 0)),
            }
        ).execute()
    except Exception:
        logger.exception("write execution log failed open_id=%s", open_id)


# ------------------------------------------------------------------
# Session hygiene — compress old transcript when token budget exceeded
# ------------------------------------------------------------------
async def _maybe_compress(session_id: str, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace old messages with an LLM summary if transcript is too long."""
    if not history:
        return history

    tokens = _session_store.estimate_tokens(session_id)
    if tokens < settings.session_token_limit:
        return history

    keep = settings.session_keep_recent
    if len(history) <= keep:
        return history  # too few messages to compress meaningfully

    to_compress = history[:-keep]
    recent = history[-keep:]

    prompt_lines = [
        "Summarize the following conversation history into 2-3 concise paragraphs.",
        "Preserve key facts, decisions, user preferences, and ongoing tasks.",
        "",
    ]
    for entry in to_compress:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        prompt_lines.append(f"{role}: {content}")
    prompt_lines.append("")
    prompt_lines.append("Summary:")
    prompt = "\n".join(prompt_lines)

    summary = ""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.gateway_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.gateway_key}", "Content-Type": "application/json"},
                json={
                    "model": "default",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            summary = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("compression failed session_id=%s", session_id)
        return history  # bail out gracefully

    if not summary:
        return history

    compressed = [
        {
            "role": "system",
            "content": f"[Earlier conversation summary]\n{summary}",
            "timestamp": datetime.now().isoformat(),
        },
        *recent,
    ]
    _session_store.replace_transcript(session_id, compressed)
    _metrics.sessions_compressed += 1
    logger.info("compressed session_id=%s from %d → %d messages", session_id, len(history), len(compressed))
    return compressed


# ------------------------------------------------------------------
# Commands (intercepted before reaching the agent)
# ------------------------------------------------------------------
_COMMANDS = {"/reset", "/new", "/compact", "/help", "/status"}


def _extract_cmd(text: str) -> str | None:
    if not text:
        return None
    t = text.strip().lower()
    for cmd in _COMMANDS:
        if t == cmd or t.startswith(cmd + " "):
            return cmd
    return None


async def _handle_command(cmd: str, open_id: str, session_key: str, session_id: str) -> str:
    if cmd in ("/reset", "/new"):
        _session_store.reset_session(session_key)
        return "Session reset. Ready for a fresh conversation."
    if cmd == "/compact":
        tx = _session_store.load_transcript(session_id)
        before = len(tx)
        tx = await _maybe_compress(session_id, tx)
        after = len(tx)
        saved = before - after
        if saved > 0:
            return f"Compressed {before} → {after} messages (saved {saved})."
        return f"Transcript has {before} messages. Nothing to compress yet."
    if cmd == "/help":
        return (
            "Commands:\n"
            "/reset — fresh session\n"
            "/compact — compress history\n"
            "/status — session info\n"
            "/help — this message"
        )
    if cmd == "/status":
        entry = _session_store._meta_path(session_key)
        if entry.exists():
            data = __import__("json").loads(entry.read_text())
            tx = _session_store.load_transcript(data.get("session_id", ""))
            return f"Session: {data.get('session_id', '???')[:24]}…\nMessages: {len(tx)}"
        return "No active session."
    return "Unknown command."


# ------------------------------------------------------------------
# Core message handler
# ------------------------------------------------------------------
async def _on_message(event: MessageEvent) -> Optional[str]:
    open_id = event.source.user_id if event.source else None
    chat_id = event.source.chat_id if event.source else None
    if not open_id:
        logger.warning("drop event without user_id")
        return None
    if not chat_id:
        chat_id = open_id

    _metrics.messages_received += 1

    # Authorization
    if settings.allowed_users_set and open_id not in settings.allowed_users_set:
        logger.warning("unauthorized open_id=%s", open_id)
        return None

    # Resolve executor
    executor_url = _get_executor_endpoint(open_id)
    if not executor_url:
        logger.info("unbound open_id=%s", open_id)
        try:
            register_url = f"{settings.dashboard_url}/register?open_id={open_id}"
            await _delivery.send_registration_card(open_id, register_url)
            return None
        except Exception:
            logger.exception("send registration card failed open_id=%s", open_id)
            # Fallback text so FeishuAdapter sends it
            return "Please register first."

    # Session
    class _Src:
        pass

    src = _Src()
    src.platform = Platform.FEISHU
    src.user_id = open_id
    src.chat_id = chat_id
    src.chat_type = "dm"
    src.user_name = ""
    src.thread_id = None

    session_entry = _session_store.get_or_create_session(src)
    session_key = session_entry.session_key

    # Command interception
    text = (event.text or "").strip()
    cmd = _extract_cmd(text)
    if cmd:
        return await _handle_command(cmd, open_id, session_key, session_entry.session_id)

    # Load transcript + hygiene
    history = _session_store.load_transcript(session_entry.session_id)
    history = await _maybe_compress(session_entry.session_id, history)

    # Build context prompt (minimal; executor can enrich)
    context_prompt = (
        f"[System: You are a digital employee for user {open_id}. "
        "Platform: Feishu. Be concise and direct.]"
    )

    # Attachments: FeishuAdapter downloaded files to local paths
    attachments: list[dict[str, Any]] = []
    media_urls = event.media_urls or []
    media_types = event.media_types or []
    for idx, path in enumerate(media_urls):
        mtype = media_types[idx] if media_types and idx < len(media_types) else ""
        try:
            with open(path, "rb") as f:
                raw = f.read()
            attachments.append({
                "name": os.path.basename(path),
                "message_type": mtype,
                "content_b64": base64.b64encode(raw).decode("ascii"),
            })
        except Exception:
            logger.warning("failed to read attachment %s", path, exc_info=True)

    # Call executor
    payload = {
        "message": text,
        "history": history,
        "context_prompt": context_prompt,
        "session_id": session_entry.session_id,
        "user_id": open_id,
        "attachments": attachments,
        "user_tokens": _get_user_tokens(open_id),
    }

    response_text: str = ""
    files: list[dict[str, str]] = []
    exec_status = "success"
    error_code = ""
    error_message = ""
    await _start_typing(chat_id)
    try:
        async with httpx.AsyncClient(timeout=settings.executor_timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(f"{executor_url}/execute", json=payload)
                    resp.raise_for_status()
                    result = resp.json()
                    response_text = result.get("response") or ""
                    files = result.get("files") or []
                    break
                except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                    if attempt < 2:
                        wait = 1.5 * (2 ** attempt)
                        logger.warning("executor retry open_id=%s attempt=%d wait=%.1fs: %s", open_id, attempt + 1, wait, exc)
                        await asyncio.sleep(wait)
                    else:
                        raise
    except httpx.TimeoutException:
        logger.error("executor timeout open_id=%s", open_id)
        response_text = "⏳ 处理超时，请稍后再试。"
        exec_status = "failed"
        error_code = "timeout"
        error_message = "executor timeout"
        _metrics.executor_timeouts += 1
        _metrics.executor_errors += 1
    except httpx.ConnectError:
        logger.error("executor connect error open_id=%s", open_id)
        response_text = "🚀 您的智能助手正在启动，请几秒后重试。"
        exec_status = "failed"
        error_code = "connect_error"
        error_message = "executor connect error"
        _metrics.executor_errors += 1
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.error("executor HTTP %d open_id=%s", status, open_id)
        response_text = f"⚠️ 服务暂时不可用 (HTTP {status})，请稍后再试。"
        exec_status = "failed"
        error_code = f"http_{status}"
        error_message = f"executor returned HTTP {status}"
        _metrics.executor_errors += 1
    except Exception as e:
        logger.error("executor error open_id=%s: %s", open_id, e)
        response_text = "❌ 处理消息时出错，请重试。"
        exec_status = "failed"
        error_code = "executor_error"
        error_message = str(e)
        _metrics.executor_errors += 1
    finally:
        await _stop_typing(chat_id)

    # Persist transcript only on success with a response
    ts = datetime.now().isoformat()
    if response_text or not history:
        if not history:
            _session_store.append_to_transcript(
                session_entry.session_id,
                {"role": "session_meta", "timestamp": ts},
            )
        _session_store.append_to_transcript(
            session_entry.session_id,
            {"role": "user", "content": text, "timestamp": ts},
        )
        if response_text:
            _session_store.append_to_transcript(
                session_entry.session_id,
                {"role": "assistant", "content": response_text, "timestamp": ts},
            )

    # Update metadata
    _session_store.update_session(session_key, updated_at=ts)

    # Deliver text via FeishuAdapter (chat_id). Fallback to open_id send path.
    if _adapter and response_text:
        try:
            send_result = await _adapter.send(chat_id, response_text)
            if getattr(send_result, "success", False):
                _metrics.messages_sent += 1
            else:
                logger.error(
                    "send text failed open_id=%s chat_id=%s err=%s",
                    open_id,
                    chat_id,
                    getattr(send_result, "error", "unknown"),
                )
                await _delivery.send_text(open_id, response_text)
                _metrics.messages_sent += 1
        except Exception:
            logger.exception("send text failed open_id=%s chat_id=%s", open_id, chat_id)
            await _delivery.send_text(open_id, response_text)
            _metrics.messages_sent += 1

    # Deliver files via delivery layer
    for f in files:
        name = f.get("name") or "file.bin"
        b64 = f.get("content_b64")
        if not b64:
            continue
        try:
            raw = base64.b64decode(b64)
            if len(raw) <= 30 * 1024 * 1024:
                await _delivery.send_file(open_id, name, raw)
                continue

            access_token = _get_drive_token(open_id)
            drive_upload_ok = False
            if access_token:
                url = await _delivery.upload_to_user_drive(access_token, name, raw)
                if url:
                    await _delivery.send_text(
                        open_id,
                        f"文件 {name} 已上传到飞书云盘：{url}",
                    )
                    drive_upload_ok = True
                    continue
                logger.warning("drive upload failed open_id=%s file=%s", open_id, name)

            if r2.is_configured():
                try:
                    r2_url = await asyncio.get_running_loop().run_in_executor(None, r2.upload_file, name, raw)
                    await _delivery.send_text(
                        open_id,
                        f"文件 {name} 已上传到下载空间：{r2_url}\n链接有效期由存储策略决定。",
                    )
                    continue
                except Exception:
                    logger.exception("r2 upload failed open_id=%s file=%s", open_id, name)

            if access_token and not drive_upload_ok:
                await _delivery.send_text(
                    open_id,
                    f"文件 {name} 上传失败（云盘与下载空间均不可用），请稍后重试。",
                )
                continue

            auth_url = _delivery.build_drive_auth_url(settings.api_base_url, open_id)
            await _delivery.send_drive_auth_card(open_id, name, auth_url)
        except Exception:
            logger.exception("send file failed open_id=%s", open_id)

    # Persist run-level execution log for user dashboard visibility.
    _log_execution(
        open_id=open_id,
        session_id=session_entry.session_id,
        request_text=text,
        status=exec_status,
        error_code=error_code,
        error_message=error_message,
        response_text=response_text,
        files_count=len(files),
    )

    # Fire-and-forget: sync memory files back to DB after successful execution.
    if exec_status == "success" and executor_url:
        user_id = _get_user_id(open_id)
        if user_id:
            asyncio.create_task(_sync_memory_to_db(executor_url, user_id))

    return None  # We already sent manually


# ------------------------------------------------------------------
# Adapter lifecycle
# ------------------------------------------------------------------
async def _run_adapter() -> None:
    global _adapter

    platform_cfg = PlatformConfig(enabled=True, extra={})
    adapter = FeishuAdapter(platform_cfg)
    adapter.set_message_handler(_on_message)
    _adapter = adapter

    connected = await adapter.connect()
    if not connected:
        logger.error("FeishuAdapter failed to connect")
        return

    logger.info("FeishuAdapter connected")
    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        raise
    finally:
        await adapter.disconnect()


# ------------------------------------------------------------------
# Idle session cleanup — runs every hour
# ------------------------------------------------------------------
async def _cleanup_idle_sessions() -> None:
    while True:
        await asyncio.sleep(3600)
        now = datetime.now().timestamp()
        cut_off = 7 * 86400  # 7 days
        cleaned = 0
        for path in Path(settings.sessions_dir).glob("*.json"):
            try:
                data = json.loads(path.read_text())
                updated = datetime.fromisoformat(data.get("updated_at", "2000-01-01T00:00:00")).timestamp()
                if now - updated > cut_off:
                    sid = data.get("session_id")
                    if sid:
                        tx = _session_store._tx_path(sid)
                        if tx.exists():
                            tx.unlink()
                    path.unlink()
                    cleaned += 1
            except Exception:
                pass
        if cleaned:
            logger.info("cleaned %d idle sessions", cleaned)


@app.on_event("startup")
async def startup() -> None:
    global _adapter_task, _cleanup_task
    _adapter_task = asyncio.create_task(_run_adapter())
    _cleanup_task = asyncio.create_task(_cleanup_idle_sessions())


@app.on_event("shutdown")
async def shutdown() -> None:
    global _adapter_task, _cleanup_task
    if _adapter_task:
        _adapter_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _adapter_task
    if _cleanup_task:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
    if _adapter:
        await _adapter.disconnect()


@app.get("/health")
def health() -> dict[str, bool]:
    running = bool(_adapter and getattr(_adapter, "is_connected", False))
    return {"ok": running}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {
        "messages_received": _metrics.messages_received,
        "messages_sent": _metrics.messages_sent,
        "executor_errors": _metrics.executor_errors,
        "executor_timeouts": _metrics.executor_timeouts,
        "sessions_compressed": _metrics.sessions_compressed,
    }


# ------------------------------------------------------------------
# Internal notification endpoint (called by api service)
# ------------------------------------------------------------------
@app.post("/internal/notify")
async def internal_notify(
    open_id: str = Form(...),
    text: str = Form(...),
    x_internal_secret: str | None = Header(default=None),
):
    if x_internal_secret != settings.gateway_key:
        raise HTTPException(status_code=403, detail="invalid secret")
    if text:
        try:
            await _delivery.send_text(open_id, text)
        except Exception:
            logger.exception("internal notify failed open_id=%s", open_id)
    return {"ok": True}
