"""
Feishu account binding: links a user's Feishu open_id to their pi-matrix account.
Feishu Drive OAuth: lets users authorize the platform to upload large files to their Drive.
"""
import logging
import threading
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.db import supabase
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["feishu"])

_FEISHU_AUTHORIZE_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"
_FEISHU_APP_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
_FEISHU_USER_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/access_token"


class BindRequest(BaseModel):
    open_id: str


@router.post("/bind")
def bind_feishu(body: BindRequest, user: dict = Depends(get_current_user)):
    existing = supabase.table("pi_matrix_feishu_bindings") \
        .select("id").eq("open_id", body.open_id).maybe_single().execute()
    if existing and existing.data:
        raise HTTPException(status_code=409, detail="This Feishu account is already linked.")

    supabase.table("pi_matrix_feishu_bindings").insert({
        "user_id": user["sub"],
        "open_id": body.open_id,
    }).execute()

    threading.Thread(target=_provision, args=(user["sub"],), daemon=True).start()
    _welcome(body.open_id)
    return {"ok": True}


def _welcome(open_id: str) -> None:
    try:
        with httpx.Client(timeout=10) as client:
            client.post(
                f"{settings.platform_gateway_url}/internal/notify",
                data={"open_id": open_id, "text": "🎉 绑定成功！您的爱马仕员工正在准备中，稍后直接发消息开始对话。"},
                headers={"x-internal-secret": settings.gateway_key},
            )
    except Exception:
        pass  # non-critical


def _provision(user_id: str) -> None:
    try:
        with httpx.Client(timeout=30) as client:
            client.post(
                f"{settings.orchestrator_url}/webhook/user",
                json={"type": "INSERT", "record": {"id": user_id}},
                headers={"x-webhook-secret": settings.gateway_key},
            )
    except Exception:
        pass  # pre-provisioned at registration; this is a fallback


@router.get("/bind")
def get_binding(user: dict = Depends(get_current_user)):
    result = supabase.table("pi_matrix_feishu_bindings") \
        .select("open_id,created_at").eq("user_id", user["sub"]).maybe_single().execute()
    return result.data or {}


@router.delete("/bind")
def unbind_feishu(user: dict = Depends(get_current_user)):
    supabase.table("pi_matrix_feishu_bindings").delete().eq("user_id", user["sub"]).execute()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Feishu Drive OAuth
# ---------------------------------------------------------------------------

@router.get("/drive/auth-url")
def drive_auth_url(user: dict = Depends(get_current_user)):
    """Return the Feishu OAuth URL so the frontend can open it for Drive auth."""
    binding = supabase.table("pi_matrix_feishu_bindings") \
        .select("open_id").eq("user_id", user["sub"]).maybe_single().execute()
    if not binding or not binding.data:
        raise HTTPException(status_code=404, detail="Feishu account not linked.")
    open_id = binding.data["open_id"]
    url = _build_drive_oauth_url(open_id)
    return {"auth_url": url}


def _build_drive_oauth_url(open_id: str) -> str:
    params = {
        "app_id": settings.feishu_app_id,
        "redirect_uri": f"{settings.api_base_url}/feishu/drive/callback",
        "scope": "drive:drive",
        "state": open_id,
    }
    return f"{_FEISHU_AUTHORIZE_URL}?{urlencode(params)}"


@router.get("/drive/callback")
async def drive_callback(code: str, state: str):
    """OAuth callback: exchange code for user token, store in Supabase, notify user."""
    open_id = state
    try:
        async with httpx.AsyncClient(timeout=15) as hx:
            # 1. Get app access token
            app_resp = await hx.post(
                _FEISHU_APP_TOKEN_URL,
                json={"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret},
            )
            app_data = app_resp.json()
            app_access_token = app_data.get("app_access_token")
            if not app_access_token:
                raise ValueError(f"app_access_token missing: {app_data}")

            # 2. Exchange code for user access token
            user_resp = await hx.post(
                _FEISHU_USER_TOKEN_URL,
                headers={"Authorization": f"Bearer {app_access_token}"},
                json={"grant_type": "authorization_code", "code": code},
            )
            user_data = user_resp.json()
            data = user_data.get("data", {})
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token", "")
            expires_in = int(data.get("expires_in", 7200))
            if not access_token:
                raise ValueError(f"user access_token missing: {user_data}")
    except Exception as exc:
        logger.error("drive_callback token exchange failed open_id=%s: %s", open_id, exc)
        return HTMLResponse(
            "<h3>授权失败，请返回飞书重试。</h3>",
            status_code=400,
        )

    # 3. Look up user_id from open_id
    binding = supabase.table("pi_matrix_feishu_bindings") \
        .select("user_id").eq("open_id", open_id).maybe_single().execute()
    if not binding or not binding.data:
        return HTMLResponse(
            "<h3>账号未绑定，请先在 pi-matrix 完成注册。</h3>",
            status_code=400,
        )
    user_id = binding.data["user_id"]
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

    # 4. Upsert token into unified credential store
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        supabase.table("pi_matrix_user_credentials").upsert(
            [
                {
                    "user_id": user_id,
                    "provider": "feishu_drive",
                    "credential_key": "access_token",
                    "credential_value": access_token,
                    "external_id": open_id,
                    "updated_at": now_iso,
                },
                {
                    "user_id": user_id,
                    "provider": "feishu_drive",
                    "credential_key": "refresh_token",
                    "credential_value": refresh_token,
                    "external_id": open_id,
                    "updated_at": now_iso,
                },
                {
                    "user_id": user_id,
                    "provider": "feishu_drive",
                    "credential_key": "expires_at",
                    "credential_value": expires_at,
                    "external_id": open_id,
                    "updated_at": now_iso,
                },
            ],
            on_conflict="user_id,provider,credential_key",
        ).execute()
    except Exception:
        # Transitional fallback before DB migration is applied.
        supabase.table("pi_matrix_feishu_drive_tokens").upsert(
            {
                "user_id": user_id,
                "open_id": open_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "updated_at": now_iso,
            },
            on_conflict="user_id",
        ).execute()

    # 5. Notify user via Feishu
    threading.Thread(target=_notify_drive_auth_success, args=(open_id,), daemon=True).start()

    return HTMLResponse(
        "<h3>✅ 飞书云盘授权成功！</h3><p>您可以关闭此页面，返回飞书继续对话。</p>",
        status_code=200,
    )


def _notify_drive_auth_success(open_id: str) -> None:
    try:
        with httpx.Client(timeout=10) as hx:
            hx.post(
                f"{settings.platform_gateway_url}/internal/notify",
                data={"open_id": open_id, "text": "✅ 飞书云盘授权成功！当前版本仍以飞书消息附件回传为主，云盘自动上传通道正在接入中。"},
                headers={"x-internal-secret": settings.gateway_key},
            )
    except Exception:
        pass


@router.get("/drive/status")
def drive_status(user: dict = Depends(get_current_user)):
    """Check if the current user has a valid Drive token."""
    rows = []
    try:
        result = (
            supabase.table("pi_matrix_user_credentials")
            .select("credential_key,credential_value")
            .eq("user_id", user["sub"])
            .eq("provider", "feishu_drive")
            .in_("credential_key", ["access_token", "expires_at"])
            .execute()
        )
        rows = result.data if result and result.data else []
    except Exception:
        pass
    if not rows:
        # Transitional fallback before DB migration is applied.
        legacy = (
            supabase.table("pi_matrix_feishu_drive_tokens")
            .select("access_token,expires_at")
            .eq("user_id", user["sub"])
            .maybe_single()
            .execute()
        )
        if legacy and legacy.data:
            rows = [
                {"credential_key": "access_token", "credential_value": legacy.data.get("access_token")},
                {"credential_key": "expires_at", "credential_value": legacy.data.get("expires_at")},
            ]
    if not rows:
        return {"authorized": False}
    kv = {str(r.get("credential_key")): str(r.get("credential_value") or "") for r in rows}
    expires_at_str = kv.get("expires_at", "")
    access_token = kv.get("access_token", "")
    if not access_token or not expires_at_str:
        return {"authorized": False}
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        authorized = datetime.now(timezone.utc) < expires_at
    except Exception:
        authorized = False
    return {"authorized": authorized, "expires_at": expires_at_str}
