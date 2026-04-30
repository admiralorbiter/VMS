# Import Pipeline — Phase 3 Hardening Plan

**Status:** Ready to execute
**Created:** 2026-04-29
**Owner:** Development Team
**Prerequisites:** Phase 1 (TD-055, TD-056) and Phase 2 (TD-057) complete ✅

> See [salesforce_import_roadmap.md](salesforce_import_roadmap.md) for the full history.
> See [tech_debt.md](tech_debt.md) for TD-058, TD-059, TD-060 (dead code items).

---

## Pre-Flight Fixes (do first — ~30 min)

These must be done before Sprint B to avoid runtime errors:

- [x] **Pre-1 — Missing Alembic migrations:** Create a migration for:
  - `data_quality_flag.entity_sf_id` column (added in TD-056, no migration exists)
  - `pending_participation_imports` table (added in TD-057, no migration exists)
  - Run: `flask db migrate -m "add_entity_sf_id_and_pending_participation_imports"`, review, apply
- [x] **Pre-2 — Mark TD-033 resolved in roadmap:** Update `salesforce_import_roadmap.md` checkbox

---

## Sprint A — Silent Data Correctness (~1 hour)

> 5 targeted fixes that close gaps causing wrong data to be written silently. No new models, no migrations needed.

### A-1: Affiliations import — set `date_source='salesforce'`

**File:** `routes/salesforce/organization_import.py` ~line 491
**Problem:** New `VolunteerOrganization` rows created via direct constructor get `date_source='auto_detected'` from the `before_insert` hook. The SF start_date is then applied in the update block, but `date_source` is never corrected.

```python
# Before
vol_org = VolunteerOrganization(
    volunteer_id=contact.id, organization_id=org.id
)

# After
vol_org = VolunteerOrganization(
    volunteer_id=contact.id,
    organization_id=org.id,
    date_source="salesforce",
)
```

**AC:** New affiliation rows have `date_source='salesforce'`, not `'auto_detected'`.

---

### A-2: Affiliations import — STATUS_MAP normalization

**File:** `routes/salesforce/organization_import.py` ~line 502
**Problem:** `vol_org.status = new_status` writes the raw SF value directly. `'Former'` leaks through instead of being normalized to `'Past'`.

```python
# Add at top of affiliation processing block
_STATUS_MAP = {
    "former": "Past", "past": "Past",
    "current": "Current", "pending": "Pending",
}

# Replace
raw_status = row.get("npe5__Status__c")
new_status = _STATUS_MAP.get((raw_status or "").lower(), raw_status)
```

**Also check:** `routes/virtual/pathful_import/matching.py` and `processing.py` — both write `VolunteerOrganization.status` from CSV data and may need the same normalization.

**AC:** `SELECT DISTINCT status FROM volunteer_organization` returns only `'Current'`, `'Past'`, `'Pending'`, `NULL` after a full affiliations re-import.

---

### A-3: Health metrics — unify `sync_types` into one constant

**File:** `routes/salesforce/routes.py` ~lines 36–48 and 115–124
**Problem:** Two separate hard-coded `sync_types` lists. The `health_metrics` endpoint omits `student_participations`, `unaffiliated_events`, and `classes` — those three never appear as stale.

```python
# Extract at module level (used by both endpoints)
ALL_SYNC_TYPES = [
    "organizations", "volunteers", "affiliations",
    "events", "history", "schools", "classes",
    "teachers", "students", "student_participations",
    "unaffiliated_events",
]
```

Replace both inline lists with `ALL_SYNC_TYPES`.

**AC:** `GET /admin/salesforce/health-metrics` returns entries for all 11 sync types.

---

### A-4: Fix `pathway_import.py` wrong import source

**File:** `routes/salesforce/pathway_import.py` line ~35
**Problem:** `from routes.salesforce.event_import import safe_parse_delivery_hours` — imports from a route file instead of the canonical location.

```python
# Before
from routes.salesforce.event_import import safe_parse_delivery_hours

# After
from services.salesforce.utils import safe_parse_delivery_hours
```

**AC:** No import from `routes.salesforce.event_import` in `pathway_import.py`.

---

### A-5: Remove dead function copies from `routes/events/routes.py`

**File:** `routes/events/routes.py`
**Problem (TD-058):** This file contains outdated copies of functions that were extracted to `services/salesforce/processors/event.py`:

| Dead copy | Line | Issue |
|---|---|---|
| `safe_parse_delivery_hours()` | ~83 | Duplicate of `services/salesforce/utils.py` |
| `process_event_row()` | ~114 | Old N+1 version with no caches |
| `process_participation_row()` | ~268 | Pre-TD-056, silently drops unmatched records |
| `process_student_participation_row()` | ~338 | Does `db.session.commit()` per row |
| `fix_missing_participation_records()` | ~447 | Called on every `view_event()` page load — hidden N+1 |

Two test files import the dead `process_student_participation_row` copy:
- `tests/integration/test_participation_sync.py:32`
- `tests/integration/test_event_routes.py:259`

**Action:**
1. Update both test files to import from `services.salesforce.processors.event`
2. Remove the 5 dead functions from `routes/events/routes.py`
3. Remove `fix_missing_participation_records(event)` call from `view_event()` (~line 738)

**AC:** `pytest tests/ -q` green. No definition of `process_event_row` or `safe_parse_delivery_hours` in `routes/events/routes.py`.

---

## Sprint B — Observability (~4 hours)

### B-1: DQ flags for unmatched history records

**File:** `routes/salesforce/history_import.py` + `models/data_quality_flag.py`

Add `UNMATCHED_SF_HISTORY = "unmatched_sf_history"` to `DataQualityIssueType` (and `all_types()` / `display_name()`).

In the history import loop, where a `Task` or `EmailMessage` row fails to match a local contact:

```python
from models.data_quality_flag import DataQualityIssueType, flag_data_quality_issue

flag_data_quality_issue(
    entity_type="sf_history",
    entity_id=None,
    entity_sf_id=row.get("Id"),
    issue_type=DataQualityIssueType.UNMATCHED_SF_HISTORY,
    details=(
        f"SF history record {row.get('Id')} could not be linked. "
        f"WhoId={row.get('WhoId')} not found in local DB."
    ),
    salesforce_id=row.get("Id"),
)
```

> **Note:** The `uix_dqf_entity_issue` constraint covers `(entity_type, entity_id, issue_type)` — not `entity_sf_id`. SQLite treats NULL as distinct so multiple `entity_id=NULL` flags won't collide, but the dedup logic in `flag_data_quality_issue()` must check by `entity_sf_id` (it already does). Document this assumption.

**AC:** After a history import with unmatched contacts, `DataQualityFlag.query.filter_by(issue_type='unmatched_sf_history').count()` returns the expected number.

---

### B-2: Pending queue breakdown in `import_health`

**Files:** `routes/management/data_integrity.py` + `templates/management/import_health.html`

Replace the single `pending_queue_depth` count with a structured breakdown:

```python
from sqlalchemy import func
from models.pending_participation import PendingParticipationImport as PPI

pending_stats = {
    "total":      PPI.query.filter(PPI.resolved_at.is_(None)).count(),
    "orphaned":   PPI.query.filter(PPI.resolved_at.is_(None), PPI.error_reason == "likely_sf_orphan").count(),
    "resolvable": PPI.query.filter(PPI.resolved_at.is_(None),
                      (PPI.error_reason != "likely_sf_orphan") | (PPI.error_reason.is_(None))).count(),
}
```

Also expose a CSV export endpoint (`GET /admin/import-health/pending-export`) so admins can pull orphaned SF IDs and investigate in Salesforce.

**AC:** Import health page shows Total / Resolvable / Orphaned breakdown. CSV export works.

---

### B-3: Import ordering staleness warning in SF dashboard

**Files:** `routes/salesforce/routes.py` + `templates/salesforce/import_dashboard.html`

Add a check: if `volunteers.completed_at > affiliations.completed_at`, render an orange warning banner:

> "Volunteers were synced after Affiliations. Run Affiliations to ensure org links are current."

**AC:** Warning appears when volunteers are more recently synced than affiliations. Disappears after affiliations re-run.

---

### B-4: Fast-exit in `resolve_pending_participations`

**File:** `services/salesforce/processors/event.py` ~line 508

```python
def resolve_pending_participations(volunteers_cache=None, events_cache=None) -> int:
    from models.pending_participation import PendingParticipationImport

    # Fast-exit — avoid full table scan when queue is empty
    if not PendingParticipationImport.query.filter(
        PendingParticipationImport.resolved_at.is_(None)
    ).limit(1).first():
        return 0
    # ... existing logic
```

**AC:** Returns 0 immediately with no further queries when queue is empty.

---

## Sprint C — Performance (~5 hours)

### C-1: History import — pre-load volunteer + teacher caches

**File:** `routes/salesforce/history_import.py`

After fetching `task_rows` and `email_rows`, build lookup caches before the processing loops:

```python
all_who_ids = {r.get("WhoId") for r in task_rows + email_rows if r.get("WhoId")}

volunteer_history_cache = {
    v.salesforce_individual_id: v
    for v in Volunteer.query.filter(
        Volunteer.salesforce_individual_id.in_(list(all_who_ids))
    ).all()
}
teacher_history_cache = {
    t.salesforce_individual_id: t
    for t in Teacher.query.filter(
        Teacher.salesforce_individual_id.in_(list(all_who_ids))
    ).all()
    if hasattr(t, "salesforce_individual_id")
}
```

> If `all_who_ids` exceeds 999, use `chunked_in_query()` pattern from `organization_import.py`.

Replace per-row `Volunteer.query.filter_by(...)` with cache lookups.

**AC:** History import of 1,000+ records completes with 0 per-row volunteer/teacher DB queries.

---

### C-2: Delta sync for `sync_unaffiliated_events`

**File:** `routes/salesforce/pathway_import.py`

Add `DeltaSyncHelper("unaffiliated_events")` at the top of `sync_unaffiliated_events()` and append `build_date_filter(watermark)` to the SOQL query when delta mode is active. Pass `is_delta` to `create_sync_log_with_watermark()`.

**AC:** Running with `?delta=true` fetches only recently modified unaffiliated events. Watermark visible in health metrics.

---

### C-3: Pre-load event cache in `process_event_row`

**Files:** `services/salesforce/processors/event.py` + `routes/salesforce/event_import.py`

1. Add optional `events_cache: Optional[Dict[str, Event]] = None` to `process_event_row`
2. When provided, use `events_cache.get(event_sf_id)` instead of a DB query; add new events to the cache after flush
3. In `import_events_from_salesforce()`, build and pass the cache before the loop

**AC:** Event import of 3,450 events completes with 0 per-row `Event.query` calls.

---

## Sprint D — Architecture (~6 hours)

### D-1: Extract `_map_event_fields(event, row)` shared helper

**Files:** `services/salesforce/processors/event.py`, `routes/salesforce/pathway_import.py`

Extract all SF field → Event model assignments into a single helper. Both `process_event_row` and `_create_event_from_salesforce` call it. Adding a new SF field requires editing exactly 1 place.

---

### D-2: Shared `build_participation_caches()` utility

**File:** `services/salesforce/utils.py` (new function)

```python
def build_participation_caches(db_session) -> tuple[dict, dict]:
    """Returns (volunteers_cache, events_cache) mapping salesforce_id → local int id."""
    from models.event import Event
    from models.volunteer import Volunteer

    volunteers_cache = {
        sf_id: vol_id
        for vol_id, sf_id in db_session.query(
            Volunteer.id, Volunteer.salesforce_individual_id
        ).filter(Volunteer.salesforce_individual_id.isnot(None)).all()
    }
    events_cache = {
        sf_id: event_id
        for event_id, sf_id in db_session.query(
            Event.id, Event.salesforce_id
        ).filter(Event.salesforce_id.isnot(None)).all()
    }
    return volunteers_cache, events_cache
```

Replace inline cache-building in both `event_import.py` and `pathway_import.py`.

---

### D-3: Chunked commits in `resolve_pending_participations`

**File:** `services/salesforce/processors/event.py`

Add a batch commit every 500 records inside the sweep loop. A crash mid-sweep no longer loses all previously resolved records.

---

## Delivery Checklist

```
Pre-Flight  ──► [x] Pre-1: Alembic migration (entity_sf_id + pending_participation_imports)
            ──► [x] Pre-2: Fix TD-033 checkbox in roadmap

Sprint A    ──► [x] A-1 date_source fix
            ──► [x] A-2 STATUS_MAP normalization  (also check pathful imports)
            ──► [x] A-3 ALL_SYNC_TYPES constant
            ──► [x] A-4 pathway_import import fix
            ──► [x] A-5 Remove dead function copies + fix test imports

Sprint B    ──► [x] B-1 DQ flags for history
            ──► [x] B-2 Pending queue breakdown + CSV export
            ──► [x] B-3 Import ordering warning
            ──► [x] B-4 Fast-exit in resolve_pending

Sprint C    ──► [x] C-1 History N+1 fix
            ──► [x] C-2 Delta sync for unaffiliated events
            ──► [x] C-3 Event cache in process_event_row

Sprint D    ──►  D-1 Shared _map_event_fields helper
            ──►  D-2 Shared build_participation_caches util
            ──►  D-3 Chunked sweep commits
```

**Total estimated effort:** ~16–18 hours

---

## New Tech Debt Items (logged from pre-flight review)

| ID | Title | Status |
|---|---|---|
| TD-058 | Dead function copies in `routes/events/routes.py` | Addressed in Sprint A-5 |
| TD-059 | `fix_missing_participation_records()` called on every event page load (N+1) | Addressed in Sprint A-5 |
| TD-060 | `MISSING_ADDRESS` and `TRUNCATED_SKILL` zombie DQ issue types on dashboard | Backlog |

---

## References

- [salesforce_import_roadmap.md](salesforce_import_roadmap.md)
- [tech_debt.md](tech_debt.md)
- Pre-flight inspection notes (in session artifact)
