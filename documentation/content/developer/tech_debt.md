# Tech Debt Tracker

This document tracks active technical debt. Resolved items are summarized in the [Resolved Archive](#resolved-archive) at the bottom. For the phased plan to address these items, see the [Development Roadmap](development_roadmap.md).

---

## TD-004: `Event.district_partner` Is a Text Field, Not a FK *(Deferred)*

**Created:** 2026-02-28 · **Evaluated:** 2026-03-02

Used in 60+ locations for `ILIKE` fuzzy matching, string splitting, and direct display. Events already have a proper `Event.districts` M2M relationship for relational work. Converting to FK would require a full rewrite of reporting and scoping layers. The field remains a **denormalized text cache** prioritized for its flexibility in fuzzy querying.

---

## TD-009: `db.session.commit()` Scattered in 44 Route Files

**Created:** 2026-03-01 · **Priority:** High · **Category:** Architecture / Transaction Safety

`db.session.commit()` is called directly in 44 route files. There is no centralized transaction management. Route handlers are coupled to the DB session lifecycle, error recovery is inconsistent (some rollback, others don't), and it's impossible to compose multiple operations in a single transaction.

### Proposed Fix

Adopt a service-layer transaction pattern:
1. Route handlers delegate to service functions
2. Single `db.session.commit()` at the service boundary
3. Use a decorator or context manager for commit/rollback

**Risk:** High — pervasive change, requires careful migration per-route.

---

## TD-011: SQLite in Production

**Created:** 2026-03-01 · **Priority:** High · **Category:** Scalability / Concurrency

Both `DevelopmentConfig` and `ProductionConfig` default to the same SQLite file database. Current config uses `timeout: 20` but this only delays — doesn't solve — write contention. SQLite allows only one writer at a time. No WAL mode is configured.

ADR G-002 accepted this tradeoff for simplicity, but as multi-tenant usage grows and daily imports run concurrently with user activity, this becomes the largest scalability ceiling.

### Proposed Fix

- **Short term:** Enable WAL mode (`PRAGMA journal_mode=WAL`) for better read concurrency.
- **Long term:** Migrate to MySQL (PythonAnywhere). Requires testing all raw SQL, SOQL queries, and SQLite-specific patterns. See [Development Roadmap — Phase 5](development_roadmap.md#phase-5-mysql-migration-separate-branch).

**Risk:** Very high for MySQL migration — largest infrastructure change possible.

---

## TD-013: No True Application Factory Pattern

**Created:** 2026-03-01 · **Priority:** Medium · **Category:** Architecture / Testability

`app.py` creates the Flask app at module import time. The `create_app()` function just returns the pre-created global. This means tests cannot create isolated app instances, circular import risks exist (`from app import db`), and WSGI servers can't use the factory pattern properly.

### Proposed Fix

Convert to a proper factory: move all initialization inside `create_app(config_name=None)`, return the configured app.

**Risk:** Medium — many files do `from app import db`, which would need to change.

---

## TD-016: Cache Model Proliferation in `reports.py`

**Created:** 2026-03-01 · **Priority:** Medium · **Category:** Architecture / DRY

`models/reports.py` contains 10+ cache model classes with near-identical structures (JSON data column, `last_updated` timestamp, unique constraints). Additional cache models exist in `usage.py`. Every new report requires a new model, migration, and boilerplate CRUD.

### Proposed Fix

Create a generic `ReportCache` model with `cache_key` (composite of report type + parameters), `data` JSON column, and TTL logic. Replace dedicated cache models over time.

**Risk:** Medium — requires migrating existing cached data.

---

## TD-022: No Test Coverage for Extracted Blueprints

**Created:** 2026-03-02 · **Priority:** Medium · **Category:** Testing / Reliability

The `quality` and `docs` blueprints (extracted from `app.py` in TD-006) have zero test coverage. The 14-module `reports/` directory is only partially covered by `test_report_routes.py`.

### Proposed Fix

Add integration tests for `quality_bp` and `docs_bp`. Audit `reports/` test coverage to ensure all 14 report modules have at least smoke tests.

**Risk:** Low — additive, no code changes needed.

---

## Priority Order

Ordered by **what best unblocks future work**:

| Priority | ID | Item |
|:--------:|----|------|
| 1 | **TD-009** | Centralize transaction management |
| 2 | **TD-013** | True application factory pattern |
| 3 | **TD-016** | Generic `ReportCache` model |
| 4 | **TD-022** | Add tests for extracted blueprints |
| 5 | **TD-011** | SQLite → PostgreSQL *(do last when codebase is clean)* |

> TD-004 is intentionally deferred — the M2M relationship is the correct path forward.

---

## Resolved Archive

All resolved items, for historical reference:

| ID | Title | Resolved | Summary |
|----|-------|----------|---------|
| TD-001 | Enum vs String Storage for Roles | 2026-03-01 | `TenantRole` converted to `str, Enum`. `hasattr` workarounds removed. |
| TD-002 | Incomplete Savepoint Recovery | 2026-02-04 | All SF import files updated with savepoint recovery and structured error codes. |
| TD-003 | `Teacher.school_id` FK Constraint | N/A | Evaluated — column type already correct. FK would break imports due to identity lag. |
| TD-005 | EventTeacher Primary Counting | 2026-02-28 | All 464 TeacherProgress linked. EventTeacher backfill completed (15,838+ records, 97.5%). |
| TD-006 | `app.py` God Module (841 lines) | 2026-03-01 | Extracted `quality_bp` + `docs_bp`. `app.py` reduced 841 → 248 lines. |
| TD-007 | Deprecated `datetime.utcnow()` | 2026-03-01 | All calls replaced with `datetime.now(timezone.utc)` across 18 files. |
| TD-008 | Blanket `except Exception` (50+ files) | 2026-03-03 | Error hierarchy (`AppError` + 6 subclasses), `@handle_route_errors` decorator. 4-phase migration. |
| TD-010 | Hardcoded District Mappings | 2026-03-01 | Replaced with `DistrictAlias` model + `resolve_district()` (4-tier lookup). |
| TD-012 | Oversized Model Files | 2026-03-03 | Enums extracted from `contact.py`, `event.py`, `volunteer.py` into dedicated modules. |
| TD-014 | Duplicate Method in `volunteer.py` | 2026-03-01 | Removed duplicate `_check_local_status_from_events`. |
| TD-015 | F-String Logger Interpolation | 2026-03-03 | 562 f-string logger calls migrated to `%s` lazy interpolation across ~30 files. |
| TD-017 | `usage.py` God Module (7,473 lines) | 2026-03-02 | Extracted into 7 domain-specific modules. |
| TD-018 | Inline `is_admin` Checks (40+ instances) | 2026-03-03 | 37 inline checks replaced with `@admin_required` across 13 files. |
| TD-019 | `management.py` God Module (1,410 lines) | 2026-03-03 | Extracted into 5 domain-specific modules. |
| TD-020 | Oversized Route Files (3 files) | 2026-03-03 | `virtual_session.py`, `pathful_import.py`, `district_year_end.py` extracted into packages. |
| TD-021 | SQLite `RETURNING` Workaround | 2026-03-03 | `MockLog` replaced with real `RosterImportLog` using standard ORM. |
| TD-023 | Unsafe Test Fixtures (prod DB risk) | 2026-03-02 | 31 unsafe fixture definitions removed across 7 test files. |
| TD-024 | Legacy `import_sheet()` Route | 2026-03-02 | Removed ~1,537 lines of dead code + 18 helper functions. |
| TD-025 | Consolidate Permission Decorators | 2026-03-02 | Canonical `admin_required` + `global_admin_required` in `routes/decorators.py`. |
| TD-026 | DB Commit Patterns in SF Imports | 2026-03-02 | 3 files fixed with consistent batch commit patterns. |
| TD-027 | N+1 Queries in Volunteer Import | 2026-03-02 | Pre-loaded 4 lookup caches, eliminating ~15,000+ individual queries. |
| TD-028 | Model Cleanup (Duplicates, Ordering) | 2026-03-02 | Duplicate assignments removed, missing imports added, deterministic ordering. |
| TD-029 | Unlinked TeacherProgress Records | 2026-03-06 | Centralized identity resolution in `teacher_matching_service.py` (`resolve_teacher_for_tp`, `match_tp_to_profile`). Reconciliation script linked 42 profiles, resolved 35 TPs. |
| TD-030 | Override Double-Counting | 2026-03-06 | ADD overrides now event-aware — skip if event already counted via EventTeacher. Stale ADDs auto-resolved with logging. |
| TD-031 | No-Show Text-Match Leak | 2026-03-06 | Split `matched_event_ids` into `all_et_event_ids` + `counted_events_per_tp`. No-show EventTeacher records now excluded from supplementary text-matching. |
