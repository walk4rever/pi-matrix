"""
pi-matrix router: receives normalized inbound events from platform Hermes
Gateway wrapper, routes to the correct user agent instance, and relays
replies back to Feishu.
"""
import base64
from urllib.parse import urlencode
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
from config import settings
from feishu import remove_reaction, send_drive_auth_card, send_file, send_message, upload_to_user_drive
from dispatch import dispatch, get_drive_token

app = FastAPI(title="pi-matrix router", version="0.1.0")


class HermesIngressEvent(BaseModel):
    """Normalized inbound event produced by platform Hermes Gateway."""
    open_id: str
    text: str = ""
    message_type: str | None = None
    raw_content: dict | None = None
    attachments: list[dict] | None = None
    message_id: str | None = None
    reaction_id: str | None = None


def _verify_ingress_secret(secret: str | None) -> None:
    required = settings.hermes_ingress_secret.strip()
    if not required:
        return
    if secret != required:
        raise HTTPException(status_code=403, detail="invalid ingress secret")


@app.post("/ingress/hermes-event")
async def ingest_hermes_event(
    event: HermesIngressEvent,
    x_ingress_secret: str | None = Header(default=None, alias="x-ingress-secret"),
):
    """Primary inbound path: platform Hermes Gateway posts normalized events."""
    _verify_ingress_secret(x_ingress_secret)
    await dispatch(
        event.open_id,
        event.text,
        attachments=event.attachments,
        message_type=event.message_type,
        raw_content=event.raw_content,
        message_id=event.message_id,
        reaction_id=event.reaction_id,
    )
    return {"ok": True}


@app.post("/reply")
async def agent_reply(request: Request):
    """Agent instances POST their reply here; router sends it back to Feishu."""
    body = await request.json()
    open_id = body.get("open_id")
    text = body.get("text")
    files = body.get("files") or []
    drive_files_raw = body.get("drive_files") or []
    if not open_id or (not text and not files and not drive_files_raw):
        raise HTTPException(status_code=400, detail="open_id and at least one of text/files/drive_files required")

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

    if drive_files_raw:
        await _handle_drive_files(open_id, drive_files_raw)

    return {"ok": True}


def _build_drive_auth_url(open_id: str) -> str:
    params = {
        "app_id": settings.feishu_app_id,
        "redirect_uri": f"{settings.api_base_url}/feishu/drive/callback",
        "scope": "drive:drive",
        "state": open_id,
    }
    return f"https://open.feishu.cn/open-apis/authen/v1/authorize?{urlencode(params)}"


async def _handle_drive_files(open_id: str, drive_files: list) -> None:
    for item in drive_files:
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

        token_row = get_drive_token(open_id)
        if not token_row:
            await send_drive_auth_card(open_id, file_name, _build_drive_auth_url(open_id))
            continue

        share_url = await upload_to_user_drive(token_row["access_token"], file_name, content)
        if share_url:
            await send_message(open_id, f"文件 **{file_name}** 已上传到您的飞书云盘：[点击查看]({share_url})")
        else:
            await send_message(open_id, f"文件 **{file_name}** 上传到云盘失败，文件已保存在员工工作区。")


@app.get("/health")
def health():
    return {"ok": True}
