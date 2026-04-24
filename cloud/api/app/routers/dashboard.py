from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends

from app.db import supabase
from app.middleware.auth import get_current_user

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
        status = _device_status(last_seen)
        if status == "运行中":
            online_count += 1
        instance_type = str(row.get("instance_type") or "mac")
        is_cloud = instance_type == "cloud"

        detail = "容器在线。" if is_cloud and status == "运行中" else "等待设备心跳。"
        if is_cloud and row.get("endpoint"):
            detail = "云端执行入口可达。" if status == "运行中" else "云端执行入口已注册，等待新心跳。"

        devices.append(
            {
                "id": row.get("id"),
                "name": row.get("name") or ("Cloud Executor" if is_cloud else "Mac 设备"),
                "type": "云端" if is_cloud else "Mac 端",
                "status": status,
                "version": row.get("version") or "-",
                "last_seen": _humanize_time_ago(last_seen),
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
    has_feishu_binding = bool(binding and binding.data and binding.data.get("open_id"))

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

    run_logs: list[dict[str, Any]] = []
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
