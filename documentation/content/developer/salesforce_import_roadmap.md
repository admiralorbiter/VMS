# Salesforce Import Improvement Roadmap

**Status**: Active Development
**Created**: February 2026
**Owner**: Development Team

---

## Overview

This document tracks improvements to the Salesforce import system following the February 2026 retrospective. All items are actionable with clear acceptance criteria.

---

## Completed Work (Feb–Mar 2026)

All 4 sprint milestones are complete. Key outcomes:

| Sprint | Focus | Key Result |
|--------|-------|------------|
| Sprint 1 | Service layer extraction | `services/salesforce/` package; route file 955 → 530 lines |
| Sprint 2 | Error handling & savepoints | `ImportErrorCode` enum, savepoint recovery in all import files |
| Sprint 3 | Dashboard enhancements | Health metrics API, 7-day trend chart, stale sync warnings |
| Sprint 4 | Integration tests & data quality | 79 tests, 52 mapper tests, `str(None)` bug fix |

**Completed items:** Centralized service layer, duplicate helper consolidation, batch commits, savepoint recovery, structured error codes, blueprint prefix standardization (`sf_*`), health metrics dashboard, mapper unit tests.

---

## April 2026 Incident: Volunteer Participation Gap

### What Happened

On 2026-04-28, two volunteers (181650 Kiera Santulli, 181652 Addison Leitch) were flagged as showing no event history in VMS despite Salesforce showing them as participants.

**Diagnosis:** A batch of 7+ volunteers imported around the same period all had 0 `EventParticipation` records in VMS. Root cause was the March 8, 2026 `daily_import` sync failing with status `failed` — which **froze the delta watermark**. Subsequent delta syncs used that stale watermark, and any participations added to Salesforce after March 8 were missed until a manual full reimport was run.

**Full scope:** 161 volunteers had `times_volunteered > 0` in Salesforce but 0 `EventParticipation` records in VMS at the time of discovery.

**Remediation:** Full reimport run 2026-04-28:
- Volunteers: 12,643 processed, 73 new, 10,469 updated
- Events: 3,450/3,450 processed
- Participants: 19,643/20,180 processed (537 errors = unmatched SF contacts)

### Three Root Causes Identified

| # | Failure Mode | Source |
|---|---|---|
| 1 | **Watermark freeze on failure** | `last_sync_watermark` only set for `success`/`partial` — a `failed` sync freezes delta at old date (TD-055) |
| 2 | **Silent EP drop** | `process_participation_row` silently drops EPs when volunteer/event lookup fails — errors only in JSON response, never persisted (TD-056) |
| 3 | **Import ordering race** | Volunteer import must run before participation import or new volunteers miss their participations permanently until next full sync (TD-057) |

---

## Remediation Plan (Active)

### Phase 1 — Delta Reliability Hardening *(✅ Complete, 2026-04-28)*

> Fixed the two critical bugs that caused the April incident.

- [x] **Fix watermark freeze (TD-055):** `last_sync_watermark` now always advances at end of every sync, regardless of status. New `recovery_buffer_hours` column (migration: `migrate_sync_log_recovery_buffer.py`): failed runs write `48`, success/partial write `1`. `SyncLog.get_watermark_with_buffer()` replaces `get_last_successful_watermark()` and applies the correct buffer on next delta. Applied to all 11 sync sites in 7 files. **Bonus:** Fixed `student_participations` sync_type key mismatch that was forcing a full 49k-record scan on every run.
- [x] **Persist EP errors to DB (TD-056):** `process_participation_row()` now writes a `DataQualityFlag` with `issue_type='unmatched_sf_participation'` on lookup miss. New `entity_sf_id` column on `DataQualityFlag`; `entity_id` made nullable. Dashboard at `/admin/data-quality` updated to render SF IDs for flags without local integer IDs. Auto-resolution on next successful import.

**Files to change:**
- `routes/salesforce/event_import.py` — `SyncLog` creation block (watermark logic)
- `services/salesforce/delta_sync.py` — `get_watermark()` to apply wider buffer after failure
- `services/salesforce/processors/event.py` — `process_participation_row()` error path

### Phase 2 — Retry Queue, Health Dashboard & N+1 Optimizations *(P1, ~2-4 days)*

> Structural fixes and performance optimizations for robust scaling.

**Part A: N+1 Elimination**
- [x] Pre-load ID caches for volunteers and events in `import_events_from_salesforce()`
- [x] Refactor `process_participation_row` to use caches, eliminating 60,000 queries per run

**Part B: TD-057 Retry Queue**
- [x] **New model `PendingParticipationImport`** with full retry lifecycle tracking (`retry_count`, `last_retry_at`, `resolved_at`)
- [x] **Modify `process_participation_row`** to insert into `pending_participation_imports` on lookup miss
- [x] **Add `resolve_pending_participations()`** sweep at the end of the import to heal orphaned records

**Part C: Import Health Dashboard**
- [x] Add `/admin/import-health` route showing sync status across all pipelines
- [x] Display recovery buffer status and pending retry queue depth

**Part D: Cleanup**
- [x] Adopt `create_sync_log_with_watermark()` across all 11 sync sites
- [x] Remove dead code (`fix_missing_participation_records()`)


## Phase 3 — Data Correctness, Observability & Performance *(Planning, 2026-04-29)*

> Derived from the 2026-04-29 Import Pipeline Audit. Full implementation plan at `brain/.../phase3_import_hardening_plan.md`.

**Sprint A — Silent Data Correctness (~1 hr):**
- [ ] **A-1:** Affiliations import — set `date_source='salesforce'` on new `VolunteerOrganization` rows (`organization_import.py`)
- [ ] **A-2:** Affiliations import — apply `STATUS_MAP` normalization before writing `vol_org.status` (`organization_import.py`)
- [ ] **A-3:** Health metrics endpoint — add `student_participations`, `unaffiliated_events`, `classes` to sync_types list; extract as single `ALL_SYNC_TYPES` constant (`routes/salesforce/routes.py`)
- [ ] **A-4:** Fix `pathway_import.py` import source for `safe_parse_delivery_hours` (use `services.salesforce.utils`, not `routes.salesforce.event_import`)

**Sprint B — Observability (~4 hrs):**
- [ ] **B-1:** Raise `DataQualityFlag(issue_type='unmatched_sf_history')` for unmatched history records instead of silently dropping them (`history_import.py` + `DataQualityIssueType`)
- [ ] **B-2:** Add pending queue breakdown to `/admin/import-health`: resolvable / orphaned / by missing side (`data_integrity.py` + template)
- [ ] **B-3:** Show import ordering staleness warning in SF dashboard when affiliations are stale relative to volunteers (`routes.py` + template)
- [ ] **B-4:** Fast-exit in `resolve_pending_participations()` when queue is empty (`processors/event.py`)

**Sprint C — Performance (~5 hrs):**
- [ ] **C-1:** Pre-load volunteer + teacher caches in history import to eliminate N+1 queries (`history_import.py`)
- [ ] **C-2:** Add `LastModifiedDate` delta sync support to `sync_unaffiliated_events` (`pathway_import.py`)
- [ ] **C-3:** Pre-load event cache and pass into `process_event_row` to eliminate per-row queries (`processors/event.py` + `event_import.py`)

**Sprint D — Architecture (~6 hrs):**
- [ ] **D-1:** Extract `_map_event_fields(event, row)` helper shared by `process_event_row` and `_create_event_from_salesforce` (`processors/event.py` + `pathway_import.py`)
- [ ] **D-2:** Extract `build_participation_caches()` to `services/salesforce/utils.py`; use in both `event_import.py` and `pathway_import.py`
- [ ] **D-3:** Add chunked commits (every 500) inside `resolve_pending_participations()` sweep (`processors/event.py`)

---

## Future Roadmap

### Near Future (Next Quarter)

- [x] ~~**Student data cleanup and reimport** *(TD-033)*~~ — **Resolved 2026-03-13**
  - ~~Delete 158,923 email records and 158,925 phone records containing the literal string `"None"`~~
  - ~~Re-import students from Salesforce to back-fill real email/phone data~~
  - 317K garbage records deleted. Import guard (`isinstance()` check) in place. Data quality rescan shows 0 `str(None)` records.

- [x] ~~Salesforce data quality investigation~~ *(TD-034)* — **Resolved Mar 2026**
  - Skeleton addresses: 4,630 deleted, import guard added
  - ALL CAPS names: `smart_title_case()` in import; 18,814 normalized on next sync
  - Truncated skills: `Skill.name` widened 50→200 chars
  - Connector data: `ConnectorData` model removed, `PathfulUserProfile` used instead
  - Missing org type: defaulted to "Other" + flagged via Data Quality system
  - Data Quality Dashboard: live at `/admin/data-quality`

- [ ] **Background task execution for large imports**
  - Move long-running imports to background worker (threading or Celery)
  - Add status polling endpoint (`GET /import-status/{id}`)
  - Simpler than SSE/WebSocket, more Flask-native

- [ ] **Resumable imports with checkpointing**
  - Store last processed ID in SyncLog
  - Add `?resume=true` parameter to continue from checkpoint
  - Faster recovery than idempotency-based restart

- [ ] **Data Quality Platform** *(Epic)*
  - Extend the Data Quality Dashboard beyond Salesforce to cover all data sources (Pathful, Google Sheets, manual entry)
  - Auto-detect new issue types: duplicate contacts, orphaned records, stale data
  - Resolution workflows: bulk fix, merge duplicates, link to source for correction
  - Trend tracking: data quality score over time, improvement metrics
  - Integration with import pipelines: flag issues in real-time during import

- [ ] **Conflict detection dashboard**
  - Visual display of data conflicts (Polaris vs. Salesforce)
  - Allow manual resolution before overwrite
  - Audit trail of conflict resolutions

### Far Future (Backlog)

- [ ] **Salesforce Change Data Capture (CDC)**
  - Subscribe to SF CDC event stream for near real-time sync (< 1 min latency)
  - Eliminates polling lag and import ordering races entirely
  - **Not recommended now** — requires persistent websocket worker + SF org licensing. Revisit if sync frequency needs to exceed 4x/day.

- [ ] **Multi-tenant import isolation**
  - District-specific import configurations
  - Tenant-scoped sync logs
  - Separate import schedules per tenant

- [ ] **Machine learning for data quality**
  - Auto-detect anomalies in imported data
  - Suggest data cleansing rules
  - Pattern recognition for duplicate detection

---

## Not Planned

The following were considered but are **not currently feasible**:

| Feature | Reason |
|---------|--------|
| Import scheduling UI | Scheduler infrastructure needed first |
| Bidirectional sync | Requires SF write permissions & conflict rules |
| Webhook-triggered imports | SF outbound message setup TBD |
| Import analytics dashboard | Lower priority than functional improvements |

---

## Progress Tracking

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Service layer extraction | ✅ Complete |
| Sprint 2 | Error handling & savepoints | ✅ Complete |
| Sprint 3 | Dashboard enhancements | ✅ Complete |
| Sprint 4 | Integration tests & data quality | ✅ Complete (79 tests, `str(None)` bug fix) |
| **Phase 1** | **Delta reliability hardening** | ✅ **Complete 2026-04-28** (TD-055, TD-056 + bonus watermark key fix) |
| **Phase 2** | **Retry Queue, Health Dashboard, Optimizations** | ✅ Complete (TD-057) |
| **Phase 3** | **Data Correctness, Observability & Performance** | 🔵 Planning (audit 2026-04-29) |

---

## References

- [Import Playbook](../operations/import_playbook) — Operational procedures
- [Architecture - Sync Cadences](../technical/architecture#sync-cadences) — Integration patterns
- [Field Mappings](../technical/field_mappings) — Data transformation rules
- [Tech Debt Tracker](tech_debt.md) — TD-055, TD-056, TD-057
- [Phase 3 Implementation Plan](../../../brain/eae6a31f.../phase3_import_hardening_plan.md) — Detailed sprint tasks

---

*Last Updated: April 29, 2026 — Phase 3 planning complete.*
