"""
pi-matrix router: receives Feishu events via long connection (WebSocket),
dispatches to correct user agent instance, relays replies back to Feishu.
"""
import asyncio
import threading
import lark_oapi as lark
from fastapi import FastAPI, Request, HTTPException
from feishu import send_message, build_ws_client
from dispatch import dispatch

app = FastAPI(title="pi-matrix router", version="0.1.0")


def _on_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """Called by Feishu SDK on each incoming message (runs in SDK thread)."""
    import json
    sender_open_id = data.event.sender.sender_id.open_id
    message = data.event.message
    if message.message_type != "text":
        return
    content = json.loads(message.content)
    text = content.get("text", "").strip()
    if text and sender_open_id:
        asyncio.run(dispatch(sender_open_id, text))


@app.on_event("startup")
def start_feishu_ws():
    """Start Feishu long connection in a background thread on startup."""
    ws_client = build_ws_client(_on_message)

    def run():
        ws_client.start()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


@app.post("/reply")
async def agent_reply(request: Request):
    """Agent instances POST their reply here; router sends it back to Feishu."""
    body = await request.json()
    open_id = body.get("open_id")
    text = body.get("text")
    if not open_id or not text:
        raise HTTPException(status_code=400, detail="open_id and text required")
    await send_message(open_id, text)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
