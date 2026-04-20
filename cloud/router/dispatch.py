"""
Route incoming messages to the correct agent instance.

TODO: replace echo mode with real routing once Supabase is configured.
"""
import asyncio
import httpx
from feishu import send_message

# open_id -> asyncio.Queue for Mac mini long-poll delivery
_mac_queues: dict[str, asyncio.Queue] = {}


def register_mac_queue(open_id: str, queue: asyncio.Queue) -> None:
    _mac_queues[open_id] = queue


def unregister_mac_queue(open_id: str) -> None:
    _mac_queues.pop(open_id, None)


async def dispatch(open_id: str, text: str) -> None:
    # Echo mode: reply directly for testing
    # TODO: replace with real user/instance resolution via Supabase
    await send_message(open_id, f"[echo] {text}")
