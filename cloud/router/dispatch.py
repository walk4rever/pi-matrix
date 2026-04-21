"""
Route incoming messages to the correct agent instance.
On first message from an unbound open_id, prompt user to link their account.
"""
import httpx
from supabase import create_client
from feishu import send_message, send_registration_card
from config import settings

supabase = create_client(settings.supabase_url, settings.supabase_service_key)


async def dispatch(
    open_id: str,
    text: str,
    message_id: str | None = None,
    reaction_id: str | None = None,
) -> None:
    user_id = _resolve_user(open_id)

    if user_id is None:
        await _handle_unbound(open_id, text)
        return

    instance = _resolve_instance(user_id)
    if instance is None:
        await send_message(open_id, "Your instance is being set up, please try again in a moment.")
        return

    await _deliver(instance["endpoint"], open_id, text, message_id=message_id, reaction_id=reaction_id)


def _resolve_user(open_id: str) -> str | None:
    result = supabase.table("pi_matrix_feishu_bindings") \
        .select("user_id").eq("open_id", open_id).maybe_single().execute()
    if result is None or not result.data:
        return None
    return result.data["user_id"]


def _resolve_instance(user_id: str) -> dict | None:
    result = supabase.table("pi_matrix_devices") \
        .select("endpoint,instance_type") \
        .eq("user_id", user_id) \
        .eq("instance_type", "cloud") \
        .maybe_single().execute()
    if result is None or not result.data:
        return None
    return result.data


async def _deliver(
    endpoint: str,
    open_id: str,
    text: str,
    message_id: str | None = None,
    reaction_id: str | None = None,
) -> None:
    payload = {"open_id": open_id, "text": text}
    if message_id:
        payload["message_id"] = message_id
    if reaction_id:
        payload["reaction_id"] = reaction_id
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(endpoint, json=payload)


async def _handle_unbound(open_id: str, text: str) -> None:
    register_url = f"{settings.dashboard_url}/register?open_id={open_id}"
    await send_registration_card(open_id, register_url)
