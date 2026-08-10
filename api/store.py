"""Persistensi kunjungan: PostgreSQL via SQLAlchemy untuk produksi, SQLite untuk test."""

from __future__ import annotations

import json
import os
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
