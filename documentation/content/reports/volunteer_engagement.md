# Volunteer Engagement Reports

Engaging and recognizing volunteers is critical. These reports help identify top contributors and track service hours.

## Volunteer Thank You Report

**Location**: `Reports > Volunteer Thank You`

This report is designed for recognition programs (e.g., end-of-year thank yous).

### Features
-   **Ranking**: Sort volunteers by Total Hours or Total Events.
-   **Filtering**: Filter by School Year (e.g., "24-25") or Host (e.g., "PrepKC" vs. "All").
-   **Export**: Download as Excel for mail merge.

### Calculations
-   **Total Hours**: Sum of `delivery_hours` for all attended/completed events.
-   **Total Events**: Count of attended/completed events.
-   **Organization**: Displays the primary organization of the volunteer.

## Volunteer Detail View

Clicking a volunteer's name in reports opens their **Detail View**, showing:
-   Chronological list of all attended events in the selected year.
-   Hours per event.
-   School/District breakdown.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-701](user_stories#us-701), [US-402](user_stories#us-402) |
| **Requirements** | [FR-REPORTING-401](requirements#fr-reporting-401), [FR-REPORTING-406](requirements#fr-reporting-406) |
| **Code** | `routes.reports.volunteer_thankyou.volunteer_thankyou` |
