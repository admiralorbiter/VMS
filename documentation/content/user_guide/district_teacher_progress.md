# District & Teacher Progress

This guide explains how district users and teachers access the VMS to track progress, and how administrators manage that access.

## Overview

The VMS provides specialized views for:
-   **District Viewers**: Access to dashboard for specific districts.
-   **Teachers**: Access to their own session history via "Magic Links".

## 1. District Dashboard Access

### User Scoping
Users can be scoped to specific districts.
-   **Global Scope**: Can see all districts (Admins/Staff).
-   **District Scope**: Can only see assigned districts.

### Logging In
1.  Navigate to the designated District Portal URL.
2.  District-scoped users are automatically redirected to their district's dashboard.
3.  The dashboard shows:
    -   **Teacher Progress**: List of teachers and their completion status.
    -   **Issues**: Flagged data issues.

## 2. Teacher Progress Tracking

### Status Definitions
-   **Achieved**: Completed ≥ 1 virtual session.
-   **In Progress**: Has ≥ 1 future signup but 0 completed.
-   **Not Started**: No signups and no completed sessions.

### Roster Import & Matching
Teacher data is imported from district rosters via Google Sheets. This process ensures the "Teacher Progress" list matches the actual district staff.

#### 1. Preparing the Google Sheet
Create a Google Sheet with the following columns (headers are recommended but not strictly required if order matches, but best practice is to follow standard format):
-   **Building** (School Name)
-   **Name** (Teacher Name)
-   **Email** (District Email)
-   **Grade** (Optional)

*Note: Ensure the sheet is accessible to the system service account or publicly viewable (depending on configuration).*

#### 2. Importing the Roster
1.  Navigate to the District Dashboard.
2.  Click **"Manage Google Sheets"** (or similar import action).
3.  Click **"Add Google Sheet"**.
4.  Select the **District** (if global admin) or verify your district is pre-selected.
5.  Enter the **Sheet ID** (from the Google Sheet URL).
6.  Click **Add**.
7.  Once added, click **Import** to pull the teacher records.

#### 3. Teacher Matching
After import, "TeacherProgress" records exist but may not be linked to VMS "Teacher" accounts. Linking them enables the detail view.

-   **Auto-Matching**:
    -   The system attempts to match by **Email** (Exact) then **Name** (Fuzzy/Similar).
    -   Run this immediately after import via the **"Match Teachers"** interface.
-   **Manual Matching**:
    -   Go to **"Match Teachers"**.
    -   Filter by **"Show Unmatched Only"**.
    -   For each unmatched teacher, select the correct VMS Teacher record from the dropdown and click **Match**.

*Reference: See [Teacher Progress Matching Guide](../guides/teacher_progress_matching.md) for technical details on the matching algorithm.*

## 3. Teacher Magic Links

Teachers do not need passwords. They use **Magic Links** sent to their email.

1.  Teacher clicks "Teacher Login" on the portal.
2.   Enters email address.
3.  Receives an email with a secure, time-limited link.
4.  Clicking the link opens their personal dashboard showing Past and Upcoming sessions.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-501](user_stories#us-501), [US-502](user_stories#us-502), [US-503](user_stories#us-503), [US-504](user_stories#us-504), [US-505](user_stories#us-505) |
| **Requirements** | [FR-DISTRICT-501](requirements#fr-district-501) through [FR-DISTRICT-524](requirements#fr-district-524) |
