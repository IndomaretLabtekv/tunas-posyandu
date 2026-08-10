"""LightGBM decision-support scoring for workflow growth histories."""

from __future__ import annotations

from typing import Any

from api.features import build_model_frame
from api.model import explain_row, predict_scores


def score_growth_history(
    *, child: dict[str, Any], checks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Score the latest check using the same longitudinal features as training."""
    visits = [
        {
            **check,
            "child_id": int(child["child_id"]),
            "child_sex": child["sex"],
        }
        for check in checks
    ]
    frame = build_model_frame(visits)
    if frame.empty:
        raise ValueError("riwayat pengukuran kosong")

    latest_index = frame.index[-1]
    score = float(predict_scores(frame.loc[[latest_index]])[0])
    return {
        "score": round(score, 4),
        "factors": explain_row(frame, latest_index, top_k=3),
    }
