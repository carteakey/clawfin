from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from backend.config import settings

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_at: str


def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Require the UI JWT when CLAWFIN_PASSWORD is configured."""
    if not settings.PASSWORD:
        return

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("sub") != "clawfin-user":
        raise HTTPException(status_code=401, detail="Invalid token subject")


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
