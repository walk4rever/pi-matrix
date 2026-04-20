from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from app.middleware.auth import get_current_user, get_device
from app.db import supabase

router = APIRouter(prefix="/devices", tags=["devices"])


class RegisterDevice(BaseModel):
    name: str


class DeviceHeartbeat(BaseModel):
    version: str


@router.post("/")
def register_device(body: RegisterDevice, user: dict = Depends(get_current_user)):
    import secrets
    token = secrets.token_urlsafe(32)
    result = supabase.table("pi_matrix_devices").insert({
        "user_id": user["sub"],
        "name": body.name,
        "token": token,
    }).execute()
    return {"device": result.data[0], "token": token}


@router.get("/")
def list_devices(user: dict = Depends(get_current_user)):
    result = supabase.table("pi_matrix_devices").select("*").eq("user_id", user["sub"]).execute()
    return result.data


@router.post("/heartbeat")
def heartbeat(body: DeviceHeartbeat, token: str = Depends(get_device)):
    result = supabase.table("pi_matrix_devices").update({
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "version": body.version,
    }).eq("token", token).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Unknown device token")
    return {"ok": True}
