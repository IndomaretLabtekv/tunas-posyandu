# Tunas 0–23 Month Growth Screening Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Tunas into a periodic 0–23 month workflow where a mother submits a CV-assisted growth check, a kader performs field follow-up, and an ahli gizi/Puskesmas reviews verified cases and records the next action.

**Architecture:** Keep the existing FastAPI, SQLAlchemy, PostgreSQL/SQLite, Next.js, OpenCV CV pipeline, and WHO LMS components. Add an additive workflow domain (`users`, child ownership, growth checks, follow-up cases, and case actions) beside the legacy `children`/`visits` contract, then expose role-scoped `/api/*` endpoints. The first demo reuses the existing Python CV through the API; the uploaded image is processed temporarily and the stored record contains only structured results. A true on-device CV port is a separate project because the current CV implementation is Python/OpenCV server-side.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy Core, PostgreSQL/SQLite, current OpenCV pipeline, WHO LMS tables, Next.js 15, React 19, TypeScript, Tailwind CSS, PyJWT, pwdlib/Argon2.

## Global Constraints

- Supported age is inclusive `0 <= age_days <= 730`; the 24–59 month standing-height protocol is out of scope.
- The CV output is a screening signal, never an automatic diagnosis of stunting.
- Home submissions are `unverified` until a kader or health worker confirms the measurement.
- The mother owns only her linked children; kader and ahli gizi see only their assigned `scope_key`.
- Monthly check-in is the product cadence; overdue status is computed from `last_check_at + 30 days` without a background scheduler.
- Existing `/measurements`, `/priority`, and `/children/{id}` endpoints remain working during migration.
- Food logging, speech milestone analysis, Claude recommendations, push notifications, and 24–59 month standing-height CV are not part of this plan.
- No new UI dependency or chart library is added; reuse the current Next.js and Tailwind setup.
- Every new state transition and trust-boundary validation gets an automated test.

## Current Code Boundaries

- `api/routes.py:276` receives the current image upload and calls the CV pipeline.
- `api/store.py:35-51` owns the existing `children` and `visits` tables.
- `api/model.py` and `api/features.py` expose the current longitudinal growth-risk model.
- `web/src/app/kader/page.tsx` is currently the measurement form, not a mother-facing workflow.
- `web/src/app/petugas/page.tsx` and `web/src/app/petugas/[id]/page.tsx` are the current priority list and child detail views.
- `api/main.py` currently includes one unprefixed router and has no authentication middleware.

## Target Flow

```text
Mother app/PWA
  └─ monthly photo + weight + child context
       ↓
  CV result + confidence + HAZ + screening status
       ↓
Kader queue
  └─ contact/home visit/repeat measurement/record notes
       ↓ verified
Ahli gizi/Puskesmas dashboard
  └─ review timeline → nutrition action → referral or resolve
```

State transitions:

```text
submitted → normal
submitted → needs_review → assigned → home_visit → verified_risk
verified_risk → referred → resolved
needs_review → resolved       # reviewer records a non-risk explanation
```

`needs_review` means the result needs human verification. It must not be rendered as `stunting`.

## File Map

### Create

- `api/auth.py` — password hashing and JWT encode/decode.
- `api/dependencies.py` — authenticated-user and role/scope dependencies.
- `api/cv_service.py` — shared public wrapper around the existing CV processing path.
- `api/workflow.py` — screening classification, monthly due calculation, and case priority.
- `api/workflow_routes.py` — `/api/auth`, mother, kader, and ahli gizi endpoints.
- `api/workflow_schemas.py` — request/response models for the new contract.
- `tests/test_workflow_store.py` — additive storage and state-transition tests.
- `tests/test_workflow_api.py` — role, ownership, submission, and case API tests.
- `tests/test_workflow_priority.py` — pure classification and priority tests.
- `scripts/seed_demo_users.py` — deterministic mother, kader, and nutritionist accounts for the demo.
- `web/src/lib/api.ts` — authenticated fetch wrapper and typed API calls.
- `web/src/lib/types.ts` — shared frontend contract types.
- `web/src/app/login/page.tsx` — shared login screen for all roles.
- `web/src/app/ibu/page.tsx` — mother monthly check-in and result screen.
- `web/src/app/ibu/children/[id]/page.tsx` — mother timeline and next-due status.
- `web/src/app/kader/[caseId]/page.tsx` — kader case detail and field-action form.
- `web/src/app/ahli-gizi/page.tsx` — nutritionist/Puskesmas case dashboard.
- `web/src/app/ahli-gizi/[caseId]/page.tsx` — verified timeline, decision, and referral form.

### Modify

- `api/store.py` — add workflow tables and functions without removing legacy tables.
- `api/schemas.py` — keep legacy models; import or re-export new models only if needed by shared code.
- `api/routes.py` — call `api.cv_service.process_image` instead of owning a private duplicate.
- `api/main.py` — include the new router and configure CORS/auth settings.
- `requirements.txt` — add only `PyJWT` and `pwdlib[argon2]` for secure authentication.
- `.env.example` — add `JWT_SECRET`, `JWT_ACCESS_MINUTES`, and demo scope settings.
- `docker-compose.yml` — pass the JWT settings to the backend.
- `web/src/app/page.tsx` — present Mother, Kader, and Ahli Gizi/Puskesmas roles.
- `web/src/app/kader/page.tsx` — replace the upload-only screen with the kader case queue.
- `web/src/app/petugas/page.tsx` — redirect or preserve as a compatibility link to `/ahli-gizi`.
- `web/src/app/petugas/[id]/page.tsx` — redirect old child detail links to the new case/child detail route.
- `docs/NEW-FLOW.md` — record the 0–23 month scope, verification states, and role responsibilities.
- `docs/DECISIONS.md` — record server-side CV demo boundary and the explicit non-diagnostic claim.
- `docs/RESPONSIBLE_AI.md` — document mother-submitted screening, human verification, retention, and referral limits.
- `README.md` — document the three roles, demo accounts, monthly flow, and verified setup commands.
- `tests/test_smoke.py` — replace the empty placeholder with the new vertical-slice smoke test.

---

### Task 1: Freeze the 0–23 Month Product Contract

**Files:**
- Modify: `docs/NEW-FLOW.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/RESPONSIBLE_AI.md`
- Test: none; review-only contract gate

**Interfaces:**
- Produces the canonical role names: `mother`, `kader`, `nutritionist`.
- Produces the canonical case statuses and the `unverified`/`verified` measurement distinction used by every later task.

- [ ] **Step 1: Add the supported-age contract.** State that this implementation supports `0 <= age_days <= 730`, uses recumbent length, and does not implement standing height.
- [ ] **Step 2: Add the screening disclaimer.** Replace any automatic stunting wording with `indikasi gangguan pertumbuhan — perlu verifikasi`.
- [ ] **Step 3: Add the role responsibilities.** Mother submits data, kader handles operational follow-up, and nutritionist/Puskesmas reviews and decides intervention/referral.
- [ ] **Step 4: Add the state machine.** Document every allowed transition from `submitted` to `resolved`.
- [ ] **Step 5: Review the document for contradictions.** Search for `diagnosis`, `confirmed stunting`, `0–5`, and `on-device` claims that are not supported by this plan.
- [ ] **Step 6: Commit the contract separately.**

Run: `rtk git diff --check`

Expected: no whitespace errors and no code files changed.

---

### Task 2: Add Additive Workflow Storage

**Files:**
- Modify: `api/store.py`
- Create: `tests/test_workflow_store.py`

**Interfaces:**
- `create_user(conn, *, name: str, role: str, password_hash: str, scope_key: str) -> int`
- `create_child_profile(conn, *, child_id: int, mother_id: int, birth_date: str, scope_key: str) -> None`
- `record_growth_check(conn, *, child_id: int, submitted_by: int, source: str, age_days: int, weight_kg: float, length_cm: float | None, haz: float | None, mode: str, confidence: float, qc_reasons: list[str], status: str, measured_at: str, next_due_at: str) -> int`
- `create_follow_up_case(conn, *, child_id: int, growth_check_id: int, scope_key: str, status: str, priority: str, reason_codes: list[str]) -> int`
- `list_cases(conn, *, scope_key: str, status: str | None = None) -> list[dict[str, Any]]`
- `transition_case(conn, *, case_id: int, new_status: str, actor_id: int, notes: str = "") -> None`
- `record_case_action(conn, *, case_id: int, actor_id: int, action_type: str, notes: str) -> int`

- [ ] **Step 1: Write failing round-trip tests.** Cover users, child ownership, growth checks, cases, actions, and JSON reason-code persistence.
- [ ] **Step 2: Write failing transition tests.** Allow only the documented transitions and reject `resolved → home_visit` or an unknown status with `ValueError`.
- [ ] **Step 3: Add additive SQLAlchemy tables.** Use `users`, `child_profiles`, `growth_checks`, `follow_up_cases`, and `case_actions`; retain `children` and `visits` unchanged.
- [ ] **Step 4: Add store functions.** Commit each insert/update explicitly, matching the existing SQLAlchemy Core style.
- [ ] **Step 5: Run the storage tests.**

Run: `rtk proxy pytest -q tests/test_workflow_store.py`

Expected: all new storage and transition tests pass.

- [ ] **Step 6: Commit the storage slice.**

---

### Task 3: Add Secure Authentication and Scope Guards

**Files:**
- Create: `api/auth.py`
- Create: `api/dependencies.py`
- Create: `api/workflow_schemas.py`
- Create: `api/workflow_routes.py`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Create: `tests/test_workflow_api.py`

**Interfaces:**
- `hash_password(password: str) -> str`
- `verify_password(password: str, password_hash: str) -> bool`
- `create_access_token(user_id: int, role: str, scope_key: str) -> str`
- `get_current_user(request: Request) -> AuthenticatedUser`
- `require_roles(*roles: str) -> Callable`

- [ ] **Step 1: Add the dependency pins.** Add `PyJWT` and `pwdlib[argon2]`; do not implement password hashing with a homemade hash.
- [ ] **Step 2: Write failing auth tests.** Cover valid login, wrong password, expired token, malformed token, and role mismatch.
- [ ] **Step 3: Implement password hashing and JWT claims.** Include `sub`, `role`, `scope_key`, and `exp`; read the secret from `JWT_SECRET`.
- [ ] **Step 4: Implement role and scope dependencies.** A mother may access only linked children; kader/nutritionist queries must use the authenticated `scope_key`.
- [ ] **Step 5: Add `POST /api/auth/register` for mothers and `POST /api/auth/login` to `api/workflow_routes.py`.** Staff roles are created by the demo seed script, not public registration.
- [ ] **Step 6: Run auth tests.**

Run: `rtk proxy pytest -q tests/test_workflow_api.py -k auth`

Expected: invalid credentials return `401`; valid credentials return a bearer token; role/scope violations return `403`.

- [ ] **Step 7: Commit the auth slice.**

---

### Task 4: Extract the Shared CV Service and Add Mother Growth Submission

**Files:**
- Create: `api/cv_service.py`
- Modify: `api/workflow_routes.py`
- Modify: `api/routes.py`
- Modify: `api/main.py`
- Modify: `api/workflow_schemas.py`
- Modify: `tests/test_api_measurements.py`
- Modify: `tests/test_workflow_api.py`

**Interfaces:**
- `process_image(contents: bytes, sex: str, age_days: int) -> dict[str, Any]`
- `POST /api/mother/children`
- `GET /api/mother/children`
- `POST /api/mother/growth-checks`
- `GET /api/mother/children/{child_id}/timeline`

- [ ] **Step 1: Write the shared-service regression test.** Verify that the legacy `/measurements` endpoint and the new growth endpoint return the same CV result for the same synthetic image.
- [ ] **Step 2: Move `_process_image` into `api/cv_service.py`.** Preserve `ColorSegmenter`, `ImageQC`, temporary-file cleanup, and the existing result keys.
- [ ] **Step 3: Update the legacy route to import the shared service.** Do not change its response contract.
- [ ] **Step 4: Write the mother endpoint tests.** Cover child creation, mother ownership, age `0`, age `730`, age `731` rejection, weight validation, and a successful image submission.
- [ ] **Step 5: Implement child registration.** Store the existing child row, its `child_profiles` row, and the mother link in one transaction.
- [ ] **Step 6: Implement the growth submission.** Derive age from the child profile, call `process_image`, store only structured output, and calculate `next_due_at = measured_at + 30 days`. Leave case creation to Task 5, which owns screening classification.
- [ ] **Step 7: Implement the mother timeline.** Return measurement source, confidence, verification status, case status, and next due date; reject another mother’s child with `404`.
- [ ] **Step 8: Run the focused API tests.**

Run: `rtk proxy pytest -q tests/test_api_measurements.py tests/test_workflow_api.py -k 'mother or measurement'`

Expected: legacy tests remain green and the new mother flow creates one child, one growth check, and zero or one case without storing image bytes.

- [ ] **Step 9: Commit the mother submission slice.**

---

### Task 5: Add Screening Classification and Case Priority

**Files:**
- Create: `api/workflow.py`
- Create: `tests/test_workflow_priority.py`
- Modify: `api/workflow_routes.py`

**Interfaces:**
- `classify_screening(*, haz: float | None, confidence: float, mode: str, age_days: int) -> tuple[str, list[str]]`
- `monthly_due(*, last_check_at: datetime, now: datetime) -> bool`
- `case_sort_key(case: dict[str, Any]) -> tuple[int, int, datetime]`

- [ ] **Step 1: Write pure classification tests.** Assert that rejected/low-confidence/estimate results produce `needs_review`, that a low HAZ produces `needs_review`, and that a valid high-confidence result produces `normal`.
- [ ] **Step 2: Implement reason codes.** Use stable values such as `cv_rejected`, `low_confidence`, `estimate_mode`, and `growth_signal`; never emit `stunting_confirmed`.
- [ ] **Step 3: Implement monthly due calculation.** Use a 30-day interval and make the function deterministic with an injected `now`.
- [ ] **Step 4: Implement deterministic case ordering.** Sort urgent review first, then overdue cases, then oldest unresolved case; tie-break with case ID.
- [ ] **Step 5: Wire classification into growth submission.** The endpoint creates a case only for `needs_review`; normal checks remain visible on the mother timeline.
- [ ] **Step 6: Run pure workflow tests.**

Run: `rtk proxy pytest -q tests/test_workflow_priority.py`

Expected: all classifications, due dates, and tie-breaks are deterministic.

- [ ] **Step 7: Commit the workflow rules slice.**

---

### Task 6: Add Kader Follow-Up and Ahli Gizi/Puskesmas Review APIs

**Files:**
- Modify: `api/workflow_routes.py`
- Modify: `api/workflow_schemas.py`
- Modify: `tests/test_workflow_api.py`

**Interfaces:**
- `GET /api/kader/cases`
- `GET /api/kader/cases/{case_id}`
- `POST /api/kader/cases/{case_id}/assign`
- `POST /api/kader/cases/{case_id}/home-visit`
- `POST /api/kader/cases/{case_id}/verify`
- `GET /api/nutritionist/cases`
- `GET /api/nutritionist/cases/{case_id}`
- `POST /api/nutritionist/cases/{case_id}/decision`
- `POST /api/nutritionist/cases/{case_id}/referral`

- [ ] **Step 1: Write role and scope tests.** A mother cannot list cases; a kader cannot access another scope; a nutritionist can read cases in the assigned scope.
- [ ] **Step 2: Write transition tests through HTTP.** Cover `needs_review → assigned → home_visit → verified_risk → referred → resolved` and rejection of invalid transitions.
- [ ] **Step 3: Implement the kader queue.** Return child identity, latest screen, reason codes, confidence, days since submission, priority, and current status.
- [ ] **Step 4: Implement assignment and home-visit recording.** `assign` transitions `needs_review → assigned`; `home-visit` transitions `assigned → home_visit` and stores notes plus optional manual length/weight as a new case action. Do not overwrite the mother’s original result.
- [ ] **Step 5: Implement verification.** Create a separate verified measurement record, attach its source as `kader` or `puskesmas`, and transition the case to `verified_risk` or `resolved`.
- [ ] **Step 6: Implement the nutritionist dashboard.** Return the case timeline, source provenance, verified values, prior visits, and outstanding actions.
- [ ] **Step 7: Implement decision and referral recording.** Store nutrition advice/action, referral destination, notes, actor, and timestamp; transition the case explicitly.
- [ ] **Step 8: Run the end-to-end API test.**

Run: `rtk proxy pytest -q tests/test_workflow_api.py`

Expected: one mother submission appears in the kader queue, a kader can record a home visit, and the nutritionist sees the verified case and can close or refer it.

- [ ] **Step 9: Commit the field-to-Puskesmas slice.**

---

### Task 7: Build the Three Role Views in the Existing Next.js App

**Files:**
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/api.ts`
- Create: `web/src/app/ibu/page.tsx`
- Create: `web/src/app/ibu/children/[id]/page.tsx`
- Create: `web/src/app/login/page.tsx`
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/kader/page.tsx`
- Create: `web/src/app/kader/[caseId]/page.tsx`
- Create: `web/src/app/ahli-gizi/page.tsx`
- Create: `web/src/app/ahli-gizi/[caseId]/page.tsx`
- Modify: `web/src/app/petugas/page.tsx`
- Modify: `web/src/app/petugas/[id]/page.tsx`

**Interfaces:**
- `api.ts` owns bearer-token fetches and typed calls; pages must not build raw endpoint URLs independently.
- `types.ts` mirrors `workflow_schemas.py` field names, including `screening_status`, `verification_status`, `reason_codes`, `case_status`, and `next_due_at`.

- [ ] **Step 1: Write the typed API client.** Add `login`, `registerMother`, `createChild`, `submitGrowthCheck`, `listMotherCases`, `listKaderCases`, `getNutritionistCase`, and action methods.
- [ ] **Step 2: Add the login route.** Store only the access token and role metadata needed by the API client; redirect each role to its own route.
- [ ] **Step 3: Add the mother route.** Show registered children, next monthly due date, photo capture/upload, weight input, CV result, confidence, and “menunggu verifikasi kader” state.
- [ ] **Step 4: Add the mother timeline.** Show all submissions, source, verification state, case status, and the next check date.
- [ ] **Step 5: Replace the current kader upload page with a case queue.** Show urgent/review/overdue status and link to the home-visit action screen.
- [ ] **Step 6: Add the kader case detail.** Record visit notes, manual verification values, and transition the case without exposing nutritionist-only decisions.
- [ ] **Step 7: Adapt the current petugas list/detail into the ahli gizi dashboard.** Keep the existing growth table and SHAP display only where backed by data; add verified source, case status, action, and referral sections.
- [ ] **Step 8: Update the role selector and compatibility links.** Route old `/petugas` links to `/ahli-gizi`; do not leave the old UI claiming it is the only workflow.
- [ ] **Step 9: Build the frontend.**

Run: `rtk bun --cwd web run build`

Expected: Next.js build passes with no implicit `any` in the new API contracts.

- [ ] **Step 10: Commit the three-role UI slice.**

---

### Task 8: Seed the Demo and Wire the Local Stack

**Files:**
- Create: `scripts/seed_demo_users.py`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `Makefile`

**Interfaces:**
- Seed output prints credentials once for a mother, kader, and nutritionist in one `scope_key`.
- `make seed-demo` creates accounts and one 0–23 month child without inserting fake clinical conclusions.

- [ ] **Step 1: Write the seed script.** Use the same store functions and deterministic records; never hard-code production secrets.
- [ ] **Step 2: Add the Make target.** Make it call `python scripts/seed_demo_users.py` against the configured database.
- [ ] **Step 3: Add backend environment variables.** Require `JWT_SECRET` outside tests and pass it through Compose.
- [ ] **Step 4: Document the demo path.** Mother submits a monthly check, kader records a home visit, nutritionist verifies and decides, and the mother timeline updates.
- [ ] **Step 5: Run the local stack smoke path.**

Run: `rtk docker compose config`

Expected: Compose renders successfully and includes the JWT settings without exposing credentials in tracked files.

- [ ] **Step 6: Commit the runnable demo slice.**

---

### Task 9: Add the End-to-End Regression Gate

**Files:**
- Modify: `tests/test_smoke.py`
- Modify: `tests/test_api_priority.py` only if legacy fixtures need isolation
- Create: `tests/test_workflow_e2e.py`
- Modify: `docs/RESPONSIBLE_AI.md`
- Modify: `README.md`

- [ ] **Step 1: Write the full TestClient flow.** Register mother, create child, submit a synthetic 180-day image, authenticate as kader, record a home visit, authenticate as nutritionist, verify the case, and assert the mother timeline contains the verified result.
- [ ] **Step 2: Assert the safety boundary.** The API never returns `stunting_confirmed`; it returns `needs_review`, `verified_risk`, or `resolved`.
- [ ] **Step 3: Assert ownership and scope.** A second mother cannot read the child; a different scope cannot read the case.
- [ ] **Step 4: Run the complete backend suite.**

Run: `rtk proxy pytest -q`

Expected: legacy CV/model tests and all new workflow tests pass.

- [ ] **Step 5: Run formatting and frontend verification.**

Run: `rtk git diff --check`

Run: `rtk bun --cwd web run build`

Expected: no diff errors and a successful production frontend build.

- [ ] **Step 6: Commit the verification gate.**

---

## Acceptance Criteria

- A mother can register one child aged 0–730 days and submit a CV-assisted monthly growth check with manual weight.
- The system stores structured results and creates a review case without storing the uploaded image bytes.
- A kader can see only assigned-scope cases, record a home visit, and attach a separate manual verification.
- An ahli gizi/Puskesmas user can see the verified timeline, record an intervention, refer the case, or resolve it.
- The mother can see the case status and next monthly check date.
- Legacy Tunas endpoints and tests remain functional.
- No UI or API labels the CV output as a confirmed diagnosis.
- Backend tests, end-to-end smoke test, `git diff --check`, and frontend build pass.

## Explicit Follow-Up Plans

These are intentionally separate from the first vertical slice:

1. **On-device CV:** export/replace the Python/OpenCV inference path with a mobile-compatible model and send summaries only.
2. **Food logging:** local TKPI subset, manual food fallback, nutrient summary, and nutrition recommendation.
3. **Panic/speech:** urgent alerts and speech milestone checks after the growth/referral workflow is stable.
4. **24–59 months:** standing-height protocol, separate capture guidance, WHO height tables, and new validation data.
