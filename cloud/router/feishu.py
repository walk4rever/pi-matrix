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


def _feishu_markdown(text: str) -> str:
    """Convert unsupported markdown to Feishu card markdown."""
    import re
    # ### heading → **heading**
    text = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
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


def add_reaction(message_id: str, emoji: str = "Thinking") -> str | None:
    """Add an emoji reaction to a message. Returns reaction_id or None on failure."""
    req = CreateMessageReactionRequest.builder() \
        .message_id(message_id) \
        .request_body(
            CreateMessageReactionRequestBody.builder()
            .reaction_type(Emoji.builder().emoji_type(emoji).build())
            .build()
        ).build()
    resp = client.im.v1.message_reaction.create(req)
    if not resp.success():
        logger.error("add_reaction failed: code=%s msg=%s request_id=%s", resp.code, resp.msg, resp.request_id)
        return None
    logger.info("add_reaction ok: reaction_id=%s", resp.data.reaction_id if resp.data else None)
    return resp.data.reaction_id if resp.data else None


def remove_reaction(message_id: str, reaction_id: str) -> None:
    req = DeleteMessageReactionRequest.builder() \
        .message_id(message_id) \
        .reaction_id(reaction_id) \
        .build()
    resp = client.im.v1.message_reaction.delete(req)
    if not resp.success():
        logger.error("remove_reaction failed: code=%s msg=%s", resp.code, resp.msg)


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
