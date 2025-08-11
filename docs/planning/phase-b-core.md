---
title: "Phase B – Harden Core Functionality (Weeks 2–3)"
description: "Finish key features, import reliability, and RBAC safety"
tags: [phase-b, features, imports, rbac]
---

## Goals

- Close gaps in unfinished modules and critical workflows
- Ensure data import is reliable, observable, and recoverable
- Add role-based protections to destructive actions

## Milestones

- Week 2: Import flow complete with logging and errors surfaced
- Week 3: RBAC and feature gaps closed; tests green

## Detailed Tasks

### 1) Finish key "To Do" features
- [ ] Identify unfinished features in `docs/FEATURE_MATRIX.md` and assign owners
- [ ] For each feature:
  - [ ] Finalize UX (happy path + edge cases)
  - [ ] Add or update unit/integration tests
  - [ ] Update docs (user and dev sections)

Acceptance criteria:
- [ ] All P1 features marked complete with tests and docs

### 2) Single-click import process
- [ ] Implement CLI entrypoint `manage_imports.py --sequential`
- [ ] Add structured logging to imports with timestamps and IDs
- [ ] Add failure handling and `--only` rerun capability
- [ ] Write runbook section in `docs/planning/checklists.md`
- [ ] Optional: cron/Task Scheduler entry for nightly runs

Acceptance criteria:
- [ ] One command performs a full import reliably
- [ ] On failure, rerun target steps is trivial; logs are sufficient

### 3) RBAC on destructive actions
- [ ] Audit existing routes for delete/update risks
- [ ] Add role checks or permission decorators
- [ ] Add audit logging to critical operations
- [ ] Add tests for unauthorized access and audit records

Acceptance criteria:
- [ ] Destructive endpoints are protected and logged
- [ ] Tests cover allowed/denied scenarios

## Dependencies

- Phase A CI must be active to catch regressions

## Risks

- Hidden edge cases in imports → add generous logging and retries

## Deliverables

- Updated modules, import CLI, RBAC guards, tests, and docs
