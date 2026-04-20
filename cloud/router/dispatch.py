"""
Route incoming messages to the correct agent instance.

Cloud instance: HTTP POST to container endpoint.
Mac mini: push via persistent WebSocket connection (registry below).
"""
import asyncio
import httpx
from supabase import create_client
from config import settings

supabase = create_client(settings.supabase_url, settings.supabase_service_key)

# open_id -> asyncio.Queue for Mac mini long-poll delivery
_mac_queues: dict[str, asyncio.Queue] = {}


def register_mac_queue(open_id: str, queue: asyncio.Queue) -> None:
    _mac_queues[open_id] = queue


def unregister_mac_queue(open_id: str) -> None:
    _mac_queues.pop(open_id, None)


async def dispatch(open_id: str, text: str) -> None:
    user = _resolve_user(open_id)
    if user is None:
        return  # unbound open_id, silently drop

    instance = _resolve_instance(user["id"])
    if instance is None:
        return

    if instance["type"] == "cloud":
        await _deliver_to_cloud(instance["endpoint"], open_id, text)
    else:
        await _deliver_to_mac(open_id, text)


def _resolve_user(open_id: str) -> dict | None:
    result = supabase.table("feishu_bindings").select("user_id").eq("open_id", open_id).maybe_single().execute()
    if not result.data:
        return None
    user_result = supabase.table("users").select("id").eq("id", result.data["user_id"]).single().execute()
    return user_result.data


def _resolve_instance(user_id: str) -> dict | None:
    result = supabase.table("devices").select("id,instance_type,endpoint").eq("user_id", user_id).maybe_single().execute()
    if not result.data:
        return None
    return {
        "type": result.data.get("instance_type", "mac"),
        "endpoint": result.data.get("endpoint"),
    }


async def _deliver_to_cloud(endpoint: str, open_id: str, text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(endpoint, json={"open_id": open_id, "text": text}, timeout=30)


async def _deliver_to_mac(open_id: str, text: str) -> None:
    queue = _mac_queues.get(open_id)
    if queue:
        await queue.put(text)
