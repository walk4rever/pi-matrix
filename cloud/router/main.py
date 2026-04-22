"""
pi-matrix router: receives Feishu events via long connection (WebSocket),
dispatches to correct user agent instance, relays replies back to Feishu.
"""
import asyncio
import base64
import json
import lark_oapi as lark
from fastapi import FastAPI, Request, HTTPException
from feishu import (
    add_reaction,
    build_ws_client,
    download_message_resource,
    remove_reaction,
    send_file,
    send_message,
)
from dispatch import dispatch

app = FastAPI(title="pi-matrix router", version="0.1.0")


def _on_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """Called by Feishu SDK on each incoming message."""
    sender_open_id = data.event.sender.sender_id.open_id
    message = data.event.message
    if not sender_open_id:
        return

    message_type = message.message_type
    content = json.loads(message.content or "{}")
    message_id = message.message_id
    reaction_id = add_reaction(message_id)

    text = ""
    if message_type == "text":
        text = str(content.get("text", "")).strip()

    attachments: list[dict] = []
    resource_refs: list[tuple[str, str]] = []

    image_key = content.get("image_key")
    if image_key:
        resource_refs.append(("image", str(image_key)))

    file_key = content.get("file_key")
    if file_key:
        resource_kind = message_type if message_type in {"audio", "media", "video"} else "file"
        resource_refs.append((resource_kind, str(file_key)))

    seen_refs: set[tuple[str, str]] = set()
    for resource_type, key in resource_refs:
        ref = (resource_type, key)
        if ref in seen_refs:
            continue
        seen_refs.add(ref)
        downloaded = download_message_resource(message_id, key, resource_type)
        if downloaded is None:
            continue
        file_name, file_bytes = downloaded
        attachments.append(
            {
                "name": file_name,
                "message_type": resource_type,
                "feishu_file_key": key,
                "content_b64": base64.b64encode(file_bytes).decode("ascii"),
            }
        )

    if not text and attachments:
        text = f"用户发送了 {message_type} 消息，请结合附件处理。"
    elif not text:
        text = f"用户发送了 {message_type} 消息，原始内容如下：{json.dumps(content, ensure_ascii=False)}"

    asyncio.get_event_loop().create_task(
        dispatch(
            sender_open_id,
            text,
            attachments=attachments or None,
            message_type=message_type,
            raw_content=content,
            message_id=message_id,
            reaction_id=reaction_id,
        )
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
    files = body.get("files") or []
    if not open_id or (not text and not files):
        raise HTTPException(status_code=400, detail="open_id and at least one of text/files required")

    message_id = body.get("message_id")
    reaction_id = body.get("reaction_id")
    if message_id and reaction_id:
        remove_reaction(message_id, reaction_id)

    if text:
        await send_message(open_id, text)

    for item in files:
        if not isinstance(item, dict):
            continue
        file_name = item.get("name") or "artifact.bin"
        content_b64 = item.get("content_b64")
        if not content_b64:
            continue
        try:
            content = base64.b64decode(content_b64)
        except Exception:
            continue
        await send_file(open_id, file_name, content)

    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}
