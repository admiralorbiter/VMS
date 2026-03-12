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

---

## References

- [Import Playbook](../operations/import_playbook) — Operational procedures
- [Architecture - Sync Cadences](../technical/architecture#sync-cadences) — Integration patterns
- [Field Mappings](../technical/field_mappings) — Data transformation rules

---

*Last Updated: March 2026*
