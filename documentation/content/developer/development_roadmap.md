# Development Roadmap

**Created:** 2026-03-06
**Goal:** Systematic improvements building toward MySQL production readiness, while keeping SQLite as the local dev database.

> [!NOTE]
> Each phase is designed as its own branch/PR. Phases 1–4 stay on SQLite. Phase 5 (MySQL cutover) is a separate branch.

---

## Phase 1: Safety Net *(Pre-merge / Current Branch)* ✅

Quick wins that reduce risk before any architectural changes.

### 1.1 — Automated SQLite Backup ✅

- [x] Create `scripts/daily_imports/backup_database.py` — copies `instance/*.db` to `instance/backups/` with timestamped names, auto-prunes after 7 days
- [x] Add `instance/backups/` to `.gitignore`

### 1.2 — Clean Up Repo Artifacts ✅ *(Already done)*

- [x] `*.csv` in `.gitignore`, 0 tracked CSVs remain
- [x] `scripts/dedup_*.csv` pattern in `.gitignore`

### 1.3 — CSRF Secret Guard ✅

- [x] Add fail-fast check for `WTF_CSRF_SECRET_KEY` in production (mirrors the `SECRET_KEY` guard in `app.py`)

### 1.4 — Enable WAL Mode ✅ *(Already done)*

- [x] SQLAlchemy event listener in `config/__init__.py` enables WAL mode + NORMAL synchronous for SQLite

### 1.5 — Consolidate `require_tenant_context` ✅

- [x] Move `require_tenant_context` from `district/volunteers.py` and `district/events.py` into `routes/decorators.py`
- [x] Update imports in both files

---

## Phase 2: Migration System Reset

> **"Can I set up a good migration system even though I've messed it up?"**
> **Yes.** The approach is a **baseline migration** — snapshot the current schema as the new starting point, then all future changes go through Alembic properly.

### 2.1 — Alembic Baseline Reset

- [ ] Back up the database
- [ ] Absorb all `fix_database_schema.py` changes into the current schema (run the script one final time if needed)
- [ ] Delete all existing migration files in `alembic/versions/`
- [ ] Generate a fresh baseline: `flask db init` or `alembic revision --autogenerate -m "baseline_march_2026"`
- [ ] Stamp the database as current: `alembic stamp head`
- [ ] Delete `scripts/fix_database_schema.py` — no longer needed
- [ ] **From this point forward:** all schema changes go through `alembic revision --autogenerate`

### 2.2 — Migration Workflow Documentation

- [ ] Add a "Schema Changes" section to the Developer Guide (`index.md`):
  ```
  # Making Schema Changes
  1. Modify the model in models/
  2. Generate: alembic revision --autogenerate -m "description"
  3. Review the generated migration
  4. Apply: alembic upgrade head
  5. Commit the migration file
  ```

---

## Phase 3: Architecture Hardening

These are the existing tech debt items, resequenced for the MySQL path.

### 3.1 — Application Factory Pattern *(TD-013)*

- [ ] Move all initialization inside `create_app(config_name=None)` in `app.py`
- [ ] Replace `from app import db` with proper patterns (Flask `current_app`, or lazy extension init)
- [ ] Update `conftest.py` to use the factory
- [ ] Verify all 1,169 tests pass with isolated app instances

> [!IMPORTANT]
> This is the **#1 architectural priority**. It unblocks: proper test isolation, conditional engine options (SQLite vs MySQL), and WSGI deployment patterns.

### 3.2 — Centralize Transaction Management *(TD-009)*

- [ ] Create a `@transactional` decorator or context manager
- [ ] Migrate route handlers in phases (start with `salesforce/` imports, then `management/`, then `virtual/`)
- [ ] Each route handler delegates to a service function; commit happens at the service boundary

### 3.3 — Replace Raw SQL with ORM *(MySQL Portability)*

- [ ] `routes/events/routes.py` L1120–1123: `DELETE FROM event_districts/event_skills` → ORM `Table.delete()`
- [ ] `routes/salesforce/history_import.py` L233: raw `text()` query → ORM query
- [ ] Audit `scripts/maintenance/optimize_*.py` for raw SQL
- [ ] Add conditional engine options in `Config`: `if 'sqlite' in uri` guard for `check_same_thread`, `timeout`

### 3.4 — Generic ReportCache Model *(TD-016)*

- [ ] Create `models/report_cache.py` with `cache_key`, `data` (JSON), `ttl`, `last_updated`
- [ ] Migrate existing cache models one at a time
- [ ] Delete old models as each migration completes

### 3.5 — Test Coverage for Extracted Blueprints *(TD-022)*

- [ ] Add integration tests for `quality_bp` and `docs_bp`
- [ ] Audit `reports/` test coverage — at least smoke tests for all 14 modules

---

## Phase 4: MySQL Readiness *(Still on SQLite)*

All preparation that can happen before the actual database switch.

### 4.1 — SQL Portability Audit

- [ ] Search for SQLite-specific patterns: `GROUP_CONCAT`, `LIKE` (SQLite is case-insensitive; MySQL isn't), `PRAGMA`, boolean `0/1`
- [ ] Create `utils/db_compat.py` with adapter functions if needed (e.g., `case_insensitive_like()`)
- [ ] Run full test suite to verify nothing breaks

### 4.2 — Multi-Tenant Strategy Decision

The current `db_manager.py` uses per-tenant SQLite files. This won't work with MySQL. Two options:

| Approach | Pros | Cons |
|----------|------|------|
| **Column scoping** (`tenant_id` on every table) | Simple, single DB, easy cross-tenant queries | Query discipline required, risk of data leaks |
| **Schema-per-tenant** (MySQL `CREATE DATABASE polaris_kckps`) | True isolation, easy to reason about | Complex connection management, hard to query across tenants |

- [ ] Make decision and document in ADR
- [ ] If column scoping: audit all models for `tenant_id` column, update `scoping.py`
- [ ] If schema-per-tenant: redesign `db_manager.py` for MySQL connection pool

### 4.3 — Production Snapshot Workflow

For your "see production data via SQLite" requirement:

- [ ] Create `scripts/utilities/snapshot_production.py`:
  1. `mysqldump` the production database
  2. Convert to SQLite via `mysql2sqlite` (open-source tool) or a Python script
  3. Save as `instance/production_snapshot.db`
- [ ] Document the workflow in the operations guide

### 4.4 — Background Task Infrastructure

From the [Salesforce Import Roadmap](salesforce_import_roadmap.md) future items:

- [ ] Evaluate: threading vs Celery vs APScheduler for background imports
- [ ] Add status polling endpoint (`GET /import-status/{id}`)
- [ ] Move long-running imports out of request/response cycle

---

## Phase 5: MySQL Migration *(Separate Branch)*

The actual database switch. Only start when Phases 1–4 are complete.

### 5.1 — PythonAnywhere MySQL Setup

- [ ] Create MySQL database on PythonAnywhere
- [ ] Set `DATABASE_URL=mysql+pymysql://user:pass@host/db` in production `.env`
- [ ] Install `pymysql` or `mysqlclient` in production requirements

### 5.2 — Schema Migration

- [ ] Run Alembic migrations against MySQL: `alembic upgrade head`
- [ ] Verify all tables created correctly (column types, indexes, constraints)
- [ ] Fix any MySQL-specific migration issues (TEXT column indexes, default values)

### 5.3 — Data Migration

- [ ] Export SQLite data → MySQL using a migration script
- [ ] Verify row counts match
- [ ] Run application smoke tests against MySQL

### 5.4 — Verification & Cutover

- [ ] Run full test suite against MySQL (`DATABASE_URL` pointed at test MySQL)
- [ ] Load test with `locustfile.py` against MySQL
- [ ] Cutover: update PythonAnywhere WSGI to use MySQL config
- [ ] Keep SQLite backup as rollback option for 2 weeks

---

## Not Planned (Acknowledged)

From various sources — tracked here so nothing is lost:

| Item | Source | Why Not Now |
|------|--------|-------------|
| Bidirectional Salesforce sync | SF Roadmap | Requires SF write permissions & conflict rules |
| Webhook-triggered imports | SF Roadmap | SF outbound message setup not available |
| Machine learning for data quality | SF Roadmap | Lower priority than infrastructure |
| Import scheduling UI | SF Roadmap | Needs scheduler infrastructure first (Phase 4.4) |
| `Event.district_partner` → FK | TD-004 | 60+ callsites, M2M already exists |
| Resumable import state | SF Roadmap | Depends on background task infrastructure (Phase 4.4) |

---

## References

- [Tech Debt Tracker](tech_debt.md) — Active debt items with full descriptions
- [Salesforce Import Roadmap](salesforce_import_roadmap.md) — Import-specific improvements
- [Architecture](../technical/architecture.md) — System design
- [ADR Log](../technical/adr.md) — Architectural decisions

---

*Last Updated: March 2026*
