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

- [ ] **Create centralized service layer**
  - Extract import logic from route files to `services/salesforce/processors/`
  - Create `services/salesforce/utils.py` for shared utilities
  - Keep routes as thin HTTP handlers only
  - **Acceptance**: Routes only handle request/response, all logic in services

- [ ] **Consolidate duplicate helper functions**
  - Audit: `safe_parse_delivery_hours`, date parsers, null-safety helpers
  - Move to `services/salesforce/utils.py`
  - Update all import modules to use centralized versions
  - **Acceptance**: `grep` returns single definition per helper

- [ ] **Migrate Teacher import to batch commits**
  - Replace per-record `db.session.commit()` with Flush+Batch pattern
  - Use 50-record commit windows (matching other imports)
  - **Acceptance**: Teacher import uses same commit pattern as Student import

- [ ] **Implement savepoint recovery**
  - Wrap individual record processing in `db.session.begin_nested()`
  - Allow skipping malformed records without failing entire batch
  - Log skipped records with reason
  - **Acceptance**: Single bad record doesn't fail entire import

---

### 🟡 Medium Priority

- [ ] **Add dry-run mode to HTTP routes**
  - Add `?dry_run=true` parameter to all import endpoints
  - Return what would be changed without committing
  - **Acceptance**: Dry-run returns preview of changes

- [ ] **Implement structured error codes**
  - Define error taxonomy (e.g., `MISSING_SF_ID`, `INVALID_DATE`, `FK_NOT_FOUND`)
  - Create `ImportError` dataclass with code, record_id, field, message
  - Update all import modules to use structured errors
  - **Acceptance**: API responses include machine-parseable error codes

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
| Sprint 1 | Service layer extraction | ⬜ Not Started |
| Sprint 2 | Error handling & savepoints | ⬜ Not Started |
| Sprint 3 | Dashboard enhancements | ⬜ Not Started |

---

## References

- [Import Playbook](../operations/import_playbook) — Operational procedures
- [Architecture - Sync Cadences](../technical/architecture#sync-cadences) — Integration patterns
- [Field Mappings](../technical/field_mappings) — Data transformation rules

---

*Last Updated: February 2026*
