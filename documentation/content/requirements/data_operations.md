# Data Integrity & Operations Requirements

**Core System Logic**

---

## Data Integrity

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-data-901"></a>**FR-DATA-901** | **Duplicate Management**: The system shall provide automated logic to identify and merge duplicate event or participant records based on unique identifiers (Salesforce ID, email), prioritizing valid status data (e.g., 'Attended' > 'Registered'). | [TC-901](test-pack-7#tc-901) | *Technical* |
| <a id="fr-data-902"></a>**FR-DATA-902** | **Dynamic Profile Creation**: When importing participants, if a profile (Volunteer/Organization) does not exist, the system shall automatically create a draft profile using provided details. | [TC-902](test-pack-7#tc-902) | *Technical* |
| <a id="fr-data-903"></a>**FR-DATA-903** | **Sync Dependencies**: Data synchronization shall enforce dependency order (Orgs → Volunteers → Events) and support "Partial Success" states. | [TC-903](test-pack-7#tc-903), [TC-904](test-pack-7#tc-904) | *Technical* |

---

## Operational Requirements

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-ops-904"></a>**FR-OPS-904** | **Attendance Workflow**: The system shall track the *status of attendance taking* (Not Taken, In Progress, Completed) separately from the event status itself. | [TC-910](test-pack-7#tc-910) | *Operational* |
| <a id="fr-ops-905"></a>**FR-OPS-905** | **Admin Safety (Purge)**: The system shall provide a restricted 'Purge' capability for Administrators to bulk-delete event data, requiring high-level privileges and generating an audit log. | [TC-911](test-pack-7#tc-911) | *Operational* |
| <a id="fr-ops-906"></a>**FR-OPS-906** | **Granular Categorization**: The system shall support detailed event categorization (e.g., Career Fair, Classroom Speaker, Ignite) beyond simple Virtual/In-Person types. | [TC-913](test-pack-7#tc-913) | *Operational* |
| <a id="fr-ops-907"></a>**FR-OPS-907** | **Auto-Admin Provisioning**: On initialization, if no administrator exists, the system shall securely provision a default admin account. | [TC-912](test-pack-7#tc-912) | *Technical* |

---

## Data Synchronization (In-Person)

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-inperson-108"></a>**FR-INPERSON-108** | The system shall support scheduled daily imports of in-person events from Salesforce, including events, volunteer participations, and student participations. | [TC-160](test-pack-7#tc-160) | *Technical* |
| <a id="fr-inperson-110"></a>**FR-INPERSON-110** | Daily imports shall process events in batches to handle large datasets without exceeding API limits. | [TC-161](test-pack-7#tc-161) | *Technical* |
| <a id="fr-inperson-111"></a>**FR-INPERSON-111** | The system shall provide visibility into daily import status, success/failure counts, and error details. | [TC-162](test-pack-7#tc-162) | *Technical* |
| <a id="fr-inperson-112"></a>**FR-INPERSON-112** | The system shall sync student participation data from Salesforce for in-person events, creating EventStudentParticipation records. | [TC-170](test-pack-7#tc-170) | *Technical* |
| <a id="fr-inperson-113"></a>**FR-INPERSON-113** | Student participation sync shall update attendance status and delivery hours from Salesforce. | [TC-171](test-pack-7#tc-171) | *Technical* |
| <a id="fr-inperson-114"></a>**FR-INPERSON-114** | The system shall sync volunteer participation data from Salesforce for in-person events, including status, delivery hours, and participant attributes. | [TC-172](test-pack-7#tc-172) | *Technical* |
| <a id="fr-inperson-115"></a>**FR-INPERSON-115** | Volunteer participation sync shall handle batch processing for large event sets (e.g., 50 events per batch). | [TC-173](test-pack-7#tc-173) | *Technical* |
| <a id="fr-inperson-116"></a>**FR-INPERSON-116** | The system shall identify and sync events from Salesforce that are missing School, District, or Parent Account associations. | [TC-180](test-pack-7#tc-180) | *Technical* |
| <a id="fr-inperson-117"></a>**FR-INPERSON-117** | For unaffiliated events, the system shall attempt to associate events with districts based on participating students. | [TC-181](test-pack-7#tc-181) | *Technical* |
| <a id="fr-inperson-118"></a>**FR-INPERSON-118** | Unaffiliated event sync shall update both event data and associated volunteer/student participation records. | [TC-182](test-pack-7#tc-182) | *Technical* |
| <a id="fr-inperson-119"></a>**FR-INPERSON-119** | When syncing events, the system shall update event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) from Salesforce. | [TC-190](test-pack-7#tc-190) | *Technical* |
| <a id="fr-inperson-120"></a>**FR-INPERSON-120** | The system shall preserve cancellation reasons when events are cancelled in Salesforce. | [TC-191](test-pack-7#tc-191) | *Technical* |
| <a id="fr-inperson-121"></a>**FR-INPERSON-121** | Status changes shall be reflected in VolunTeach and on public website within the sync cycle. | [TC-192](test-pack-7#tc-192) | *Technical* |

---

## Sync Error Monitoring

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-inperson-122"></a>**FR-INPERSON-122** | The system shall detect and report sync failures with detailed error messages (not silent failures). | [TC-104](test-pack-2#tc-104) | *Technical* |
| <a id="fr-inperson-123"></a>**FR-INPERSON-123** | Sync operations shall be idempotent (no duplicates on re-sync). | [TC-102](test-pack-2#tc-102) | [US-102](user-stories#us-102) |
| <a id="fr-inperson-124"></a>**FR-INPERSON-124** | The system shall distinguish between "no events to sync" and "sync failure" for monitoring purposes. | [TC-200](test-pack-7#tc-200) | *Technical* |
| <a id="fr-inperson-125"></a>**FR-INPERSON-125** | Failed sync operations shall be logged with timestamps, error details, and affected record counts. | [TC-201](test-pack-7#tc-201) | *Technical* |
| <a id="fr-inperson-130"></a>**FR-INPERSON-130** | The system shall distinguish "no events to sync" from "event sync failure" (visibility into data completeness). | [TC-200](test-pack-7#tc-200) | *Technical* |
| <a id="fr-inperson-131"></a>**FR-INPERSON-131** | Sync status indicators shall show last successful sync time, record counts, and any pending errors. | [TC-220](test-pack-7#tc-220) | *Technical* |

---

## Delta Sync (Incremental Import)

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-delta-001"></a>**FR-DELTA-001** | The system shall provide a reusable `DeltaSyncHelper` service for managing incremental sync operations across all Salesforce imports. | *Feb 2026* | *Technical* |
| <a id="fr-delta-002"></a>**FR-DELTA-002** | The `sync_logs` table shall store `last_sync_watermark` (timestamp) and `is_delta_sync` (boolean) fields to track incremental sync state. | *Feb 2026* | *Technical* |
| <a id="fr-delta-003"></a>**FR-DELTA-003** | Event and participant imports shall support delta sync via `?delta=true` query parameter, querying only records where `LastModifiedDate > watermark`. | *Feb 2026* | *Technical* |
| <a id="fr-delta-004"></a>**FR-DELTA-004** | Volunteer imports shall support delta sync, fetching only volunteers modified since the last successful sync. | *Feb 2026* | *Technical* |
| <a id="fr-delta-005"></a>**FR-DELTA-005** | History imports (Tasks, EmailMessages) shall support delta sync for incremental communication history updates. | *Feb 2026* | *Technical* |
| <a id="fr-delta-006"></a>**FR-DELTA-006** | School and District imports shall support delta sync for incremental organizational data updates. | *Feb 2026* | *Technical* |
| <a id="fr-delta-007"></a>**FR-DELTA-007** | Teacher imports shall support delta sync, fetching only teachers modified since the last successful sync. | *Feb 2026* | *Technical* |
| <a id="fr-delta-008"></a>**FR-DELTA-008** | Student imports shall support delta sync within chunked processing, maintaining watermark tracking across chunks. | *Feb 2026* | *Technical* |
| <a id="fr-delta-009"></a>**FR-DELTA-009** | Organization imports shall support delta sync for incremental organization data updates. | *Feb 2026* | *Technical* |
| <a id="fr-delta-010"></a>**FR-DELTA-010** | Student participant syncs shall support delta sync for incremental participation record updates. | *Feb 2026* | *Technical* |
| <a id="fr-delta-011"></a>**FR-DELTA-011** | Delta sync shall apply a configurable safety buffer (default: 1 hour) to the watermark to prevent missing records modified during previous sync. | *Feb 2026* | *Technical* |
| <a id="fr-delta-012"></a>**FR-DELTA-012** | If no previous watermark exists for a sync type, the system shall automatically fall back to a full sync. | *Feb 2026* | *Technical* |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [Deployment Guide](deployment) — Operational procedures
- [Runbook](runbook) — Troubleshooting
- [Import Playbook](import_playbook) — Delta sync usage guide

---

*Last updated: February 2026 · Version 2.0* — Added Delta Sync requirements
