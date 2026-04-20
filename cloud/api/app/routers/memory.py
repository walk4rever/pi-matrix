from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user, get_device
from app.db import supabase

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryItem(BaseModel):
    content: str
    device_id: str | None = None


@router.post("/")
def add_memory(body: MemoryItem, token: str = Depends(get_device)):
    device = supabase.table("pi_matrix_devices").select("user_id,id").eq("token", token).single().execute()
    supabase.table("pi_matrix_memories").insert({
        "user_id": device.data["user_id"],
        "device_id": device.data["id"],
        "content": body.content,
    }).execute()
    return {"ok": True}


@router.get("/")
def list_memories(user: dict = Depends(get_current_user)):
    result = supabase.table("pi_matrix_memories").select("*").eq("user_id", user["sub"]).order("created_at", desc=True).limit(100).execute()
    return result.data


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, user: dict = Depends(get_current_user)):
    supabase.table("pi_matrix_memories").delete().eq("id", memory_id).eq("user_id", user["sub"]).execute()
    return {"ok": True}
