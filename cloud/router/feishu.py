import json
import logging
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageReactionRequest,
    CreateMessageReactionRequestBody,
    DeleteMessageReactionRequest,
    Emoji,
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


def _convert_markdown_tables(text: str) -> str:
    """Convert markdown tables to Feishu-friendly bullet lists."""
    import re

    sep_re = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
    lines = text.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        if (
            i + 1 < len(lines)
            and "|" in lines[i]
            and sep_re.match(lines[i + 1] or "")
        ):
            headers = _parse_table_row(lines[i])
            if not headers:
                out.append(lines[i])
                i += 1
                continue

            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i]:
                row = _parse_table_row(lines[i])
                if row:
                    rows.append(row)
                i += 1

            for row in rows:
                first_header = headers[0]
                first_value = row[0] if len(row) > 0 else ""
                out.append(f"- **{first_header}**：{first_value}")
                for col in range(1, min(len(headers), len(row))):
                    out.append(f"  - {headers[col]}：{row[col]}")
            continue

        out.append(lines[i])
        i += 1

    return "\n".join(out)


def _feishu_markdown(text: str) -> str:
    """Convert unsupported markdown to Feishu card markdown."""
    import re
    # ### heading → **heading**
    text = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
    # Markdown table → list (Feishu markdown has weak table support)
    text = _convert_markdown_tables(text)
    return text


async def send_message(open_id: str, text: str) -> None:
    card = {
        "elements": [{"tag": "markdown", "content": _feishu_markdown(text)}]
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
