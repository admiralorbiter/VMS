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

**Status:** DECIDED
**Date:** January 2026 (Updated)

#### Context

The legacy Google Sheets workflow allowed staff to manually correct data before import:
- Fix teacher name typos
- Mark volunteers as local vs. non-local
- Add missing information
- Set cancellation reasons

With direct Pathful import, these corrections need a new home.

#### Decision

**Two-phase approach:**

| Phase | Approach | Status |
|-------|----------|--------|
| Phase 1 | Accept Pathful data as-is, flag issues for review | ✅ Implemented |
| Phase 2 | Enable post-import editing in Polaris with audit trail | 🔄 In Progress |

#### Phase 2 Specification

Post-import data management will be handled in Polaris with:

1. **Auto-flagging** of issues that need attention (see DEC-007)
2. **Cancellation reasons** for sessions that didn't occur (see DEC-008)
3. **District admin access** to edit their schools' data (see DEC-009)
4. **Audit logging** of all changes (see DEC-010)

#### Consequences

- Staff and district admins can correct data without external spreadsheets
- All corrections have audit trail
- Original Pathful data preserved (changes tracked separately)
- Reports can show data provenance

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

### DEC-007: Post-Import Data Management Workflow

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

After Pathful import, data may need corrections or additional information:
- Events imported as "Draft" but date has passed
- Missing teacher/presenter assignments
- Sessions that were cancelled need reasons documented
- Teacher progress calculations need verification

Currently there is no defined workflow for addressing these issues.

#### Decision

Implement a post-import data management workflow with auto-flagging and review queues.

#### Specification

**Auto-Flag Conditions:**

| Condition | Flag Type | Assigned To |
|-----------|-----------|-------------|
| Event status = Draft AND session_date < today | `NEEDS_ATTENTION` | Staff |
| Event has no teachers tagged | `MISSING_TEACHER` | District Admin |
| Event has no presenter tagged | `MISSING_PRESENTER` | Staff |
| Event status = Cancelled AND cancellation_reason is NULL | `NEEDS_REASON` | Staff |
| Unmatched teacher in import | `UNMATCHED_TEACHER` | Staff (existing) |
| Unmatched volunteer in import | `UNMATCHED_VOLUNTEER` | Staff (existing) |

**Flag Model:**

```python
class EventFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    flag_type = db.Column(db.String(50), nullable=False)  # ENUM values above
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))  # 'system' or user_id
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
```

**Review Queue UI:**

| View | Audience | Shows |
|------|----------|-------|
| `/virtual/flags/all` | Staff | All flags across all districts |
| `/virtual/flags/district/<id>` | District Admin | Flags for their district only |
| `/virtual/pathful/unmatched` | Staff | Unmatched records (existing) |

#### Workflow

```
Import completes
      ↓
System scans for flag conditions
      ↓
Flags created automatically
      ↓
Staff/District Admin sees flag queue
      ↓
User resolves issue (edit event, tag teacher, set reason)
      ↓
Flag marked resolved with notes
      ↓
Audit log entry created
```

#### Consequences

- Issues are visible immediately after import
- Clear ownership of who should address each issue type
- Resolution is tracked and auditable
- Reports can exclude flagged/unresolved data if needed

---

### DEC-008: Cancellation Reason Tracking

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

Virtual sessions are sometimes cancelled. Pathful shows status as "Cancelled" but doesn't capture why. Understanding cancellation reasons helps with:
- Identifying patterns (e.g., frequent presenter cancellations)
- Accurate reporting (exclude cancelled sessions appropriately)
- Historical documentation

#### Decision

Add cancellation reason field to Event model with predefined options.

#### Specification

**Cancellation Reasons (ENUM):**

| Value | Display Name | Description |
|-------|--------------|-------------|
| `WEATHER` | Weather / Snow Day | School closed due to weather |
| `PRESENTER_CANCELLED` | Presenter Cancelled | Volunteer/presenter unable to attend |
| `TEACHER_CANCELLED` | Teacher Cancelled | Teacher unable to host session |
| `SCHOOL_CONFLICT` | School Conflict | Assembly, testing, or other school event |
| `TECHNICAL_ISSUES` | Technical Issues | Platform or connectivity problems |
| `LOW_ENROLLMENT` | Low Enrollment | Not enough student signups |
| `SCHEDULING_ERROR` | Scheduling Error | Double-booked or incorrectly scheduled |
| `OTHER` | Other | See notes for details |

**Model Changes:**

```python
class CancellationReason(enum.Enum):
    WEATHER = "Weather / Snow Day"
    PRESENTER_CANCELLED = "Presenter Cancelled"
    TEACHER_CANCELLED = "Teacher Cancelled"
    SCHOOL_CONFLICT = "School Conflict"
    TECHNICAL_ISSUES = "Technical Issues"
    LOW_ENROLLMENT = "Low Enrollment"
    SCHEDULING_ERROR = "Scheduling Error"
    OTHER = "Other"

# Add to Event model:
cancellation_reason = db.Column(db.Enum(CancellationReason), nullable=True)
cancellation_notes = db.Column(db.Text, nullable=True)  # Required if OTHER
cancellation_set_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
cancellation_set_at = db.Column(db.DateTime, nullable=True)
```

**Business Rules:**

1. `cancellation_reason` only valid when `status = CANCELLED`
2. If `cancellation_reason = OTHER`, then `cancellation_notes` is required
3. Setting cancellation reason creates audit log entry
4. Auto-flag created if status is CANCELLED but reason is NULL

#### Consequences

- Standardized reasons enable reporting and pattern analysis
- "Other" option with notes handles edge cases
- Audit trail shows who set the reason and when

---

### DEC-009: District Admin Virtual Data Access

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

District administrators need to help manage virtual session data for their schools:
- Tag teachers to sessions
- Tag presenters to sessions
- Set cancellation reasons
- Verify data accuracy for reports

Currently only PrepKC staff can edit virtual event data.

#### Decision

Grant district admins scoped edit access to virtual events at their district's schools.

#### Specification

**Access Scope:**

| User Role | Can View | Can Edit | Scope |
|-----------|----------|----------|-------|
| Staff (Admin/User) | All events | All events | Global |
| District Admin | Their district's events | Their district's events | District-scoped |
| District Viewer | Their district's events | None | Read-only |
| Teacher | Their sessions only | None (flag only) | Self only |

**Scoping Logic:**

```python
def get_district_events(user):
    """Return events scoped to user's district(s)."""
    if user.role in ['admin', 'user']:
        return Event.query.filter_by(type=EventType.VIRTUAL_SESSION)

    if user.role == 'district_admin':
        # Get schools in user's district(s)
        district_ids = [d.id for d in user.districts]
        school_ids = School.query.filter(
            School.district_id.in_(district_ids)
        ).with_entities(School.id).all()

        # Get events at those schools
        return Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.school_id.in_(school_ids)
        )

    return Event.query.filter(False)  # No access
```

**Editable Fields (District Admin):**

| Field | Editable | Notes |
|-------|----------|-------|
| Teachers (tag/untag) | ✅ Yes | Can add/remove teacher associations |
| Presenters (tag/untag) | ✅ Yes | Can add/remove presenter associations |
| Cancellation reason | ✅ Yes | Can set/change reason |
| Event status | ⚠️ Limited | Can change Draft→Cancelled only |
| Event title | ❌ No | Owned by Pathful import |
| Event date | ❌ No | Owned by Pathful import |
| Student counts | ❌ No | Owned by Pathful import |

**UI Changes:**

1. Add district filter to `/virtual/pathful/events`
2. Add "My District" view for district admins
3. Edit buttons visible only for authorized events
4. Audit log shows editor identity and role

#### Consequences

- District admins can self-serve data corrections
- PrepKC staff workload reduced
- All edits tracked with user identity
- Original Pathful data preserved

---

### DEC-010: Audit Logging for Virtual Event Changes

**Status:** RECOMMENDED
**Date:** January 2026

#### Context

With multiple user types editing virtual event data (staff and district admins), we need to track:
- Who made changes
- What was changed
- When changes occurred
- Distinguish staff changes from district admin changes

#### Decision

Implement comprehensive audit logging for virtual event changes.

#### Specification

**Audit Log Model:**

```python
class VirtualEventAuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

    # Who
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)  # admin, user, district_admin
    user_district_id = db.Column(db.Integer, nullable=True)  # If district_admin

    # What
    action = db.Column(db.String(50), nullable=False)  # See action types below
    field_name = db.Column(db.String(100), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)

    # When
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Context
    source = db.Column(db.String(50), default='manual')  # manual, import, system
    notes = db.Column(db.Text, nullable=True)
```

**Action Types:**

| Action | Description |
|--------|-------------|
| `TEACHER_ADDED` | Teacher tagged to event |
| `TEACHER_REMOVED` | Teacher untagged from event |
| `PRESENTER_ADDED` | Presenter tagged to event |
| `PRESENTER_REMOVED` | Presenter untagged from event |
| `STATUS_CHANGED` | Event status modified |
| `CANCELLATION_REASON_SET` | Cancellation reason added/changed |
| `FLAG_RESOLVED` | Event flag marked resolved |
| `IMPORTED` | Event created/updated via import |

**Audit Views:**

| Route | Audience | Purpose |
|-------|----------|---------|
| `/virtual/audit/event/<id>` | Staff | Full history for one event |
| `/virtual/audit/recent` | Staff | Recent changes across all events |
| `/virtual/audit/district/<id>` | Staff | Changes by district admin users |
| `/virtual/audit/user/<id>` | Staff | Changes by specific user |

**Reporting Integration:**

- Reports can filter by `source` to show only import data vs. manual edits
- Reports can show "last modified by" for transparency
- Discrepancy reports can compare original import values vs. current values

#### Consequences

- Full accountability for all changes
- Can distinguish staff vs. district admin edits
- Supports compliance and data quality audits
- Enables rollback if incorrect changes made

---

## Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| Q1 | What specific corrections were made in Google Sheets? | Team | **CLOSED** — Captured in DEC-003, DEC-007, DEC-008 |
| Q2 | What is acceptable unmatched teacher rate? | Team | OPEN |
| Q3 | Who will run imports going forward? | Team | OPEN |
| Q4 | Is Pathful API available for future automation? | Team | OPEN |
| Q5 | What is the exact Pathful export column schema? | Dev | **CLOSED** |
| Q6 | Should district admins be notified of new flags? | Team | OPEN |
| Q7 | What is the retention period for audit logs? | Team | OPEN |

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

- [ ] Final Google Sheets data archived *(User Action)*
- [ ] Archive location documented *(User Action)*
- [ ] Archive set to read-only *(User Action)*
- [x] Old import code marked deprecated (Playbook C marked deprecated in import_playbook.md)
- [ ] Staff trained on new process *(User Action)*
- [x] Documentation updated (Architecture, Field Mappings, User Guide)
  - Updated: `user_guide/pathful_import.md` (new)
  - Updated: `user_guide/virtual_events.md`
  - Updated: `import_playbook.md` (Playbook A, C)
  - Updated: `dev/pathful_import_deployment.md`
- [x] US-306 consolidated into US-304 (Pathful direct import)

---

*Last updated: January 30, 2026*
*Version: 1.1 — Deprecation checklist updated*
