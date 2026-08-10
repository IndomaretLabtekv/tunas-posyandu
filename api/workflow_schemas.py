"""Pydantic contracts for workflow authentication endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthUserOut(BaseModel):
    id: int
    name: str
    role: Literal["mother", "kader", "nutritionist"]
    scope_key: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    scope_key: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(str_strip_whitespace=True)


class LoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)
    scope_key: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(str_strip_whitespace=True)


class DemoLoginRequest(BaseModel):
    role: Literal["mother", "kader", "nutritionist"]


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AuthUserOut


class MotherChildCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sex: Literal["M", "F"]
    birth_date: date

    model_config = ConfigDict(str_strip_whitespace=True)


class MotherChildOut(BaseModel):
    child_id: int
    name: str
    sex: Literal["M", "F"]
    birth_date: date
    scope_key: str
    next_due_at: str | None = None


class GrowthCheckOut(BaseModel):
    growth_check_id: int
    child_id: int
    source: str
    age_days: int
    weight_kg: float
    length_cm: float | None
    haz: float | None
    mode: str
    confidence: float
    low_confidence: bool
    qc_reasons: list[str]
    screening_status: Literal["normal", "needs_review"]
    verification_status: Literal["unverified", "verified"]
    case_id: int | None = None
    case_status: str | None = None
    measured_at: str
    next_due_at: str


class MotherTimelineOut(BaseModel):
    child: MotherChildOut
    checks: list[GrowthCheckOut]


class CaseSummaryOut(BaseModel):
    case_id: int
    child_id: int
    child_name: str
    status: str
    priority: str
    reason_codes: list[str]
    source: str
    screening_status: str
    age_days: int
    weight_kg: float
    length_cm: float | None
    haz: float | None
    mode: str
    confidence: float
    submitted_at: str
    next_due_at: str
    days_since_submission: int
    overdue: bool


class CaseActionOut(BaseModel):
    action_id: int
    actor_id: int
    action_type: str
    notes: str
    details: dict | None = None
    created_at: str


class CaseDetailOut(BaseModel):
    case: CaseSummaryOut
    checks: list[GrowthCheckOut]
    actions: list[CaseActionOut]


class CaseNotesRequest(BaseModel):
    notes: str = Field(default="", max_length=2000)


class HomeVisitRequest(BaseModel):
    notes: str = Field(default="", max_length=2000)
    weight_kg: float | None = Field(default=None, gt=0)
    length_cm: float | None = Field(default=None, gt=0)


class VerificationRequest(BaseModel):
    weight_kg: float = Field(gt=0)
    length_cm: float = Field(gt=0)
    outcome: Literal["verified_risk", "resolved"]
    notes: str = Field(default="", max_length=2000)


class NutritionDecisionRequest(BaseModel):
    action: str = Field(min_length=1, max_length=240)
    notes: str = Field(default="", max_length=2000)
    resolve: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class ReferralRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=240)
    notes: str = Field(default="", max_length=2000)

    model_config = ConfigDict(str_strip_whitespace=True)
