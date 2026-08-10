"""Authentication and access-control tests for the growth workflow API."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api import store
from api.auth import hash_password, verify_password
from api.dependencies import (
    AuthenticatedUser,
    assert_child_access,
    enforce_scope,
    get_current_user,
    require_roles,
)
from api.workflow_routes import router


@pytest.fixture
def auth_app(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-workflow")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'auth.db'}")

    app = FastAPI()
    app.include_router(router, prefix="/api")

    @app.get("/protected")
    def protected(user: AuthenticatedUser = Depends(require_roles("kader"))):
        return {"user_id": user.user_id, "role": user.role}

    @app.get("/scope/{scope_key}")
    def scoped(
        scope_key: str,
        user: AuthenticatedUser = Depends(require_roles("kader")),
    ):
        enforce_scope(user, scope_key)
        return {"scope_key": scope_key}

    return app


def test_password_hash_is_one_way_and_verifiable():
    password_hash = hash_password("secret-password")

    assert password_hash != "secret-password"
    assert verify_password("secret-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_register_and_login_issue_claimed_mother_token(auth_app):
    client = TestClient(auth_app)
    register = client.post(
        "/api/auth/register",
        json={"name": "Ibu Ani", "password": "secret-password", "scope_key": "posyandu-a"},
    )

    assert register.status_code == 201
    body = register.json()
    assert body["user"] == {"id": 1, "name": "Ibu Ani", "role": "mother", "scope_key": "posyandu-a"}

    claims = jwt.decode(
        body["access_token"],
        "test-secret-for-workflow",
        algorithms=["HS256"],
    )
    assert claims["sub"] == "1"
    assert claims["role"] == "mother"
    assert claims["scope_key"] == "posyandu-a"
    assert "exp" in claims

    login = client.post(
        "/api/auth/login",
        json={"name": "Ibu Ani", "password": "secret-password", "scope_key": "posyandu-a"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "mother"


def test_registration_does_not_allow_public_staff_creation(auth_app):
    client = TestClient(auth_app)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Kader Jahat",
            "password": "secret-password",
            "scope_key": "posyandu-a",
            "role": "kader",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "mother"


def test_wrong_password_is_unauthorized(auth_app):
    client = TestClient(auth_app)
    client.post(
        "/api/auth/register",
        json={"name": "Ibu Ani", "password": "secret-password", "scope_key": "posyandu-a"},
    )

    response = client.post(
        "/api/auth/login",
        json={"name": "Ibu Ani", "password": "wrong-password", "scope_key": "posyandu-a"},
    )

    assert response.status_code == 401


def test_expired_and_malformed_tokens_are_unauthorized(auth_app):
    client = TestClient(auth_app)
    expired = jwt.encode(
        {
            "sub": "1",
            "role": "mother",
            "scope_key": "posyandu-a",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "test-secret-for-workflow",
        algorithm="HS256",
    )

    expired_response = client.get(
        "/protected", headers={"Authorization": f"Bearer {expired}"}
    )
    malformed_response = client.get(
        "/protected", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert expired_response.status_code == 401
    assert malformed_response.status_code == 401


def test_role_and_scope_guards_reject_wrong_access(auth_app):
    client = TestClient(auth_app)
    registered = client.post(
        "/api/auth/register",
        json={"name": "Ibu Ani", "password": "secret-password", "scope_key": "posyandu-a"},
    ).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    role_response = client.get("/protected", headers=headers)
    scope_response = client.get("/scope/posyandu-b", headers=headers)

    assert role_response.status_code == 403
    assert scope_response.status_code == 403


def test_child_access_is_limited_to_mother_ownership_and_staff_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'scope.db'}")
    conn = store.get_conn()
    store.init_db(conn)
    try:
        mother_id = store.create_user(
            conn,
            name="Ibu Ani",
            role="mother",
            password_hash="hash",
            scope_key="posyandu-a",
        )
        other_mother_id = store.create_user(
            conn,
            name="Ibu Budi",
            role="mother",
            password_hash="hash",
            scope_key="posyandu-a",
        )
        kader_id = store.create_user(
            conn,
            name="Kader A",
            role="kader",
            password_hash="hash",
            scope_key="posyandu-a",
        )
        other_kader_id = store.create_user(
            conn,
            name="Kader B",
            role="kader",
            password_hash="hash",
            scope_key="posyandu-b",
        )
        child_id = store.create_child(conn, name="Anak Ani", sex="F")
        store.create_child_profile(
            conn,
            child_id=child_id,
            mother_id=mother_id,
            birth_date="2025-01-01",
            scope_key="posyandu-a",
        )

        assert assert_child_access(
            conn, AuthenticatedUser(mother_id, "mother", "posyandu-a"), child_id
        )
        assert not assert_child_access(
            conn, AuthenticatedUser(other_mother_id, "mother", "posyandu-a"), child_id
        )
        assert assert_child_access(
            conn, AuthenticatedUser(kader_id, "kader", "posyandu-a"), child_id
        )
        assert not assert_child_access(
            conn, AuthenticatedUser(other_kader_id, "kader", "posyandu-b"), child_id
        )
    finally:
        conn.close()


def test_missing_bearer_token_is_unauthorized(auth_app):
    client = TestClient(auth_app)

    response = client.get("/protected")

    assert response.status_code == 401
