"""
Feishu webhook verification and API helpers.
"""
import hashlib
import hmac
import httpx
from config import settings

FEISHU_API = "https://open.feishu.cn/open-apis"

_tenant_token: str | None = None


async def get_tenant_token() -> str:
    global _tenant_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
        )
        resp.raise_for_status()
        _tenant_token = resp.json()["tenant_access_token"]
    return _tenant_token


def verify_token(token: str) -> bool:
    return token == settings.feishu_verification_token


async def send_message(open_id: str, text: str) -> None:
    token = await get_tenant_token()
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{FEISHU_API}/im/v1/messages?receive_id_type=open_id",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": open_id,
                "msg_type": "text",
                "content": f'{{"text": "{text}"}}',
            },
        )
