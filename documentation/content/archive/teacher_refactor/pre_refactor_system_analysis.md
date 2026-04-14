# Pre-Refactor System Analysis: Multiple Perspectives

**Date:** 2026-02-27
**Goal:** Identify anything beyond the teacher data system that should be addressed before or in parallel with the teacher refactor.

---

## Perspective 1: The `event.educators` Pattern is Systemic

The Event model has **four** denormalized text fields with the same anti-pattern:

| Field | Stores | Parallel FK Table |
|-------|--------|-------------------|
| `event.educators` | `;`-separated teacher names | `event_teacher` (EventTeacher) |
| `event.educator_ids` | `;`-separated teacher IDs | `event_teacher` (EventTeacher) |
| `event.professionals` | `;`-separated volunteer names | `event_volunteers` (many-to-many) |
| `event.professional_ids` | `;`-separated volunteer IDs | `event_volunteers` (many-to-many) |

The Event model source code literally has TODO comments:

```python
# line 530-537 in models/event.py
educators = db.Column(db.Text)  # Semicolon-separated list - candidate for normalization
educator_ids = db.Column(db.Text)  # Semicolon-separated list - candidate for normalization
professionals = db.Column(db.Text)  # Consider normalizing this data
professional_ids = db.Column(db.Text)  # Consider normalizing this data
```

> [!IMPORTANT]
> **Impact on Sprint 2:** When we make `EventTeacher` the source of truth for educators, we should apply the **same pattern to professionals** simultaneously. Otherwise we're solving half the problem. The `sync_educators_field()` helper should become a generic `sync_event_participant_cache(event)` that regenerates all four fields from their FK tables.

---

## Perspective 2: Route File Monoliths (Not Just `usage.py`)

Top 5 route files by size:

| File | Lines | Concern |
|------|------:|---------|
| `routes/virtual/usage.py` | 6,534 | Reports + CRUD + cache + teacher creation |
| `routes/virtual/virtual_session.py` | 4,673 | Virtual session management |
| `routes/virtual/pathful_import.py` | 2,295 | Pathful import + manual session/teacher creation |
| `routes/district/district_year_end.py` | 2,132 | Year-end reporting |
| `routes/virtual/routes.py` | 1,593 | CSV import + teacher creation |

> [!WARNING]
> **Sprint 3 scope check:** We planned to decompose `usage.py`. But `virtual_session.py` (4,673 lines) and `pathful_import.py` (2,295 lines) also contain Teacher creation logic we need to refactor. The service extraction in Sprint 1 (`teacher_service.py`) will touch all three files.

**Recommendation:** Don't decompose all the monoliths in this refactor — that's a separate project. Focus only on extracting the teacher-related logic into the service layer. The routes stay as-is but delegate to the service.

---

## Perspective 3: Thin Services Layer

Current services breakdown:

| Layer | File Count | Total Lines |
|-------|-----------|-------------|
| Models | 34 files | ~10K+ |
| Routes | 20+ files | ~25K+ |
| **Services** | **7 files** | **~600** |

The services layer is very thin — most business logic lives directly in routes. This means:
- Business logic is duplicated across routes (e.g., Teacher find-or-create in 6 places)
- Testing requires full HTTP request setup instead of clean unit tests
- Refactoring routes requires understanding all the business logic they embed

> [!IMPORTANT]
> **Sprint 1's `teacher_service.py` establishes the pattern.** After this refactor, use it as the template for future service extraction (volunteer service, event service, etc.). But don't try to do all services now.

---

## Perspective 4: Testing Coverage

Tests exist and cover the teacher domain:

| Test File | Type | What it Tests |
|-----------|------|---------------|
| `unit/models/test_teacher.py` | Unit | Teacher model |
| `unit/models/test_teacher_progress_tracking.py` | Unit | TeacherProgress model |
| `integration/test_teacher_matching.py` | Integration | Name matching logic |
| `integration/test_teachers_routes.py` | Integration | Teacher CRUD routes |
| `integration/test_roster_import.py` | Integration | Roster import upsert/merge |
| `integration/test_pathful_import.py` | Integration | Pathful import pipeline |

**What's NOT tested:**
- `teacher_matching_service.py` (no dedicated tests — only tested indirectly via integration tests)
- `compute_teacher_progress()` in the dashboard
- The `_link_progress_to_teachers()` bridge we just added
- `EventTeacher` creation/sync logic

> [!IMPORTANT]
> **Sprint 1 action:** Write tests for `teacher_service.py` from day one. This is the safest investment — a centralized service with clean unit tests will catch regressions as we refactor the routes.

---

## Perspective 5: Multi-Tenant Readiness

Current `tenant_id` coverage:

| Model | Has `tenant_id`? | Notes |
|-------|-------------------|-------|
| `Event` | ✅ Yes | Added for District Suite |
| `TeacherProgress` | ✅ Yes | Scoped to tenant |
| `Tenant` | ✅ (is the tenant) | Fully built out |
| `User` | ✅ Yes | Via tenant relationship |
| `DistrictParticipation` | ✅ Yes | |
| `RecruitmentNote` | ✅ Yes | |
| **Teacher** | ❌ No | Globally scoped |
| **Contact** (base) | ❌ No | Inherited globally |
| **School** | ❌ No | Globally scoped |

**Risk:** If a second district starts importing rosters, their teachers will share the same global `Teacher` records. This works only if teachers are unique per person, not per district. If districts need isolated views, adding `tenant_id` to Teacher becomes critical.

**Recommendation:** Add `tenant_id` to Teacher in Sprint 4 as planned, but design the query patterns now (Sprint 1) so the service layer already filters by tenant when available.

---

## Perspective 6: Database State — Fresh Start vs Migration

Given the scope of changes, here's the tradeoff:

### Option A: Incremental Migrations
- ✅ No data loss
- ✅ Can deploy changes gradually
- ❌ Need complex migration scripts for backfills
- ❌ Data quality issues from old imports carry forward
- ❌ Need to handle both old and new data shapes during transition

### Option B: Clean Slate (Teacher Tables Only)
- ✅ Clean data from the start
- ✅ No migration complexity
- ✅ Verifies full import pipeline works end-to-end
- ❌ Need to coordinate: Salesforce import → Roster import → Pathful import
- ❌ Lose manually-created sessions/teacher links

> [!IMPORTANT]
> **Recommendation: Hybrid approach.** Do incremental migrations through Sprint 1. After Sprint 2 (EventTeacher as source of truth), do a clean-slate reset of `teacher`, `teacher_progress`, and `event_teacher` tables only. Re-import from all sources. Events, volunteers, students are preserved.

---

## What Should Be Done Before the Refactor Starts

These are zero-cost preparatory steps:

1. **Run existing tests** — Establish a green baseline before any changes
2. **Run `fix_duplicate_teachers.py`** — Clean existing duplicates now
3. **Back up the database** — Snapshot before any schema changes
4. **Document current dashboard numbers** — Capture baseline metrics (teacher counts, session counts per teacher) so we can verify post-refactor

---

## What Should Be Done in Parallel (Not in the Sprint Plan)

These don't depend on the teacher refactor but would benefit from it:

| Item | Why | When |
|------|-----|------|
| **Add `event.professionals` normalization** | Same anti-pattern as `event.educators` | During Sprint 2 (free since pattern is identical) |
| **Service layer template** | Establish patterns for future services | Sprint 1 naturally creates this |
| **`pathful_import.py` cleanup** | Contains teacher creation + match_teacher | Sprint 3 partly addresses this |
| **Test coverage for teacher_matching_service.py** | Currently untested | Sprint 1 (test alongside new service) |

---

## Changes to the Sprint Plan

Based on this analysis, I recommend these updates:

1. **Sprint 1:** Add task: "Run existing tests to establish green baseline"
2. **Sprint 2:** Expand `sync_educators_field()` to also handle `professionals` and their `_ids` variants → rename to `sync_event_participant_fields(event)`
3. **Sprint 2:** Add task: "Write integration test for EventTeacher-based counting"
4. **Sprint 3:** DON'T decompose `usage.py` fully — only extract teacher logic into the service. The full monolith decomposition is a separate project.
5. **Sprint 4:** Add `tenant_id` filtering into `find_or_create_teacher()` from Sprint 1, not as a separate concern
