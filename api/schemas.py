"""Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class MeasurementResponse(BaseModel):
    """Keluaran endpoint /measurements."""

    mode: str
    length_cm: float | None
    confidence: float
    low_confidence: bool
    qc_reasons: list[str]
    haz: float | None
    child_id: int
    visit_id: int
