"""Test SQLAlchemy persistence layer (api/store.py)."""

import pytest
from sqlalchemy import text

from api import store


@pytest.fixture
def tmp_conn(tmp_path, monkeypatch):
    """Provide an initialized SQLAlchemy connection isolated per test."""
    db_path = tmp_path / "tunas_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    conn = store.get_conn()
    store.init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_init_db_creates_tables(tmp_conn):
    cur = tmp_conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    )
    tables = {row[0] for row in cur.fetchall()}
    assert "children" in tables
    assert "visits" in tables


def test_create_child_and_visit_roundtrip(tmp_conn):
    child_id = store.create_child(tmp_conn, name="Budi", sex="M")
    assert isinstance(child_id, int)

    visit_id = store.record_visit(
        tmp_conn,
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

    visit = store.get_visit(tmp_conn, visit_id)
    assert visit["child_id"] == child_id
    assert visit["age_days"] == 180
    assert visit["mode"] == "measurement"
    assert visit["length_cm"] == pytest.approx(65.4)
    assert visit["confidence"] == pytest.approx(0.95)
    assert visit["haz"] == pytest.approx(-0.42)
    assert visit["qc_reasons"] == ["ok"]
    assert visit["low_confidence"] is False


def test_list_visits_by_child(tmp_conn):
    c1 = store.create_child(tmp_conn, "Ani", "F")
    c2 = store.create_child(tmp_conn, "Budi", "M")
    store.record_visit(tmp_conn, c1, 180, "measurement", 65.0, 0.9, -0.5, [], False)
    store.record_visit(tmp_conn, c2, 200, "estimate", 70.0, 0.3, None, ["no mat"], True)

    v1 = store.list_visits(tmp_conn, child_id=c1)
    assert len(v1) == 1
    assert v1[0]["child_id"] == c1

    all_visits = store.list_visits(tmp_conn)
    assert len(all_visits) == 2


def test_get_visit_missing_returns_none(tmp_conn):
    assert store.get_visit(tmp_conn, 999) is None


def test_get_conn_creates_parent_directory(tmp_path, monkeypatch):
    db_path = tmp_path / "nested" / "tunas.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    conn = store.get_conn()
    try:
        store.init_db(conn)
        assert db_path.exists()
    finally:
        conn.close()
