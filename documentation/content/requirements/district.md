# District & Teacher Progress Requirements

**Polaris**

---

## District Dashboard Access

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-501"></a>**FR-DISTRICT-501** | The system shall allow District Viewer users to authenticate and access district dashboards. | TC-001 | [US-501](user-stories#us-501) |
| <a id="fr-district-502"></a>**FR-DISTRICT-502** | District dashboards shall display: number of schools, number of teachers, and progress breakdown. | TC-010 | [US-501](user-stories#us-501), [US-503](user-stories#us-503) |
| <a id="fr-district-503"></a>**FR-DISTRICT-503** | District dashboards shall support drilldown by school to teacher-level completion detail. | TC-011–TC-014 | [US-502](user-stories#us-502) |
| <a id="fr-district-504"></a>**FR-DISTRICT-504** | The system should send automated reminder emails to teachers based on progress status. | Placeholder | *Near-term* |

---

## Teacher Self-Service

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-505"></a>**FR-DISTRICT-505** | The system shall provide a teacher self-service flow to request a magic link by entering their email address. | TC-020, TC-021 | [US-505](user-stories#us-505) |
| <a id="fr-district-506"></a>**FR-DISTRICT-506** | A teacher magic link shall grant access only to that teacher's progress/data. | TC-022 | [US-505](user-stories#us-505) |
| <a id="fr-district-507"></a>**FR-DISTRICT-507** | The teacher view shall provide a mechanism to flag incorrect data and submit a note to internal staff. | TC-023 | [US-505](user-stories#us-505) |
| <a id="fr-district-508"></a>**FR-DISTRICT-508** | The system shall compute teacher progress status using definitions: Achieved (completed), In Progress (future signup exists), Not Started (no signups). | TC-010–TC-014, TC-022 | [US-503](user-stories#us-503) |

---

## Access Control

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-521"></a>**FR-DISTRICT-521** | The system shall enforce role-based access for Admin, User, District Viewer, and Teacher. | TC-002 | [US-501](user-stories#us-501), [US-505](user-stories#us-505) |
| <a id="fr-district-522"></a>**FR-DISTRICT-522** | District Viewer users shall only access data scoped to their district. | TC-002 | [US-501](user-stories#us-501) |
| <a id="fr-district-523"></a>**FR-DISTRICT-523** | Teacher magic-link access shall be scoped to a single teacher identity matched by email from the imported district roster. | TC-003, TC-024 | [US-505](user-stories#us-505) |

---

## Teacher Roster Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-524"></a>**FR-DISTRICT-524** | The system shall support importing a district-provided teacher roster (minimum: teacher name, email, grade; school if available) using merge/upsert strategy. Removed teachers are soft-deleted. | TC-030, TC-031 | [US-504](user-stories#us-504) |
| <a id="fr-district-531"></a>**FR-DISTRICT-531** | The system shall provide automatic and manual matching of imported TeacherProgress entries to Teacher database records using email (primary) and fuzzy name matching (secondary). | *TBD* | [US-508](user-stories#us-508) |
| <a id="fr-district-532"></a>**FR-DISTRICT-532** | The system shall allow Google Sheets for teacher progress tracking to be scoped to a specific district. | *TBD* | *Technical* |

---

## Semester Reset & Archiving

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-540"></a>**FR-DISTRICT-540** | The system shall automatically reset teacher progress status to "Not Started" at the start of each semester (January 1 and June 30). | TC-040, TC-041 | [US-509](user-stories#us-509) |
| <a id="fr-district-541"></a>**FR-DISTRICT-541** | Before resetting progress, the system shall archive the previous semester's progress data including teacher status, session counts, and completion dates. | TC-042 | [US-509](user-stories#us-509) |
| <a id="fr-district-542"></a>**FR-DISTRICT-542** | Archived semester data shall be retained and viewable for historical reporting purposes. | TC-043 | [US-509](user-stories#us-509) |
| <a id="fr-district-543"></a>**FR-DISTRICT-543** | The system shall log semester reset operations with timestamps and affected record counts. | TC-044 | *Technical* |
| <a id="fr-district-544"></a>**FR-DISTRICT-544** | The system shall provide a manual "Archive Semester" action for admins to force-archive current progress data at any time. | *TBD* | [US-509](user-stories#us-509) |

---

## Data Tracker Features

> [!NOTE]
> **System Locations**
> - **District Portal**: `/virtual/<district_name>`
> - **District Dashboard**: `/virtual/usage/district/<district_name>`
> - **Teacher Dashboard**: `/virtual/<district_name>/teacher/<teacher_id>`

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-district-525"></a>**FR-DISTRICT-525** | District users shall be able to flag data issues (missing or incorrect data) related to teachers and sessions in their district, with structured issue reports. | *TBD* | [US-506](user-stories#us-506) |
| <a id="fr-district-526"></a>**FR-DISTRICT-526** | Teachers shall be able to view their own session history including past and upcoming sessions via the teacher dashboard. | *TBD* | [US-507](user-stories#us-507) |
| <a id="fr-district-527"></a>**FR-DISTRICT-527** | Teachers shall be able to flag incorrect data related to their own session data via the teacher dashboard. | *TBD* | [US-507](user-stories#us-507) |
| <a id="fr-district-528"></a>**FR-DISTRICT-528** | District issue reports shall create BugReport entries with type `DATA_ERROR` and structured descriptions. | *TBD* | *Technical* |
| <a id="fr-district-529"></a>**FR-DISTRICT-529** | District users shall only be able to report issues for teachers in the TeacherProgress tracking list for their district. | *TBD* | *Technical* |
| <a id="fr-district-530"></a>**FR-DISTRICT-530** | The district portal landing page shall provide separate login options for District Login and Teacher Login. | *TBD* | *Technical* |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [District Self-Service Guide](user-guide-district-self-service) — User documentation

---

*Last updated: February 2026 · Version 1.0*
