from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.db import supabase
from app.middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_ONLINE_WINDOW = timedelta(minutes=5)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _humanize_time_ago(ts: datetime | None) -> str:
    if ts is None:
        return "未知"
    now = datetime.now(timezone.utc)
    delta = now - ts
    secs = int(max(delta.total_seconds(), 0))
    if secs < 10:
        return "刚刚"
    if secs < 60:
        return f"{secs} 秒前"
    mins = secs // 60
    if mins < 60:
        return f"{mins} 分钟前"
    hours = mins // 60
    if hours < 24:
        return f"{hours} 小时前"
    days = hours // 24
    return f"{days} 天前"


def _device_status(last_seen: datetime | None) -> str:
    if not last_seen:
        return "离线"
    return "运行中" if datetime.now(timezone.utc) - last_seen <= _ONLINE_WINDOW else "离线"


def _short_text(text: str, max_len: int = 56) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def _credential_content(res: Any) -> str:
    if not res:
        return ""
    data = getattr(res, "data", None)
    if not data or not isinstance(data, dict):
        return ""
    return str(data.get("credential_value") or "")


def _cloud_endpoint_healthy(endpoint: str | None) -> bool:
    if not endpoint:
        return False
    base = str(endpoint).strip().rstrip("/")
    if not base:
        return False
    candidates = [f"{base}/health", base]
    try:
        with httpx.Client(timeout=2.0) as client:
            for url in candidates:
                try:
                    resp = client.get(url)
                    if resp.status_code < 500:
                        return True
                except Exception:
                    continue
    except Exception:
        return False
    return False


def _query_run_logs(user_id: str, page: int = 1, page_size: int = 10) -> dict[str, Any]:
    page = max(page, 1)
    page_size = max(1, min(page_size, 50))
    offset = (page - 1) * page_size

    run_logs: list[dict[str, Any]] = []
    total = 0

    try:
        total_res = (
            supabase.table("pi_matrix_execution_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        total = int(getattr(total_res, "count", 0) or 0)
    except Exception:
        total = 0

    try:
        log_res = (
            supabase.table("pi_matrix_execution_logs")
            .select("created_at,request_text,status,error_code,error_message,response_preview,files_count")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = log_res.data or []
        for row in rows:
            status_text = "成功" if str(row.get("status") or "success") == "success" else "失败"
            reason = (
                str(row.get("error_message") or row.get("error_code") or "").strip()
                if status_text == "失败"
                else "执行完成"
            )
            if not reason:
                reason = "执行失败"
            files_count = int(row.get("files_count") or 0)
            output_text = f"{files_count} 个文件" if files_count > 0 else "-"
            run_logs.append(
                {
                    "time": row.get("created_at"),
                    "task": _short_text(str(row.get("request_text") or "执行任务")),
                    "status": status_text,
                    "reason": _short_text(reason, 80),
                    "output": output_text,
                    "retryable": status_text == "失败",
                }
            )
    except Exception:
        run_logs = []

    return {"items": run_logs, "total": total, "page": page, "page_size": page_size}


@router.get("/overview")
def dashboard_overview(user: dict = Depends(get_current_user)):
    user_id = user["sub"]

    devices_res = (
        supabase.table("pi_matrix_devices")
        .select("id,name,instance_type,version,last_seen,endpoint,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    device_rows = devices_res.data or []

    devices: list[dict[str, Any]] = []
    online_count = 0
    for row in device_rows:
        last_seen = _parse_dt(str(row.get("last_seen") or ""))
        instance_type = str(row.get("instance_type") or "mac")
        is_cloud = instance_type == "cloud"
        endpoint = str(row.get("endpoint") or "").strip()
        cloud_health_ok = _cloud_endpoint_healthy(endpoint) if is_cloud else False

        status = _device_status(last_seen)
        if is_cloud and cloud_health_ok:
            status = "运行中"
        if status == "运行中":
            online_count += 1

        if is_cloud:
            if cloud_health_ok:
                detail = "云端容器健康，执行入口可达。"
            elif endpoint:
                detail = "云端执行入口已注册，等待容器恢复。"
            else:
                detail = "云端执行入口未注册。"
        else:
            detail = "设备在线。" if status == "运行中" else "等待设备心跳。"

        last_seen_display = _humanize_time_ago(last_seen)
        if is_cloud and cloud_health_ok and last_seen_display == "未知":
            last_seen_display = "健康检查在线"

        devices.append(
            {
                "id": row.get("id"),
                "name": row.get("name") or ("Cloud Executor" if is_cloud else "Mac 设备"),
                "type": "云端" if is_cloud else "Mac 端",
                "status": status,
                "version": row.get("version") or "-",
                "last_seen": last_seen_display,
                "detail": detail,
            }
        )

    # Binding status
    binding = (
        supabase.table("pi_matrix_feishu_bindings")
        .select("open_id")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    binding_data = getattr(binding, "data", None)
    has_feishu_binding = bool(binding_data and binding_data.get("open_id"))

    # User-provided credentials
    cred_res = (
        supabase.table("pi_matrix_user_credentials")
        .select("provider,credential_value")
        .eq("user_id", user_id)
        .execute()
    )
    cred_rows = cred_res.data or []
    provider_ready: dict[str, bool] = {}
    for row in cred_rows:
        provider = str(row.get("provider") or "").strip()
        value = str(row.get("credential_value") or "").strip()
        if provider and value:
            provider_ready[provider] = True

    platform_ready = {
        "tavily": bool((os.getenv("TAVILY_API_KEY") or "").strip()),
    }

    capability_spec = [
        {
            "capability": "Feishu 会话",
            "credential": "feishu_binding",
            "owner": "用户授权",
            "check": "binding",
        },
        {
            "capability": "飞书云盘大文件",
            "credential": "feishu_drive",
            "owner": "用户提供",
            "check": "provider",
            "provider": "feishu_drive",
        },
        {
            "capability": "Web 检索",
            "credential": "tavily",
            "owner": "平台提供",
            "check": "platform",
            "platform_key": "tavily",
        },
        {
            "capability": "图像生成",
            "credential": "fal",
            "owner": "用户提供",
            "check": "provider",
            "provider": "fal",
        },
        {
            "capability": "MoA 多模型",
            "credential": "openrouter",
            "owner": "用户提供",
            "check": "provider",
            "provider": "openrouter",
        },
        {
            "capability": "Discord",
            "credential": "discord",
            "owner": "用户提供",
            "check": "provider",
            "provider": "discord",
        },
        {
            "capability": "Home Assistant",
            "credential": "homeassistant",
            "owner": "用户提供",
            "check": "provider",
            "provider": "homeassistant",
        },
        {
            "capability": "RL",
            "credential": "rl",
            "owner": "用户提供",
            "check": "provider",
            "provider": "rl",
        },
    ]

    capabilities: list[dict[str, Any]] = []
    ready_count = 0
    for spec in capability_spec:
        configured = False
        if spec["check"] == "binding":
            configured = has_feishu_binding
        elif spec["check"] == "provider":
            configured = provider_ready.get(str(spec.get("provider") or ""), False)
        elif spec["check"] == "platform":
            configured = platform_ready.get(str(spec.get("platform_key") or ""), False)

        capability_status = "可用" if configured else "不可用"
        credential_status = "已配置" if configured else "未配置"
        if configured:
            ready_count += 1

        capabilities.append(
            {
                "capability": spec["capability"],
                "capability_status": capability_status,
                "credential": spec["credential"],
                "owner": spec["owner"],
                "credential_status": credential_status,
                "action": "查看配置" if configured else "去配置凭证",
            }
        )

    memory_res = (
        supabase.table("pi_matrix_memories")
        .select("id,content,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    memory_events = memory_res.data or []

    latest_memory_at = None
    if memory_events:
        latest_memory_at = _parse_dt(str(memory_events[0].get("created_at") or ""))

    def _find_memory_file_ts(pattern: str) -> datetime | None:
        try:
            res = (
                supabase.table("pi_matrix_memories")
                .select("created_at")
                .eq("user_id", user_id)
                .ilike("content", pattern)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                return latest_memory_at
            return _parse_dt(str(rows[0].get("created_at") or ""))
        except Exception:
            return latest_memory_at

    memory_md_ts = _find_memory_file_ts("%MEMORY.md%")
    user_md_ts = _find_memory_file_ts("%USER.md%")

    memory_files = [
        {
            "file": "MEMORY.md",
            "role": "长期任务记忆",
            "updated_at": _humanize_time_ago(memory_md_ts),
            "summary": "沉淀任务事实、上下文与长期偏好。",
            "status": "已启用",
        },
        {
            "file": "USER.md",
            "role": "用户画像与规则",
            "updated_at": _humanize_time_ago(user_md_ts),
            "summary": "记录用户风格、约束与固定偏好。",
            "status": "已启用",
        },
    ]

    log_page = _query_run_logs(user_id=user_id, page=1, page_size=10)
    run_logs: list[dict[str, Any]] = list(log_page.get("items") or [])

    if not run_logs:
        # Backward-compatible fallback before execution log table is available.
        failure_keywords = ("fail", "error", "exception", "timeout", "失败", "错误", "超时")
        for row in memory_events[:10]:
            content = str(row.get("content") or "")
            lower = content.lower()
            failed = any(k in lower for k in failure_keywords)
            run_logs.append(
                {
                    "time": row.get("created_at"),
                    "task": _short_text(content or "执行事件"),
                    "status": "失败" if failed else "成功",
                    "reason": "检测到失败关键词" if failed else "执行记录",
                    "output": "-",
                    "retryable": failed,
                }
            )

    return {
        "profile": {"email": user.get("email"), "user_id": user_id},
        "summary": {
            "device_total": len(devices),
            "online_devices": online_count,
            "capability_total": len(capabilities),
            "capability_ready": ready_count,
        },
        "devices": devices,
        "capabilities": capabilities,
        "memory_files": memory_files,
        "run_logs": run_logs,
    }


@router.get("/execution-logs")
def dashboard_execution_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]
    log_page = _query_run_logs(user_id=user_id, page=page, page_size=page_size)

    if log_page["items"]:
        return log_page

    # Fallback for users without log-table records yet.
    memory_total = 0
    try:
        m_total_res = (
            supabase.table("pi_matrix_memories")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        memory_total = int(getattr(m_total_res, "count", 0) or 0)
    except Exception:
        memory_total = 0

    memory_res = (
        supabase.table("pi_matrix_memories")
        .select("content,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range((page - 1) * page_size, page * page_size - 1)
        .execute()
    )
    rows = memory_res.data or []
    failure_keywords = ("fail", "error", "exception", "timeout", "失败", "错误", "超时")
    fallback_items = []
    for row in rows:
        content = str(row.get("content") or "")
        lower = content.lower()
        failed = any(k in lower for k in failure_keywords)
        fallback_items.append(
            {
                "time": row.get("created_at"),
                "task": _short_text(content or "执行事件"),
                "status": "失败" if failed else "成功",
                "reason": "检测到失败关键词" if failed else "执行记录",
                "output": "-",
                "retryable": failed,
            }
        )

    return {"items": fallback_items, "total": memory_total, "page": page, "page_size": page_size}


_MEMORY_FILE_PROVIDERS: dict[str, str] = {
    "USER": "user_md",
    "MEMORY": "memory_md",
}


class MemoryFileBody(BaseModel):
    content: str


@router.get("/memory/{file_key}")
def get_memory_file(file_key: str, user: dict = Depends(get_current_user)) -> dict[str, str]:
    provider = _MEMORY_FILE_PROVIDERS.get(file_key.upper())
    if not provider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown memory file")
    user_id = user["sub"]
    try:
        providers = [provider]
        if file_key.upper() == "USER":
            providers.append("memory_user_md")

        content = ""
        for current_provider in providers:
            res = (
                supabase.table("pi_matrix_user_credentials")
                .select("credential_value")
                .eq("user_id", user_id)
                .eq("provider", current_provider)
                .eq("credential_key", "content")
                .maybe_single()
                .execute()
            )
            content = _credential_content(res)
            if content:
                provider = current_provider
                break
        logger.info(
            "get_memory_file user=%s file=%s found=%s len=%d",
            user_id,
            file_key,
            bool(content),
            len(content),
        )
        return {"content": content}
    except Exception:
        logger.exception("get_memory_file failed user=%s file=%s", user_id, file_key)
        raise


def _get_cloud_executor_url(user_id: str) -> str | None:
    """Return the cloud executor base URL for a user, or None."""
    try:
        res = (
            supabase.table("pi_matrix_devices")
            .select("endpoint")
            .eq("user_id", user_id)
            .eq("instance_type", "cloud")
            .maybe_single()
            .execute()
        )
        data = getattr(res, "data", None)
        if not data:
            return None
        url = str(data.get("endpoint") or "").strip().rstrip("/")
        for suffix in ("/inbox", "/execute"):
            if url.endswith(suffix):
                url = url[: -len(suffix)]
        return url or None
    except Exception:
        return None


@router.put("/memory/{file_key}")
def update_memory_file(
    file_key: str, body: MemoryFileBody, user: dict = Depends(get_current_user)
) -> dict[str, bool]:
    provider = _MEMORY_FILE_PROVIDERS.get(file_key.upper())
    if not provider:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown memory file")
    user_id = user["sub"]

    # Write to DB first (always succeeds even if executor is offline).
    supabase.table("pi_matrix_user_credentials").upsert(
        {
            "user_id": user_id,
            "provider": provider,
            "credential_key": "content",
            "credential_value": body.content,
        },
        on_conflict="user_id,provider,credential_key",
    ).execute()

    # Best-effort push to executor container.
    executor_url = _get_cloud_executor_url(user_id)
    if executor_url:
        try:
            resp = httpx.put(
                f"{executor_url}/files/{file_key.upper()}",
                json={"content": body.content},
                timeout=5.0,
            )
            if resp.status_code != 200:
                import logging
                logging.getLogger(__name__).warning(
                    "executor file push failed user_id=%s file=%s status=%d",
                    user_id, file_key, resp.status_code,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "executor file push skipped (offline?) user_id=%s file=%s", user_id, file_key
            )

    return {"ok": True}


class SoulUpdateBody(BaseModel):
    content: str


@router.get("/soul")
def get_soul(user: dict = Depends(get_current_user)) -> dict[str, str]:
    user_id = user["sub"]
    res = (
        supabase.table("pi_matrix_user_credentials")
        .select("credential_value")
        .eq("user_id", user_id)
        .eq("provider", "soul_md")
        .eq("credential_key", "content")
        .maybe_single()
        .execute()
    )
    content = _credential_content(res)
    return {"content": content}


@router.put("/soul")
def update_soul(body: SoulUpdateBody, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    user_id = user["sub"]
    supabase.table("pi_matrix_user_credentials").upsert(
        {
            "user_id": user_id,
            "provider": "soul_md",
            "credential_key": "content",
            "credential_value": body.content,
        },
        on_conflict="user_id,provider,credential_key",
    ).execute()

    executor_url = _get_cloud_executor_url(user_id)
    if executor_url:
        try:
            resp = httpx.put(
                f"{executor_url}/files/SOUL",
                json={"content": body.content},
                timeout=5.0,
            )
            if resp.status_code != 200:
                import logging
                logging.getLogger(__name__).warning(
                    "executor soul push failed user_id=%s status=%d", user_id, resp.status_code
                )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "executor soul push skipped (offline?) user_id=%s", user_id
            )

    return {"ok": True}
