# Retrospective: Teacher Data Linking Fix

**Date:** 2026-02-27
**Sprint/Work:** Teacher Import & Dashboard Consistency

---

## Summary

Diagnosed and fixed a data disconnection between two teacher systems: `TeacherProgress` (from district spreadsheet imports) and `Teacher` (from Pathful/Salesforce imports). Teachers added to sessions via the UI weren't appearing in the teacher usage dashboard because the dashboard only matched sessions through the `event.educators` text field, ignoring `EventTeacher` records.

## What We Found

### Root Cause: Two Disconnected Data Systems

```
┌──────────────────────┐         ┌──────────────────────┐
│   TeacherProgress    │         │      Teacher         │
│   (Spreadsheet)      │         │   (Pathful/SF)       │
│                      │  NO     │                      │
│  name: "Michelle     │──LINK──▶│  first_name: MICHELLE│
│        Michalski"    │         │  last_name: MICHALSKI│
│  building: TA Edison │         │  school_id: NULL     │
│  teacher_id: NULL    │         │                      │
│  email: M.M@kckps    │         │                      │
└──────────────────────┘         └──────────────────────┘
```

**Data stats before fix:**
| Metric | Count |
|--------|-------|
| TeacherProgress records | 464 |
| TeacherProgress linked to Teacher | 0 (0%) |
| Teacher records | 9,692 |
| Teachers without `school_id` | 5,846 (60%) |

### Secondary Issue: Dashboard Session Matching

The teacher usage dashboard (`tenant_teacher_usage.py`) only matched sessions using the `event.educators` text field (semicolon-separated names from Pathful). When sessions were manually created or teachers were added via the edit page, they used `EventTeacher` records but NOT the educators text field — so they were invisible to the dashboard.

## What We Fixed

### 1. Teacher Linking on Import (`roster_import.py`)
- Added `_link_progress_to_teachers()` — matches by first/last name, sets `teacher_id`
- Added `_find_school_by_building_name()` — fuzzy-matches abbreviated building names to full School names
- Runs automatically after every roster import

### 2. Dashboard Session Display (`tenant_teacher_usage.py`)
- `teacher_detail()` now queries BOTH `EventTeacher` records AND `event.educators` text (with dedup)
- `compute_teacher_progress()` now counts EventTeacher-linked sessions in dashboard totals

## Results After Fix

| Metric | Before | After |
|--------|--------|-------|
| TeacherProgress linked | 0 | **280** (60%) |
| Teacher school_ids set | — | **56** |
| Michelle's sessions shown | 19 | **20** |
| "Black History Month" in dashboard | ❌ No | ✅ Yes |

## What Went Well

- **Investigation approach was thorough** — writing scripts to query the DB directly revealed the full scope of the disconnection
- **Fuzzy school matching** was effective — 28/28 building names now match (KCKPS schools seeded in Sprint 4.4)
- **Minimal code changes** — two files modified, existing architecture leveraged

## What Could Be Better

### Open Items / Known Gaps

1. **184 unlinked TeacherProgress records** — These teachers exist only in the spreadsheet and have no `Teacher` entity. They'll auto-link if/when they appear in a Pathful session. *(Partially addressed: email-first matching added in Sprint 1.)*

2. ~~**3 missing School records** — Douglass, Grant, and JFK~~ ✅ **Resolved in Sprint 4.4.** All 28 KCKPS schools created.

3. **Name-based matching limitations** — Matching by first/last name can have issues with:
   - Name variations (e.g., "MICHELLE" vs "Michelle" — handled via case-insensitive)
   - Name duplicates (two teachers with same name — `.first()` picks one arbitrarily)
   - Middle names or suffixes — not currently handled

4. **`event.educators` vs `EventTeacher` duality** — Tracked as [TD-005](../developer/tech_debt.md#td-005). Currently using text-primary + EventTeacher-supplementary counting. EventTeacher-only simplification deferred until backfill.

5. ~~**Dashboard counting accuracy**~~ ✅ **Resolved.** Dedup via `matched_event_ids` prevents double-counting between text and EventTeacher paths.

## Lessons Learned

1. **When two systems store the same data independently, they WILL drift.** The Teacher/TeacherProgress separation was a design choice, but without a linking mechanism, it created invisible data silos.

2. **Investigate before fixing.** Running DB queries to understand the actual data state (not just the code) was critical to finding the real root cause vs. what we initially assumed.

3. **The "simple" fix (just set school_id) wasn't enough.** The dashboard display issue was a separate symptom of the same root cause — needed to fix data layer AND presentation layer.
