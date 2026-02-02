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

#### 2. Importing the Roster & Matching
 Teacher data is imported and matched by internal VMS administrators.

 > [!NOTE]
 > **Internal Staff:** Please refer to the [Teacher Roster Import Playbook](import_playbook#playbook-b-teacher-roster-import) for detailed instructions on importing rosters and running the matching process.

 Once imported, teachers appear in the list below. Matching ensures they are linked to their VMS user accounts for detailed reporting.

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
| **User Stories** | [US-501](user_stories#us-501)–[US-505](user_stories#us-505), [US-1005](user_stories#us-1005), [US-1006](user_stories#us-1006) |
| **Requirements** | [FR-DISTRICT-501](requirements#fr-district-501)–[FR-DISTRICT-524](requirements#fr-district-524), [FR-TENANT-113](requirements#fr-tenant-113)–[FR-TENANT-117](requirements#fr-tenant-117) |

---

> [!TIP]
> **Tenant Administrators**: For tenant-scoped teacher management (roster import and usage dashboards), see [Tenant Management Guide](tenant_management#teacher-roster-import).

---

*Last updated: February 2026*
