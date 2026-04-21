"""
pi-matrix router: receives Feishu events via long connection (WebSocket),
dispatches to correct user agent instance, relays replies back to Feishu.
"""
import asyncio
import json
import lark_oapi as lark
from fastapi import FastAPI, Request, HTTPException
from feishu import send_message, build_ws_client, add_reaction, remove_reaction
from dispatch import dispatch

app = FastAPI(title="pi-matrix router", version="0.1.0")


def _on_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """Called by Feishu SDK on each incoming message."""
    sender_open_id = data.event.sender.sender_id.open_id
    message = data.event.message
    if message.message_type != "text":
        return
    content = json.loads(message.content)
    text = content.get("text", "").strip()
    if not text or not sender_open_id:
        return
    message_id = message.message_id
    reaction_id = add_reaction(message_id)
    asyncio.get_event_loop().create_task(
        dispatch(sender_open_id, text, message_id=message_id, reaction_id=reaction_id)
    )


@app.on_event("startup")
async def start_feishu_ws():
    """Start Feishu long connection as a task in FastAPI's event loop."""
    ws_client = build_ws_client(_on_message)
    asyncio.create_task(ws_client._connect())


@app.post("/reply")
async def agent_reply(request: Request):
    """Agent instances POST their reply here; router sends it back to Feishu."""
    body = await request.json()
    open_id = body.get("open_id")
    text = body.get("text")
    if not open_id or not text:
        raise HTTPException(status_code=400, detail="open_id and text required")
    message_id = body.get("message_id")
    reaction_id = body.get("reaction_id")
    if message_id and reaction_id:
        remove_reaction(message_id, reaction_id)
    await send_message(open_id, text)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
