"""
File delivery to Feishu via lark_oapi.
Text delivery goes through FeishuAdapter; this module handles file/media
attachments only until FeishuAdapter exposes a clean file-send API.
"""
from __future__ import annotations

import io
import json
import logging
from urllib.parse import urlencode

import httpx
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateFileRequest,
    CreateFileRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
)

logger = logging.getLogger(__name__)

_FEISHU_FILE_LIMIT = 30 * 1024 * 1024  # 30 MB
_FEISHU_DRIVE_ROOT_META = "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta"
_FEISHU_DRIVE_UPLOAD_ALL = "https://open.feishu.cn/open-apis/drive/v1/files/upload_all"
_FEISHU_DRIVE_PERMISSION = "https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/public"
_FEISHU_AUTHORIZE_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"


class FeishuDelivery:
    def __init__(self, app_id: str, app_secret: str):
        self._app_id = app_id
        self._client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()

    async def send_text(self, open_id: str, text: str) -> None:
        req = CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(open_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()
            ).build()
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            logger.error("send text failed code=%s msg=%s", resp.code, resp.msg)

    async def send_file(self, open_id: str, file_name: str, content: bytes) -> None:
        if len(content) > _FEISHU_FILE_LIMIT:
            mb = len(content) / 1024 / 1024
            logger.warning("file %s too large (%.1f MB)", file_name, mb)
            # We intentionally do NOT send a chat message here; caller handles UX.
            return

        upload_req = CreateFileRequest.builder().request_body(
            CreateFileRequestBody.builder()
            .file_type("stream")
            .file_name(file_name)
            .file(io.BytesIO(content))
            .build()
        ).build()
        try:
            upload_resp = self._client.im.v1.file.create(upload_req)
        except Exception:
            logger.exception("upload failed %s", file_name)
            return
        if not upload_resp.success() or not upload_resp.data or not upload_resp.data.file_key:
            logger.error("upload failed code=%s msg=%s", upload_resp.code, upload_resp.msg)
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
        send_resp = self._client.im.v1.message.create(send_req)
        if not send_resp.success():
            logger.error("send file msg failed code=%s msg=%s", send_resp.code, send_resp.msg)

    async def send_registration_card(self, open_id: str, register_url: str) -> None:
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "markdown",
                    "content": "👋 欢迎使用 **pi-matrix**\n\n您的专属爱马仕员工正在等待，注册后即可开始对话。"
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
        await self._send_card(open_id, card, "send registration card")

    def build_drive_auth_url(self, api_base_url: str, open_id: str) -> str:
        params = {
            "app_id": self._app_id,
            "redirect_uri": f"{api_base_url}/feishu/drive/callback",
            "scope": "drive:drive",
            "state": open_id,
        }
        return f"{_FEISHU_AUTHORIZE_URL}?{urlencode(params)}"

    async def send_drive_auth_card(self, open_id: str, file_name: str, auth_url: str) -> None:
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "markdown",
                    "content": (
                        f"文件 **{file_name}** 超过飞书消息附件限制。\n\n"
                        "请点击下方按钮授权飞书云盘，授权后请重新发送上条请求，系统将改为云盘链接回传。"
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
        await self._send_card(open_id, card, "send drive auth card")

    async def upload_to_user_drive(
        self,
        user_access_token: str,
        file_name: str,
        content: bytes,
    ) -> str | None:
        headers = {"Authorization": f"Bearer {user_access_token}"}
        async with httpx.AsyncClient(timeout=120) as hx:
            root_resp = await hx.get(_FEISHU_DRIVE_ROOT_META, headers=headers)
            root_data = root_resp.json()
            if root_data.get("code") != 0:
                logger.error("get drive root failed: %s", root_data)
                return None
            root_token = root_data.get("data", {}).get("token", "")

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
                logger.error("drive upload failed: %s", upload_data)
                return None
            file_token = upload_data.get("data", {}).get("file_token")
            if not file_token:
                logger.error("drive upload missing file_token: %s", upload_data)
                return None

            perm_resp = await hx.patch(
                _FEISHU_DRIVE_PERMISSION.format(token=file_token),
                headers=headers,
                params={"type": "file"},
                json={"link_share_entity": "tenant_readable"},
            )
            perm_data = perm_resp.json()
            if perm_data.get("code") != 0:
                logger.warning("set drive permission failed: %s", perm_data)

            return f"https://feishu.cn/file/{file_token}"

    async def _send_card(self, open_id: str, card: dict, op: str) -> None:
        req = CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(open_id)
                .msg_type("interactive")
                .content(json.dumps(card))
                .build()
            ).build()
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            logger.error("%s failed code=%s msg=%s", op, resp.code, resp.msg)
