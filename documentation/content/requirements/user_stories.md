# User Stories

**Business intent organized by epic with acceptance criteria**

---

## Quick Navigation

| Epic | Description | Stories |
|------|-------------|:-------:|
| [Epic 1](#epic-1) | In-Person Events (Salesforce → VolunTeach → Website) | 5 |
| [Epic 2](#epic-2) | Public Volunteer Signup + Confirmation + Calendar Invite | 3 |
| [Epic 3](#epic-3) | Virtual Events in Polaris + Pathful Data Ingest + Data Management | 15 |
| [Epic 4](#epic-4) | Volunteer Recruitment (Search + History + Communication Logs) | 6 |
| [Epic 5](#epic-5) | District Progress Dashboards + Teacher Magic Links | 6 |
| [Epic 6](#epic-6) | Student Roster + Attendance | 3 |
| [Epic 7](#epic-7) | Reporting + Exports + Ad Hoc Queries | 5 |
| [Epic 8](#epic-8) | Email System Management | 3 |
| [Epic 9](#epic-9) | Data Tracker Features | 3 |
| [Epic 10](#epic-10) | Tenant Management (District Suite) | 6 |
| [Epic 11](#epic-11) | District Self-Service (District Suite) | 7 |
| [Epic 12](#epic-12) | Public Event API (District Suite) | 2 |
| [Epic 13](#epic-13) | Bug Reporting | 3 |

---

## Structure

Each story follows: **As [role], I want [capability], So that [benefit]**. Acceptance criteria define "done."

---

<a id="epic-1"></a>

## Epic 1: In-Person Events (Salesforce → VolunTeach → Website)

### <a id="us-101"></a>US-101: Create an in-person event in Salesforce

**As** internal staff, **I want** to create an in-person event record in Salesforce, **So that** it can be synced to VolunTeach and published as needed.

**Related Requirements:** [FR-INPERSON-101](requirements-in-person#fr-inperson-101)

**Related Use Cases:** [UC-1](use-cases#uc-1)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#creating-an-event-in-salesforce)

**Acceptance Criteria:**

- Given I have Salesforce access, when I create an event with required fields, then the event is saved successfully.
- Given the event exists, when synced, then it contains key fields for website display (date/time, school, description/type, volunteer slots needed, location).

### <a id="us-102"></a>US-102: Sync events from Salesforce into VolunTeach

**As** internal staff, **I want** events to sync from Salesforce into VolunTeach automatically and on-demand, **So that** the website list stays current.

**Related Requirements:** [FR-INPERSON-102](requirements-in-person#fr-inperson-102), [FR-INPERSON-103](requirements-in-person#fr-inperson-103), [FR-INPERSON-123](requirements-in-person#fr-inperson-123)

**Related Use Cases:** [UC-2](use-cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#syncing-to-volunteach)

**Acceptance Criteria:**

- Given a new Salesforce event exists, when hourly sync runs, then the event appears in VolunTeach.
- Given a new Salesforce event exists, when I click "Sync now," then the event appears in VolunTeach.
- Given I run sync repeatedly without changes, then events are not duplicated (idempotent).

### <a id="us-103"></a>US-103: Control public in-person page visibility

**As** internal staff, **I want** to toggle whether an event appears on the public in-person events page, **So that** orientations/internal events don't show publicly.

**Related Requirements:** [FR-INPERSON-104](requirements-in-person#fr-inperson-104), [FR-INPERSON-105](requirements-in-person#fr-inperson-105)

**Related Use Cases:** [UC-2](use-cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#managing-visibility)

**Acceptance Criteria:**

- Given an event exists in VolunTeach, when I set "In-person page visibility" ON, then the event appears on the public page.
- Given an event exists, when I set that toggle OFF, then the event does not appear on the public page (unless it is a DIA event).
- Given an event is OFF, then it may still appear on district pages if district-linked.
- Given an event has "DIA" in the session type (Data in Action), then it appears on the public page automatically (regardless of the toggle), provided it has future slots available.

### <a id="us-104"></a>US-104: Link events to districts for district pages

**As** internal staff, **I want** to link an event to a district in VolunTeach, **So that** it appears on the district's website view.

**Related Requirements:** [FR-INPERSON-107](requirements-in-person#fr-inperson-107), [FR-INPERSON-109](requirements-in-person#fr-inperson-109)

**Related Use Cases:** [UC-2](use-cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#district-page-visibility)

**Acceptance Criteria:**

- Given an event exists, when I link it to District X, then it appears on District X's website page.
- Given the event is district-linked, then it appears on the district page regardless of the in-person page visibility toggle.
- Given I unlink an event from District X, then it no longer appears on District X's page.

### <a id="us-105"></a>US-105: Display correct event details on website

**As** a volunteer, **I want** to see key event information on the website listing, **So that** I can decide whether to sign up.

**Related Requirements:** [FR-INPERSON-106](requirements-in-person#fr-inperson-106)

**Acceptance Criteria:**

- Given an event is visible on a page, then it shows at minimum: volunteer slots needed, slots filled, date/time, school, description/type.
- Given a signup occurs, when I refresh the listing, then "slots filled" reflects the new signup.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-2"></a>

## Epic 2: Public Volunteer Signup + Confirmation + Calendar Invite

### <a id="us-201"></a>US-201: Volunteer can sign up without an account

**As** a volunteer, **I want** to sign up for an event without creating an account, **So that** I can register quickly.

**Related Requirements:** [FR-SIGNUP-121](requirements-in-person#fr-signup-121), [FR-SIGNUP-122](requirements-in-person#fr-signup-122), [FR-SIGNUP-127](requirements-in-person#fr-signup-127)

**Related Use Cases:** [UC-3](use-cases#uc-3)

**User Guide:** [Public Signup Flow](#user-guide-public-signup)

**Acceptance Criteria:**

- Given I view an event signup form, when I submit valid required fields, then my signup is accepted and stored as a participation record.
- Given I submit with missing required fields, then I see clear validation errors and the signup is not stored.

### <a id="us-202"></a>US-202: Collect required signup fields (including dropdowns)

**As** internal staff, **I want** the signup form to collect standardized volunteer profile fields, **So that** we can recruit and report consistently.

**Related Requirements:** [FR-SIGNUP-126](requirements-in-person#fr-signup-126), [FR-SIGNUP-127](requirements-in-person#fr-signup-127)

**Acceptance Criteria:**

- Given the signup form, then it requires: First Name, Last Name, Email, Organization, Title, and all dropdown fields (Skills, Age Group, Education, Gender, Race/Ethnicity).
- Given a dropdown field, when a user submits an invalid value (tampered), then the submission is rejected.

### <a id="us-203"></a>US-203: Send confirmation email and calendar invite

**As** a volunteer, **I want** an email confirmation and calendar invite, **So that** I have the details saved and reminders.

**Related Requirements:** [FR-SIGNUP-123](requirements-in-person#fr-signup-123), [FR-SIGNUP-124](requirements-in-person#fr-signup-124), [FR-SIGNUP-125](requirements-in-person#fr-signup-125)

**Related Use Cases:** [UC-3](use-cases#uc-3)

**Acceptance Criteria:**

- Given a successful signup, then a confirmation email is sent to the submitted email.
- Given a successful signup, then a calendar invite is sent to the submitted email.
- Given the Salesforce event has location details, then the calendar invite includes the correct location/map details.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-3"></a>

## Epic 3: Virtual Events in Polaris + Pathful Data Ingest

### <a id="us-301"></a>US-301: Create a virtual event in Polaris

**As** internal staff, **I want** to create and edit virtual events in Polaris, **So that** we can manage sessions without Google Sheets.

**Related Requirements:** [FR-VIRTUAL-201](requirements-virtual#fr-virtual-201)

**Related Use Cases:** [UC-4](use-cases#uc-4)

**User Guide:** [Virtual Event Management](user_guide/virtual_events#1-creating-virtual-events)

**Acceptance Criteria:**

- Given I create a virtual event with required fields, then it saves and is visible in the event list.
- Given I edit the event, then changes persist after reload.

### <a id="us-302"></a>US-302: Tag teachers via Salesforce-linked search

**As** internal staff, **I want** to attach teachers to a virtual event via search, **So that** reporting and progress tracking are linked to real teacher records.

**Related Requirements:** [FR-VIRTUAL-202](requirements-virtual#fr-virtual-202)

**Related Use Cases:** [UC-4](use-cases#uc-4)

**Acceptance Criteria:**

- Given a teacher exists in Salesforce and is synced to Polaris, when I search and select the teacher, then the teacher is linked to the Polaris event.
- Given a synced record search failure, then Polaris shows an actionable error (not silent empty results).

### <a id="us-303"></a>US-303: Tag presenters to virtual events

**As** internal staff, **I want** to search for and tag presenters/volunteers to a virtual event using Salesforce-linked records, **So that** events have assigned presenters and recruitment tracking is accurate.

**Related Requirements:** [FR-VIRTUAL-203](requirements-virtual#fr-virtual-203)

**Related Use Cases:** [UC-4](use-cases#uc-4), [UC-11](use-cases#uc-11)

**Acceptance Criteria:**

- Given a volunteer/presenter exists in Salesforce and is synced to Polaris, when I search and select them, then they are linked to the Polaris event as a presenter.
- Given I tag a presenter to an event, then the event no longer appears in the presenter recruitment view.
- Given a synced record search failure, then Polaris shows an actionable error (not silent empty results).

### <a id="us-304"></a>US-304: Import Pathful export into Polaris

**As** internal staff, **I want** to import Pathful signup/attendance data into Polaris, **So that** we can track attendance and teacher progress.

**Related Requirements:** [FR-VIRTUAL-206](requirements-virtual#fr-virtual-206)

**Related Use Cases:** [UC-5](use-cases#uc-5)

**Related Stories (Post-Import):** [US-310](user-stories#us-310), [US-311](user-stories#us-311), [US-312](user-stories#us-312)

**Acceptance Criteria:**

- Given a Pathful export with valid rows, when I import it, then Polaris creates/updates participation records without duplicates.
- Given the same file is imported twice, then the import is idempotent (no duplicates; updates only).
- Given rows reference unknown teachers or events, then those rows are flagged as unmatched.
- Given required columns are missing, then the import fails with a clear missing-columns message.
- Given import completes successfully, then events are scanned for data issues (missing teachers, missing presenters, cancelled without reason) and flagged per [FR-VIRTUAL-224](requirements-virtual#fr-virtual-224) through [FR-VIRTUAL-228](requirements-virtual#fr-virtual-228).

### <a id="us-305"></a>US-305: Track local vs non-local volunteers

**As** internal staff, **I want** to track whether a virtual volunteer is local vs non-local, **So that** I can prioritize local volunteers for in-person opportunities and understand geographic reach.

**Related Requirements:** [FR-VIRTUAL-208](requirements-virtual#fr-virtual-208)

**Acceptance Criteria:**

- Given a volunteer participates in a virtual event, when I view their profile, then I can see whether they are marked as local or non-local.
- Given I filter volunteers by local status, then results correctly show only local or only non-local volunteers.
- Given a volunteer's local status is unknown, then the system displays "unknown" without error.

### <a id="us-306"></a>US-306: Import historical virtual data from Google Sheets

> [!NOTE]
> **Consolidated into US-304** — Historical data import via Pathful direct export (contains 2-4 years of data). See [Pathful Import Deployment](dev/pathful_import_deployment) for details.

**As** internal staff, **I want** to import 2–4 years of historical virtual events from Google Sheets, **So that** our reporting and history are complete.

**Related Requirements:** [FR-VIRTUAL-204](requirements-virtual#fr-virtual-204)

**Acceptance Criteria:**

- Given a sheet where one event spans multiple lines, when imported, then the event is not duplicated and all teacher/presenter relationships are preserved.
- Given the same historical sheet is imported twice, then the import is idempotent (no duplicates).

### <a id="us-307"></a>US-307: View upcoming sessions needing presenters

**As** internal staff with global scope or admin privileges, **I want** to see a list of upcoming virtual events that don't have a presenter yet, **So that** I can proactively recruit volunteers and ensure all sessions are covered.

**Related Requirements:** [FR-VIRTUAL-210](requirements-virtual#fr-virtual-210), [FR-VIRTUAL-211](requirements-virtual#fr-virtual-211), [FR-VIRTUAL-212](requirements-virtual#fr-virtual-212), [FR-VIRTUAL-213](requirements-virtual#fr-virtual-213), [FR-VIRTUAL-214](requirements-virtual#fr-virtual-214), [FR-VIRTUAL-215](requirements-virtual#fr-virtual-215), [FR-VIRTUAL-216](requirements-virtual#fr-virtual-216), [FR-VIRTUAL-217](requirements-virtual#fr-virtual-217), [FR-VIRTUAL-218](requirements-virtual#fr-virtual-218), [FR-VIRTUAL-219](requirements-virtual#fr-virtual-219)

**Related Use Cases:** [UC-11](use-cases#uc-11)

**User Guide:** [Virtual Event Management](user_guide/virtual_events#2-presenter-recruitment)

**Acceptance Criteria:**

- Given I access the presenter recruitment view at /virtual/usage/recruitment, then I see only virtual events without an assigned presenter (no EventParticipation with participant_type='Presenter').
- Given an event is in the past, then it does not appear in the presenter recruitment view.
- Given I filter by academic year, date range, school, district, or text search, then results match those criteria.
- Given events are displayed, then they are sorted by start date with urgency indicators: red (≤7 days), yellow (8-14 days), blue (>14 days).
- Given I am a district-scoped or school-scoped user, then I receive an access denied error and am redirected to Virtual Session Usage Report.
- Given an event has at least one presenter tagged, then it disappears from the view on page refresh.
- Given I click an event row or "Edit Event" button, then I can access the event edit page to tag a presenter.
- Given I click "Find Volunteers" button, then I navigate to the volunteer search/recruitment page.
- Given all upcoming virtual sessions have presenters, then I see a success message "All upcoming virtual sessions have presenters assigned."

### <a id="us-308"></a>US-308: Quick Create Teacher in Virtual Session Flow

**As** internal staff, **I want** to add a new teacher record directly from the virtual session creation form if they don't exist in search results, **So that** I can complete the event setup without navigating away.

**Related Requirements:** [FR-VIRTUAL-222](requirements-virtual#fr-virtual-222)

**Related Use Cases:** [UC-4](use-cases#uc-4)

**Acceptance Criteria:**

- Given I search for a teacher and get no results, then I see an option to "Add New Teacher".
- Given I select "Add New Teacher", then I can enter First Name, Last Name, and School (required).
- Given I submit the new teacher, then the record is created locally in Polaris and immediately linked to the session.
- The new teacher is flagged as "Created in Polaris" (not synced from Salesforce).

### <a id="us-309"></a>US-309: Quick Create Presenter in Virtual Session Flow

**As** internal staff, **I want** to add a new presenter/volunteer record directly from the virtual session creation form if they don't exist in search results, **So that** I can tag non-synced or new volunteers immediately.

**Related Requirements:** [FR-VIRTUAL-223](requirements-virtual#fr-virtual-223)

**Related Use Cases:** [UC-4](use-cases#uc-4)

**Acceptance Criteria:**

- Given I search for a presenter and get no results, then I see an option to "Add New Presenter".
- Given I select "Add New Presenter", then I can enter First Name, Last Name, and Organization (required) and Email (optional).
- Given I submit the new presenter, then the record is created locally in Polaris and immediately linked to the session.
- The new volunteer is flagged as "Created in Polaris" (not synced from Salesforce).

### <a id="us-310"></a>US-310: District Admin Reviews Virtual Session Data

**As** a district administrator, **I want** to review and correct virtual session data for schools in my district, **So that** I can ensure accurate progress tracking and reporting without waiting for PrepKC staff.

**Related Requirements:** [FR-VIRTUAL-224](requirements-virtual#fr-virtual-224), [FR-VIRTUAL-225](requirements-virtual#fr-virtual-225), [FR-VIRTUAL-226](requirements-virtual#fr-virtual-226), [FR-VIRTUAL-228](requirements-virtual#fr-virtual-228), [FR-VIRTUAL-229](requirements-virtual#fr-virtual-229), [FR-VIRTUAL-230](requirements-virtual#fr-virtual-230)

**Related Use Cases:** [UC-5](use-cases#uc-5), [UC-20](use-cases#uc-20)

**Acceptance Criteria:**

- Given I am a district admin, when I access the virtual events view, then I see only events at schools within my district(s).
- Given an event has auto-flagged issues (missing teacher, missing presenter, draft with past date), then those flags are visible in my view.
- Given I have edit access to an event, when I tag a teacher or presenter, then the change is saved and the corresponding flag is resolved.
- Given I cannot find a teacher in search, then I can "Quick Create" a new teacher record locally.
- Given I edit an event, then my changes are logged with my user identity and role.

### <a id="us-311"></a>US-311: Set Cancellation Reasons for Virtual Sessions

**As** staff or a district administrator, **I want** to record why a virtual session was cancelled using predefined reasons, **So that** we can identify patterns and report accurately on session outcomes.

**Related Requirements:** [FR-VIRTUAL-227](requirements-virtual#fr-virtual-227), [FR-VIRTUAL-228](requirements-virtual#fr-virtual-228), [FR-VIRTUAL-231](requirements-virtual#fr-virtual-231)

**Related Use Cases:** [UC-5](use-cases#uc-5), [UC-20](use-cases#uc-20)

**Acceptance Criteria:**

- Given a virtual event has status=Cancelled, when I edit it, then I see a dropdown to select a cancellation reason.
- Given the cancellation reasons, then they include: Weather/Snow Day, Presenter Cancelled, Teacher Cancelled, School Conflict, Technical Issues, Low Enrollment, Scheduling Error, Other.
- Given I select "Other", then I must provide explanatory notes.
- Given I set a cancellation reason, then the corresponding "needs reason" flag is resolved.
- Given I am a district admin, then I can set cancellation reasons only for events in my district scope.

### <a id="us-312"></a>US-312: View Audit Trail for Virtual Event Changes

**As** PrepKC staff, **I want** to view a complete audit trail of changes to virtual events, **So that** I can track who made edits, when, and what was changed for accountability and troubleshooting.

**Related Requirements:** [FR-VIRTUAL-232](requirements-virtual#fr-virtual-232), [FR-VIRTUAL-233](requirements-virtual#fr-virtual-233)

**Related Use Cases:** [UC-5](use-cases#uc-5)

**Acceptance Criteria:**

- Given changes are made to a virtual event (tagging, status change, cancellation reason), then an audit log entry is created capturing: user identity, user role, timestamp, action type, old value, new value.
- Given I view an event's audit history, then I see all changes in chronological order.
- Given I filter the audit log by user, district, or date range, then results match those criteria.
- Given I view the audit log, then I can distinguish between staff edits, district admin edits, and system/import changes.

### <a id="us-313"></a>US-313: Virtual Admin Adds Teacher to Session Attendance

**As** a virtual admin, **I want** to manually add a teacher to a completed virtual session's attendance, **So that** teachers who attended without prior signup or joined via another class get credit toward their session goal.

**Related Requirements:** [FR-VIRTUAL-234](requirements-virtual#fr-virtual-234), [FR-VIRTUAL-235](requirements-virtual#fr-virtual-235), [FR-VIRTUAL-236](requirements-virtual#fr-virtual-236), [FR-VIRTUAL-238](requirements-virtual#fr-virtual-238), [FR-VIRTUAL-239](requirements-virtual#fr-virtual-239), [FR-VIRTUAL-240](requirements-virtual#fr-virtual-240)

**Related Use Cases:** [UC-21](use-cases#uc-21)

**Acceptance Criteria:**

- Given I am a virtual admin, when I view a teacher's session history, then I see an "Add to Session" action.
- Given I click "Add to Session", then I can search/browse completed sessions within my tenant's district.
- Given I select a session, then I must provide a reason/note before confirming (required field).
- Given I confirm the override, then the teacher's progress immediately recalculates to include the added session.
- Given the override is saved, then it is reflected in district dashboards, exports, and main app tracking.
- Given the override is displayed in the teacher detail view, then it is visually distinguished from system-matched sessions (e.g., badge or icon).

### <a id="us-314"></a>US-314: Virtual Admin Removes Teacher from Session Attendance

**As** a virtual admin, **I want** to remove an incorrectly recorded teacher from a session's attendance, **So that** progress data is accurate when a teacher was mistakenly credited.

**Related Requirements:** [FR-VIRTUAL-237](requirements-virtual#fr-virtual-237), [FR-VIRTUAL-235](requirements-virtual#fr-virtual-235), [FR-VIRTUAL-236](requirements-virtual#fr-virtual-236), [FR-VIRTUAL-238](requirements-virtual#fr-virtual-238), [FR-VIRTUAL-239](requirements-virtual#fr-virtual-239)

**Related Use Cases:** [UC-21](use-cases#uc-21)

**Acceptance Criteria:**

- Given I am a virtual admin viewing a teacher's session history, when I see a session with incorrect attendance, then I see a "Remove from Session" action.
- Given I click "Remove from Session", then I must provide a reason/note before confirming (required field).
- Given I confirm the removal, then the teacher's progress recalculates excluding the removed session.
- Given the removal is a soft operation, then the original data is preserved (not hard-deleted) and can be restored.

### <a id="us-315"></a>US-315: View Audit Log for Virtual Admin Attendance Overrides

**As** PrepKC staff, **I want** to view an audit trail of all virtual admin attendance overrides, **So that** I can verify changes, roll back if needed, and monitor admin activity across tenants.

**Related Requirements:** [FR-VIRTUAL-241](requirements-virtual#fr-virtual-241), [FR-VIRTUAL-242](requirements-virtual#fr-virtual-242), [FR-VIRTUAL-243](requirements-virtual#fr-virtual-243)

**Related Use Cases:** [UC-21](use-cases#uc-21)

**Acceptance Criteria:**

- Given attendance overrides are made, then an audit log entry is created capturing: admin identity, admin role, timestamp, teacher, session, action (add/remove), and stated reason.
- Given I view the audit log, then I can filter by admin, teacher, session, date range, and tenant.
- Given I view a teacher's session history, then I can distinguish between system-matched attendance and admin-overridden attendance.
- Given I identify an incorrect override, then I can reverse it and restore the original attendance state.

[↑ Back to Quick Navigation](#quick-navigation)

---

## Epic 4: Volunteer Recruitment (Search + History + Communication Logs)

### <a id="us-401"></a>US-401: Search volunteers with advanced filters

**As** internal staff, **I want** to search volunteers by name/org/skills/career/local, **So that** I can recruit the right people quickly.

**Related Requirements:** [FR-RECRUIT-301](requirements-recruitment#fr-recruit-301), [FR-RECRUIT-302](requirements-recruitment#fr-recruit-302), [FR-RECRUIT-303](requirements-recruitment#fr-recruit-303)

**Related Use Cases:** [UC-6](use-cases#uc-6)

**User Guide:** [Volunteer Recruitment](user_guide/volunteer_recruitment#1-volunteer-directory)

**Acceptance Criteria:**

- Given the volunteer directory, when I filter by organization, skills, career type, and local, then results match those criteria.
- Given I combine filters, then results reflect the intersection (not a union).
- Given a volunteer is missing an attribute, then searches do not error and results are consistent.

### <a id="us-402"></a>US-402: View volunteer participation history

**As** internal staff, **I want** to see a volunteer's participation history including most recent volunteer date, **So that** I can understand their engagement level and prioritize outreach.

**Related Requirements:** [FR-RECRUIT-304](requirements-recruitment#fr-recruit-304)

**Related Use Cases:** [UC-6](use-cases#uc-6)

**Acceptance Criteria:**

- Given a volunteer has participated in events, when I view their profile, then I see a list of their participation history.
- Given the participation history, then it displays the most recent volunteer date.
- Given a volunteer has no participation, then the profile shows an appropriate message (not an error).

### <a id="us-403"></a>US-403: Record recruitment notes and outcomes

**As** internal staff, **I want** to record recruitment notes and outcomes in Polaris, **So that** I can track outreach efforts and outcomes for future reference.

**Related Requirements:** [FR-RECRUIT-306](requirements-recruitment#fr-recruit-306)

**Acceptance Criteria:**

- Given I am viewing a volunteer profile, when I record a recruitment note, then the note is saved and associated with that volunteer.
- Given I record an outcome (e.g., "Accepted", "Declined", "Follow-up needed"), then the outcome is stored and visible in the volunteer's profile.
- Given I view a volunteer's recruitment history, then I can see all notes and outcomes in chronological order.

### <a id="us-404"></a>US-404: View communication history from Salesforce Gmail logging

**As** internal staff, **I want** to see communication history in Polaris sourced from Salesforce email logs, **So that** I know the latest outreach and context.

**Related Requirements:** [FR-RECRUIT-305](requirements-recruitment#fr-recruit-305), [FR-RECRUIT-308](requirements-recruitment#fr-recruit-308)

**Related Use Cases:** [UC-6](use-cases#uc-6)

**User Guide:** [Volunteer Recruitment](user_guide/volunteer_recruitment#4-logging-communication-salesforce-gmail-integration)

**Acceptance Criteria:**

- Given emails are logged via Salesforce Gmail add-on, when comms sync runs, then those emails appear on the correct volunteer profile.
- Given new emails are logged, then after sync they appear in Polaris.

### <a id="us-405"></a>US-405: Distinguish "no comms" vs "sync failure"

**As** internal staff, **I want** Polaris to tell me whether comms are missing because none were logged vs sync failed, **So that** I can trust what I'm seeing.

**Related Requirements:** [FR-RECRUIT-309](requirements-recruitment#fr-recruit-309)

**Acceptance Criteria:**

- Given the comms sync is failing, then comms panel shows an explicit sync failure status (not "no comms").

### <a id="us-406"></a>US-406: Rank volunteers by relevance (Intelligent Matching)

**As** internal staff, **I want** the system to rank volunteers by relevance (keywords, history, location), **So that** I don't have to sift through hundreds of records manually.

**Related Requirements:** [FR-RECRUIT-310](requirements-recruitment#fr-recruit-310)–[FR-RECRUIT-336](requirements-recruitment#fr-recruit-336)

**Related Use Cases:** [UC-6](use-cases#uc-6)

**Acceptance Criteria:**

- Given I view recruitment search, then candidates are ranked by score (highest first).
- Given I add "Custom Keywords", then candidates matching those keywords get a higher score.
- The system explains *why* a candidate matched (e.g., "Matched on Title: Engineer").

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-5"></a>

## Epic 5: District Progress Dashboards + Teacher Magic Links

### <a id="us-501"></a>US-501: District viewer can see progress dashboard

**As** a district viewer, **I want** to see my district's progress dashboard, **So that** I can track school/teacher completion.

**Related Requirements:** [FR-DISTRICT-501](requirements-district#fr-district-501), [FR-DISTRICT-502](requirements-district#fr-district-502), [FR-DISTRICT-521](requirements-district#fr-district-521), [FR-DISTRICT-522](requirements-district#fr-district-522)

**Related Use Cases:** [UC-8](use-cases#uc-8)

**User Guide:** [District & Teacher Progress](user_guide/district_teacher_progress#1-district-dashboard-access)

**Acceptance Criteria:**

- Given I'm a District Viewer for District X, then I can access District X's dashboard and no other districts.
- Dashboard shows counts: schools, teachers, achieved/in-progress/not-started totals.

### <a id="us-502"></a>US-502: Drill down from district → school → teacher

**As** a district viewer, **I want** to drill down to schools and teachers, **So that** I can see who needs support.

**Related Requirements:** [FR-DISTRICT-503](requirements-district#fr-district-503)

**Related Use Cases:** [UC-8](use-cases#uc-8)

**Acceptance Criteria:**

- Given I click a school, then I see teacher-level rows for that school only.
- Each teacher displays status computed by the defined rules.

### <a id="us-503"></a>US-503: Define and compute progress statuses correctly

**As** internal staff and district viewers, **I want** the progress statuses to be computed consistently, **So that** reporting is trustworthy.

**Related Requirements:** [FR-DISTRICT-502](requirements-district#fr-district-502), [FR-DISTRICT-508](requirements-district#fr-district-508)

**Related Use Cases:** [UC-8](use-cases#uc-8)

**Acceptance Criteria:**

- Achieved = teacher completed ≥1 virtual session.
- In Progress = teacher has ≥1 future signup and 0 completed.
- Not Started = teacher has no signups and 0 completed.

### <a id="us-504"></a>US-504: Import teacher roster for progress tracking

**As** internal staff, **I want** to import a district-provided teacher roster, **So that** the system can track progress and enable magic-link access for teachers.

**Related Requirements:** [FR-DISTRICT-524](requirements-district#fr-district-524)

**Acceptance Criteria:**

- Given a district provides a teacher roster file (minimum: teacher name, email, grade; school if available), when I import it, then teachers are added to the system.
- Given the roster is imported, then it becomes the authoritative list for progress tracking.
- Given a teacher is in the roster, then they are eligible for magic-link access using their email.
- Given the same roster is imported again, then the import is idempotent (updates existing, adds new, handles removed teachers per policy).



### <a id="us-505"></a>US-505: Teacher can request magic link and verify data

**As** a teacher, **I want** to request a magic link using my email, **So that** I can view my progress and verify it.

**Related Requirements:** [FR-DISTRICT-505](requirements-district#fr-district-505), [FR-DISTRICT-506](requirements-district#fr-district-506), [FR-DISTRICT-507](requirements-district#fr-district-507), [FR-DISTRICT-508](requirements-district#fr-district-508), [FR-DISTRICT-521](requirements-district#fr-district-521), [FR-DISTRICT-523](requirements-district#fr-district-523)

**Related Use Cases:** [UC-9](use-cases#uc-9)

**User Guide:** [District & Teacher Progress](user_guide/district_teacher_progress#3-teacher-magic-links)

**Acceptance Criteria:**

- Given my email exists in the roster, when I request a link, then I receive an email with a link.
- The link shows only my data and cannot be modified to view other teachers.
- I can submit a flag/note if my data is incorrect.

### <a id="us-509"></a>US-509: Automatic Semester Progress Reset

**As** internal staff, **I want** teacher progress to reset automatically at the start of each semester, **So that** each semester's participation is tracked independently and historical data is preserved.

**Related Requirements:** [FR-DISTRICT-540](requirements-district#fr-district-540), [FR-DISTRICT-541](requirements-district#fr-district-541), [FR-DISTRICT-542](requirements-district#fr-district-542), [FR-DISTRICT-543](requirements-district#fr-district-543)

**Related Use Cases:** [UC-13](use-cases#uc-13)

**Acceptance Criteria:**

- Given it is January 1 or June 30, when the system runs the semester reset, then all teacher progress statuses are reset to "Not Started".
- Given the reset runs, then the previous semester's data is archived before reset.
- Given archived data exists, then staff can view historical semester summaries.
- Given the reset completes, then a log entry records the operation details.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-6"></a>

## Epic 6: Student Roster + Attendance

### <a id="us-601"></a>US-601: Staff can roster students to events

**As** internal staff, **I want** to associate students with events, **So that** we can track reach and attendance.

**Related Requirements:** [FR-STUDENT-601](requirements-student#fr-student-601)

**Related Use Cases:** [UC-10](use-cases#uc-10)

**User Guide:** [Student Roster & Attendance](user_guide/student_management#1-rostering-students)

**Acceptance Criteria:**

- Given an event, when students are added to the roster, then student-event participation records exist.

### <a id="us-602"></a>US-602: Staff can mark student attendance

**As** internal staff, **I want** to record attendance for rostered students, **So that** reports reflect real participation.

**Related Requirements:** [FR-STUDENT-602](requirements-student#fr-student-602)

**Related Use Cases:** [UC-10](use-cases#uc-10)

**Acceptance Criteria:**

- Given a rostered student, when attendance is marked, then attendance status is saved and can be updated.

### <a id="us-603"></a>US-603: Reporting uses attendance to compute student reach

**As** leadership/internal staff, **I want** reports to compute unique students reached using attendance, **So that** we can report impact accurately.

**Related Requirements:** [FR-STUDENT-603](requirements-student#fr-student-603), [FR-STUDENT-604](requirements-student#fr-student-604)

**Related Use Cases:** [UC-10](use-cases#uc-10)

**Acceptance Criteria:**

- Given attended records, then unique students reached matches the defined computation rules for district/school.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-7"></a>

## Epic 7: Reporting + Exports + Ad Hoc Queries

### <a id="us-701"></a>US-701: Volunteer thank-you reporting

**As** leadership/internal staff, **I want** volunteer thank-you dashboards, **So that** I can recognize top contributors.

**Related Requirements:** [FR-REPORTING-401](requirements-reporting#fr-reporting-401), [FR-REPORTING-406](requirements-reporting#fr-reporting-406)

**Related Use Cases:** [UC-7](use-cases#uc-7)

**User Guide:** [Volunteer Engagement Reports](reports/volunteer_engagement)

**Acceptance Criteria:**

- Dashboard ranks volunteers correctly by hours and/or events for a selected time range.
- Export matches the dashboard view.

### <a id="us-702"></a>US-702: Organization participation reporting

**As** leadership/internal staff, **I want** organization participation dashboards, **So that** I can recognize partner organizations.

**Related Requirements:** [FR-REPORTING-402](requirements-reporting#fr-reporting-402), [FR-REPORTING-406](requirements-reporting#fr-reporting-406)

**Related Use Cases:** [UC-7](use-cases#uc-7)

**User Guide:** [Impact & KPI Reports](reports/impact)

**Acceptance Criteria:**

- Dashboard shows correct totals per organization and unique organizations engaged.
- Export matches view.

### <a id="us-703"></a>US-703: District/school impact reporting

**As** leadership/internal staff, **I want** district/school impact dashboards, **So that** I can complete district reporting and grants.

**Related Requirements:** [FR-REPORTING-403](requirements-reporting#fr-reporting-403), [FR-REPORTING-404](requirements-reporting#fr-reporting-404), [FR-REPORTING-406](requirements-reporting#fr-reporting-406)

**Related Use Cases:** [UC-7](use-cases#uc-7)

**User Guide:** [Impact & KPI Reports](reports/impact)

**Acceptance Criteria:**

- Dashboard includes: unique students reached, unique volunteers reached, total volunteer hours, unique organizations engaged.
- Filters by district/school/event type/date range work correctly.
- Export matches filtered view.

### <a id="us-704"></a>US-704: Ad hoc reporting for one-off questions

**As** leadership/internal staff, **I want** to answer one-off questions with queries/reports, **So that** I can respond to partner and grant requests quickly.

**Related Requirements:** [FR-REPORTING-405](requirements-reporting#fr-reporting-405), [FR-REPORTING-406](requirements-reporting#fr-reporting-406)

**Related Use Cases:** [UC-7](use-cases#uc-7)

**User Guide:** [Ad Hoc Queries](reports/ad_hoc)

**Acceptance Criteria:**

- Given an organization filter, the query returns correct counts/lists.
- Export matches query results.

### <a id="us-705"></a>US-705: Reconcile external partner lists (e.g., KCTAA)

**As** internal staff, **I want** to match an external list of names against our database, **So that** I can report on partner member engagement even if they used different email addresses.

**Related Requirements:** [FR-REPORTING-407](requirements-reporting#fr-reporting-407), [FR-REPORTING-408](requirements-reporting#fr-reporting-408)

**Related Use Cases:** [UC-12](use-cases#uc-12)


**User Guide:** [Partner Reconciliation](reports/partner_match)

**Acceptance Criteria:**

- Given I upload/select a partner list (CSV), then the system returns matches against the volunteer database.
- Given names are slightly different (e.g., "Rob" vs "Robert"), then the system identifies them as "Fuzzy Matches".
- I can export the reconciled list showing which partners are active volunteers.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-8"></a>

## Epic 8: Email System Management

### <a id="us-801"></a>US-801: Manage email templates

**As** internal staff (Admin), **I want** to create and manage email templates in the admin panel, **So that** we can send consistent, branded communications to volunteers and stakeholders.

**Related Requirements:** *Email system features documented in guides*

**User Guide:** [Email System](user_guide/email_system)

**Acceptance Criteria:**

- Given I access the email templates section, when I create a new template, then it is saved with a purpose key and version.
- Given a template exists, when I preview it with sample context, then it renders correctly with placeholders filled.
- Given I update a template, then the system validates that required placeholders are present and both HTML and text versions exist.

### <a id="us-802"></a>US-802: Monitor email delivery status

**As** internal staff (Admin), **I want** to monitor email delivery status and see delivery attempts, **So that** I can ensure communications are reaching recipients and troubleshoot failures.

**Related Requirements:** *Email system features documented in guides*

**Acceptance Criteria:**

- Given emails are sent, when I view the email dashboard, then I can see delivery status (sent, failed, blocked, queued).
- Given an email delivery fails, when I view the delivery attempt, then I see detailed error information.
- Given I view email metrics, then I see counts of successful sends, failures, and blocked emails.

### <a id="us-803"></a>US-803: Send emails via admin panel

**As** internal staff (Admin), **I want** to send emails through the admin panel with safety controls, **So that** I can communicate with volunteers while preventing accidental delivery in non-production environments.

**Related Requirements:** *Email system features documented in guides*

**Acceptance Criteria:**

- Given I am in a non-production environment, when I attempt to send an email, then delivery is blocked unless the recipient is on the allowlist.
- Given email delivery is disabled globally, when I attempt to send, then the email is queued but not delivered.
- Given I send an email, then the system creates a message record in the outbox before attempting delivery.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-9"></a>

## Epic 9: Data Tracker Features

### <a id="us-506"></a>US-506: District users can flag data issues

**As** a district user, **I want** to flag missing or incorrect data related to teachers and sessions in my district, **So that** internal staff can correct the data and reporting is accurate.

**Related Requirements:** *Data tracker features documented in guides*

**User Guide:** [Data Tracker](user_guide/data_tracker)

**Acceptance Criteria:**

- Given I am a district user viewing teacher or session data, when I identify incorrect information, then I can submit a flag with context (teacher, school, session, issue category, notes).
- Given I submit a flag, then it is stored and visible to internal staff for follow-up.
- Given I view my district's data, then I can only flag issues for teachers/sessions in my district (no cross-district access).

### <a id="us-507"></a>US-507: Teachers can view their session history

**As** a teacher, **I want** to view my past and upcoming virtual sessions, **So that** I can track my participation and verify the data is correct.

**Related Requirements:** *Data tracker features documented in guides*

**Acceptance Criteria:**

- Given I authenticate as a teacher, when I access my dashboard, then I see my past sessions (completed virtual sessions).
- Given I view my dashboard, then I see my upcoming sessions (scheduled virtual sessions).
- Given I identify incorrect data, then I can flag it with a note to internal staff.
- Given I view my data, then I can only see my own sessions (no access to other teachers' data).

### <a id="us-508"></a>US-508: Match imported teachers to database records

**As** internal staff, **I want** to match imported TeacherProgress entries to actual Teacher records, **So that** clicking a teacher links to their detail page.

**Related Requirements:** [FR-DISTRICT-531](requirements-district#fr-district-531)

**Acceptance Criteria:**

- Given TeacherProgress entries exist, when I run auto-match, then the system matches by email (primary) or fuzzy name.
- Given auto-match leaves unmatched entries, when I view the matching interface, then I can manually select and match.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-10"></a>

## Epic 10: Tenant Management (District Suite)

> [!NOTE]
> **District Suite** stories define capabilities for the multi-tenant platform expansion. These are planned for phased implementation.

### <a id="us-1001"></a>US-1001: Create and configure district tenant

**As** a PrepKC administrator, **I want** to create and configure new district tenants, **So that** partner districts can operate in isolated environments.

**Related Requirements:** [FR-TENANT-101](requirements-district-suite#fr-tenant-101), [FR-TENANT-102](requirements-district-suite#fr-tenant-102)

**Related Use Cases:** [UC-14](use-cases#uc-14)

**Acceptance Criteria:**

- Given I am a PrepKC admin, when I create a new tenant, then a new isolated database is provisioned with schema and reference data.
- Given a tenant exists, when I access the tenant management interface, then I can view and edit tenant settings.
- Given a tenant has issues, when I deactivate it, then users can no longer access that tenant.

### <a id="us-1002"></a>US-1002: Switch tenant context for support

**As** a PrepKC administrator, **I want** to switch to a district's tenant context, **So that** I can provide support and troubleshoot issues.

**Related Requirements:** [FR-TENANT-105](requirements-district-suite#fr-tenant-105)

**Acceptance Criteria:**

- Given I am a PrepKC admin, when I select a tenant from the switcher, then I operate within that tenant's context.
- Given I switch tenants, then my actions are logged with my identity and the target tenant for audit purposes.
- Given I am in a tenant context, then I see that tenant's data and can navigate their features.

### <a id="us-1003"></a>US-1003: Polaris admin creates tenant users

**As** a Polaris administrator, **I want** to create user accounts for district tenants, **So that** district staff can access their tenant's features.

**Related Requirements:** [FR-TENANT-108](requirements-district-suite#fr-tenant-108)

**Related Use Cases:** [UC-14](use-cases#uc-14)

**Acceptance Criteria:**

- Given I view a tenant's details, when I click "Add User", then I see a user creation form.
- Given I fill in valid user details (username, email, password, role), when I submit, then the user is created and assigned to that tenant.
- Given I create a user, then they have options for role selection: Tenant Admin, Coordinator, or User.
- Given the new user logs in, then they access only their assigned tenant's data.

### <a id="us-1004"></a>US-1004: Tenant admin manages users within tenant

**As** a tenant administrator, **I want** to create and manage user accounts for my organization, **So that** my colleagues can access our district's features based on their roles.

**Related Requirements:** [FR-TENANT-109](requirements-district-suite#fr-tenant-109), [FR-TENANT-110](requirements-district-suite#fr-tenant-110), [FR-TENANT-112](requirements-district-suite#fr-tenant-112)

**Related Use Cases:** [UC-19](use-cases#uc-19)

**Acceptance Criteria:**

- Given I am a tenant admin, when I access User Management, then I see only users in my tenant.
- Given I create a new user, then I can assign them a role: Admin, Coordinator, or User.
- Given I edit a user, then I can change their role or deactivate their account.
- Given a user logs in, then they see navigation appropriate to their role and my tenant's enabled features.
- Given a user with "User" role logs in, they see read-only dashboards and reports, but cannot modify data.

### <a id="us-1005"></a>US-1005: Tenant admin imports teacher roster

**As** a tenant administrator, **I want** to import my district's teacher roster, **So that** I can track teacher progress and enable teacher dashboard access.

**Related Requirements:** [FR-TENANT-113](requirements-district-suite#fr-tenant-113), [FR-TENANT-114](requirements-district-suite#fr-tenant-114)

**Related Use Cases:** [UC-14](use-cases#uc-14)

**Acceptance Criteria:**

- Given I am a tenant admin, when I access the Teacher Import page, then I can import teachers via CSV or Google Sheet URL.
- Given I import a roster, then teachers are created with their school associations and email addresses.
- Given a teacher already exists (by email), then their record is updated rather than duplicated.
- Given the import completes, then I see a summary showing teachers created, updated, and any errors.

### <a id="us-1006"></a>US-1006: Tenant admin views teacher usage dashboard

**As** a tenant administrator, **I want** to view a dashboard showing how many virtual sessions each teacher has attended, **So that** I can monitor district-wide teacher engagement.

**Related Requirements:** [FR-TENANT-115](requirements-district-suite#fr-tenant-115), [FR-TENANT-116](requirements-district-suite#fr-tenant-116), [FR-TENANT-117](requirements-district-suite#fr-tenant-117)

**Acceptance Criteria:**

- Given I access the Teacher Usage Dashboard, then I see all teachers in my tenant with their session counts.
- Given the dashboard displays, then teachers are grouped by building/school with aggregated totals.
- Given I select a semester filter (Fall/Spring), then only sessions from that semester are counted.
- Given I export the data, then I receive an Excel file with teacher names, schools, and session counts.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-11"></a>

## Epic 11: District Self-Service (District Suite)

### <a id="us-1101"></a>US-1101: District admin creates and manages events

**As** a district administrator, **I want** to create and manage events for my district, **So that** we can run volunteer engagement without PrepKC staff involvement.

**Related Requirements:** [FR-SELFSERV-201](requirements-district-suite#fr-selfserv-201), [FR-SELFSERV-202](requirements-district-suite#fr-selfserv-202), [FR-SELFSERV-203](requirements-district-suite#fr-selfserv-203)

**Related Use Cases:** [UC-15](use-cases#uc-15)

**Acceptance Criteria:**

- Given I am a district admin, when I create an event with required fields, then it is saved to my district's database.
- Given an event exists, when I edit it, then changes persist and are visible to my district's users.
- Given I cancel an event, then signed-up volunteers receive notification emails.

### <a id="us-1102"></a>US-1102: District admin manages event calendar

**As** a district administrator, **I want** to view my district's events in calendar and list formats, **So that** I can plan and track volunteer activities.

**Related Requirements:** [FR-SELFSERV-204](requirements-district-suite#fr-selfserv-204), [FR-SELFSERV-205](requirements-district-suite#fr-selfserv-205)

**Acceptance Criteria:**

- Given I access the calendar view, then I see my district's events in month/week/day format.
- Given I access the list view, then I can search, sort, and filter events by status and date.

### <a id="us-1103"></a>US-1103: District admin imports and manages volunteers

**As** a district administrator, **I want** to build and manage my district's volunteer pool, **So that** we have volunteers to recruit for our events.

**Related Requirements:** [FR-SELFSERV-301](requirements-district-suite#fr-selfserv-301), [FR-SELFSERV-302](requirements-district-suite#fr-selfserv-302), [FR-SELFSERV-303](requirements-district-suite#fr-selfserv-303)

**Related Use Cases:** [UC-16](use-cases#uc-16)

**Acceptance Criteria:**

- Given I am a district admin, when I add a volunteer, then they are saved to my district's database.
- Given I upload a CSV/Excel file, when I import it, then volunteers are created with validation and error reporting.
- Given volunteers exist, when I search by name/org/skills, then results are scoped to my district only.

### <a id="us-1104"></a>US-1104: District admin assigns volunteers to events

**As** a district administrator, **I want** to assign volunteers to my district's events, **So that** I can track who is participating.

**Related Requirements:** [FR-SELFSERV-304](requirements-district-suite#fr-selfserv-304)

**Related Use Cases:** [UC-15](use-cases#uc-15)

**Acceptance Criteria:**

- Given an event exists, when I assign a volunteer, then they appear on the event roster.
- Given a volunteer is assigned, then I can track their confirmation status (Invited, Confirmed, Declined).

### <a id="us-1105"></a>US-1105: District admin uses recruitment dashboard

**As** a district administrator, **I want** to use recruitment tools to fill volunteer gaps, **So that** I can proactively ensure events are staffed.

**Related Requirements:** [FR-SELFSERV-401](requirements-district-suite#fr-selfserv-401), [FR-SELFSERV-402](requirements-district-suite#fr-selfserv-402), [FR-SELFSERV-403](requirements-district-suite#fr-selfserv-403)

**Related Use Cases:** [UC-16](use-cases#uc-16)

**Acceptance Criteria:**

- Given I access the recruitment dashboard, then I see events needing volunteers with urgency indicators.
- Given I view volunteer recommendations, then they are ranked by fit (history, skills, location).
- Given I conduct outreach, when I log it, then the attempt and outcome are recorded.

### <a id="us-1106"></a>US-1106: Volunteer signs up via district form

**As** a volunteer, **I want** to sign up for district events via a public form, **So that** I can participate without creating an account.

**Related Requirements:** [FR-SELFSERV-404](requirements-district-suite#fr-selfserv-404), [FR-SELFSERV-405](requirements-district-suite#fr-selfserv-405)

**Acceptance Criteria:**

- Given I access a district's public signup form, when I submit my information, then I am registered for the event.
- Given successful signup, then I receive a confirmation email with calendar invite.
- Given I complete signup, then my information is added to the district's volunteer pool.

### <a id="us-1107"></a>US-1107: District user views PrepKC events

**As** a district user, **I want** to see PrepKC events happening at my schools (read-only), **So that** I am aware of all volunteer activities in my district.

**Related Requirements:** [FR-SELFSERV-501](requirements-district-suite#fr-selfserv-501), [FR-SELFSERV-502](requirements-district-suite#fr-selfserv-502), [FR-SELFSERV-503](requirements-district-suite#fr-selfserv-503)

**Related Use Cases:** [UC-18](use-cases#uc-18)

**Acceptance Criteria:**

- Given I view my district calendar, then PrepKC events at my schools appear with distinct styling.
- Given I view event details, then I can see PrepKC event information but cannot edit.
- Given I access statistics, then I see aggregate metrics for PrepKC events at my schools.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-12"></a>

## Epic 12: Public Event API (District Suite)

### <a id="us-1201"></a>US-1201: District embeds events on website

**As** a district IT staff member, **I want** to embed my district's event listings on our website, **So that** community members can see volunteer opportunities.

**Related Requirements:** [FR-API-101](requirements-district-suite#fr-api-101), [FR-API-102](requirements-district-suite#fr-api-102), [FR-API-108](requirements-district-suite#fr-api-108)

**Related Use Cases:** [UC-17](use-cases#uc-17)

**Acceptance Criteria:**

- Given I have my district's API key, when I call the events endpoint, then I receive published events in JSON format.
- Given I call the event detail endpoint, then I receive full event information including signup URL.
- Given I make API calls from my website, then CORS allows the requests.

### <a id="us-1202"></a>US-1202: District rotates API key

**As** a district administrator, **I want** to rotate my API key, **So that** I can maintain security if a key is compromised.

**Related Requirements:** [FR-API-106](requirements-district-suite#fr-api-106)

**Acceptance Criteria:**

- Given I access tenant settings, when I click "Rotate API Key", then a new key is generated.
- Given a new key is generated, then the old key immediately stops working.

[↑ Back to Quick Navigation](#quick-navigation)

---

<a id="epic-13"></a>

## Epic 13: Bug Reporting

### <a id="us-1301"></a>US-1301: Submit a bug report

**As** an authenticated user, **I want** to submit a bug report describing an issue I encountered, **So that** administrators can track and resolve problems.

**Related Requirements:** [FR-BUG-001](requirements-bug-reporting#fr-bug-001), [FR-BUG-002](requirements-bug-reporting#fr-bug-002), [FR-BUG-003](requirements-bug-reporting#fr-bug-003), [FR-BUG-004](requirements-bug-reporting#fr-bug-004), [FR-BUG-005](requirements-bug-reporting#fr-bug-005)

**Acceptance Criteria:**

- Given I am logged in, when I open the bug report form, then I can select a type (Bug, Data Error, Other), enter a description, and the page URL/title are captured automatically.
- Given I submit a report with a valid description, then the report is saved and I see a success confirmation.
- Given I submit a report with an empty description, then I see an error message and the report is not saved.
- Given I am not logged in, when I attempt to access the bug report form, then I am redirected to the login page.

### <a id="us-1302"></a>US-1302: Manage bug reports as admin

**As** an administrator, **I want** to view, filter, resolve, and delete bug reports, **So that** I can track and address user-reported issues.

**Related Requirements:** [FR-BUG-006](requirements-bug-reporting#fr-bug-006)–[FR-BUG-012](requirements-bug-reporting#fr-bug-012)

**Acceptance Criteria:**

- Given I am an admin, when I access the bug reports page, then I see all reports separated into open and resolved sections.
- Given I filter by status or type, then only matching reports are displayed.
- Given I search by keyword, then results match against description, page title, or URL.
- Given I resolve a report with notes, then it moves to the resolved section with my identity and timestamp recorded.
- Given I delete a report, then it is removed and an audit log entry is created.
- Given I am a non-admin user attempting to delete a report, then I receive a 403 Forbidden response.

### <a id="us-1303"></a>US-1303: System generates bug reports for failures

**As** the system, **I want** to auto-create bug reports for email delivery failures, **So that** administrators are alerted to operational issues without manual reporting.

**Related Requirements:** [FR-BUG-013](requirements-bug-reporting#fr-bug-013)

**Acceptance Criteria:**

- Given an email delivery fails, then the system creates a bug report with type=Other, containing the message ID, template, recipients, and error details.
- Given no system user exists, then the report uses the first admin user as the submitter.

[↑ Back to Quick Navigation](#quick-navigation)

---

*Last updated: February 2026*
*Version: 1.5*
