# District Self-Service Guide

**User guide for District Administrators and Coordinators**

> [!NOTE]
> This guide covers the District Suite self-service features for managing events and volunteers within your district's isolated Polaris environment.

## Getting Started

### Logging In

1. Navigate to your district's Polaris URL (provided by PrepKC)
2. Enter your email and password
3. Click **Sign In**

If you forgot your password, click **Forgot Password** and enter your email to receive a reset link.

### User Roles

| Role | Description | Access |
|------|-------------|--------|
| **District Admin** | Full access to all district features | Events, volunteers, settings, users |
| **District Coordinator** | Day-to-day event and volunteer management | Events, volunteers |
| **District Viewer** | Read-only access to dashboards | View only |

---

## Event Management

### Creating an Event

1. Navigate to **Events** → **Create Event**
2. Fill in required fields:
   - **Title** - Descriptive event name
   - **Date** - Event date
   - **Start/End Time** - Event hours
   - **Location** - Full address
   - **Description** - Event details
   - **Volunteers Needed** - Number of volunteers required
3. Click **Save as Draft** or **Publish**

### Event Status Workflow

| Status | Description |
|--------|-------------|
| **Draft** | Not visible to public; still editing |
| **Published** | Visible on public API; accepting signups |
| **Completed** | Event has occurred; no more signups |
| **Cancelled** | Event cancelled; volunteers notified |

### Editing Events

1. Navigate to **Events** → **All Events**
2. Click on event title or **Edit** button
3. Make changes and click **Save**

> [!TIP]
> You can edit events until they are marked as Completed.

### Cancelling Events

1. Navigate to **Events** → **All Events**
2. Click on event and select **Cancel Event**
3. Optionally enter a cancellation reason
4. Confirm cancellation

All signed-up volunteers will receive a cancellation email.

---

## Calendar View

### Viewing the Calendar

1. Navigate to **Events** → **Calendar**
2. Use navigation buttons to change month/week/day
3. Click on an event to view details

### Event Colors

- **Blue** - Your district's events
- **Gray** - PrepKC events at your schools (read-only)
- **Red** - Events needing volunteers

---

## Volunteer Management

### Adding a Volunteer

1. Navigate to **Volunteers** → **Add New**
2. Fill in required fields:
   - First Name, Last Name
   - Email
   - Organization
3. Add optional fields: skills, career type, phone
4. Click **Save**

### Importing Volunteers

1. Navigate to **Volunteers** → **Import**
2. Download the template CSV
3. Fill in volunteer data
4. Upload the file
5. Map columns to fields (if needed)
6. Review any validation errors
7. Click **Import**

### Searching Volunteers

1. Navigate to **Volunteers** → **Search**
2. Use filters:
   - **Name** - First or last name
   - **Organization** - Company or org name
   - **Skills** - Filter by skill tags
   - **Career Type** - Industry/profession
3. Results update automatically

---

## Assigning Volunteers to Events

### From Event Detail Page

1. Open an event
2. Scroll to **Volunteers** section
3. Click **Add Volunteer**
4. Search for volunteer by name
5. Select and confirm

### From Volunteer Profile

1. Open a volunteer profile
2. Click **Assign to Event**
3. Select event from list
4. Confirm assignment

---

## Recruitment Dashboard

### Accessing the Dashboard

1. Navigate to **Events** → **Recruitment**
2. See events needing volunteers, sorted by urgency

### Urgency Indicators

| Badge | Meaning |
|-------|---------|
| 🔴 Red | Event in ≤7 days |
| 🟡 Yellow | Event in 8-14 days |
| 🔵 Blue | Event in >14 days |

### Logging Outreach

1. Click on a volunteer from recommendations
2. Click **Log Outreach**
3. Select outcome:
   - No Response
   - Interested
   - Declined
   - Confirmed
4. Add notes if needed
5. Save

---

## Settings (Admin Only)

### API Settings

1. Navigate to **Settings** → **API**
2. Copy your API key for website integration
3. Add allowed origins (your website URLs)
4. Click **Rotate Key** if you need a new key

### User Management

1. Navigate to **Settings** → **Users**
2. Click **Add User** to invite new staff
3. Select role (Admin, Coordinator, Viewer)
4. User receives email invitation

---

## Related Documentation

- **API Reference:** [Public Event API](api_reference)
- **Development Phases:** [District Suite Phases](district_suite_phases)
- **Requirements:** [District Self-Service](requirements#district-self-service)

---

*Last updated: January 2026*
*Version: 1.0*
