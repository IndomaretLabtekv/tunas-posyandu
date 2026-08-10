# NutriLink — Product Requirements Document
**Version:** 1.0  
**Context:** Hackathon Submission — Duke-NUS Track 2: Newborn, Infant & Young Child Feeding  
**Timeline:** 1 Month  
**Last Updated:** June 2026

> **0–23 month backend contract (Task 1).** The current implementation supports
> `0 <= age_days <= 730`, inclusive. Growth screening uses recumbent length;
> standing height is not implemented. A screening result is an
> **indikasi gangguan pertumbuhan — perlu verifikasi**, never an automatic
> diagnosis or confirmed clinical result.

### Canonical workflow contract

The three canonical roles are:

| Role | Responsibility |
|---|---|
| `mother` | Submits the child's monthly growth-check data and views the resulting status and next due date. |
| `kader` | Handles operational follow-up, including contact, home visit, repeat measurement, and notes. |
| `nutritionist` | Represents the nutritionist/Puskesmas reviewer who verifies the case, decides the nutrition action, and records intervention or referral. |

Home-submitted measurements are `unverified` until a `kader` or health worker
confirms them. A confirmed measurement is `verified`; verification provenance
must remain visible alongside the value. The case state machine is:

```text
submitted → normal
submitted → needs_review → assigned → home_visit → verified_risk
verified_risk → referred → resolved
needs_review → resolved
```

Only the transitions shown above are allowed. `needs_review` means
**indikasi gangguan pertumbuhan — perlu verifikasi** and must not be rendered as
`stunting` or a diagnosis. `resolved` is terminal for this case.

---

## Table of Contents

1. [Project Brief](#1-project-brief)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Solution Overview](#4-solution-overview)
5. [MVP Features](#5-mvp-features)
6. [API Endpoint Plan](#6-api-endpoint-plan)
7. [Project Structure](#7-suggested-project-structure)
8. [Execution Timeline](#8-1-month-execution-timeline)
9. [Post-Hackathon Roadmap](#9-post-hackathon-roadmap)

---

## 1. Project Brief

| Field | Detail |
|---|---|
| **Product Name** | NutriLink |
| **Track** | Track 2 — Newborn, Infant & Young Child Feeding |
| **Type** | Mobile-first application (cross-platform) |
| **Core Premise** | End-to-end monitoring and intervention platform connecting breastfeeding mothers in remote communities with Community Health Workers (CHWs) |
| **Architecture Principle** | Server-side CV demo; store structured results and discard temporary uploads |
| **Target Region** | Asia-Pacific (primary: Indonesia) |
| **Demo Format** | Live mobile prototype with CHW dashboard walkthrough |

---

## 2. Problem Statement

Gaps in breastfeeding and complementary feeding practices during the first two years of life are hindering child development, particularly in remote communities across the Asia-Pacific region. Existing intervention models rely heavily on periodic in-person visits by Community Health Workers — a resource-constrained and geographically limited approach that leaves critical windows of nutritional risk unmonitored.

Specific failure points include:

- No continuous visibility into a mother's daily nutritional intake
- No standardized, low-cost mechanism for tracking infant growth between clinic visits
- No data-driven prioritization tool for CHWs managing large, dispersed caseloads
- No early warning system for developmental delays in under-two children
- Infrastructure dependency (connectivity) that makes cloud-first solutions impractical for last-mile communities

The result is that deteriorating nutritional and developmental conditions go undetected until they become acute, when intervention is costlier and less effective.

---

## 3. Target Users

### Primary Users

**Breastfeeding Mothers (End Users)**
- Age range: 18–40
- Location: Remote or semi-remote communities in Asia-Pacific
- Tech profile: Basic smartphone literacy; owns a low-mid range Android device
- Key need: Simple, guided tools to self-monitor nutrition and child health without needing connectivity at all times

**Community Health Workers (CHWs)**
- Role: Frontline health personnel responsible for 20–100+ households
- Tech profile: Moderate smartphone/tablet literacy
- Key need: Prioritized, actionable view of which mothers and children require immediate follow-up

### Secondary Users

**Health Supervisors / Puskesmas Officers**
- Role: Oversee multiple CHWs; manage supplement/intervention supply chains
- Key need: Aggregate reporting and escalation visibility

---

## 4. Solution Overview

NutriLink is a dual-interface mobile platform with two interconnected modules:

### Module A — Mother-Facing Mobile App

Enables mothers to self-report and self-monitor through three core mechanisms:

1. **Daily Food Logging** — Photo capture with a structured nutritional summary using a localized food database (TKPI + ASEAN Food Composition Database), or manual input. This feature is outside the 0–23 month backend workflow.

2. **Monthly Growth Check** — The mother submits a growth-check image, age, weight, and context. The backend CV path returns a screening signal and recumbent-length estimate; the measurement remains `unverified` until human review. Standing height is outside this implementation.

3. **Speech Milestone Check (Secondary Indicator)** — Monthly elicited imitation task. This feature is outside the 0–23 month backend workflow.

4. **Panic Report** — A lightweight, always-accessible button allowing mothers to flag urgent concerns outside of scheduled check-ins. Triggers an immediate high-priority alert on the CHW dashboard.

### Module B — CHW Web Dashboard

A responsive web dashboard providing:

- AI-prioritized intervention queue (scored by nutritional trend, growth flags, developmental signals, and panic alerts)
- Per-mother/child timeline view with historical logs
- Intervention assignment and logging (supplement dispatch, home visit, escalation)
- Role-based access for supervisors and Puskesmas officers

### Architecture Principle

For this implementation, image processing runs through the existing server-side
Python/OpenCV backend path. Uploaded images are processed temporarily; only
structured results, provenance, and workflow actions are retained. Mobile
inference is future work and is not part of this contract.

```
[MOTHER]
  Monthly growth check → temporary upload → structured screening result
         ↓
[CLOUD / BACKEND]
  Store: measurement provenance, workflow status, actions, and referrals
  Compute: CV result and case priority
         ↓
[CHW DASHBOARD]
  Priority queue → Intervention assignment → Escalation
```

---

## 5. MVP Features

### Must Have — For Demo

These features must be functional and demonstrable during the hackathon presentation.

#### Mother App

| Feature | Description | Notes |
|---|---|---|
| Food photo logging | Camera capture + structured nutritional summary | Outside the 0–23 month backend workflow |
| Manual food input | Searchable food list from TKPI subset | Pre-load 100–150 most common local foods for demo |
| Nutrition recommendation | Per-log AI recommendation card (dismissable) | Can use Claude API for generation; keep prompt structured |
| Guided growth photo | Mother submits an image for server-side CV screening | Output recumbent-length estimate and confidence |
| Manual weight input | Simple numeric input accompanying the growth check | Retained as a structured measurement |
| Growth result display | Show recumbent-length result, provenance, verification state, and case status | Human review remains required |
| Panic report button | One-tap urgent alert with optional short text | Must reach CHW dashboard immediately |
| Offline-first behavior | All inputs work without connectivity; sync when available | Core architecture requirement |

#### CHW Dashboard

| Feature | Description | Notes |
|---|---|---|
| Priority queue | List of mothers/children sorted by AI risk score | Score based on nutritional deficit + growth flag + panic alert |
| Mother profile view | Timeline of logs, growth data, flags for each mother | Clicking from queue opens this view |
| Intervention log | CHW can record action taken (supplement given, visit scheduled, escalated) | Simple dropdown + notes field |
| Alert notification | Panic report triggers visible alert on dashboard | Push notification or polling acceptable for demo |
| Role-based login | Separate login flows for Mother, CHW, and Supervisor | Basic JWT auth sufficient |

---

### Nice to Have — If Time Allows

These features strengthen the product but are not required for demo day.

| Feature | Description | Priority |
|---|---|---|
| Speech milestone check | Audio recording + structured milestone flag | Outside the 0–23 month backend workflow |
| Crowdsourced food validation | CHW can approve/add unrecognized foods to local DB | Medium |
| Aggregate supervisor view | Puskesmas-level reporting and heatmap | Medium |
| Multilingual support | Bahasa Indonesia + local language toggle | Low for demo |
| Supplement inventory tracking | Track what CHW has distributed and to whom | Low for demo |
| Push notification to mother | Reminder for daily log or upcoming monthly check | Low for demo |

---

## 6. API Endpoint Plan

### Authentication

```
POST   /api/auth/register          Register new user (mother / CHW / supervisor)
POST   /api/auth/login             Login and receive JWT token
POST   /api/auth/refresh           Refresh access token
```

### Mother — Food Logging

```
POST   /api/logs/food              Submit food log (outside this workflow)
GET    /api/logs/food/:userId      Get food log history for a user
GET    /api/logs/food/:userId/today  Get today's logs for quick display
```

### Mother — Growth Check

```
POST   /api/logs/growth            Submit growth check result (recumbent length, weight, provenance, verification state)
GET    /api/logs/growth/:userId    Get growth history for a child
```

### Mother — Speech Milestone

```
POST   /api/logs/speech            Submit speech milestone flag result
GET    /api/logs/speech/:userId    Get speech milestone history
```

### Mother — Panic Report

```
POST   /api/alerts/panic           Submit panic report (triggers priority escalation)
GET    /api/alerts/panic/:userId   Get panic report history for a user
```

### CHW Dashboard

```
GET    /api/dashboard/queue        Get prioritized intervention queue for logged-in CHW
GET    /api/dashboard/mother/:id   Get full profile and history for a specific mother
POST   /api/interventions          Log an intervention (supplement, visit, escalation)
GET    /api/interventions/:userId  Get intervention history for a mother
PATCH  /api/alerts/:alertId        Mark alert as acknowledged / resolved
```

### Nutrition Reference (Local Food DB)

```
GET    /api/foods/search?q=        Search local food database
GET    /api/foods/:id              Get nutritional details for a specific food item
POST   /api/foods/suggest          Suggest a new food item (pending CHW validation)
```

### AI Recommendation (Claude API-backed)

```
POST   /api/recommend/nutrition    Generate dietary recommendation based on log summary
POST   /api/recommend/priority     Compute risk score for a mother/child record
```

> **Note:** All endpoints require Authorization header with Bearer token. Mother endpoints are scoped to the authenticated user's own data. CHW endpoints are scoped to their assigned community. Supervisor endpoints have read access across all communities.

---

## 7. Suggested Project Structure

```
nutrilink/
│
├── mobile/                          # React Native (Expo) — Mother App
│   ├── app/
│   │   ├── (auth)/                  # Login, register screens
│   │   ├── (tabs)/
│   │   │   ├── home.tsx             # Daily summary + quick log
│   │   │   ├── food-log.tsx         # Photo capture + manual input
│   │   │   ├── growth-check.tsx     # Guided camera + weight input
│   │   │   ├── speech-check.tsx     # Audio elicitation screen
│   │   │   └── profile.tsx          # History and personal data
│   │   └── panic.tsx                # Panic report button (always accessible)
│   │
│   ├── components/
│   │   ├── GuidedCamera.tsx         # Overlay-assisted camera component
│   │   ├── NutritionCard.tsx        # Recommendation display card
│   │   ├── GrowthChart.tsx          # Height/weight trend chart
│   │   └── PanicButton.tsx          # Floating panic button
│   │
│   ├── services/
│   │   ├── growthApi.ts             # Server-side growth screening API client
│   │   ├── api.ts                   # API client (with offline queue)
│   │   └── storage.ts               # Local queue for pending submissions
│   │
│   └── assets/
│       └── food-db/                 # Bundled TKPI subset (JSON)
│
├── dashboard/                       # Next.js — CHW Web Dashboard
│   ├── pages/
│   │   ├── login.tsx
│   │   ├── queue.tsx                # Priority intervention queue
│   │   ├── mother/[id].tsx          # Individual mother profile
│   │   └── interventions.tsx        # Intervention log
│   │
│   ├── components/
│   │   ├── PriorityQueue.tsx
│   │   ├── MotherTimeline.tsx
│   │   ├── InterventionPanel.tsx
│   │   └── AlertBanner.tsx
│   │
│   └── services/
│       └── api.ts
│
├── backend/                         # Node.js + Express (or FastAPI)
│   ├── routes/
│   │   ├── auth.ts
│   │   ├── logs.ts
│   │   ├── alerts.ts
│   │   ├── dashboard.ts
│   │   ├── interventions.ts
│   │   ├── foods.ts
│   │   └── recommend.ts
│   │
│   ├── services/
│   │   ├── priorityScoring.ts       # AI-driven risk score computation
│   │   ├── claudeClient.ts          # Anthropic API integration
│   │   └── notificationService.ts   # Panic alert push logic
│   │
│   ├── models/                      # DB schema (Prisma / Mongoose)
│   │   ├── User.ts
│   │   ├── FoodLog.ts
│   │   ├── GrowthLog.ts
│   │   ├── SpeechLog.ts
│   │   ├── Alert.ts
│   │   └── Intervention.ts
│   │
│   └── middleware/
│       ├── auth.ts
│       └── roleGuard.ts
│
└── docs/
    ├── PRD.md                       # This document
    ├── API.md                       # Full API reference
    └── architecture-diagram.png
```

---

## 8. 1-Month Execution Timeline

### Overview

| Week | Focus | Milestone |
|---|---|---|
| Week 1 | Foundation & Setup | All environments running; auth working; data models defined |
| Week 2 | Core Mother App Features | Food logging + growth check functional |
| Week 3 | CHW Dashboard + AI Integration | Dashboard live; priority scoring working; Claude API connected |
| Week 4 | Integration, Polish & Demo Prep | End-to-end flow working; demo script finalized |

---

### Week 1 — Foundation (Days 1–7)

**Goals:** Project scaffolding, auth, database, basic navigation

- [ ] Set up monorepo (mobile, dashboard, backend)
- [ ] Configure Expo project for React Native
- [ ] Set up Next.js dashboard project
- [ ] Set up backend (Node/Express or FastAPI) with chosen DB (PostgreSQL recommended)
- [ ] Implement auth endpoints (register, login, JWT)
- [ ] Define and migrate all data models
- [ ] Build login/register screens (mobile + dashboard)
- [ ] Set up CI/CD or deployment pipeline (Railway / Render / Vercel)
- [ ] Bundle TKPI food subset (100–150 foods) as local JSON in mobile app

**Deliverable:** All three apps running locally; a user can register and log in.

---

### Week 2 — Core Mother App (Days 8–14)

**Goals:** Food logging and growth check are fully functional end-to-end

- [ ] Build food photo capture screen with camera permissions
- [ ] Integrate lightweight food estimation model (or rule-based nutritional lookup from local DB)
- [ ] Build manual food search + input screen
- [ ] Connect food log to backend API (with offline queue for low-connectivity)
- [ ] Implement guided camera overlay component for growth check
- [ ] Integrate the existing server-side CV path for recumbent-length screening
- [ ] Build weight manual input screen
- [ ] Connect growth log to backend API
- [ ] Build nutrition recommendation card (Claude API integration — first pass)
- [ ] Build basic home screen showing daily summary

**Deliverable:** A mother can log food and complete a growth check; data appears in the backend.

---

### Week 3 — Dashboard + AI + Alerts (Days 15–21)

**Goals:** CHW dashboard functional; priority scoring live; panic report working

- [ ] Build CHW priority queue page (pulls from backend scoring endpoint)
- [ ] Implement priority scoring logic in backend (weight: panic > growth flag > nutrition deficit)
- [ ] Build individual mother profile / timeline view
- [ ] Build intervention logging panel
- [ ] Build role-based access guard (Mother vs CHW vs Supervisor)
- [ ] Implement panic report button in mobile app
- [ ] Connect panic report to backend; trigger alert on dashboard
- [ ] Refine Claude API prompt for nutrition recommendations (structured output)
- [ ] Add basic speech milestone screen (audio recording + simple flag — Nice to Have if time permits)
- [ ] Build supervisor aggregate view (optional, if time allows)

**Deliverable:** CHW can log in, see a prioritized list of mothers, view profiles, and log interventions. Panic report flows end-to-end.

---

### Week 4 — Integration, Polish & Demo Prep (Days 22–30)

**Goals:** Everything works together; demo is compelling and rehearsed

- [ ] End-to-end integration test of full user flow
- [ ] Seed demo data (3–5 realistic mother profiles with varied risk levels)
- [ ] Fix critical bugs and edge cases
- [ ] Polish mobile UI (loading states, error handling, empty states)
- [ ] Polish dashboard UI (responsive layout, clear visual hierarchy)
- [ ] Prepare demo script: Mother logs food → growth check → CHW dashboard → intervention
- [ ] Prepare presentation slides (problem, solution, architecture, impact, roadmap)
- [ ] Rehearse demo at least twice with full team
- [ ] Deploy to staging environment for demo day

**Deliverable:** Demo-ready build with seeded data; presentation slides complete.

---

## 9. Post-Hackathon Roadmap

### Phase 1 — Validation (Month 2–3)

Focus: Real-world feasibility testing with a small cohort

- Pilot with 2–3 CHWs and 10–20 mothers in a target community
- Validate structured food summaries against manual nutritional assessment
- Collect feedback on app usability from mothers with low digital literacy
- Validate growth photo estimation against anthropometric measurements
- Refine local food database based on actual foods reported in pilot
- IRB / ethical approval process initiation for clinical data collection

### Phase 2 — Model & Data Improvement (Month 3–6)

Focus: Accuracy, localization, and reliability

- Fine-tune food recognition model on locally collected food photos
- Expand TKPI food database with regional variants (Papua, NTT, Kalimantan)
- Integrate ASEAN Food Composition Database for cross-border portability
- Implement crowdsourced food validation loop (CHW approves unrecognized foods)
- Refine priority scoring algorithm with clinician input and outcome data
- Add speech milestone module with normative data for Bahasa Indonesia
- Formal accuracy benchmarking for recumbent-length estimation

### Phase 3 — Scale & Integration (Month 6–12)

Focus: Institutional adoption and ecosystem integration

- Integration with national health information systems (SIMPUS / SISFO)
- Multi-language support (Bahasa Indonesia + key regional languages)
- Offline sync improvements for extremely low-bandwidth environments (SMS fallback)
- Supplement supply chain tracking for CHW inventory management
- Aggregate analytics for Puskesmas and Dinas Kesehatan level reporting
- Formal clinical validation study with published outcomes
- Partnerships with UNICEF, WHO regional offices, or Kemenkes for scale

### Phase 4 — Regional Expansion (Month 12–24)

Focus: Asia-Pacific rollout beyond Indonesia

- Localize food database for Philippines, Papua New Guinea, Pacific Island nations
- Adapt speech milestone norms for target languages (Filipino, Tok Pisin, etc.)
- Partner with regional CHW training programs for onboarding at scale
- Explore integration with community health financing mechanisms (JKN, PhilHealth)
- Open-source mobile inference components for regional health tech reuse

---

## Appendix: Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Mobile framework | React Native (Expo) | Cross-platform; large ecosystem; Expo supports the submission flow |
| Growth screening CV | Existing Python/OpenCV backend path | Reuses the current server-side implementation for the demo |
| Food database | TKPI subset (bundled) + API fallback | Offline-first; covers Indonesian staples adequately for MVP |
| AI recommendations | Claude API (claude-sonnet-4-20250514) | Structured output; multilingual; handles nutritional context well |
| Priority scoring | Rule-based weighted score → ML in Phase 2 | Explainable to CHWs; fast to implement; upgradeable |
| Backend | Node.js + Express + PostgreSQL | Familiar stack; good ORM support (Prisma); scales adequately |
| Dashboard | Next.js | SSR for fast initial load; easy deployment; good for data tables |
| Auth | JWT with refresh tokens | Stateless; works well for multi-role mobile + web setup |

---

*NutriLink PRD v1.0 — Prepared for Duke-NUS Hackathon Submission*
