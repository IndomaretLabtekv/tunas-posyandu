# Desktop Demo Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed one account for each workflow role and add desktop-only one-click login shortcuts without exposing demo credentials to the browser.

**Architecture:** Keep demo credentials and account-name mapping on the FastAPI server behind an explicit feature flag. Reuse the existing JWT response and frontend session redirect flow. Keep the seed script idempotent by reconciling existing demo account roles and password hashes.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Next.js 15, React 19, TypeScript, Tailwind CSS, Docker Compose.

---

## File Map

- Modify `api/workflow_schemas.py`: typed demo role request.
- Modify `api/workflow_routes.py`: feature-gated demo authentication endpoint.
- Modify `scripts/seed_demo_users.py`: reconcile all three deterministic accounts.
- Modify `web/src/lib/api.ts`: browser-safe role-only demo request.
- Modify `web/src/app/login/page.tsx`: desktop shortcuts and shared auth completion.
- Modify `.env.example`, `docker-compose.yml`, and `README.md`: explicit demo-mode configuration and usage.
- Create ignored `.env`: local-only secrets used to start and seed the stack.

### Task 1: Feature-Gated Demo Endpoint

**Files:**
- Modify: `api/workflow_schemas.py`
- Modify: `api/workflow_routes.py`

- [ ] Add `DemoLoginRequest` with `role: Literal["mother", "kader", "nutritionist"]`.
- [ ] Add a fixed server-side role-to-name map.
- [ ] Add `_demo_login_enabled()` accepting only `1`, `true`, `yes`, or `on`.
- [ ] Add `POST /auth/demo-login`: return 404 when disabled, load server-side scope/password, verify the seeded user, return 503 when unavailable, and otherwise reuse `_response(user)`.
- [ ] Confirm the endpoint never accepts or returns `DEMO_PASSWORD`.

### Task 2: Idempotent Three-Role Seed

**Files:**
- Modify: `scripts/seed_demo_users.py`

- [ ] Update `_ensure_user` so an existing fixed-name account is reconciled to the expected role and a fresh hash of the configured demo password, then commit the update.
- [ ] Keep creation of `Ibu Demo`, `Kader Demo`, `Ahli Gizi Demo`, and `Bayi Demo` unchanged for an empty database.
- [ ] Remove duplicate scope output and keep the seed command's credential summary.

### Task 3: Desktop One-Click UI

**Files:**
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/app/login/page.tsx`

- [ ] Export `demoLogin(role: Role)` which posts only `{ role }` to `/api/auth/demo-login` without authentication.
- [ ] Extract a shared `completeAuth` function that saves the session and redirects through `roleHome`.
- [ ] Track the selected demo role while busy and add a one-click handler using the same error alert as the normal form.
- [ ] Add three `hidden lg:grid` buttons below the normal form, with accessible labels and per-button processing text.
- [ ] Disable normal auth controls while any auth request is active and preserve every existing field, registration rule, and redirect.

### Task 4: Demo Configuration and Documentation

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Create: `.env` (ignored)

- [ ] Add `ENABLE_DEMO_LOGIN=true` to the documented demo environment.
- [ ] Pass `ENABLE_DEMO_LOGIN: ${ENABLE_DEMO_LOGIN:-false}` to the backend container.
- [ ] Document the desktop quick-login buttons and the three account names.
- [ ] Create local `.env` with scope `posyandu-demo`, a demo-only password, and a non-production JWT secret.

### Task 5: Start and Seed Local Demo

- [ ] Run `rtk docker compose up -d --build` and wait for backend health/readiness.
- [ ] Run `rtk make seed-demo` and confirm all three account names are printed.
- [ ] Do not run automated tests or the frontend production build in this execution; they remain deferred by user request.
- [ ] Run static checks only: `rtk git diff --check`, search frontend code for the demo password, and inspect container status.

### Deferred Verification

Later, add API coverage for disabled mode, each role, missing seeds, and stale password. Run the frontend production build and manually check desktop buttons, mobile absence, errors, and all role redirects before committing implementation files.
