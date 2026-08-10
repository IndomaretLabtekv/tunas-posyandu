"""Password hashing and JWT helpers for the workflow API."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_MINUTES = 60
password_hash = PasswordHash.recommended()


class AuthenticationError(ValueError):
    """Raised when credentials or a token cannot be trusted."""


def hash_password(password: str) -> str:
    """Hash a password with the recommended Argon2 configuration."""
    if not password:
        raise ValueError("password tidak boleh kosong")
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password without exposing malformed stored hashes."""
    if not password or not hashed_password:
        return False
    try:
        return password_hash.verify(password, hashed_password)
    except (TypeError, ValueError):
        return False


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET belum diset")
    return secret


def _token_minutes() -> int:
    raw = os.getenv("JWT_ACCESS_MINUTES", str(DEFAULT_ACCESS_TOKEN_MINUTES))
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise RuntimeError("JWT_ACCESS_MINUTES harus berupa integer") from exc
    if minutes <= 0:
        raise RuntimeError("JWT_ACCESS_MINUTES harus lebih besar dari 0")
    return minutes


def create_access_token(user_id: int, role: str, scope_key: str) -> str:
    """Create a short-lived token carrying only workflow authorization claims."""
    if user_id <= 0:
        raise ValueError("user_id tidak valid")
    if not role.strip() or not scope_key.strip():
        raise ValueError("role dan scope_key tidak boleh kosong")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "scope_key": scope_key,
        "exp": now + timedelta(minutes=_token_minutes()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate the claims required by workflow dependencies."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("token tidak valid") from exc
    except RuntimeError:
        raise

    raw_user_id = payload.get("sub")
    role = payload.get("role")
    scope_key = payload.get("scope_key")
    if (
        isinstance(raw_user_id, bool)
        or not str(raw_user_id or "").isdigit()
        or int(raw_user_id) <= 0
        or not isinstance(role, str)
        or not role.strip()
        or not isinstance(scope_key, str)
        or not scope_key.strip()
    ):
        raise AuthenticationError("claim token tidak lengkap")

    return payload
