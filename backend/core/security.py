"""JWT auth and password hashing."""
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from core.config import get_settings

# Bcrypt only uses the first 72 bytes of the password
BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(plain: str) -> bytes:
    """Encode password to bytes, truncating to bcrypt's 72-byte limit."""
    encoded = plain.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        encoded = encoded[:BCRYPT_MAX_PASSWORD_BYTES]
    return encoded


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(plain),
            hashed.encode("utf-8") if isinstance(hashed, str) else hashed,
        )
    except Exception:
        return False


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(_password_bytes(plain), salt)
    return hashed.decode("utf-8")


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
