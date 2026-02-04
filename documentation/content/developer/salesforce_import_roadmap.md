# Salesforce Import Improvement Roadmap

**Status**: Active Development
**Created**: February 2026
**Owner**: Development Team

---

## Overview

This document tracks improvements to the Salesforce import system following the February 2026 retrospective. All items are actionable with clear acceptance criteria.

---

## Development Checklist

### 🔴 High Priority

- [x] **Create centralized service layer** *(Complete)*
  - ✅ Created `services/salesforce/` package structure
  - ✅ Created `services/salesforce/utils.py` for shared utilities
  - ✅ Created `services/salesforce/processors/event.py` with row processors
  - ✅ Updated `routes/salesforce/event_import.py` to import from services
  - **Verified**: Tests pass, route file reduced from 955 to 530 lines

- [x] **Consolidate duplicate helper functions** *(Complete)*
  - ✅ Added `safe_parse_delivery_hours` to `services/salesforce/utils.py`
  - ✅ Added `chunked_in_query` to `services/salesforce/utils.py`
  - ✅ Updated `event_import.py` to import from centralized location
  - **Verified**: Route imports from `services.salesforce.utils`

- [x] **Migrate Teacher import to batch commits** *(Complete)*
  - ✅ Replaced per-record `db.session.commit()` with Flush+Batch pattern
  - ✅ Using 50-record commit windows (matching other imports)
  - **Verified**: Uses `flush()` then batch commits, matching student_import.py

- [x] **Implement savepoint recovery** *(Complete)*
  - ✅ Wrapped record processing in `db.session.begin_nested()`
  - ✅ Failures skip individual records without failing batch
  - ✅ Logs skipped records with reason and Salesforce ID
  - **Applied to**: All import files (teacher, student, organization, school, volunteer, history, pathway)
  - **Note**: `event_import.py` uses processor pattern which already provides isolation

---

### 🟡 Medium Priority

- [x] **Implement structured error codes** *(Complete)*
  - ✅ Created `services/salesforce/errors.py` with `ImportErrorCode` enum
  - ✅ Created `ImportError` dataclass with code, record_id, record_name, field, message
  - ✅ Added `classify_exception()` for auto-categorization
  - **Applied to**: All import files

- [ ] **Add progress streaming for long imports**
  - Evaluate SSE vs WebSocket for real-time progress
  - Update admin dashboard to display progress bar
  - **Acceptance**: Admin sees live progress during 1000+ record imports

- [ ] **Evaluate Student import automation**
  - Document rate limit requirements
  - Test off-peak scheduling (2-4 AM)
  - Add to `--daily` preset if viable
  - **Acceptance**: Decision documented with rationale

---

### 🟢 Lower Priority

- [ ] **Standardize blueprint prefixes**
  - Audit all SF-related blueprints
  - Rename to consistent `sf_` prefix
  - Update route registrations in `routes/routes.py`
  - **Acceptance**: All SF blueprints use `sf_` prefix

- [ ] **Integrate health metrics into dashboard**
  - Add 7-day error rate trend chart
  - Add average duration by sync type
  - Add stale sync warnings
  - **Acceptance**: Metrics visible on `/admin/salesforce`

- [ ] **Add unit tests for mapper functions**
  - Create `tests/unit/services/test_salesforce_mappers.py`
  - Test all enum mappings (education, age group, race/ethnicity)
  - Test null handling and edge cases
  - **Acceptance**: >90% coverage on mapper functions

---

## Future Roadmap

### Near Future (Next Quarter)

- [ ] **Resumable imports with checkpointing**
  - Store last processed ID in SyncLog
  - Add `?resume=true` parameter to continue from checkpoint
  - Faster recovery than idempotency-based restart

- [ ] **Conflict detection dashboard**
  - Visual display of data conflicts (Polaris vs. Salesforce)
  - Allow manual resolution before overwrite
  - Audit trail of conflict resolutions

### Far Future (Backlog)

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
| Sprint 3 | Dashboard enhancements | ⬜ Not Started |

---

## References

- [Import Playbook](../operations/import_playbook) — Operational procedures
- [Architecture - Sync Cadences](../technical/architecture#sync-cadences) — Integration patterns
- [Field Mappings](../technical/field_mappings) — Data transformation rules

---

*Last Updated: February 2026*
