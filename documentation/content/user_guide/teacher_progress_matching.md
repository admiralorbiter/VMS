# Teacher Progress Matching

Links imported `TeacherProgress` entries (from Google Sheets/Pathful) to actual `Teacher` records in the database.

## Overview

The matching system enables the teacher detail view to work correctly when clicking on teachers in the progress tracking interface.

---

## How Matching Works

### Two-Tier Matching Strategy

#### 1. Email Matching (Primary)

- Compares `TeacherProgress.email` to `Teacher` primary email
- Exact match (case-insensitive)
- **Priority**: Highest — if email match found, name matching skipped

**Example:**
- TeacherProgress: `tiffany.pattison@kckps.org`
- Teacher primary email: `tiffany.pattison@kckps.org`
- Result: ✅ Match

#### 2. Name Matching (Secondary)

- Uses fuzzy string matching (85%+ similarity threshold)
- Only used if email matching fails
- Names normalized before comparison (lowercase, punctuation removed)

**Example:**
- TeacherProgress: `"John A. Smith"`
- Teacher: `"John Smith"`
- Normalized: `"john a smith"` vs `"john smith"`
- Similarity: ~85% → ✅ Match

---

## Usage

### Running Automatic Matching

#### Via Admin Interface

1. Navigate to: `/virtual/usage/district/<district>/teacher-progress/matching`
2. Select the virtual year
3. Click **"Run Auto-Match"** button
4. Review results in statistics dashboard

#### Via Command Line

```bash
python scripts/utilities/match_teacher_progress.py [virtual_year]
```

Example:
```bash
python scripts/utilities/match_teacher_progress.py 2025-2026
```

### Manual Matching

**Location**: `/virtual/usage/district/<district>/teacher-progress/matching`

**Features:**
- View all TeacherProgress entries with match status
- Filter by unmatched only
- Search by name, email, or building
- Select teacher from dropdown and match
- Unmatch existing matches

---

## Visual Indicators

| Status | Indicator |
|--------|-----------|
| Matched | ✅ Clickable link (green) |
| Unmatched | ⚠️ Warning icon, grayed name, tooltip |

---

## Matching Function

**Location**: `routes/virtual/usage.py`

**Function**: `match_teacher_progress_to_teachers(virtual_year=None, min_similarity=0.85)`

**Returns:**
```python
{
    "total_processed": 462,
    "matched_by_email": 326,
    "matched_by_name": 135,
    "unmatched": 1,
    "errors": []
}
```

---

## Best Practices

1. **Run Auto-Match After Import** — Always run after importing new teacher data
2. **Review Unmatched Teachers** — Check regularly for manual matching needs
3. **Verify Matches** — Sample check a few matches for accuracy
4. **Handle Edge Cases:**
   - Teachers with multiple email addresses
   - Name variations (middle names, nicknames)
   - Teachers who changed names

---

## Troubleshooting

### No Teachers Matched

- Check: Are there Teacher records in the database?
- Check: Do Teacher records have primary emails set?
- Check: Are email addresses in TeacherProgress valid?

### Low Match Rate

- Review name formats in both systems
- Use manual matching for difficult cases
- Consider adjusting similarity threshold (with caution)

### False Matches

- Review matches manually
- Unmatch incorrect matches
- Report patterns for logic adjustment

---

## Access Control

| Action | Access |
|--------|--------|
| Matching Interface | Admin only |
| Auto-Match Endpoint | Admin only |
| Manual Match/Unmatch | Admin only |
| Progress View (read) | District-scoped users |

---

## Technical Details

### Database Schema

The `teacher_progress` table includes:
- `teacher_id` (Integer, nullable): Foreign key to `teacher.id`
- Relationship: `TeacherProgress.teacher` → `Teacher` model

### Key Files

| Category | Files |
|----------|-------|
| **Route** | `routes/virtual/usage.py` |
| **Models** | `models/teacher_progress.py`, `models/teacher.py` |
| **Script** | `scripts/utilities/match_teacher_progress.py` |
