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
                    "row_max_height": "220px",
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
