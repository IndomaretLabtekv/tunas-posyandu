"""Persistensi kunjungan: PostgreSQL via SQLAlchemy untuk produksi, SQLite untuk test."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import (
    Boolean,
    Column,
    Connection,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

DEFAULT_DATABASE_URL = "postgresql://tunas:tunas@localhost:5432/tunas"
DEFAULT_DB_PATH = "./data/tunas.db"

metadata = MetaData()

children_table = Table(
    "children",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("sex", String(1), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)

visits_table = Table(
    "visits",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("child_id", Integer, ForeignKey("children.id"), nullable=False),
    Column("age_days", Integer, nullable=False),
    Column("mode", String, nullable=False),
    Column("length_cm", Float),
    Column("confidence", Float, nullable=False),
    Column("haz", Float),
    Column("qc_reasons", Text, default="[]"),
    Column("low_confidence", Boolean, default=False),
    Column("measured_at", DateTime, server_default=func.now()),
)

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("role", String(32), nullable=False),
    Column("password_hash", String, nullable=False),
    Column("scope_key", String, nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)

child_profiles_table = Table(
    "child_profiles",
    metadata,
    Column("child_id", Integer, ForeignKey("children.id"), primary_key=True),
    Column("mother_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("birth_date", String(10), nullable=False),
    Column("scope_key", String, nullable=False),
)

growth_checks_table = Table(
    "growth_checks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("child_id", Integer, ForeignKey("children.id"), nullable=False),
    Column("submitted_by", Integer, ForeignKey("users.id"), nullable=False),
    Column("source", String(32), nullable=False),
    Column("age_days", Integer, nullable=False),
    Column("weight_kg", Float, nullable=False),
    Column("length_cm", Float),
    Column("haz", Float),
    Column("mode", String(32), nullable=False),
    Column("confidence", Float, nullable=False),
    Column("qc_reasons", Text, default="[]"),
    Column("status", String(32), nullable=False),
    Column("measured_at", DateTime, nullable=False),
    Column("next_due_at", DateTime, nullable=False),
)

follow_up_cases_table = Table(
    "follow_up_cases",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("child_id", Integer, ForeignKey("children.id"), nullable=False),
    Column("growth_check_id", Integer, ForeignKey("growth_checks.id"), nullable=False),
    Column("scope_key", String, nullable=False),
    Column("status", String(32), nullable=False),
    Column("priority", String(32), nullable=False),
    Column("reason_codes", Text, default="[]"),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now()),
)

case_actions_table = Table(
    "case_actions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("case_id", Integer, ForeignKey("follow_up_cases.id"), nullable=False),
    Column("actor_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("action_type", String(32), nullable=False),
    Column("notes", Text, nullable=False, default=""),
    Column("created_at", DateTime, server_default=func.now()),
)

USER_ROLES = {"mother", "kader", "nutritionist"}
GROWTH_CHECK_STATUSES = {"normal", "needs_review"}
CASE_TRANSITIONS = {
    "needs_review": {"assigned", "resolved"},
    "assigned": {"home_visit"},
    "home_visit": {"verified_risk", "resolved"},
    "verified_risk": {"referred", "resolved"},
    "referred": {"resolved"},
    "resolved": set(),
}


def _database_url() -> str:
    """Baca DATABASE_URL; bila kosong, fallback ke file SQLite lewat DB_PATH."""
    if url := os.getenv("DATABASE_URL"):
        return url
    db_path = os.getenv("DB_PATH", DEFAULT_DB_PATH)
    return f"sqlite+pysqlite:///{Path(db_path).resolve()}"


def _ensure_sqlite_parent(url: str) -> None:
    """Buat direktori induk untuk file SQLite bila perlu."""
    if not url.startswith("sqlite"):
        return
    parsed = urlparse(url)
    db_path = parsed.path or parsed.netloc
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def get_engine() -> Engine:
    """Engine SQLAlchemy untuk URL aktif."""
    url = _database_url()
    _ensure_sqlite_parent(url)
    return create_engine(url, pool_pre_ping=True)


def get_conn(path: str | os.PathLike[str] | None = None) -> Connection:
    """Buka koneksi SQLAlchemy.

    `path` adalah cara lama untuk test berbasis file SQLite; bila diberikan,
    dipakai sebagai database SQLite sementara.
    """
    if path is not None:
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+pysqlite:///{resolved}"
        return create_engine(url).connect()
    return get_engine().connect()


def init_db(conn: Connection | Engine | None = None) -> None:
    """Buat tabel bila belum ada."""
    target = conn if conn is not None else get_engine()
    metadata.create_all(target)
    if isinstance(target, Connection):
        target.commit()


def _row_to_dict(row: Any) -> dict[str, Any]:
    d = dict(row._mapping)
    raw = d.get("qc_reasons", "[]")
    d["qc_reasons"] = json.loads(raw) if isinstance(raw, str) else raw
    d["low_confidence"] = bool(d.get("low_confidence", False))
    measured_at = d.get("measured_at")
    if measured_at is not None:
        d["measured_at"] = measured_at.isoformat()
    return d


def create_child(conn: Connection, name: str, sex: str) -> int:
    """Simpan data anak; kembalikan id."""
    stmt = (
        insert(children_table)
        .values(name=name, sex=sex)
        .returning(children_table.c.id)
    )
    result = conn.execute(stmt)
    try:
        row = result.fetchone()
        assert row is not None
        child_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return child_id


def record_visit(
    conn: Connection,
    child_id: int,
    age_days: int,
    mode: str,
    length_cm: float | None,
    confidence: float,
    haz: float | None,
    qc_reasons: list[str],
    low_confidence: bool,
) -> int:
    """Simpan hasil satu kunjungan; kembalikan id."""
    stmt = (
        insert(visits_table)
        .values(
            child_id=child_id,
            age_days=age_days,
            mode=mode,
            length_cm=length_cm,
            confidence=confidence,
            haz=haz,
            qc_reasons=json.dumps(qc_reasons or []),
            low_confidence=low_confidence,
        )
        .returning(visits_table.c.id)
    )
    result = conn.execute(stmt)
    try:
        row = result.fetchone()
        assert row is not None
        visit_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return visit_id


def get_visit(conn: Connection, visit_id: int) -> dict[str, Any] | None:
    """Ambil satu kunjungan lengkap dengan nama anak."""
    stmt = (
        select(
            visits_table,
            children_table.c.name.label("child_name"),
            children_table.c.sex.label("child_sex"),
        )
        .select_from(
            visits_table.join(children_table, visits_table.c.child_id == children_table.c.id)
        )
        .where(visits_table.c.id == visit_id)
    )
    row = conn.execute(stmt).fetchone()
    return _row_to_dict(row) if row else None


def list_visits(
    conn: Connection, child_id: int | None = None
) -> list[dict[str, Any]]:
    """Daftar kunjungan, opsional difilter per anak."""
    stmt = (
        select(
            visits_table,
            children_table.c.name.label("child_name"),
            children_table.c.sex.label("child_sex"),
        )
        .select_from(
            visits_table.join(children_table, visits_table.c.child_id == children_table.c.id)
        )
    )
    if child_id is not None:
        stmt = stmt.where(visits_table.c.child_id == child_id)
    stmt = stmt.order_by(visits_table.c.measured_at.asc())
    rows = conn.execute(stmt).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_child(conn: Connection, child_id: int) -> dict[str, Any] | None:
    """Ambil data satu anak."""
    stmt = select(children_table).where(children_table.c.id == child_id)
    row = conn.execute(stmt).fetchone()
    return dict(row._mapping) if row else None


def list_children(conn: Connection) -> list[dict[str, Any]]:
    """Daftar semua anak."""
    stmt = select(children_table).order_by(children_table.c.id)
    rows = conn.execute(stmt).fetchall()
    return [dict(row._mapping) for row in rows]


def _coerce_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_scope(scope_key: str) -> str:
    scope = scope_key.strip()
    if not scope:
        raise ValueError("scope_key tidak boleh kosong")
    return scope


def create_user(
    conn: Connection,
    *,
    name: str,
    role: str,
    password_hash: str,
    scope_key: str,
) -> int:
    """Simpan akun workflow dengan peran dan scope yang eksplisit."""
    if role not in USER_ROLES:
        raise ValueError(f"role tidak dikenal: {role}")
    if not name.strip():
        raise ValueError("name tidak boleh kosong")
    if not password_hash:
        raise ValueError("password_hash tidak boleh kosong")

    result = conn.execute(
        insert(users_table).values(
            name=name.strip(),
            role=role,
            password_hash=password_hash,
            scope_key=_require_scope(scope_key),
        ).returning(users_table.c.id)
    )
    try:
        row = result.fetchone()
        assert row is not None
        user_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return user_id


def create_child_profile(
    conn: Connection,
    *,
    child_id: int,
    mother_id: int,
    birth_date: str,
    scope_key: str,
) -> None:
    """Hubungkan anak ke ibu dan scope layanan untuk workflow baru."""
    if not birth_date.strip():
        raise ValueError("birth_date tidak boleh kosong")
    conn.execute(
        insert(child_profiles_table).values(
            child_id=child_id,
            mother_id=mother_id,
            birth_date=birth_date,
            scope_key=_require_scope(scope_key),
        )
    )
    conn.commit()


def create_owned_child(
    conn: Connection,
    *,
    name: str,
    sex: str,
    mother_id: int,
    birth_date: str,
    scope_key: str,
) -> int:
    """Create the legacy child row and workflow ownership row atomically."""
    if sex not in {"M", "F"}:
        raise ValueError("sex harus M atau F")
    if not name.strip():
        raise ValueError("name tidak boleh kosong")
    if not birth_date.strip():
        raise ValueError("birth_date tidak boleh kosong")

    try:
        result = conn.execute(
            insert(children_table)
            .values(name=name.strip(), sex=sex)
            .returning(children_table.c.id)
        )
        try:
            row = result.fetchone()
            assert row is not None
            child_id = int(row[0])
        finally:
            result.close()
        conn.execute(
            insert(child_profiles_table).values(
                child_id=child_id,
                mother_id=mother_id,
                birth_date=birth_date,
                scope_key=_require_scope(scope_key),
            )
        )
        conn.commit()
        return child_id
    except Exception:
        conn.rollback()
        raise


def get_child_profile(conn: Connection, child_id: int) -> dict[str, Any] | None:
    """Return child identity plus mother ownership and workflow scope."""
    row = conn.execute(
        select(
            children_table.c.id.label("child_id"),
            children_table.c.name,
            children_table.c.sex,
            child_profiles_table.c.mother_id,
            child_profiles_table.c.birth_date,
            child_profiles_table.c.scope_key,
        )
        .select_from(
            children_table.join(
                child_profiles_table,
                children_table.c.id == child_profiles_table.c.child_id,
            )
        )
        .where(children_table.c.id == child_id)
    ).fetchone()
    return dict(row._mapping) if row else None


def list_owned_children(conn: Connection, mother_id: int) -> list[dict[str, Any]]:
    """List only children explicitly linked to one mother account."""
    rows = conn.execute(
        select(
            children_table.c.id.label("child_id"),
            children_table.c.name,
            children_table.c.sex,
            child_profiles_table.c.birth_date,
            child_profiles_table.c.scope_key,
        )
        .select_from(
            children_table.join(
                child_profiles_table,
                children_table.c.id == child_profiles_table.c.child_id,
            )
        )
        .where(child_profiles_table.c.mother_id == mother_id)
        .order_by(children_table.c.id)
    ).fetchall()
    return [dict(row._mapping) for row in rows]


def record_growth_check(
    conn: Connection,
    *,
    child_id: int,
    submitted_by: int,
    source: str,
    age_days: int,
    weight_kg: float,
    length_cm: float | None,
    haz: float | None,
    mode: str,
    confidence: float,
    qc_reasons: list[str],
    status: str,
    measured_at: str | datetime,
    next_due_at: str | datetime,
) -> int:
    """Simpan satu hasil growth check sebagai structured result."""
    if not 0 <= age_days <= 730:
        raise ValueError("age_days harus antara 0 dan 730")
    if weight_kg <= 0:
        raise ValueError("weight_kg harus lebih besar dari 0")
    if status not in GROWTH_CHECK_STATUSES:
        raise ValueError(f"status growth check tidak dikenal: {status}")
    if not source.strip() or not mode.strip():
        raise ValueError("source dan mode tidak boleh kosong")

    result = conn.execute(
        insert(growth_checks_table).values(
            child_id=child_id,
            submitted_by=submitted_by,
            source=source,
            age_days=age_days,
            weight_kg=weight_kg,
            length_cm=length_cm,
            haz=haz,
            mode=mode,
            confidence=confidence,
            qc_reasons=json.dumps(qc_reasons or []),
            status=status,
            measured_at=_coerce_datetime(measured_at),
            next_due_at=_coerce_datetime(next_due_at),
        ).returning(growth_checks_table.c.id)
    )
    try:
        row = result.fetchone()
        assert row is not None
        check_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return check_id


def list_growth_checks(conn: Connection, child_id: int) -> list[dict[str, Any]]:
    """Return a child's structured submissions with optional case state."""
    rows = conn.execute(
        select(
            growth_checks_table,
            follow_up_cases_table.c.id.label("case_id"),
            follow_up_cases_table.c.status.label("case_status"),
        )
        .select_from(
            growth_checks_table.outerjoin(
                follow_up_cases_table,
                growth_checks_table.c.id == follow_up_cases_table.c.growth_check_id,
            )
        )
        .where(growth_checks_table.c.child_id == child_id)
        .order_by(growth_checks_table.c.measured_at.asc(), growth_checks_table.c.id.asc())
    ).fetchall()

    checks: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row._mapping)
        item["qc_reasons"] = json.loads(item.get("qc_reasons") or "[]")
        for key in ("measured_at", "next_due_at"):
            if isinstance(item.get(key), datetime):
                item[key] = item[key].isoformat()
        checks.append(item)
    return checks


def create_follow_up_case(
    conn: Connection,
    *,
    child_id: int,
    growth_check_id: int,
    scope_key: str,
    status: str,
    priority: str,
    reason_codes: list[str],
) -> int:
    """Buat case tindak lanjut yang dapat dilacak lintas peran."""
    if status not in CASE_TRANSITIONS:
        raise ValueError(f"status kasus tidak dikenal: {status}")
    if not priority.strip():
        raise ValueError("priority tidak boleh kosong")

    result = conn.execute(
        insert(follow_up_cases_table).values(
            child_id=child_id,
            growth_check_id=growth_check_id,
            scope_key=_require_scope(scope_key),
            status=status,
            priority=priority,
            reason_codes=json.dumps(reason_codes or []),
        ).returning(follow_up_cases_table.c.id)
    )
    try:
        row = result.fetchone()
        assert row is not None
        case_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return case_id


def list_cases(
    conn: Connection,
    *,
    scope_key: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Daftar case pada scope tertentu, lengkap dengan hasil screening terbaru."""
    stmt = (
        select(
            follow_up_cases_table,
            children_table.c.name.label("child_name"),
            growth_checks_table.c.age_days.label("growth_age_days"),
            growth_checks_table.c.weight_kg.label("growth_weight_kg"),
            growth_checks_table.c.length_cm.label("growth_length_cm"),
            growth_checks_table.c.haz.label("growth_haz"),
            growth_checks_table.c.confidence.label("growth_confidence"),
            growth_checks_table.c.mode.label("growth_mode"),
            growth_checks_table.c.status.label("growth_status"),
            growth_checks_table.c.qc_reasons.label("growth_qc_reasons"),
            growth_checks_table.c.measured_at.label("growth_measured_at"),
            growth_checks_table.c.next_due_at.label("growth_next_due_at"),
        )
        .select_from(
            follow_up_cases_table
            .join(children_table, follow_up_cases_table.c.child_id == children_table.c.id)
            .join(
                growth_checks_table,
                follow_up_cases_table.c.growth_check_id == growth_checks_table.c.id,
            )
        )
        .where(follow_up_cases_table.c.scope_key == _require_scope(scope_key))
        .order_by(follow_up_cases_table.c.created_at.asc(), follow_up_cases_table.c.id.asc())
    )
    if status is not None:
        stmt = stmt.where(follow_up_cases_table.c.status == status)

    rows = conn.execute(stmt).fetchall()
    cases = []
    for row in rows:
        item = dict(row._mapping)
        item["reason_codes"] = json.loads(item.get("reason_codes") or "[]")
        item["growth_qc_reasons"] = json.loads(item.get("growth_qc_reasons") or "[]")
        for key in ("created_at", "updated_at", "growth_measured_at", "growth_next_due_at"):
            if isinstance(item.get(key), datetime):
                item[key] = item[key].isoformat()
        cases.append(item)
    return cases


def transition_case(
    conn: Connection,
    *,
    case_id: int,
    new_status: str,
    actor_id: int,
    notes: str = "",
) -> None:
    """Pindahkan case hanya melalui transisi workflow yang disepakati."""
    row = conn.execute(
        select(follow_up_cases_table.c.status).where(follow_up_cases_table.c.id == case_id)
    ).fetchone()
    if row is None:
        raise ValueError("kasus tidak ditemukan")
    current_status = str(row[0])
    if new_status not in CASE_TRANSITIONS:
        raise ValueError(f"status kasus tidak dikenal: {new_status}")
    if new_status not in CASE_TRANSITIONS[current_status]:
        raise ValueError(
            f"transisi kasus tidak diizinkan: {current_status} -> {new_status}"
        )

    conn.execute(
        follow_up_cases_table.update()
        .where(follow_up_cases_table.c.id == case_id)
        .values(status=new_status, updated_at=datetime.now(timezone.utc))
    )
    conn.execute(
        insert(case_actions_table).values(
            case_id=case_id,
            actor_id=actor_id,
            action_type=f"status:{new_status}",
            notes=notes,
        )
    )
    conn.commit()


def record_case_action(
    conn: Connection,
    *,
    case_id: int,
    actor_id: int,
    action_type: str,
    notes: str,
) -> int:
    """Simpan catatan tindakan tanpa mengubah hasil measurement asli."""
    if not action_type.strip():
        raise ValueError("action_type tidak boleh kosong")
    result = conn.execute(
        insert(case_actions_table).values(
            case_id=case_id,
            actor_id=actor_id,
            action_type=action_type,
            notes=notes or "",
        ).returning(case_actions_table.c.id)
    )
    try:
        row = result.fetchone()
        assert row is not None
        action_id = int(row[0])
    finally:
        result.close()
    conn.commit()
    return action_id


def list_case_actions(conn: Connection, case_id: int) -> list[dict[str, Any]]:
    """Return the immutable action log for one follow-up case."""
    rows = conn.execute(
        select(case_actions_table)
        .where(case_actions_table.c.case_id == case_id)
        .order_by(case_actions_table.c.created_at.asc(), case_actions_table.c.id.asc())
    ).fetchall()
    actions: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row._mapping)
        raw_notes = item.get("notes") or ""
        try:
            details = json.loads(raw_notes)
        except (TypeError, json.JSONDecodeError):
            details = None
        item["details"] = details if isinstance(details, dict) else None
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()
        actions.append(item)
    return actions


def get_scoped_case(
    conn: Connection,
    *,
    case_id: int,
    scope_key: str,
) -> dict[str, Any] | None:
    """Resolve a case only inside the caller's authorized service scope."""
    return next(
        (
            case
            for case in list_cases(conn, scope_key=scope_key)
            if int(case["id"]) == case_id
        ),
        None,
    )
