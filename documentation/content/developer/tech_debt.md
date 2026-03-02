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

## TD-017: `usage.py` Is Still 7,473 Lines

**Created:** 2026-03-01
**Priority:** High
**Category:** Architecture / Maintainability

### Description

`routes/virtual/usage.py` remains at 7,473 lines with 68 top-level functions covering cache management, data processing, session computation, district reporting, teacher progress, Excel export, and event CRUD. This is the **single largest file** in the codebase and the highest-friction point for development.

See also: KI TD-004 (originally identified 2026-02-02).

### Proposed Fix

Domain-driven extraction:
1. `routes/virtual/usage/cache.py` — cache CRUD
2. `routes/virtual/usage/computation.py` — data processing helpers
3. `routes/virtual/usage/exports.py` — Excel generation
4. Move aggregation logic to `services/usage_service.py`

**Risk:** Medium — large file but routes can be extracted one at a time.
