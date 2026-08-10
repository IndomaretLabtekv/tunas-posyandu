"""Tests for GET /priority and GET /children/{id}."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import store
from api.main import app


@pytest.fixture
def client(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "tunas.db"
        monkeypatch.setenv("DB_PATH", str(db_path))
        monkeypatch.setenv("MODEL_PATH", "results/tabular/final/primary_model.joblib")
        # Clear model cache so each test uses the current MODEL_PATH.
        from api.model import _load_artifact_cached
        _load_artifact_cached.cache_clear()
        yield TestClient(app)


def _seed_child_and_visits(client: TestClient):
    """Create two children with visits directly via the SQLite store.

    History is built to roughly match the distribution the model was trained on
    (children ~600 days old with ~15 visits) so scores are not all collapsed to
    the base rate.
    """
    conn = store.get_conn()
    try:
        store.init_db(conn)
        c1 = store.create_child(conn, name="Ani", sex="F")
        c2 = store.create_child(conn, name="Budi", sex="M")
        start_age = 120
        n_visits = 15
        gap_days = 30
        for i in range(n_visits):
            age = start_age + i * gap_days
            haz_c1 = 0.0 - i * 0.18
            length_c1 = 60.0 + i * 1.5
            store.record_visit(
                conn,
                child_id=c1,
                age_days=age,
                mode="measurement",
                length_cm=length_c1,
                confidence=0.95,
                haz=haz_c1,
                qc_reasons=[],
                low_confidence=False,
            )
            haz_c2 = -0.3
            length_c2 = 60.0 + i * 2.0
            store.record_visit(
                conn,
                child_id=c2,
                age_days=age,
                mode="measurement",
                length_cm=length_c2,
                confidence=0.95,
                haz=haz_c2,
                qc_reasons=[],
                low_confidence=False,
            )
        return c1, c2
    finally:
        conn.close()


def test_priority_returns_ranked_children(client):
    _seed_child_and_visits(client)
    resp = client.get("/priority")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["children"]) == 2
    ranks = [c["rank"] for c in data["children"]]
    assert ranks == [1, 2]
    assert data["children"][0]["name"] == "Ani"
    assert data["children"][1]["name"] == "Budi"
    for c in data["children"]:
        assert "score" in c
        assert 0.0 <= c["score"] <= 1.0
        assert c["risk_label"] in {"Rendah", "Sedang", "Tinggi"}
        assert "latest_haz" in c
        assert "last_visit_days_ago" in c
        assert len(c["top_factors"]) > 0


def test_priority_empty_database(client):
    resp = client.get("/priority")
    assert resp.status_code == 200
    assert resp.json() == {"children": [], "total": 0}


def test_child_detail_returns_history_and_shap(client):
    c1, _ = _seed_child_and_visits(client)
    resp = client.get(f"/children/{c1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["child_id"] == c1
    assert data["name"] == "Ani"
    assert data["sex"] == "F"
    assert data["disclaimer"]
    assert len(data["visits"]) == 15
    assert data["top_factors"]


def test_child_detail_not_found(client):
    resp = client.get("/children/9999")
    assert resp.status_code == 404
