# Functional Requirements

**Numbered requirements referenced by test packs**

## Functional Requirement ID Policy

Functional requirements use **stable, namespaced IDs** that never change once assigned:

- **Format**: `FR-{DOMAIN}-{NNN}` where:
  - `{DOMAIN}` is a domain prefix (e.g., `INPERSON`, `SIGNUP`, `VIRTUAL`)
  - `{NNN}` is a 3-digit number (001-999)
- **Anchors**: Lowercase with hyphens: `fr-{domain}-{nnn}` (e.g., `fr-inperson-101`)
- **Stability**: IDs are never reused or renumbered. Gaps in numbering are allowed.
- **Adding new requirements**: Choose the appropriate domain and assign the next available number within that domain.

**Domain Prefixes:**
- `INPERSON` - In-person event management (7.1)
- `SIGNUP` - Public volunteer signup (7.2)
- `VIRTUAL` - Virtual events (7.3)
- `RECRUIT` - Volunteer search and recruitment (7.4)
- `REPORTING` - Reporting and dashboards (7.5)
- `DISTRICT` - District and teacher progress (7.6)
- `STUDENT` - Student roster and attendance (7.7)

## Traceability

Each **FR-xxx** is referenced by test cases in **Test Packs 1–6**. User stories with acceptance criteria in **[User Stories](user_stories)**.

## 7.1 In-Person Event Management

**Salesforce + VolunTeach + Website**

> [!INFO]
> **System Locations**
> - **Salesforce**: [https://prep-kc.my.salesforce.com/](https://prep-kc.my.salesforce.com/) (core CRM system for data entry and event management)
> - **VolunTeach**: [https://voluntold-prepkc.pythonanywhere.com/dashboard](https://voluntold-prepkc.pythonanywhere.com/dashboard) (admin interface for event management and sync controls)
> - **Public Website**: [https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html) (volunteer hub with in-person events signup page)

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-101"></a>**FR-INPERSON-101** | Staff shall create and maintain in-person event records in Salesforce. | [TC-100](test-pack-2#tc-100) | [US-101](user_stories#us-101) |
| <a id="fr-inperson-102"></a>**FR-INPERSON-102** | VolunTeach shall sync in-person events from Salesforce at least once per hour via automated scheduled sync. The system also supports scheduled daily batch imports that process events, volunteer participations, and student participations. | [TC-101](test-pack-2#tc-101), [TC-103](test-pack-2#tc-103) | [US-102](user_stories#us-102) |
| <a id="fr-inperson-103"></a>**FR-INPERSON-103** | VolunTeach shall provide a manual "sync now" action for immediate synchronization. Manual sync operations shall support large datasets with configurable batch sizes and progress indicators for use cases such as reports and historical data imports. | [TC-100](test-pack-2#tc-100), [TC-102](test-pack-2#tc-102) | [US-102](user_stories#us-102) |
| <a id="fr-inperson-104"></a>**FR-INPERSON-104** | VolunTeach shall allow staff to control whether an event appears on the public in-person events page via a visibility toggle. | [TC-110](test-pack-2#tc-110), [TC-111](test-pack-2#tc-111) | [US-103](user_stories#us-103) |
| <a id="fr-inperson-105"></a>**FR-INPERSON-105** | The system shall support events that are not displayed on the public in-person page (e.g., orientations). | [TC-112](test-pack-2#tc-112) | [US-103](user_stories#us-103) |
| <a id="fr-inperson-106"></a>**FR-INPERSON-106** | The website shall display for each event at minimum: volunteer slots needed, slots filled, date/time, school, and event description/type. | [TC-120](test-pack-2#tc-120), [TC-121](test-pack-2#tc-121) | [US-105](user_stories#us-105) |
| <a id="fr-inperson-107"></a>**FR-INPERSON-107** | VolunTeach shall allow staff to link events to one or more districts for district-specific website pages. | [TC-113](test-pack-2#tc-113), [TC-114](test-pack-2#tc-114) | [US-104](user_stories#us-104) |
| <a id="fr-inperson-109"></a>**FR-INPERSON-109** | Any event linked to a district shall appear on that district's website page regardless of the in-person-page visibility toggle. | [TC-113](test-pack-2#tc-113), [TC-115](test-pack-2#tc-115) | [US-104](user_stories#us-104) |

### Scheduled Imports

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-108"></a>**FR-INPERSON-108** | The system shall support scheduled daily imports of in-person events from Salesforce, including events, volunteer participations, and student participations. | [TC-160](test-pack-2#tc-160) | *Technical requirement* |
| <a id="fr-inperson-110"></a>**FR-INPERSON-110** | Daily imports shall process events in batches to handle large datasets without exceeding API limits. | [TC-161](test-pack-2#tc-161) | *Technical requirement* |
| <a id="fr-inperson-111"></a>**FR-INPERSON-111** | The system shall provide visibility into daily import status, success/failure counts, and error details. | [TC-162](test-pack-2#tc-162) | *Technical requirement* |

### Participation Sync

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-112"></a>**FR-INPERSON-112** | The system shall sync student participation data from Salesforce for in-person events, creating EventStudentParticipation records. | [TC-170](test-pack-2#tc-170) | *Technical requirement* |
| <a id="fr-inperson-113"></a>**FR-INPERSON-113** | Student participation sync shall update attendance status and delivery hours from Salesforce. | [TC-171](test-pack-2#tc-171) | *Technical requirement* |
| <a id="fr-inperson-114"></a>**FR-INPERSON-114** | The system shall sync volunteer participation data from Salesforce for in-person events, including status, delivery hours, and participant attributes. | [TC-172](test-pack-2#tc-172) | *Technical requirement* |
| <a id="fr-inperson-115"></a>**FR-INPERSON-115** | Volunteer participation sync shall handle batch processing for large event sets (e.g., 50 events per batch). | [TC-173](test-pack-2#tc-173) | *Technical requirement* |

### Unaffiliated Events

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-116"></a>**FR-INPERSON-116** | The system shall identify and sync events from Salesforce that are missing School, District, or Parent Account associations. | [TC-180](test-pack-2#tc-180) | *Technical requirement* |
| <a id="fr-inperson-117"></a>**FR-INPERSON-117** | For unaffiliated events, the system shall attempt to associate events with districts based on participating students. | [TC-181](test-pack-2#tc-181) | *Technical requirement* |
| <a id="fr-inperson-118"></a>**FR-INPERSON-118** | Unaffiliated event sync shall update both event data and associated volunteer/student participation records. | [TC-182](test-pack-2#tc-182) | *Technical requirement* |

### Status Management

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-119"></a>**FR-INPERSON-119** | When syncing events, the system shall update event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) from Salesforce. | [TC-190](test-pack-2#tc-190) | *Technical requirement* |
| <a id="fr-inperson-120"></a>**FR-INPERSON-120** | The system shall preserve cancellation reasons when events are cancelled in Salesforce. | [TC-191](test-pack-2#tc-191) | *Technical requirement* |
| <a id="fr-inperson-121"></a>**FR-INPERSON-121** | Status changes shall be reflected in VolunTeach and on public website within the sync cycle. | [TC-192](test-pack-2#tc-192) | *Technical requirement* |

### Error Handling and Monitoring

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-122"></a>**FR-INPERSON-122** | The system shall detect and report sync failures with detailed error messages (not silent failures). | [TC-104](test-pack-2#tc-104) | *Technical requirement* |
| <a id="fr-inperson-123"></a>**FR-INPERSON-123** | Sync operations shall be idempotent (no duplicates on re-sync). | [TC-102](test-pack-2#tc-102) | [US-102](user_stories#us-102) |
| <a id="fr-inperson-124"></a>**FR-INPERSON-124** | The system shall distinguish between "no events to sync" and "sync failure" for monitoring purposes. | [TC-200](test-pack-2#tc-200) | *Technical requirement* |
| <a id="fr-inperson-125"></a>**FR-INPERSON-125** | Failed sync operations shall be logged with timestamps, error details, and affected record counts. | [TC-201](test-pack-2#tc-201) | *Technical requirement* |

### Historical Data Import

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-126"></a>**FR-INPERSON-126** | The system shall support importing historical in-person event data from Salesforce (e.g., 2–4 years of past events). | [TC-210](test-pack-2#tc-210) | *Technical requirement* |
| <a id="fr-inperson-127"></a>**FR-INPERSON-127** | Historical import shall preserve event-participant relationships and maintain data integrity. | [TC-211](test-pack-2#tc-211) | *Technical requirement* |

### Manual Operations

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-128"></a>**FR-INPERSON-128** | For large datasets, the system shall provide manual sync operations that process events in configurable batch sizes. | [TC-212](test-pack-2#tc-212) | *Technical requirement* |
| <a id="fr-inperson-129"></a>**FR-INPERSON-129** | Manual sync operations shall provide progress indicators and allow cancellation/resumption. | [TC-213](test-pack-2#tc-213) | *Technical requirement* |

### Data Completeness Visibility

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-130"></a>**FR-INPERSON-130** | The system shall distinguish "no events to sync" from "event sync failure" (visibility into data completeness). | [TC-200](test-pack-2#tc-200) | *Technical requirement* |
| <a id="fr-inperson-131"></a>**FR-INPERSON-131** | Sync status indicators shall show last successful sync time, record counts, and any pending errors. | [TC-220](test-pack-2#tc-220) | *Technical requirement* |

### Reporting Integration

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-inperson-132"></a>**FR-INPERSON-132** | Event sync operations shall trigger cache invalidation for reports that depend on event data. | [TC-221](test-pack-2#tc-221) | *Technical requirement* |
| <a id="fr-inperson-133"></a>**FR-INPERSON-133** | Manual cache refresh for event-based reports shall be available when automated sync is insufficient for large datasets. | [TC-222](test-pack-2#tc-222) | *Technical requirement* |

## 7.2 Public Volunteer Signup

**Website**

> [!INFO]
> **System Location**
> - **Public Website Volunteer Hub**: [https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)
>
> The volunteer hub provides access to signup pages for:
> - In-person events
> - Data in Action (DIA) events
> - Virtual events
> - Other volunteer opportunities

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-signup-121"></a>**FR-SIGNUP-121** | The website shall allow volunteers to sign up for an event via a public form without authentication. | [TC-130](#tc-130)–[TC-140](#tc-140) | [US-201](user_stories#us-201) |
| <a id="fr-signup-122"></a>**FR-SIGNUP-122** | Each signup shall create a participation record associated with the event and the volunteer identity (email-based at minimum). | [TC-140](#tc-140), [TC-142](#tc-142) | [US-201](user_stories#us-201) |
| <a id="fr-signup-123"></a>**FR-SIGNUP-123** | The system shall send a confirmation email upon successful signup. | [TC-150](#tc-150) | [US-203](user_stories#us-203) |
| <a id="fr-signup-124"></a>**FR-SIGNUP-124** | The system shall send a calendar invite upon successful signup. | [TC-151](#tc-151) | [US-203](user_stories#us-203) |
| <a id="fr-signup-125"></a>**FR-SIGNUP-125** | The calendar invite shall include event details and location/map information derived from the Salesforce event record. | [TC-152](#tc-152) | [US-203](user_stories#us-203) |
| <a id="fr-signup-126"></a>**FR-SIGNUP-126** | The signup form shall collect: First Name, Last Name, Email, Organization, Title, Volunteer Skills (dropdown), Age Group (dropdown), Highest Education Attainment (dropdown), Gender (dropdown), Race/Ethnicity (dropdown). | [TC-130](#tc-130)–[TC-132](#tc-132) | [US-202](user_stories#us-202) |
| <a id="fr-signup-127"></a>**FR-SIGNUP-127** | The system shall store the submitted signup attributes for use in reporting, recruitment search, and volunteer profiles. | [TC-141](#tc-141) | [US-201](user_stories#us-201), [US-202](user_stories#us-202) |

## 7.3 Virtual Events

**Polaris + Pathful**

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-virtual-201"></a>**FR-VIRTUAL-201** | Polaris shall allow staff to create and maintain virtual event records. | [TC-200](#tc-200), [TC-201](#tc-201) | [US-301](user_stories#us-301) |
| <a id="fr-virtual-202"></a>**FR-VIRTUAL-202** | Polaris shall allow staff to search for and tag teachers using Salesforce-linked teacher records. | [TC-202](#tc-202), [TC-204](#tc-204) | [US-302](user_stories#us-302) |
| <a id="fr-virtual-203"></a>**FR-VIRTUAL-203** | Polaris shall allow staff to search for and tag presenters/volunteers using Salesforce-linked records. | [TC-203](#tc-203), [TC-204](#tc-204) | [US-303](user_stories#us-303) |
| <a id="fr-virtual-204"></a>**FR-VIRTUAL-204** | The system shall support importing 2–4 years of historical virtual event data from Google Sheets, preserving event–teacher relationships and multi-line mapping. | [TC-270](#tc-270)–[TC-275](#tc-275) | [US-306](user_stories#us-306) |
| <a id="fr-virtual-205"></a>**FR-VIRTUAL-205** | The system shall treat Pathful as the current source for virtual event signup and reminder emails. | Context only | *Context only* |
| <a id="fr-virtual-206"></a>**FR-VIRTUAL-206** | Polaris shall ingest Pathful export data to update virtual attendance and participation tracking. | [TC-250](#tc-250)–[TC-260](#tc-260) | [US-304](user_stories#us-304) |
| <a id="fr-virtual-207"></a>**FR-VIRTUAL-207** | The system should support automation to pull Pathful exports and load them into Polaris. *Near-term* | [TC-280](#tc-280) | *Near-term* |
| <a id="fr-virtual-208"></a>**FR-VIRTUAL-208** | The system shall track whether a virtual volunteer is local vs non-local. | [TC-230](#tc-230)–[TC-232](#tc-232) | *Missing: US-305* |
| <a id="fr-virtual-209"></a>**FR-VIRTUAL-209** | The system should support sending automated communications that connect local volunteers. *Near-term* | [TC-281](#tc-281) | *Near-term* |
| <a id="fr-virtual-210"></a>**FR-VIRTUAL-210** | Polaris shall provide a view listing upcoming virtual events that do not have a presenter assigned. | [TC-290](#tc-290)–[TC-299](#tc-299) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-211"></a>**FR-VIRTUAL-211** | The presenter recruitment view shall filter to show only future events (start_datetime > current date/time). | [TC-291](#tc-291) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-212"></a>**FR-VIRTUAL-212** | The presenter recruitment view shall support filtering by date range, school, district, and event type. | [TC-292](#tc-292)–[TC-295](#tc-295) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-213"></a>**FR-VIRTUAL-213** | The presenter recruitment view shall display for each event: title, date/time, school/district, teacher count, and days until event. | [TC-298](#tc-298) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-214"></a>**FR-VIRTUAL-214** | Staff shall be able to navigate directly from a presenter-needed event to the volunteer search/recruitment workflow. | [TC-299](#tc-299) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-215"></a>**FR-VIRTUAL-215** | Once a presenter is tagged to an event, that event shall no longer appear in the presenter recruitment view. | [TC-296](#tc-296), [TC-297](#tc-297) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-216"></a>**FR-VIRTUAL-216** | The presenter recruitment view shall support filtering by academic year (Aug 1 – Jul 31 cycle). | [TC-292](#tc-292) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-217"></a>**FR-VIRTUAL-217** | The presenter recruitment view shall display urgency indicators: red (≤7 days), yellow (8-14 days), blue (>14 days). | [TC-298](#tc-298) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-218"></a>**FR-VIRTUAL-218** | The presenter recruitment view shall support text search across event title and teacher names. | [TC-292](#tc-292) | [US-307](user_stories#us-307) |
| <a id="fr-virtual-219"></a>**FR-VIRTUAL-219** | The presenter recruitment view shall display a success message when all upcoming virtual sessions have presenters assigned. | Context only | [US-307](user_stories#us-307) |

## 7.4 Volunteer Search, Recruitment & Communication History

**Polaris + Salesforce Email Logging**

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-recruit-301"></a>**FR-RECRUIT-301** | Polaris shall provide a searchable list of volunteers. | [TC-300](#tc-300) | [US-401](user_stories#us-401) |
| <a id="fr-recruit-302"></a>**FR-RECRUIT-302** | Polaris shall support filtering/search by volunteer name, organization, role, skills, and career type. | [TC-301](#tc-301)–[TC-308](#tc-308) | [US-401](user_stories#us-401) |
| <a id="fr-recruit-303"></a>**FR-RECRUIT-303** | Polaris shall support identifying volunteers who have participated in virtual activities (including virtual-only). | [TC-320](#tc-320)–[TC-322](#tc-322) | [US-401](user_stories#us-401) |
| <a id="fr-recruit-304"></a>**FR-RECRUIT-304** | Polaris shall display volunteer participation history including most recent volunteer date. | [TC-340](#tc-340)–[TC-343](#tc-343) | [US-402](user_stories#us-402) |
| <a id="fr-recruit-305"></a>**FR-RECRUIT-305** | Polaris shall display communication history sourced from Salesforce email logging (Gmail add-on), including most recent contact date. | [TC-360](#tc-360)–[TC-361](#tc-361) | [US-404](user_stories#us-404) |
| <a id="fr-recruit-306"></a>**FR-RECRUIT-306** | Polaris shall allow staff to record recruitment notes and outcomes where Polaris provides that UI. | [TC-380](#tc-380)–[TC-381](#tc-381) | *Missing: US-403* |
| <a id="fr-recruit-308"></a>**FR-RECRUIT-308** | Polaris shall import/sync logged email communication records from Salesforce and associate them to the correct volunteer/person. | [TC-360](#tc-360)–[TC-366](#tc-366) | [US-404](user_stories#us-404) |
| <a id="fr-recruit-309"></a>**FR-RECRUIT-309** | Polaris shall distinguish "no communication logged" from "communication sync failure" (visibility into data completeness). | [TC-363](#tc-363), [TC-364](#tc-364) | [US-405](user_stories#us-405) |

## 7.5 Reporting and Dashboards

**Polaris**

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-reporting-401"></a>**FR-REPORTING-401** | Polaris shall provide a volunteer thank-you dashboard/report showing top volunteers by hours and/or events. | [TC-700](#tc-700)–[TC-703](#tc-703) | [US-701](user_stories#us-701) |
| <a id="fr-reporting-402"></a>**FR-REPORTING-402** | Polaris shall provide an organization participation dashboard/report. | [TC-720](#tc-720)–[TC-722](#tc-722) | [US-702](user_stories#us-702) |
| <a id="fr-reporting-403"></a>**FR-REPORTING-403** | Polaris shall provide district/school impact dashboards. | [TC-740](#tc-740)–[TC-744](#tc-744) | [US-703](user_stories#us-703) |
| <a id="fr-reporting-404"></a>**FR-REPORTING-404** | Polaris shall report at minimum: unique students reached, unique volunteers reached, total volunteer hours, and unique organizations engaged. | [TC-740](#tc-740), [TC-741](#tc-741) | [US-703](user_stories#us-703) |
| <a id="fr-reporting-405"></a>**FR-REPORTING-405** | Polaris shall support ad hoc querying/reporting for one-off participation questions (e.g., counts for a specific org). | [TC-760](#tc-760)–[TC-762](#tc-762) | [US-704](user_stories#us-704) |
| <a id="fr-reporting-406"></a>**FR-REPORTING-406** | Polaris shall provide export outputs (e.g., CSV) suitable for grant and district reporting workflows. | [TC-780](#tc-780)–[TC-783](#tc-783) | [US-701](user_stories#us-701), [US-702](user_stories#us-702), [US-703](user_stories#us-703), [US-704](user_stories#us-704) |

## 7.6 District and Teacher Progress

**Polaris**

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-district-501"></a>**FR-DISTRICT-501** | The system shall allow District Viewer users to authenticate and access district dashboards. | [TC-001](#tc-001) | [US-501](user_stories#us-501) |
| <a id="fr-district-502"></a>**FR-DISTRICT-502** | District dashboards shall display: number of schools, number of teachers, and progress breakdown. | [TC-010](#tc-010) | [US-501](user_stories#us-501), [US-503](user_stories#us-503) |
| <a id="fr-district-503"></a>**FR-DISTRICT-503** | District dashboards shall support drilldown by school to teacher-level completion detail. | [TC-011](#tc-011)–[TC-014](#tc-014) | [US-502](user_stories#us-502) |
| <a id="fr-district-504"></a>**FR-DISTRICT-504** | The system should send automated reminder emails to teachers based on progress status. *Near-term* | Placeholder | *Near-term* |
| <a id="fr-district-505"></a>**FR-DISTRICT-505** | The system shall provide a teacher self-service flow to request a magic link by entering their email address. | [TC-020](#tc-020), [TC-021](#tc-021) | [US-505](user_stories#us-505) |
| <a id="fr-district-506"></a>**FR-DISTRICT-506** | A teacher magic link shall grant access only to that teacher's progress/data. | [TC-022](#tc-022) | [US-505](user_stories#us-505) |
| <a id="fr-district-507"></a>**FR-DISTRICT-507** | The teacher view shall provide a mechanism to flag incorrect data and submit a note to internal staff. | [TC-023](#tc-023) | [US-505](user_stories#us-505) |
| <a id="fr-district-508"></a>**FR-DISTRICT-508** | The system shall compute teacher progress status using definitions: Achieved (completed), In Progress (future signup exists), Not Started (no signups). | [TC-010](#tc-010)–[TC-014](#tc-014), [TC-022](#tc-022) | [US-503](user_stories#us-503) |
| <a id="fr-district-521"></a>**FR-DISTRICT-521** | The system shall enforce role-based access for Admin, User, District Viewer, and Teacher. | [TC-002](#tc-002) | [US-501](user_stories#us-501), [US-505](user_stories#us-505) |
| <a id="fr-district-522"></a>**FR-DISTRICT-522** | District Viewer users shall only access data scoped to their district. | [TC-002](#tc-002) | [US-501](user_stories#us-501) |
| <a id="fr-district-523"></a>**FR-DISTRICT-523** | Teacher magic-link access shall be scoped to a single teacher identity matched by email from the imported district roster. | [TC-003](#tc-003), [TC-024](#tc-024) | [US-505](user_stories#us-505) |
| <a id="fr-district-524"></a>**FR-DISTRICT-524** | The system shall support importing a district-provided teacher roster (minimum: teacher name, email, grade; school if available) and use it as the authoritative list for progress tracking and magic-link eligibility. | [TC-020](#tc-020), [TC-030](#tc-030)–[TC-031](#tc-031) | [US-504](user_stories#us-504) |

## 7.7 Student Roster and Attendance

**Salesforce + Polaris Reporting**

| ID | Requirement | Test Coverage | Related User Stories |
|----|-------------|---------------|----------------------|
| <a id="fr-student-601"></a>**FR-STUDENT-601** | The system shall support associating students with events (student roster). | [TC-600](#tc-600)–[TC-603](#tc-603) | [US-601](user_stories#us-601) |
| <a id="fr-student-602"></a>**FR-STUDENT-602** | The system shall support recording student attendance status per student-event participation. | [TC-610](#tc-610)–[TC-613](#tc-613) | [US-602](user_stories#us-602) |
| <a id="fr-student-603"></a>**FR-STUDENT-603** | Polaris reporting shall use student attendance to compute unique students reached and other impact metrics by school and district. | [TC-620](#tc-620)–[TC-624](#tc-624) | [US-603](user_stories#us-603) |
| <a id="fr-student-604"></a>**FR-STUDENT-604** | Reporting users shall be able to view student reach metrics by district, school, event type, and date range. | | [US-603](user_stories#us-603) |

## Traceability Matrix

This section provides a comprehensive view of the relationships between Functional Requirements (FR) and User Stories (US).

### FR → US Mapping

| Functional Requirement | Related User Stories | Notes |
|------------------------|---------------------|-------|
| **In-Person Events** | | |
| FR-INPERSON-101 | [US-101](user_stories#us-101) | Event creation |
| FR-INPERSON-102, 103, 123 | [US-102](user_stories#us-102) | Sync operations |
| FR-INPERSON-104, 105 | [US-103](user_stories#us-103) | Visibility control |
| FR-INPERSON-107, 109 | [US-104](user_stories#us-104) | District linking |
| FR-INPERSON-106 | [US-105](user_stories#us-105) | Website display |
| FR-INPERSON-108, 110-133 | *Technical requirements* | Infrastructure/sync operations |
| **Public Signup** | | |
| FR-SIGNUP-121, 122, 127 | [US-201](user_stories#us-201) | Signup without account |
| FR-SIGNUP-126, 127 | [US-202](user_stories#us-202) | Form fields |
| FR-SIGNUP-123, 124, 125 | [US-203](user_stories#us-203) | Email/calendar |
| **Virtual Events** | | |
| FR-VIRTUAL-201 | [US-301](user_stories#us-301) | Create virtual event |
| FR-VIRTUAL-202 | [US-302](user_stories#us-302) | Tag teachers |
| FR-VIRTUAL-203 | *Missing: US-303* | Tag presenters |
| FR-VIRTUAL-204 | [US-306](user_stories#us-306) | Historical import |
| FR-VIRTUAL-206 | [US-304](user_stories#us-304) | Pathful import |
| FR-VIRTUAL-208 | *Missing: US-305* | Local vs non-local |
| FR-VIRTUAL-210-219 | [US-307](user_stories#us-307) | Presenter recruitment |
| FR-VIRTUAL-205, 207, 209 | *Context/Near-term* | Future features |
| **Volunteer Recruitment** | | |
| FR-RECRUIT-301, 302, 303 | [US-401](user_stories#us-401) | Search/filter |
| FR-RECRUIT-304 | [US-402](user_stories#us-402) | Participation history |
| FR-RECRUIT-305, 308 | [US-404](user_stories#us-404) | Communication history |
| FR-RECRUIT-306 | [US-403](user_stories#us-403) | Recruitment notes |
| FR-RECRUIT-309 | [US-405](user_stories#us-405) | Sync health visibility |
| **Reporting** | | |
| FR-REPORTING-401, 406 | [US-701](user_stories#us-701) | Volunteer thank-you |
| FR-REPORTING-402, 406 | [US-702](user_stories#us-702) | Organization reporting |
| FR-REPORTING-403, 404, 406 | [US-703](user_stories#us-703) | District/school impact |
| FR-REPORTING-405, 406 | [US-704](user_stories#us-704) | Ad hoc queries |
| **District Progress** | | |
| FR-DISTRICT-501, 502, 521, 522 | [US-501](user_stories#us-501) | District dashboard |
| FR-DISTRICT-503 | [US-502](user_stories#us-502) | Drilldown |
| FR-DISTRICT-502, 508 | [US-503](user_stories#us-503) | Status computation |
| FR-DISTRICT-524 | *Missing: US-504* | Roster import |
| FR-DISTRICT-505, 506, 507, 508, 521, 523 | [US-505](user_stories#us-505) | Teacher magic link |
| FR-DISTRICT-504 | *Near-term* | Automated reminders |
| **Student Roster** | | |
| FR-STUDENT-601 | [US-601](user_stories#us-601) | Roster creation |
| FR-STUDENT-602 | [US-602](user_stories#us-602) | Attendance recording |
| FR-STUDENT-603, 604 | [US-603](user_stories#us-603) | Reporting metrics |

### Coverage Summary

- **Total FRs**: 89
- **FRs with User Stories**: 44 (49%)
- **Technical/Infrastructure FRs** (appropriately without US): 45 (51%)
- **User Stories Added**: 9 new stories (US-303, 305, 402, 403, 504, 506, 507, 801-803)
- **Additional Features Documented**: Email system (US-801-803) and Data Tracker (US-506-507) features are now captured as user stories

### US → FR Mapping

| User Story | Related Functional Requirements |
|------------|--------------------------------|
| US-101 | FR-INPERSON-101 |
| US-102 | FR-INPERSON-102, 103, 123 |
| US-103 | FR-INPERSON-104, 105 |
| US-104 | FR-INPERSON-107, 109 |
| US-105 | FR-INPERSON-106 |
| US-201 | FR-SIGNUP-121, 122, 127 |
| US-202 | FR-SIGNUP-126, 127 |
| US-203 | FR-SIGNUP-123, 124, 125 |
| US-301 | FR-VIRTUAL-201 |
| US-302 | FR-VIRTUAL-202 |
| US-304 | FR-VIRTUAL-206 |
| US-306 | FR-VIRTUAL-204 |
| US-307 | FR-VIRTUAL-210 through 219 |
| US-401 | FR-RECRUIT-301, 302, 303 |
| US-404 | FR-RECRUIT-305, 308 |
| US-405 | FR-RECRUIT-309 |
| US-501 | FR-DISTRICT-501, 502, 521, 522 |
| US-502 | FR-DISTRICT-503 |
| US-503 | FR-DISTRICT-502, 508 |
| US-505 | FR-DISTRICT-505, 506, 507, 508, 521, 523 |
| US-601 | FR-STUDENT-601 |
| US-602 | FR-STUDENT-602 |
| US-603 | FR-STUDENT-603, 604 |
| US-701 | FR-REPORTING-401, 406 |
| US-702 | FR-REPORTING-402, 406 |
| US-703 | FR-REPORTING-403, 404, 406 |
| US-704 | FR-REPORTING-405, 406 |
| US-506 | *Data tracker features* |
| US-507 | *Data tracker features* |
| US-801 | *Email system features* |
| US-802 | *Email system features* |
| US-803 | *Email system features* |

---

*Last updated: January 2026*
*Version: 1.0*
