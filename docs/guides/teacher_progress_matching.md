# Teacher Progress Matching System

## Overview

The Teacher Progress Matching System links imported `TeacherProgress` entries (from Google Sheets) to actual `Teacher` records in the database. This enables the teacher detail view to work correctly when clicking on teachers in the progress tracking interface.

## How Matching Works

### Automatic Matching

The system uses a two-tier matching strategy:

#### 1. Email Matching (Primary Method)
- **How it works**: Compares the `TeacherProgress.email` field to each `Teacher` record's primary email address
- **Match type**: Exact match (case-insensitive)
- **Priority**: Highest - if an email match is found, name matching is skipped
- **Example**:
  - TeacherProgress: `tiffany.pattison@kckps.org`
  - Teacher primary email: `tiffany.pattison@kckps.org`
  - Result: ✅ Match

#### 2. Name Matching (Secondary Method)
- **How it works**: Uses fuzzy string matching to compare `TeacherProgress.name` to `Teacher.first_name + Teacher.last_name`
- **Match type**: Similarity-based (85%+ similarity threshold)
- **Priority**: Only used if email matching fails
- **Normalization**: Names are normalized before comparison:
  - Converted to lowercase
  - Punctuation removed (`.`, `,`, `-`, `(`, `)`, `'`, `"`)
  - Multiple spaces collapsed to single space
- **Example**:
  - TeacherProgress: `"John A. Smith"`
  - Teacher: `"John Smith"` (first_name: "John", last_name: "Smith")
  - Normalized: `"john a smith"` vs `"john smith"`
  - Similarity: ~85% → ✅ Match

### Manual Matching

Admins can manually match or unmatch teachers through the admin interface:
- **Location**: `/virtual/usage/district/Kansas City Kansas Public Schools/teacher-progress/matching`
- **Features**:
  - View all TeacherProgress entries with match status
  - Filter by unmatched only
  - Search by name, email, or building
  - Select teacher from dropdown and match
  - Unmatch existing matches
  - Run automatic matching for a virtual year

## Usage

### Running Automatic Matching

#### Via Admin Interface
1. Navigate to: `/virtual/usage/district/Kansas City Kansas Public Schools/teacher-progress/matching`
2. Select the virtual year
3. Click "Run Auto-Match" button
4. Review results in the statistics dashboard

#### Via Command Line
```bash
python scripts/utilities/match_teacher_progress.py [virtual_year]
```

Example:
```bash
python scripts/utilities/match_teacher_progress.py 2025-2026
```

### Manual Matching Process

1. **Access Matching Interface**:
   - Go to Google Sheets management page
   - Click "Match Teachers" button
   - Or navigate directly to the matching URL

2. **Find Unmatched Teachers**:
   - Use "Show unmatched only" filter
   - Or search by name/email

3. **Match a Teacher**:
   - Select teacher from dropdown
   - Click "Match" button
   - Teacher will be linked and status updated

4. **Unmatch a Teacher**:
   - Click "Unmatch" button next to matched teacher
   - Confirmation dialog will appear
   - Match will be removed

## Technical Details

### Database Schema

The `teacher_progress` table includes:
- `teacher_id` (Integer, nullable): Foreign key to `teacher.id`
- Relationship: `TeacherProgress.teacher` → `Teacher` model

### Matching Function

**Location**: `routes/virtual/usage.py`

**Function**: `match_teacher_progress_to_teachers(virtual_year=None, min_similarity=0.85)`

**Parameters**:
- `virtual_year`: Filter matching to specific virtual year (None = all years)
- `min_similarity`: Minimum similarity ratio for name matching (default: 0.85)

**Returns**: Dictionary with statistics:
```python
{
    "total_processed": 462,
    "matched_by_email": 326,
    "matched_by_name": 135,
    "unmatched": 1,
    "errors": []
}
```

### Name Similarity Algorithm

Uses Python's `difflib.SequenceMatcher`:
- Compares normalized name strings
- Returns similarity ratio (0.0 to 1.0)
- Only matches if similarity >= threshold (default: 0.85)

### Progress Tracking Integration

The `compute_teacher_progress_tracking()` function includes `matched_teacher_id` in the response:
- If matched: `matched_teacher_id` contains the Teacher ID
- If unmatched: `matched_teacher_id` is `None`
- Template uses this to show/hide warning icons and enable/disable links

## Visual Indicators

### Matched Teachers
- ✅ Clickable link to teacher detail page
- No warning icon
- Green link color

### Unmatched Teachers
- ⚠️ Warning icon (yellow triangle) next to name
- Grayed out name (not clickable)
- Tooltip: "Teacher not matched to database record"

## Best Practices

1. **Run Auto-Match After Import**: Always run automatic matching after importing new teacher data from Google Sheets

2. **Review Unmatched Teachers**: Check unmatched teachers regularly - they may need manual matching if:
   - Email addresses don't match exactly
   - Names have significant variations
   - Teacher records don't exist in database yet

3. **Verify Matches**: After auto-matching, review a sample of matches to ensure accuracy

4. **Handle Edge Cases**:
   - Teachers with multiple email addresses
   - Name variations (middle names, nicknames)
   - Teachers who changed names

## Troubleshooting

### No Teachers Matched
- **Check**: Are there Teacher records in the database?
- **Check**: Do Teacher records have primary emails set?
- **Check**: Are email addresses in TeacherProgress entries valid?

### Low Match Rate
- **Solution**: Lower the similarity threshold (not recommended - may cause false matches)
- **Solution**: Review name formats in both systems
- **Solution**: Use manual matching for difficult cases

### False Matches
- **Solution**: Review matches manually
- **Solution**: Unmatch incorrect matches
- **Solution**: Adjust matching logic if needed

## Related Features

- **Teacher Progress Tracking**: Main feature that uses matched teachers
- **Google Sheets Import**: Source of TeacherProgress data
- **Teacher Detail View**: Destination when clicking matched teachers

## Access Control

- **Matching Interface**: Admin only (`@admin_required`)
- **Auto-Match Endpoint**: Admin only
- **Manual Match/Unmatch**: Admin only
- **Progress View**: District-scoped users can view but not modify matches
