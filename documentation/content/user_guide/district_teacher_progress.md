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
-   **Achieved**: Teacher attended ≥ 1 completed virtual session (verified via EventTeacher attendance status).
-   **In Progress**: Has ≥ 1 future signup but 0 attended completed sessions.
-   **Not Started**: No signups and no attended completed sessions.

> [!NOTE]
> **Attendance-Based Counting**: The system only counts sessions where the teacher's `EventTeacher.status` is `'attended'` or `'completed'`. Teachers who registered but did not attend (status `'registered'` or `'no_show'`) are not counted toward completion. Attendance status is set automatically during the daily Pathful import based on the CSV's `Status` column.

### Revising No-Shows

If a teacher is incorrectly marked as a no-show, virtual admins and global admins can correct it directly from the **No Shows Report** page:

1.  Navigate to the **Teacher Usage Dashboard** → click the **No Shows** link.
2.  Find the session in question under the teacher's school section.
3.  Click the **Revise No-Show** button next to the session.
4.  Enter a required reason explaining the correction (e.g., "Teacher was present but not recorded in system").
5.  Click **Mark as Attended** — the teacher's `EventTeacher.status` changes from `no_show` to `attended`, and the session is removed from the no-show list.

All revisions are logged in the [Audit Log](../requirements/virtual#fr-virtual-241) with the admin's identity, timestamp, and stated reason. Overrides can be reversed from the teacher's detail view if needed.

### Signing Up for Upcoming Sessions

Virtual admins and global admins can register a teacher for an upcoming virtual session directly from the **Teacher Detail** page:

1.  Navigate to a teacher's detail view from the **Teacher Usage Dashboard**.
2.  Click the **Sign Up for Session** button next to the **Upcoming Sessions** header.
3.  Search for an upcoming session by title or topic.
4.  Select the session and enter a required reason.
5.  Click **Sign Up** — an `EventTeacher` record is created with `status='registered'`, and the session appears in the teacher's Upcoming Sessions list with an **Override** badge.

Sign-ups can be removed using the **Remove** button that appears on override sessions. All actions are audit-logged.

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

*Last updated: March 2026*
