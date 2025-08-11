---
title: "Foundation-to-Finish Plan (Index)"
description: "Ordered, actionable roadmap with phased breakdowns and checklists"
tags: [planning, roadmap, execution, phases]
---

## Purpose

A clear, chronologically ordered roadmap from baseline to release, split into executable phase docs with detailed subtasks and acceptance criteria.

## Timeline Overview

- Week 1: Phase A – Establish Baseline
- Weeks 2–3: Phase B – Harden Core Functionality
- Weeks 3–4: Phase C – Documentation Deep-Dive
- Week 5: Phase D – Ops & QA
- Week 6: Phase E – Release Prep

## Current State Snapshot

| Area | Strengths | Gaps & Risks |
|------|-----------|--------------|
| Feature coverage | Strong event/org/volunteer reporting | Import automation and some modules unfinished (e.g. Schools, Client Projects) |
| README | Setup & stack described | Missing architecture overview, data flow, contributor info |
| Testing & CI | pytest exists | No lint/type CI; no coverage gate |
| Data sync | Salesforce + spreadsheet partial | Sequential import and error alerting incomplete |
| Documentation tooling | Markdown | No consistent structure, AI-readable cues, or doc site generation |

## Phased Plan (detailed in separate docs)

- Phase A – Baseline: `docs/planning/phase-a-baseline.md`
- Phase B – Harden Core: `docs/planning/phase-b-core.md`
- Phase C – Documentation: `docs/planning/phase-c-documentation.md`
- Phase D – Ops & QA: `docs/planning/phase-d-ops-qa.md`
- Phase E – Release Prep: `docs/planning/phase-e-release-prep.md`

## Workstreams and Backlog

- Backlog and non-blocking improvements: `docs/planning/backlog.md`
- Checklists (PR, feature spec, runbooks): `docs/planning/checklists.md`
- Tooling deep dive and configs: `docs/planning/tooling.md`

## This Week’s Action Items

- Create missing planning subdocs and link them here
- Enable pre-commit and CI lint/test
- Assign owners for incomplete features in `docs/FEATURE_MATRIX.md`
- Draft Mermaid system diagram in `docs/02-architecture.md`
- Write first ADR: “Why SQLite with Salesforce Sync” (see `docs/templates/adr.md`)

## Outcome

- Complete unfinished key functionality
- AI-usable, human-readable documentation
- Automated dev pipeline with tests and lint
- Clear release scope and notes