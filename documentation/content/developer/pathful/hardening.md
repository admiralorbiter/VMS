# Pathful Import Pipeline — Hardening Plan

**Epic: Import Integrity & False-Positive/Negative Prevention**
**Status:** 🔧 IN PROGRESS — Phase E (C1 + C2 complete)
**Last Updated:** 2026-04-01
**Author:** AI Collab (sessions 929d9ac2, 854a998c)

> [!IMPORTANT]
> This plan was created after a root-cause investigation triggered by missing sessions
> on the KCNSC employer report. A full pipeline audit revealed five structural gaps.
> All decisions in this document follow the [AI Collaboration Guide](../ai_collab_guide.md)
> decision-making format (2 options max, recommendation stated, tradeoffs documented).

---

## Background & Motivation

### Incident Summary (2026-03-31)

A user reported that two volunteer sessions were missing from the KCNSC employer report.
Investigation revealed two distinct root causes, one per person:

**Bug A — Amanda Turk:** The Pathful import stored the company name as plain text in
`volunteer.organization_name` but never wrote a `VolunteerOrganization` FK row — the
actual relational link the org report queries. Session was in the DB but invisible on
all reports. Affected **107 volunteers historically**.

**Bug B — David Switzer:** The volunteer's name in Pathful (`Dave`) differed from the
VMS canonical record (`David`). `pathful_user_id` was `None` on the Salesforce-synced
record. Both lookups failed → import created a **duplicate `Dave Switzer`** → session
attributed to the duplicate → canonical `David Switzer` shows 0 sessions.
Found **152 collision events in one spreadsheet alone**.

### Pipeline Audit Results

A full audit of every matching decision point in `matching.py` identified 5 gaps:

| # | Component | Risk Type | Severity |
|---|---|---|---|
| 1 | Teacher model name cache — no collision detection | False Positive | 🔴 High |
| 2 | Event P2 (title+date) — no cross-check before merge | False Positive | 🟠 Medium |
| 3 | Email caches — no collision detection (vol + teacher) | False Positive | 🟡 Medium |
| 4 | `resolve_organization` T4 — auto-learns aliases without admin review | False Positive | 🟠 Medium |
| 5 | Historical duplicate volunteers — 152+ existing collisions not surfaced | False Negative | 🟡 Medium |

### Fixes Applied Before This Plan

The following were fixed during the investigation session and are already in production:

- ✅ `_ensure_volunteer_org_link` added to import pipeline (Bug A root cause)
- ✅ Company quarantine queue added (aggregate view, bulk-map, alias cascade)
- ✅ Volunteer Priority 4 (near-name match) implemented as **quarantine-first** (not auto-merge)
- ✅ `confirm_near_match` / `reject_near_match` resolve actions added
- ✅ Near-match candidates surfaced in `get_match_suggestions` via `_near_match_volunteer_ids`

---

## Phase E: Hardening Epics

### Epic A — High-severity fixes (small effort, immediate)

#### A1 — Teacher model cache collision detection

**File:** `routes/virtual/pathful_import/matching.py`, `build_import_caches()` lines 124–139

**Problem:**
`teacher_record_by_name` cache uses plain `dict[key] = t` assignment. Unlike the
`teacher_by_name` (TeacherProgress) cache which sets to `None` on collision,
`teacher_record_by_name` silently lets the second teacher overwrite the first. Two
teachers with the same normalized full name → wrong teacher gets attendance attributed.

The `setdefault()` used for the short-key (first-word-of-last) *is* safe, but the
primary key assignment is not.

**Decision:**

| Option | Approach | Pro | Con | Recommended |
|---|---|---|---|---|
| **A** | Mirror TeacherProgress pattern: track seen keys; if key already exists, set to `None` (collision marker). Lookups skip `None`. | Simple, consistent, zero behavior change for unique names | Collision produces no quarantine alert — fails silently | ✅ **Yes** |
| **B** | Store a list on collision; during lookup create quarantine ticket listing both candidates | Surfaces ambiguity explicitly to admin | Requires changing lookup + caller logic — medium scope | Later |

**Decision: Option A now.** Immediate safety fix. Option B (explicit surfacing) is a
follow-on enhancement, not a blocker.

**Implementation:**
```python
# In build_import_caches(), teacher_record_by_name build loop:
norm_name = f"{norm_first} {norm_last}".strip()
if norm_name:
    if norm_name in teacher_record_by_name:
        teacher_record_by_name[norm_name] = None  # collision — skip on lookup
    else:
        teacher_record_by_name[norm_name] = t
```

**Verification:**
- Import a file where two teachers have identical normalized names
- Confirm neither is matched (both create new records / quarantine tickets)
- Confirm no attendance is misattributed

**Acceptance criteria:**
- [ ] `teacher_record_by_name` sets `None` on collision (matches TeacherProgress pattern)
- [ ] Lookup skips `None` entries
- [ ] Unit test: two teachers with same name in cache → lookup returns `None`

---

#### A2 — Event P2 (title+date) session_id cross-check

**File:** `matching.py`, `match_or_create_event()` lines 349–367

**Problem:**
P2 matches events by `(title.lower(), date)`. If two different Pathful sessions share
an identical title on the same day (two consecutive "Creative Careers Uncovered" back-to-back
sessions), P2 silently merges them into one Event record. No quarantine ticket created.
Participant counts and teacher links become incorrect.

**Decision:**

| Option | Approach | Pro | Con | Recommended |
|---|---|---|---|---|
| **A** | Before accepting P2 match: if incoming `session_id` is non-null AND matched event already has a *different* non-null `session_id` → skip P2, create new event | Surgical fix, zero impact on normal flow | Assumes Pathful session IDs are stable (they are) | ✅ **Yes** |
| **B** | Remove P2 entirely — only match by session_id | Cleanest possible logic | Rows with missing session_id always create duplicate events; breaks historical deduplication | No |

**Decision: Option A.** Session IDs are stable Pathful identifiers. The cross-check is
one conditional — low risk, high protection.

**Implementation:**
```python
# In match_or_create_event(), the P2 block:
if event:
    # GUARD: if incoming session_id conflicts with the matched event's session_id,
    # these are two different sessions that share a title+date — do NOT merge.
    if (session_id_str
            and event.pathful_session_id
            and event.pathful_session_id != session_id_str):
        # Fall through to create new event
        pass
    else:
        if session_id_str and not event.pathful_session_id:
            event.pathful_session_id = session_id_str
        _update_matched_event(event, status_str, career_cluster)
        return event, "matched_by_title_date"
```

**Acceptance criteria:**
- [ ] Two rows with same title+date but different session_ids → two distinct Event records
- [ ] Two rows with same title+date and same session_id → one Event record (idempotent)
- [ ] Re-import of same file → no new events created

---

### Epic B — Structural guardrails (medium effort, next session)

#### B1 — Email collision detection in volunteer and teacher caches

**File:** `matching.py`, `build_import_caches()` lines ~70–82 (volunteer) and ~43–44 (teacher)

**Problem:**
Both `volunteer_by_email` and `teacher_by_email` caches use plain `dict[email] = record`
assignment. If two people share an email (family account, shared department inbox),
the second record silently overwrites the first. Either person may receive the other's
sessions.

**Decision:**

| Option | Approach | Pro | Con | Recommended |
|---|---|---|---|---|
| **A** | Check before setting; if collision, set to `None`. Lookup sees `None` → skip email match, fall through to name match. | Consistent with name cache pattern. Immediate fix. | No admin alert — silent fallthrough | ✅ **Yes (now)** |
| **B** | Option A + track `_email_collisions` set; surface on import log page as a warning | Makes problem visible; admin can clean up shared emails | Medium UI effort | Later |

**Decision: Option A now, Option B in a future session.**

**Implementation:**
```python
# volunteer_by_email build:
for email_addr, contact_id in volunteer_emails:
    if email_addr and contact_id in vol_id_map:
        key = email_addr.lower()
        if key in volunteer_by_email:
            volunteer_by_email[key] = None  # collision marker
        else:
            volunteer_by_email[key] = vol_id_map[contact_id]

# teacher_by_email build:
for t in all_teachers:
    if t.email:
        key = t.email.lower()
        if key in teacher_by_email:
            teacher_by_email[key] = None  # collision marker
        else:
            teacher_by_email[key] = t
```

**Acceptance criteria:**
- [ ] Two volunteers with same email → both email lookups return `None`
- [ ] Import falls through to name match (no wrong attribution)
- [ ] Unit test: collision scenario verified

---

#### B2 — Organization T4 auto-alias: quarantine-first instead of auto-learn

**File:** `services/organization_service.py` lines 93–134

**Problem:**
`resolve_organization` Tier 4 uses a suffix-stripping regex to find near-matches, then
**immediately writes** an `OrganizationAlias` with `is_auto_generated=True`. If the
suffix-strip produces a spurious match (two different companies that become identical
after stripping punctuation and corporate suffixes), that alias is permanent.
Every future volunteer with that company string is silently linked to the wrong employer.
The `is_auto_generated=True` flag is never surfaced in the admin UI.

**Decision:**

| Option | Approach | Pro | Con | Recommended |
|---|---|---|---|---|
| **A** | Keep auto-learn, but add a UI panel in the quarantine page listing auto-generated aliases with Confirm/Delete buttons | Fast path preserved; admin can audit afterwards | Window of time where wrong alias is active | No |
| **B** | T4 returns `None` and creates an `ORGANIZATION` quarantine ticket instead of writing the alias. Admin confirms in quarantine → alias written | Zero false positive window. Consistent with volunteer near-match pattern. | Every new company string (even obviously correct ones like "Prep-KC, Inc." → "Prep-KC") requires one admin click | ✅ **Yes** |
| **C** | T4 auto-learns only for company strings already seen in the quarantine queue | Limits damage to previously-reviewed strings | Complex conditional; quarantine is the right abstraction | No |

**Decision: Option B.** After admin confirms, the alias is permanent (future imports hit T3).
One admin click per novel company string is the right tradeoff for correct employer
attribution. Consistent with the quarantine-first philosophy applied to volunteer near-matches.

**Implementation sketch:**
```python
# In resolve_organization(), T4 block — replace auto-learn with quarantine:
if fallback_match:
    logger.info(
        "Near-org match found (T4): '%s' → '%s'. Queuing for admin confirmation.",
        name, fallback_match.name
    )
    # DO NOT write alias here.
    # Return None so the caller (_ensure_volunteer_org_link) creates a quarantine ticket.
    # The quarantine ticket's attempted_match_organization = name, and we store
    # the candidate org_id in raw_data as '_near_org_match_id' for the suggestion engine.
    return None  # Will cause _ensure_volunteer_org_link to quarantine
```

The `_ensure_volunteer_org_link` caller already creates an `ORGANIZATION` quarantine ticket
when `resolve_organization` returns `None`. We add the candidate ID to `raw_data` for the UI.

The resolve handler then gains a `confirm_org_alias` action that:
1. Writes the `OrganizationAlias` (what T4 used to do)
2. Links the volunteer's `VolunteerOrganization` row
3. Runs the existing sibling cascade (links all pending records with the same company string)
4. Marks the ticket resolved

**Acceptance criteria:**
- [ ] T4 no longer writes aliases automatically
- [ ] A quarantine ticket is created with the near-match candidate visible in suggestions
- [ ] Admin confirms → alias written, volunteer linked, siblings cascaded
- [ ] Admin rejects → ticket closed, company string stays in queue for manual mapping
- [ ] Existing auto-generated aliases (already in DB) are unaffected

---

#### B3 — Historical duplicate volunteer backfill (dry-run first)

**File:** New script: `scripts/maintenance/backfill_near_match_tickets.py`

**Problem:**
152+ name/ID collision events were found in just one spreadsheet. These represent existing
duplicate volunteer records in the DB right now. Each one is a session silently attributed
to a duplicate rather than the canonical volunteer, producing incorrect org report counts.
They are invisible until a user notices missing sessions (as with KCNSC).

**Decision:**

| Option | Approach | Pro | Con | Recommended |
|---|---|---|---|---|
| **A** | Maintenance script: dry-run finds all pairs (one with `pathful_user_id`, one without, same last name, same first-3-char prefix), then --apply creates a quarantine ticket for each pair | Safe, auditable, admin-controlled merge | Creates a burst of quarantine tickets | ✅ **Yes** |
| **B** | Leave them to surface organically as users report issues | No admin burden now | KCNSC-type issues keep appearing; each requires a user complaint to detect | No |

**Decision: Option A** — dry-run first to see exact count, then apply.

**Script contract:**
```
python scripts/maintenance/backfill_near_match_tickets.py --dry-run
  → Prints: "Found N duplicate pairs. Would create N quarantine tickets."
  → Writes audit JSON to tmp/near_match_backfill_YYYY-MM-DD.json

python scripts/maintenance/backfill_near_match_tickets.py --apply
  → Creates PathfulUnmatchedRecord (type=VOLUNTEER) for each pair
  → Stores {_near_match_volunteer_ids: [canonical_id]} in raw_data on duplicate's ticket
  → Writes audit log JSON (for undo reference)
  → Reports: "Created N tickets. Run dry-run to verify."
```

**Safety rules (per [AI Collab Guide](../ai_collab_guide.md#data-operations-safety-pattern)):**
1. Dry-run always first — default if no flag given
2. Audit JSON written before any writes
3. No data deleted — only quarantine tickets created
4. Flask server must be stopped before running (SQLite locking)

**Acceptance criteria:**
- [ ] `--dry-run` runs safely with server stopped, outputs count and JSON
- [ ] `--apply` creates tickets with correct `raw_data` and `_near_match_volunteer_ids`
- [ ] Admin can find the tickets in the quarantine queue (Volunteers filter)
- [ ] Near-match suggestion engine surfaces the canonical candidate from `_near_match_volunteer_ids`
- [ ] Confirm/reject flow (already built) works for these backfilled tickets

---

### Epic C — Future Hardening (next sprint, after A+B stable)

#### C1 — Pathful email backfill onto existing volunteer records ✅ DONE

**Problem (root cause of B3):** Salesforce-synced volunteers have `pathful_user_id=None`.
Every import of that person falls through to name match. Even a small name variant
(Dave/David) creates a duplicate. Over hundreds of imports, this compounds.

**Fix:** After each P3 (name) match or new volunteer creation (P4 fallthrough),
the import calls `backfill_volunteer_from_profile(volunteer, pathful_user_id_str)`
from `services/pathful_id_backfill_service.py`. The service:

1. Writes `pathful_user_id` onto the Volunteer if not already set → **P1 wins on every future import**
2. Looks up `PathfulUserProfile` for the same `pathful_user_id`
3. If a profile exists and has a `login_email`, adds that email to the `contact_email`
   table (type=`professional`, primary=False) → **P2 wins if User Report is imported first**
4. Links `PathfulUserProfile.volunteer_id` → Volunteer (for downstream enrichment)

**Hooks are in `matching.py` `match_volunteer()`:**
- After P3 (name match) returns the volunteer
- After new volunteer creation (P4 fallthrough creates a new record)

**Safety rules:**
- Never overwrites an existing email — only adds if the address is not already present
- Never overwrites an existing `pathful_user_id`
- All writes in the caller's transaction; no standalone `commit()`
- Idempotent — safe to run on every import

**Acceptance criteria:**
- [x] New service `services/pathful_id_backfill_service.py` created
- [x] Hook added at P3 return in `match_volunteer()`
- [x] Hook added at new-volunteer creation in `match_volunteer()`
- [ ] Test: P3 match + UserProfile present → email row added, next import hits P2
- [ ] Test: P3 match + no UserProfile → pathful_user_id set, function returns cleanly
- [ ] Test: two calls with same email → idempotent (no duplicate email rows)

---

#### C2 — Volunteer merge UI (side-by-side preview + audit log)

**Problem:** The current `confirm_near_match` action is a blind form POST. Admin sees
a summary but not the full picture of what will change.

**Enhanced UI should show:**
- Side-by-side table: duplicate record vs. canonical record (fields, org links, event counts)
- Exact list of `event_volunteers` rows that will be moved (session titles, dates)
- "Confirm Merge" button only after this preview is shown
- Full audit log entry written as JSON before transaction commits

**Implementation:** New `/virtual/pathful/unmatched/<id>/merge-preview` GET route +
template. The existing `confirm_near_match` POST becomes the confirm step after preview.

**Acceptance criteria:**
- [ ] Preview shows both records side-by-side before commit
- [ ] Preview shows exact sessions being moved
- [ ] Audit log entry written with full undo information (JSON)
- [ ] Merge is reversible by re-assigning the `event_volunteers` rows

---

## Execution Checklist

### Epic A (Do First — both are ~30 min each)

```
[ ] A1: Teacher cache collision detection (matching.py build_import_caches)
[ ] A1: Unit test: same normalized name → None in cache → no mis-attribution
[ ] A2: Event P2 session_id cross-check (match_or_create_event)
[ ] A2: Test: two rows same title+date different session_id → two events
[ ] A2: Test: re-import → no duplicate events
```

### Epic B (Next session)

```
[ ] B1: Email collision markers — volunteer_by_email (matching.py)
[ ] B1: Email collision markers — teacher_by_email (matching.py)
[ ] B1: Unit test: shared email → None → fallthrough to name match
[ ] B2: org_service.py T4 — return None instead of auto-alias
[ ] B2: Pass candidate org_id in _near_org_match_id via raw_data
[ ] B2: confirm_org_alias action in resolve_unmatched handler
[ ] B2: Test: T4 near-match → quarantine ticket created, no alias written
[ ] B2: Test: admin confirms → alias written, volunteer linked, siblings cascaded
[ ] B3: Write backfill_near_match_tickets.py (dry-run mode)
[ ] B3: Run dry-run, review count and audit JSON
[ ] B3: Approve and run --apply
[ ] B3: Verify tickets appear in quarantine queue with correct suggestions
```

### Epic C (Future sprint)

```
[x] C1: services/pathful_id_backfill_service.py created
[x] C1: Hook wired into match_volunteer() at P3 return and new-volunteer creation
[ ] C1: Test: P3 match + UserProfile present → email added, next import hits P2
[ ] C1: Test: no UserProfile → pathful_user_id set, clean return
[ ] C1: Test: idempotent — two calls, no duplicate email rows
[x] C2: GET /pathful/unmatched/<id>/merge-preview route added (pathful_merge_preview)
[x] C2: templates/virtual/pathful/merge_preview.html created
[x] C2: "Preview Merge" button added to unmatched.html for volunteer tickets with near_match candidates
[ ] C2: Test: preview shows correct sessions for both sides
[ ] C2: Test: Confirm Merge button fires existing confirm_near_match POST
[ ] C2: Test: Reject button fires existing reject_near_match POST
```

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| B2 increases admin workload if many new company strings per import | High workflow friction | Monitor ticket volume after first 3 imports; revert to Option A (review panel) if volume is unsustainable |
| B3 dry-run shows 1000+ duplicate pairs | Admin queue flooded | Release in batches of 50; add a `--limit N` flag to the script |
| A2 cross-check breaks a legitimate re-import | Duplicate events created | Ensure session_id is always present in Pathful exports before re-importing |
| C1 backfill assigns wrong pathful_user_id | Wrong person permanently linked via P1 | Only backfill on confirmed P3/P4 matches; log every backfill action |

---

## Related Documentation

- [Pathful Deployment Plan](deployment.md) — Phase history and Phase D (current)
- [Pathful Recommendations](recommendations.md) — Decision log (DEC-001 through DEC-010)
- [Tech Debt Tracker](../tech_debt.md) — Add items TD-0xx for each gap
- [AI Collab Guide](../ai_collab_guide.md) — Decision-making standards
- [Pipeline Audit](../../../../.gemini/antigravity/brain/929d9ac2-1af9-474f-b7a7-cf1eead3d383/pipeline_audit.md) — Full FP/FN analysis

---

*Created: 2026-03-31*
*Session: 929d9ac2 — Hardening Pathful Reconciliation Pipeline*
