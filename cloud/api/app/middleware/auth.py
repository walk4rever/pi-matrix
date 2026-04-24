from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db import supabase

bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(bearer),
) -> dict:
    try:
        result = supabase.auth.get_user(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not result or not result.user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"sub": result.user.id, "email": result.user.email}


def get_device(
    creds: HTTPAuthorizationCredentials = Security(bearer),
) -> str:
    """Device auth via static token (not JWT)."""
    return creds.credentials
