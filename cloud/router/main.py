import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from feishu import verify_token, send_message
from dispatch import dispatch, register_mac_queue, unregister_mac_queue

app = FastAPI(title="pi-matrix router", version="0.1.0")


@app.post("/webhook/feishu")
async def feishu_webhook(request: Request):
    body = await request.json()

    # URL verification challenge (Feishu sends this when you first configure webhook)
    if body.get("type") == "url_verification":
        token = body.get("token", "")
        if not verify_token(token):
            raise HTTPException(status_code=403, detail="Invalid token")
        return {"challenge": body["challenge"]}

    # Event callback
    header = body.get("header", {})
    event_type = header.get("event_type", "")

    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
        sender_open_id = event.get("sender", {}).get("sender_id", {}).get("open_id")
        message = event.get("message", {})
        msg_type = message.get("message_type")

        if msg_type == "text" and sender_open_id:
            import json
            content = json.loads(message.get("content", "{}"))
            text = content.get("text", "").strip()
            if text:
                asyncio.create_task(dispatch(sender_open_id, text))

    return {"ok": True}


@app.get("/poll/{open_id}")
async def mac_poll(open_id: str):
    """Mac mini long-polls this endpoint to receive messages."""
    queue: asyncio.Queue = asyncio.Queue()
    register_mac_queue(open_id, queue)

    async def event_stream():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield "data: ping\n\n"
        finally:
            unregister_mac_queue(open_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
