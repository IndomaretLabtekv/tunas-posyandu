"""FastAPI authentication, role, and scope dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, status
from sqlalchemy import Connection, select

from api import auth, store


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: int
    role: str
    scope_key: str


def _unauthorized(detail: str = "kredensial tidak valid") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract the bearer token and return its trusted authorization claims."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()

    try:
        payload = auth.decode_access_token(token.strip())
    except auth.AuthenticationError as exc:
        raise _unauthorized() from exc

    return AuthenticatedUser(
        user_id=int(payload["sub"]),
        role=payload["role"],
        scope_key=payload["scope_key"],
    )


def require_roles(*roles: str) -> Callable[[Request], AuthenticatedUser]:
    """Build a dependency that requires one of the supplied workflow roles."""
    allowed_roles = {role for role in roles if role}
    if not allowed_roles:
        raise ValueError("minimal satu role harus diminta")

    def dependency(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="role tidak memiliki akses")
        return user

    return dependency


def enforce_scope(user: AuthenticatedUser, scope_key: str) -> None:
    """Reject staff access outside the scope carried by the token."""
    if user.scope_key != scope_key:
        raise HTTPException(status_code=403, detail="scope tidak memiliki akses")


def assert_child_access(conn: Connection, user: AuthenticatedUser, child_id: int) -> bool:
    """Check mother ownership or staff scope without leaking child records."""
    row = conn.execute(
        select(
            store.child_profiles_table.c.mother_id,
            store.child_profiles_table.c.scope_key,
        ).where(store.child_profiles_table.c.child_id == child_id)
    ).fetchone()
    if row is None:
        return False
    if user.role == "mother":
        return int(row.mother_id) == user.user_id
    return str(row.scope_key) == user.scope_key
