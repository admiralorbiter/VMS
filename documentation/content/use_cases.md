# Use Cases

**End-to-end workflows for key system functions**

## Overview

Use cases describe complete workflows that span multiple systems and features. They show **how** users accomplish tasks step-by-step, complementing user stories (which describe **what** users need and **why**).

**Reference:**
- Detailed test cases in [Test Packs](test_packs/index)
- Integration specs in Contracts
- Related [User Stories](user_stories) and [Functional Requirements](requirements)

## Use Case Index

| ID | Title | Related User Stories | Test Coverage |
|----|-------|---------------------|---------------|
| [UC-1](#uc-1) | Create In-Person Event (Salesforce) | [US-101](user_stories#us-101) | [Test Pack 2](test_packs/test_pack_2) |
| [UC-2](#uc-2) | Sync and Publish Event to Website | [US-102](user_stories#us-102), [US-103](user_stories#us-103), [US-104](user_stories#us-104) | [Test Pack 2](test_packs/test_pack_2) |
| [UC-3](#uc-3) | Volunteer Signs Up (Public Website) | [US-201](user_stories#us-201), [US-203](user_stories#us-203) | [Test Pack 2](test_packs/test_pack_2) |
| [UC-4](#uc-4) | Create Virtual Event (Polaris) | [US-301](user_stories#us-301), [US-302](user_stories#us-302), [US-303](user_stories#us-303) | [Test Pack 3](test_packs/test_pack_3) |
| [UC-5](#uc-5) | Import Virtual Signup/Attendance | [US-304](user_stories#us-304) | [Test Pack 3](test_packs/test_pack_3) |
| [UC-6](#uc-6) | Volunteer Recruitment (Polaris) | [US-401](user_stories#us-401), [US-402](user_stories#us-402), [US-404](user_stories#us-404) | [Test Pack 4](test_packs/test_pack_4) |
| [UC-7](#uc-7) | Reporting and Ad Hoc Queries | [US-701](user_stories#us-701), [US-702](user_stories#us-702), [US-703](user_stories#us-703), [US-704](user_stories#us-704) | [Test Pack 6](test_packs/test_pack_6) |
| [UC-8](#uc-8) | District Progress Dashboard | [US-501](user_stories#us-501), [US-502](user_stories#us-502), [US-503](user_stories#us-503) | [Test Pack 1](test_packs/test_pack_1) |
| [UC-9](#uc-9) | Teacher Magic Link Self-Verification | [US-505](user_stories#us-505) | [Test Pack 1](test_packs/test_pack_1) |
| [UC-10](#uc-10) | Student Roster and Attendance | [US-601](user_stories#us-601), [US-602](user_stories#us-602), [US-603](user_stories#us-603) | [Test Pack 5](test_packs/test_pack_5) |
| [UC-11](#uc-11) | Identify and Fill Presenter Gaps | [US-307](user_stories#us-307), [US-303](user_stories#us-303) | [Test Pack 3](test_packs/test_pack_3) |

---

## <a id="uc-1"></a>UC-1: Create In-Person Event (Salesforce)

**Workflow:**
1. Staff logs into Salesforce
2. Creates event and enters details (date/time/location/needs/etc.)
3. Saves the event

**Related:**
- **Requirements**: [FR-INPERSON-101](requirements#fr-inperson-101)
- **User Stories**: [US-101](user_stories#us-101)
- **Test Coverage**: [Test Pack 2](test_packs/test_pack_2)
- **Contracts**: Contract A

---

## <a id="uc-2"></a>UC-2: Sync and Publish Event to Website (VolunTeach)

**Workflow:**
1. Staff opens VolunTeach
2. Syncs events manually OR waits for hourly sync
3. Sets in-person page visibility toggle if event should appear on public page
4. Links event to district if needed for district-specific page display

**Related:**
- **Requirements**: [FR-INPERSON-102](requirements#fr-inperson-102) through [FR-INPERSON-109](requirements#fr-inperson-109)
- **User Stories**: [US-102](user_stories#us-102), [US-103](user_stories#us-103), [US-104](user_stories#us-104)
- **Test Coverage**: [Test Pack 2](test_packs/test_pack_2)

---

## <a id="uc-3"></a>UC-3: Volunteer Signs Up (Public Website)

**Workflow:**
1. Volunteer finds event on in-person page or district page
2. Submits signup form (no login; repeats info each time)
3. Receives confirmation email
4. Receives calendar invite (includes location/map details from Salesforce)

**Related:**
- **Requirements**: [FR-SIGNUP-121](requirements#fr-signup-121) through [FR-SIGNUP-127](requirements#fr-signup-127)
- **User Stories**: [US-201](user_stories#us-201), [US-203](user_stories#us-203)
- **Test Coverage**: [Test Pack 2](test_packs/test_pack_2)
- **Contracts**: Contract B

---

## <a id="uc-4"></a>UC-4: Create Virtual Event (Polaris)

**Workflow:**
1. Staff logs into Polaris
2. Creates virtual event
3. Tags teachers (Salesforce-linked)
4. Tags presenters/volunteers (Salesforce-linked)
5. Saves event

**Related:**
- **Requirements**: [FR-VIRTUAL-201](requirements#fr-virtual-201), [FR-VIRTUAL-202](requirements#fr-virtual-202), [FR-VIRTUAL-203](requirements#fr-virtual-203)
- **User Stories**: [US-301](user_stories#us-301), [US-302](user_stories#us-302), [US-303](user_stories#us-303)
- **Test Coverage**: [Test Pack 3](test_packs/test_pack_3)

---

## <a id="uc-5"></a>UC-5: Import Virtual Signup/Attendance (Pathful → Polaris)

**Workflow:**
1. Export is obtained from Pathful (manual today; automated later)
2. Polaris imports data and updates attendance/progress tracking fields
3. District/teacher dashboards update accordingly

**Related:**
- **Requirements**: [FR-VIRTUAL-206](requirements#fr-virtual-206)
- **User Stories**: [US-304](user_stories#us-304)
- **Test Coverage**: [Test Pack 3](test_packs/test_pack_3)
- **Contracts**: Contract D
- **Reference**: Import Playbooks

---

## <a id="uc-6"></a>UC-6: Volunteer Recruitment (Polaris)

**Workflow:**
1. Staff searches volunteers by criteria (name/org/role/skills/career/local/virtual-only)
2. Reviews volunteer participation and communication history
3. Conducts outreach via email (manual today)
4. Communications are logged in Salesforce via Gmail add-on and surfaced into Polaris

**Related:**
- **Requirements**: [FR-RECRUIT-301](requirements#fr-recruit-301) through [FR-RECRUIT-309](requirements#fr-recruit-309)
- **User Stories**: [US-401](user_stories#us-401), [US-402](user_stories#us-402), [US-404](user_stories#us-404)
- **Test Coverage**: [Test Pack 4](test_packs/test_pack_4)

---

## <a id="uc-7"></a>UC-7: Reporting and Ad Hoc Queries (Polaris)

**Workflow:**
1. Leadership runs dashboards/reports: volunteer thank-you, organization participation, district/school impact
2. Exports data for grant/district reporting
3. Runs one-off queries (e.g., participation by a specific org)

**Related:**
- **Requirements**: [FR-REPORTING-401](requirements#fr-reporting-401) through [FR-REPORTING-406](requirements#fr-reporting-406)
- **User Stories**: [US-701](user_stories#us-701), [US-702](user_stories#us-702), [US-703](user_stories#us-703), [US-704](user_stories#us-704)
- **Test Coverage**: [Test Pack 6](test_packs/test_pack_6)

---

## <a id="uc-8"></a>UC-8: District Progress Dashboard (Polaris)

**Workflow:**
1. District Viewer logs in
2. Sees district summary: schools count, teachers count, overall goal progress
3. Sees breakdown of achieved/in-progress/not-started
4. Drills into school → teacher-level detail

**Related:**
- **Requirements**: [FR-DISTRICT-501](requirements#fr-district-501), [FR-DISTRICT-502](requirements#fr-district-502), [FR-DISTRICT-503](requirements#fr-district-503)
- **User Stories**: [US-501](user_stories#us-501), [US-502](user_stories#us-502), [US-503](user_stories#us-503)
- **Test Coverage**: [Test Pack 1](test_packs/test_pack_1)

---

## <a id="uc-9"></a>UC-9: Teacher Magic Link Self-Verification

**Workflow:**
1. Teacher requests magic link by entering email
2. Receives email with link
3. Opens link and views their progress/data
4. Flags incorrect data and submits a note back to internal staff

**Related:**
- **Requirements**: [FR-DISTRICT-505](requirements#fr-district-505), [FR-DISTRICT-506](requirements#fr-district-506), [FR-DISTRICT-507](requirements#fr-district-507)
- **User Stories**: [US-505](user_stories#us-505)
- **Test Coverage**: [Test Pack 1](test_packs/test_pack_1)

---

## <a id="uc-10"></a>UC-10: Student Roster and Attendance (Salesforce-driven)

**Workflow:**
1. Staff associates students to events (roster)
2. Staff updates attendance after event
3. Polaris reporting uses student attendance for district/school impact totals

**Related:**
- **Requirements**: [FR-STUDENT-601](requirements#fr-student-601) through [FR-STUDENT-604](requirements#fr-student-604)
- **User Stories**: [US-601](user_stories#us-601), [US-602](user_stories#us-602), [US-603](user_stories#us-603)
- **Test Coverage**: [Test Pack 5](test_packs/test_pack_5)

---

## <a id="uc-11"></a>UC-11: Identify and Fill Presenter Gaps (Polaris)

**Workflow:**
1. Staff logs into Polaris with Admin role or global scope
2. Navigates to Virtual Session Usage Report (`/virtual/usage`)
3. Clicks "Presenter Recruitment" button to access recruitment view (`/virtual/usage/recruitment`)
4. Reviews upcoming virtual events without presenters, sorted by urgency (earliest/red badges first)
5. Applies filters as needed: academic year, date range, district, school, or text search
6. Identifies urgent events (red badges = ≤7 days until event)
7. Clicks "Find Volunteers" button to access volunteer recruitment search
8. Searches for suitable volunteer by skills, availability, location, etc.
9. Returns to recruitment view and clicks event row or "Edit Event" button
10. On event details page, assigns volunteer as presenter (creates EventParticipation with `participant_type='Presenter'`)
11. Returns to recruitment view and confirms event no longer appears in list
12. Repeats for remaining events or clicks "Back to Usage Report"

**Related:**
- **Requirements**: [FR-VIRTUAL-210](requirements#fr-virtual-210) through [FR-VIRTUAL-219](requirements#fr-virtual-219)
- **User Stories**: [US-307](user_stories#us-307), [US-303](user_stories#us-303)
- **Test Coverage**: [Test Pack 3](test_packs/test_pack_3)
- **Related Use Cases**: [UC-4](use_cases#uc-4) (Create Virtual Event), [UC-6](use_cases#uc-6) (Volunteer Recruitment)

---

*Last updated: January 2026*
*Version: 1.0*
