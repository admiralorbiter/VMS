# Architecture Decision Records

Index of Architecture Decision Records (ADRs) for the VMS/Polaris system.

ADRs are immutable records of significant technical decisions that capture context, decision, and consequences.

---

## ADR Directory

### Global System Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| G-001 | Flask as Web Framework | ✅ Accepted | 2024-01 |
| G-002 | SQLite as Primary Database | ✅ Accepted | 2024-01 |
| G-003 | Vanilla JavaScript Frontend | ✅ Accepted | 2024-02 |

### Validation System Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| V-001 | 5-Tier Validation Architecture | ✅ Accepted | 2024-06 |
| V-002 | Quality Scoring Algorithm | ✅ Accepted | 2024-08 |
| V-003 | Business Rule Engine | ✅ Accepted | 2024-09 |

### Data Integration Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| D-001 | Salesforce API (Simple-Salesforce) | ✅ Accepted | 2024-03 |
| D-002 | Google Sheets Integration | ✅ Accepted | 2024-03 |
| D-003 | Daily Sync with Conflict Resolution | ✅ Accepted | 2024-04 |
| D-004 | Auto-Link TeacherProgress to Teacher on Import | ✅ Accepted | 2026-02 |

### GUI Enhancement Decisions

| ID | Decision | Status | Date |
|----|----------|--------|------|
| U-001 | Mobile-First Responsive Design | ✅ Accepted | 2024-05 |
| U-002 | Custom CSS Design System | ✅ Accepted | 2024-05 |

---

## ADR Numbering Convention

| Prefix | Category |
|--------|----------|
| G-XXX | Global system decisions |
| V-XXX | Validation system decisions |
| D-XXX | Data integration decisions |
| U-XXX | User interface decisions |
| P-XXX | Performance decisions |
| S-XXX | Security decisions |

---

## ADR Lifecycle

| State | Description |
|-------|-------------|
| Proposed | Under consideration |
| Accepted | Approved and implemented |
| Deprecated | Superseded by newer approach |
| Archived | No longer relevant |

---

## Recent Decisions

### 2025-08-17: Removed Salesforce Pathway Import System

**Decision:** Remove complex Salesforce pathway import; replace with simpler event affiliation via `pathway_events.py`.

**What Was Removed:**
- `models/pathways.py` — Complex Pathway model
- `routes/pathways/` — Entire pathways blueprint
- `routes/reports/pathways.py` — Pathway reports
- Database tables: `pathway_contacts`, `pathway_events`

**What Was Kept:**
- `routes/events/pathway_events.py` — Unaffiliated event sync
- Simple `pathway` field in `EventAttendanceDetail`
- Pathway event types (`PATHWAY_CAMPUS_VISITS`, `PATHWAY_WORKPLACE_VISITS`)

**Benefits:**
- Simpler, maintainable codebase
- Focus on actual data relationships
- Reduced database complexity

---

### 2026-02-27: D-004 — Auto-Link TeacherProgress to Teacher on Import

**Context:** The teacher roster import (`utils/roster_import.py`) created `TeacherProgress` records from district spreadsheets but never linked them to `Teacher` records (created separately by Pathful/Salesforce imports). This caused:
- `TeacherProgress.teacher_id` was always `None` (0/464 linked)
- `Teacher.school_id` was `None` for 60% of records (5,846/9,692)
- Manually-added session teachers didn't appear in the teacher usage dashboard
- The two data systems (spreadsheet imports vs session imports) were completely disconnected

**Decision:** Add an automatic post-import linking step to `import_roster()` that:
1. Matches `TeacherProgress` → `Teacher` by first/last name (case-insensitive)
2. Sets `Teacher.school_id` by fuzzy-matching the `building` name to the School table
3. Also updates `teacher_detail` and `compute_teacher_progress` to use both `EventTeacher` records AND `event.educators` text field for session matching

**Consequences:**
- ✅ 280/464 TeacherProgress records now linked to Teacher entities
- ✅ 56 Teacher `school_id` values automatically set
- ✅ Dashboard now shows sessions from both import paths (Pathful text matching + EventTeacher DB links)
- ⚠️ 184 TeacherProgress records remain unlinked (no matching Teacher entity exists — these teachers haven't appeared in any Pathful session)
- ⚠️ 3 buildings (Douglass, Grant, JFK) have no School record and are skipped

**Files Changed:**
- `utils/roster_import.py` — `_find_school_by_building_name()`, `_link_progress_to_teachers()`
- `routes/district/tenant_teacher_usage.py` — `teacher_detail()`, `compute_teacher_progress()`

---

### 2026-02-27: D-005 — Sprint 1: Centralized Teacher Service + Model Hardening

**Context:** Teacher records were created inline across 5+ route files (`routes/virtual/routes.py`, `usage.py`, `pathful_import.py`, etc.) using inconsistent matching logic. This caused duplicates and made the system fragile. Name matching in `roster_import.py` used raw `func.lower()` instead of the shared `normalize_name()` function.

**Decision:**
1. Create `services/teacher_service.py` with a single `find_or_create_teacher()` entry point using prioritized matching: `salesforce_individual_id` → email → normalized name
2. Add `cached_email` column to Teacher (named `cached_email` instead of `primary_email` to avoid shadowing the existing `Contact.primary_email` property)
3. Add `import_source` column to Teacher for data provenance tracking
4. Add `UniqueConstraint('tenant_id', 'email', 'academic_year')` to TeacherProgress
5. Refactor `_link_progress_to_teachers()` to use email-first matching + shared `normalize_name()`

**Consequences:**
- ✅ Single entry point for all teacher creation — future sprints wire routes through the service
- ✅ Email matching is now the primary strategy (higher confidence than name matching)
- ✅ TeacherProgress duplicates prevented at the DB level
- ✅ `MatchInfo` dataclass provides transparency for debugging matches
- ⚠️ Existing routes still create teachers inline (Sprint 3 will redirect them)
- ⚠️ `cached_email` needs backfill from Email model records via `backfill_primary_emails()`

**Files Changed:**
- `services/teacher_service.py` — **NEW**: `find_or_create_teacher()`, `backfill_primary_emails()`, `MatchInfo`
- `models/teacher.py` — `cached_email`, `import_source` columns
- `models/teacher_progress.py` — `UniqueConstraint`
- `utils/roster_import.py` — email-first + normalized matching
- `tests/unit/services/test_teacher_service.py` — **NEW**: 13 tests
- `scripts/migrations/sprint1_teacher_foundation.py` — **NEW**: migration script

---

### 2026-02-27: D-006 — Sprint 2: EventTeacher as Single Source of Truth

**Context:** Teacher-session links were stored in two disconnected ways: (1) `event.educators` text field (semicolon-separated names from Pathful import), and (2) `EventTeacher` FK records (from session edit UI). The dashboard used a fragile dual-path counting merge that could double-count or miss sessions.

**Decision:**
1. Make `EventTeacher` the canonical source of truth for teacher-session links
2. Create `sync_event_participant_fields()` to regenerate all 4 text cache fields from FK tables
3. Create `ensure_event_teacher()` for idempotent EventTeacher creation
4. Wire Pathful import to create EventTeacher records (previously only set text)
5. Add sync calls to session edit/create handlers
6. Refactor dashboard counting to EventTeacher-first with text fallback

**Consequences:**
- ✅ Single authoritative path for teacher-session relationships
- ✅ Text fields are now a cache, not a source of truth
- ✅ Dashboard counting simplified — EventTeacher-first with text fallback
- ✅ Backfill script available for existing data
- ⚠️ Backfill script must be run on existing database to populate EventTeacher records
- ⚠️ Text fallback still active until backfill is complete

**Files Changed:**
- `services/teacher_service.py` — `sync_event_participant_fields()`, `ensure_event_teacher()`
- `scripts/utilities/backfill_event_teachers.py` — **NEW**: backfill from text
- `routes/virtual/pathful_import.py` — create EventTeacher on teacher match
- `routes/virtual/usage.py` — sync cache in edit + create
- `routes/district/tenant_teacher_usage.py` — EventTeacher-first counting

---

### 2026-02-27: D-007 — Sprint 3: All Teacher Creation Through Service Layer

**Context:** 7 inline `Teacher()` constructor calls in route files bypassed the centralized matching logic (Salesforce ID, email, normalized name). This meant duplicate-prone name-only matching and no `import_source` provenance tracking.

**Decision:** Replace all 7 inline sites with `find_or_create_teacher()` from `teacher_service.py`. Delete obsolete `fix_duplicate_teachers.py`.

**Consequences:**
- ✅ All Teacher creation uses the full matching chain (SF ID → email → normalized name)
- ✅ `import_source` tracked on every creation (`"spreadsheet"`, `"manual"`)
- ✅ Zero inline `Teacher()` calls remain in routes
- ✅ `fix_duplicate_teachers.py` deleted — Sprint 1 constraints prevent duplicates

---

### 2026-02-28: D-008 — Sprint 4: Text-Primary + EventTeacher-Supplementary Counting

**Context:** Sprint 4 initially removed text-based counting in favor of EventTeacher-only. However, the real database has 0 EventTeacher records and 3,793 events with educators text — the text path was doing all the work.

**Decision:** Restore text-based counting as PRIMARY (handles all historical data). EventTeacher is SUPPLEMENTARY (catches future FK-linked sessions not in text). The EventTeacher-only simplification is deferred until a verified backfill populates the EventTeacher table. Added `tenant_id` to Teacher model.

**Lesson:** Never remove a data access path before verifying the new path has equivalent data coverage. Sequence: backfill → verify → simplify.

**Consequences:**
- ✅ Dashboard counts match pre-refactor numbers
- ✅ Both `compute_teacher_progress` and `teacher_detail` use dual-path strategy
- ✅ Teacher model has `tenant_id` for future tenant-scoped queries
- ✅ Health check script created for ongoing data integrity monitoring

---

## Creating New ADRs

### When to Create

- Technology choices affecting the entire system
- Architecture decisions impacting multiple components
- Integration decisions with external systems
- Data model changes affecting multiple entities
- Performance optimizations changing system behavior

### ADR Template

```markdown
---
title: "NNNN: <short decision>"
status: proposed | accepted | deprecated | archived
project: "<project_slug>"
date: YYYY-MM-DD
summary: "<one paragraph what/why>"
---

## Context
[What is the issue motivating this decision?]

## Decision
[What is the change we're proposing/doing?]

## Consequences
[What becomes easier or more difficult?]

## Alternatives Considered
[What other options were considered and why rejected?]
```

---

## Key ADR Summaries

### G-001: Flask as Web Framework

**Context:** Needed a Python web framework for VMS development.

**Decision:** Choose Flask over Django.

**Rationale:**
- Lightweight and flexible
- Python-native
- Easy PythonAnywhere deployment
- Good for solo development

### G-002: SQLite as Primary Database

**Context:** Needed database for development and production.

**Decision:** Use SQLite for both environments.

**Rationale:**
- File-based, no server setup
- Good for PythonAnywhere hosting
- Simplifies deployment

### V-001: 5-Tier Validation Architecture

**Context:** Needed comprehensive data validation.

**Decision:** Implement 5-tier system: Count, Completeness, Data Type, Relationship, Business Rules.

**Rationale:**
- Layered approach
- Configurable rules
- Comprehensive coverage
