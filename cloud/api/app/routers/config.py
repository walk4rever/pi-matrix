from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user, get_device
from app.db import supabase

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdate(BaseModel):
    platform: str | None = None
    config: dict | None = None


@router.get("/")
def get_config(user: dict = Depends(get_current_user)):
    result = supabase.table("pi_matrix_user_configs").select("*").eq("user_id", user["sub"]).maybe_single().execute()
    return result.data or {}


@router.put("/")
def update_config(body: ConfigUpdate, user: dict = Depends(get_current_user)):
    existing = supabase.table("pi_matrix_user_configs").select("id").eq("user_id", user["sub"]).maybe_single().execute()
    data = {"user_id": user["sub"], **body.model_dump(exclude_none=True)}
    if existing.data:
        supabase.table("pi_matrix_user_configs").update(data).eq("user_id", user["sub"]).execute()
    else:
        supabase.table("pi_matrix_user_configs").insert(data).execute()
    return {"ok": True}


@router.get("/device")
def get_config_for_device(token: str = Depends(get_device)):
    """Device pulls its config on startup or after OTA update."""
    device = supabase.table("pi_matrix_devices").select("user_id").eq("token", token).single().execute()
    result = supabase.table("pi_matrix_user_configs").select("*").eq("user_id", device.data["user_id"]).maybe_single().execute()
    return result.data or {}
