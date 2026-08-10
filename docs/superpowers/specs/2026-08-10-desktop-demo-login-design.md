# Desktop Demo Login Design

## Goal

Provide three deterministic demo accounts and desktop-only one-click login shortcuts for the mother, kader, and nutritionist workflows. Keep normal login and mother registration unchanged, and never ship the demo password in the browser bundle.

## Account Contract

The existing `scripts/seed_demo_users.py` remains the source of demo accounts. It creates these users in one configured scope:

- `Ibu Demo` with role `mother`
- `Kader Demo` with role `kader`
- `Ahli Gizi Demo` with role `nutritionist`

All three use `DEMO_SCOPE_KEY` and the server-only `DEMO_PASSWORD`. The local demo environment uses scope `posyandu-demo`. Seeding remains idempotent and keeps the existing sample child for the mother account.

## Backend Design

Add `ENABLE_DEMO_LOGIN`, disabled by default. Docker demo configuration explicitly passes this variable to the backend.

Add `POST /api/auth/demo-login` with a body containing one role from `mother`, `kader`, or `nutritionist`. The endpoint:

1. returns HTTP 404 when demo login is disabled, so production does not advertise the feature;
2. maps the requested role to the fixed account name;
3. reads `DEMO_SCOPE_KEY` and `DEMO_PASSWORD` only on the server;
4. loads the seeded user and verifies its password hash against `DEMO_PASSWORD`;
5. returns the same JWT response as normal login;
6. returns HTTP 503 with a seed instruction when the account is missing or the configured password no longer matches.

Normal `/api/auth/login` and `/api/auth/register` behavior stays unchanged.

## Frontend Design

Add a typed `demoLogin(role)` API helper. On the login page, render a `Quick login` panel only at the `lg` breakpoint and above. It contains three buttons labeled `Ibu Demo`, `Kader Demo`, and `Ahli Gizi Demo`.

Clicking a shortcut calls the demo endpoint, saves the returned session, and redirects through the existing `roleHome` function. While a request is active, all auth controls are disabled and the selected button displays a processing state. Backend failures use the existing error alert. The normal form fields are not populated with demo credentials.

The shortcuts sit inside the form-side panel, not over the Three.js scene. They remain hidden on phone and tablet layouts to keep the PWA login compact and focused.

## Configuration and Documentation

Add `ENABLE_DEMO_LOGIN=true` to `.env.example` for the documented local demo and pass it into Docker Compose with a safe default of `false` when absent. Update the README demo section to explain the one-click desktop path and retain the manual credentials flow.

The local `.env` is not committed. It will be created from `.env.example` with a non-production JWT secret and demo password before the three accounts are seeded.

## Error and Safety Boundaries

- Demo login cannot be enabled accidentally by merely setting a password; the explicit feature flag is required.
- The browser receives only a role selector and the resulting token, never `DEMO_PASSWORD`.
- Missing seeds and password drift fail closed instead of creating users from a public request.
- The endpoint supports only the three fixed role values.

## Verification

Automated tests and production builds remain deferred at the user's request. Static inspection will verify that the password is absent from frontend code, normal auth remains intact, mobile shortcuts are hidden, and changed files have no whitespace errors. Later verification should cover disabled mode, all three role redirects, missing seed behavior, desktop visibility, and mobile absence.
