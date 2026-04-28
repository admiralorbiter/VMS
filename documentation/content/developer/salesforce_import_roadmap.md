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

### Phase 1 — Delta Reliability Hardening *(P0, ~2 hours)*

> Fix the two critical bugs that caused the April incident. Can be done in a single PR.

- [ ] **Fix watermark freeze (TD-055):** Always advance `last_sync_watermark` on sync completion, even on `failed` status. Use a wider lookback buffer (48 hours) on the next delta if the previous sync failed, to catch any records that fell in the gap.
- [ ] **Persist EP errors to DB (TD-056):** Write unmatched participation records to the existing `data_quality_flag` table (or `sync_logs.error_details`) instead of only returning them in the JSON response. Makes gaps visible without a manual DB query.

**Files to change:**
- `routes/salesforce/event_import.py` — `SyncLog` creation block (watermark logic)
- `services/salesforce/delta_sync.py` — `get_watermark()` to apply wider buffer after failure
- `services/salesforce/processors/event.py` — `process_participation_row()` error path

### Phase 2 — Retry Queue for Unresolved Participations *(P1, ~2-3 days)*

> Structural fix: instead of dropping EP records when volunteer/event lookup fails, queue them and re-attempt automatically on the next import after volunteers have been synced.

- [ ] **New model `PendingParticipationImport`** with fields: `sf_participation_id`, `sf_contact_id`, `sf_session_id`, `status`, `delivery_hours`, `first_seen_at`, `retry_count`, `last_retry_at`, `resolved_at`, `error_reason`
- [ ] **Modify `process_participation_row`** to insert to `pending_participation_imports` on lookup miss (instead of silently dropping)
- [ ] **Add `resolve_pending_participations()`** sweep at end of `import_events_from_salesforce()` — runs after all volunteers are current
- [ ] **Max retries guard:** After 10 retries, flag as likely SF orphan and surface in data quality dashboard

### Phase 3 — Import Health Dashboard *(P2, ~1 day)*

> Proactive monitoring: catch gaps before users report them.

- [ ] Add `/admin/import-health` route showing:
  - Last successful sync per type (volunteers, events, participants)
  - Count of volunteers with SF `times_volunteered > 0` but 0 local EPs
  - Count of pending retry queue entries
  - Count of orphaned EPs (event_id pointing to missing events)
- [ ] Link from existing admin dashboard sidebar

---

## Future Roadmap

### Near Future (Next Quarter)

- [ ] **Student data cleanup and reimport** *(TD-033)*
  - Delete 158,923 email records and 158,925 phone records containing the literal string `"None"`
  - Re-import students from Salesforce to back-fill real email/phone data
  - **Root cause fixed:** `Student.update_contact_info` now uses `isinstance()` guard

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
| **Phase 1** | **Delta reliability hardening** | 📋 Pending (TD-055, TD-056) |
| **Phase 2** | **Retry queue for unresolved EPs** | 📋 Pending (TD-057) |
| **Phase 3** | **Import health dashboard** | 📋 Pending |

---

## References

- [Import Playbook](../operations/import_playbook) — Operational procedures
- [Architecture - Sync Cadences](../technical/architecture#sync-cadences) — Integration patterns
- [Field Mappings](../technical/field_mappings) — Data transformation rules
- [Tech Debt Tracker](tech_debt.md) — TD-055, TD-056, TD-057

---

*Last Updated: April 2026*
