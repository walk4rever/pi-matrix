import json
import logging
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
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
