# Implementation Plan: Time-Scoped Volunteer–Organization Membership

> **Audience:** Junior developers
> **Status:** ✅ Parts 0, 1, 1-D, 2 COMPLETE — merged 2026-04-28
> **Priority:** High — affects accuracy of all Organization Reports
> **Next PR:** Part 4 (Admin UI for date editing)

---

## Problem Statement

Volunteers change employers. The system marks old `VolunteerOrganization` rows as
`status='Past'` and creates new ones as `status='Current'`, but reports never filter
on those values or on dates. A volunteer who left UMKC for Lockton in Aug 2025
appears on **both** org reports for **all** years.

**Immediate case — Lauren Orozco:**

| Org | Status | Correct behavior |
|---|---|---|
| UMKC | Past (left Aug 2025) | Show on UMKC report only **before** Aug 2025 |
| Lockton Companies | Current (joined Aug 2025) | Show on Lockton report only **from** Aug 2025 |

---

## How the Fix Works (Read This First)

The filter uses two rules:

1. **Current + no dates** → always include. Every active volunteer is unaffected.
2. **Past + `end_date` set** → include only if that window overlaps the report year.
3. **Past + no `end_date`** → exclude in Verified mode (we can't confirm when they left).

Reports get a **mode toggle**:

| Mode | Who appears |
|---|---|
| **Verified** (default) | Current members + Past members with known dates |
| **Full History** | Everyone ever linked to the org |

Current volunteers are **not affected** — they all continue to appear exactly as before.

---

## What Is NOT in This PR

The following are deliberately deferred:

| Deferred item | Why | Future PR? |
|---|---|---|
| Migrating 25+ direct `VolunteerOrganization(...)` constructor sites | Not needed for the fix; mechanical work | Yes — Part 1-D |
| Admin UI for editing dates on volunteer profile | Nice to have; not required | Yes — Part 4 |
| Status normalization SQL (`'Former'` → `'Past'`) | Run only if audit shows it's needed | Before Part 1-D |
| Date backfill for historical Past volunteers | **Not feasible** — `EventParticipation` has no `organization_id`, so we cannot reliably infer which org a volunteer was at for any given event. Existing Past/undated volunteers appear in Full History mode and admins can set dates via the future UI. | N/A |

---

## Delivery Order

```
✅ DONE (2026-04-28)   ──►  Part 0: Manual data patch for Lauren (flask shell)
✅ DONE (2026-04-28)   ──►  Part 1: Model changes + Alembic migration
✅ DONE (2026-04-28)   ──►  Part 2: org_membership_filter.py + route/template integration
⏭  SKIPPED             ──►  Part 3: Cache pre-warm script (not needed — reports are fast)
✅ DONE (2026-04-28)   ──►  Part 1-D: Migrate constructor sites to link_volunteer_to_org()
NEXT PR               ──►  Part 4: Admin UI for editing start_date/end_date on volunteer profile
```

---

## ✅ Completion Summary (2026-04-28)

All user-facing parts of this plan are implemented and verified.

### What was done

| Part | Description | Files changed |
|---|---|---|
| Part 0 | Lauren Orozco UMKC→Lockton patch (via flask shell) | DB only — no code |
| Part 1 | `date_source` column, `idx_vo_status_dates` index, `link_volunteer_to_org()` factory, `@validates('status')` auto-date hook | `models/organization.py`, `alembic/versions/4ad62fb9fdbd_...py` |
| Part 2 | `org_membership_filter.py` service, integrated into 3 report routes + `organization_service.py`, toggle UI in both templates | `utils/services/org_membership_filter.py`, `routes/reports/organization_report.py`, `utils/services/organization_service.py`, `templates/reports/organizations/organization_report.html`, `templates/reports/organizations/organization_report_detail.html` |

### Verified results

- **Lockton:** Verified=6 volunteers, Full=7 (Lauren correctly excluded from 2425 Verified view)
- **UMKC:** Verified=72, Full=78 (historical/undated Past members correctly excluded)
- All edge cases pass: injection attempts, all-time queries, `Current→Past` auto-date hook, cache bypass for Full mode

### What is NOT done (next PR)

| Item | Tech Debt ID | Status |
|---|---|---|
| Constructor migration | TD-054 | ✅ Resolved 2026-04-28 — Hybrid: `before_insert` hook (safety net for SF import) + 14 UI call sites migrated to `link_volunteer_to_org()`. |
| Admin UI for date editing | Part 4 | Pending — Allow admins to set `start_date`, `end_date`, `date_source` from the volunteer profile page. |

---

## Part 0 — Manual Data Patch for Lauren (No Code Deploy Needed)

Run in `flask shell` before anything else. This fixes Lauren immediately.

```python
from models.organization import VolunteerOrganization
from models.volunteer import Volunteer
from models.reports import OrganizationDetailCache, OrganizationSummaryCache
from models import db
from datetime import datetime

# Step 1: Find Lauren's rows — note both org IDs from the output
lauren = Volunteer.query.get(179891)
for vo in lauren.volunteer_organizations:
    print(vo.organization_id, vo.organization.name, vo.status, vo.start_date, vo.end_date)

# Step 2: Fill in these IDs from the output above
UMKC_ORG_ID    = <fill_in>
LOCKTON_ORG_ID = <fill_in>
TRANSITION     = datetime(2025, 8, 1)

# Step 3: Set the dates
umkc = VolunteerOrganization.query.filter_by(
    volunteer_id=lauren.id, organization_id=UMKC_ORG_ID).first()
umkc.end_date = TRANSITION
umkc.status   = 'Past'

lockton = VolunteerOrganization.query.filter_by(
    volunteer_id=lauren.id, organization_id=LOCKTON_ORG_ID).first()
lockton.start_date = TRANSITION
lockton.status     = 'Current'

# Step 4: Clear cache so reports regenerate fresh
OrganizationDetailCache.query.filter_by(organization_id=UMKC_ORG_ID).delete()
OrganizationDetailCache.query.filter_by(organization_id=LOCKTON_ORG_ID).delete()
OrganizationSummaryCache.query.delete()
db.session.commit()
print("Done. Verify by loading both org reports.")
```

**Verify immediately:**

- SY2425 UMKC report → Lauren appears ✅
- SY2425 Lockton report → Lauren does NOT appear ✅
- SY2526 Lockton report → Lauren appears ✅
- SY2526 UMKC report → Lauren does NOT appear ✅

> Part 0 fixes Lauren only. All other Past/undated volunteers are unchanged
> until the filter is deployed in Parts 1–3.

---

## Part 1 — Schema & Model Changes

**Files changed:** `models/organization.py`, one new Alembic migration
**Effort:** ~1 day

### 1-A: Alembic Migration

```bash
flask db migrate -m "add date_source to volunteer_organization and add index"
```

Edit the generated file:

```python
import sqlalchemy as sa

def upgrade():
    op.add_column(
        'volunteer_organization',
        sa.Column('date_source', sa.String(50), nullable=True)
        # Valid values: 'manual', 'auto_detected', 'salesforce', 'unknown'
    )
    # Composite index for the filter query pattern:
    # WHERE (status='Current' AND end_date IS NULL)
    #    OR (end_date IS NOT NULL AND end_date >= ?)
    op.create_index(
        'idx_vo_status_dates',
        'volunteer_organization',
        ['status', 'start_date', 'end_date']
    )

def downgrade():
    op.drop_index('idx_vo_status_dates', 'volunteer_organization')
    op.drop_column('volunteer_organization', 'date_source')
```

### 1-B: Create `link_volunteer_to_org` Classmethod

> **Important:** This method does **not exist yet**. Create it from scratch inside
> `VolunteerOrganization` in `models/organization.py`.
>
> Also add `date_source` to the model column definitions at the same time (matches
> the migration above).

```python
# Add this column alongside start_date / end_date in VolunteerOrganization:
date_source = db.Column(db.String(50), nullable=True)
# Valid values: 'manual', 'auto_detected', 'salesforce', 'unknown'


@classmethod
def link_volunteer_to_org(
    cls,
    volunteer,
    org_name=None,
    organization=None,
    role=None,
    is_primary=False,
    status='Current',
    start_date=None,
    end_date=None,
    date_source=None,
):
    """
    THE canonical way to create or update a VolunteerOrganization link.

    Use this instead of VolunteerOrganization(...) everywhere.
    Handles: org lookup, upsert, status normalization, auto start_date.

    Returns the VolunteerOrganization row (already added to session).
    Callers must NOT call db.session.add() — this method handles it.
    """
    from models import db
    from datetime import datetime, timezone

    # Normalize status strings so 'Former', 'former', 'past' all become 'Past'
    STATUS_MAP = {
        'former': 'Past', 'past': 'Past',
        'current': 'Current', 'pending': 'Pending',
    }
    normalized = STATUS_MAP.get((status or 'Current').lower(), 'Current')

    # Resolve org by name if object not passed directly
    if organization is None and org_name:
        organization = Organization.query.filter_by(name=org_name).first()
        if not organization:
            organization = Organization(name=org_name)
            db.session.add(organization)
            db.session.flush()

    if organization is None:
        raise ValueError("Must provide org_name or organization.")

    # Upsert: find existing row or create new
    vol_org = cls.query.filter_by(
        volunteer_id=volunteer.id,
        organization_id=organization.id,
    ).first()

    if vol_org:
        vol_org.status = normalized
        if role is not None:
            vol_org.role = role
        if is_primary:
            vol_org.is_primary = is_primary
        if start_date is not None:
            vol_org.start_date = start_date
            vol_org.date_source = date_source or 'manual'
        if end_date is not None:
            vol_org.end_date = end_date
            vol_org.date_source = date_source or 'manual'
    else:
        # Auto-set start_date=now for brand-new Current rows going forward
        effective_start = start_date
        effective_source = date_source
        if effective_start is None and normalized == 'Current':
            effective_start = datetime.now(timezone.utc)
            effective_source = effective_source or 'auto_detected'

        vol_org = cls(
            volunteer_id=volunteer.id,
            organization_id=organization.id,
            role=role,
            is_primary=is_primary,
            status=normalized,
            start_date=effective_start,
            end_date=end_date,
            date_source=effective_source,
        )
        db.session.add(vol_org)

    return vol_org
```

**Before/after example for any future migration of existing constructor sites:**

```python
# BEFORE (old pattern — do not use going forward):
vol_org = VolunteerOrganization(
    volunteer_id=volunteer.id,
    organization_id=org.id,
    is_primary=not has_primary,
)
db.session.add(vol_org)   # ← remove this line when switching to factory

# AFTER (new pattern):
vol_org = VolunteerOrganization.link_volunteer_to_org(
    volunteer=volunteer,
    organization=org,
    is_primary=not has_primary,
)
# Do NOT call db.session.add() — the factory handles it
```

### 1-C: Add `@validates('status')` Auto-Detection Hook

Add inside `VolunteerOrganization`, after the column definitions.
Uses the same pattern as `Teacher.validate_status` (`hasattr` guard).

```python
from sqlalchemy.orm import validates

@validates('status')
def auto_set_transition_dates(self, key, new_status):
    """
    Automatically record transition dates when status changes.
    - Current → Past:  set end_date = now (if not already set)
    - * → Current:    set start_date = now (if not already set)

    Uses hasattr guard (same as Teacher model) to avoid misfiring
    during initial DB row load.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    if hasattr(self, 'status') and self.status != new_status:
        if self.status == 'Current' and new_status == 'Past':
            if not self.end_date:
                self.end_date = now
                self.date_source = self.date_source or 'auto_detected'
        elif new_status == 'Current' and self.status != 'Current':
            if not self.start_date:
                self.start_date = now
                self.date_source = self.date_source or 'auto_detected'

    return new_status
```

> **Note for status normalization:** A quick audit of production status values is
> recommended before deploy. Run in flask shell:
> ```python
> from models import db
> from models.organization import VolunteerOrganization
> db.session.query(
>     VolunteerOrganization.status,
>     db.func.count(VolunteerOrganization.volunteer_id)
> ).group_by(VolunteerOrganization.status).all()
> ```
> If `'Former'` rows exist, the `@validates` hook and `link_volunteer_to_org`
> will normalize them going forward, but existing `'Former'` rows will not match
> `'Past'` in the filter. Update if needed (see Deferred section).

---

## Part 2 — Reporting Filter

**Files changed:** new `utils/services/org_membership_filter.py`,
`routes/reports/organization_report.py`, `utils/services/organization_service.py`,
one report template
**Effort:** ~1 day

### 2-A: Create `utils/services/org_membership_filter.py`

```python
"""
org_membership_filter.py
========================
Date-scoped volunteer-organization membership filter.

Policy:
  Verified mode (default):
    - Current + no dates        → always include (open-ended active member)
    - Past + end_date set       → include only if overlaps report window
    - Past + no end_date        → exclude (departure date unknown)
    - Pending + no end_date     → exclude (not yet active)
    - start_date set            → used as lower bound regardless of status

  Full History mode:
    → no filter applied; returns None; include everyone ever linked

NOTE on timezones: volunteer_organization.start_date / end_date are stored as
naive DateTime. Strip timezone from report boundary datetimes before comparing:
    report_start = start_date.replace(tzinfo=None)
"""
from sqlalchemy import and_, or_
from models.organization import VolunteerOrganization


def membership_date_filter(report_start, report_end, mode='verified'):
    """
    Returns a SQLAlchemy filter clause or None.

    Args:
        report_start: School year start datetime (naive)
        report_end:   School year end datetime (naive)
        mode:         'verified' (conservative default) or 'full' (no filter)

    Usage:
        mode = request.args.get('mode', 'verified')
        if mode not in ('verified', 'full'):   # whitelist — never trust raw input
            mode = 'verified'
        f = membership_date_filter(start, end, mode=mode)
        if f is not None:
            query = query.filter(f)
    """
    if mode == 'full':
        return None  # Full History: bypass filter entirely; also bypass cache

    if report_start is None and report_end is None:
        return None  # All-time query with no boundaries — nothing to scope

    # Strip timezone from boundaries to match naive DB columns
    if report_start and getattr(report_start, 'tzinfo', None):
        report_start = report_start.replace(tzinfo=None)
    if report_end and getattr(report_end, 'tzinfo', None):
        report_end = report_end.replace(tzinfo=None)

    VO = VolunteerOrganization

    # Rule 1: Membership must have started before the report window ended
    started_in_time = or_(
        VO.start_date == None,           # noqa: E711 — SQLAlchemy IS NULL
        VO.start_date <= report_end,
    )

    # Rule 2: Membership must still have been active during the window
    # Pending + no end_date → excluded (not yet active)
    # Past + no end_date   → excluded (unknown departure = conservative)
    still_active = or_(
        # Active current member with no known end
        and_(VO.status == 'Current', VO.end_date == None),  # noqa: E711
        # Any member whose recorded end overlaps the window
        and_(VO.end_date != None, VO.end_date >= report_start),  # noqa: E711
    )

    return and_(started_in_time, still_active)
```

### 2-B: Apply Filter — `routes/reports/organization_report.py`

Add at the top of the file:
```python
from utils.services.org_membership_filter import membership_date_filter
```

In each report view function, get and sanitize the mode:
```python
mode = request.args.get('mode', 'verified')
if mode not in ('verified', 'full'):
    mode = 'verified'
```

Apply the filter at these **4 query sites** (add after the existing `.filter(...)` call):
```python
date_filter = membership_date_filter(start_date, end_date, mode=mode)
if date_filter is not None:
    query = query.filter(date_filter)
```

| Query variable | Approx line | Event type |
|---|---|---|
| `org_stats` (HTML) | ~115 | In-person |
| `virtual_org_stats` (HTML) | ~152 | Virtual |
| `org_stats` (Excel export) | ~414 | In-person |
| `volunteer_stats` (Excel) | ~582 | Volunteer breakdown |

Also pass `mode` into the template context:
```python
return render_template(..., mode=mode)
```

### 2-C: Apply Filter — `utils/services/organization_service.py`

Same import. Add `mode='verified'` parameter to `get_organization_detail`:

```python
def get_organization_detail(self, org_id: int, school_year=None, mode='verified') -> Dict:
```

**Cache bypass for Full History** — replace the existing cache check block (lines 118–123):

```python
# Full History always bypasses cache — results are not stored
if school_year != 'all_time' and mode == 'verified':
    cache = OrganizationDetailCache.query.filter_by(
        organization_id=org_id, school_year=school_year
    ).first()
    if cache and self._is_cache_fresh(cache):
        return self._format_cached_data(organization, cache, school_year)
```

Add `_is_cache_fresh` method to the class (matches existing pattern in `cache_service.py`):

```python
def _is_cache_fresh(self, cache, max_age_hours=24) -> bool:
    """Returns True if the cache row was written within max_age_hours."""
    from datetime import timedelta, timezone
    if not cache or not cache.last_updated:
        return False
    last = cache.last_updated
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last) < timedelta(hours=max_age_hours)
```

Pass `mode` into `_get_volunteers_data`, `_get_in_person_events`, `_get_virtual_events`,
`_get_cancelled_events` and apply the filter in each:

```python
# In each method, after existing .filter(...) calls:
from utils.services.org_membership_filter import membership_date_filter

date_filter = membership_date_filter(start_date, end_date, mode=mode)
if date_filter is not None:
    query = query.filter(date_filter)
```

**Do not cache Full History results** — update `_cache_organization_detail` call:

```python
# Only cache Verified results
if school_year != 'all_time' and mode == 'verified':
    self._cache_organization_detail(...)
```

### 2-D: Add Mode Toggle to Report Template

Add above the report table in the org report HTML template:

```html
<div class="report-mode-toggle mb-3">
  <div class="btn-group" role="group" aria-label="Report mode">
    <a href="{{ url_for(request.endpoint, **dict(request.args, mode='verified')) }}"
       class="btn btn-sm {{ 'btn-primary' if mode != 'full' else 'btn-outline-secondary' }}">
      Verified Members Only
    </a>
    <a href="{{ url_for(request.endpoint, **dict(request.args, mode='full')) }}"
       class="btn btn-sm {{ 'btn-primary' if mode == 'full' else 'btn-outline-secondary' }}">
      Include Unverified Members
    </a>
  </div>
  <small class="text-muted ms-2">
    {% if mode == 'full' %}
      Showing all members ever linked to this organization.
      Counts may be overstated for members whose affiliation dates are unknown.
    {% else %}
      Showing members whose affiliation dates are known or confirmed.
      Use "Include Unverified Members" to see all historical associations.
    {% endif %}
  </small>
</div>
```

Also add a note to the Excel export header:
```python
mode_label = "Include Unverified Members" if mode == 'full' else "Verified Members Only"
# Write to cell A1 before data rows:
ws['A1'] = f"Organization Report — {mode_label}"
```

---

## Part 3 — Cache Fix + Pre-Warm

**Files changed:** `utils/services/organization_service.py` (partially done in Part 2),
`app.py`
**Effort:** ~2 hours

### 3-A: Cache TTL

Already handled in Part 2-C via `_is_cache_fresh(cache, max_age_hours=24)`.
The org detail cache was the only cache in the system without a TTL — this fixes that.

### 3-B: Add Pre-Warm CLI Command

**File:** `app.py` (add near other CLI commands, or in a `cli.py` if one exists)

```python
import click
from flask.cli import with_appcontext

@app.cli.command("prewarm-org-cache")
@click.option("--school-year", default=None,
              help="School year to warm, e.g. '2526'. Defaults to current year.")
@with_appcontext
def prewarm_org_cache(school_year):
    """Clear stale org caches and regenerate for all organizations."""
    from models.reports import OrganizationDetailCache, OrganizationSummaryCache
    from models.organization import Organization
    from models import db
    from utils.services.organization_service import OrganizationService
    from routes.reports.common import get_current_school_year

    sy = school_year or get_current_school_year()

    OrganizationDetailCache.query.filter_by(school_year=sy).delete()
    OrganizationSummaryCache.query.filter_by(school_year=sy).delete()
    db.session.commit()
    click.echo(f"Cleared cache for {sy}.")

    service = OrganizationService()
    orgs = Organization.query.all()
    click.echo(f"Pre-warming {len(orgs)} organizations for {sy}...")

    for i, org in enumerate(orgs, 1):
        try:
            service.get_organization_detail(org.id, sy, mode='verified')
            click.echo(f"  [{i}/{len(orgs)}] {org.name} ✓")
        except Exception as e:
            click.echo(f"  [{i}/{len(orgs)}] {org.name} FAILED: {e}")

    click.echo("Pre-warm complete.")
```

---

## Files Changed in This PR

| File | Change type | Notes |
|---|---|---|
| `alembic/versions/<new>.py` | New | `date_source` column + composite index |
| `models/organization.py` | Edit | Add `date_source` column, create `link_volunteer_to_org`, add `@validates` |
| `utils/services/org_membership_filter.py` | **New file** | ~50 lines, core filter logic |
| `routes/reports/organization_report.py` | Edit | Filter at 4 sites + mode param + template context |
| `utils/services/organization_service.py` | Edit | Filter at 4 methods + cache TTL + mode param |
| Report HTML template | Edit | Mode toggle + disclaimer |
| `app.py` | Edit | `prewarm-org-cache` CLI command |

---

## Testing Checklist

Run these after deploy, before closing the PR.

### Smoke tests (do these first)

- [ ] `flask db upgrade` runs cleanly, no errors
- [ ] Current volunteer at any org still appears on that org's report ✅ (regression check)
- [ ] Lauren — SY2425 UMKC report: appears ✅
- [ ] Lauren — SY2425 Lockton report: does NOT appear ✅
- [ ] Lauren — SY2526 Lockton report: appears ✅
- [ ] Lauren — SY2526 UMKC report: does NOT appear ✅

### Toggle tests

- [ ] **Verified mode** (default, no `?mode=` param): Lauren correctly scoped
- [ ] **Full History mode** (`?mode=full`): Lauren appears on both orgs (intentional)
- [ ] **Invalid mode** (`?mode=hacked`): falls back to Verified, no error
- [ ] Toggle buttons render and switch correctly

### Cache tests

- [ ] After hard-refreshing an org detail page, data is correct (not stale)
- [ ] Full History mode page does NOT write to cache (check DB: no new cache row appears)
- [ ] `flask prewarm-org-cache --school-year 2526` runs to completion
- [ ] Org detail page loads fast after pre-warm (cache hit)

### Regression tests (run existing test suite)

- [ ] `pytest tests/integration/test_organization_reporting.py` — all pass
- [ ] `pytest tests/integration/test_organization_report_excel.py` — all pass

---

## Deploy Checklist (Production)

Run in this exact order:

```
[ ] 1. Run Part 0 (flask shell) to patch Lauren's dates — if not done already
[ ] 2. Deploy the code
[ ] 3. flask db upgrade
[ ] 4. Audit status values (flask shell query above) — fix 'Former' rows if found
[ ] 5. flask prewarm-org-cache --school-year 2526
[ ] 6. flask prewarm-org-cache --school-year 2425
[ ] 7. Verify Lauren's reports for both school years
[ ] 8. Notify stakeholders: org report volunteer counts may decrease for some orgs
        in Verified mode — this is correct behavior, not a bug. Full History mode
        shows previous counts.
```

---

## Deferred — Future PRs

### Part 1-D: Constructor Site Migration — ✅ COMPLETE (2026-04-28)

Resolved via TD-054 using a **hybrid approach**:

1. **`before_insert` SQLAlchemy hook** added to `models/organization.py` — fires transparently on every new `VolunteerOrganization` INSERT, auto-setting `start_date` and `date_source='auto_detected'` for new `Current` rows. This preserves the N+1-free pre-loaded dict cache in `organization_import.py`.

2. **14 Tier-2 UI call sites** migrated to `link_volunteer_to_org()` with meaningful `date_source` labels:

| File | Sites | date_source |
|---|---|---|
| `routes/virtual/pathful_import/routes.py` | 7 | `'pathful'` |
| `routes/virtual/usage/session_routes.py` | 5 | `'manual'` |
| `routes/virtual/pathful_import/matching.py` | 1 | `'pathful'` |
| `models/event.py` | 2 | `'csv_import'` |

3. **10 test fixture sites** intentionally left as direct constructors — test fixtures are explicit by design.

### Part 4: Admin UI for Date Editing

Allows admins to set/correct dates directly from the volunteer profile page.
Includes cache invalidation on save and audit logging.
Define the scope once Part 1-D is complete.
