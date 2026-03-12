# Development Plan

**Last Updated:** March 2026
**Purpose:** Single source of truth for development priorities. Replaces the former `development_roadmap.md`.

> [!NOTE]
> This plan is organized by priority tiers. Work within each tier generally follows the listed order, but items can be parallelized where dependencies allow.

---

## Active Work

| Item | Status | Notes |
|------|--------|-------|
| District Suite Phase 4 verification | 🔧 In Progress | Code complete, needs end-to-end testing. See [phases.md](../district_suite/phases.md) |
| Documentation consolidation | 🔧 In Progress | Merging roadmaps, archiving completed sprints |
| TD-034 Data Quality Dashboard | ✅ Complete | Dashboard live at `/admin/data-quality` with stats, filters, pagination, dismiss |
| Advanced Search CSV Export | 🔧 In Progress | FR-RECRUIT-307 — export search results with email, activity dates |

---

## Tier 1: Data Cleanup & Quick Wins

High-impact, low-risk items that should be done first.

### TD-033: Student `str(None)` Data Cleanup

- [ ] Write a one-time migration script to null-out `email = 'None'` (158,923 records) and `phone = 'None'` (158,925 records)
- [ ] Re-import students from Salesforce to back-fill real email/phone data
- **Root cause is fixed** — `Student.update_contact_info` now uses `isinstance()` guard

### TD-034: Salesforce Data Quality Audit

- [x] ~~Skeleton addresses~~ — 4,630 hollow addresses deleted; import fixed to skip empty addresses
- [x] ~~ALL CAPS name normalization~~ — `smart_title_case()` added to import; 18,814 records normalized
- [x] ~~Truncated skills~~ — `Skill.name` widened from 50→200 chars
- [x] ~~Organizations with NULL type~~ — Defaulted to "Other" + flagged via Data Quality system
- [x] ~~Connector → Pathful migration~~ — `ConnectorData` model removed; all UI/routes now use `PathfulUserProfile`
  - **Post-deploy:** Drop the orphaned `connector_data` table (`DROP TABLE connector_data;` — 12,576 rows, no code references remain)
- [x] ~~Data Quality Review Dashboard~~ — Live at `/admin/data-quality` with stats, filters, pagination, dismiss/bulk-dismiss
- **New:** Data Quality Flag system (`data_quality_flag` table) — flags created during Salesforce imports

> **Deploy note:** This commit is **code-only**. The name normalization and skeleton address fixes are in the import logic and will take effect on next Salesforce sync. Drop `connector_data` table post-deploy.

---

## Tier 2: Architecture Hardening

Foundational improvements that unblock future work and reduce risk.

### 2.1 — Alembic Migration Reset

> **"Can I set up a good migration system even though I've messed it up?"**
> **Yes.** The approach is a **baseline migration** — snapshot the current schema as the new starting point.

- [ ] Back up the database
- [ ] Absorb all `fix_database_schema.py` changes into the current schema
- [ ] Delete all existing migration files in `alembic/versions/`
- [ ] Generate a fresh baseline: `alembic revision --autogenerate -m "baseline_march_2026"`
- [ ] Stamp the database as current: `alembic stamp head`
- [ ] Delete `scripts/fix_database_schema.py`
- [ ] Add "Schema Changes" section to Developer Guide:
  ```
  1. Modify the model in models/
  2. Generate: alembic revision --autogenerate -m "description"
  3. Review the generated migration
  4. Apply: alembic upgrade head
  5. Commit the migration file
  ```

### 2.2 — Application Factory Pattern *(TD-013)*

> [!IMPORTANT]
> This is the **#1 architectural priority**. It unblocks: proper test isolation, conditional engine options (SQLite vs MySQL), and WSGI deployment patterns.

- [ ] Move all initialization inside `create_app(config_name=None)` in `app.py`
- [ ] Replace `from app import db` with proper patterns (Flask `current_app`, or lazy extension init)
- [ ] Update `conftest.py` to use the factory
- [ ] Verify all tests pass with isolated app instances

### 2.3 — Centralize Transaction Management *(TD-009)*

- [ ] Create a `@transactional` decorator or context manager
- [ ] Migrate route handlers in phases (start with `salesforce/`, then `management/`, then `virtual/`)
- [ ] Each route handler delegates to a service function; commit at the service boundary

### 2.4 — Replace Raw SQL with ORM *(MySQL Portability)*

- [ ] `routes/events/routes.py` L1120–1123: `DELETE FROM event_districts/event_skills` → ORM `Table.delete()`
- [ ] `routes/salesforce/history_import.py` L233: raw `text()` query → ORM query
- [ ] Audit `scripts/maintenance/optimize_*.py` for raw SQL
- [ ] Add conditional engine options in `Config`: `if 'sqlite' in uri` guard for `check_same_thread`, `timeout`

### 2.5 — Generic ReportCache Model *(TD-016)*

- [ ] Create `models/report_cache.py` with `cache_key`, `data` (JSON), `ttl`, `last_updated`
- [ ] Migrate existing cache models one at a time
- [ ] Delete old models as each migration completes

### 2.6 — Test Coverage for Extracted Blueprints *(TD-022)*

- [ ] Add integration tests for `quality_bp` and `docs_bp`
- [ ] Audit `reports/` test coverage — at least smoke tests for all 14 modules

---

## Tier 3: MySQL Migration

All preparation and execution for switching production from SQLite to MySQL. Only start when Tier 2 is substantially complete.

> [!NOTE]
> **Dual-database strategy:** SQLite remains the local dev database. MySQL is the production target on PythonAnywhere. Tooling should support easy conversion between the two.

### 3.1 — SQL Portability Audit

- [ ] Search for SQLite-specific patterns: `GROUP_CONCAT`, `LIKE` (case-sensitivity), `PRAGMA`, boolean `0/1`
- [ ] Create `utils/db_compat.py` with adapter functions if needed (e.g., `case_insensitive_like()`)
- [ ] Run full test suite to verify nothing breaks

### 3.2 — Multi-Tenant Strategy Decision

The current `db_manager.py` uses per-tenant SQLite files. This won't work with MySQL.

| Approach | Pros | Cons |
|----------|------|------|
| **Column scoping** (`tenant_id` on every table) | Simple, single DB, easy cross-tenant queries | Query discipline required, risk of data leaks |
| **Schema-per-tenant** (MySQL `CREATE DATABASE polaris_kckps`) | True isolation, easy to reason about | Complex connection management, hard to query across tenants |

- [ ] Make decision and document in ADR
- [ ] If column scoping: audit all models for `tenant_id` column, update `scoping.py`
- [ ] If schema-per-tenant: redesign `db_manager.py` for MySQL connection pool

### 3.3 — Production Snapshot Workflow

For "see production data via SQLite" requirement:

- [ ] Create `scripts/utilities/snapshot_production.py`:
  1. `mysqldump` the production database
  2. Convert to SQLite via `mysql2sqlite` or a Python script
  3. Save as `instance/production_snapshot.db`
- [ ] Document the workflow in the operations guide

### 3.4 — Background Task Infrastructure

- [ ] Evaluate: threading vs Celery vs APScheduler for background imports
- [ ] Add status polling endpoint (`GET /import-status/{id}`)
- [ ] Move long-running imports out of request/response cycle

### 3.5 — PythonAnywhere MySQL Setup

- [ ] Create MySQL database on PythonAnywhere
- [ ] Set `DATABASE_URL=mysql+pymysql://user:pass@host/db` in production `.env`
- [ ] Install `pymysql` or `mysqlclient` in production requirements

### 3.6 — Schema & Data Migration

- [ ] Run Alembic migrations against MySQL: `alembic upgrade head`
- [ ] Verify all tables created correctly (column types, indexes, constraints)
- [ ] Export SQLite data → MySQL using a migration script
- [ ] Verify row counts match

### 3.7 — Verification & Cutover

- [ ] Run full test suite against MySQL (`DATABASE_URL` pointed at test MySQL)
- [ ] Load test with `locustfile.py` against MySQL
- [ ] Cutover: update PythonAnywhere WSGI to use MySQL config
- [ ] Keep SQLite backup as rollback option for 2 weeks

---

## Tier 4: Feature Development

Remaining requirements from the [Status Tracker](development_status_tracker.md). Prioritized by user impact.

### 🚨 High Priority

| Area | FRs | Count |
|------|-----|-------|
| Email System | FR-EMAIL-801–852 | 22 |
| Reporting Cache Management | FR-REPORTING-420–425 | 6 |
| Year-End Reporting | FR-REPORTING-430–434 | 5 |
| District Data Tracker | FR-DISTRICT-525–530 | 6 |

### ⚡ Medium Priority

| Area | FRs | Count |
|------|-----|-------|
| Tenant Teacher Excel Export | FR-TENANT-117 | 1 |
| Manual Archive Semester | FR-DISTRICT-544 | 1 |

### 🔮 Future / Near-term

| Area | FRs | Notes |
|------|-----|-------|
| Virtual Pathful Automation | FR-VIRTUAL-207 | Auto-pull Pathful exports |
| Virtual Local Volunteer Comms | FR-VIRTUAL-209 | Automated comms for local volunteers |
| PrepKC Event Visibility | FR-SELFSERV-501–503 | District Suite Phase 5 |
| District Reminder Emails | FR-DISTRICT-504 | Automated teacher reminders |
| Data Quality Platform | *Epic* | Extend Data Quality Dashboard across all data sources; auto-detect dupes, orphans, stale records; resolution workflows; trend tracking |

---

## Salesforce Import — Remaining Items

Pending items from the [Salesforce Import Roadmap](salesforce_import_roadmap.md):

- [ ] **Student data cleanup and reimport** *(TD-033)* — see Tier 1
- [x] ~~Salesforce data quality investigation~~ *(TD-034)* — Resolved. See Tier 1
- [ ] **Background task execution for large imports** — see Tier 3.4
- [ ] **Resumable imports with checkpointing** — store last processed ID in SyncLog, add `?resume=true`
- [ ] **Conflict detection dashboard** — visual display of Polaris vs Salesforce data conflicts

---

## Deferred / Not Planned

Items considered but not currently feasible:

| Item | Source | Why Not Now |
|------|--------|-------------|
| Bidirectional Salesforce sync | SF Roadmap | Requires SF write permissions & conflict rules |
| Webhook-triggered imports | SF Roadmap | SF outbound message setup not available |
| Machine learning for data quality | SF Roadmap | Lower priority than infrastructure |
| Import scheduling UI | SF Roadmap | Needs scheduler infrastructure first (Tier 3.4) |
| `Event.district_partner` → FK | TD-004 | 60+ callsites, M2M already exists |
| Resumable import state | SF Roadmap | Depends on background task infrastructure (Tier 3.4) |
| Multi-tenant import isolation | SF Roadmap | Depends on multi-tenant strategy decision (Tier 3.2) |
| Import analytics dashboard | SF Roadmap | Lower priority than functional improvements |

---

## Completed Milestones

| Milestone | Date | Summary |
|-----------|------|---------|
| Safety Net (Phase 1) | Mar 2026 | SQLite backup, repo cleanup, CSRF guard, WAL mode, decorator consolidation |
| Teacher Data Refactor | Feb–Mar 2026 | 5 sprints: service layer, EventTeacher authority, pipeline cleanup, dashboard hardening, identity resolution. See [archive](../archive/teacher_refactor/) |
| Salesforce Import Improvements | Feb–Mar 2026 | 4 sprints: service layer extraction, error handling, dashboard, tests. See [SF Import Roadmap](salesforce_import_roadmap.md) |
| District Suite Phases 1–3 | Jan 2026 | Foundation, events, volunteers. All complete with test coverage |
| District Suite Phase 4 | Mar 2026 | Recruitment tools — code complete, verification in progress |
| TD-034 Data Quality Audit | Mar 2026 | Skeleton addresses, ALL CAPS names, truncated skills, connector migration, Data Quality Dashboard. See [Tech Debt Tracker](tech_debt.md) |
| Tech Debt TD-001 through TD-034 | Feb–Mar 2026 | 21 items resolved. See [Tech Debt Tracker](tech_debt.md#resolved-archive) |

---

## References

- [Development Status Tracker](development_status_tracker.md) — FR-by-FR implementation status (~188 FRs)
- [Tech Debt Tracker](tech_debt.md) — Active debt items with descriptions and priorities
- [Architecture](../technical/architecture.md) — System design
- [ADR Log](../technical/adr.md) — Architectural decisions
- [Salesforce Import Roadmap](salesforce_import_roadmap.md) — Import-specific improvements
- [District Suite Phases](../district_suite/phases.md) — Multi-tenant development history

---

*This document is the primary development planning reference. Update as items are completed or priorities shift.*
