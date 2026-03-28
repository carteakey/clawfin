from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from jose import jwt
from backend.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_at: str


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate with the app password."""
    if not settings.PASSWORD:
        # No password set — open access
        raise HTTPException(status_code=400, detail="No password configured. Set CLAWFIN_PASSWORD env var.")

    if req.password != settings.PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    expires = datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRE_HOURS)
    token = jwt.encode(
        {"exp": expires, "sub": "clawfin-user"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return TokenResponse(token=token, expires_at=expires.isoformat())


@router.get("/check")
def check_auth_status():
    """Check if auth is required (password is set)."""
    return {
        "auth_required": bool(settings.PASSWORD),
    }
