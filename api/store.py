"""Persistensi kunjungan (SQLite untuk MVP)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = "./data/tunas.db"


def _db_path() -> str:
    return os.getenv("DB_PATH", DEFAULT_DB_PATH)


def get_conn(path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    """Buka koneksi SQLite, buat direktori induk bila perlu."""
    path = Path(path) if path is not None else Path(_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Inisialisasi skema: anak dan kunjungannya."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            sex TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER NOT NULL,
            age_days INTEGER NOT NULL,
            mode TEXT NOT NULL,
            length_cm REAL,
            confidence REAL NOT NULL,
            haz REAL,
            qc_reasons TEXT NOT NULL DEFAULT '[]',
            low_confidence INTEGER NOT NULL DEFAULT 0,
            measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (child_id) REFERENCES children(id)
        );
        """
    )
    conn.commit()


def create_child(conn: sqlite3.Connection, name: str, sex: str) -> int:
    """Simpan data anak; kembalikan id."""
    cur = conn.execute(
        "INSERT INTO children (name, sex) VALUES (?, ?)",
        (name, sex),
    )
    conn.commit()
    return int(cur.lastrowid)


def record_visit(
    conn: sqlite3.Connection,
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
    cur = conn.execute(
        """
        INSERT INTO visits
            (child_id, age_days, mode, length_cm, confidence, haz,
             qc_reasons, low_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            child_id,
            age_days,
            mode,
            length_cm,
            confidence,
            haz,
            json.dumps(qc_reasons or []),
            1 if low_confidence else 0,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["low_confidence"] = bool(d["low_confidence"])
    d["qc_reasons"] = json.loads(d["qc_reasons"])
    return d


def get_visit(conn: sqlite3.Connection, visit_id: int) -> dict[str, Any] | None:
    """Ambil satu kunjungan lengkap dengan nama anak."""
    row = conn.execute(
        """
        SELECT v.*, c.name AS child_name, c.sex AS child_sex
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.id = ?
        """,
        (visit_id,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def list_visits(
    conn: sqlite3.Connection, child_id: int | None = None
) -> list[dict[str, Any]]:
    """Daftar kunjungan, opsional difilter per anak."""
    sql = """
        SELECT v.*, c.name AS child_name, c.sex AS child_sex
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """
    params: tuple = ()
    if child_id is not None:
        sql += " WHERE v.child_id = ?"
        params = (child_id,)
    sql += " ORDER BY v.measured_at ASC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_child(conn: sqlite3.Connection, child_id: int) -> dict[str, Any] | None:
    """Ambil data satu anak."""
    row = conn.execute(
        "SELECT id, name, sex, created_at FROM children WHERE id = ?",
        (child_id,),
    ).fetchone()
    return dict(row) if row else None


def list_children(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Daftar semua anak."""
    rows = conn.execute(
        "SELECT id, name, sex, created_at FROM children ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]
