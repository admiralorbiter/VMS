---
title: "Automated Volunteer Recruitment & Matching – Feature Plan"
description: "End-to-end plan to propose, rank, and contact candidate volunteers for events"
tags: [planning, recruitment, matching, outreach]
---

## Why

Coordinators spend significant time finding, ranking, and contacting volunteers for each event. This feature automates the first pass: generate high-quality candidate lists with clear reasons, then streamline personalized outreach while honoring opt-outs and data privacy.

## Goals and Non‑Goals

- **Goals**:
  - **Automatic candidate generation** for any event with explainable matching reasons.
  - **Configurable scoring/ranking** using existing data (skills, past events, org/title, interests, location, engagement).
  - **One-click outreach** with templated, personalized messages and safety checks (opt-outs, frequency caps).
  - **Diversity and balance controls** (e.g., local/non-local mix, People of Color, first-time vs. returning).
  - **Auditable actions**: why each candidate was suggested; outreach logs.
- **Non‑Goals (Phase 1)**:
  - Full CRM replacement or mass email provider. We’ll integrate with existing email infrastructure initially.
  - Predictive ML. We start with deterministic scoring; ML is future work.

## Current Capabilities We’ll Build On

- Volunteers: skills, organizations and roles, industry, title/department, local status, interests, People of Color flag, engagement history, Salesforce and Mailchimp fields, participation history via `EventParticipation` (models/volunteer.py).
- Events: rich `EventType`, status, date/time, district, school, series, counts; association tables include `event_volunteers`, `event_districts`, and `event_skills` (models/event.py). If the `Event.skills` relationship is not currently exposed, we’ll add it (see Data Model updates).
- Pathways: event ↔ pathway and contact ↔ pathway associations exist (models/pathways.py) and can align candidates by pathway.
- Recruitment UI: quick recruitment and advanced search exist (`/reports/recruitment`, `/reports/recruitment/quick`, `/reports/recruitment/search`).

## Feature Set Overview

### 1) Event-based Candidate Generation

- Entry points:
  - From `events/view/{id}`: “Find Candidates” button opens a side panel.
  - From Reports → Recruitment: “Match Volunteers to Event.”
- Inputs: event id; optional filters (min score, max candidates, diversity constraints, exclude orgs, time window, include first-timers).
- Output: ranked list with badges and “because” reasons.
- Actions per candidate: add to event invite list, send message, copy email, view history, suppress, mark not a fit.

### 2) Scoring and Ranking Engine (Deterministic, explainable)

Weighted scoring with transparent reasons. Default weights are adjustable in admin.

- **Direct relevance**:
  - Event type match with past participation (same `EventType`) [+1.0]
  - Skill overlap with event required skills or title keywords (synonyms supported) [+0.8]
  - Title/department keyword match to event theme (e.g., “Data Analyst”, “BI”, “SQL”) [+0.6]
  - Organization/industry alignment (partner companies, relevant sectors) [+0.6]
  - Series/district/school recurrence (worked the same series/district/school) [+0.4]
- **Engagement**:
  - Recency of last volunteer date with exponential decay boost [+0.0–0.4]
  - Frequency (times volunteered) with diminishing returns [+0.0–0.3]
  - Last non-internal email activity, mail engagement [+0.0–0.2]
  - No-show or cancellations penalized [−0.5]
- **Logistics and constraints**:
  - Local status proximity (local > partial > non_local) [+0.0–0.3]
  - Day/time fit if availability exists (future) [+0.0–0.4]
  - Contact governance: do-not-contact/email opt-out → excluded hard filter
- **Balance and fairness**:
  - People of Color complement rule for event type (optional, admin-configurable) [+0.0–0.2]
  - First-time volunteer share target for wide events like `CAREER_JUMPING` [+0.0–0.2]

Each candidate includes a “why” list, e.g., “Past Data Viz event (2024-10-12), Skill: SQL, Title: Data Analyst, Local, Last volunteered 2 months ago.”

### 3) Templates and Personalized Outreach

- Template library with variables: `{{first_name}}`, `{{event_title}}`, `{{event_date}}`, `{{start_time}}`, `{{location}}`, `{{cta_link}}`, `{{role}}`, `{{teacher_name}}`, `{{district}}`, `{{series}}`.
- Message composer supports preview for N selected candidates, with per-candidate reason snips.
- Sending modes:
  - Export CSV for mail-merge or Mailchimp upload
  - Send via system email (initially SMTP/Flask-Mail if configured)
  - Generate Gmail drafts via mailto deeplinks (low-friction option)
- Safety checks: respect do-not-contact, email opt-out, contact frequency caps (e.g., ≤1 outreach per 14 days).
- Logging: store outreach intent and delivery status when sending via system email.

### 4) Diversity and Slate Controls

- Sliding controls to target proportions (e.g., 30–50% local, 20–40% first-time volunteers, People of Color ≥ target share where appropriate).
- Auto-suggested “balanced slate” subset derived from top-ranked pool.

### 5) Admin Controls and Audit

- Adjust weights, keyword dictionaries, synonym maps, industry ↔ event mappings.
- View and export decisions: “why suggested,” suppressions, responses.

## Exhaustive Matching Signals (Current + Near-Term)

- Event → Volunteer:
  - **Event type** ↔ past participation by `EventType`
  - **Title/department keywords** ↔ event theme (maintain keyword-to-type map)
  - **Skills** ↔ `Volunteer.skills` vs. `Event.skills` (add `Event.skills` rel if missing)
  - **Industry/organization** ↔ event theme or partner list
  - **Pathway alignment** ↔ event pathways vs. volunteer pathways
  - **District/school/series** recurrence
  - **Time/day window** vs. volunteer availability (future)
  - **Location** via local status (and later distance by zip)
- Volunteer context:
  - **Engagement**: last_volunteer_date, times_volunteered, no-show history
  - **Comms**: last_non_internal_email_date, mailchimp history, interests text
  - **Governance**: do_not_contact, email_opt_out, exclude_from_reports
  - **Diversity tags**: People of Color flag, gender (for specific programs if policy allows)

## Data Model and Infrastructure Changes

- Minimal (Phase 1):
  - Add `Event.skills` relationship using existing `event_skills` association.
  - Create `match_recommendation` table to store precomputed/on-demand matches:
    - `id`, `event_id`, `volunteer_id`, `score` (float), `reasons` (JSON), `created_at`, `refreshed_at`, `suppressed` (bool), indexes on `(event_id, score desc)` and `(volunteer_id)`.
  - Seed keyword dictionaries and synonym maps: `title_keywords`, `skill_synonyms`, `industry_to_eventtype`.
- Outreach logging (Phase 1–2):
  - `email_campaign` (`id`, `event_id`, `name`, `created_by`, `created_at`)
  - `email_message` (`campaign_id`, `volunteer_id`, `status`, `sent_at`, `provider_id`, `error`)
- Availability (Phase 2):
  - `volunteer_availability` (weekday/time windows, virtual vs. in-person preference)
- Optional (Phase 3):
  - `volunteer_preference` (preferred event types, schools/districts, frequency caps)

## APIs and Screens

- Routes:
  - **GET** `/events/{id}/candidates` → HTML/JSON list with scores and reasons, filters (`min_score`, `limit`, `balance: on/off`).
  - **POST** `/events/{id}/candidates/refresh` → recompute and cache matches.
  - **POST** `/events/{id}/candidates/add` → add selected volunteers to event invite/roster (no email).
  - **POST** `/recruitment/campaigns` → create campaign for selected candidates and template.
  - **POST** `/recruitment/campaigns/{id}/send` → send via configured provider (SMTP first).
  - **GET** `/recruitment/templates` → manage/view templates.
- UI:
  - Event view drawer: top candidates, chips for reasons, inline add/send.
  - Recruitment page: advanced filters, score sliders, balance toggles, export.

## Implementation Plan (Phased)

- **Phase 1 – Heuristics MVP**
  - Implement scoring service and `/events/{id}/candidates` (server-side pagination, explainable reasons).
  - Add `Event.skills` relationship and basic keyword dictionaries.
  - Event view drawer and recruitment list page.
  - CSV export and mailto-based compose; log outreach intents.
  - Respect governance flags and frequency caps.
- **Phase 2 – Outreach + Availability**
  - SMTP send with per-candidate substitution; delivery status logging.
  - `volunteer_availability` and day/time matching; distance scoring using zip proximity.
  - Balance controls and slate generation; admin weight tuning.
- **Phase 3 – Enrichment + Caching**
  - Precompute nightly recommendations for upcoming events; admin cache refresh.
  - Synonym/keyword management UI; industry-partner mappings.
  - Preference capture (volunteer opt-in forms) and suppression reasons.
- **Phase 4 – ML Assist (Optional)**
  - Train model on historical accept/attend to adjust weights; A/B score blending.

## Data Sources (Now and Future)

- Now: internal DB (volunteer, event participation, organizations, skills, pathways), Salesforce sync fields, Mailchimp history.
- Near-term: teacher/district relationships via events, partner org whitelist, curated keyword files.
- Future: LinkedIn public titles (manual import), enrichment APIs (Clearbit-like) subject to policy.

## Personalization Templates (Initial Set)

- Data/BI event invite, Career Jumping rotation, Classroom Speaker subject-aligned, FAFSA/Financial Literacy, Pathway Campus Visit—each with short and formal variants.

## Privacy, Policy, and Compliance

- Always honor `do_not_contact` and `email_opt_out`; suppress these from candidates.
- Provide unsubscription instructions when sending via system email, or use existing provider’s opt-out.
- Audit log for send/suppress actions; RBAC for bulk outreach.

## Metrics and Success Criteria

- Candidate precision@K vs. coordinator selections.
- Time-to-fill reduction; outreach-to-accept rate; no-show rate change.
- Diversity and first-time share adherence for targeted events.

## Testing Strategy

- Unit: scoring function, weight configs, reason generation, governance filters.
- Integration: routes produce stable JSON/HTML, CSV exports, email send stubs.
- E2E (manual): event drawer flow, selection, compose, send/export.

## Open Questions

- Do we need explicit event roles for volunteers at invite time vs. at attendance time?
- Should balance constraints be hard caps or soft targets in ranking?
- What minimum viable email provider and quota policy should we enforce?

## Acceptance Criteria (Phase 1)

- For a Data/BI event, top candidates include prior `DATA_VIZ` or `CAREER_SPEAKER` with skills {SQL, Excel, Data Analysis} or titles containing {Data, Analyst, BI}; all include explicit “why”.
- For `CAREER_JUMPING`, pool broadens across industries with a tunable first-time volunteer share; governance flags are respected; CSV export works.
- Event view shows “Find Candidates” and returns results <2s on typical datasets.
