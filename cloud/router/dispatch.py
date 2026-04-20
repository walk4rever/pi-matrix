"""
Route incoming messages to the correct agent instance.
On first message from an unbound open_id, prompt user to link their account.
"""
import httpx
from supabase import create_client
from feishu import send_message
from config import settings

supabase = create_client(settings.supabase_url, settings.supabase_service_key)


async def dispatch(open_id: str, text: str) -> None:
    user_id = _resolve_user(open_id)

    if user_id is None:
        await _handle_unbound(open_id, text)
        return

    instance = _resolve_instance(user_id)
    if instance is None:
        await send_message(open_id, "Your instance is being set up, please try again in a moment.")
        return

    await _deliver(instance["endpoint"], open_id, text)


def _resolve_user(open_id: str) -> str | None:
    result = supabase.table("pi_matrix_feishu_bindings") \
        .select("user_id").eq("open_id", open_id).maybe_single().execute()
    return result.data["user_id"] if result.data else None


def _resolve_instance(user_id: str) -> dict | None:
    result = supabase.table("pi_matrix_devices") \
        .select("endpoint,instance_type") \
        .eq("user_id", user_id) \
        .eq("instance_type", "cloud") \
        .maybe_single().execute()
    return result.data or None


async def _deliver(endpoint: str, open_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=60) as client:
        await client.post(endpoint, json={"open_id": open_id, "text": text})


async def _handle_unbound(open_id: str, text: str) -> None:
    await send_message(
        open_id,
        f"欢迎使用 pi-matrix！点击注册您的数字员工：https://air7.fun/register?open_id={open_id}"
    )
