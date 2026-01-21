# Functional Requirements

**Numbered requirements referenced by test packs**

## Traceability

Each **FR-xxx** is referenced by test cases in **Test Packs 1–6**. User stories with acceptance criteria in **User Stories**.

## 7.1 In-Person Event Management

**Salesforce + VolunTeach + Website**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-101"></a>**FR-101** | Staff shall create and maintain in-person event records in Salesforce. | [TC-100](test-pack-2#tc-100) |
| <a id="fr-102"></a>**FR-102** | VolunTeach shall sync in-person events from Salesforce at least once per hour via automated scheduled sync. The system also supports scheduled daily batch imports that process events, volunteer participations, and student participations. | [TC-101](test-pack-2#tc-101), [TC-103](test-pack-2#tc-103) |
| <a id="fr-103"></a>**FR-103** | VolunTeach shall provide a manual "sync now" action for immediate synchronization. Manual sync operations shall support large datasets with configurable batch sizes and progress indicators for use cases such as reports and historical data imports. | [TC-100](test-pack-2#tc-100), [TC-102](test-pack-2#tc-102) |
| <a id="fr-104"></a>**FR-104** | VolunTeach shall allow staff to control whether an event appears on the public in-person events page via a visibility toggle. | [TC-110](test-pack-2#tc-110), [TC-111](test-pack-2#tc-111) |
| <a id="fr-105"></a>**FR-105** | The system shall support events that are not displayed on the public in-person page (e.g., orientations). | [TC-112](test-pack-2#tc-112) |
| <a id="fr-106"></a>**FR-106** | The website shall display for each event at minimum: volunteer slots needed, slots filled, date/time, school, and event description/type. | [TC-120](test-pack-2#tc-120), [TC-121](test-pack-2#tc-121) |
| <a id="fr-107"></a>**FR-107** | VolunTeach shall allow staff to link events to one or more districts for district-specific website pages. | [TC-113](test-pack-2#tc-113), [TC-114](test-pack-2#tc-114) |
| <a id="fr-109"></a>**FR-109** | Any event linked to a district shall appear on that district's website page regardless of the in-person-page visibility toggle. | [TC-113](test-pack-2#tc-113), [TC-115](test-pack-2#tc-115) |

### Scheduled Imports

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-108"></a>**FR-108** | The system shall support scheduled daily imports of in-person events from Salesforce, including events, volunteer participations, and student participations. | [TC-160](test-pack-2#tc-160) |
| <a id="fr-110"></a>**FR-110** | Daily imports shall process events in batches to handle large datasets without exceeding API limits. | [TC-161](test-pack-2#tc-161) |
| <a id="fr-111"></a>**FR-111** | The system shall provide visibility into daily import status, success/failure counts, and error details. | [TC-162](test-pack-2#tc-162) |

### Participation Sync

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-112"></a>**FR-112** | The system shall sync student participation data from Salesforce for in-person events, creating EventStudentParticipation records. | [TC-170](test-pack-2#tc-170) |
| <a id="fr-113"></a>**FR-113** | Student participation sync shall update attendance status and delivery hours from Salesforce. | [TC-171](test-pack-2#tc-171) |
| <a id="fr-114"></a>**FR-114** | The system shall sync volunteer participation data from Salesforce for in-person events, including status, delivery hours, and participant attributes. | [TC-172](test-pack-2#tc-172) |
| <a id="fr-115"></a>**FR-115** | Volunteer participation sync shall handle batch processing for large event sets (e.g., 50 events per batch). | [TC-173](test-pack-2#tc-173) |

### Unaffiliated Events

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-116"></a>**FR-116** | The system shall identify and sync events from Salesforce that are missing School, District, or Parent Account associations. | [TC-180](test-pack-2#tc-180) |
| <a id="fr-117"></a>**FR-117** | For unaffiliated events, the system shall attempt to associate events with districts based on participating students. | [TC-181](test-pack-2#tc-181) |
| <a id="fr-118"></a>**FR-118** | Unaffiliated event sync shall update both event data and associated volunteer/student participation records. | [TC-182](test-pack-2#tc-182) |

### Status Management

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-119"></a>**FR-119** | When syncing events, the system shall update event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) from Salesforce. | [TC-190](test-pack-2#tc-190) |
| <a id="fr-120"></a>**FR-120** | The system shall preserve cancellation reasons when events are cancelled in Salesforce. | [TC-191](test-pack-2#tc-191) |
| <a id="fr-121"></a>**FR-121** | Status changes shall be reflected in VolunTeach and on public website within the sync cycle. | [TC-192](test-pack-2#tc-192) |

### Error Handling and Monitoring

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-122"></a>**FR-122** | The system shall detect and report sync failures with detailed error messages (not silent failures). | [TC-104](test-pack-2#tc-104) |
| <a id="fr-123"></a>**FR-123** | Sync operations shall be idempotent (no duplicates on re-sync). | [TC-102](test-pack-2#tc-102) |
| <a id="fr-124"></a>**FR-124** | The system shall distinguish between "no events to sync" and "sync failure" for monitoring purposes. | [TC-200](test-pack-2#tc-200) |
| <a id="fr-125"></a>**FR-125** | Failed sync operations shall be logged with timestamps, error details, and affected record counts. | [TC-201](test-pack-2#tc-201) |

### Historical Data Import

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-126"></a>**FR-126** | The system shall support importing historical in-person event data from Salesforce (e.g., 2–4 years of past events). | [TC-210](test-pack-2#tc-210) |
| <a id="fr-127"></a>**FR-127** | Historical import shall preserve event-participant relationships and maintain data integrity. | [TC-211](test-pack-2#tc-211) |

### Manual Operations

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-128"></a>**FR-128** | For large datasets, the system shall provide manual sync operations that process events in configurable batch sizes. | [TC-212](test-pack-2#tc-212) |
| <a id="fr-129"></a>**FR-129** | Manual sync operations shall provide progress indicators and allow cancellation/resumption. | [TC-213](test-pack-2#tc-213) |

### Data Completeness Visibility

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-130"></a>**FR-130** | The system shall distinguish "no events to sync" from "event sync failure" (visibility into data completeness). | [TC-200](test-pack-2#tc-200) |
| <a id="fr-131"></a>**FR-131** | Sync status indicators shall show last successful sync time, record counts, and any pending errors. | [TC-220](test-pack-2#tc-220) |

### Reporting Integration

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-132"></a>**FR-132** | Event sync operations shall trigger cache invalidation for reports that depend on event data. | [TC-221](test-pack-2#tc-221) |
| <a id="fr-133"></a>**FR-133** | Manual cache refresh for event-based reports shall be available when automated sync is insufficient for large datasets. | [TC-222](test-pack-2#tc-222) |

## 7.2 Public Volunteer Signup

**Website**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-121"></a>**FR-121** | The website shall allow volunteers to sign up for an event via a public form without authentication. | [TC-130](#tc-130)–[TC-140](#tc-140) |
| <a id="fr-122"></a>**FR-122** | Each signup shall create a participation record associated with the event and the volunteer identity (email-based at minimum). | [TC-140](#tc-140), [TC-142](#tc-142) |
| <a id="fr-123"></a>**FR-123** | The system shall send a confirmation email upon successful signup. | [TC-150](#tc-150) |
| <a id="fr-124"></a>**FR-124** | The system shall send a calendar invite upon successful signup. | [TC-151](#tc-151) |
| <a id="fr-125"></a>**FR-125** | The calendar invite shall include event details and location/map information derived from the Salesforce event record. | [TC-152](#tc-152) |
| <a id="fr-126"></a>**FR-126** | The signup form shall collect: First Name, Last Name, Email, Organization, Title, Volunteer Skills (dropdown), Age Group (dropdown), Highest Education Attainment (dropdown), Gender (dropdown), Race/Ethnicity (dropdown). | [TC-130](#tc-130)–[TC-132](#tc-132) |
| <a id="fr-127"></a>**FR-127** | The system shall store the submitted signup attributes for use in reporting, recruitment search, and volunteer profiles. | [TC-141](#tc-141) |

## 7.3 Virtual Events

**Polaris + Pathful**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-201"></a>**FR-201** | Polaris shall allow staff to create and maintain virtual event records. | [TC-200](#tc-200), [TC-201](#tc-201) |
| <a id="fr-202"></a>**FR-202** | Polaris shall allow staff to search for and tag teachers using Salesforce-linked teacher records. | [TC-202](#tc-202), [TC-204](#tc-204) |
| <a id="fr-203"></a>**FR-203** | Polaris shall allow staff to search for and tag presenters/volunteers using Salesforce-linked records. | [TC-203](#tc-203), [TC-204](#tc-204) |
| <a id="fr-204"></a>**FR-204** | The system shall support importing 2–4 years of historical virtual event data from Google Sheets, preserving event–teacher relationships and multi-line mapping. | [TC-270](#tc-270)–[TC-275](#tc-275) |
| <a id="fr-205"></a>**FR-205** | The system shall treat Pathful as the current source for virtual event signup and reminder emails. | Context only |
| <a id="fr-206"></a>**FR-206** | Polaris shall ingest Pathful export data to update virtual attendance and participation tracking. | [TC-250](#tc-250)–[TC-260](#tc-260) |
| <a id="fr-207"></a>**FR-207** | The system should support automation to pull Pathful exports and load them into Polaris. *Near-term* | [TC-280](#tc-280) |
| <a id="fr-208"></a>**FR-208** | The system shall track whether a virtual volunteer is local vs non-local. | [TC-230](#tc-230)–[TC-232](#tc-232) |
| <a id="fr-209"></a>**FR-209** | The system should support sending automated communications that connect local volunteers. *Near-term* | [TC-281](#tc-281) |
| <a id="fr-210"></a>**FR-210** | Polaris shall provide a view listing upcoming virtual events that do not have a presenter assigned. | [TC-290](#tc-290)–[TC-299](#tc-299) |
| <a id="fr-211"></a>**FR-211** | The presenter recruitment view shall filter to show only future events (start_datetime > current date/time). | [TC-291](#tc-291) |
| <a id="fr-212"></a>**FR-212** | The presenter recruitment view shall support filtering by date range, school, district, and event type. | [TC-292](#tc-292)–[TC-295](#tc-295) |
| <a id="fr-213"></a>**FR-213** | The presenter recruitment view shall display for each event: title, date/time, school/district, teacher count, and days until event. | [TC-298](#tc-298) |
| <a id="fr-214"></a>**FR-214** | Staff shall be able to navigate directly from a presenter-needed event to the volunteer search/recruitment workflow. | [TC-299](#tc-299) |
| <a id="fr-215"></a>**FR-215** | Once a presenter is tagged to an event, that event shall no longer appear in the presenter recruitment view. | [TC-296](#tc-296), [TC-297](#tc-297) |
| <a id="fr-216"></a>**FR-216** | The presenter recruitment view shall support filtering by academic year (Aug 1 – Jul 31 cycle). | [TC-292](#tc-292) |
| <a id="fr-217"></a>**FR-217** | The presenter recruitment view shall display urgency indicators: red (≤7 days), yellow (8-14 days), blue (>14 days). | [TC-298](#tc-298) |
| <a id="fr-218"></a>**FR-218** | The presenter recruitment view shall support text search across event title and teacher names. | [TC-292](#tc-292) |
| <a id="fr-219"></a>**FR-219** | The presenter recruitment view shall display a success message when all upcoming virtual sessions have presenters assigned. | Context only |

## 7.4 Volunteer Search, Recruitment & Communication History

**Polaris + Salesforce Email Logging**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-301"></a>**FR-301** | Polaris shall provide a searchable list of volunteers. | [TC-300](#tc-300) |
| <a id="fr-302"></a>**FR-302** | Polaris shall support filtering/search by volunteer name, organization, role, skills, and career type. | [TC-301](#tc-301)–[TC-308](#tc-308) |
| <a id="fr-303"></a>**FR-303** | Polaris shall support identifying volunteers who have participated in virtual activities (including virtual-only). | [TC-320](#tc-320)–[TC-322](#tc-322) |
| <a id="fr-304"></a>**FR-304** | Polaris shall display volunteer participation history including most recent volunteer date. | [TC-340](#tc-340)–[TC-343](#tc-343) |
| <a id="fr-305"></a>**FR-305** | Polaris shall display communication history sourced from Salesforce email logging (Gmail add-on), including most recent contact date. | [TC-360](#tc-360)–[TC-361](#tc-361) |
| <a id="fr-306"></a>**FR-306** | Polaris shall allow staff to record recruitment notes and outcomes where Polaris provides that UI. | [TC-380](#tc-380)–[TC-381](#tc-381) |
| <a id="fr-308"></a>**FR-308** | Polaris shall import/sync logged email communication records from Salesforce and associate them to the correct volunteer/person. | [TC-360](#tc-360)–[TC-366](#tc-366) |
| <a id="fr-309"></a>**FR-309** | Polaris shall distinguish "no communication logged" from "communication sync failure" (visibility into data completeness). | [TC-363](#tc-363), [TC-364](#tc-364) |

## 7.5 Reporting and Dashboards

**Polaris**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-401"></a>**FR-401** | Polaris shall provide a volunteer thank-you dashboard/report showing top volunteers by hours and/or events. | [TC-700](#tc-700)–[TC-703](#tc-703) |
| <a id="fr-402"></a>**FR-402** | Polaris shall provide an organization participation dashboard/report. | [TC-720](#tc-720)–[TC-722](#tc-722) |
| <a id="fr-403"></a>**FR-403** | Polaris shall provide district/school impact dashboards. | [TC-740](#tc-740)–[TC-744](#tc-744) |
| <a id="fr-404"></a>**FR-404** | Polaris shall report at minimum: unique students reached, unique volunteers reached, total volunteer hours, and unique organizations engaged. | [TC-740](#tc-740), [TC-741](#tc-741) |
| <a id="fr-405"></a>**FR-405** | Polaris shall support ad hoc querying/reporting for one-off participation questions (e.g., counts for a specific org). | [TC-760](#tc-760)–[TC-762](#tc-762) |
| <a id="fr-406"></a>**FR-406** | Polaris shall provide export outputs (e.g., CSV) suitable for grant and district reporting workflows. | [TC-780](#tc-780)–[TC-783](#tc-783) |

## 7.6 District and Teacher Progress

**Polaris**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-501"></a>**FR-501** | The system shall allow District Viewer users to authenticate and access district dashboards. | [TC-001](#tc-001) |
| <a id="fr-502"></a>**FR-502** | District dashboards shall display: number of schools, number of teachers, and progress breakdown. | [TC-010](#tc-010) |
| <a id="fr-503"></a>**FR-503** | District dashboards shall support drilldown by school to teacher-level completion detail. | [TC-011](#tc-011)–[TC-014](#tc-014) |
| <a id="fr-504"></a>**FR-504** | The system should send automated reminder emails to teachers based on progress status. *Near-term* | Placeholder |
| <a id="fr-505"></a>**FR-505** | The system shall provide a teacher self-service flow to request a magic link by entering their email address. | [TC-020](#tc-020), [TC-021](#tc-021) |
| <a id="fr-506"></a>**FR-506** | A teacher magic link shall grant access only to that teacher's progress/data. | [TC-022](#tc-022) |
| <a id="fr-507"></a>**FR-507** | The teacher view shall provide a mechanism to flag incorrect data and submit a note to internal staff. | [TC-023](#tc-023) |
| <a id="fr-508"></a>**FR-508** | The system shall compute teacher progress status using definitions: Achieved (completed), In Progress (future signup exists), Not Started (no signups). | [TC-010](#tc-010)–[TC-014](#tc-014), [TC-022](#tc-022) |
| <a id="fr-521"></a>**FR-521** | The system shall enforce role-based access for Admin, User, District Viewer, and Teacher. | [TC-002](#tc-002) |
| <a id="fr-522"></a>**FR-522** | District Viewer users shall only access data scoped to their district. | [TC-002](#tc-002) |
| <a id="fr-523"></a>**FR-523** | Teacher magic-link access shall be scoped to a single teacher identity matched by email from the imported district roster. | [TC-003](#tc-003), [TC-024](#tc-024) |
| <a id="fr-524"></a>**FR-524** | The system shall support importing a district-provided teacher roster (minimum: teacher name, email, grade; school if available) and use it as the authoritative list for progress tracking and magic-link eligibility. | [TC-020](#tc-020), [TC-030](#tc-030)–[TC-031](#tc-031) |

## 7.7 Student Roster and Attendance

**Salesforce + Polaris Reporting**

| ID | Requirement | Test Coverage |
|----|-------------|---------------|
| <a id="fr-601"></a>**FR-601** | The system shall support associating students with events (student roster). | [TC-600](#tc-600)–[TC-603](#tc-603) |
| <a id="fr-602"></a>**FR-602** | The system shall support recording student attendance status per student-event participation. | [TC-610](#tc-610)–[TC-613](#tc-613) |
| <a id="fr-603"></a>**FR-603** | Polaris reporting shall use student attendance to compute unique students reached and other impact metrics by school and district. | [TC-620](#tc-620)–[TC-624](#tc-624) |
| <a id="fr-604"></a>**FR-604** | Reporting users shall be able to view student reach metrics by district, school, event type, and date range. | |

---

*Last updated: January 2026*
*Version: 1.0*
