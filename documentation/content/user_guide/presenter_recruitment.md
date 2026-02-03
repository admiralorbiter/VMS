# Presenter Recruitment

Specialized tool for internal staff to identify and fill presenter gaps in upcoming virtual sessions.

## Access

**URL**: `/virtual/usage/recruitment`

**Access Control:**
- ✅ Admin users (any scope)
- ✅ Regular users with global scope
- ❌ District-scoped users
- ❌ School-scoped users

---

## Features

### Event Display

- Shows only **virtual events** (EventType.VIRTUAL_SESSION)
- Filters to **future events only**
- Displays only events **without assigned presenters**
- Sorted by start date (earliest = highest priority)

### Filtering

| Filter | Description |
|--------|-------------|
| Academic Year | Virtual session year (Aug 1 - Jul 31 cycle) |
| Date Range | Custom start and end dates |
| District | Filter by school district |
| School | Filter by specific school |
| Search | Text search across event title and teacher names |

### Event Information

| Column | Description |
|--------|-------------|
| Event Title | Full title of the virtual session |
| Date & Time | Formatted date and time |
| School | School name or "N/A" |
| District | District name or "N/A" |
| Teachers | Number of teachers tagged (badge) |
| Days Until | Days remaining (color-coded urgency) |
| Actions | "Edit Event" button |

### Urgency Indicators

| Color | Timeframe | Meaning |
|-------|-----------|---------|
| 🔴 Red | ≤7 days | Urgent |
| 🟡 Yellow | 8-14 days | Warning |
| 🔵 Blue | >14 days | Normal |

---

## Workflow

### Typical Recruitment Workflow

1. **Access the Recruitment View** → `/virtual/usage/recruitment`
2. **Prioritize Events** → Focus on red badges (≤7 days)
3. **Find Volunteers** → Click "Find Volunteers" button
4. **Assign Presenter** → Click event row → Assign volunteer as presenter
5. **Verify** → Event disappears from list when presenter assigned

### Dynamic Behavior

- **Event appears**: No presenter participation records exist
- **Event disappears**: At least one presenter assigned
- **Event reappears**: Last presenter removed

---

## Navigation

### From Virtual Session Usage Report

1. Navigate to `/virtual/usage`
2. Click **"Presenter Recruitment"** button (yellow)
3. Access the recruitment view

### Action Buttons

| Button | Description |
|--------|-------------|
| Apply Filters | Apply selected filter criteria |
| Reset | Clear all filters |
| Find Volunteers | Navigate to volunteer search |
| Back to Usage Report | Return to main usage report |

---

## Query Logic

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

---

## Troubleshooting

### Events Not Appearing

1. Verify event type is `VIRTUAL_SESSION`
2. Confirm event start date is in the future
3. Check for any EventParticipation records with `participant_type='Presenter'`
4. Verify date filters include the event date range

### Events Not Disappearing

1. Verify EventParticipation was created with `participant_type='Presenter'`
2. Refresh the page
3. Check database for the participation record

### Access Denied

- Verify you are Admin OR have `scope_type='global'`
- District/school-scoped users cannot access this view

---

## Technical Details

### Key Files

| Category | Files |
|----------|-------|
| **Route** | `routes/virtual/usage.py` → `virtual_recruitment()` |
| **Template** | `templates/virtual/virtual_recruitment.html` |
| **Styles** | `css/reports.css`, `css/virtual_usage.css` |
| **Models** | `Event`, `EventParticipation`, `EventTeacher`, `School`, `District` |
