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


class Attribution(BaseModel):
    """Satu faktor penting global dari model."""

    feature: str
    label: str
    value: float | None
    importance: float


class VisitOut(BaseModel):
    """Satu kunjungan pada riwayat anak."""

    visit_id: int
    age_days: int
    mode: str
    length_cm: float | None
    confidence: float
    haz: float | None
    qc_reasons: list[str]
    measured_at: str


class PriorityChild(BaseModel):
    """Satu baris daftar prioritas."""

    rank: int
    child_id: int
    name: str
    sex: str
    age_days: int
    score: float
    risk_label: str
    latest_haz: float | None
    last_visit_days_ago: int
    top_factors: list[Attribution]


class PriorityResponse(BaseModel):
    """Keluaran endpoint /priority."""

    children: list[PriorityChild]
    total: int


class ChildDetail(BaseModel):
    """Keluaran endpoint /children/{id}."""

    child_id: int
    name: str
    sex: str
    age_days: int
    score: float
    risk_label: str
    latest_haz: float | None
    top_factors: list[Attribution]
    visits: list[VisitOut]
    disclaimer: str
