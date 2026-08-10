"""Tests for additive mother-kader-nutritionist workflow storage."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from api import store


@pytest.fixture
def workflow_conn(tmp_path, monkeypatch):
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    conn = store.get_conn()
    store.init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_init_db_creates_workflow_tables(workflow_conn):
    rows = workflow_conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    tables = {row[0] for row in rows}

    assert {
        "users",
        "child_profiles",
        "growth_checks",
        "follow_up_cases",
        "case_actions",
    } <= tables


def test_workflow_records_preserve_ownership_and_provenance(workflow_conn):
    mother_id = store.create_user(
        workflow_conn,
        name="Ibu Ani",
        role="mother",
        password_hash="hashed-password",
        scope_key="puskesmas-a",
    )
    child_id = store.create_child(workflow_conn, name="Budi", sex="M")
    store.create_child_profile(
        workflow_conn,
        child_id=child_id,
        mother_id=mother_id,
        birth_date="2025-01-01",
        scope_key="puskesmas-a",
    )

    measured_at = datetime(2025, 7, 1, tzinfo=timezone.utc).isoformat()
    check_id = store.record_growth_check(
        workflow_conn,
        child_id=child_id,
        submitted_by=mother_id,
        source="mother_app",
        age_days=181,
        weight_kg=7.2,
        length_cm=66.1,
        haz=-2.1,
        mode="measurement",
        confidence=0.88,
        qc_reasons=["low light"],
        status="needs_review",
        measured_at=measured_at,
        next_due_at="2025-07-31T00:00:00+00:00",
    )
    case_id = store.create_follow_up_case(
        workflow_conn,
        child_id=child_id,
        growth_check_id=check_id,
        scope_key="puskesmas-a",
        status="needs_review",
        priority="urgent",
        reason_codes=["growth_signal", "low_confidence"],
    )
    action_id = store.record_case_action(
        workflow_conn,
        case_id=case_id,
        actor_id=mother_id,
        action_type="submitted",
        notes="Pengukuran dikirim dari rumah.",
    )

    assert check_id > 0
    assert action_id > 0
    cases = store.list_cases(workflow_conn, scope_key="puskesmas-a")
    assert len(cases) == 1
    assert cases[0]["id"] == case_id
    assert cases[0]["child_id"] == child_id
    assert cases[0]["growth_check_id"] == check_id
    assert cases[0]["priority"] == "urgent"
    assert cases[0]["reason_codes"] == ["growth_signal", "low_confidence"]

    check = workflow_conn.execute(
        select(store.growth_checks_table).where(store.growth_checks_table.c.id == check_id)
    ).mappings().one()
    assert check["submitted_by"] == mother_id
    assert check["source"] == "mother_app"
    assert check["weight_kg"] == pytest.approx(7.2)
    assert check["qc_reasons"] == '["low light"]'


def test_case_transitions_follow_workflow_and_reject_invalid_state(workflow_conn):
    mother_id = store.create_user(
        workflow_conn,
        name="Ibu Citra",
        role="mother",
        password_hash="hashed-password",
        scope_key="puskesmas-b",
    )
    kader_id = store.create_user(
        workflow_conn,
        name="Kader B",
        role="kader",
        password_hash="hashed-password",
        scope_key="puskesmas-b",
    )
    child_id = store.create_child(workflow_conn, name="Dito", sex="M")
    store.create_child_profile(
        workflow_conn,
        child_id=child_id,
        mother_id=mother_id,
        birth_date="2025-01-01",
        scope_key="puskesmas-b",
    )
    check_id = store.record_growth_check(
        workflow_conn,
        child_id=child_id,
        submitted_by=mother_id,
        source="mother_app",
        age_days=180,
        weight_kg=7.0,
        length_cm=None,
        haz=None,
        mode="rejected",
        confidence=0.0,
        qc_reasons=["gagal membaca citra"],
        status="needs_review",
        measured_at="2025-07-01T00:00:00+00:00",
        next_due_at="2025-07-31T00:00:00+00:00",
    )
    case_id = store.create_follow_up_case(
        workflow_conn,
        child_id=child_id,
        growth_check_id=check_id,
        scope_key="puskesmas-b",
        status="needs_review",
        priority="review",
        reason_codes=["cv_rejected"],
    )

    for status in ("assigned", "home_visit", "verified_risk", "referred", "resolved"):
        store.transition_case(
            workflow_conn,
            case_id=case_id,
            new_status=status,
            actor_id=kader_id,
            notes=f"transition to {status}",
        )

    cases = store.list_cases(workflow_conn, scope_key="puskesmas-b")
    assert cases[0]["status"] == "resolved"

    with pytest.raises(ValueError, match="transisi kasus tidak diizinkan"):
        store.transition_case(
            workflow_conn,
            case_id=case_id,
            new_status="home_visit",
            actor_id=kader_id,
        )
