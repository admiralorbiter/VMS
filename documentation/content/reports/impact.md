# Impact & KPI Reports

These reports provide high-level metrics for grant reporting and district feedback.

---

## District Impact Report

**Location**: `Reports > District Impact`

Shows the value provided to specific school districts.

### Key Metrics

| Metric | Calculation | Source |
|--------|-------------|--------|
| **Unique Students Reached** | Count of distinct students with `attended=True` | Event attendance rosters |
| **Unique Volunteers** | Count of distinct volunteer IDs per district | EventParticipation records |
| **Total Volunteer Hours** | Sum of event duration × volunteers | Event.duration × participant count |
| **Unique Organizations** | Count of distinct org names from volunteers | Volunteer.organization |
| **Schools Served** | Count of distinct schools with events | Event.school |

### Filters Available
- **Date Range**: Filter by event dates
- **District**: Single or multiple districts
- **Event Type**: In-person, Virtual, or All

---

## Organization Participation

**Location**: `Reports > Organization Participation`

Shows engagement levels of partner companies.

### Features
- **Ranking**: Sort by most active organizations (hours or event count)
- **Drill-down**: Click an organization to see its individual volunteers
- **Export**: Download organization summary as CSV

### Metrics Per Organization
- Total Hours Contributed
- Number of Events Attended
- Number of Unique Volunteers
- Most Recent Activity Date

---

## Tips for Grant Reporting

> [!TIP]
> For annual grant reports, set the date range to your fiscal year and export the District Impact report. Include the "Unique Students Reached" and "Unique Organizations" metrics.

---

## Technical Scope & Traceability

| Component | Items |
|---|---|
| **User Stories** | [US-702](user_stories#us-702), [US-703](user_stories#us-703) |
| **Requirements** | [FR-REPORTING-402](requirements#fr-reporting-402), [FR-REPORTING-403](requirements#fr-reporting-403) |
| **Code** | `routes.reports.organization_report` |

---

*Last updated: January 2026*
*Version: 1.1*
