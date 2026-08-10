"""Demo seed should populate every role dashboard without duplication."""

from collections import Counter

from sqlalchemy import func, select

from api import store
from api.dependencies import AuthenticatedUser
from api.workflow_routes import _list_role_cases
from scripts.seed_demo_users import main


def test_demo_seed_populates_workflow_once(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.setenv("DEMO_PASSWORD", "demo-password")
    monkeypatch.setenv("DEMO_SCOPE_KEY", "posyandu-demo")

    main()
    main()

    conn = store.get_conn()
    try:
        assert conn.scalar(select(func.count()).select_from(store.users_table)) == 4
        assert conn.scalar(select(func.count()).select_from(store.child_profiles_table)) == 12
        assert conn.scalar(select(func.count()).select_from(store.growth_checks_table)) == 28
        mother_id = conn.scalar(
            select(store.users_table.c.id).where(store.users_table.c.name == "Ibu Demo")
        )
        community_mother_id = conn.scalar(
            select(store.users_table.c.id).where(
                store.users_table.c.name == "Ibu Komunitas Demo"
            )
        )
        assert mother_id is not None
        assert community_mother_id is not None
        assert [child["name"] for child in store.list_owned_children(conn, mother_id)] == [
            "Bayi Demo",
            "Alya",
        ]
        assert conn.scalar(
            select(func.count())
            .select_from(store.child_profiles_table)
            .where(store.child_profiles_table.c.mother_id == community_mother_id)
        ) == 10
        kader_id = conn.scalar(
            select(store.users_table.c.id).where(store.users_table.c.name == "Kader Demo")
        )
        cases = store.list_cases(conn, scope_key="posyandu-demo")
    finally:
        conn.close()

    assert Counter(case["status"] for case in cases) == {
        "needs_review": 2,
        "assigned": 2,
        "home_visit": 2,
        "verified_risk": 2,
        "referred": 1,
        "resolved": 1,
    }

    summaries = _list_role_cases(
        AuthenticatedUser(kader_id, "kader", "posyandu-demo")
    )
    scores = [summary.risk_score for summary in summaries]
    assert all(score is not None and 0.0 <= score <= 1.0 for score in scores)
    assert scores == sorted(scores, reverse=True)
    assert all(summary.risk_factors for summary in summaries)
