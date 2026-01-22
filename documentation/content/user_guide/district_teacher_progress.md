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
Teacher data is imported from district rosters (CSV/Google Sheets).
-   **Auto-Matching**: The system attempts to link imported rows to database records by Email (primary) or Fuzzy Name Match (secondary).
-   **Manual Matching**: Admins can resolve unmatched teachers at `/virtual/usage/district/.../matching`.

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
