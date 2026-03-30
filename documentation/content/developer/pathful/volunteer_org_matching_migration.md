# TD-052: Volunteer Org Matching — Migrate to Alias-Based Resolution

**Created:** 2026-03-30 · **Priority:** Medium · **Category:** Data Integrity / Architecture
**Status:** Planned — provisional regex fix active (see [Current State](#current-state))
**Related TD:** TD-010 (DistrictAlias pattern, ✅ resolved)
**Related ADR:** *(new ADR recommended — see [ADR Recommendation](#adr-recommendation))*

---

## Problem Statement

When Pathful session reports are imported, "professional" participants (volunteers presenting at
virtual sessions) are matched to existing `Volunteer` records via `match_volunteer()` in
`routes/virtual/pathful_import/matching.py`. When no match is found by `pathful_user_id` or
email, the function creates a new `Volunteer` record and attempts to link them to an
`Organization` by **exact case-insensitive name match** on the `"District or Company"` field
from the Pathful CSV.

This exact match fails silently whenever Pathful's company string differs from the canonical
org name in the database. For example:

| Pathful CSV value | DB canonical name | Result |
|---|---|---|
| `"Turner Construction Company"` | `"Turner Construction"` | ❌ New duplicate org created |
| `"KC Tomorrow"` | `"Kansas City Tomorrow"` | ❌ New duplicate org created |
| `"AECOM Inc."` | `"AECOM"` | ❌ New duplicate org created |

A suffix-stripping regex was applied as a **provisional fix** on 2026-03-30 (strips "Company",
"Inc.", "LLC", "Corp", etc.), but this does not cover abbreviations, trade names, or any
variation the admin has not pre-registered.

The current approach also creates `VolunteerOrganization` links automatically during import
without any admin verification, which can silently mis-attribute volunteers to the wrong org.

---

## Current State

Three files were modified on 2026-03-30 as a working fix for the immediate issue (Turner
Construction / Carson Gonzalez & Marissa Plath):

| File | What changed | Limitation |
|---|---|---|
| `routes/virtual/pathful_import/matching.py` | Creates `Volunteer` + `VolunteerOrganization` for new professionals; suffix-regex org lookup | Regex can't catch abbreviations or trade names |
| `utils/services/organization_service.py` | `_get_volunteers_data()` now unions `event_volunteers` M2M + `EventParticipation` | None — this part is correct and final |
| `routes/reports/organization_report.py` | Summary list query also unions both tables | None — this part is correct and final |

The org report query fixes (**Bug 2**) are **permanent and correct** regardless of how
volunteer creation is handled. Only the org-matching logic in `matching.py` (**Bug 1**) needs
the architectural migration described here.

---

## Target Architecture

### Principle: Mirror the DistrictAlias Pattern

`upsert_district()` (TD-010, resolved) uses a 4-tier lookup:
1. Cache hit
2. Canonical name match
3. Alias match (via `DistrictAlias` table)
4. Create new + register incoming name as alias

Organizations need the same infrastructure: an **`OrganizationAlias`** table where admins
pre-register known alternative names (Pathful variants, abbreviations, trade names) so the
import can resolve them without creating duplicates.

### New Model: `OrganizationAlias`

```python
class OrganizationAlias(db.Model):
    __tablename__ = "organization_alias"

    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(255), nullable=False, unique=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    source = db.Column(db.String(64))          # e.g. "pathful", "manual", "salesforce"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    organization = db.relationship("Organization", back_populates="aliases")
```

Add to `Organization`:
```python
aliases = db.relationship("OrganizationAlias", back_populates="organization", lazy="dynamic")
```

### New Service Function: `resolve_organization()`

Mirrors `resolve_district()` in `services/district_service.py`:

```python
def resolve_organization(name: str, caches: dict = None) -> Organization | None:
    """
    Resolve an org name to an existing Organization record.

    Lookup priority:
    1. Cache hit (org_by_name + org_by_alias)
    2. Exact case-insensitive name match
    3. Alias match via OrganizationAlias table
    4. Suffix-stripped fallback (Company, Inc, LLC, etc.)

    Returns Organization if found, None if no match.
    Does NOT create a new org — caller decides what to do on miss.
    """
```

### Migration of `match_volunteer()` Org Linking

**Remove** the auto-create `VolunteerOrganization` logic from `match_volunteer()`.

**Replace** with:
1. Call `resolve_organization(organization_name, caches)`.
2. If found → create `VolunteerOrganization` link and proceed as normal.
3. If NOT found → store the raw string in `Volunteer.organization_name` (text field, already
   exists on the model). Do NOT create an Organization or VolunteerOrganization. Surface in
   the draft review queue (see below).

```python
# Proposed match_volunteer creation block (simplified)
volunteer = Volunteer(
    first_name=first_name,
    last_name=last_name,
    pathful_user_id=pathful_id_str or None,
    organization_name=organization_name,   # raw text fallback
)
db.session.add(volunteer)
db.session.flush()

org = resolve_organization(organization_name, caches=caches)
if org:
    # Clean FK link — org was found in the alias registry
    vol_org = VolunteerOrganization(
        volunteer_id=volunteer.id,
        organization_id=org.id,
        is_primary=True,
    )
    db.session.add(vol_org)
    # Auto-register the alias so future imports resolve without admin action
    if organization_name.lower() != org.name.lower():
        _ensure_org_alias(organization_name, org.id)
else:
    # No resolved org — leave for draft review queue
    pass
```

### Draft Review Queue Integration

Unresolved volunteer org matches surface in `draft_review_service.py` with a new queue type:

```python
class DraftReviewType(str, Enum):
    DRAFT_EVENT = "draft_event"          # existing
    UNRESOLVED_VOLUNTEER_ORG = "unresolved_volunteer_org"  # new
```

The review UI (`/pathful/draft-review`) shows a card for each unresolved volunteer:

```
Carson Gonzalez  |  "Turner Construction Company"  |  Crafting Success (02/25/26)
[ Link to existing org ▾ ]  [ Create new org ]  [ Mark as Independent ]
```

When an admin selects "Turner Construction" → creates the `VolunteerOrganization` FK,
registers "Turner Construction Company" as an `OrganizationAlias`, and clears the review item.

> [!IMPORTANT]
> Until an admin resolves the item, the volunteer **will not appear on the org report**.
> This is a deliberate accuracy-over-immediacy tradeoff. Volunteers do appear in the
> virtual session's own volunteer list immediately after import.

---

## Migration Plan

### Phase 0 — Prerequisites (do before any code changes)

- [ ] Audit existing `OrganizationAlias`-style variants already in the DB by querying
  `pathful_unmatched_record.attempted_match_organization` for all-time imports and
  comparing against `organization.name`.
- [ ] Identify any duplicate orgs already created by the current regex fix (run
  `check_duplicate_orgs.py` — see [Verification](#verification)).
- [ ] Merge/clean any duplicate orgs found before the new alias table is introduced.

### Phase 1 — Schema (1 migration file)

- [ ] Create `OrganizationAlias` model in `models/organization.py`.
- [ ] Write Alembic migration: `add_organization_alias_table`.
- [ ] Add `Organization.aliases` relationship.
- [ ] Add `org_by_alias` cache to `build_import_caches()` in `matching.py`.

### Phase 2 — Service Layer

- [ ] Create `resolve_organization(name, caches)` in `services/organization_service.py`
  (or a new `services/organization_matching_service.py` to mirror
  `services/district_service.py`).
- [ ] Implement 4-tier lookup: cache → exact name → alias → suffix-stripped.
- [ ] Add `_ensure_org_alias(alias_str, org_id)` helper that creates alias records when
  an import-time variant resolves to an existing org.
- [ ] Unit tests: `tests/unit/services/test_organization_matching_service.py`
  - exact match, alias match, suffix match, no match, auto-alias creation.

### Phase 3 — Import Changes

- [ ] Replace org-creation block in `match_volunteer()` with call to `resolve_organization()`.
- [ ] Remove suffix-stripping regex (`_find_org` function) — now handled by service.
- [ ] Add `org_by_alias` to cache dict in `build_import_caches()`.
- [ ] Update unmatched record to include `resolved_volunteer_id` FK (so the review queue
  knows which volunteer to link when admin resolves).

### Phase 4 — Draft Review Queue

- [ ] Add `UNRESOLVED_VOLUNTEER_ORG` type to `DraftReviewType` enum.
- [ ] Update `get_draft_review_queue()` in `draft_review_service.py` to include unresolved
  volunteer org records (join `pathful_unmatched_record WHERE volunteer_id IS NOT NULL AND
  unmatched_type = 'VOLUNTEER' AND ...`).
- [ ] Add `resolve_volunteer_org(volunteer_id, org_id, user_id)` action to service:
  - Creates `VolunteerOrganization` FK
  - Creates `OrganizationAlias` for the Pathful string
  - Marks the unmatched record as resolved
  - Audit logs the action
- [ ] Update the draft review template (`templates/virtual/pathful/draft_review.html`) to
  render volunteer org cards with org search/select.
- [ ] Integration tests: `tests/integration/test_draft_review.py` — extend existing suite.

### Phase 5 — Admin UI for OrganizationAlias Management

- [ ] Add `OrganizationAlias` CRUD to the existing org management pages (or a new
  `/admin/organizations/aliases` route).
- [ ] Allows admins to pre-register known aliases before a Pathful import runs (e.g.,
  register "Turner Construction Company" → Turner Construction so the next import resolves
  automatically without queuing).

### Phase 6 — Backfill

- [ ] Write `scripts/maintenance/backfill_org_aliases.py`:
  - Queries all `pathful_unmatched_record.attempted_match_organization` for resolved
    volunteers (those who now have a `VolunteerOrganization` via the data fix or admin action).
  - Registers any unregistered variants as `OrganizationAlias` records.
- [ ] Run on both local and production after Phase 1–5 are deployed.

---

## ADR Recommendation

File a new ADR: **"Entity Identity Reconciliation Pattern"**

**Decision:** All external-source name resolution (Pathful mapping to Districts, Schools, and Organizations) uses `resolve_entity()` combined with an `Alias` registry (e.g., `DistrictAlias`, `SchoolAlias`, `OrganizationAlias`). Auto-creation of relationships (like `VolunteerOrganization` or fallback guessing of a `School`) without admin verification is strictly prohibited. Unresolved entities must fail loudly and safely to the `PathfulUnmatchedRecord` queue.

**Rationale:** The string-munging regex approach (active since 2026-03-30 for Orgs) is fundamentally insufficient and fragile. The Entity Identity Reconciliation pattern (TD-010 for Districts, Epic 17 Option 3 hardening for Schools) has proven correct for solving this entire class of problems. Extending it to Volunteer-Org matching gives Admins a single, unified "Unmatched Queue" to resolve missing data safely.

## Verification

After Phase 1–3 are deployed, run:

```sql
-- Check for duplicate orgs with similar names (should be 0 after cleanup)
SELECT a.id, a.name, b.id, b.name
FROM organization a
JOIN organization b ON a.id < b.id
WHERE lower(a.name) LIKE lower(b.name) || '%'
   OR lower(b.name) LIKE lower(a.name) || '%';

-- Check alias coverage for common Pathful org variants
SELECT attempted_match_organization, COUNT(*) as freq
FROM pathful_unmatched_record
WHERE unmatched_type = 'VOLUNTEER'
GROUP BY attempted_match_organization
ORDER BY freq DESC
LIMIT 50;
```

After Phase 4, verify:
- Volunteers with unresolved org display in draft review queue at `/pathful/draft-review`
- Resolving one creates `VolunteerOrganization` + `OrganizationAlias`
- Re-importing the same session report resolves the volunteer directly (no review needed)

---

## Notes

- **The Bug 2 fix** (`_get_volunteers_data` and org summary union queries) is **independent**
  of this migration and is already correct. Do not revert it.
- **The suffix-regex `_find_org` function** in `matching.py` is the only code to remove
  once Phase 2 is complete. Everything else in `match_volunteer()` stays.
- **`Volunteer.organization_name`** (text field) already exists on the model — it is the
  intended fallback for unresolved org names. No schema change needed for this field.
