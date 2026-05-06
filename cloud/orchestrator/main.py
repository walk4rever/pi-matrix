"""
Orchestrator API — called by Supabase webhooks on user lifecycle events.
"""
import secrets
from datetime import UTC, datetime
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from supabase import create_client
from containers import provision, deprovision, rollback, upgrade
from config import settings

app = FastAPI(title="pi-matrix orchestrator", version="0.1.0")
supabase = create_client(settings.supabase_url, settings.supabase_service_key)


class UserEvent(BaseModel):
    type: str        # INSERT | DELETE
    record: dict     # Supabase row


class UpgradeRequest(BaseModel):
    image: str | None = None
    hermes_version: str | None = None
    user_ids: list[str] | None = None
    backup: bool = True
    dry_run: bool = False


class RollbackRequest(BaseModel):
    image: str | None = None


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
        "endpoint": endpoint,
        "version": settings.hermes_version,
        "hermes_version": settings.hermes_version,
        "executor_image": settings.executor_image,
    }, on_conflict="user_id,name").execute()


def _deprovision_user(user_id: str) -> None:
    deprovision(user_id)
    supabase.table("pi_matrix_devices").delete().eq("user_id", user_id).eq("name", "cloud-instance").execute()


@app.post("/users/{user_id}/upgrade")
def upgrade_user(user_id: str, req: UpgradeRequest, _: None = Depends(_auth)):
    target_image = req.image or settings.executor_image
    target_version = req.hermes_version or settings.hermes_version
    if req.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "user_id": user_id,
            "image": target_image,
            "hermes_version": target_version,
        }

    previous = _get_cloud_device(user_id)
    try:
        result = upgrade(user_id, target_image, backup=req.backup)
        _record_upgrade_success(user_id, result["endpoint"], target_image, target_version, previous, result)
        return {"ok": True, **result, "hermes_version": target_version}
    except Exception as exc:
        _record_upgrade_failure(user_id, target_image, target_version, previous, str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/executors/upgrade")
def upgrade_executors(req: UpgradeRequest, _: None = Depends(_auth)):
    target_image = req.image or settings.executor_image
    target_version = req.hermes_version or settings.hermes_version
    users = req.user_ids or _list_cloud_user_ids()

    if req.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "count": len(users),
            "user_ids": users,
            "image": target_image,
            "hermes_version": target_version,
        }

    results: list[dict] = []
    for user_id in users:
        previous = _get_cloud_device(user_id)
        try:
            result = upgrade(user_id, target_image, backup=req.backup)
            _record_upgrade_success(user_id, result["endpoint"], target_image, target_version, previous, result)
            results.append({"ok": True, **result, "hermes_version": target_version})
        except Exception as exc:
            _record_upgrade_failure(user_id, target_image, target_version, previous, str(exc))
            results.append({"ok": False, "user_id": user_id, "image": target_image, "error": str(exc)})

    return {"ok": all(r["ok"] for r in results), "results": results}


@app.post("/users/{user_id}/rollback")
def rollback_user(user_id: str, req: RollbackRequest, _: None = Depends(_auth)):
    previous = _get_cloud_device(user_id)
    image = req.image or (previous or {}).get("previous_executor_image")
    if not image:
        raise HTTPException(status_code=400, detail="No rollback image provided or recorded")

    try:
        result = rollback(user_id, image)
        supabase.table("pi_matrix_devices").update({
            "endpoint": result["endpoint"],
            "executor_image": image,
            "previous_executor_image": (previous or {}).get("executor_image"),
            "hermes_version": (previous or {}).get("previous_hermes_version") or (previous or {}).get("version"),
            "version": (previous or {}).get("previous_hermes_version") or (previous or {}).get("version"),
            "last_upgrade_status": "rolled_back",
            "last_upgrade_error": None,
            "last_upgrade_at": _now_iso(),
        }).eq("user_id", user_id).eq("name", "cloud-instance").execute()
        return {"ok": True, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"ok": True}


def _list_cloud_user_ids() -> list[str]:
    rows = supabase.table("pi_matrix_devices").select("user_id").eq("instance_type", "cloud").execute().data or []
    seen: set[str] = set()
    users: list[str] = []
    for row in rows:
        user_id = row.get("user_id")
        if user_id and user_id not in seen:
            seen.add(user_id)
            users.append(user_id)
    return users


def _get_cloud_device(user_id: str) -> dict | None:
    rows = (
        supabase.table("pi_matrix_devices")
        .select("*")
        .eq("user_id", user_id)
        .eq("name", "cloud-instance")
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _record_upgrade_success(
    user_id: str,
    endpoint: str,
    image: str,
    hermes_version: str,
    previous: dict | None,
    result: dict,
) -> None:
    supabase.table("pi_matrix_devices").update({
        "endpoint": endpoint,
        "version": hermes_version,
        "hermes_version": hermes_version,
        "previous_hermes_version": (previous or {}).get("hermes_version") or (previous or {}).get("version"),
        "executor_image": image,
        "previous_executor_image": (previous or {}).get("executor_image") or result.get("previous_image"),
        "last_upgrade_status": "success",
        "last_upgrade_error": None,
        "last_upgrade_backup_path": result.get("backup_path"),
        "last_upgrade_at": _now_iso(),
    }).eq("user_id", user_id).eq("name", "cloud-instance").execute()


def _record_upgrade_failure(
    user_id: str,
    image: str,
    hermes_version: str,
    previous: dict | None,
    error: str,
) -> None:
    supabase.table("pi_matrix_devices").update({
        "version": (previous or {}).get("version"),
        "hermes_version": (previous or {}).get("hermes_version") or (previous or {}).get("version"),
        "previous_hermes_version": hermes_version,
        "executor_image": (previous or {}).get("executor_image"),
        "previous_executor_image": image,
        "last_upgrade_status": "failed_rolled_back",
        "last_upgrade_error": error[:1000],
        "last_upgrade_at": _now_iso(),
    }).eq("user_id", user_id).eq("name", "cloud-instance").execute()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
