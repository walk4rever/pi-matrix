import io
import json
import logging
import httpx
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateFileRequest,
    CreateFileRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageReactionRequest,
    CreateMessageReactionRequestBody,
    DeleteMessageReactionRequest,
    Emoji,
    GetMessageResourceRequest,
    P2ImMessageReceiveV1,
)
from config import settings

logger = logging.getLogger(__name__)

client = lark.Client.builder() \
    .app_id(settings.feishu_app_id) \
    .app_secret(settings.feishu_app_secret) \
    .build()


def _parse_table_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return [c for c in cells if c != ""]


def _normalize_markdown(text: str) -> str:
    """Convert unsupported markdown to Feishu card markdown."""
    import re
    # ### heading → **heading**
    return re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)


def _build_card_elements(text: str) -> list[dict]:
    """Render markdown tables as Feishu Card JSON 2.0 table components."""
    import re

    sep_re = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
    lines = text.splitlines()
    elements: list[dict] = []
    pending_text: list[str] = []
    i = 0

    def flush_text() -> None:
        nonlocal pending_text
        content = _normalize_markdown("\n".join(pending_text)).strip()
        if content:
            elements.append({"tag": "markdown", "content": content})
        pending_text = []

    while i < len(lines):
        if i + 1 < len(lines) and "|" in lines[i] and sep_re.match(lines[i + 1] or ""):
            headers = _parse_table_row(lines[i])
            if not headers:
                pending_text.append(lines[i])
                i += 1
                continue

            flush_text()
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i]:
                row = _parse_table_row(lines[i])
                if row:
                    rows.append(row)
                i += 1

            if not headers or not rows:
                continue

            columns = [
                {
                    "name": f"col_{idx}",
                    "display_name": header or f"列{idx+1}",
                    "data_type": "lark_md",
                    "width": "auto",
                }
                for idx, header in enumerate(headers)
            ]

            table_rows = []
            for row in rows:
                item = {}
                for idx in range(len(headers)):
                    key = f"col_{idx}"
                    item[key] = row[idx] if idx < len(row) and row[idx] else "-"
                table_rows.append(item)

            elements.append(
                {
                    "tag": "table",
                    "row_height": "auto",
                    "columns": columns,
                    "rows": table_rows,
                }
            )
            continue

        pending_text.append(lines[i])
        i += 1

    flush_text()
    if not elements:
        elements.append({"tag": "markdown", "content": _normalize_markdown(text)})
    return elements


async def send_message(open_id: str, text: str) -> None:
    card = {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "body": {
            "elements": _build_card_elements(text),
        },
    }
    req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("interactive")
            .content(json.dumps(card))
            .build()
        ).build()
    resp = client.im.v1.message.create(req)
    if not resp.success():
        logger.error("send_message failed: code=%s msg=%s", resp.code, resp.msg)


_FEISHU_FILE_SIZE_LIMIT = 30 * 1024 * 1024  # 30 MB


async def send_file(open_id: str, file_name: str, content: bytes) -> None:
    if len(content) > _FEISHU_FILE_SIZE_LIMIT:
        size_mb = len(content) / 1024 / 1024
        await send_message(open_id, f"文件 **{file_name}** 大小 {size_mb:.1f} MB，超过飞书 30 MB 限制，无法直接发送。文件已保存在员工工作区，可通过指令下载或压缩后重新发送。")
        return

    upload_req = CreateFileRequest.builder().request_body(
        CreateFileRequestBody.builder()
        .file_type("stream")
        .file_name(file_name)
        .file(io.BytesIO(content))
        .build()
    ).build()
    try:
        upload_resp = client.im.v1.file.create(upload_req)
    except Exception:
        logger.exception("send_file upload exception for %s", file_name)
        await send_message(open_id, f"文件 **{file_name}** 上传失败，文件已保存在员工工作区。")
        return
    if not upload_resp.success() or not upload_resp.data or not upload_resp.data.file_key:
        logger.error("send_file upload failed: code=%s msg=%s", upload_resp.code, upload_resp.msg)
        await send_message(open_id, f"文件 **{file_name}** 上传失败（code={upload_resp.code}），文件已保存在员工工作区。")
        return

    file_key = upload_resp.data.file_key
    send_req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("file")
            .content(json.dumps({"file_key": file_key}))
            .build()
        ).build()
    send_resp = client.im.v1.message.create(send_req)
    if not send_resp.success():
        logger.error("send_file message failed: code=%s msg=%s", send_resp.code, send_resp.msg)


def download_message_resource(message_id: str, file_key: str, resource_type: str) -> tuple[str, bytes] | None:
    req = GetMessageResourceRequest.builder() \
        .message_id(message_id) \
        .file_key(file_key) \
        .type(resource_type) \
        .build()
    resp = client.im.v1.message_resource.get(req)
    if not resp.success() or not resp.file:
        logger.error(
            "download_message_resource failed: type=%s code=%s msg=%s",
            resource_type,
            resp.code,
            resp.msg,
        )
        return None

    try:
        content = resp.file.read()
        file_name = resp.file_name or f"{resource_type}_{file_key}"
        return file_name, content
    except Exception:
        logger.exception("download_message_resource read failed")
        return None


def add_reaction(message_id: str, emoji: str = "THUMBSUP") -> str | None:
    """Add an emoji reaction to a message. Returns reaction_id or None on failure."""
    try:
        req = CreateMessageReactionRequest.builder() \
            .message_id(message_id) \
            .request_body(
                CreateMessageReactionRequestBody.builder()
                .reaction_type(Emoji.builder().emoji_type(emoji).build())
                .build()
            ).build()
        resp = client.im.v1.message_reaction.create(req)
        if not resp.success():
            logger.error("add_reaction failed: code=%s msg=%s", resp.code, resp.msg)
            return None
        return resp.data.reaction_id if resp.data else None
    except Exception:
        logger.exception("add_reaction exception")
        return None


def remove_reaction(message_id: str, reaction_id: str) -> None:
    try:
        req = DeleteMessageReactionRequest.builder() \
            .message_id(message_id) \
            .reaction_id(reaction_id) \
            .build()
        resp = client.im.v1.message_reaction.delete(req)
        if not resp.success():
            logger.error("remove_reaction failed: code=%s msg=%s", resp.code, resp.msg)
    except Exception:
        logger.exception("remove_reaction exception")


async def send_registration_card(open_id: str, register_url: str) -> None:
    card = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "markdown",
                "content": "👋 欢迎使用 **pi-matrix**\n\n您的专属爱马仕员工正在等待，注册后即刻上线。"
            },
            {
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "立即注册 →"},
                    "type": "primary",
                    "url": register_url,
                }]
            }
        ]
    }
    req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("interactive")
            .content(json.dumps(card))
            .build()
        ).build()
    resp = client.im.v1.message.create(req)
    if not resp.success():
        logger.error("send_registration_card failed: code=%s msg=%s", resp.code, resp.msg)


async def send_drive_auth_card(open_id: str, file_name: str, auth_url: str) -> None:
    """Send a Feishu card prompting the user to authorize Drive access."""
    card = {
        "config": {"wide_screen_mode": True},
        "elements": [
            {
                "tag": "markdown",
                "content": (
                    f"文件 **{file_name}** 超过飞书消息 30 MB 限制，需上传到飞书云盘。\n\n"
                    "请点击下方按钮授权，授权后文件将自动上传并发送给您。"
                ),
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "授权飞书云盘 →"},
                        "type": "primary",
                        "url": auth_url,
                    }
                ],
            },
        ],
    }
    req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("interactive")
            .content(json.dumps(card))
            .build()
        ).build()
    resp = client.im.v1.message.create(req)
    if not resp.success():
        logger.error("send_drive_auth_card failed: code=%s msg=%s", resp.code, resp.msg)


_FEISHU_DRIVE_ROOT_META = "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta"
_FEISHU_DRIVE_UPLOAD_ALL = "https://open.feishu.cn/open-apis/drive/v1/files/upload_all"
_FEISHU_DRIVE_PERMISSION = "https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/public"


async def upload_to_user_drive(
    user_access_token: str,
    file_name: str,
    content: bytes,
) -> str | None:
    """Upload content to user's Feishu Drive My Space. Returns share URL or None."""
    headers = {"Authorization": f"Bearer {user_access_token}"}
    async with httpx.AsyncClient(timeout=120) as hx:
        # 1. Get root folder token for My Space
        root_resp = await hx.get(_FEISHU_DRIVE_ROOT_META, headers=headers)
        root_data = root_resp.json()
        if root_data.get("code") != 0:
            logger.error("upload_to_user_drive get_root failed: %s", root_data)
            return None
        root_token = root_data.get("data", {}).get("token", "")

        # 2. Upload file to root of My Space
        upload_resp = await hx.post(
            _FEISHU_DRIVE_UPLOAD_ALL,
            headers=headers,
            data={
                "file_name": file_name,
                "parent_type": "explorer",
                "parent_node": root_token,
                "size": str(len(content)),
            },
            files={"file": (file_name, io.BytesIO(content), "application/octet-stream")},
        )
        upload_data = upload_resp.json()
        if upload_data.get("code") != 0:
            logger.error("upload_to_user_drive upload failed: %s", upload_data)
            return None
        file_token = upload_data.get("data", {}).get("file_token")
        if not file_token:
            logger.error("upload_to_user_drive: no file_token in response: %s", upload_data)
            return None

        # 3. Enable tenant-readable link sharing
        perm_resp = await hx.patch(
            _FEISHU_DRIVE_PERMISSION.format(token=file_token),
            headers=headers,
            params={"type": "file"},
            json={"link_share_entity": "tenant_readable"},
        )
        perm_data = perm_resp.json()
        if perm_data.get("code") != 0:
            logger.warning("upload_to_user_drive set_permission failed: %s", perm_data)

        return f"https://feishu.cn/file/{file_token}"


def build_ws_client(on_message) -> lark.ws.Client:
    handler = lark.EventDispatcherHandler.builder(
        settings.feishu_encrypt_key,
        settings.feishu_verification_token,
    ).register_p2_im_message_receive_v1(on_message).build()

    return lark.ws.Client(
        settings.feishu_app_id,
        settings.feishu_app_secret,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )
