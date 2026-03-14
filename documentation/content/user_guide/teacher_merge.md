# Teacher Merge Tool

> **Audience:** PrepKC Admin users only (`@admin_required`)

## Overview

The Teacher Merge Tool allows admins to identify and merge duplicate teacher records that arise from name mismatches across data sources (e.g., maiden vs. married names, name casing differences between Pathful and roster imports).

**Access:** Admin Dashboard → **Merge Teachers**, or directly at `/teachers/merge`

## When to Use

Use the merge tool when:

-   A teacher appears twice on event pages under different names (e.g., "Caitlin Atkinson" from Pathful and "Caitlin Borel" from the roster)
-   The same teacher has separate session counts that should be combined
-   Pathful imports create records with a different last name than the school roster (common with maiden/married names, hyphenation, or name changes)

> [!NOTE]
> **Exact-name duplicates** (same first + last, different casing) are handled automatically by the `merge_duplicate_teachers.py` script. The merge UI is for **different-name** pairs that require human judgment.

## Workflow

### Step 1: Review Flagged Candidates

On page load, the tool automatically scans for suspected duplicates and displays them as clickable cards. These are teacher pairs that meet **all** of:

-   Same normalized first name
-   Different last name
-   90%+ shared event overlap
-   No conflicting schools (if both have schools, they must match)

Cards are ranked by shared event count. Click a card to load both teachers into the comparison view.

### Step 2: Compare Side-by-Side

The comparison view shows:

| Field | Description |
|---|---|
| **Name & ID** | Full name and database ID for both teachers |
| **School** | Associated school (if any) |
| **Events** | Total EventTeacher count |
| **TP links** | TeacherProgress records linked to this teacher |
| **Shared events table** | Per-event status comparison with "After Merge" preview |

The left slot is **KEEP** (blue) and the right slot is **MERGE** (orange). Use the **Swap** button if needed.

### Step 3: Merge

Click **Merge Right Into Left** and confirm. The tool will:

1. **Move EventTeachers** — unique events from the duplicate are reassigned to the canonical teacher
2. **Dedup shared events** — for events where both appear, the higher-priority status wins:
    - `attended` (highest) > `no_show` > `registered` (lowest)
3. **Move TeacherProgress** and **Student** records
4. **Deactivate duplicate** — marked `active=False` with `import_source` tagged `merged_into_<ID>`

A success toast confirms the merge with a summary of what moved.

### Step 4: Manual Search

If a pair isn't in the flagged list, use the **Search Teachers** box to find any teacher by name, load them into the slots, and merge.

## Audit Trail

Every merge creates a JSON log file in `data/td035_name_merge_2026_03_13/` with:

-   Canonical and duplicate teacher names/IDs
-   Who performed the merge and when
-   EventTeachers moved, deduped, and status upgrades applied
-   TeacherProgress and Student records reassigned

These logs are the undo reference if something needs to be reversed.

## Remaining Candidates (as of March 2026)

Approximately 11 flagged candidates still need staff review. High-confidence pairs include teachers with 8–24 shared events and matching or unknown schools. Review each pair in the merge UI and decide:

-   **Same person?** → Merge (keep the one with the school/TP link)
-   **Different people?** → Skip (they'll stay in the flagged list but won't cause data issues)

## Technical Reference

| Component | Location |
|---|---|
| **Routes** | `routes/teachers/routes.py` — 5 endpoints: page, search, candidates, compare, execute |
| **Template** | `templates/teachers/merge.html` |
| **Access** | `@login_required` + `@global_users_only` + `@admin_required` |
| **Related TD** | [TD-036](../developer/tech_debt#td-036-exact-name-duplicate-teacher-records-2100-pairs) |

---

*Last updated: March 2026*
