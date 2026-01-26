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
| [UC-1](#uc-1) | Create In-Person Event (Salesforce) | [US-101](user_stories#us-101) | [Test Pack 2](#test-pack-2) |
| [UC-2](#uc-2) | Sync and Publish Event to Website | [US-102](user_stories#us-102), [US-103](user_stories#us-103), [US-104](user_stories#us-104) | [Test Pack 2](#test-pack-2) |
| [UC-3](#uc-3) | Volunteer Signs Up (Public Website) | [US-201](user_stories#us-201), [US-203](user_stories#us-203) | [Test Pack 2](#test-pack-2) |
| [UC-4](#uc-4) | Create Virtual Event (Polaris) | [US-301](user_stories#us-301), [US-302](user_stories#us-302), [US-303](user_stories#us-303) | [Test Pack 3](#test-pack-3) |
| [UC-5](#uc-5) | Import Virtual Signup/Attendance | [US-304](user_stories#us-304) | [Test Pack 3](#test-pack-3) |
| [UC-6](#uc-6) | Volunteer Recruitment & Intelligent Matching | [US-401](user_stories#us-401), [US-406](user_stories#us-406) | [Test Pack 4](#test-pack-4) |
| [UC-7](#uc-7) | Reporting and Ad Hoc Queries | [US-701](user_stories#us-701) through [US-704](user_stories#us-704) | [Test Pack 6](#test-pack-6) |
| [UC-8](#uc-8) | District Progress Dashboard | [US-501](user_stories#us-501), [US-502](user_stories#us-502), [US-503](user_stories#us-503) | [Test Pack 1](#test-pack-1) |
| [UC-9](#uc-9) | Teacher Magic Link Self-Verification | [US-505](user_stories#us-505) | [Test Pack 1](#test-pack-1) |
| [UC-10](#uc-10) | Student Roster and Attendance | [US-601](user_stories#us-601), [US-602](user_stories#us-602), [US-603](user_stories#us-603) | [Test Pack 5](#test-pack-5) |
| [UC-11](#uc-11) | Identify and Fill Presenter Gaps | [US-307](user_stories#us-307), [US-303](user_stories#us-303) | [Test Pack 3](#test-pack-3) |
| [UC-12](#uc-12) | Generate Partner Reconciliation Report | [US-705](user_stories#us-705) | [Test Pack 6](#test-pack-6) |
| [UC-13](#uc-13) | Semester Progress Rollover | [US-509](user_stories#us-509) | [Test Pack 1](#test-pack-1) |

---

## <a id="uc-1"></a>UC-1: Create In-Person Event (Salesforce)

**Workflow:**
1. Staff logs into Salesforce
2. Creates event and enters details (date/time/location/needs/etc.)
3. Saves the event

**Related:**
- **Requirements**: [FR-INPERSON-101](requirements#fr-inperson-101)
- **User Stories**: [US-101](user_stories#us-101)
- **Test Coverage**: [Test Pack 2](#test-pack-2)
- **Contracts**: [Contract A](contract_a)

---

## <a id="uc-2"></a>UC-2: Sync and Publish Event to Website (VolunTeach)

**Workflow:**
1. Staff opens VolunTeach
2. Syncs events manually OR waits for hourly sync
3. Sets in-person page visibility toggle if event should appear on public page (Note: DIA events appear automatically regardless of toggle)
4. Links event to district if needed for district-specific page display

**Related:**
- **Requirements**: [FR-INPERSON-102](requirements#fr-inperson-102) through [FR-INPERSON-109](requirements#fr-inperson-109)
- **User Stories**: [US-102](user_stories#us-102), [US-103](user_stories#us-103), [US-104](user_stories#us-104)
- **Test Coverage**: [Test Pack 2](test_packs/test_pack_2)
- **Contracts**: [Contract A](contract_a)

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
- **Contracts**: [Contract B](contract_b)

---

## <a id="uc-4"></a>UC-4: Create Virtual Event (Polaris)

**Workflow:**
1. Staff logs into Polaris
2. Creates virtual event
3. Tags teachers (Salesforce-linked)
    - *Alternative Flow*: If teacher not found, creates new teacher locally via "Quick Create".
4. Tags presenters/volunteers (Salesforce-linked)
    - *Alternative Flow*: If presenter not found, creates new volunteer locally via "Quick Create".
5. Saves event

**Related:**
- **Requirements**: [FR-VIRTUAL-201](requirements#fr-virtual-201), [FR-VIRTUAL-202](requirements#fr-virtual-202), [FR-VIRTUAL-203](requirements#fr-virtual-203)
- **User Stories**: [US-301](user_stories#us-301), [US-302](user_stories#us-302), [US-303](user_stories#us-303)
- **Test Coverage**: [Test Pack 3](#test-pack-3)

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
- **Contracts**: [Contract D](contract_d)
- **Reference**: Import Playbooks

---

## <a id="uc-6"></a>UC-6: Volunteer Recruitment & Intelligent Matching (Polaris)

 **Workflow:**
 1. Staff searches volunteers by criteria (name/org/role/skills/career/local/virtual-only)
 2. **Optional**: Staff adds "Custom Keywords" (e.g., "Python, Data Science") to boost ranking
 3. System **automatically ranks** candidates by score (matching history, location, keywords)
 4. Staff reviews volunteer profile, why they matched (score breakdown), and communication history
 5. Conducts outreach via email (manual today)
 6. Communications are logged in Salesforce via Gmail add-on and surfaced into Polaris

 **Related:**
 - **Requirements**: [FR-RECRUIT-301](requirements#fr-recruit-301) through [FR-RECRUIT-311](requirements#fr-recruit-311)
 - **User Stories**: [US-401](user_stories#us-401), [US-402](user_stories#us-402), [US-404](user_stories#us-404), [US-406](user_stories#us-406)
 - **Test Coverage**: [Test Pack 4](#test-pack-4)

---

## <a id="uc-7"></a>UC-7: Reporting and Ad Hoc Queries (Polaris)

**Workflow:**
1. Leadership runs dashboards/reports: volunteer thank-you, organization participation, district/school impact
2. Exports data for grant/district reporting
3. Runs one-off queries (e.g., participation by a specific org)

**Related:**
- **Requirements**: [FR-REPORTING-401](requirements#fr-reporting-401) through [FR-REPORTING-406](requirements#fr-reporting-406)
- **User Stories**: [US-701](user_stories#us-701), [US-702](user_stories#us-702), [US-703](user_stories#us-703), [US-704](user_stories#us-704)
- **Test Coverage**: [Test Pack 6](#test-pack-6)

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
- **Test Coverage**: [Test Pack 1](#test-pack-1)

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
- **Test Coverage**: [Test Pack 1](#test-pack-1)

---

## <a id="uc-10"></a>UC-10: Student Roster and Attendance (Salesforce-driven)

> [!NOTE]
> **Current Implementation:** Student rostering and attendance is managed in **Salesforce** and synced to Polaris for reporting. Future enhancements may add additional attendance capture methods directly in Polaris.

**Workflow:**
1. Staff associates students to events (roster) **in Salesforce**
2. Staff updates attendance after event **in Salesforce**
3. Periodic manual import syncs student data to Polaris (see [Playbook D3: Student Import](import_playbook#d3-student-import))
4. Polaris reporting uses synced student attendance for district/school impact totals

**Virtual Events:** Virtual events do not track individual students. Student reach is estimated at **25 students per session** for reporting purposes.

**Related:**
- **Requirements**: [FR-STUDENT-601](requirements#fr-student-601) through [FR-STUDENT-605](requirements#fr-student-605)
- **User Stories**: [US-601](user_stories#us-601), [US-602](user_stories#us-602), [US-603](user_stories#us-603)
- **Test Coverage**: [Test Pack 5](#test-pack-5) (reporting), [Test Pack 7](test_packs/test_pack_7) (sync verification)

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

 ## <a id="uc-12"></a>UC-12: Generate Partner Reconciliation Report (KCTAA)

 **Workflow:**
 1. Staff logs into Polaris
 2. Navigates to Reports > KCTAA Match Report
 3. System loads configured partner name list from file
 4. System performs **Fuzzy Matches** against volunteer database
 5. Staff reviews matches (Exact vs Fuzzy vs None)
 6. Staff exports results to CSV to share with partner

 **Related:**
 - **Requirements**: [FR-REPORTING-407](requirements#fr-reporting-407), [FR-REPORTING-408](requirements#fr-reporting-408)
 - **User Stories**: [US-705](user_stories#us-705)
 - **Test Coverage**: [Test Pack 6](test_packs/test_pack_6)

---

 ## <a id="uc-13"></a>UC-13: Semester Progress Rollover (Polaris)

 **Workflow:**
 1. System detects semester boundary date (January 1 or June 30)
 2. System archives current semester's progress data (status, counts, dates per teacher)
 3. System resets all teacher progress statuses to "Not Started"
 4. System logs the operation with timestamp and affected counts
 5. District dashboards now show fresh semester data

 **Related:**
 - **Requirements**: [FR-DISTRICT-540](requirements#fr-district-540), [FR-DISTRICT-541](requirements#fr-district-541), [FR-DISTRICT-542](requirements#fr-district-542), [FR-DISTRICT-543](requirements#fr-district-543)
 - **User Stories**: [US-509](user_stories#us-509)
 - **Test Coverage**: [Test Pack 1](test_packs/test_pack_1)

---

*Last updated: January 2026*
*Version: 1.0*
