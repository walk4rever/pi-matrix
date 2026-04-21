"""
Feishu account binding: links a user's Feishu open_id to their pi-matrix account.
User initiates from dashboard after logging in.
"""
import threading
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.db import supabase
from app.config import settings

router = APIRouter(prefix="/feishu", tags=["feishu"])


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
                f"{settings.router_reply_url}",
                json={"open_id": open_id, "text": "🎉 绑定成功！您的爱马仕员工正在准备中，稍后直接发消息开始对话。"},
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
