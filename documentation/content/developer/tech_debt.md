# Tech Debt Tracker

This document tracks technical debt items identified during development that should be addressed in future iterations.

---

## ~~TD-001: Inconsistent Enum vs String Storage for Role Fields~~ *(Resolved 2026-03-01)*

`TenantRole` converted from plain class to `str, Enum`. `hasattr` workarounds removed. All 20 tenant user management tests pass.

### Related Issues

- Phase D-4 Audit Logging implementation
- Tenant user permission checks

---

## ~~TD-002: Incomplete Savepoint Recovery in Import Files~~ *(Resolved 2026-02-04)*

All Salesforce import files updated with savepoint recovery and structured error codes.

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

## ~~TD-005: EventTeacher Cannot Be Primary Until All TeacherProgress Are Linked~~ *(Resolved 2026-02-28)*

All 464 TeacherProgress linked to Teacher records. EventTeacher backfill completed (15,838+ records, 97.5% coverage). Dashboard switched to EventTeacher-primary counting. See ADR D-008.
