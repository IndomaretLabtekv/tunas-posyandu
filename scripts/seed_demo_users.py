"""Create deterministic local demo accounts and one age-valid child."""

from __future__ import annotations

import os
from datetime import date, timedelta

from sqlalchemy import select

from api import auth, store


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} belum diset")
    return value


def _find_user(conn, *, name: str, scope_key: str) -> dict | None:
    row = conn.execute(
        select(store.users_table).where(
            store.users_table.c.name == name,
            store.users_table.c.scope_key == scope_key,
        )
    ).fetchone()
    return dict(row._mapping) if row else None


def _ensure_user(conn, *, name: str, role: str, password: str, scope_key: str) -> int:
    existing = _find_user(conn, name=name, scope_key=scope_key)
    if existing:
        conn.execute(
            store.users_table.update()
            .where(store.users_table.c.id == int(existing["id"]))
            .values(role=role, password_hash=auth.hash_password(password))
        )
        conn.commit()
        return int(existing["id"])
    return store.create_user(
        conn,
        name=name,
        role=role,
        password_hash=auth.hash_password(password),
        scope_key=scope_key,
    )


def main() -> None:
    password = _required("DEMO_PASSWORD")
    scope_key = os.getenv("DEMO_SCOPE_KEY", "posyandu-demo").strip()
    accounts = (
        ("Ibu Demo", "mother"),
        ("Kader Demo", "kader"),
        ("Ahli Gizi Demo", "nutritionist"),
    )

    conn = store.get_conn()
    try:
        store.init_db(conn)
        user_ids = {
            role: _ensure_user(
                conn,
                name=name,
                role=role,
                password=password,
                scope_key=scope_key,
            )
            for name, role in accounts
        }

        children = store.list_owned_children(conn, user_ids["mother"])
        if not children:
            store.create_owned_child(
                conn,
                name="Bayi Demo",
                sex="F",
                mother_id=user_ids["mother"],
                birth_date=(date.today() - timedelta(days=180)).isoformat(),
                scope_key=scope_key,
            )
    finally:
        conn.close()

    print("Demo Tunas siap")
    print(f"Scope: {scope_key}")
    for name, role in accounts:
        print(f"{role}: {name} / {password}")


if __name__ == "__main__":
    main()
