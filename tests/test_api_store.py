"""Test SQLite persistence layer (api/store.py)."""

import os
import sqlite3

import pytest

from api import store


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point DB_PATH to a fresh temporary SQLite file for each test."""
    db_path = tmp_path / "tunas_test.db"
    monkeypatch.setattr(store, "DB_PATH", str(db_path))
    monkeypatch.setenv("DB_PATH", str(db_path))
    return str(db_path)


def test_init_db_creates_tables(tmp_db):
    conn = store.get_conn()
    store.init_db(conn)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cur.fetchall()}
    assert "children" in tables
    assert "visits" in tables


def test_create_child_and_visit_roundtrip(tmp_db):
    conn = store.get_conn()
    store.init_db(conn)

    child_id = store.create_child(conn, name="Budi", sex="M")
    assert isinstance(child_id, int)

    visit_id = store.record_visit(
        conn,
        child_id=child_id,
        age_days=180,
        mode="measurement",
        length_cm=65.4,
        confidence=0.95,
        haz=-0.42,
        qc_reasons=["ok"],
        low_confidence=False,
    )
    assert isinstance(visit_id, int)

    visit = store.get_visit(conn, visit_id)
    assert visit["child_id"] == child_id
    assert visit["age_days"] == 180
    assert visit["mode"] == "measurement"
    assert visit["length_cm"] == pytest.approx(65.4)
    assert visit["confidence"] == pytest.approx(0.95)
    assert visit["haz"] == pytest.approx(-0.42)
    assert visit["qc_reasons"] == ["ok"]
    assert visit["low_confidence"] is False


def test_list_visits_by_child(tmp_db):
    conn = store.get_conn()
    store.init_db(conn)

    c1 = store.create_child(conn, "Ani", "F")
    c2 = store.create_child(conn, "Budi", "M")
    store.record_visit(conn, c1, 180, "measurement", 65.0, 0.9, -0.5, [], False)
    store.record_visit(conn, c2, 200, "estimate", 70.0, 0.3, None, ["no mat"], True)

    v1 = store.list_visits(conn, child_id=c1)
    assert len(v1) == 1
    assert v1[0]["child_id"] == c1

    all_visits = store.list_visits(conn)
    assert len(all_visits) == 2


def test_get_visit_missing_returns_none(tmp_db):
    conn = store.get_conn()
    store.init_db(conn)
    assert store.get_visit(conn, 999) is None


def test_get_conn_creates_parent_directory(tmp_path, monkeypatch):
    db_path = tmp_path / "nested" / "tunas.db"
    monkeypatch.setattr(store, "DB_PATH", str(db_path))
    conn = store.get_conn()
    store.init_db(conn)
    assert db_path.exists()
