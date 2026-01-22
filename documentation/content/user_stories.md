# User Stories

**Business intent organized by epic with acceptance criteria**

## Structure

Each story follows: **As [role], I want [capability], So that [benefit]**. Acceptance criteria define "done."

## Epic 1: In-Person Events (Salesforce → VolunTeach → Website)

### <a id="us-101"></a>US-101: Create an in-person event in Salesforce

**As** internal staff, **I want** to create an in-person event record in Salesforce, **So that** it can be synced to VolunTeach and published as needed.

**Acceptance Criteria:**

- Given I have Salesforce access, when I create an event with required fields, then the event is saved successfully.
- Given the event exists, when synced, then it contains key fields for website display (date/time, school, description/type, volunteer slots needed, location).

### <a id="us-102"></a>US-102: Sync events from Salesforce into VolunTeach

**As** internal staff, **I want** events to sync from Salesforce into VolunTeach automatically and on-demand, **So that** the website list stays current.

**Acceptance Criteria:**

- Given a new Salesforce event exists, when hourly sync runs, then the event appears in VolunTeach.
- Given a new Salesforce event exists, when I click "Sync now," then the event appears in VolunTeach.
- Given I run sync repeatedly without changes, then events are not duplicated (idempotent).

### <a id="us-103"></a>US-103: Control public in-person page visibility

**As** internal staff, **I want** to toggle whether an event appears on the public in-person events page, **So that** orientations/internal events don't show publicly.

**Acceptance Criteria:**

- Given an event exists in VolunTeach, when I set "In-person page visibility" ON, then the event appears on the public page.
- Given an event exists, when I set that toggle OFF, then the event does not appear on the public page.
- Given an event is OFF, then it may still appear on district pages if district-linked.

### <a id="us-104"></a>US-104: Link events to districts for district pages

**As** internal staff, **I want** to link an event to a district in VolunTeach, **So that** it appears on the district's website view.

**Acceptance Criteria:**

- Given an event exists, when I link it to District X, then it appears on District X's website page.
- Given the event is district-linked, then it appears on the district page regardless of the in-person page visibility toggle.
- Given I unlink an event from District X, then it no longer appears on District X's page.

### <a id="us-105"></a>US-105: Display correct event details on website

**As** a volunteer, **I want** to see key event information on the website listing, **So that** I can decide whether to sign up.

**Acceptance Criteria:**

- Given an event is visible on a page, then it shows at minimum: volunteer slots needed, slots filled, date/time, school, description/type.
- Given a signup occurs, when I refresh the listing, then "slots filled" reflects the new signup.

## Epic 2: Public Volunteer Signup + Confirmation + Calendar Invite

### <a id="us-201"></a>US-201: Volunteer can sign up without an account

**As** a volunteer, **I want** to sign up for an event without creating an account, **So that** I can register quickly.

**Acceptance Criteria:**

- Given I view an event signup form, when I submit valid required fields, then my signup is accepted and stored as a participation record.
- Given I submit with missing required fields, then I see clear validation errors and the signup is not stored.

### <a id="us-202"></a>US-202: Collect required signup fields (including dropdowns)

**As** internal staff, **I want** the signup form to collect standardized volunteer profile fields, **So that** we can recruit and report consistently.

**Acceptance Criteria:**

- Given the signup form, then it requires: First Name, Last Name, Email, Organization, Title, and all dropdown fields (Skills, Age Group, Education, Gender, Race/Ethnicity).
- Given a dropdown field, when a user submits an invalid value (tampered), then the submission is rejected.

### <a id="us-203"></a>US-203: Send confirmation email and calendar invite

**As** a volunteer, **I want** an email confirmation and calendar invite, **So that** I have the details saved and reminders.

**Acceptance Criteria:**

- Given a successful signup, then a confirmation email is sent to the submitted email.
- Given a successful signup, then a calendar invite is sent to the submitted email.
- Given the Salesforce event has location details, then the calendar invite includes the correct location/map details.

## Epic 3: Virtual Events in Polaris + Pathful Data Ingest

### <a id="us-301"></a>US-301: Create a virtual event in Polaris

**As** internal staff, **I want** to create and edit virtual events in Polaris, **So that** we can manage sessions without Google Sheets.

**Acceptance Criteria:**

- Given I create a virtual event with required fields, then it saves and is visible in the event list.
- Given I edit the event, then changes persist after reload.

### <a id="us-302"></a>US-302: Tag teachers via Salesforce-linked search

**As** internal staff, **I want** to attach teachers to a virtual event via search, **So that** reporting and progress tracking are linked to real teacher records.

**Acceptance Criteria:**

- Given a teacher exists in Salesforce, when I search and select the teacher, then the teacher is linked to the Polaris event.
- Given a Salesforce search failure, then Polaris shows an actionable error (not silent empty results).

### <a id="us-304"></a>US-304: Import Pathful export into Polaris

**As** internal staff, **I want** to import Pathful signup/attendance data into Polaris, **So that** we can track attendance and teacher progress.

**Acceptance Criteria:**

- Given a Pathful export with valid rows, when I import it, then Polaris creates/updates participation records without duplicates.
- Given the same file is imported twice, then the import is idempotent (no duplicates; updates only).
- Given rows reference unknown teachers or events, then those rows are flagged as unmatched.
- Given required columns are missing, then the import fails with a clear missing-columns message.

### <a id="us-306"></a>US-306: Import historical virtual data from Google Sheets

**As** internal staff, **I want** to import 2–4 years of historical virtual events from Google Sheets, **So that** our reporting and history are complete.

**Acceptance Criteria:**

- Given a sheet where one event spans multiple lines, when imported, then the event is not duplicated and all teacher/presenter relationships are preserved.
- Given the same historical sheet is imported twice, then the import is idempotent (no duplicates).

### <a id="us-307"></a>US-307: View upcoming sessions needing presenters

**As** internal staff with global scope or admin privileges, **I want** to see a list of upcoming virtual events that don't have a presenter yet, **So that** I can proactively recruit volunteers and ensure all sessions are covered.

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

**Acceptance Criteria:**

- Given the volunteer directory, when I filter by organization, skills, career type, and local, then results match those criteria.
- Given I combine filters, then results reflect the intersection (not a union).
- Given a volunteer is missing an attribute, then searches do not error and results are consistent.

### <a id="us-404"></a>US-404: View communication history from Salesforce Gmail logging

**As** internal staff, **I want** to see communication history in Polaris sourced from Salesforce email logs, **So that** I know the latest outreach and context.

**Acceptance Criteria:**

- Given emails are logged via Salesforce Gmail add-on, when comms sync runs, then those emails appear on the correct volunteer profile.
- Given new emails are logged, then after sync they appear in Polaris.

### <a id="us-405"></a>US-405: Distinguish "no comms" vs "sync failure"

**As** internal staff, **I want** Polaris to tell me whether comms are missing because none were logged vs sync failed, **So that** I can trust what I'm seeing.

**Acceptance Criteria:**

- Given a volunteer has no logged emails, then comms panel shows "no communication history logged."
- Given the comms sync is failing, then comms panel shows an explicit sync failure status (not "no comms").

## Epic 5: District Progress Dashboards + Teacher Magic Links

### <a id="us-501"></a>US-501: District viewer can see progress dashboard

**As** a district viewer, **I want** to see my district's progress dashboard, **So that** I can track school/teacher completion.

**Acceptance Criteria:**

- Given I'm a District Viewer for District X, then I can access District X's dashboard and no other districts.
- Dashboard shows counts: schools, teachers, achieved/in-progress/not-started totals.

### <a id="us-502"></a>US-502: Drill down from district → school → teacher

**As** a district viewer, **I want** to drill down to schools and teachers, **So that** I can see who needs support.

**Acceptance Criteria:**

- Given I click a school, then I see teacher-level rows for that school only.
- Each teacher displays status computed by the defined rules.

### <a id="us-503"></a>US-503: Define and compute progress statuses correctly

**As** internal staff and district viewers, **I want** the progress statuses to be computed consistently, **So that** reporting is trustworthy.

**Acceptance Criteria:**

- Achieved = teacher completed ≥1 virtual session.
- In Progress = teacher has ≥1 future signup and 0 completed.
- Not Started = teacher has no signups and 0 completed.

### <a id="us-505"></a>US-505: Teacher can request magic link and verify data

**As** a teacher, **I want** to request a magic link using my email, **So that** I can view my progress and verify it.

**Acceptance Criteria:**

- Given my email exists in the roster, when I request a link, then I receive an email with a link.
- The link shows only my data and cannot be modified to view other teachers.
- I can submit a flag/note if my data is incorrect.

## Epic 6: Student Roster + Attendance

### <a id="us-601"></a>US-601: Staff can roster students to events

**As** internal staff, **I want** to associate students with events, **So that** we can track reach and attendance.

**Acceptance Criteria:**

- Given an event, when students are added to the roster, then student-event participation records exist.

### <a id="us-602"></a>US-602: Staff can mark student attendance

**As** internal staff, **I want** to record attendance for rostered students, **So that** reports reflect real participation.

**Acceptance Criteria:**

- Given a rostered student, when attendance is marked, then attendance status is saved and can be updated.

### <a id="us-603"></a>US-603: Reporting uses attendance to compute student reach

**As** leadership/internal staff, **I want** reports to compute unique students reached using attendance, **So that** we can report impact accurately.

**Acceptance Criteria:**

- Given attended records, then unique students reached matches the defined computation rules for district/school.

## Epic 7: Reporting + Exports + Ad Hoc Queries

### <a id="us-701"></a>US-701: Volunteer thank-you reporting

**As** leadership/internal staff, **I want** volunteer thank-you dashboards, **So that** I can recognize top contributors.

**Acceptance Criteria:**

- Dashboard ranks volunteers correctly by hours and/or events for a selected time range.
- Export matches the dashboard view.

### <a id="us-702"></a>US-702: Organization participation reporting

**As** leadership/internal staff, **I want** organization participation dashboards, **So that** I can recognize partner organizations.

**Acceptance Criteria:**

- Dashboard shows correct totals per organization and unique organizations engaged.
- Export matches view.

### <a id="us-703"></a>US-703: District/school impact reporting

**As** leadership/internal staff, **I want** district/school impact dashboards, **So that** I can complete district reporting and grants.

**Acceptance Criteria:**

- Dashboard includes: unique students reached, unique volunteers reached, total volunteer hours, unique organizations engaged.
- Filters by district/school/event type/date range work correctly.
- Export matches filtered view.

### <a id="us-704"></a>US-704: Ad hoc reporting for one-off questions

**As** leadership/internal staff, **I want** to answer one-off questions with queries/reports, **So that** I can respond to partner and grant requests quickly.

**Acceptance Criteria:**

- Given an organization filter, the query returns correct counts/lists.
- Export matches query results.

---

*Last updated: January 2026*
*Version: 1.0*
