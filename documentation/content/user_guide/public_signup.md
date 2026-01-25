# Public Volunteer Signup

This guide explains the public-facing signup flow for context.

## 1. Ways to Sign Up

We offer multiple pathways for volunteers to get involved, depending on their entry point:

1.  **Volunteer Hub (Standard)**: The main public page listing all open opportunities.
    *   **URL**: [prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)
2.  **Data in Action (DIA)**: Targeted events often shared via specific outreach.
    *   **URL**: [prepkc.org/dia.html](https://prepkc.org/dia.html)
3.  **District Links**: Custom, filtered views of the Volunteer Hub sent directly to district partners.

## 2. The Signup Process

1.  Volunteer clicks **"Sign Up"** on an event.
2.  This opens the **Form Assembly** integration (via the event's unique `Registration Link`).

### The Signup Form

![Volunteer Signup Form](content/user_guide/images/signup_form.png)

Volunteers must provide the following information:

*   **Contact Info**:
    *   First Name *, Last Name *
    *   Email * (Used as unique identifier)
    *   Organization *, Title *
    *   Mobile Phone
*   **Background**:
    *   Volunteer Skill(s) * (Select multiple)
*   **Demographics** (for reporting):
    *   Age Group *
    *   Highest Level of Education *
    *   Gender *
    *   Racial/Ethnic Background *

3.  **Submission**:
    *   Form Assembly validates the input.
    *   A **Salesforce Contact/Participation** record is created immediately.
    *   Salesforce sends a **Confirmation Email** & **Calendar Invite**.
    *   Polaris imports the new volunteer record via nightly sync.

## 3. Post-Signup

-   **Confirmation**: Volunteer receives an email immediately.
-   **Reminders**: System sends reminders closer to the event.

> [!WARNING]
> **Calendar Invite Updates**
> Calendar invites sent upon signup are **static**. If event details change (e.g., time or location), the calendar invite will **NOT** automatically update. Volunteers must manually update their calendars based on the email notifications they receive.

## Technical Scope & Traceability

This guide addresses the following scopes:

| Component | Items |
|---|---|
| **User Stories** | [US-201](user_stories#us-201), [US-202](user_stories#us-202), [US-203](user_stories#us-203) |
| **Requirements** | [FR-SIGNUP-121](requirements#fr-signup-121) through [FR-SIGNUP-127](requirements#fr-signup-127) |
