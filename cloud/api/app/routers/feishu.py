"""
Feishu account binding: links a user's Feishu open_id to their pi-matrix account.
User initiates from dashboard after logging in.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.db import supabase

router = APIRouter(prefix="/feishu", tags=["feishu"])


class BindRequest(BaseModel):
    open_id: str


@router.post("/bind")
def bind_feishu(body: BindRequest, user: dict = Depends(get_current_user)):
    existing = supabase.table("pi_matrix_feishu_bindings") \
        .select("id").eq("open_id", body.open_id).maybe_single().execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="This Feishu account is already linked.")

    supabase.table("pi_matrix_feishu_bindings").insert({
        "user_id": user["sub"],
        "open_id": body.open_id,
    }).execute()
    return {"ok": True}


@router.get("/bind")
def get_binding(user: dict = Depends(get_current_user)):
    result = supabase.table("pi_matrix_feishu_bindings") \
        .select("open_id,created_at").eq("user_id", user["sub"]).maybe_single().execute()
    return result.data or {}


@router.delete("/bind")
def unbind_feishu(user: dict = Depends(get_current_user)):
    supabase.table("pi_matrix_feishu_bindings").delete().eq("user_id", user["sub"]).execute()
    return {"ok": True}
