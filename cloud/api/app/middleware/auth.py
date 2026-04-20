from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings

bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(bearer),
) -> dict:
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_device(
    creds: HTTPAuthorizationCredentials = Security(bearer),
) -> str:
    """Device auth via static token (not JWT)."""
    return creds.credentials
