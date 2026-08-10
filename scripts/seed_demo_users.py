"""Create deterministic demo accounts and dashboard-ready workflow data."""

from __future__ import annotations

import os
import json
import secrets
from datetime import date, datetime, timedelta, timezone

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


DEMO_MOTHER_CHILDREN = (
    ("Bayi Demo", "F", 180, "normal", []),
    ("Alya", "F", 245, "normal", []),
)

COMMUNITY_CHILDREN = (
    ("Bima", "M", 310, "needs_review", ["low_confidence"]),
    ("Citra", "F", 420, "needs_review", ["growth_signal"]),
    ("Daffa", "M", 520, "assigned", ["estimate_mode"]),
    ("Elina", "F", 275, "assigned", ["low_confidence"]),
    ("Farhan", "M", 390, "home_visit", ["growth_signal"]),
    ("Gita", "F", 455, "home_visit", ["cv_rejected"]),
    ("Hana", "F", 330, "verified_risk", ["growth_signal"]),
    ("Ilham", "M", 610, "verified_risk", ["growth_signal"]),
    ("Jasmine", "F", 500, "referred", ["growth_signal"]),
    ("Kayla", "F", 365, "resolved", ["low_confidence"]),
)

DEMO_CHILDREN = DEMO_MOTHER_CHILDREN + COMMUNITY_CHILDREN


def _seed_children(conn, *, user_ids: dict[str, int], scope_key: str) -> None:
    existing = {
        row.name: {"child_id": int(row.child_id), "mother_id": int(row.mother_id)}
        for row in conn.execute(
            select(
                store.children_table.c.id.label("child_id"),
                store.children_table.c.name,
                store.child_profiles_table.c.mother_id,
            )
            .join(
                store.child_profiles_table,
                store.child_profiles_table.c.child_id == store.children_table.c.id,
            )
            .where(store.child_profiles_table.c.scope_key == scope_key)
        )
    }
    now = datetime.now(timezone.utc).replace(microsecond=0)

    for index, (name, sex, age_days, target_status, reasons) in enumerate(DEMO_CHILDREN):
        mother_id = (
            user_ids["mother"]
            if index < len(DEMO_MOTHER_CHILDREN)
            else user_ids["community_mother"]
        )
        child = existing.get(name)
        if child is None:
            child_id = store.create_owned_child(
                conn,
                name=name,
                sex=sex,
                mother_id=mother_id,
                birth_date=(date.today() - timedelta(days=age_days)).isoformat(),
                scope_key=scope_key,
            )
        else:
            child_id = child["child_id"]
            if child["mother_id"] != mother_id:
                conn.execute(
                    store.child_profiles_table.update()
                    .where(store.child_profiles_table.c.child_id == child_id)
                    .values(mother_id=mother_id)
                )
                conn.commit()
        if store.list_growth_checks(conn, child_id):
            continue

        measured_at = now - timedelta(days=2 + index * 4)
        base_weight = 6.2 + age_days / 180
        base_length = 58.0 + age_days / 28
        store.record_growth_check(
            conn,
            child_id=child_id,
            submitted_by=mother_id,
            source="mother",
            age_days=age_days - 30,
            weight_kg=round(base_weight - 0.3, 1),
            length_cm=round(base_length - 1.4, 1),
            haz=-0.4,
            mode="measurement",
            confidence=0.96,
            qc_reasons=[],
            status="normal",
            measured_at=measured_at - timedelta(days=30),
            next_due_at=measured_at,
        )
        check_id = store.record_growth_check(
            conn,
            child_id=child_id,
            submitted_by=mother_id,
            source="mother",
            age_days=age_days,
            weight_kg=round(base_weight, 1),
            length_cm=round(base_length, 1),
            haz=-2.3 if "growth_signal" in reasons else -0.7,
            mode="estimate" if "estimate_mode" in reasons else "measurement",
            confidence=0.42 if "low_confidence" in reasons else 0.93,
            qc_reasons=reasons,
            status="normal" if target_status == "normal" else "needs_review",
            measured_at=measured_at,
            next_due_at=measured_at + timedelta(days=30),
        )
        if target_status == "normal":
            continue

        case_id = store.create_follow_up_case(
            conn,
            child_id=child_id,
            growth_check_id=check_id,
            scope_key=scope_key,
            status="needs_review",
            priority="urgent" if {"growth_signal", "cv_rejected"} & set(reasons) else "review",
            reason_codes=reasons,
        )
        transitions = {
            "needs_review": (),
            "assigned": ("assigned",),
            "home_visit": ("assigned", "home_visit"),
            "verified_risk": ("assigned", "home_visit", "verified_risk"),
            "referred": ("assigned", "home_visit", "verified_risk", "referred"),
            "resolved": ("assigned", "home_visit", "verified_risk", "resolved"),
        }[target_status]
        for status in transitions:
            actor_id = user_ids["nutritionist"] if status in {"referred", "resolved"} else user_ids["kader"]
            if status == "verified_risk":
                store.record_growth_check(
                    conn,
                    child_id=child_id,
                    submitted_by=user_ids["kader"],
                    source="kader",
                    age_days=age_days,
                    weight_kg=round(base_weight + 0.1, 1),
                    length_cm=round(base_length - 0.3, 1),
                    haz=-2.2,
                    mode="manual_verification",
                    confidence=1.0,
                    qc_reasons=[],
                    status="needs_review",
                    measured_at=measured_at + timedelta(days=1),
                    next_due_at=measured_at + timedelta(days=31),
                )
            store.transition_case(
                conn,
                case_id=case_id,
                new_status=status,
                actor_id=actor_id,
                notes=json.dumps({"notes": f"Data demo: {status.replace('_', ' ')}"}),
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
        user_ids["community_mother"] = _ensure_user(
            conn,
            name="Ibu Komunitas Demo",
            role="mother",
            password=secrets.token_urlsafe(32),
            scope_key=scope_key,
        )

        _seed_children(conn, user_ids=user_ids, scope_key=scope_key)
    finally:
        conn.close()

    print("Demo Tunas siap")
    print(f"Data: {len(DEMO_MOTHER_CHILDREN)} anak Ibu Demo / 10 kasus tindak lanjut")
    print(f"Scope: {scope_key}")
    for name, role in accounts:
        print(f"{role}: {name} / {password}")


if __name__ == "__main__":
    main()
