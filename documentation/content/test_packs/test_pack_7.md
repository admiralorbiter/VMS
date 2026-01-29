# Test Pack 7: Data Integrity & Operations

Validation of system resilience, data integrity logic, and operational workflows.

> [!INFO]
> **Coverage**
> [FR-DATA-901](requirements#fr-data-901) (Duplicates), [FR-DATA-902](requirements#fr-data-902) (Profile Creation), [FR-DATA-903](requirements#fr-data-903) (Sync Dependencies), [FR-OPS-904](requirements#fr-ops-904) (Attendance), [FR-OPS-905](requirements#fr-ops-905) (Purge), [FR-OPS-907](requirements#fr-ops-907) (Auto-Admin)

---

## Test Data Setup

**Scenario 1: Duplicate Processing**
- **Existing Event A**: SalesforceID=`SF123`, Status=`Requested`
- **Incoming Event B**: SalesforceID=`SF123`, Status=`Confirmed` (Newer timestamp)

**Scenario 2: Profile Creation**
- **Incoming Participant**: "New Volunteer", Email=`new.vol@example.com`, Role=`Professional`
- **System State**: No existing Volunteer record for this email.

## Test Cases

### Data Integrity

| TC | Description | Expected | Status | Last Verified |
|----|-------------|----------|--------|---------------|
| <a id="tc-901"></a>**TC-901** | **Duplicate Merge Strategy**<br>Import row with same SalesforceID as existing event | - Single event record remains<br>- Status updates to `Confirmed`<br>- Registered counts sum or take max based on logic | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_data_integrity.py`) |
| <a id="tc-902"></a>**TC-902** | **Profile Auto-Creation**<br>Import participant with unknown email | - New `Volunteer` record created<br>- Participation linked to new record<br>- No error returned | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_participation_sync.py`) |
| <a id="tc-903"></a>**TC-903** | **Sync Dependency Order**<br>Attempt to import Event for unknown School | - Import fails or creates placeholder (depending on config)<br>- Error logged specific to missing dependency | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_data_integrity.py`) |
| <a id="tc-904"></a>**TC-904** | **Partial Batch Success**<br>Import batch of 10 events, 1 invalid | - 9 Events created successfully<br>- 1 Error recorded in sync log<br>- Response indicates "Partial Success" | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_participation_sync.py`) |

### Operational Workflows

| TC | Description | Expected | Status | Last Verified |
|----|-------------|----------|--------|---------------|
| <a id="tc-910"></a>**TC-910** | **Attendance Status Workflow**<br>Update attendance to 'In Progress' | - `EventAttendance.status` = `IN_PROGRESS`<br>- Event `status` remains unchanged (e.g. `COMPLETED`) | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_event.py`) |
| <a id="tc-911"></a>**TC-911** | **Admin Purge Action**<br>Execute purge endpoint as Admin | - Events table count = 0<br>- Audit Log contains "PURGE" entry<br>- Non-admin user receives 403 Forbidden | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_management_routes.py`) |
| <a id="tc-912"></a>**TC-912** | **Auto-Admin Creation**<br>Start app with empty User table | - Default `admin` user created<br>- Default password hash set<br>- Log entry confirms creation | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_user.py`) |
| <a id="tc-913"></a>**TC-913** | **Event Categorization**<br>Create event with type 'Career Fair' | - Event saved with correct `EventType`<br>- Filtering by 'Career Fair' returns this event | <span style="color:green">**PASS**</span> | 2026-01-24 (Automated: `test_event.py`) |

---

*Last updated: January 2026*
*Version: 1.0*

### In-Person Data Operations

| TC | Description | Expected | Status | Last Verified |
|----|-------------|----------|--------|---------------|
| <a id="tc-160"></a>**TC-160** | **Daily Import Execution**<br>Run scheduled import job | - Events, volunteers, students imported<br>- Logs show successful execution | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_data_integrity.py`) |
| <a id="tc-161"></a>**TC-161** | **Batch Processing**<br>Import large dataset (500+ events) | - Processed in chunks (e.g., 50/batch)<br>- No API rate limit errors | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_data_integrity.py`) |
| <a id="tc-162"></a>**TC-162** | **Import Status Visibility**<br>Check status of completed import | - Status = `SUCCESS`<br>- Counts displayed for Added/Updated/Failed | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_data_integrity.py`) |
| <a id="tc-170"></a>**TC-170** | **Student Participation Sync**<br>Sync student attendance from SF | - `EventStudentParticipation` created<br>- Links correct Student and Event | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_participation_sync.py`) |
| <a id="tc-171"></a>**TC-171** | **Attendance Status Updates**<br>Update status in SF -> Sync | - Status updates in VT (e.g. Registered -> Attended)<br>- Delivery hours update | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_participation_sync.py`) |
| <a id="tc-172"></a>**TC-172** | **Volunteer Participation Sync**<br>Sync volunteer data from SF | - `EventParticipation` created<br>- Attributes (Role, Attributes) synced | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_participation_sync.py`) |
| <a id="tc-180"></a>**TC-180** | **Unaffiliated Event Sync**<br>Sync event with no District/School | - Event synced successfully<br>- Flagged as unaffiliated (opt) | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_unaffiliated_events.py`) |
| <a id="tc-181"></a>**TC-181** | **District Inference**<br>Unaffiliated event with students | - District inferred from student roster<br>- Event linked to District | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_unaffiliated_events.py`) |
| <a id="tc-190"></a>**TC-190** | **Status Sync**<br>Sync various statuses from SF | - VT Status matches SF Status map<br>- (Draft -> Requested -> Confirmed) | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_status_management.py`) |
| <a id="tc-200"></a>**TC-200** | **Empty vs Failed Sync**<br>Run sync with 0 updates | - Result = Success (0 records)<br>- Distinct from API Connection Error | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_sync_error_handling.py`) |
| <a id="tc-201"></a>**TC-201** | **Error Logging**<br>Force API error during sync | - Error logged with timestamp/details<br>- Import marked as Failed | <span style="color:green">**PASS**</span> | 2026-01-23 (Automated: `test_sync_error_handling.py`) |

---

## Detailed Test Specifications (Moved from Test Pack 2)

### Scheduled Imports

#### FR-INPERSON-108: Scheduled Daily Imports
**Covered by:** [TC-160](#tc-160)
**Objective:** Verify that the system supports scheduled daily imports of in-person events from Salesforce, including events, volunteer participations, and student participations.

### Participation Sync

#### FR-INPERSON-112: Student Participation Sync
**Covered by:** [TC-170](#tc-170)
**Objective:** Verify that the system syncs student participation data from Salesforce for in-person events, creating EventStudentParticipation records.

#### FR-INPERSON-113: Student Attendance Update
**Covered by:** [TC-171](#tc-171)
**Objective:** Verify that student participation sync updates attendance status and delivery hours from Salesforce.

### Unaffiliated Events

#### FR-INPERSON-116: Identify Unaffiliated Events
**Covered by:** [TC-180](#tc-180)
**Objective:** Verify that the system identifies and syncs events from Salesforce that are missing School, District, or Parent Account associations.

### Status Management

#### FR-INPERSON-119: Event Status Update
**Covered by:** [TC-190](#tc-190)
**Objective:** Verify that when syncing events, the system updates event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) from Salesforce.

### Error Handling

#### FR-INPERSON-122: Sync Failure Detection
**Covered by:** [TC-104](#tc-104), [TC-200](#tc-200)
**Objective:** Verify that the system detects and reports sync failures with detailed error messages (not silent failures).
