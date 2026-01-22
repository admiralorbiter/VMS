# Partner Reconciliation (KCTAA Special)

**Location**: `Reports > KCTAA Special` (or similar partner routes)

This tool solves the problem of cross-referencing an external list of members (e.g., from a partner organization's CSV) with the VMS database to see which members are active volunteers.

## How It Works

1.  **Input**: The system reads a CSV file (default: `data/kctaa_first_last_names.csv`) containing `First Name` and `Last Name`.
2.  **Matching**: It attempts to match each name against the `Volunteer` database table.
3.  **Output**: A list showing Match Status, Volunteer Stats (Hours/Events), and confidence score.

## Matching Logic

### 1. Exact Match
-   **Criteria**: Case-insensitive match of First Name + Last Name.
-   **Confidence**: 100%.

### 2. Fuzzy Match
-   **Criteria**: Uses `difflib.SequenceMatcher` to compare normalized strings.
-   **Threshold**: Matches with similarity ≥ 90% (configurable).
-   **Example**: "Rob Smith" might match "Robert Smith".

## Usage

1.  Navigate to the report page.
2.  Adjust **Minimum Match Score** filter if needed (default 0.9).
3.  Toggle **"Include Unmatched"** to see people from the CSV who were *not* found in the VMS.
4.  **Export CSV** to get the full reconciled list.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-705](user_stories#us-705) |
| **Requirements** | [FR-REPORTING-407](requirements#fr-reporting-407), [FR-REPORTING-408](requirements#fr-reporting-408) |
| **Code** | `routes.reports.kctaa_special.kctaa_report` |
