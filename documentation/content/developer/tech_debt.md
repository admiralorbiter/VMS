# Tech Debt Tracker

This document tracks technical debt items identified during development that should be addressed in future iterations.

---

## TD-001: Inconsistent Enum vs String Storage for Role Fields

**Created:** 2026-02-02
**Priority:** Low
**Category:** Code Consistency / Type Safety

### Description

The codebase has inconsistent handling of enumerated fields:

| Field | Model | Storage Type |
|-------|-------|--------------|
| `EventStatus` | Event | Python Enum |
| `EventType` | Event | Python Enum |
| `CancellationReason` | Event | Python Enum |
| `tenant_role` | User | Plain String |

This inconsistency led to a bug where `audit_service.py:_get_user_role()` called `.value` on `tenant_role`, expecting it to be an enum.

### Root Cause

`tenant_role` was originally designed as a simple string field for flexibility, while Event fields were designed with stricter type safety using enums.

### Current Workaround

Added `hasattr` checks throughout the codebase:
```python
role_value = tenant_role.value if hasattr(tenant_role, 'value') else str(tenant_role)
```

### Proposed Solutions

**Option A: Convert `tenant_role` to Enum (Recommended)**
- Create `TenantRole` enum in `models/user.py`
- Add migration to convert existing string values
- Update all references to use enum
- Pros: Type safety, IDE autocomplete, consistent with Event model patterns
- Cons: Requires migration, more boilerplate

**Option B: Document String-Only Pattern**
- Add clear docstrings noting `tenant_role` is a string
- Add type hints: `tenant_role: Optional[str]`
- Pros: No migration needed
- Cons: Doesn't address underlying inconsistency

### Files Affected

- `models/user.py` - `tenant_role` field definition
- `services/audit_service.py` - `_get_user_role()` function
- `services/scoping.py` - Role checking functions
- Any future code that accesses `user.tenant_role`

### Related Issues

- Phase D-4 Audit Logging implementation
- Tenant user permission checks

---

## ~~TD-002: Incomplete Savepoint Recovery in Import Files~~ *(Resolved)*

**Created:** 2026-02-04
**Resolved:** 2026-02-04
**Category:** Data Integrity / Error Handling

### Resolution

All Salesforce import files have been updated with:
- Savepoint recovery using `db.session.begin_nested()`
- Structured error codes using `ImportErrorCode` enum and `ImportError` dataclass

Files updated: `volunteer_import.py`, `history_import.py`, `pathway_import.py`, `teacher_import.py`, `student_import.py`, `organization_import.py`, `school_import.py`

See [Salesforce Import Roadmap](salesforce_import_roadmap.md) for details.

---

*Add new tech debt items below following the same format.*

---

## TD-003: `Teacher.school_id` Has No FK Constraint

**Created:** 2026-02-28
**Priority:** Low
**Category:** Data Integrity / Schema

### Description

`Teacher.school_id` is `String(255)` with no `ForeignKey('school.id')`. Existing values are Salesforce contact IDs that mostly don't resolve to valid `School` records. Used in 40+ places in `routes/virtual/usage.py`.

### Current Workaround

Code does `School.query.get(teacher.school_id)` and handles `None` gracefully.

### Proposed Fix

Add `ForeignKey('school.id')`. Requires a data migration to clean up invalid values first.

**Risk:** High — many callsites, requires data migration.

---

## TD-004: `Event.district_partner` Is a Text Field, Not a FK

**Created:** 2026-02-28
**Priority:** Low
**Category:** Data Normalization

### Description

Events store the district name as a plain text string (`Event.district_partner`), not a FK to the `District` table. Used in 50+ places for filtering across `usage.py`, `pathful_import.py`, `tenant_teacher_usage.py`.

### Current Workaround

Text matching works — filtering by `Event.district_partner == district_name`. Just not normalized.

### Proposed Fix

Replace with `district_id` FK to `District`. Requires updating all filtering logic across the codebase.

**Risk:** Very high — most pervasive data pattern in the codebase.

---

## ~~TD-005: EventTeacher Cannot Be Primary Until All TeacherProgress Are Linked~~ *(Resolved)*

**Created:** 2026-02-28
**Resolved:** 2026-02-28
**Category:** Data Architecture

### Resolution

1. Created 184 missing Teacher records from unlinked TeacherProgress data
2. All 464 TeacherProgress now have `teacher_id` (100% linking)
3. EventTeacher backfill: 15,838+ records (97.5% event coverage)
4. Dashboard switched to EventTeacher-primary, text-supplementary
5. Verified: 162 goals achieved (matches expected ±1 due to new Teacher matches)

See ADR D-008.
