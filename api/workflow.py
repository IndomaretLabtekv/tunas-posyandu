"""Pure screening, cadence, and case-ordering rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from cv.pipeline import LOW_CONFIDENCE

REVIEW_PRIORITIES = {"urgent", "review"}


def classify_screening(
    *,
    haz: float | None,
    confidence: float,
    mode: str,
    age_days: int,
) -> tuple[str, list[str]]:
    """Classify a screening signal without making a clinical diagnosis."""
    if not 0 <= age_days <= 730:
        raise ValueError("age_days harus antara 0 dan 730")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence harus antara 0 dan 1")

    reasons: list[str] = []
    if mode == "rejected":
        reasons.append("cv_rejected")
    if confidence < LOW_CONFIDENCE:
        reasons.append("low_confidence")
    if mode == "estimate":
        reasons.append("estimate_mode")
    if haz is not None and haz < -2.0:
        reasons.append("growth_signal")

    return ("needs_review", reasons) if reasons else ("normal", [])


def monthly_due(*, last_check_at: datetime, now: datetime) -> bool:
    """Return whether at least 30 days have elapsed since the last check."""
    if last_check_at.tzinfo is None:
        last_check_at = last_check_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now >= last_check_at + timedelta(days=30)


def case_sort_key(case: dict[str, Any]) -> tuple[int, int, datetime, int]:
    """Order urgent, then overdue, then oldest cases with an ID tie-break."""
    priority = str(case.get("priority", "review"))
    urgent_rank = 0 if priority == "urgent" else 1
    overdue = bool(case.get("overdue", case.get("is_overdue", False)))
    overdue_rank = 0 if overdue else 1

    created_at = case.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if not isinstance(created_at, datetime):
        created_at = datetime.max.replace(tzinfo=timezone.utc)
    elif created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return urgent_rank, overdue_rank, created_at, int(case.get("id", 0))


def case_priority(reason_codes: list[str]) -> str:
    """Escalate rejected or adverse growth signals ahead of routine review."""
    return "urgent" if {"cv_rejected", "growth_signal"} & set(reason_codes) else "review"
