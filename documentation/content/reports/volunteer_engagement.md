# Volunteer Engagement Reports

Engaging and recognizing volunteers is critical. These reports help identify top contributors and track service hours.

---

## Volunteer Thank You Report

**Location**: `Reports > Volunteer Thank You`

This report is designed for recognition programs (e.g., end-of-year thank yous).

### Features
- **Ranking**: Sort volunteers by Total Hours or Total Events
- **Filtering**: Filter by School Year (e.g., "24-25") or Host (e.g., "PrepKC" vs. "All")
- **Export**: Download as Excel for mail merge

### Calculation Details

| Metric | Calculation | Notes |
|--------|-------------|-------|
| **Total Hours** | Sum of `delivery_hours` for attended events | Excludes cancelled/no-show |
| **Total Events** | Count of attended events | Unique event count |
| **Organization** | Primary organization of volunteer | From volunteer profile |

---

## Workflow: Annual Recognition Program

1. **Set Date Range**: Select the fiscal/school year (e.g., July 1, 2024 - June 30, 2025)
2. **Sort by Hours**: Identify top 50 contributors
3. **Export to Excel**: Download for mail merge with recognition certificates
4. **Send Thank-You Emails**: Use exported list with your email template

> [!TIP]
> For large recognition programs, filter by "Local" volunteers first to focus on KC metro area contributors.

---

## Volunteer Detail View

Clicking a volunteer's name in reports opens their **Detail View**, showing:
- Chronological list of all attended events in the selected year
- Hours per event
- School/District breakdown

---

## Technical Scope & Traceability

| Component | Items |
|---|---|
| **User Stories** | [US-701](user_stories#us-701), [US-402](user_stories#us-402) |
| **Requirements** | [FR-REPORTING-401](requirements#fr-reporting-401), [FR-REPORTING-406](requirements#fr-reporting-406) |
| **Code** | `routes.reports.volunteer_thankyou.volunteer_thankyou` |

---

*Last updated: January 2026*
*Version: 1.1*
