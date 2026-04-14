# Teacher Progress Matching

Links imported `TeacherProgress` entries (from Google Sheets/Pathful) to actual `Teacher` records in the database.

## Overview

The matching system enables the teacher detail view to work correctly when clicking on teachers in the progress tracking interface. All matching is centralized in `services/teacher_matching_service.py`.

---

## How Matching Works

### Centralized Identity Resolution

All teacher matching flows through two canonical functions in `teacher_matching_service.py`:

#### `resolve_teacher_for_tp(tp)` — Link TP → Teacher

Priority chain:
1. **Email match** — `tp.email` → `Teacher.cached_email` (case-insensitive)
2. **Profile bridge** — `tp.pathful_user_id` → `PathfulUserProfile` → `Teacher` (via stored email or linked teacher_id)
3. **Normalized name match** — full name normalization (lowercase, punctuation removed)
4. **First+last name match** — ignores middle names (e.g., "Sarah Jean Williams" → matches "Sarah Williams")
5. **Create new Teacher** — if no match found, creates a new `Teacher` record with `cached_email` populated

#### `match_tp_to_profile(tp)` — Link TP → PathfulUserProfile

Priority chain:
1. **pathful_user_id** — exact FK match
2. **Email match** — `tp.email` → `PathfulUserProfile.email`
3. **Normalized name match** — handles variations

> [!NOTE]
> Name normalization (`normalize_name()`) strips punctuation, lowercases, and removes extra whitespace. The first+last name fallback handles middle names, hyphenated names, and maiden/married name differences.

---

## Automatic Matching

### On Import

Matching runs automatically during:
- **Roster import** — `_link_progress_to_teachers()` in `roster_import.py` uses email-first + normalized name matching
- **Pathful session import** — `_reverse_link_teacher_progress()` resolves TP links for each session
- **Pathful user report** — `match_tp_to_profile()` links TPs to user profiles

### Backfill

The dashboard route runs `_backfill_teacher_ids()` on each page load, catching any TPs that still have `teacher_id = NULL`. This delegates to `resolve_teacher_for_tp()`.

---

## Dashboard Session Counting

### Counting Strategy

Session counts use a two-tier approach (in `compute_teacher_progress()`):

1. **EventTeacher path (primary):** Count FK-linked events where `EventTeacher.status IN ('attended', 'completed')` — does **not** filter by `Event.district_partner` (the FK link itself proves attendance; see TD-032)
2. **Text path (supplementary):** Match teacher names in `Event.educators` for events NOT linked via EventTeacher — **does** filter by `district_partner` since there's no FK to prove attendance

### Deduplication

Two sets prevent double-counting:
- `all_et_event_ids` — all EventTeacher-linked events (any status, including no_show) — used to exclude from text-matching
- `counted_events_per_tp` — (tp_id, event_id) pairs actually counted — used for override logic

### Attendance Overrides

Both ADD and REMOVE overrides are **event-aware**:
- **ADD:** Only increments if the event was NOT already counted via EventTeacher
- **REMOVE:** Only decrements if the event WAS counted
- **Stale ADDs:** If an ADD override's event is already counted via import data, the override is auto-resolved and logged

---

## Visual Indicators

| Status | Indicator |
|--------|-----------|
| Matched | ✅ Clickable link (green) |
| Unmatched | ⚠️ Warning icon, grayed name, tooltip |

---

## Key Files

| Category | Files |
|----------|-------|
| **Matching Service** | `services/teacher_matching_service.py` |
| **Teacher Service** | `services/teacher_service.py` |
| **Dashboard Route** | `routes/district/tenant_teacher_usage.py` |
| **Import Processing** | `routes/virtual/pathful_import/processing.py` |
| **Models** | `models/teacher_progress.py`, `models/teacher.py`, `models/attendance_override.py` |

---

## Troubleshooting

### No Teachers Matched

- Check: Are there Teacher records in the database?
- Check: Do Teacher records have `cached_email` populated?
- Check: Are email addresses in TeacherProgress valid?

### Low Match Rate

- Review name formats in both systems
- Check for middle names or hyphenated names causing mismatches
- Run the reconciliation script: `scripts/reconcile_teacher_links.py`

### False Matches

- Review matches manually
- Report patterns for logic adjustment

---

## Access Control

| Action | Access |
|--------|--------|
| Dashboard View | Admin + district-scoped users |
| Attendance Overrides | Virtual admins (tenant-scoped) |
| Progress View (read) | District-scoped users |

---

*Last updated: March 2026*
