"""
Orchestrator API — called by Supabase webhooks on user lifecycle events.
"""
import secrets
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from supabase import create_client
from containers import provision, deprovision
from config import settings

app = FastAPI(title="pi-matrix orchestrator", version="0.1.0")
supabase = create_client(settings.supabase_url, settings.supabase_service_key)


class UserEvent(BaseModel):
    type: str        # INSERT | DELETE
    record: dict     # Supabase row


def _auth(secret: str = Header(alias="x-webhook-secret")) -> None:
    if secret != settings.gateway_key:
        raise HTTPException(status_code=403)


@app.post("/webhook/user")
def on_user_event(event: UserEvent, _: None = Depends(_auth)):
    user_id = event.record.get("id")
    if not user_id:
        return {"ok": False, "reason": "no user_id"}

    if event.type == "INSERT":
        _provision_user(user_id)
    elif event.type == "DELETE":
        _deprovision_user(user_id)

    return {"ok": True}


def _provision_user(user_id: str) -> None:
    endpoint = provision(user_id)

    # Register device in Supabase
    device_token = secrets.token_urlsafe(32)
    supabase.table("pi_matrix_devices").upsert({
        "user_id": user_id,
        "name": "cloud-instance",
        "token": device_token,
        "instance_type": "cloud",
        "endpoint": f"{endpoint}/inbox",
    }, on_conflict="user_id,name").execute()


def _deprovision_user(user_id: str) -> None:
    deprovision(user_id)
    supabase.table("pi_matrix_devices").delete().eq("user_id", user_id).eq("name", "cloud-instance").execute()


@app.get("/health")
def health():
    return {"ok": True}
