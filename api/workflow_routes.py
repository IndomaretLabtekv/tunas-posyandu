"""Authentication routes shared by the mother and staff workflow APIs."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from api import auth, store
from api.cv_service import process_image, read_upload_limited
from api.dependencies import AuthenticatedUser, assert_child_access, require_roles
from api.workflow import case_priority, case_sort_key, classify_screening, monthly_due
from api.workflow_schemas import (
    AuthResponse,
    AuthUserOut,
    CaseActionOut,
    CaseDetailOut,
    CaseNotesRequest,
    CaseSummaryOut,
    DemoLoginRequest,
    GrowthCheckOut,
    HomeVisitRequest,
    LoginRequest,
    MotherChildCreate,
    MotherChildOut,
    MotherTimelineOut,
    NutritionDecisionRequest,
    ReferralRequest,
    RegisterRequest,
    VerificationRequest,
)
from cv.pipeline import LOW_CONFIDENCE
from tabular.who_lms import haz

router = APIRouter()

DEMO_ACCOUNT_NAMES = {
    "mother": "Ibu Demo",
    "kader": "Kader Demo",
    "nutritionist": "Ahli Gizi Demo",
}


def _user_out(user: dict) -> AuthUserOut:
    return AuthUserOut(
        id=int(user["id"]),
        name=user["name"],
        role=user["role"],
        scope_key=user["scope_key"],
    )


def _find_user(conn, *, name: str, scope_key: str) -> dict | None:
    row = conn.execute(
        select(store.users_table).where(
            store.users_table.c.name == name,
            store.users_table.c.scope_key == scope_key,
        )
    ).fetchone()
    return dict(row._mapping) if row else None


def _response(user: dict) -> AuthResponse:
    return AuthResponse(
        access_token=auth.create_access_token(
            int(user["id"]), user["role"], user["scope_key"]
        ),
        user=_user_out(user),
    )


def _demo_login_enabled() -> bool:
    return os.getenv("ENABLE_DEMO_LOGIN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> AuthResponse:
    """Public registration is intentionally restricted to mothers."""
    conn = store.get_conn()
    try:
        store.init_db(conn)
        if _find_user(conn, name=payload.name, scope_key=payload.scope_key):
            raise HTTPException(status_code=409, detail="akun sudah terdaftar")
        user_id = store.create_user(
            conn,
            name=payload.name,
            role="mother",
            password_hash=auth.hash_password(payload.password),
            scope_key=payload.scope_key,
        )
        user = _find_user(conn, name=payload.name, scope_key=payload.scope_key)
        if user is None or int(user["id"]) != user_id:
            raise HTTPException(status_code=500, detail="akun gagal dibuat")
        return _response(user)
    finally:
        conn.close()


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        user = _find_user(conn, name=payload.name, scope_key=payload.scope_key)
        if user is None or not auth.verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="nama atau password salah",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _response(user)
    finally:
        conn.close()


@router.post("/auth/demo-login", response_model=AuthResponse)
def demo_login(payload: DemoLoginRequest) -> AuthResponse:
    if not _demo_login_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tidak ditemukan")

    scope_key = os.getenv("DEMO_SCOPE_KEY", "posyandu-demo").strip()
    password = os.getenv("DEMO_PASSWORD", "").strip()
    if not scope_key or not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="konfigurasi akun demo belum siap",
        )

    conn = store.get_conn()
    try:
        store.init_db(conn)
        user = _find_user(
            conn,
            name=DEMO_ACCOUNT_NAMES[payload.role],
            scope_key=scope_key,
        )
        if (
            user is None
            or user["role"] != payload.role
            or not auth.verify_password(password, user["password_hash"])
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="akun demo belum siap; jalankan make seed-demo",
            )
        return _response(user)
    finally:
        conn.close()


def _age_days(birth_date: date, measured_on: date) -> int:
    age_days = (measured_on - birth_date).days
    if not 0 <= age_days <= 730:
        raise HTTPException(status_code=422, detail="usia anak harus antara 0 dan 730 hari")
    return age_days


def _child_out(child: dict, *, next_due_at: str | None = None) -> MotherChildOut:
    return MotherChildOut(
        child_id=int(child["child_id"]),
        name=child["name"],
        sex=child["sex"],
        birth_date=child["birth_date"],
        scope_key=child["scope_key"],
        next_due_at=next_due_at,
    )


def _check_out(check: dict) -> GrowthCheckOut:
    source = str(check["source"])
    return GrowthCheckOut(
        growth_check_id=int(check["id"]),
        child_id=int(check["child_id"]),
        source=source,
        age_days=int(check["age_days"]),
        weight_kg=float(check["weight_kg"]),
        length_cm=check.get("length_cm"),
        haz=check.get("haz"),
        mode=check["mode"],
        confidence=float(check["confidence"]),
        low_confidence=float(check["confidence"]) < LOW_CONFIDENCE,
        qc_reasons=check.get("qc_reasons", []),
        screening_status=check["status"],
        verification_status="unverified" if source == "mother" else "verified",
        case_id=check.get("case_id"),
        case_status=check.get("case_status"),
        measured_at=str(check["measured_at"]),
        next_due_at=str(check["next_due_at"]),
    )


@router.post(
    "/mother/children",
    response_model=MotherChildOut,
    status_code=status.HTTP_201_CREATED,
)
def create_mother_child(
    payload: MotherChildCreate,
    user: AuthenticatedUser = Depends(require_roles("mother")),
) -> MotherChildOut:
    _age_days(payload.birth_date, datetime.now(timezone.utc).date())
    conn = store.get_conn()
    try:
        store.init_db(conn)
        child_id = store.create_owned_child(
            conn,
            name=payload.name,
            sex=payload.sex,
            mother_id=user.user_id,
            birth_date=payload.birth_date.isoformat(),
            scope_key=user.scope_key,
        )
        child = store.get_child_profile(conn, child_id)
        if child is None:
            raise HTTPException(status_code=500, detail="profil anak gagal dibuat")
        return _child_out(child)
    finally:
        conn.close()


@router.get("/mother/children", response_model=list[MotherChildOut])
def list_mother_children(
    user: AuthenticatedUser = Depends(require_roles("mother")),
) -> list[MotherChildOut]:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        children = store.list_owned_children(conn, user.user_id)
        output: list[MotherChildOut] = []
        for child in children:
            checks = store.list_growth_checks(conn, int(child["child_id"]))
            next_due_at = str(checks[-1]["next_due_at"]) if checks else None
            output.append(_child_out(child, next_due_at=next_due_at))
        return output
    finally:
        conn.close()


@router.post(
    "/mother/growth-checks",
    response_model=GrowthCheckOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_mother_growth_check(
    child_id: Annotated[int, Form(gt=0)],
    weight_kg: Annotated[float, Form(gt=0)],
    image: Annotated[UploadFile, File()],
    user: AuthenticatedUser = Depends(require_roles("mother")),
) -> GrowthCheckOut:
    measured_at = datetime.now(timezone.utc)
    conn = store.get_conn()
    try:
        store.init_db(conn)
        if not assert_child_access(conn, user, child_id):
            raise HTTPException(status_code=404, detail="anak tidak ditemukan")
        child = store.get_child_profile(conn, child_id)
        if child is None:
            raise HTTPException(status_code=404, detail="anak tidak ditemukan")

        birth_date = date.fromisoformat(str(child["birth_date"]))
        age_days = _age_days(birth_date, measured_at.date())
        contents = read_upload_limited(image.file)
        cv_result = process_image(contents, child["sex"], age_days)
        next_due_at = measured_at + timedelta(days=30)
        screening_status, reason_codes = classify_screening(
            haz=cv_result.get("haz"),
            confidence=cv_result["confidence"],
            mode=cv_result["mode"],
            age_days=age_days,
        )

        check_id = store.record_growth_check(
            conn,
            child_id=child_id,
            submitted_by=user.user_id,
            source="mother",
            age_days=age_days,
            weight_kg=weight_kg,
            length_cm=cv_result["length_cm"],
            haz=cv_result.get("haz"),
            mode=cv_result["mode"],
            confidence=cv_result["confidence"],
            qc_reasons=cv_result["qc_reasons"],
            status=screening_status,
            measured_at=measured_at,
            next_due_at=next_due_at,
        )
        if screening_status == "needs_review":
            store.create_follow_up_case(
                conn,
                child_id=child_id,
                growth_check_id=check_id,
                scope_key=user.scope_key,
                status="needs_review",
                priority=case_priority(reason_codes),
                reason_codes=reason_codes,
            )
        checks = store.list_growth_checks(conn, child_id)
        check = next(item for item in checks if int(item["id"]) == check_id)
        return _check_out(check)
    finally:
        conn.close()


@router.get(
    "/mother/children/{child_id}/timeline",
    response_model=MotherTimelineOut,
)
def get_mother_timeline(
    child_id: int,
    user: AuthenticatedUser = Depends(require_roles("mother")),
) -> MotherTimelineOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        if not assert_child_access(conn, user, child_id):
            raise HTTPException(status_code=404, detail="anak tidak ditemukan")
        child = store.get_child_profile(conn, child_id)
        if child is None:
            raise HTTPException(status_code=404, detail="anak tidak ditemukan")
        checks = store.list_growth_checks(conn, child_id)
        next_due_at = str(checks[-1]["next_due_at"]) if checks else None
        return MotherTimelineOut(
            child=_child_out(child, next_due_at=next_due_at),
            checks=[_check_out(check) for check in checks],
        )
    finally:
        conn.close()


def _as_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _case_summary(case: dict, *, now: datetime) -> CaseSummaryOut:
    submitted_at = _as_datetime(case["growth_measured_at"])
    next_due_at = _as_datetime(case["growth_next_due_at"])
    return CaseSummaryOut(
        case_id=int(case["id"]),
        child_id=int(case["child_id"]),
        child_name=case["child_name"],
        status=case["status"],
        priority=case["priority"],
        reason_codes=case.get("reason_codes", []),
        source="mother",
        screening_status=case["growth_status"],
        age_days=int(case["growth_age_days"]),
        weight_kg=float(case["growth_weight_kg"]),
        length_cm=case.get("growth_length_cm"),
        haz=case.get("growth_haz"),
        mode=case["growth_mode"],
        confidence=float(case["growth_confidence"]),
        submitted_at=submitted_at.isoformat(),
        next_due_at=next_due_at.isoformat(),
        days_since_submission=max(0, (now - submitted_at).days),
        overdue=monthly_due(last_check_at=submitted_at, now=now),
    )


def _case_action_out(action: dict) -> CaseActionOut:
    details = action.get("details")
    notes = details.get("notes", "") if details else str(action.get("notes") or "")
    return CaseActionOut(
        action_id=int(action["id"]),
        actor_id=int(action["actor_id"]),
        action_type=action["action_type"],
        notes=notes,
        details=details,
        created_at=str(action["created_at"]),
    )


def _case_detail(conn, case: dict, *, now: datetime) -> CaseDetailOut:
    return CaseDetailOut(
        case=_case_summary(case, now=now),
        checks=[
            _check_out(check)
            for check in store.list_growth_checks(conn, int(case["child_id"]))
        ],
        actions=[
            _case_action_out(action)
            for action in store.list_case_actions(conn, int(case["id"]))
        ],
    )


def _require_case(conn, user: AuthenticatedUser, case_id: int) -> dict:
    case = store.get_scoped_case(conn, case_id=case_id, scope_key=user.scope_key)
    if case is None:
        raise HTTPException(status_code=404, detail="kasus tidak ditemukan")
    return case


def _transition(
    conn,
    *,
    case_id: int,
    new_status: str,
    actor_id: int,
    notes: str = "",
) -> None:
    try:
        store.transition_case(
            conn,
            case_id=case_id,
            new_status=new_status,
            actor_id=actor_id,
            notes=notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _list_role_cases(user: AuthenticatedUser) -> list[CaseSummaryOut]:
    now = datetime.now(timezone.utc)
    conn = store.get_conn()
    try:
        store.init_db(conn)
        summaries = [
            _case_summary(case, now=now)
            for case in store.list_cases(conn, scope_key=user.scope_key)
        ]
        summaries.sort(
            key=lambda item: case_sort_key(
                {
                    "id": item.case_id,
                    "priority": item.priority,
                    "overdue": item.overdue,
                    "created_at": item.submitted_at,
                }
            )
        )
        return summaries
    finally:
        conn.close()


@router.get("/kader/cases", response_model=list[CaseSummaryOut])
def list_kader_cases(
    user: AuthenticatedUser = Depends(require_roles("kader")),
) -> list[CaseSummaryOut]:
    return _list_role_cases(user)


@router.get("/kader/cases/{case_id}", response_model=CaseDetailOut)
def get_kader_case(
    case_id: int,
    user: AuthenticatedUser = Depends(require_roles("kader")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()


@router.post("/kader/cases/{case_id}/assign", response_model=CaseDetailOut)
def assign_kader_case(
    case_id: int,
    payload: CaseNotesRequest,
    user: AuthenticatedUser = Depends(require_roles("kader")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        _require_case(conn, user, case_id)
        _transition(
            conn,
            case_id=case_id,
            new_status="assigned",
            actor_id=user.user_id,
            notes=payload.notes,
        )
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()


@router.post("/kader/cases/{case_id}/home-visit", response_model=CaseDetailOut)
def record_home_visit(
    case_id: int,
    payload: HomeVisitRequest,
    user: AuthenticatedUser = Depends(require_roles("kader")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        _require_case(conn, user, case_id)
        details = json.dumps(
            {
                "notes": payload.notes,
                "weight_kg": payload.weight_kg,
                "length_cm": payload.length_cm,
            }
        )
        _transition(
            conn,
            case_id=case_id,
            new_status="home_visit",
            actor_id=user.user_id,
            notes=details,
        )
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()


@router.post("/kader/cases/{case_id}/verify", response_model=CaseDetailOut)
def verify_kader_case(
    case_id: int,
    payload: VerificationRequest,
    user: AuthenticatedUser = Depends(require_roles("kader")),
) -> CaseDetailOut:
    now = datetime.now(timezone.utc)
    conn = store.get_conn()
    try:
        store.init_db(conn)
        case = _require_case(conn, user, case_id)
        if case["status"] != "home_visit":
            raise HTTPException(status_code=409, detail="kasus harus berada pada home_visit")
        child = store.get_child_profile(conn, int(case["child_id"]))
        if child is None:
            raise HTTPException(status_code=404, detail="anak tidak ditemukan")
        age_days = _age_days(date.fromisoformat(str(child["birth_date"])), now.date())
        verified_haz = haz(payload.length_cm, child["sex"], age_days)
        store.record_growth_check(
            conn,
            child_id=int(case["child_id"]),
            submitted_by=user.user_id,
            source="kader",
            age_days=age_days,
            weight_kg=payload.weight_kg,
            length_cm=payload.length_cm,
            haz=verified_haz,
            mode="manual_verification",
            confidence=1.0,
            qc_reasons=[],
            status="needs_review" if payload.outcome == "verified_risk" else "normal",
            measured_at=now,
            next_due_at=now + timedelta(days=30),
        )
        _transition(
            conn,
            case_id=case_id,
            new_status=payload.outcome,
            actor_id=user.user_id,
            notes=json.dumps(
                {
                    "notes": payload.notes,
                    "weight_kg": payload.weight_kg,
                    "length_cm": payload.length_cm,
                    "haz": verified_haz,
                }
            ),
        )
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=now,
        )
    finally:
        conn.close()


@router.get("/nutritionist/cases", response_model=list[CaseSummaryOut])
def list_nutritionist_cases(
    user: AuthenticatedUser = Depends(require_roles("nutritionist")),
) -> list[CaseSummaryOut]:
    return _list_role_cases(user)


@router.get("/nutritionist/cases/{case_id}", response_model=CaseDetailOut)
def get_nutritionist_case(
    case_id: int,
    user: AuthenticatedUser = Depends(require_roles("nutritionist")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()


@router.post("/nutritionist/cases/{case_id}/decision", response_model=CaseDetailOut)
def record_nutritionist_decision(
    case_id: int,
    payload: NutritionDecisionRequest,
    user: AuthenticatedUser = Depends(require_roles("nutritionist")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        case = _require_case(conn, user, case_id)
        if case["status"] not in {"verified_risk", "referred"}:
            raise HTTPException(status_code=409, detail="kasus belum siap diputuskan")
        details = json.dumps({"action": payload.action, "notes": payload.notes})
        if payload.resolve:
            _transition(
                conn,
                case_id=case_id,
                new_status="resolved",
                actor_id=user.user_id,
                notes=details,
            )
        else:
            store.record_case_action(
                conn,
                case_id=case_id,
                actor_id=user.user_id,
                action_type="nutrition_decision",
                notes=details,
            )
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()


@router.post("/nutritionist/cases/{case_id}/referral", response_model=CaseDetailOut)
def refer_nutritionist_case(
    case_id: int,
    payload: ReferralRequest,
    user: AuthenticatedUser = Depends(require_roles("nutritionist")),
) -> CaseDetailOut:
    conn = store.get_conn()
    try:
        store.init_db(conn)
        _require_case(conn, user, case_id)
        _transition(
            conn,
            case_id=case_id,
            new_status="referred",
            actor_id=user.user_id,
            notes=json.dumps(
                {"destination": payload.destination, "notes": payload.notes}
            ),
        )
        return _case_detail(
            conn,
            _require_case(conn, user, case_id),
            now=datetime.now(timezone.utc),
        )
    finally:
        conn.close()
