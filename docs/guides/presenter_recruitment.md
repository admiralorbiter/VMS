# Virtual Sessions Presenter Recruitment View

## Overview

The Presenter Recruitment View is a specialized tool for internal staff (Admin and global-scoped users) to proactively identify and fill presenter gaps in upcoming virtual sessions.

## Access

**URL**: `http://localhost:5050/virtual/usage/recruitment`

**Access Control**:
- ✅ **Allowed**: Admin users (any scope), Regular users with global scope
- ❌ **Denied**: District-scoped users, School-scoped users

Users without proper access will receive an error message and be redirected to the Virtual Session Usage Report.

## Features

### 1. Event Display
- Shows only **virtual events** (EventType.VIRTUAL_SESSION)
- Filters to **future events only** (start_date > current date/time)
- Displays only events **without assigned presenters**
- Events are sorted by start date (earliest first = highest priority)

### 2. Filtering Capabilities

The view supports comprehensive filtering:

- **Academic Year**: Select virtual session year (Aug 1 - Jul 31 cycle)
- **Date Range**: Custom start and end dates within selected year
- **District**: Filter by school district
- **School**: Filter by specific school
- **Search**: Text search across event title and teacher names
- **Multiple Filters**: All filters work together (intersection logic)

### 3. Event Information Display

For each event, the following information is displayed:

| Column | Description |
|--------|-------------|
| Event Title | Full title of the virtual session |
| Date & Time | Formatted date and time (e.g., "Jan 25, 2026 02:00 PM") |
| School | School name or "N/A" if not assigned |
| District | District name or "N/A" if not assigned |
| Teachers | Number of teachers tagged to the event (badge display) |
| Days Until | Days remaining until event (color-coded urgency) |
| Actions | "Edit Event" button to navigate to event details |

### 4. Urgency Indicators

Days until event are color-coded for quick prioritization:

- 🔴 **Red (≤7 days)**: Urgent - event happening within a week
- 🟡 **Yellow (8-14 days)**: Warning - event happening in 1-2 weeks
- 🔵 **Blue (>14 days)**: Normal - event scheduled further out

### 5. Action Buttons

**Top Action Bar**:
- **Apply Filters**: Apply selected filter criteria
- **Reset**: Clear all filters and return to defaults
- **Find Volunteers**: Navigate to volunteer search/recruitment page
- **Back to Usage Report**: Return to main virtual sessions usage report

**Per-Event Actions**:
- **Edit Event**: Opens event details page where presenters can be assigned
- **Click Row**: Clicking anywhere on the event row (except buttons) also navigates to event details

### 6. Dynamic Behavior

The view automatically updates based on presenter assignments:

- **Event appears** when: No EventParticipation records with `participant_type='Presenter'` exist for the event
- **Event disappears** when: At least one presenter is assigned (EventParticipation with `participant_type='Presenter'` created)
- **Event reappears** when: Last presenter is removed from the event

No special refresh is needed - standard page reload shows current status.

## Navigation

### From Virtual Session Usage Report
1. Navigate to `/virtual/usage`
2. Look for the **"Presenter Recruitment"** button (yellow/warning color) in the action buttons area
3. Click to access the recruitment view

### From Recruitment View
- Click **"Back to Usage Report"** to return to the main usage report
- Click **"Find Volunteers"** to search for available volunteers
- Click any event row or **"Edit Event"** button to manage that specific event

## Workflow

### Typical Recruitment Workflow

1. **Access the Recruitment View**
   - Navigate to `/virtual/usage/recruitment`
   - Review list of events needing presenters

2. **Prioritize Events**
   - Sort by "Days Until" to focus on urgent events (red badges)
   - Filter by district or school if needed
   - Use search to find specific events or teachers

3. **Find Suitable Volunteers**
   - Click **"Find Volunteers"** to access volunteer search
   - Search by skills, availability, location, etc.
   - Identify potential presenters

4. **Assign Presenter**
   - Click event row or **"Edit Event"** button
   - On event details page, assign volunteer as presenter
   - Set `participant_type='Presenter'` in EventParticipation record

5. **Verify Assignment**
   - Return to recruitment view
   - Confirm event no longer appears in the list
   - Event has been successfully filled

## Query Logic

The view uses the following SQL logic (via SQLAlchemy):

```sql
SELECT events
WHERE event_type = 'Virtual'
  AND start_datetime > NOW()
  AND NOT EXISTS (
    SELECT 1 FROM participation
    WHERE participation_type = 'Presenter'
      AND event_id = events.event_id
  )
ORDER BY start_date ASC
```

This ensures:
- Only virtual events are shown
- Only future events are included
- Events with any presenter assignment are excluded
- Results are ordered by urgency (earliest first)

## Empty State

When no events need presenters, the view displays:

> ✅ **Great news!**
>
> All upcoming virtual sessions have presenters assigned.

With a link back to the Virtual Session Usage Report.

## Technical Details

### Route Handler
- **File**: `routes/virtual/usage.py`
- **Function**: `virtual_recruitment()`
- **Decorators**: `@login_required`, custom access control check

### Template
- **File**: `templates/virtual/virtual_recruitment.html`
- **Extends**: `base.html`
- **Styles**: Reuses `css/reports.css` and `css/virtual_usage.css`

### Data Models
- **Event**: Main event data
- **EventParticipation**: Tracks volunteer-event relationships including presenters
- **EventTeacher**: Tracks teacher-event associations
- **School**: School information and district relationships
- **District**: District information

### Access Control Implementation
```python
if not (current_user.is_admin or current_user.scope_type == 'global'):
    flash("Access denied. This feature is only available to administrators and global users.", "error")
    return redirect(url_for('virtual_bp.virtual_usage'))
```

## Support and Troubleshooting

### Events Not Appearing

If an event should appear but doesn't:
1. Verify event type is `VIRTUAL_SESSION`
2. Confirm event start date is in the future
3. Check for any EventParticipation records with `participant_type='Presenter'`
4. Verify date filters include the event date range

### Events Not Disappearing

If an event still appears after assigning presenter:
1. Verify EventParticipation record was created with `participant_type='Presenter'`
2. Refresh the page to see updated results
3. Check database for the participation record

### Access Denied

If you receive "Access denied" message:
- Verify you are an Admin user OR a regular user with `scope_type='global'`
- District-scoped and school-scoped users cannot access this view
- Contact system administrator to update your account scope if needed

## Future Enhancements

Potential improvements for future versions:
- Real-time updates via AJAX (auto-refresh without page reload)
- Bulk presenter assignment workflow
- Email notifications for urgent events (< 7 days)
- Presenter availability integration
- Historical metrics on fill rates and timing
- Export functionality for recruitment tracking
