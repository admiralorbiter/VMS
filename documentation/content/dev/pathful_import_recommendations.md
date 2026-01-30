# Pathful Import Recommendations

**Decision log and options analysis for virtual session data migration**

---

## Document Purpose

This document captures architectural decisions, options analysis, and recommendations for the Pathful import implementation. It serves as a decision log for the team and documents the rationale behind implementation choices.

**Related Documentation:**
- [Pathful Import Deployment Plan](pathful_import_deployment) — Implementation phases and tasks
- [US-304](user_stories#us-304), [US-306](user_stories#us-306) — User stories
- [FR-VIRTUAL-204](requirements#fr-virtual-204), [FR-VIRTUAL-206](requirements#fr-virtual-206) — Requirements

---

## Decision Log

### DEC-001: Consolidate US-304 and US-306 into Single Pipeline

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

Two user stories address virtual session data import:
- **US-304**: Import Pathful export into Polaris (ongoing imports)
- **US-306**: Import historical virtual data from Google Sheets (2-4 years)

The legacy workflow involved downloading Pathful data and manually reformatting it in Google Sheets before importing to Polaris.

#### Decision

Consolidate both user stories into a single Pathful-direct import pipeline.

#### Rationale

| Factor | Finding |
|--------|---------|
| Data completeness | Pathful exports contain full historical record (2-4 years) |
| Data quality | Pathful data is better structured than Google Sheets |
| Maintenance burden | Single pipeline reduces code and process complexity |
| Staff dependency | Eliminates manual reformatting step (departed staff workflow) |

#### Consequences

- US-306 acceptance criteria met by importing historical Pathful exports
- Google Sheets becomes archive only (no ongoing updates)
- Manual corrections workflow needs separate solution (see DEC-003)

---

### DEC-002: Import Pipeline Design

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

The import pipeline must satisfy requirements from both user stories:
- Idempotent (same file twice → no duplicates)
- Handle unknown teachers/events (flag, don't auto-create)
- Clear error messages for missing columns
- Preserve event-teacher relationships

#### Decision

Design import with composite key matching and explicit unmatched handling.

#### Specification

**Composite Key for Idempotency:**

```
Primary Key: (event_identifier, teacher_email, session_date)
```

Where:
- `event_identifier`: Pathful event ID or (date + title) composite
- `teacher_email`: Normalized to lowercase
- `session_date`: Date portion of session datetime

**Matching Hierarchy:**

```
1. Exact match on composite key → UPDATE existing record
2. No match on composite key → CREATE new record
3. Teacher email not in TeacherProgress → FLAG as unmatched
4. Event not found → FLAG as unmatched
```

**Record States:**

| State | Description | Action |
|-------|-------------|--------|
| Matched | Teacher and event both found | Create/update participation |
| Teacher Unmatched | Teacher not in roster | Flag row, skip participation |
| Event Unmatched | Event not found | Flag row, skip participation |
| Both Unmatched | Neither found | Flag row, skip participation |

#### Consequences

- Idempotency guaranteed by composite key
- Unmatched records visible for staff review
- No orphan records created from bad data

---

### DEC-003: Manual Corrections Workflow

**Status:** DECISION REQUIRED
**Date:** January 2026

#### Context

The legacy Google Sheets workflow allowed staff to manually correct data before import:
- Fix teacher name typos
- Mark volunteers as local vs. non-local
- Add missing information

With direct Pathful import, these corrections need a new home.

#### Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Edit in Polaris** | Staff edits teacher/volunteer records directly in Polaris after import | Clean source data; edits tracked; audit trail | Requires UI for edit fields |
| **B. Edit in Pathful** | Staff corrects data in Pathful before export | Single source of truth | May not have Pathful edit access; corrections lost if re-exported |
| **C. Corrections file** | Maintain spreadsheet of overrides applied post-import | Captures institutional knowledge; no Polaris UI changes | Another file to maintain; process complexity |
| **D. Accept as-is** | Use Pathful data without corrections initially | Fast to implement; unblocks urgent need | Data quality may suffer |

#### Recommendation

**Phase 1:** Implement Option D (accept as-is) to unblock urgent import need.
**Phase 2:** Implement Option A (edit in Polaris) as follow-up enhancement.

#### Rationale

- Urgent need is restoring import capability, not perfecting data quality
- Most Pathful data is likely correct; corrections are edge cases
- Polaris-based editing provides audit trail and doesn't require external file management
- Option C (corrections file) recreates the Google Sheets problem we're eliminating

#### Action Required

> [!WARNING]
> **Team Input Needed**
>
> Confirm with team:
> 1. What specific corrections were made in Google Sheets?
> 2. What is the impact if those corrections are missing initially?
> 3. Who needs to make corrections going forward?

#### Follow-up Tasks (if Option A selected)

| Task | Description |
|------|-------------|
| Add `is_local` field to Volunteer model | Boolean flag for local vs. non-local |
| Add edit UI for teacher name corrections | Allow staff to override imported name |
| Add edit UI for volunteer local status | Allow staff to set local flag |
| Add correction audit log | Track who changed what and when |

---

### DEC-004: Unmatched Record Handling

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

Per [FR-VIRTUAL-206](requirements#fr-virtual-206) and US-304 acceptance criteria, rows referencing unknown teachers or events must be "flagged as unmatched."

#### Decision

Create explicit unmatched record table with review workflow.

#### Specification

**Unmatched Record Storage:**

```
Table: PathfulImportUnmatched
- id: Primary key
- import_batch_id: FK to import audit log
- row_number: Original row in import file
- raw_data: JSON blob of original row
- unmatched_type: ENUM (teacher, event, both)
- teacher_email: Attempted teacher match
- event_identifier: Attempted event match
- resolution_status: ENUM (pending, resolved, ignored)
- resolution_notes: Text
- resolved_by: FK to User
- resolved_at: Timestamp
```

**Review Workflow:**

1. After import, staff sees count of unmatched rows
2. Staff navigates to unmatched review screen
3. For each unmatched row:
   - View original data
   - Option: Create teacher in roster, then re-process
   - Option: Create event, then re-process
   - Option: Mark as "ignored" with notes
4. Resolved rows removed from pending queue

#### Consequences

- Clear visibility into data quality issues
- Actionable workflow for resolving mismatches
- Audit trail of how mismatches were handled

---

### DEC-005: Historical Data Reconciliation

**Status:** CONDITIONAL
**Date:** January 2026

#### Context

If Pathful exports are missing data that existed only in Google Sheets, a reconciliation may be needed.

#### Decision

Perform reconciliation only if gaps are discovered during historical load.

#### Reconciliation Process (if needed)

| Step | Action |
|------|--------|
| 1 | Export Google Sheets data to CSV |
| 2 | Export Pathful historical data to CSV |
| 3 | Run comparison script (match on composite key) |
| 4 | Generate gap report: records in GSheets but not Pathful |
| 5 | Review gaps with team |
| 6 | If gaps are significant: create one-time corrections import |
| 7 | If gaps are minor: document and accept |

#### Trigger Conditions

Perform reconciliation if:
- Historical Pathful export has fewer events than expected
- Teacher progress calculations don't match prior reports
- Staff reports missing session history

#### Recommendation

Do not perform reconciliation proactively. Load Pathful data first, validate against known metrics, and reconcile only if discrepancies found.

---

### DEC-006: Import Source Tracking

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

During transition, records may come from different sources. Tracking source aids debugging and potential rollback.

#### Decision

Add `import_source` field to participation records.

#### Specification

```
Field: EventTeacher.import_source
Type: ENUM
Values:
- pathful_direct: Imported directly from Pathful export
- pathful_via_gsheet: Legacy import via Google Sheets (historical)
- manual_entry: Created manually in Polaris UI
- salesforce_sync: Imported from Salesforce (in-person events)
```

#### Consequences

- Can identify records by source for debugging
- Can filter/report by import source if needed
- Supports potential rollback (delete all `pathful_direct` records)

---

## Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| Q1 | What specific corrections were made in Google Sheets? | Team | OPEN |
| Q2 | What is acceptable unmatched teacher rate? | Team | OPEN |
| Q3 | Who will run imports going forward? | Team | OPEN |
| Q4 | Is Pathful API available for future automation? | Team | OPEN |
| Q5 | What is the exact Pathful export column schema? | Dev | **CLOSED** - Analyzed Session Report (19 cols) and User Report (21 cols) |

---

## Data Requirements

### Required: Pathful Export Sample

Before implementation can proceed, obtain:

1. **Fresh Pathful export file** (current data)
2. **Column header documentation** (if available from Pathful)
3. **Historical exports** (for US-306, once Phase 1 complete)

### Required: Field Mapping Confirmation

| Polaris Concept | Pathful Column | Confirmed |
|-----------------|----------------|-----------|
| Session unique ID | Session ID | ✅ |
| Session title | Title | ✅ |
| Session date | Date | ✅ |
| Session status | Status | ✅ |
| Session duration | Duration | ✅ |
| Participant name | Name | ✅ |
| Participant role | SignUp Role | ✅ |
| Participant user ID | User Auth Id | ✅ |
| School name | School | ✅ |
| District/Organization | District or Company | ✅ |
| Partner filter | Partner | ✅ (filter to "PREP-KC") |
| Student count | Registered Student Count | ✅ |
| Attended students | Attended Student Count | ✅ |
| Career category | Career Cluster | ✅ |

> [!NOTE]
> Field mapping confirmed via analysis of sample Pathful exports:
> - Session Report: 27,995 rows, 19 columns
> - User Report: 54,367 rows, 21 columns

---

## Rollback Plan

If Pathful-direct import causes issues, rollback path:

| Scenario | Rollback Action |
|----------|-----------------|
| Import creates bad data | Delete records where `import_source = 'pathful_direct'` |
| Import missing critical data | Temporarily restore Google Sheets process |
| Pathful format changes unexpectedly | Revert to prior import code version |

**Rollback window:** 30 days post-deployment

During rollback window:
- Keep Google Sheets process documented (not deleted)
- Keep old import code available (branch or feature flag)
- Monitor data quality closely

---

## Success Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Import reliability** | Successful imports / Attempted imports | >99% |
| **Data accuracy** | Records matching expected counts | >95% |
| **Unmatched rate** | Flagged records / Total records | <10% |
| **Process time** | Time from export to imported | <15 min |
| **Staff confidence** | Staff comfortable running process | 100% |

---

## Appendix: Google Sheets Deprecation Checklist

When Google Sheets workflow is fully deprecated:

- [ ] Final Google Sheets data archived
- [ ] Archive location documented
- [ ] Archive set to read-only
- [ ] Old import code removed or clearly marked deprecated
- [ ] Staff trained on new process
- [ ] Documentation updated (Architecture, Field Mappings, User Guide)
- [ ] US-306 closed with reference to Pathful implementation

---

*Last updated: January 2026*
*Version: 1.0*
