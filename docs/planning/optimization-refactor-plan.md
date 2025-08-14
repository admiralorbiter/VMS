---
title: "VMS Optimization and Refactor Plan"
description: "Phased plan to improve performance, reliability, and maintainability across models, queries, and docs"
tags: [performance, database, migrations, architecture, testing]
---

## Scope

This plan tracks optimizations and refactors focused on model-level performance, integrity, and developer ergonomics. It includes rationale, alternatives, and phased rollout to minimize risk.

## Changes already implemented

- Event model
  - Added composite index `idx_event_school_start (school, start_date)`.
  - Added non-negative `CHECK` constraints for duration and all count fields.
  - Standardized timestamps to timezone-aware server defaults (`server_default=now()`, `onupdate=now()`).
  - Replaced `len(self.volunteers)` and `len(self.teacher_registrations)` with SQL `COUNT()` queries.
  - Added composite index `idx_event_student (event_id, student_id)` on student participation table.
- Organization model
  - Standardized timestamps to timezone-aware server defaults.
  - Replaced `len(self.volunteers)` with SQL `COUNT()` against association.

- **Salesforce Data Validation System** ✅ **NEW - COMPLETED**
  - Complete validation framework with database schema
  - Enhanced Salesforce client with caching and error handling
  - Validation engine with CLI interface
  - Comprehensive testing suite (6/6 tests passing)
  - Configuration management system

Status: [x] Completed; tests passed.

## High-impact pending improvements

### 1) Relationship loading strategy and N+1 avoidance

- Rationale: Extensive `lazy="dynamic"` prevents efficient eager loading and encourages collection loads/iteration. Using `selectinload/joinedload` per query reduces N+1 on list and detail pages.
- Plan:
  - Identify hot paths (events list, organization detail, volunteer detail) and add query helpers that apply `selectinload` bundles.
  - Keep `lazy="dynamic"` only where filtered subqueries are common and large result sets are expected.
- Alternatives:
  - Always-load via `joinedload` (can bloat rows; worse for large collections).
  - Data loader pattern (per-request caching layer); higher complexity.

### 2) Additional indexes and uniqueness

- Rationale: Support common filters/sorts; ensure integrity.
- Plan:
  - Consider unique `(event_id, student_id)` on `event_student_participation` if business rules guarantee 1 row per pair.
  - Add partial/covering indexes as we migrate to Postgres (e.g., CI text index for emails, GIN for JSON fields in reports).
- Alternatives:
  - Keep composite non-unique and dedupe in application layer (simpler, weaker integrity).
  - Rely on table scans (simplest, poor performance at scale).

### 3) Normalize denormalized text lists on `Event`

- Rationale: `educators`, `educator_ids`, `professionals`, `professional_ids` block proper joins and filtering.
- Plan:
  - Introduce `event_educators` and `event_professionals` association tables; write-through updates while keeping legacy columns for a deprecation window.
  - Backfill from existing data.
- Alternatives:
  - Keep semicolon lists and add FTS; query complexity remains high.
  - Postgres JSONB arrays + GIN; better queries but still less relational.

### 4) Timezone policy standardization

- Rationale: Mixing naive and aware timestamps causes subtle bugs and migration friction.
- Plan:
  - Update all models to `DateTime(timezone=True)` with DB `server_default` and `onupdate`.
  - Document “UTC everywhere” in Dev Guide and Ops Guide.
- Alternatives:
  - Keep naive UTC and enforce at app layer (simpler, error-prone).

### 5) Migrations with Alembic

- Rationale: Controlled schema evolution, enum changes, and environment parity.
- Plan:
  - Add Alembic baseline migration; integrate with CI.
  - Document workflow: generate → review → apply; include enum type management for Postgres.
- Status: [x] Alembic initialized; [x] unique `(event_id, student_id)` migration applied.
- Alternatives:
  - Flask auto-create in dev only; manual SQL for prod (riskier, less repeatable).

### 6) Enum strategy portability

- Rationale: SQLite lacks native enums; Postgres needs explicit named enum types.
- Plan:
  - Either use string columns with `CHECK` constraints, or ensure `sa.Enum(..., name=...)` with Alembic type migrations.
- Alternatives:
  - Keep SQLAlchemy Enum (works; migration complexity in Postgres when changing values).

### 7) PII normalization and search ergonomics

- Rationale: Case-insensitive search and dedupe are inconsistent across DBs.
- Plan:
  - Add `email_normalized` (lowercased) with index; enforce lowercase at write time via validators.
  - Consider phone normalization field.
- Alternatives:
  - Functional indexes in Postgres (lower(email)) without extra column.

### 8) Constraints and referential integrity

- Rationale: Push invariants to DB to catch errors early.
- Plan:
  - Audit all counters for `CHECK >= 0`.
  - Standardize `ondelete` and `passive_deletes` across FK relationships.
- Alternatives:
  - Application-only validation (faster to code; easier to regress).

### 9) Caching strategy for heavy reports

- Rationale: Sustained performance and predictable latency.
- Plan:
  - Define TTL and refresh policy fields (e.g., `last_refresh_ms`).
  - For Postgres, evaluate materialized views for aggregates; add background refresh.
- Alternatives:
  - Redis caching for computed pages (fast; adds infra).
  - Compute on demand (simple; slow for large datasets).

### 10) Bulk data operations

- Rationale: Faster imports and syncs.
- Plan:
  - Use `session.execute(insert(Model).values(list_of_dicts))` in batches; `yield_per()` for large reads.
- Alternatives:
  - `bulk_save_objects` (fast but bypasses some ORM features).

### 11) Testing enhancements

- Rationale: Prevent regressions while optimizing.
- Plan:
  - Tests for check constraints (IntegrityError paths), timezone-aware timestamps, SQL count helpers, and eliminating N+1 on key pages.

## Phased rollout

- Phase 1 (Low risk)
  - Query helpers with `selectinload` bundles for hot routes.
  - Add missing indexes and constraints where safe.
  - Update docs on timezone policy and query patterns.
  - Status: [x] Eager-load helpers applied to events list, calendar, org detail, volunteer orgs JSON, attendance details, contact report, and virtual session reports. Adjusted bundle to exclude `Event.comments` (dynamic) to avoid eager-load errors.
  - Extended: [x] Applied eager-load bundles to report routes: recruitment (quick, search, candidates CSV), volunteers_by_event, recent_volunteers (queries in route and export).

- Phase 2 (Infra)
  - Alembic initialized and first migration applied. Next: add CI step to run `alembic upgrade head` on disposable DB per PR.

- Phase 3 (Schema evolution)
  - Normalize event educator/professional lists with dual-write and backfill; deprecate old columns after read-path migration.
  - Participation dedupe guard: [x] Added app-level guard to prevent duplicate `(event_id, student_id)` insertions during SF sync while we assess uniqueness constraints.
  - Duplicate scan: [x] Added admin route `/admin/scan-student-participation-duplicates` to list duplicate pairs and records for review prior to enforcing DB uniqueness.

- Phase 4 (Caching)
  - TTL/refresh fields and background jobs; consider materialized views in Postgres.

- Phase 5 (Postgres optimizations)
  - Functional/partial indexes, GIN on JSONB, and enum type management.

## Upcoming candidates and plans

### Salesforce Data Validation System
- **Plan**: Implement comprehensive data validation system to ensure data integrity between VMS and Salesforce
- **Documents**:
  - [Salesforce Data Validation Plan](salesforce-data-validation-plan.md) - High-level planning and architecture
  - [Implementation Checklist](salesforce-validation-implementation-checklist.md) - Detailed task breakdown
  - [Technical Specification](salesforce-validation-technical-spec.md) - Implementation details and code examples
- **Status**: Planning complete, ready for implementation
- **Timeline**: 10-week phased implementation

- Email normalization and search ergonomics
  - Plan:
    - Add `email_normalized` (lowercase) column with index on `models.contact.Email` (or denormalized on `Contact` if a single-primary policy is sufficient).
    - Validator: on write, populate from `email` lowercased; enforce lowercase search.
    - Backfill script (idempotent) and Alembic migration to add column + index.
    - Update routes that search by email to use normalized field.
  - Risks: duplicates differing only by case; handle via dedupe rules.

- Normalize Event educator/professional lists
  - Plan:
    - Create `event_educators(event_id, educator_name, educator_id)` and `event_professionals(event_id, name, user_auth_id)` tables with indexes.
    - Dual-write from imports/UI while keeping legacy text columns; backfill from existing semicolon lists.
    - Migrate read paths and templates to normalized tables; then deprecate/drop legacy fields.
  - Risks: downstream queries depending on legacy strings; mitigate with compatibility views or transition window.

- Eager-loading coverage and N+1 audits
  - Audit remaining heavy pages (org/district reports) and apply `selectinload` where helpful; avoid `lazy="dynamic"` relationships in eager bundles.
  - Add simple query-count logging in debug for key endpoints to track regressions.

- Caching
  - Add TTL/refresh policies to caches (e.g., `last_refresh_ms` fields) and a background job to refresh stale entries.
  - Optionally store cache provenance (filters, counts) to aid debugging.

- Import/bulk operations
  - Ensure batch inserts with `session.execute(insert(...))` and iterate with `yield_per()` for large reads.
  - Improve progress/error reporting, standardize chunk sizes and retries.

- Observability and ops
  - Add slow-query logging threshold in prod.
  - Optional Sentry/Apm integration for error/latency tracking.
  - DB maintenance notes: vacuum/analyze guidance for Postgres.

- Security and PII
  - Review storage for PII (emails, addresses); encrypt at rest where warranted.
  - Minimize exposure in logs and exports; document data-access policies.

## Risks and mitigations

- Check constraints may surface latent negative values → add pre-migration cleanup scripts and guarded migrations.
- Normalization may affect downstream queries → provide compatibility views or dual-write window.
- Enum/type changes in Postgres → explicit Alembic migrations with downtime windows or rolling deploys.

## Metrics and acceptance criteria

- P95 latency on event list, organization detail: target ≥30% improvement.
- DB query count per page: reduce by ≥50% on N+1 hotspots.
- Test suite: green on constraints and eager-load tests.
- No increase in error rate post-deploy.
