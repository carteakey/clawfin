"""Small encryption helpers for sensitive local configuration values."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings


ENC_PREFIX = "enc:"


def _fernet() -> Fernet:
    secret = settings.SECRET_KEY or "clawfin-dev-secret-change-me"
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if value.startswith(ENC_PREFIX):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENC_PREFIX}{token}"


def decrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    if not value.startswith(ENC_PREFIX):
        return value
    token = value[len(ENC_PREFIX):].encode("utf-8")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken:
        return None


def is_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(ENC_PREFIX))
