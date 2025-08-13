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

### Feature audit results (initial pass)

- Reports → Virtual Session Usage
  - Link to core spreadsheet: Complete (`google_sheet_url` wired into `templates/reports/virtual_usage.html`)
  - Export to Excel: Complete (`virtual_usage_export` endpoint present)
  - Caching: Present via `VirtualSessionReportCache`
- Reports → First Time Volunteer
  - Export to Excel: Complete (`/reports/first-time-volunteer/export`)
- Reports → District Year-End Detail
  - Sortable table: Complete (client-side sorting active)
- Reports → Organization Report
  - Cached results: Complete (routes wired to summary/detail caches with invalidation)
- Admin
  - Import process automation & sequential import: Complete in Admin UI (one-click sequential import). CLI tool present
  - Update local statuses: Complete (`/volunteers/update-local-statuses` + Admin button)
  - Refresh all caches: Complete (Admin action for org, virtual, first-time volunteer, district caches)
- History
  - Activity type filter: Complete (filtering supported in routes and template)
- Schools System
  - Column sort: Complete (client-side sorting on districts and schools tables)
  - Filters/Pagination: Complete (district and school filters; independent pagination)
 - Client Projects
   - Filters/Pagination: Complete (title/description, status, district, organization; paginated)
- Event Attendance Impact
  - Connect with End of Year reporting: Deferred (see `docs/planning/backlog.md`)

 Follow-ups to close for Phase B:
- [x] Implement CLI `manage_imports.py --sequential --only=<step>` with structured logging (timestamps, IDs)
- [x] Add CLI ergonomics for fast testing and selective runs:
  - [x] `--exclude <steps>` to skip specific steps during a sequential run (e.g., skip `schools,classes,students`)
  - [x] `--plan-only` to print planned steps and exit without executing (dry-run)
  - [x] `--students-max-chunks N` to limit student import to N chunks for quick verification
  - [x] `--fail-fast` to abort on first failure (optional)
- [x] Add audit logging to destructive endpoints (volunteers, events, orgs, attendance, bug, sheets, school/district)
- [x] Add explicit permission decorators/guards to destructive endpoints (tighten RBAC) using `admin_required`
- [x] Implement sortable columns in `district_year_end_detail` views
- [x] Wire `OrganizationReport` routes to use caches with invalidation controls
- [x] Add "Refresh All Caches" actions in Admin for reports/org caches
- [x] Replace legacy `pathways` import step with `pathway-events/sync-unaffiliated-events` in CLI sequence
- [x] Tests: unauthorized access (403), audit records presence for delete/purge endpoints; CLI behavior covered elsewhere

### 2) Single-click import process
- [x] Implement CLI entrypoint `manage_imports.py --sequential`
- [x] Add structured logging to imports with timestamps and IDs
- [x] Add failure handling and `--only` rerun capability
- [x] Support selective/fast testing: `--exclude`, `--plan-only`, `--students-max-chunks`, and `--fail-fast`
- [x] Write runbook section in `docs/planning/checklists.md`
- [x] Optional: cron/Task Scheduler entry for nightly runs

Acceptance criteria:
- [ ] One command performs a full import reliably
- [ ] On failure, rerun target steps is trivial; logs are sufficient
- [ ] Dry-run prints an accurate plan with resolved steps
- [ ] Selective runs skip specified heavy steps without side-effects
- [ ] Student import can be chunk-limited for rapid smoke testing

### 3) RBAC on destructive actions
- [x] Audit existing routes for delete/update risks
- [x] Add role checks or permission decorators
- [x] Add audit logging to critical operations
- [x] Add tests for unauthorized access and audit records

Acceptance criteria:
- [x] Destructive endpoints are protected and logged
- [x] Tests cover allowed/denied scenarios

## Dependencies

- Phase A CI must be active to catch regressions

## Risks

- Hidden edge cases in imports → add generous logging and retries

## Deliverables

- Updated modules, import CLI, RBAC guards, tests, and docs
