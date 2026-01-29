# Ad Hoc Queries

**Location**: `Reports > Ad Hoc`

The Ad Hoc Query builder allows staff to answer one-off questions that don't fit a standard dashboard.

---

## Step-by-Step Guide

### 1. Access the Query Builder
Navigate to **Reports > Ad Hoc** from the main menu.

### 2. Build Your Query
1. **Select Entity**: Choose what you're querying (Volunteers, Events, Participations, Organizations)
2. **Add Filters**: Click "Add Filter" to narrow results
3. **Choose Fields**: Select which columns to display in results
4. **Run Query**: Click "Execute" to see results

### 3. Export Results
- Click **Export CSV** to download for Excel analysis
- Results include all visible columns with current filters applied

---

## Available Filters

| Filter | Description | Example |
|--------|-------------|---------|
| **Date Range** | Events or activity within dates | Jan 1 - Mar 31, 2025 |
| **Organization** | Filter by company/org name | "IBM", "Cerner" |
| **Skills** | Volunteer skills/expertise | "Engineering", "Finance" |
| **Event Type** | In-person, Virtual, DIA | "Virtual" |
| **District** | School district | "Kansas City, KS" |
| **Activity Status** | Active volunteers only | Last active within 1 year |

---

## Common Use Cases

| Question | Query Approach |
|----------|----------------|
| "List all engineers from IBM" | Entity: Volunteers, Filter: Org = IBM, Skills contains "Engineer" |
| "Events at Wyandotte High last month" | Entity: Events, Filter: School = Wyandotte, Date = Last 30 days |
| "Volunteers inactive since 2023" | Entity: Volunteers, Filter: Last Activity < Jan 1, 2024 |
| "All virtual sessions needing presenters" | Entity: Events, Filter: Type = Virtual, Presenter = Empty |

---

## Tips

> [!TIP]
> **Save frequently-used queries** by bookmarking the URL after running - filter state is preserved in the URL.

> [!NOTE]
> Complex queries with many filters may take longer to execute. For very large exports, consider narrowing date ranges.

---

## Technical Scope & Traceability

| Component | Items |
|---|---|
| **User Stories** | [US-704](user_stories#us-704) |
| **Requirements** | [FR-REPORTING-405](requirements#fr-reporting-405) |

---

*Last updated: January 2026*
*Version: 1.1*
