from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from .config import settings
from ..db.models import User


def create_access_token(user: User) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("APPV2_JWT_SECRET is not set; cannot issue tokens.")
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": role_val,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    if not settings.jwt_secret:
        raise jwt.InvalidTokenError("APPV2_JWT_SECRET is not set")
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
