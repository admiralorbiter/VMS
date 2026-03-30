# Tech Debt Tracker

This document tracks active technical debt. Resolved items are summarized in the [Resolved Archive](#resolved-archive) at the bottom. For the phased plan to address these items, see the [Development Plan](development_plan.md).

---

## TD-004: `Event.district_partner` Is a Text Field, Not a FK *(Deferred)*

**Created:** 2026-02-28 · **Evaluated:** 2026-03-02

Used in 60+ locations for `ILIKE` fuzzy matching, string splitting, and direct display. Events already have a proper `Event.districts` M2M relationship for relational work. Converting to FK would require a full rewrite of reporting and scoping layers. The field remains a **denormalized text cache** prioritized for its flexibility in fuzzy querying.

> [!NOTE]
> **Downstream consequence (TD-032):** Because `district_partner` is a single text value per event, multi-district sessions (teachers from multiple districts attending one event) get tagged with only one district's name. This caused under-counting for 17 KCKPS teachers. Mitigated by removing the `district_partner` filter from FK-based EventTeacher counting. Upstream fix: ask Pathful to correctly tag multi-district events.

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

- **Short term:** Enable WAL mode (`PRAGMA journal_mode=WAL`) for better read concurrency. *(Done — WAL mode enabled in `config/__init__.py`)*
- **Long term:** Migrate production to **MySQL** (PythonAnywhere). Keep SQLite as the local development database with tooling for easy SQLite ↔ MySQL conversion. Requires testing all raw SQL, SOQL queries, and SQLite-specific patterns. See [Development Plan](development_plan.md).

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

## TD-033: Student Import `str(None)` Data Cleanup ✅ RESOLVED

**Created:** 2026-03-07 · **Resolved:** 2026-03-13 · **Category:** Data Integrity

`Student.update_contact_info` used `str(sf_data.get("Email", ""))`, which converted Salesforce `None` values into the literal string `"None"`. This created **158,923 email records** and **158,925 phone records** containing the string `"None"` — all for student contacts.

**Import code fixed** (uses `isinstance()` guard now). **Database cleaned (2026-03-13):**

- 158,923 email records with `email='None'` — **deleted**
- 158,925 phone records with `number='None'` — **deleted**
- Script: `scripts/maintenance/fix_student_none_data.py`

---

## TD-034: Salesforce Data Quality Audit

**Created:** 2026-03-07 · **Priority:** Medium · **Category:** Data Quality

Production database analysis revealed several data patterns in Salesforce. Most issues have been resolved:

| Issue | Scale | Status |
|:---|:---|:---|
| Skeleton addresses (all fields empty) | 4,587 / 5,582 | ✅ Resolved — 4,630 deleted, import guard added |
| ALL CAPS names (e.g., `"JANE"`, `"DOE"`) | 18,225 contacts | ✅ Resolved — `smart_title_case()` in import; 18,814 normalized |
| Truncated skills | ~20 records | ✅ Resolved — `Skill.name` widened 50→200 chars |
| Connector subscriptions = NONE | 12,576 | ✅ Code removed — `ConnectorData` model deleted; `PathfulUserProfile` used instead |
| Organizations with no type | 983 / 3,811 | ✅ Resolved — Defaulted to "Other" + flagged |

### Remaining

- [x] ~~**Drop `connector_data` table**~~ — Table does not exist on current database (already clean).

**Re-scanned (2026-03-13):** Data quality scan run on clean DB, 1,088 flags created:

| Detector | Issues | Flags |
|:---|:---|:---|
| ALL CAPS contact names | 103 | 103 |
| Organizations missing type | 985 | 985 |
| Student str(None) email/phone (TD-033) | 0 | 0 |

View results at `/admin/data-quality`.

---

## TD-035: Multi-Part Name Creates Duplicate Teacher Records ✅ RESOLVED

**Created:** 2026-03-13 · **Resolved:** 2026-03-13 · **Category:** Data Integrity

`parse_name()` and two `_split_name()` functions treated the **last word** as the surname, splitting multi-part surnames like "Maria Garcia Lopez" into first="Maria Garcia", last="Lopez". This created duplicate Teacher records with stale "registered" statuses.

**Fix:** All 5 name-splitting locations now use first-word-as-given-name convention. `find_or_create_teacher()` has word-boundary matching (Priority 3b). 15 unit tests added. Data cleanup: 31 multi-part surname pairs + 4 misparsed first-name pairs merged. Merge logs in `scripts/maintenance/`.

---

## TD-036: Exact-Name Duplicate Teacher Records (~2,100 pairs)

**Created:** 2026-03-13 · **Priority:** Low · **Category:** Data Integrity

~2,106 Teacher pairs have identical normalized names but different IDs (e.g., "AARON GADDIS" vs "Aaron Gaddis"). Most have 0 EventTeachers on one side, suggesting they are orphaned stubs.

**Root cause:** Multiple import sources create Teacher records independently without case-insensitive dedup:

1. **Google Sheets roster import** — creates Teachers from the teacher roster with original casing
2. **Pathful session import** — creates Teachers from Pathful data, often in ALL-CAPS
3. **Reconciliation scripts** — `resolve_teacher_for_tp()` can create new Teachers during backfill

Each source calls `find_or_create_teacher()` which does case-insensitive matching — but historically, earlier code paths (manual creation, direct DB inserts, Salesforce sync) did not normalize before insertion.

**Impact:** Low — most duplicates are orphaned (0 EventTeachers). The ones with EventTeachers (1,132 pairs) could cause minor count inflation in aggregate reports.

**Recommended fix:** Run `merge_duplicate_teachers.py` with exact-name matching re-enabled, using the same school-validation safety check. Add case-insensitive unique constraint or pre-insert dedup check.

**Update (2026-03-13):**
- 7,660 orphaned teachers (0 FKs, no email) soft-deleted. Active teachers reduced from 10,122 to 2,462. Prune log in `data/`.
- **Admin Merge UI** built at `/teachers/merge` — search, compare, and merge with audit trail. Includes auto-flagged candidates (same first name, different last name, 90%+ event overlap, no school conflicts).
- **~11 flagged maiden/married name candidates** remain for manual review (e.g., maiden/married name mismatches). One pair merged so far — **staff review needed** for the rest. Use the merge UI to process them.

---

## TD-037: Hard-Delete Pruned Teachers (after 2026-04-13)

**Created:** 2026-03-13 · **Priority:** Low · **Category:** Maintenance

7,660 teachers were soft-deleted (marked `active=False`, tagged `pruned_20260313`) on 2026-03-13. If no issues are reported by **April 13, 2026**, they can be permanently deleted. Prune log: `data/prune_log_20260313_233506.json`.

**Undo:** `UPDATE teacher SET active = 1, import_source = REPLACE(import_source, '|pruned_20260313', '') WHERE import_source LIKE '%pruned_20260313%'`

---

## Priority Order

Ordered by **what best unblocks future work**:

| Priority | ID | Item |
|:--------:|----|------|
| 1 | **TD-033** | Student `str(None)` data cleanup (159K garbage records) |
| 2 | **TD-009** | Centralize transaction management |
| 3 | **TD-013** | True application factory pattern |
| 4 | **TD-052** | Volunteer org matching → alias-based resolution *(provisional regex active)* |
| 5 | **TD-016** | Generic `ReportCache` model |
| 6 | **TD-022** | Add tests for extracted blueprints |
| 7 | **TD-034** | Salesforce data quality audit |
| 8 | **TD-036** | Exact-name duplicate Teacher cleanup |
| 9 | **TD-037** | Hard-delete pruned teachers (after 2026-04-13) |
| 10 | **TD-040** | `NEPRIS_SESSION_BASE_URL` in single file (YAGNI) |
| 11 | **TD-011** | SQLite → MySQL *(do last when codebase is clean)* |

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
| TD-032 | Pathful Multi-District `district_partner` Mismatch | 2026-03-07 | Removed `district_partner` filter from FK-based EventTeacher counting path. Pathful assigns a single `district_partner` per event, so multi-district sessions get mislabelled (e.g. KCKPS event tagged "Hogan Preparatory Academy"). FK link already proves attendance; filter kept only on supplementary text-matching path. Fixed under-counting for 17 teachers across 2 events in Spring 2025-2026. **Upstream fix needed:** notify Pathful that events with teachers from multiple districts get the wrong `district_partner` value. |
| TD-038 | Session Status Classification Dedup | 2026-03-16 | CONFIRMED/PUBLISHED sessions silently dropped from teacher progress counting. Extracted ~350 lines of duplicated inline classification from 2 route files into `services/session_status_service.py`. Future CONFIRMED/PUBLISHED → "Planned"; past → "Needs Review". 36 unit tests. See ADR D-010. |
| TD-039 | Inline `import pytz` in Newsletter | 2026-03-17 | `import pytz` was inside 2 endpoint functions in `newsletter.py`. Moved to module level. |

---

## TD-040: `NEPRIS_SESSION_BASE_URL` in Single File

**Created:** 2026-03-17 · **Priority:** Low · **Category:** Maintainability

`NEPRIS_SESSION_BASE_URL` is defined only in `routes/tools/newsletter.py`. If another feature needs Nepris links, the URL would be duplicated.

**Proposed fix:** Move to app config or a shared constants module **when a second consumer appears** (YAGNI until then).

**Risk:** None — cosmetic.

---

## TD-052: Volunteer Org Matching — Migrate to Alias-Based Resolution

**Created:** 2026-03-30 · **Priority:** Medium · **Category:** Data Integrity / Architecture

When Pathful session reports are imported, new "professional" participants are matched to an `Organization` by exact (case-insensitive) name on the `"District or Company"` CSV field. This fails silently when Pathful's string differs from the canonical DB name (e.g. `"Turner Construction Company"` vs `"Turner Construction"`), creating **duplicate organizations** and mis-attributed `VolunteerOrganization` links.

A **provisional regex fix** (suffix-stripping: Company, Inc, LLC, etc.) was applied on 2026-03-30. It resolves the most common variant class but cannot handle abbreviations, trade names, or reordered names.

### Current Provisional Fix (active)

- `_find_org()` in `match_volunteer()` strips common business suffixes before falling back to creating a new org.
- Data fix applied: duplicate org 3849 ("Turner Construction Company") merged into org 3230 ("Turner Construction") on 2026-03-30.

### Target Architecture

Mirror the `DistrictAlias` pattern (TD-010, resolved):

1. New `OrganizationAlias` model — admins register known Pathful-name variants.
2. New `resolve_organization()` service function — 4-tier lookup (cache → exact → alias → suffix-stripped).
3. `match_volunteer()` calls `resolve_organization()`; on miss, stores raw string in `Volunteer.organization_name` and skips FK creation.
4. Unresolved volunteers surface in the **draft review queue** (`/pathful/draft-review`) where an admin links them to the correct org, which also auto-registers the alias for future imports.

**Full migration plan:** [`documentation/content/developer/pathful/volunteer_org_matching_migration.md`](pathful/volunteer_org_matching_migration.md)

### Risk

Medium — requires new model + migration, service function, draft review queue extension, and admin UI. The org report query fix (Bug 2) is independent and already final.

> [!NOTE]
> Until this is implemented, re-importing a Pathful session report where a company name does not match after suffix stripping will still create a duplicate org. Monitor for new orgs with similar names after each major import.
