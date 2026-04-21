"""
Thin HTTP wrapper around hermes AIAgent.
Calls our LiteLLM Gateway — no direct LLM API keys needed in this container.

Uses Hermes native session persistence (SessionDB) keyed by Feishu open_id.
"""
import asyncio
import logging
import os
from pathlib import Path
import httpx
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from hermes_state import SessionDB
from run_agent import AIAgent

logger = logging.getLogger(__name__)
app = FastAPI()

ROUTER_REPLY_URL = os.environ["ROUTER_REPLY_URL"]
GATEWAY_URL      = os.environ["GATEWAY_URL"]       # http://gateway:4000/v1
GATEWAY_KEY      = os.environ["GATEWAY_KEY"]       # litellm master key
HERMES_MODEL     = os.environ.get("HERMES_MODEL", "default")
HERMES_STATE_DB_PATH = Path(os.environ.get("HERMES_STATE_DB_PATH", "/root/.hermes/state/state.db"))

session_db = SessionDB(db_path=HERMES_STATE_DB_PATH)
_session_locks: dict[str, asyncio.Lock] = {}
_session_locks_guard = asyncio.Lock()


def _session_id_from_open_id(open_id: str) -> str:
    return f"feishu:{open_id}"


async def _get_session_lock(session_id: str) -> asyncio.Lock:
    async with _session_locks_guard:
        lock = _session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _session_locks[session_id] = lock
        return lock


def _run_turn(session_id: str, user_id: str, text: str) -> str:
    # Gateway pattern: fresh agent per turn + replay persisted conversation.
    agent = AIAgent(
        model=HERMES_MODEL,
        base_url=GATEWAY_URL,
        api_key=GATEWAY_KEY,
        session_id=session_id,
        session_db=session_db,
        platform="feishu",
        user_id=user_id,
        persist_session=True,
    )
    history = session_db.get_messages_as_conversation(session_id)
    result = agent.run_conversation(text, conversation_history=history)
    return result["final_response"] if isinstance(result, dict) else str(result)


class InboxMessage(BaseModel):
    open_id: str
    text: str
    message_id: str | None = None
    reaction_id: str | None = None


async def _process(msg: InboxMessage) -> None:
    session_id = _session_id_from_open_id(msg.open_id)
    session_lock = await _get_session_lock(session_id)
    try:
        async with session_lock:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, _run_turn, session_id, msg.open_id, msg.text)
        payload: dict = {"open_id": msg.open_id, "text": text}
        if msg.message_id:
            payload["message_id"] = msg.message_id
        if msg.reaction_id:
            payload["reaction_id"] = msg.reaction_id
        async with httpx.AsyncClient(timeout=60) as client:
            await client.post(ROUTER_REPLY_URL, json=payload)
    except Exception:
        logger.exception("_process failed for open_id=%s session_id=%s", msg.open_id, session_id)


@app.post("/inbox")
async def inbox(msg: InboxMessage, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process, msg)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
