# User Stories

**Business intent organized by epic with acceptance criteria**

## Structure

Each story follows: **As [role], I want [capability], So that [benefit]**. Acceptance criteria define "done."

## Epic 1: In-Person Events (Salesforce → VolunTeach → Website)

### <a id="us-101"></a>US-101: Create an in-person event in Salesforce

**As** internal staff, **I want** to create an in-person event record in Salesforce, **So that** it can be synced to VolunTeach and published as needed.

**Related Requirements:** [FR-INPERSON-101](requirements#fr-inperson-101)

**Related Use Cases:** [UC-1](use_cases#uc-1)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#creating-an-event-in-salesforce)

**Acceptance Criteria:**

- Given I have Salesforce access, when I create an event with required fields, then the event is saved successfully.
- Given the event exists, when synced, then it contains key fields for website display (date/time, school, description/type, volunteer slots needed, location).

### <a id="us-102"></a>US-102: Sync events from Salesforce into VolunTeach

**As** internal staff, **I want** events to sync from Salesforce into VolunTeach automatically and on-demand, **So that** the website list stays current.

**Related Requirements:** [FR-INPERSON-102](requirements#fr-inperson-102), [FR-INPERSON-103](requirements#fr-inperson-103), [FR-INPERSON-123](requirements#fr-inperson-123)

**Related Use Cases:** [UC-2](use_cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#syncing-to-volunteach)

**Acceptance Criteria:**

- Given a new Salesforce event exists, when hourly sync runs, then the event appears in VolunTeach.
- Given a new Salesforce event exists, when I click "Sync now," then the event appears in VolunTeach.
- Given I run sync repeatedly without changes, then events are not duplicated (idempotent).

### <a id="us-103"></a>US-103: Control public in-person page visibility

**As** internal staff, **I want** to toggle whether an event appears on the public in-person events page, **So that** orientations/internal events don't show publicly.

**Related Requirements:** [FR-INPERSON-104](requirements#fr-inperson-104), [FR-INPERSON-105](requirements#fr-inperson-105)

**Related Use Cases:** [UC-2](use_cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#managing-visibility)

**Acceptance Criteria:**

- Given an event exists in VolunTeach, when I set "In-person page visibility" ON, then the event appears on the public page.
- Given an event exists, when I set that toggle OFF, then the event does not appear on the public page (unless it is a DIA event).
- Given an event is OFF, then it may still appear on district pages if district-linked.
- Given an event has "DIA" in the session type (Data in Action), then it appears on the public page automatically (regardless of the toggle), provided it has future slots available.

### <a id="us-104"></a>US-104: Link events to districts for district pages

**As** internal staff, **I want** to link an event to a district in VolunTeach, **So that** it appears on the district's website view.

**Related Requirements:** [FR-INPERSON-107](requirements#fr-inperson-107), [FR-INPERSON-109](requirements#fr-inperson-109)

**Related Use Cases:** [UC-2](use_cases#uc-2)

**User Guide:** [In-Person Event Management](user_guide/in_person_events#district-page-visibility)

**Acceptance Criteria:**

- Given an event exists, when I link it to District X, then it appears on District X's website page.
- Given the event is district-linked, then it appears on the district page regardless of the in-person page visibility toggle.
- Given I unlink an event from District X, then it no longer appears on District X's page.

### <a id="us-105"></a>US-105: Display correct event details on website

**As** a volunteer, **I want** to see key event information on the website listing, **So that** I can decide whether to sign up.

**Related Requirements:** [FR-INPERSON-106](requirements#fr-inperson-106)

**Acceptance Criteria:**

- Given an event is visible on a page, then it shows at minimum: volunteer slots needed, slots filled, date/time, school, description/type.
- Given a signup occurs, when I refresh the listing, then "slots filled" reflects the new signup.

## Epic 2: Public Volunteer Signup + Confirmation + Calendar Invite

### <a id="us-201"></a>US-201: Volunteer can sign up without an account

**As** a volunteer, **I want** to sign up for an event without creating an account, **So that** I can register quickly.

**Related Requirements:** [FR-SIGNUP-121](requirements#fr-signup-121), [FR-SIGNUP-122](requirements#fr-signup-122), [FR-SIGNUP-127](requirements#fr-signup-127)

**Related Use Cases:** [UC-3](use_cases#uc-3)

**User Guide:** [Public Signup Flow](#user-guide-public-signup)

**Acceptance Criteria:**

- Given I view an event signup form, when I submit valid required fields, then my signup is accepted and stored as a participation record.
- Given I submit with missing required fields, then I see clear validation errors and the signup is not stored.

### <a id="us-202"></a>US-202: Collect required signup fields (including dropdowns)

**As** internal staff, **I want** the signup form to collect standardized volunteer profile fields, **So that** we can recruit and report consistently.

**Related Requirements:** [FR-SIGNUP-126](requirements#fr-signup-126), [FR-SIGNUP-127](requirements#fr-signup-127)

**Acceptance Criteria:**

- Given the signup form, then it requires: First Name, Last Name, Email, Organization, Title, and all dropdown fields (Skills, Age Group, Education, Gender, Race/Ethnicity).
- Given a dropdown field, when a user submits an invalid value (tampered), then the submission is rejected.

### <a id="us-203"></a>US-203: Send confirmation email and calendar invite

**As** a volunteer, **I want** an email confirmation and calendar invite, **So that** I have the details saved and reminders.

**Related Requirements:** [FR-SIGNUP-123](requirements#fr-signup-123), [FR-SIGNUP-124](requirements#fr-signup-124), [FR-SIGNUP-125](requirements#fr-signup-125)

**Related Use Cases:** [UC-3](use_cases#uc-3)

**Acceptance Criteria:**

- Given a successful signup, then a confirmation email is sent to the submitted email.
- Given a successful signup, then a calendar invite is sent to the submitted email.
- Given the Salesforce event has location details, then the calendar invite includes the correct location/map details.

## Epic 3: Virtual Events in Polaris + Pathful Data Ingest

### <a id="us-301"></a>US-301: Create a virtual event in Polaris

**As** internal staff, **I want** to create and edit virtual events in Polaris, **So that** we can manage sessions without Google Sheets.

**Related Requirements:** [FR-VIRTUAL-201](requirements#fr-virtual-201)

**Related Use Cases:** [UC-4](use_cases#uc-4)

**User Guide:** [Virtual Event Management](user_guide/virtual_events#1-creating-virtual-events)

**Acceptance Criteria:**

- Given I create a virtual event with required fields, then it saves and is visible in the event list.
- Given I edit the event, then changes persist after reload.

### <a id="us-302"></a>US-302: Tag teachers via Salesforce-linked search

**As** internal staff, **I want** to attach teachers to a virtual event via search, **So that** reporting and progress tracking are linked to real teacher records.

**Related Requirements:** [FR-VIRTUAL-202](requirements#fr-virtual-202)

**Related Use Cases:** [UC-4](use_cases#uc-4)

**Acceptance Criteria:**

- Given a teacher exists in Salesforce, when I search and select the teacher, then the teacher is linked to the Polaris event.
- Given a Salesforce search failure, then Polaris shows an actionable error (not silent empty results).

### <a id="us-303"></a>US-303: Tag presenters to virtual events

**As** internal staff, **I want** to search for and tag presenters/volunteers to a virtual event using Salesforce-linked records, **So that** events have assigned presenters and recruitment tracking is accurate.

**Related Requirements:** [FR-VIRTUAL-203](requirements#fr-virtual-203)

**Related Use Cases:** [UC-4](use_cases#uc-4), [UC-11](use_cases#uc-11)

**Acceptance Criteria:**

- Given a volunteer/presenter exists in Salesforce, when I search and select them, then they are linked to the Polaris event as a presenter.
- Given I tag a presenter to an event, then the event no longer appears in the presenter recruitment view.
- Given a Salesforce search failure, then Polaris shows an actionable error (not silent empty results).

### <a id="us-304"></a>US-304: Import Pathful export into Polaris

**As** internal staff, **I want** to import Pathful signup/attendance data into Polaris, **So that** we can track attendance and teacher progress.

**Related Requirements:** [FR-VIRTUAL-206](requirements#fr-virtual-206)

**Related Use Cases:** [UC-5](use_cases#uc-5)

**Acceptance Criteria:**

- Given a Pathful export with valid rows, when I import it, then Polaris creates/updates participation records without duplicates.
- Given the same file is imported twice, then the import is idempotent (no duplicates; updates only).
- Given rows reference unknown teachers or events, then those rows are flagged as unmatched.
- Given required columns are missing, then the import fails with a clear missing-columns message.

### <a id="us-305"></a>US-305: Track local vs non-local volunteers

**As** internal staff, **I want** to track whether a virtual volunteer is local vs non-local, **So that** I can prioritize local volunteers for in-person opportunities and understand geographic reach.

**Related Requirements:** [FR-VIRTUAL-208](requirements#fr-virtual-208)

**Acceptance Criteria:**

- Given a volunteer participates in a virtual event, when I view their profile, then I can see whether they are marked as local or non-local.
- Given I filter volunteers by local status, then results correctly show only local or only non-local volunteers.
- Given a volunteer's local status is unknown, then the system displays "unknown" without error.

### <a id="us-306"></a>US-306: Import historical virtual data from Google Sheets

**As** internal staff, **I want** to import 2–4 years of historical virtual events from Google Sheets, **So that** our reporting and history are complete.

**Related Requirements:** [FR-VIRTUAL-204](requirements#fr-virtual-204)

**Acceptance Criteria:**

- Given a sheet where one event spans multiple lines, when imported, then the event is not duplicated and all teacher/presenter relationships are preserved.
- Given the same historical sheet is imported twice, then the import is idempotent (no duplicates).

### <a id="us-307"></a>US-307: View upcoming sessions needing presenters

**As** internal staff with global scope or admin privileges, **I want** to see a list of upcoming virtual events that don't have a presenter yet, **So that** I can proactively recruit volunteers and ensure all sessions are covered.

**Related Requirements:** [FR-VIRTUAL-210](requirements#fr-virtual-210), [FR-VIRTUAL-211](requirements#fr-virtual-211), [FR-VIRTUAL-212](requirements#fr-virtual-212), [FR-VIRTUAL-213](requirements#fr-virtual-213), [FR-VIRTUAL-214](requirements#fr-virtual-214), [FR-VIRTUAL-215](requirements#fr-virtual-215), [FR-VIRTUAL-216](requirements#fr-virtual-216), [FR-VIRTUAL-217](requirements#fr-virtual-217), [FR-VIRTUAL-218](requirements#fr-virtual-218), [FR-VIRTUAL-219](requirements#fr-virtual-219)

**Related Use Cases:** [UC-11](use_cases#uc-11)

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

## Epic 4: Volunteer Recruitment (Search + History + Communication Logs)

### <a id="us-401"></a>US-401: Search volunteers with advanced filters

**As** internal staff, **I want** to search volunteers by name/org/skills/career/local, **So that** I can recruit the right people quickly.

**Related Requirements:** [FR-RECRUIT-301](requirements#fr-recruit-301), [FR-RECRUIT-302](requirements#fr-recruit-302), [FR-RECRUIT-303](requirements#fr-recruit-303)

**Related Use Cases:** [UC-6](use_cases#uc-6)

**User Guide:** [Volunteer Recruitment](user_guide/volunteer_recruitment#1-volunteer-directory)

**Acceptance Criteria:**

- Given the volunteer directory, when I filter by organization, skills, career type, and local, then results match those criteria.
- Given I combine filters, then results reflect the intersection (not a union).
- Given a volunteer is missing an attribute, then searches do not error and results are consistent.

### <a id="us-402"></a>US-402: View volunteer participation history

**As** internal staff, **I want** to see a volunteer's participation history including most recent volunteer date, **So that** I can understand their engagement level and prioritize outreach.

**Related Requirements:** [FR-RECRUIT-304](requirements#fr-recruit-304)

**Related Use Cases:** [UC-6](use_cases#uc-6)

**Acceptance Criteria:**

- Given a volunteer has participated in events, when I view their profile, then I see a list of their participation history.
- Given the participation history, then it displays the most recent volunteer date.
- Given a volunteer has no participation, then the profile shows an appropriate message (not an error).

### <a id="us-403"></a>US-403: Record recruitment notes and outcomes

**As** internal staff, **I want** to record recruitment notes and outcomes in Polaris, **So that** I can track outreach efforts and outcomes for future reference.

**Related Requirements:** [FR-RECRUIT-306](requirements#fr-recruit-306)

**Acceptance Criteria:**

- Given I am viewing a volunteer profile, when I record a recruitment note, then the note is saved and associated with that volunteer.
- Given I record an outcome (e.g., "Accepted", "Declined", "Follow-up needed"), then the outcome is stored and visible in the volunteer's profile.
- Given I view a volunteer's recruitment history, then I can see all notes and outcomes in chronological order.

### <a id="us-404"></a>US-404: View communication history from Salesforce Gmail logging

**As** internal staff, **I want** to see communication history in Polaris sourced from Salesforce email logs, **So that** I know the latest outreach and context.

**Related Requirements:** [FR-RECRUIT-305](requirements#fr-recruit-305), [FR-RECRUIT-308](requirements#fr-recruit-308)

**Related Use Cases:** [UC-6](use_cases#uc-6)

**Acceptance Criteria:**

- Given emails are logged via Salesforce Gmail add-on, when comms sync runs, then those emails appear on the correct volunteer profile.
- Given new emails are logged, then after sync they appear in Polaris.

### <a id="us-405"></a>US-405: Distinguish "no comms" vs "sync failure"

**As** internal staff, **I want** Polaris to tell me whether comms are missing because none were logged vs sync failed, **So that** I can trust what I'm seeing.

**Related Requirements:** [FR-RECRUIT-309](requirements#fr-recruit-309)

**Acceptance Criteria:**

- Given the comms sync is failing, then comms panel shows an explicit sync failure status (not "no comms").

### <a id="us-406"></a>US-406: Rank volunteers by relevance (Intelligent Matching)

**As** internal staff, **I want** the system to rank volunteers by relevance (keywords, history, location), **So that** I don't have to sift through hundreds of records manually.

**Related Requirements:** [FR-RECRUIT-310](requirements#fr-recruit-310), [FR-RECRUIT-311](requirements#fr-recruit-311)

**Related Use Cases:** [UC-6](use_cases#uc-6)

**Acceptance Criteria:**

- Given I view recruitment search, then candidates are ranked by score (highest first).
- Given I add "Custom Keywords", then candidates matching those keywords get a higher score.
- The system explains *why* a candidate matched (e.g., "Matched on Title: Engineer").

## Epic 5: District Progress Dashboards + Teacher Magic Links

### <a id="us-501"></a>US-501: District viewer can see progress dashboard

**As** a district viewer, **I want** to see my district's progress dashboard, **So that** I can track school/teacher completion.

**Related Requirements:** [FR-DISTRICT-501](requirements#fr-district-501), [FR-DISTRICT-502](requirements#fr-district-502), [FR-DISTRICT-521](requirements#fr-district-521), [FR-DISTRICT-522](requirements#fr-district-522)

**Related Use Cases:** [UC-8](use_cases#uc-8)

**User Guide:** [District & Teacher Progress](user_guide/district_teacher_progress#1-district-dashboard-access)

**Acceptance Criteria:**

- Given I'm a District Viewer for District X, then I can access District X's dashboard and no other districts.
- Dashboard shows counts: schools, teachers, achieved/in-progress/not-started totals.

### <a id="us-502"></a>US-502: Drill down from district → school → teacher

**As** a district viewer, **I want** to drill down to schools and teachers, **So that** I can see who needs support.

**Related Requirements:** [FR-DISTRICT-503](requirements#fr-district-503)

**Related Use Cases:** [UC-8](use_cases#uc-8)

**Acceptance Criteria:**

- Given I click a school, then I see teacher-level rows for that school only.
- Each teacher displays status computed by the defined rules.

### <a id="us-503"></a>US-503: Define and compute progress statuses correctly

**As** internal staff and district viewers, **I want** the progress statuses to be computed consistently, **So that** reporting is trustworthy.

**Related Requirements:** [FR-DISTRICT-502](requirements#fr-district-502), [FR-DISTRICT-508](requirements#fr-district-508)

**Related Use Cases:** [UC-8](use_cases#uc-8)

**Acceptance Criteria:**

- Achieved = teacher completed ≥1 virtual session.
- In Progress = teacher has ≥1 future signup and 0 completed.
- Not Started = teacher has no signups and 0 completed.

### <a id="us-504"></a>US-504: Import teacher roster for progress tracking

**As** internal staff, **I want** to import a district-provided teacher roster, **So that** the system can track progress and enable magic-link access for teachers.

**Related Requirements:** [FR-DISTRICT-524](requirements#fr-district-524)

**Acceptance Criteria:**

- Given a district provides a teacher roster file (minimum: teacher name, email, grade; school if available), when I import it, then teachers are added to the system.
- Given the roster is imported, then it becomes the authoritative list for progress tracking.
- Given a teacher is in the roster, then they are eligible for magic-link access using their email.
- Given the same roster is imported again, then the import is idempotent (updates existing, adds new, handles removed teachers per policy).

### <a id="us-505"></a>US-505: Teacher can request magic link and verify data

**As** a teacher, **I want** to request a magic link using my email, **So that** I can view my progress and verify it.

**Related Requirements:** [FR-DISTRICT-505](requirements#fr-district-505), [FR-DISTRICT-506](requirements#fr-district-506), [FR-DISTRICT-507](requirements#fr-district-507), [FR-DISTRICT-508](requirements#fr-district-508), [FR-DISTRICT-521](requirements#fr-district-521), [FR-DISTRICT-523](requirements#fr-district-523)

**Related Use Cases:** [UC-9](use_cases#uc-9)

**User Guide:** [District & Teacher Progress](user_guide/district_teacher_progress#3-teacher-magic-links)

**Acceptance Criteria:**

- Given my email exists in the roster, when I request a link, then I receive an email with a link.
- The link shows only my data and cannot be modified to view other teachers.
- I can submit a flag/note if my data is incorrect.

## Epic 6: Student Roster + Attendance

### <a id="us-601"></a>US-601: Staff can roster students to events

**As** internal staff, **I want** to associate students with events, **So that** we can track reach and attendance.

**Related Requirements:** [FR-STUDENT-601](requirements#fr-student-601)

**Related Use Cases:** [UC-10](use_cases#uc-10)

**User Guide:** [Student Roster & Attendance](user_guide/student_management#1-rostering-students)

**Acceptance Criteria:**

- Given an event, when students are added to the roster, then student-event participation records exist.

### <a id="us-602"></a>US-602: Staff can mark student attendance

**As** internal staff, **I want** to record attendance for rostered students, **So that** reports reflect real participation.

**Related Requirements:** [FR-STUDENT-602](requirements#fr-student-602)

**Related Use Cases:** [UC-10](use_cases#uc-10)

**Acceptance Criteria:**

- Given a rostered student, when attendance is marked, then attendance status is saved and can be updated.

### <a id="us-603"></a>US-603: Reporting uses attendance to compute student reach

**As** leadership/internal staff, **I want** reports to compute unique students reached using attendance, **So that** we can report impact accurately.

**Related Requirements:** [FR-STUDENT-603](requirements#fr-student-603), [FR-STUDENT-604](requirements#fr-student-604)

**Related Use Cases:** [UC-10](use_cases#uc-10)

**Acceptance Criteria:**

- Given attended records, then unique students reached matches the defined computation rules for district/school.

## Epic 7: Reporting + Exports + Ad Hoc Queries

### <a id="us-701"></a>US-701: Volunteer thank-you reporting

**As** leadership/internal staff, **I want** volunteer thank-you dashboards, **So that** I can recognize top contributors.

**Related Requirements:** [FR-REPORTING-401](requirements#fr-reporting-401), [FR-REPORTING-406](requirements#fr-reporting-406)

**Related Use Cases:** [UC-7](use_cases#uc-7)

**User Guide:** [Volunteer Engagement Reports](reports/volunteer_engagement)

**Acceptance Criteria:**

- Dashboard ranks volunteers correctly by hours and/or events for a selected time range.
- Export matches the dashboard view.

### <a id="us-702"></a>US-702: Organization participation reporting

**As** leadership/internal staff, **I want** organization participation dashboards, **So that** I can recognize partner organizations.

**Related Requirements:** [FR-REPORTING-402](requirements#fr-reporting-402), [FR-REPORTING-406](requirements#fr-reporting-406)

**Related Use Cases:** [UC-7](use_cases#uc-7)

**User Guide:** [Impact & KPI Reports](reports/impact)

**Acceptance Criteria:**

- Dashboard shows correct totals per organization and unique organizations engaged.
- Export matches view.

### <a id="us-703"></a>US-703: District/school impact reporting

**As** leadership/internal staff, **I want** district/school impact dashboards, **So that** I can complete district reporting and grants.

**Related Requirements:** [FR-REPORTING-403](requirements#fr-reporting-403), [FR-REPORTING-404](requirements#fr-reporting-404), [FR-REPORTING-406](requirements#fr-reporting-406)

**Related Use Cases:** [UC-7](use_cases#uc-7)

**User Guide:** [Impact & KPI Reports](reports/impact)

**Acceptance Criteria:**

- Dashboard includes: unique students reached, unique volunteers reached, total volunteer hours, unique organizations engaged.
- Filters by district/school/event type/date range work correctly.
- Export matches filtered view.

### <a id="us-704"></a>US-704: Ad hoc reporting for one-off questions

**As** leadership/internal staff, **I want** to answer one-off questions with queries/reports, **So that** I can respond to partner and grant requests quickly.

**Related Requirements:** [FR-REPORTING-405](requirements#fr-reporting-405), [FR-REPORTING-406](requirements#fr-reporting-406)

**Related Use Cases:** [UC-7](use_cases#uc-7)

**User Guide:** [Ad Hoc Queries](reports/ad_hoc)

**Acceptance Criteria:**

- Given an organization filter, the query returns correct counts/lists.
- Export matches query results.

### <a id="us-705"></a>US-705: Reconcile external partner lists (e.g., KCTAA)

**As** internal staff, **I want** to match an external list of names against our database, **So that** I can report on partner member engagement even if they used different email addresses.

**Related Requirements:** [FR-REPORTING-407](requirements#fr-reporting-407), [FR-REPORTING-408](requirements#fr-reporting-408)

**Related Use Cases:** [UC-12](use_cases#uc-12)

**Related Use Cases:** [UC-12](use_cases#uc-12)

**User Guide:** [Partner Reconciliation](reports/partner_match)

**Acceptance Criteria:**

- Given I upload/select a partner list (CSV), then the system returns matches against the volunteer database.
- Given names are slightly different (e.g., "Rob" vs "Robert"), then the system identifies them as "Fuzzy Matches".
- I can export the reconciled list showing which partners are active volunteers.

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

---

*Last updated: January 2026*
*Version: 1.0*
