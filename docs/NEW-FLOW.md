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

> The broader product concepts in this legacy overview are non-binding future
> context. The current implementation and demo scope is only the 0–23 month
> growth workflow defined in Section 5 and its API in Section 6. Food logging,
> speech analysis, Claude recommendations, and push notifications are excluded.

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

### Current MVP — 0–23 Month Growth Workflow Only

These are the only features in the current demo and implementation contract.

#### Mother

| Feature | Description | Notes |
|---|---|---|
| Growth-check submission | Submit an image, age, weight, and context to the backend | Supported only for `0 <= age_days <= 730` |
| Growth result | View recumbent-length estimate, provenance, verification state, and case status | Screening signal; human review remains required |

#### Kader

| Feature | Description | Notes |
|---|---|---|
| Case queue | View assigned submitted cases and their priority | Does not establish a diagnosis |
| Operational follow-up | Record contact, home visit, repeat measurement, and notes | Moves cases through the documented state machine |

---

#### Nutritionist/Puskesmas

| Feature | Description | Notes |
|---|---|---|
| Verified case review | Review measurement provenance and the case timeline | Only verified measurements support a decision |
| Intervention or referral | Record the next nutrition action, referral, or resolution | `resolved` is terminal |

### Deferred features — non-binding future context

Food logging, speech milestone analysis, Claude-backed recommendations, push
notifications, food validation, supervisor aggregates, multilingual support,
and supplement inventory are not MVP requirements, demo steps, API endpoints,
or timeline commitments for this implementation. They may be reconsidered in a
later product phase only; this section creates no current scope.

---

## 6. API Endpoint Plan

### Authentication

```
POST   /api/auth/register          Register new user (mother / kader / nutritionist)
POST   /api/auth/login             Login and receive JWT token
POST   /api/auth/refresh           Refresh access token
```

### Mother — Growth Check

```
POST   /api/logs/growth            Submit growth check result (recumbent length, weight, provenance, verification state)
GET    /api/logs/growth/:userId    Get growth history for a child
```

### Kader and Nutritionist Dashboard

```
GET    /api/dashboard/cases        Get scoped cases for the logged-in kader or nutritionist
GET    /api/dashboard/cases/:id    Get the case timeline and measurement provenance
POST   /api/cases/:id/follow-up    Record kader operational follow-up
POST   /api/cases/:id/decision     Record nutritionist intervention, referral, or resolution
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
│   │   │   ├── growth-check.tsx     # Guided camera + weight input
│   │   │   └── profile.tsx          # Growth history and case status
│   │
│   ├── components/
│   │   ├── GuidedCamera.tsx         # Overlay-assisted camera component
│   │   ├── GrowthChart.tsx          # Height/weight trend chart
│   │   └── CaseStatus.tsx            # Verification and case status
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
│   │   └── cases.ts
│   │
│   ├── services/
│   │   ├── priorityScoring.ts       # AI-driven risk score computation
│   │   └── workflowService.ts       # Screening and case workflow logic
│   │
│   ├── models/                      # DB schema (Prisma / Mongoose)
│   │   ├── User.ts
│   │   ├── GrowthLog.ts
│   │   ├── Case.ts
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
| Week 2 | Mother Growth Submission | Growth check submission and server-side screening functional |
| Week 3 | Kader + Nutritionist Workflow | Case queue, verification, follow-up, intervention, and referral working |
| Week 4 | Integration, Polish & Demo Prep | End-to-end growth workflow demo finalized |

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
**Deliverable:** All three apps running locally; a user can register and log in.

---

### Week 2 — Core Mother App (Days 8–14)

**Goals:** The mother growth submission is functional end-to-end

- [ ] Implement guided camera overlay component for growth check
- [ ] Integrate the existing server-side CV path for recumbent-length screening
- [ ] Build weight manual input screen
- [ ] Connect growth log to backend API

**Deliverable:** A mother can submit a growth check and see its structured result and verification state.

---

### Week 3 — Case Dashboard + Decisions (Days 15–21)

**Goals:** Kader and nutritionist case workflow functional; verification and decisions working

- [ ] Build the kader case queue and operational follow-up form
- [ ] Implement case priority from the growth screening signal
- [ ] Build the nutritionist verified timeline and review form
- [ ] Build intervention logging panel
- [ ] Build role-based access guard (`mother` vs `kader` vs `nutritionist`)

**Deliverable:** Kader can follow up a submitted case; nutritionist can verify, intervene, refer, or resolve it.

---

### Week 4 — Integration, Polish & Demo Prep (Days 22–30)

**Goals:** Everything works together; demo is compelling and rehearsed

- [ ] End-to-end integration test of full user flow
- [ ] Seed demo data (3–5 realistic mother profiles with varied risk levels)
- [ ] Fix critical bugs and edge cases
- [ ] Polish mobile UI (loading states, error handling, empty states)
- [ ] Polish dashboard UI (responsive layout, clear visual hierarchy)
- [ ] Prepare demo script: Mother submits growth check → kader follow-up → nutritionist decision
- [ ] Prepare presentation slides (problem, solution, architecture, impact, roadmap)
- [ ] Rehearse demo at least twice with full team
- [ ] Deploy to staging environment for demo day

**Deliverable:** Demo-ready 0–23 month growth workflow with seeded cases; presentation slides complete.

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
| Priority scoring | Rule-based weighted score → ML in Phase 2 | Explainable to CHWs; fast to implement; upgradeable |
| Backend | Node.js + Express + PostgreSQL | Familiar stack; good ORM support (Prisma); scales adequately |
| Dashboard | Next.js | SSR for fast initial load; easy deployment; good for data tables |
| Auth | JWT with refresh tokens | Stateless; works well for multi-role mobile + web setup |

---

*NutriLink PRD v1.0 — Prepared for Duke-NUS Hackathon Submission*
