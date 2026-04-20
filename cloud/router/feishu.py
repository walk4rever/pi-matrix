import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
)
from config import settings

client = lark.Client.builder() \
    .app_id(settings.feishu_app_id) \
    .app_secret(settings.feishu_app_secret) \
    .build()


async def send_message(open_id: str, text: str) -> None:
    req = CreateMessageRequest.builder() \
        .receive_id_type("open_id") \
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("text")
            .content(f'{{"text":"{text}"}}')
            .build()
        ).build()
    client.im.v1.message.create(req)


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
