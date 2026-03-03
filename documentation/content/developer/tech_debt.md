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

## ~~TD-003: `Teacher.school_id` Has No FK Constraint~~ *(Evaluated — N/A)*

**Created:** 2026-02-28
**Evaluated:** 2026-03-02

`School.id` uses Salesforce Account IDs (`String(255)`) as primary keys, so `Teacher.school_id = String(255)` is already correct. A formal FK constraint was **not added** because Salesforce imports often set school references before the school record is synced, which would cause import failures. A working ORM relationship exists via `primaryjoin`.

---

## TD-004: `Event.district_partner` Is a Text Field, Not a FK *(Evaluated — Deferred)*

**Created:** 2026-02-28
**Evaluated:** 2026-03-02

Used in 60+ locations for `ILIKE` fuzzy matching, string splitting, and direct display. Events already have a proper `Event.districts` M2M relationship for relational work. Converting to FK would require a full rewrite of reporting and scoping layers. The field remains a **denormalized text cache** prioritized for its flexibility in fuzzy querying.

---

## ~~TD-005: EventTeacher Cannot Be Primary Until All TeacherProgress Are Linked~~ *(Resolved 2026-02-28)*

All 464 TeacherProgress linked to Teacher records. EventTeacher backfill completed (15,838+ records, 97.5% coverage). Dashboard switched to EventTeacher-primary counting. See ADR D-008.

---

## ~~TD-006: `app.py` Is a God Module (841 Lines)~~ ✅ RESOLVED

**Created:** 2026-03-01
**Resolved:** 2026-03-01
**Priority:** High
**Category:** Architecture / Maintainability

### Resolution

Extracted ~590 lines into two new blueprints:
- `routes/quality/routes.py` (`quality_bp`) — 8 route handlers + 3 helper functions
- `routes/docs/__init__.py` (`docs_bp`) — 2 documentation-serving routes

Both registered in `routes/routes.py`. `app.py` reduced from 841 → 248 lines. Also fixed a `from app import db` circular import in the extracted code.

**Risk:** Low — all 338 routes verified, no logic changes.

---

## ~~TD-007: Deprecated `datetime.utcnow()` Across 20+ Files~~ ✅ RESOLVED

**Created:** 2026-03-01
**Resolved:** 2026-03-01
**Priority:** Medium
**Category:** Correctness / Forward Compatibility

### Resolution

Replaced all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` across 18 files. Column defaults converted to `lambda: datetime.now(timezone.utc)` pattern. Added `timezone` imports where missing. Final grep scan confirms zero remaining instances.

**Risk:** Low — direct replacement, behavior-identical.

---

## TD-008: Blanket `except Exception` in 50+ Files

**Created:** 2026-03-01
**Priority:** High
**Category:** Reliability / Debuggability

### Description

Bare `except Exception` handlers found across every layer — routes, services, utils, scripts. These silently swallow bugs, hide corrupted state, and make production debugging extremely difficult. Often catch-and-continue without re-raising or logging the traceback.

### Impact

- Bugs are hidden during development
- Production issues are nearly impossible to trace
- Exception types like `SQLAlchemyError`, `SalesforceExpiredSession`, `ValueError` are all treated identically

### Proposed Fix

Audit each handler individually:
1. Replace with specific exception types
2. Add `raise` or explicit error responses where needed
3. Ensure full traceback is logged via `app.logger.exception()`

**Risk:** Medium — requires per-handler analysis, not a blanket replacement.

---

## TD-009: `db.session.commit()` Scattered in 44 Route Files

**Created:** 2026-03-01
**Priority:** High
**Category:** Architecture / Transaction Safety

### Description

`db.session.commit()` is called directly in 44 route files. There is no centralized transaction management. Route handlers are coupled to the DB session lifecycle, error recovery is inconsistent (some rollback, others don't), and it's impossible to compose multiple operations in a single transaction.

### Proposed Fix

Adopt a service-layer transaction pattern:
1. Route handlers delegate to service functions
2. Single `db.session.commit()` at the service boundary
3. Use a decorator or context manager for commit/rollback

**Risk:** High — pervasive change, requires careful migration per-route.

---

## ~~TD-010: Hardcoded District Mappings in `routes/utils.py`~~ ✅ RESOLVED

**Created:** 2026-03-01
**Resolved:** 2026-03-01
**Priority:** Medium
**Category:** Scalability / Configuration

### Resolution

Replaced the hardcoded `DISTRICT_MAPPINGS` dict with a DB-driven solution:
- Added `DistrictAlias` model in `models/district_model.py`
- Created `services/district_service.py` with `resolve_district()` (4-tier: exact name → exact alias → case-insensitive name → case-insensitive alias) and `seed_district_aliases()`
- Updated 3 consumers to use `resolve_district()`, removed dict from `routes/utils.py`

**Risk:** Low — additive model, same behavior, no districts lost.

---

## TD-011: SQLite in Production

**Created:** 2026-03-01
**Priority:** High
**Category:** Scalability / Concurrency

### Description

Both `DevelopmentConfig` and `ProductionConfig` default to the same SQLite file database. Current config uses `timeout: 20` but this only delays — doesn't solve — write contention. SQLite allows only one writer at a time. No WAL mode is configured.

ADR G-002 accepted this tradeoff for simplicity, but as multi-tenant usage grows and daily imports run concurrently with user activity, this becomes the largest scalability ceiling.

### Proposed Fix

- **Short term:** Enable WAL mode (`PRAGMA journal_mode=WAL`) for better read concurrency.
- **Long term:** Migrate to PostgreSQL. Requires testing all raw SQL, SOQL queries, and SQLite-specific patterns.

**Risk:** Very high for PostgreSQL migration — largest infrastructure change possible.

---

## TD-012: Oversized Model Files

**Created:** 2026-03-01
**Priority:** Medium
**Category:** Maintainability / Code Organization

### Description

Several model files exceed reasonable size thresholds:

| File | Lines | Contents |
|------|-------|----------|
| `models/event.py` | 1,203 | 8 enums, 5 models, association tables, SF mapping |
| `models/contact.py` | 763 | 10 enums, base Contact, Email, Phone models |
| `models/volunteer.py` | 715 | ConnectorData, Volunteer + methods |
| `models/reports.py` | 693 | 10+ report cache models |

### Proposed Fix

1. Extract enums to `models/enums/` or per-domain enum files
2. Move cache models to `models/cache.py`
3. Split `event.py` into `models/event.py` (core model) and `models/event_enums.py`

**Risk:** Low — purely organizational, no logic changes.

---

## TD-013: No True Application Factory Pattern

**Created:** 2026-03-01
**Priority:** Medium
**Category:** Architecture / Testability

### Description

`app.py` creates the Flask app at module import time (line 24: `app = Flask(__name__)`). The `create_app()` function at line 822 just returns the pre-created global:

```python
def create_app():
    return app
```

This means:
- Tests cannot create isolated app instances
- Circular import risks (`from app import db` → `app.py` imports routes)
- WSGI servers can't use the factory pattern properly
- Cannot run multiple configurations simultaneously

### Proposed Fix

Convert to a proper factory: move all initialization inside `create_app(config_name=None)`, return the configured app.

**Risk:** Medium — many files do `from app import db`, which would need to change.

---

## ~~TD-014: Duplicate Method in `volunteer.py`~~ *(Resolved 2026-03-01)*

`_check_local_status_from_events` was defined twice (lines 343–382 and 384–423) — identical copies. Second definition silently overwrote the first. Removed the duplicate.

---

## TD-015: F-String Logger Interpolation

**Created:** 2026-03-01
**Priority:** Low
**Category:** Observability / Best Practice

### Description

Throughout routes, logging uses f-string interpolation: `app.logger.info(f"Processing {entity_type}")`. Python's logging module supports `%`-style lazy interpolation which avoids computing the string if the log level is disabled and enables structured log aggregation.

### Proposed Fix

Migrate to `app.logger.info("Processing %s", entity_type)` pattern. Can be done incrementally or via a pre-commit hook / linting rule.

**Risk:** Low — cosmetic, no behavior change.

---

## TD-016: Cache Model Proliferation in `reports.py`

**Created:** 2026-03-01
**Priority:** Medium
**Category:** Architecture / DRY

### Description

`models/reports.py` contains 10+ cache model classes with near-identical structures (JSON data column, `last_updated` timestamp, unique constraints). Additional cache models exist in `usage.py`. Every new report requires a new model, migration, and boilerplate CRUD.

### Proposed Fix

Create a generic `ReportCache` model with `cache_key` (composite of report type + parameters), `data` JSON column, and TTL logic. Replace dedicated cache models over time.

**Risk:** Medium — requires migrating existing cached data.

---

## ~~TD-017: `usage.py` Is Still 7,473 Lines~~ ✅ RESOLVED

**Created:** 2026-03-01
**Resolved:** 2026-03-02
**Priority:** High
**Category:** Architecture / Maintainability

### Resolution

Extracted `routes/virtual/usage.py` (7,473 lines) into a package with 7 domain-specific modules:

| Module | Lines | Responsibility |
|--------|------:|----------------|
| `cache.py` | 221 | Cache CRUD |
| `computation.py` | 1,837 | Data processing |
| `exports.py` | 250 | Excel generation |
| `session_routes.py` | 1,774 | Session CRUD routes |
| `district_routes.py` | 1,743 | District reporting |
| `teacher_progress_routes.py` | 1,330 | Teacher progress |
| `teacher_progress.py` | 744 | Standalone helpers |

Backward-compatible `__init__.py` re-exports all public symbols. All 1,114 tests pass.

**Risk:** Low — verified, no behavior changes.

---

## TD-018: Duplicate Permission Pattern — Inline `is_admin` Checks

**Created:** 2026-03-02
**Priority:** Medium
**Category:** Security / Maintainability

### Description

40+ instances of `if not current_user.is_admin:` scattered across route handlers instead of using the `@admin_required` decorator from `routes/decorators.py`. Worst offender: `management/management.py` with 20+ inline checks.

**Files affected:** `management/management.py`, `client_projects/routes.py` (7), `volunteers/routes.py`, `events/routes.py`, `teachers/routes.py`, `auth/routes.py`, `attendance/routes.py`, `bug_reports/routes.py`

### Proposed Fix

Replace inline checks with `@admin_required` or `@staff_required` decorators. Audit each handler for nuanced permission logic that may need a custom decorator (e.g., `tenant_teacher_usage.py` checks both `is_admin` and `tenant_id`).

**Risk:** Low — decorator already exists, mostly mechanical replacement.

---

## TD-019: `management.py` Is a God Module (~1,300+ Lines)

**Created:** 2026-03-02
**Priority:** Medium
**Category:** Architecture / Maintainability

### Description

`routes/management/management.py` contains user management, bulk operations, data purging, configuration, and administrative actions all in a single file. It has 20+ inline admin checks and mixes CRUD, import triggers, and system maintenance.

### Proposed Fix

Extract into sub-modules: `management/users.py`, `management/bulk_ops.py`, `management/system.py`.

**Risk:** Low — same extraction pattern used for TD-006 (app.py extraction).

---

## TD-020: `virtual_session.py` and `pathful_import.py` Are Oversized

**Created:** 2026-03-02
**Priority:** Medium
**Category:** Architecture / Maintainability

### Description

With `usage.py` resolved (TD-017), these are the largest remaining route files:

| File | Lines |
|------|------:|
| `routes/reports/virtual_session.py` | 5,287 |
| `routes/virtual/pathful_import.py` | 2,686 |
| `routes/reports/district_year_end.py` | 2,405 |

### Proposed Fix

Apply the same domain-driven extraction strategy proposed for TD-017.

**Risk:** Medium — same pattern as usage.py, can be done one file at a time.

---

## TD-021: SQLite `RETURNING` Workaround in Roster Import

**Created:** 2026-03-02
**Priority:** Medium
**Category:** Database Compatibility

### Description

Line 272 of `utils/roster_import.py`:

```python
# Temporary workaround: Skipping DB logging due to SQLite RETURNING issue
```

SQLite lacks `RETURNING` clause support, which silently disables audit logging for roster imports. This means tenant roster imports have no audit trail.

### Proposed Fix

- **Short term:** Implement an alternative insert-then-query pattern to restore audit logging.
- **Long term:** Resolved automatically by PostgreSQL migration (TD-011).

**Risk:** Low for short-term fix; resolved by TD-011 long-term.

---

## TD-022: No Test Coverage for Extracted Blueprints

**Created:** 2026-03-02
**Priority:** Medium
**Category:** Testing / Reliability

### Description

The `quality` and `docs` blueprints (extracted from `app.py` in TD-006) have zero test coverage. The 14-module `reports/` directory is only partially covered by `test_report_routes.py`.

### Proposed Fix

Add integration tests for `quality_bp` and `docs_bp`. Audit `reports/` test coverage to ensure all 14 report modules have at least smoke tests.

**Risk:** Low — additive, no code changes needed.

---

## ~~TD-023: Unsafe Test Fixtures Import Real App~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02
**Priority:** Critical
**Category:** Testing / Data Safety

### Resolution

7 test files used `from app import app` (real production app) and attempted to override `SQLALCHEMY_DATABASE_URI` to `:memory:` **after** the engine was already bound. This had no effect — SQLAlchemy ignores config changes post-`init_app()`. As a result, `db.drop_all()` in `test_recruitment_notes.py` and `test_magic_link.py` **wiped the real dev database**.

Removed 31 unsafe `app` fixture definitions across 7 files. All now use the safe conftest `app` fixture (fresh Flask app + `TestingConfig` + `:memory:` safety assertion).

**Files fixed:** `test_recruitment_notes.py`, `test_magic_link.py`, `test_public_api.py`, `test_district_events.py`, `test_district_recruitment.py`, `test_district_volunteers.py`, `test_tenant_context.py`

---

## ~~TD-024: Remove Legacy `import_sheet()` Route~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02

Removed `import_sheet()` + 18 helper functions from `routes/virtual/routes.py` (1,836 → 299 lines, ~1,537 lines removed). Fixed broken imports in `session_routes.py`. Removed 3 legacy tests. Standalone script decommissioned.

---

## ~~TD-025: Consolidate Permission Decorators~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02

Created canonical `admin_required` + `global_admin_required` in `routes/decorators.py`. Removed 4 local definitions, updated 12 import sites. Fixed 6 test assertions for context-aware behavior (302 vs 403).

---

## ~~TD-026: Standardize DB Commit Patterns in Salesforce Imports~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02

Fixed 3 files with inconsistent batch commit patterns:
- `history_import.py`: `success_count % 100` → `(i+1) % 100` (no more drifting when errors occur)
- `event_import.py`: Added batch commits to volunteer participant loop (was single commit)
- `pathway_import.py`: Added batch commits to events processing loop

---

## ~~TD-027: N+1 Query Bottlenecks in Volunteer Import~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02

Pre-loaded 4 lookup caches before the main processing loop in `volunteer_import.py`:
- Volunteer cache (`salesforce_individual_id → Volunteer`)
- Skill cache (`name → Skill`)
- Email cache (`(contact_id, email) → Email`)
- Phone cache (`(contact_id, number) → Phone`)

Eliminates ~15,000+ individual queries for a 2,000-record import.

---

## ~~TD-028: Model Cleanup (Duplicate Assignments, Export Bugs, Ordering)~~ ✅ RESOLVED

**Created:** 2026-03-02
**Resolved:** 2026-03-02

- `google_sheet.py`: Removed duplicate `sheet_name` assignment and duplicate `created_by` key in `to_dict()`
- `models/__init__.py`: Removed duplicate `TeacherProgressArchive` in `__all__`, added missing `RecruitmentOutcome` import
- `recruitment_note.py`: Added `id.desc()` tiebreaker to `get_for_volunteer()` for deterministic ordering
- `volunteers/routes.py`: Replaced inline recruitment notes query with model method

---

## Priority Order

Ordered by **what best unblocks future work** — structural improvements first, since they make every subsequent fix dramatically easier.

### Phase 1: Organize the Code (Unblocks Everything Else)

| Order | ID | Item | Rationale |
|:-----:|----|------|-----------|
| ~~1~~ | ~~**TD-017**~~ | ~~Break up `usage.py`~~ ✅ | Resolved 2026-03-02. Extracted into 7 modules. |
| 2 | **TD-020** | Break up `virtual_session.py` + `pathful_import.py` | Same pattern as TD-017 — do while approach is fresh. |
| 3 | **TD-019** | Break up `management.py` | 20+ inline admin checks become trivially fixable once in smaller files. |
| 4 | **TD-012** | Split oversized model files | Enums in their own files makes route extraction cleaner. |

### Phase 2: Standardize Patterns (Safer After Smaller Files)

| Order | ID | Item | Rationale |
|:-----:|----|------|-----------|
| 5 | **TD-018** | Inline `is_admin` → decorators | 40+ sites; mechanical fix, but must be done in smaller files or you'll lose your place. |
| 6 | **TD-008** | Audit `except Exception` handlers | Per-handler analysis in 200-line files is feasible; in 7,000-line files it's not. |
| 7 | **TD-009** | Centralize transaction management | Service-layer pattern requires clear route boundaries — only possible after extraction. |
| 8 | **TD-016** | Generic `ReportCache` model | Reduces boilerplate for new reports; depends on model files being cleaned up (TD-012). |

### Phase 3: Foundation & Safety Net

| Order | ID | Item | Rationale |
|:-----:|----|------|-----------|
| 9 | **TD-013** | True application factory pattern | Enables isolated test instances; unblocks better testing infrastructure. |
| 10 | **TD-022** | Add tests for extracted blueprints | Build safety net before making data-layer changes. |
| 11 | **TD-015** | F-string → `%s` logger migration | Low priority but can be done incrementally anytime. |
| 12 | **TD-021** | SQLite `RETURNING` workaround | Short-term fix to restore audit logging. |

### Phase 4: Data Integrity (Requires Migrations)

| Order | ID | Item | Rationale |
|:-----:|----|------|-----------|
| ~~13~~ | ~~**TD-003**~~ | ~~`Teacher.school_id` FK~~ | Evaluated — N/A. Column type already correct; FK would break imports. |
| ~~14~~ | ~~**TD-004**~~ | ~~`Event.district_partner` → FK~~ | Evaluated — Deferred. 60+ callsites, M2M already exists. |

### Phase 5: Infrastructure

| Order | ID | Item | Rationale |
|:-----:|----|------|-----------|
| 15 | **TD-011** | SQLite → PostgreSQL | Largest change possible. Resolves TD-021 as a side effect. Do last when codebase is clean. |
