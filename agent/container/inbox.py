"""
Thin HTTP wrapper around hermes AIAgent.
Calls our LiteLLM Gateway — no direct LLM API keys needed in this container.

Uses Hermes native session persistence (SessionDB) keyed by Feishu open_id.
Also forwards Hermes tool/status progress updates back to Feishu.
"""
import asyncio
import base64
import json
import logging
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from hermes_state import SessionDB
from run_agent import AIAgent

logger = logging.getLogger(__name__)
app = FastAPI()

ROUTER_REPLY_URL = os.environ["ROUTER_REPLY_URL"]
GATEWAY_URL = os.environ["GATEWAY_URL"]            # http://gateway:4000/v1
GATEWAY_KEY = os.environ["GATEWAY_KEY"]            # litellm master key
HERMES_MODEL = os.environ.get("HERMES_MODEL", "default")
HERMES_STATE_DB_PATH = Path(os.environ.get("HERMES_STATE_DB_PATH", "/root/.hermes/state/state.db"))
HERMES_SKILLS_DIR = Path(os.environ.get("HERMES_SKILLS_DIR", "/root/.hermes/skills"))
HERMES_WORKSPACE_DIR = Path(os.environ.get("HERMES_WORKSPACE_DIR", "/root/.hermes/workspace"))
HERMES_ENABLED_TOOLSETS = [
    "file",
    "terminal",
    "skills",
    "memory",
    "session_search",
    "clarify",
    "code_execution",
    "delegation",
    "todo",
    "tts",
    "vision",
    "browser",
    "feishu_doc",
    "feishu_drive",
]
_UPLOADS_DIR = HERMES_WORKSPACE_DIR / "uploads"
_WORKSPACE_PATH_PATTERN = re.compile(r"(/root/\.hermes/workspace/[^\s'\"`]+)")
DEFAULT_CONFIG_PATH = Path("/app/default-config.yaml")
DEFAULT_SOUL_PATH = Path("/app/default-soul.md")
_SESSION_UPLOADS_ROOT = HERMES_WORKSPACE_DIR / ".session_uploads"

session_db = SessionDB(db_path=HERMES_STATE_DB_PATH)
_session_locks: dict[str, asyncio.Lock] = {}
_session_locks_guard = asyncio.Lock()


def _reset_corrupt_state_db(reason: Exception) -> None:
    global session_db
    ts = int(time.time())
    corrupt_path = HERMES_STATE_DB_PATH.with_suffix(f".corrupt.{ts}.db")
    try:
        if HERMES_STATE_DB_PATH.exists():
            HERMES_STATE_DB_PATH.rename(corrupt_path)
        print(f"[inbox] state db reset due to corruption: {reason}; backup={corrupt_path}", flush=True)
    except Exception as e:
        print(f"[inbox] failed to backup corrupt state db: {e}", flush=True)
    session_db = SessionDB(db_path=HERMES_STATE_DB_PATH)


def _bootstrap_hermes_home() -> None:
    """Ensure a fresh persisted /root/.hermes has required starter files/dirs."""
    hermes_home = Path("/root/.hermes")
    hermes_home.mkdir(parents=True, exist_ok=True)

    for rel in (
        "skills",
        "state",
        "workspace",
        "workspace/uploads",
        "workspace/downloads",
        "workspace/.session_uploads",
        "memories",
    ):
        (hermes_home / rel).mkdir(parents=True, exist_ok=True)

    config_path = hermes_home / "config.yaml"
    if not config_path.exists() and DEFAULT_CONFIG_PATH.exists():
        shutil.copy2(DEFAULT_CONFIG_PATH, config_path)

    soul_path = hermes_home / "SOUL.md"
    if not soul_path.exists() and DEFAULT_SOUL_PATH.exists():
        shutil.copy2(DEFAULT_SOUL_PATH, soul_path)


def _bootstrap_user_skills() -> None:
    """Ensure user skills dir exists and sync bundled skills into it."""
    HERMES_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from tools.skills_sync import sync_skills

        result = sync_skills(quiet=True) or {}
        logger.info(
            "skills synced copied=%s updated=%s user_modified=%s",
            len(result.get("copied", [])),
            len(result.get("updated", [])),
            len(result.get("user_modified", [])),
        )
    except Exception:
        logger.exception("skills bootstrap failed; continuing without sync")


class ProgressEmitter:
    def __init__(self, open_id: str):
        self.open_id = open_id
        self._client = httpx.Client(timeout=5)
        self._last_text = ""
        self._last_status_ts = 0.0
        self._tool_call_name: dict[str, str] = {}

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def _send(self, text: str, *, throttle_seconds: float = 0.0) -> None:
        text = (text or "").strip()
        if not text:
            return
        now = time.time()
        if throttle_seconds > 0 and (now - self._last_status_ts) < throttle_seconds:
            return
        if text == self._last_text:
            return

        self._last_text = text
        self._last_status_ts = now
        try:
            self._client.post(ROUTER_REPLY_URL, json={"open_id": self.open_id, "text": text})
        except Exception:
            logger.debug("progress update send failed", exc_info=True)

    def _resolve_tool_name(self, raw: str) -> str:
        if raw in self._tool_call_name:
            return self._tool_call_name[raw]
        if raw.startswith("call_"):
            return "工具调用"
        return raw

    def _extract_tool_name(self, *args, **kwargs) -> str:
        # Direct fields
        for key in ("tool_name", "name", "tool"):
            if key in kwargs and kwargs[key]:
                return self._resolve_tool_name(str(kwargs[key]))

        # Common callback signature in Hermes: (tool_call_id, function_name, function_args, ...)
        if len(args) >= 2 and isinstance(args[1], str) and args[1].strip():
            return args[1]

        # Common nested style: {"function": {"name": "bash"}}
        obj = kwargs.get("tool_call") or kwargs.get("call")
        if isinstance(obj, dict):
            fn = obj.get("function")
            if isinstance(fn, dict) and fn.get("name"):
                return str(fn["name"])
            if obj.get("name"):
                return str(obj["name"])
            if obj.get("id"):
                return self._resolve_tool_name(str(obj["id"]))

        if args:
            first = args[0]
            if isinstance(first, str):
                return self._resolve_tool_name(first)
            if isinstance(first, dict):
                for key in ("tool_name", "name", "tool"):
                    if first.get(key):
                        return self._resolve_tool_name(str(first[key]))
                fn = first.get("function")
                if isinstance(fn, dict) and fn.get("name"):
                    return str(fn["name"])
                if first.get("id"):
                    return self._resolve_tool_name(str(first["id"]))
        return "工具调用"

    @staticmethod
    def _extract_status_text(*args, **kwargs) -> str:
        for key in ("status", "message", "text"):
            if key in kwargs and kwargs[key]:
                return str(kwargs[key])
        if args:
            first = args[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("status", "message", "text"):
                    if first.get(key):
                        return str(first[key])
        return "处理中..."

    def _short(self, value: str, limit: int = 90) -> str:
        value = (value or "").strip().replace("\n", " ")
        return value if len(value) <= limit else value[:limit] + "…"

    def _extract_tool_detail(self, *args, **kwargs) -> str:
        # Hermes callback often passes function_args as 3rd positional arg.
        raw = None
        if len(args) >= 3 and args[2]:
            raw = args[2]
        elif kwargs.get("args"):
            raw = kwargs.get("args")

        if raw is None:
            return ""

        if isinstance(raw, dict):
            data = raw
        else:
            text = str(raw).strip()
            if not text:
                return ""
            try:
                data = json.loads(text)
            except Exception:
                return self._short(text)

        for key in ("command", "query", "question", "prompt", "code", "path", "pattern"):
            if key in data and data[key]:
                return self._short(str(data[key]))
        return ""

    # Hermes callbacks (accept flexible signatures)
    def tool_start(self, *args, **kwargs) -> None:
        tool = self._extract_tool_name(*args, **kwargs)
        detail = self._extract_tool_detail(*args, **kwargs)
        if detail:
            self._send(f"🔧 正在执行：{tool}（{detail}）")
        else:
            self._send(f"🔧 正在执行：{tool}")

    def tool_complete(self, *args, **kwargs) -> None:
        # Intentionally no-op to reduce chat noise and extra message round-trips.
        return

    def status(self, *args, **kwargs) -> None:
        status = self._extract_status_text(*args, **kwargs)
        if status.strip().lower() in {"lifecycle", "running"}:
            return
        self._send(f"… {status}", throttle_seconds=2.0)

    def tool_gen(self, *args, **kwargs) -> None:
        # Best-effort capture of tool_call_id -> function_name mapping
        candidates = []
        candidates.extend(args)
        candidates.extend(v for v in kwargs.values())
        for item in candidates:
            if not isinstance(item, list):
                continue
            for call in item:
                if not isinstance(call, dict):
                    continue
                call_id = call.get("id")
                fn = call.get("function")
                if call_id and isinstance(fn, dict) and fn.get("name"):
                    self._tool_call_name[str(call_id)] = str(fn["name"])


def _session_id_from_open_id(open_id: str) -> str:
    return f"feishu:{open_id}"


async def _get_session_lock(session_id: str) -> asyncio.Lock:
    async with _session_locks_guard:
        lock = _session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _session_locks[session_id] = lock
        return lock


def _sanitize_file_name(name: str) -> str:
    name = (name or "upload.bin").strip()
    name = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return safe[:120] or "upload.bin"


def _session_upload_manifest_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", session_id)
    return _SESSION_UPLOADS_ROOT / f"{safe}.json"


def _load_session_uploads(session_id: str) -> list[dict[str, Any]]:
    path = _session_upload_manifest_path(session_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        file_path = str(item.get("path") or "").strip()
        if not file_path:
            continue
        normalized.append(
            {
                "path": file_path,
                "name": str(item.get("name") or Path(file_path).name),
                "message_type": str(item.get("message_type") or "file"),
                "uploaded_at": int(item.get("uploaded_at") or 0),
            }
        )
    return normalized


def _save_session_uploads(session_id: str, uploads: list[dict[str, Any]]) -> None:
    _SESSION_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    path = _session_upload_manifest_path(session_id)
    path.write_text(json.dumps(uploads, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_within_workspace(path: Path) -> bool:
    try:
        path.resolve().relative_to(HERMES_WORKSPACE_DIR.resolve())
        return True
    except Exception:
        return False


def _materialize_attachments(attachments: list["InboxAttachment"] | None) -> tuple[list[Path], list[str], list[dict[str, Any]]]:
    saved_paths: list[Path] = []
    notes: list[str] = []
    records: list[dict[str, Any]] = []
    if not attachments:
        return saved_paths, notes, records

    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for idx, att in enumerate(attachments, start=1):
        if not att.content_b64:
            continue
        try:
            raw = base64.b64decode(att.content_b64)
        except Exception:
            notes.append(f"- 附件#{idx} 解码失败，已跳过")
            continue
        ts = int(time.time() * 1000)
        file_name = _sanitize_file_name(att.name or f"attachment_{idx}.bin")
        dest = _UPLOADS_DIR / f"{ts}_{idx}_{file_name}"
        dest.write_bytes(raw)
        saved_paths.append(dest)
        notes.append(f"- {dest}")
        records.append(
            {
                "path": str(dest),
                "name": file_name,
                "message_type": att.message_type or "file",
                "uploaded_at": ts,
            }
        )

    return saved_paths, notes, records


def _build_turn_text(session_id: str, msg: "InboxMessage") -> str:
    saved_paths, notes, new_records = _materialize_attachments(msg.attachments)
    parts: list[str] = []

    existing = _load_session_uploads(session_id)
    if new_records:
        existing.extend(new_records)
        # 去重保序（按 path）
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in existing:
            p = str(item.get("path") or "")
            if not p or p in seen:
                continue
            seen.add(p)
            merged.append(item)
        _save_session_uploads(session_id, merged)
        existing = merged

    if msg.message_type:
        parts.append(f"[平台消息类型: {msg.message_type}]")
    if msg.raw_content is not None:
        parts.append(f"[平台原始内容: {json.dumps(msg.raw_content, ensure_ascii=False)}]")

    if saved_paths:
        parts.append("用户上传了附件，已保存到以下本地路径：\n" + "\n".join(notes))

    if existing:
        lines = [f"- {item.get('path')}" for item in existing if item.get("path")]
        if lines:
            parts.append("当前会话可用的历史上传文件（后续问题可继续引用）：\n" + "\n".join(lines))

    user_text = (msg.text or "").strip()
    if user_text:
        parts.append(user_text)

    return "\n\n".join(parts).strip()


_MAX_INLINE_FILE_BYTES = 20 * 1024 * 1024   # 20 MB — IM attachment limit
_MAX_DRIVE_FILE_BYTES  = 50 * 1024 * 1024   # 50 MB — Drive upload limit via this path


def _collect_reply_files(reply_text: str) -> tuple[list[dict], list[dict]]:
    """Returns (inline_files, drive_files).

    inline_files: ≤20 MB, sent as Feishu IM attachments.
    drive_files:  20–50 MB, routed through Feishu Drive OAuth upload.
    Files >50 MB are skipped with a log message.
    """
    inline_files: list[dict] = []
    drive_files: list[dict] = []
    seen: set[str] = set()
    for match in _WORKSPACE_PATH_PATTERN.findall(reply_text or ""):
        if match in seen:
            continue
        seen.add(match)
        p = Path(match)
        try:
            resolved = p.resolve(strict=True)
        except Exception:
            continue
        if not resolved.is_file() or not _is_within_workspace(resolved):
            continue
        size = resolved.stat().st_size
        if size > _MAX_DRIVE_FILE_BYTES:
            print(f"[inbox] skip oversized file {resolved.name} ({size} bytes)", flush=True)
            continue
        content = resolved.read_bytes()
        entry = {
            "name": resolved.name,
            "content_b64": base64.b64encode(content).decode("ascii"),
        }
        if size > _MAX_INLINE_FILE_BYTES:
            drive_files.append(entry)
        else:
            inline_files.append(entry)
    return inline_files, drive_files


def _run_turn(session_id: str, user_id: str, text: str, open_id: str) -> str:
    emitter = ProgressEmitter(open_id)
    try:
        print(f"[inbox] run_turn start session_id={session_id} user_id={user_id} text_len={len(text or '')}", flush=True)
        # Gateway pattern: fresh agent per turn + replay persisted conversation.
        print(f"[inbox] run_turn init agent session_id={session_id}", flush=True)
        agent = AIAgent(
            model=HERMES_MODEL,
            base_url=GATEWAY_URL,
            api_key=GATEWAY_KEY,
            session_id=session_id,
            session_db=session_db,
            platform="feishu",
            user_id=user_id,
            persist_session=True,
            enabled_toolsets=HERMES_ENABLED_TOOLSETS,
            tool_start_callback=emitter.tool_start,
            tool_complete_callback=emitter.tool_complete,
            tool_gen_callback=emitter.tool_gen,
            status_callback=emitter.status,
        )
        print(f"[inbox] run_turn agent initialized session_id={session_id}", flush=True)
        try:
            history = session_db.get_messages_as_conversation(session_id)
        except sqlite3.DatabaseError as e:
            _reset_corrupt_state_db(e)
            history = []
        print(f"[inbox] run_turn history loaded session_id={session_id} messages={len(history)}", flush=True)
        try:
            result = agent.run_conversation(text, conversation_history=history)
        except sqlite3.DatabaseError as e:
            _reset_corrupt_state_db(e)
            # Re-create agent with the fresh DB handle.
            agent = AIAgent(
                model=HERMES_MODEL,
                base_url=GATEWAY_URL,
                api_key=GATEWAY_KEY,
                session_id=session_id,
                session_db=session_db,
                platform="feishu",
                user_id=user_id,
                persist_session=True,
                enabled_toolsets=HERMES_ENABLED_TOOLSETS,
                tool_start_callback=emitter.tool_start,
                tool_complete_callback=emitter.tool_complete,
                tool_gen_callback=emitter.tool_gen,
                status_callback=emitter.status,
            )
            result = agent.run_conversation(text, conversation_history=[])
        final_text = result["final_response"] if isinstance(result, dict) else str(result)
        print(f"[inbox] run_turn done session_id={session_id} response_len={len(final_text or '')}", flush=True)
        return final_text
    finally:
        emitter.close()


class InboxAttachment(BaseModel):
    name: str | None = None
    message_type: str | None = None
    feishu_file_key: str | None = None
    content_b64: str


class InboxMessage(BaseModel):
    open_id: str
    text: str = ""
    attachments: list[InboxAttachment] | None = None
    message_type: str | None = None
    raw_content: dict | None = None
    message_id: str | None = None
    reaction_id: str | None = None


async def _process(msg: InboxMessage) -> None:
    session_id = _session_id_from_open_id(msg.open_id)
    session_lock = await _get_session_lock(session_id)
    try:
        print(f"[inbox] process start open_id={msg.open_id} session_id={session_id}", flush=True)
        turn_text = _build_turn_text(session_id, msg)
        if not turn_text.strip():
            print(f"[inbox] process skip empty turn_text session_id={session_id}", flush=True)
            return

        async with session_lock:
            loop = asyncio.get_event_loop()
            text = await asyncio.wait_for(
                loop.run_in_executor(None, _run_turn, session_id, msg.open_id, turn_text, msg.open_id),
                timeout=180,
            )

        payload: dict = {"open_id": msg.open_id, "text": text}
        inline_files, drive_files = _collect_reply_files(text)
        if inline_files:
            payload["files"] = inline_files
        if drive_files:
            payload["drive_files"] = drive_files
        if msg.message_id:
            payload["message_id"] = msg.message_id
        if msg.reaction_id:
            payload["reaction_id"] = msg.reaction_id

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(ROUTER_REPLY_URL, json=payload)
            print(f"[inbox] process reply posted session_id={session_id} status={resp.status_code}", flush=True)
    except asyncio.TimeoutError:
        logger.exception("_process timeout for open_id=%s session_id=%s", msg.open_id, session_id)
    except Exception:
        logger.exception("_process failed for open_id=%s session_id=%s", msg.open_id, session_id)


@app.on_event("startup")
async def _startup() -> None:
    _bootstrap_hermes_home()
    _bootstrap_user_skills()


@app.post("/inbox")
async def inbox(msg: InboxMessage, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process, msg)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
