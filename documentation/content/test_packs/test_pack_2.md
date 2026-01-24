# Test Pack 2: In-Person Event Publish

SF sync + website signup + email/calendar

> [!INFO]
> **Coverage**
> [FR-INPERSON-101](requirements#fr-inperson-101)–[FR-INPERSON-109](requirements#fr-inperson-109) (Events + visibility), [FR-INPERSON-108](requirements#fr-inperson-108), [FR-INPERSON-110](requirements#fr-inperson-110)–[FR-INPERSON-133](requirements#fr-inperson-133) (Sync, participation, status, monitoring, reporting), [FR-SIGNUP-121](requirements#fr-signup-121)–[FR-SIGNUP-127](requirements#fr-signup-127) (Signup + email)

---

## Test Data

- **E1_Public** — Full location, 5 slots
- **E2_ToggleOff** — Display toggle OFF (`display_on_website = False`), 20 slots
- **E3_DistrictOnly** — For KCK district page only

## Test Cases

### A. SF → VT Sync

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-100"></a>**TC-100** | Create and sync in-person event | Event created in SF and appears in VT with correct fields | Manual | 2026-01-22 |
| <a id="tc-101"></a>**TC-101** | Hourly sync | New event appears within cycle | Automated | TBD |
| <a id="tc-102"></a>**TC-102** | Idempotency | No duplicates on double sync | Automated | 2026-01-22 |
| <a id="tc-103"></a>**TC-103** | Update propagates | Changed slots reflected in VT | Automated | 2026-01-22 |
| <a id="tc-104"></a>**TC-104** | Failure detection | Error visible, not silent | Automated | 2026-01-22 |

> [!NOTE]
> **Test Implementation Details (VolunTeach Microservice)**
> - **TC-102 & TC-103**: Covered by `test_upcoming_event_sync.py`
>   - `test_idempotency_no_duplicates_on_double_sync` - TC-102
>   - `test_update_propagates_changed_slots_reflected` - TC-103
>   - `test_update_propagates_other_fields` - TC-103 extended
> - **TC-101**: Hourly sync runs on PythonAnywhere; email notification on failure only
> - **TC-104**: Error logging in place; errors visible to user during manual imports

### B. Publish Controls + District Linking

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-110"></a>**TC-110** | Toggle ON → public page | E1 visible on volunteer signup page | Automated | 2026-01-22 |
| <a id="tc-111"></a>**TC-111** | Toggle OFF → hidden | E1 not on public page | Automated | 2026-01-22 |
| <a id="tc-112"></a>**TC-112** | District link (toggle OFF) | E3 visible on KCK district page | Automated | 2026-01-22 |
| <a id="tc-113"></a>**TC-113** | No cross-district leak | E3 not on other district pages | Automated | 2026-01-22 |
| <a id="tc-114"></a>**TC-114** | Unlink removes | E3 gone from KCK page | Automated | 2026-01-22 |
| <a id="tc-115"></a>**TC-115** | Draft event filtering | Draft status events never imported from SF | Automated | 2026-01-22 |
| <a id="tc-116"></a>**TC-116** | DIA event filtering | DIA events imported but hidden from volunteer signup page | Automated | 2026-01-22 |
| <a id="tc-120"></a>**TC-120** | Event display fields | Public page shows slots, filled, date, district (if applicable), description | Automated | 2026-01-23 |
| <a id="tc-121"></a>**TC-121** | Field accuracy | Displayed values match Salesforce source | Automated | 2026-01-23 |

> [!NOTE]
> **Visibility Logic (VolunTeach Microservice)**
> - **Sync Filter**: Draft events (`Session_Status__c = 'Draft'`) are never imported from Salesforce
> - **Manual Toggle**: `display_on_website` boolean controls visibility on public website pages
> - **DIA Event Filtering**: DIA events are imported but excluded from volunteer signup page (shown on DIA events page instead)
> - **No Other Event Type Filtering**: Orientation, Career Day, and all other event types have no automatic filtering - manual `display_on_website` toggle controls visibility
>
> **Test Coverage:** TC-110 through TC-116 and TC-120 through TC-121 are covered by automated tests in VolunTeach microservice:
> - `test_upcoming_event_sync.py` - Salesforce sync tests (3 tests)
> - `test_visibility_and_districts.py` - Visibility toggles and district mapping tests (5 tests)
> - `test_public_page_display.py` - Public page event listing API tests (TC-120, TC-121)

### C. Signup Validation

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-130"></a>**TC-130** | Required fields | Blocked with clear error | Manual | TBD |
| <a id="tc-131"></a>**TC-131** | Email format | Invalid rejected | Manual | TBD |
| <a id="tc-132"></a>**TC-132** | Dropdown validation | Tampered values rejected | Manual | TBD |
| <a id="tc-133"></a>**TC-133** | Data sanitized | Whitespace trimmed, no XSS | Manual | TBD |

### D. Persistence + Email

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-140"></a>**TC-140** | Participation created | Record exists, linked correctly | Automated | TBD |
| <a id="tc-141"></a>**TC-141** | Values match form | All fields persisted | Automated | TBD |
| <a id="tc-142"></a>**TC-142** | Duplicate prevention | No double signups | Automated | TBD |
| <a id="tc-150"></a>**TC-150** | Confirmation email | Received with event details | Manual | TBD |
| <a id="tc-151"></a>**TC-151** | Calendar invite | Received | Manual | TBD |
| <a id="tc-152"></a>**TC-152** | Invite has location | SF location in invite | Manual | TBD |

### E. Scheduled Daily Imports

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-160"></a>**TC-160** | Daily import runs | Events, volunteer participations, and student participations imported | Automated | 2026-01-23 |
| <a id="tc-161"></a>**TC-161** | Batch processing | Large datasets processed in batches without API limit errors | Automated | 2026-01-23 |
| <a id="tc-162"></a>**TC-162** | Import status visibility | Success/failure counts and error details displayed | Automated | 2026-01-23 |

### F. Participation Sync

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-170"></a>**TC-170** | Student participation sync | EventStudentParticipation records created from Salesforce | Automated | 2026-01-23 |
| <a id="tc-171"></a>**TC-171** | Student attendance update | Status and delivery hours updated from Salesforce | Automated | 2026-01-23 |
| <a id="tc-172"></a>**TC-172** | Volunteer participation sync | Status, delivery hours, and attributes synced | Automated | 2026-01-23 |
| <a id="tc-173"></a>**TC-173** | Volunteer batch processing | Large event sets processed in batches (50 events per batch) | Automated | 2026-01-23 |

> [!NOTE]
> **About "Automated" Type for Participation Sync**
> - **Test Execution**: These tests (`tests/integration/test_participation_sync.py`) run automatically with mocked Salesforce responses
> - **Data Pull**: The actual Salesforce data import is **manual** via `scripts/daily_imports/daily_imports.py` due to large data volume
> - **Verification**: For production verification, run the daily import manually and review logs for success/error counts

### G. Unaffiliated Events

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-180"></a>**TC-180** | Identify unaffiliated events | Events missing School, District, or Parent Account identified | Automated | 2026-01-23 |
| <a id="tc-181"></a>**TC-181** | District association | Events associated with districts based on participating students | Automated | 2026-01-23 |
| <a id="tc-182"></a>**TC-182** | Unaffiliated sync completeness | Event data and volunteer/student participation records updated | Automated | 2026-01-23 |

> [!NOTE]
> **About "Automated" Type for Unaffiliated Events**
> - **Test Execution**: These tests (`tests/integration/test_unaffiliated_events.py`) run automatically with mocked Salesforce responses
> - **Data Pull**: The actual Salesforce sync is **manual** via the `/pathway-events/sync-unaffiliated-events` endpoint or `daily_imports.py`
> - **Verification**: For production verification, trigger the sync manually and verify event/participation records are created



### H. Status Management

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-190"></a>**TC-190** | Status update | Event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) updated from Salesforce | Automated | 2026-01-23 |
| <a id="tc-191"></a>**TC-191** | Cancellation reason | Cancellation reasons preserved when events cancelled in Salesforce | Automated | 2026-01-23 |
| <a id="tc-192"></a>**TC-192** | Status propagation | Status changes reflected in VolunTeach and public website within sync cycle | Automated | TBD |

> [!NOTE]
> **About "Automated" Type for Status Management**
> - **Test Execution**: These tests (`tests/integration/test_status_management.py`) run automatically with mocked Salesforce responses
> - **Data Pull**: The actual Salesforce sync is **manual** or scheduled via `daily_imports.py`
> - **Verification**: For production verification, trigger the sync and verify status updates are reflected in the UI

### I. Error Handling and Monitoring

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-200"></a>**TC-200** | Distinguish no events vs failure | System distinguishes "no events to sync" from "sync failure" | Automated | 2026-01-23 |
| <a id="tc-201"></a>**TC-201** | Failed sync logging | Failed operations logged with timestamps, error details, and record counts | Automated | 2026-01-23 |

> [!NOTE]
> **About Error Handling Tests**
> - **Test Coverage**: `tests/integration/test_sync_error_handling.py` verifies that the system correctly distinguishes between empty results (success) and API errors (failure)
> - **Logging**: Error logging is currently output to stdout/stderr in the application logs

### J. Historical Data and Manual Operations

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-210"></a>**TC-210** | Historical import | 2–4 years of past virtual events imported from Salesforce | Automated | TBD |
| <a id="tc-211"></a>**TC-211** | Historical data integrity | Event-participant relationships preserved during historical import | Automated | TBD |
| <a id="tc-212"></a>**TC-212** | Manual sync batch sizes | Manual sync processes events in configurable batch sizes | Manual | TBD |
| <a id="tc-213"></a>**TC-213** | Progress indicators | Manual sync shows progress and allows cancellation/resumption | Manual | TBD |

### K. Data Completeness and Reporting

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-220"></a>**TC-220** | Sync status indicators | Last successful sync time, record counts, and pending errors displayed | Automated | TBD |
| <a id="tc-221"></a>**TC-221** | Cache invalidation | Event sync triggers cache invalidation for dependent reports | Automated | 2026-01-23 |
| <a id="tc-222"></a>**TC-222** | Manual cache refresh | Manual cache refresh available for event-based reports with large datasets | Automated | 2026-01-23 |

---

## Detailed Test Specifications

This section provides comprehensive test specifications for requirements FR-INPERSON-106 and FR-INPERSON-108 through FR-INPERSON-133. These specifications serve as a blueprint for implementing actual tests and ensure alignment between requirements and test coverage.

### Website Display

#### FR-INPERSON-106: Website Event Display

**Covered by:** [TC-120](#tc-120), [TC-121](#tc-121)

**Objective:** Verify that the public volunteer signup page correctly displays required event fields (slots, date, district, description) and that the values accurately match the Salesforce source.

**Prerequisites:**
- Salesforce instance with test events
- VolunTeach microservice running and synced with Salesforce
- Public website API endpoint (`/events/volunteer_signup_api`) accessible

**Test Steps:**
1. Sync test events from Salesforce to VolunTeach
2. Send GET request to `/events/volunteer_signup_api`
3. Verify JSON response contains: `available_slots`, `filled_volunteer_jobs`, `start_datetime`, `name` (description/title), and `districts` (if linked)
4. Compare fields in response to origin values in Salesforce
5. Cross-check for events with and without linked districts

**Expected Results:**
- API response contains all mandatory display fields
- `available_slots` and `filled_volunteer_jobs` reflect latest Salesforce counts
- `start_datetime` matches Salesforce `Start_Date__c` (properly formatted)
- `districts` array contains the correct names of linked districts
- Events not linked to districts return an empty or null district field (optional field)
- Record data integrity is maintained across the sync pipeline

**Edge Cases:**
- Event with 0 available slots (should be handled/archived per logic)
- Event with multiple districts linked (all names should be present)
- Event with no district linked (API should handle gracefully)
- Long event descriptions (check for truncation or formatting issues)

**Integration Points:**
- VolunTeach API (`/events/volunteer_signup_api`)
- VolunTeach Database (`Event`, `EventDistrictMapping` models)
- Salesforce Source Data (`Session__c` object)

### Scheduled Imports

#### FR-INPERSON-108: Scheduled Daily Imports

**Covered by:** [TC-160](#tc-160)

**Objective:** Verify that the system supports scheduled daily imports of in-person events from Salesforce, including events, volunteer participations, and student participations.

**Prerequisites:**
- Salesforce instance with test events (minimum 5 events)
- Test volunteer participation records in Salesforce
- Test student participation records in Salesforce
- Daily import scheduler configured and enabled
- Valid Salesforce credentials configured

**Test Steps:**
1. Configure scheduled daily import to run automatically
2. Ensure Salesforce has new/modified event data since last import
3. Wait for scheduled daily import to execute (or trigger manually if within test window)
4. Monitor import process logs
5. Verify import completion status

**Expected Results:**
- Daily import executes automatically on schedule
- Events from Salesforce are imported into VolunTeach
- Volunteer participation records are imported and linked to events
- Student participation records are imported and linked to events
- All imported records match Salesforce source data
- Import process completes without fatal errors

**Edge Cases:**
- Import with no new or modified data (should complete successfully with 0 new records)
- Import during Salesforce maintenance window (should handle errors gracefully)
- Import with partial data failure (some records succeed, others fail)
- Import with network interruption (should recover or report failure)

**Integration Points:**
- Salesforce API (Session__c, Session_Participant__c objects)
- VolunTeach database (Event, EventParticipation, EventStudentParticipation models)
- Daily import scheduler (scripts/daily_imports/daily_imports.py)

#### FR-INPERSON-110: Batch Processing for Large Datasets

**Covered by:** [TC-161](#tc-161)

**Objective:** Verify that daily imports process events in batches to handle large datasets without exceeding API limits.

**Prerequisites:**
- Salesforce instance with large dataset (1000+ events)
- Batch size configuration set appropriately
- API rate limit monitoring enabled

**Test Steps:**
1. Configure batch size (e.g., 200 events per batch)
2. Trigger daily import with large dataset
3. Monitor API calls and rate limits during import
4. Observe batch processing in logs
5. Verify all records are processed

**Expected Results:**
- Import processes events in configured batch sizes
- No API rate limit errors occur
- Each batch completes before starting next batch
- All events are processed regardless of dataset size
- Batch progress is logged with batch numbers

**Edge Cases:**
- Dataset size exactly matches batch size multiple
- Dataset size is not evenly divisible by batch size (final partial batch)
- Batch processing with intermittent API failures (should retry appropriately)
- Very large dataset (10,000+ events) processing time and memory usage

**Integration Points:**
- Salesforce API rate limiting
- Batch processing logic (scripts/daily_imports/daily_imports.py)
- Database transaction handling

#### FR-INPERSON-111: Import Status Visibility

**Covered by:** [TC-162](#tc-162)

**Objective:** Verify that the system provides visibility into daily import status, success/failure counts, and error details.

**Prerequisites:**
- Daily import execution environment
- Import status monitoring interface or logs
- Test scenario with both successful and failed imports

**Test Steps:**
1. Execute daily import
2. Access import status dashboard or logs
3. Review import summary information
4. Check error details for any failures
5. Verify timestamp and duration information

**Expected Results:**
- Import status is accessible (success, in-progress, failed)
- Success count displays number of successfully imported records
- Failure count displays number of failed records
- Error details are available for each failed record
- Last import timestamp is displayed
- Import duration is recorded
- Error messages are specific and actionable

**Edge Cases:**
- Import with all records successful (no errors section)
- Import with all records failed (comprehensive error list)
- Import currently in progress (status shows in-progress)
- Import status for past imports (historical status available)

**Integration Points:**
- Daily import script logging
- Admin interface status display
- Error reporting system

### Participation Sync

#### FR-INPERSON-112: Student Participation Sync

**Covered by:** [TC-170](#tc-170)

**Objective:** Verify that the system syncs student participation data from Salesforce for in-person events, creating EventStudentParticipation records.

**Prerequisites:**
- Event exists in both Salesforce and VolunTeach
- Student exists in Salesforce (Contact__c)
- Student participation record exists in Salesforce (Session_Participant__c with Participant_Type__c = 'Student')
- Event and Student are linked in Salesforce participation record

**Test Steps:**
1. Create student participation record in Salesforce for an in-person event
2. Execute student participation sync
3. Verify EventStudentParticipation record created in VolunTeach
4. Verify participation record links to correct Event
5. Verify participation record links to correct Student
6. Verify all Salesforce fields are mapped correctly

**Expected Results:**
- EventStudentParticipation record created in local database
- Salesforce ID stored for traceability
- Record correctly linked to Event (via Salesforce Session__c)
- Record correctly linked to Student (via Salesforce Contact__c)
- All participation attributes (status, delivery hours, etc.) synced

**Edge Cases:**
- Participation for event that doesn't exist locally (should create event first or log error)
- Participation for student that doesn't exist locally (should create student first or log error)
- Duplicate participation sync (should update existing record, not create duplicate)
- Participation with missing required fields (should handle gracefully with error)

**Integration Points:**
- Salesforce Session_Participant__c object
- VolunTeach EventStudentParticipation model
- Student sync process

#### FR-INPERSON-113: Student Attendance Update

**Covered by:** [TC-171](#tc-171)

**Objective:** Verify that student participation sync updates attendance status and delivery hours from Salesforce.

**Prerequisites:**
- Existing EventStudentParticipation record in VolunTeach
- Updated attendance status in Salesforce
- Updated delivery hours in Salesforce

**Test Steps:**
1. Update student participation Status__c in Salesforce
2. Update student participation Delivery_Hours__c in Salesforce
3. Execute student participation sync
4. Verify EventStudentParticipation record updated in VolunTeach
5. Verify status field matches Salesforce value
6. Verify delivery hours field matches Salesforce value

**Expected Results:**
- Existing participation record is updated (not duplicated)
- Status field reflects Salesforce Status__c value
- Delivery hours field reflects Salesforce Delivery_Hours__c value
- Other unchanged fields remain intact
- Update timestamp is recorded

**Edge Cases:**
- Status change from Attended to No-Show
- Delivery hours changed from null to value
- Delivery hours changed from value to null
- Status with invalid enum value (should handle gracefully)

**Integration Points:**
- Salesforce Session_Participant__c fields
- VolunTeach EventStudentParticipation model
- Status enum mapping

#### FR-INPERSON-114: Volunteer Participation Sync

**Covered by:** [TC-172](#tc-172)

**Objective:** Verify that the system syncs volunteer participation data from Salesforce, including status, delivery hours, and participant attributes.

**Prerequisites:**
- Event exists in both Salesforce and VolunTeach
- Volunteer exists in Salesforce
- Volunteer participation record exists in Salesforce (Session_Participant__c with Participant_Type__c = 'Volunteer')

**Test Steps:**
1. Create volunteer participation record in Salesforce
2. Execute volunteer participation sync
3. Verify EventParticipation record created in VolunTeach
4. Verify status, delivery hours, and other attributes synced
5. Verify record links to correct Event and Volunteer

**Expected Results:**
- EventParticipation record created/updated
- Status synced from Salesforce Status__c
- Delivery hours synced from Salesforce Delivery_Hours__c
- Additional attributes synced (Age_Group__c, Title__c, Email__c)
- Record correctly linked to Event and Volunteer

**Edge Cases:**
- New participation record (create)
- Existing participation record (update)
- Participation with null optional fields
- Multiple volunteers for same event

**Integration Points:**
- Salesforce Session_Participant__c object
- VolunTeach EventParticipation model
- Volunteer sync process

#### FR-INPERSON-115: Volunteer Batch Processing

**Covered by:** [TC-173](#tc-173)

**Objective:** Verify that volunteer participation sync handles batch processing for large event sets (e.g., 50 events per batch).

**Prerequisites:**
- Multiple events (100+) with volunteer participations in Salesforce
- Batch size configured (default 50 events per batch)

**Test Steps:**
1. Configure batch size for volunteer participation sync
2. Trigger sync for large event set (100+ events)
3. Monitor batch processing in logs
4. Verify all events processed in batches
5. Verify all volunteer participations synced

**Expected Results:**
- Volunteer participations processed in batches
- Each batch contains up to configured number of events
- All batches complete successfully
- No API rate limit errors
- All volunteer participations synced regardless of batch

**Edge Cases:**
- Event count exactly matches batch size multiple
- Partial final batch
- Batch failure recovery (should continue with next batch)

**Integration Points:**
- Salesforce API batch queries
- Batch processing logic
- Error handling and retry logic

### Unaffiliated Events

#### FR-INPERSON-116: Identify Unaffiliated Events

**Covered by:** [TC-180](#tc-180)

**Objective:** Verify that the system identifies and syncs events from Salesforce that are missing School, District, or Parent Account associations.

**Prerequisites:**
- Salesforce event without School__c, District__c, or Parent_Account__c
- Salesforce event with complete associations (for comparison)
- Unaffiliated event sync process configured

**Test Steps:**
1. Create event in Salesforce without School, District, or Parent Account
2. Execute unaffiliated events sync
3. Verify system identifies unaffiliated event
4. Verify event is synced to VolunTeach
5. Verify event is flagged or handled appropriately

**Expected Results:**
- System queries Salesforce for events missing associations
- Unaffiliated events are identified in query results
- Unaffiliated events are synced to VolunTeach
- Event records are created/updated in local database
- Missing association information is noted in event record

**Edge Cases:**
- Event missing only School (has District and Parent Account)
- Event missing only District (has School and Parent Account)
- Event missing only Parent Account (has School and District)
- Event missing all three associations
- Event with partial association data

**Integration Points:**
- Salesforce Session__c queries with null filters
- Unaffiliated event sync endpoint (/pathway-events/sync-unaffiliated-events)
- Event model and district/school associations

#### FR-INPERSON-117: District Association Based on Students

**Covered by:** [TC-181](#tc-181)

**Objective:** Verify that for unaffiliated events, the system attempts to associate events with districts based on participating students.

**Prerequisites:**
- Unaffiliated event in Salesforce
- Student participation records for the event in Salesforce
- Students in Salesforce linked to districts
- Local student records with district associations

**Test Steps:**
1. Create unaffiliated event with student participations
2. Ensure students are associated with districts
3. Execute unaffiliated events sync
4. Verify system queries student participations for event
5. Verify system determines districts from student associations
6. Verify event is associated with identified district(s)

**Expected Results:**
- System queries all student participants for unaffiliated events
- System determines districts from student district associations
- Event is associated with district(s) based on student participation
- Multiple districts supported if students from different districts
- Association is persisted in local database

**Edge Cases:**
- Event with students from single district (single association)
- Event with students from multiple districts (multiple associations)
- Event with students with no district association (remains unaffiliated)
- Event with no student participations (cannot determine district)
- Event with mixed student associations (some with districts, some without)

**Integration Points:**
- Salesforce Session_Participant__c queries
- Student-district relationship mapping
- Event-district association logic

#### FR-INPERSON-118: Unaffiliated Event Sync Completeness

**Covered by:** [TC-182](#tc-182)

**Objective:** Verify that unaffiliated event sync updates both event data and associated volunteer/student participation records.

**Prerequisites:**
- Unaffiliated event in Salesforce
- Volunteer participations for event in Salesforce
- Student participations for event in Salesforce

**Test Steps:**
1. Execute unaffiliated events sync
2. Verify event data is synced
3. Verify volunteer participation records are synced
4. Verify student participation records are synced
5. Verify all records are correctly linked

**Expected Results:**
- Event record created/updated in VolunTeach
- All volunteer participations synced and linked to event
- All student participations synced and linked to event
- Event-participation relationships maintained
- District associations applied to event

**Edge Cases:**
- Event with only volunteer participations (no students)
- Event with only student participations (no volunteers)
- Event with both volunteer and student participations
- Large number of participations per event (100+)

**Integration Points:**
- Event sync process
- Volunteer participation sync
- Student participation sync
- Relationship maintenance

### Status Management

#### FR-INPERSON-119: Event Status Update

**Covered by:** [TC-190](#tc-190)

**Objective:** Verify that when syncing events, the system updates event status (Draft, Requested, Confirmed, Published, Completed, Cancelled) from Salesforce.

**Prerequisites:**
- Event in Salesforce with status
- Corresponding event in VolunTeach
- Status values available: Draft, Requested, Confirmed, Published, Completed, Cancelled

**Test Steps:**
1. Update event status in Salesforce
2. Execute event sync
3. Verify status updated in VolunTeach
4. Verify status enum mapping is correct
5. Test all status values

**Expected Results:**
- Event status synced from Salesforce Session_Status__c
- Status correctly mapped to EventStatus enum
- All status values supported (Draft, Requested, Confirmed, Published, Completed, Cancelled)
- Status change is persisted in database
- Status change timestamp recorded

**Edge Cases:**
- Status change from Draft to Published
- Status change from Published to Cancelled
- Status change from Confirmed to Completed
- Unknown status value (should default or handle gracefully)
- Null status value (should use default status)

**Integration Points:**
- Salesforce Session_Status__c field
- EventStatus enum mapping
- Event model status field

#### FR-INPERSON-120: Cancellation Reason Preservation

**Covered by:** [TC-191](#tc-191)

**Objective:** Verify that the system preserves cancellation reasons when events are cancelled in Salesforce.

**Prerequisites:**
- Event in Salesforce with Cancellation_Reason__c
- Event status set to Cancelled

**Test Steps:**
1. Cancel event in Salesforce
2. Set Cancellation_Reason__c in Salesforce
3. Execute event sync
4. Verify cancellation_reason synced to VolunTeach
5. Verify cancellation reason is preserved

**Expected Results:**
- Cancellation reason synced from Salesforce Cancellation_Reason__c
- Cancellation reason stored in event cancellation_reason field
- Cancellation reason persists even if status changes
- Cancellation reason displayed in appropriate interfaces

**Edge Cases:**
- Cancelled event without cancellation reason (null value)
- Cancelled event with custom cancellation reason
- Event re-activated after cancellation (cancellation reason may remain)
- Multiple cancellation reasons over time (should preserve latest)

**Integration Points:**
- Salesforce Cancellation_Reason__c field
- Event model cancellation_reason field
- Cancellation reason mapping/enum

#### FR-INPERSON-121: Status Change Propagation

**Covered by:** [TC-192](#tc-192)

**Objective:** Verify that status changes are reflected in VolunTeach and on public website within the sync cycle.

**Prerequisites:**
- Event in Salesforce with status
- Event synced to VolunTeach
- Event visible on public website

**Test Steps:**
1. Change event status in Salesforce
2. Execute event sync
3. Verify status updated in VolunTeach admin interface
4. Verify status reflected on public website
5. Verify propagation time is within sync cycle

**Expected Results:**
- Status change syncs within hourly sync cycle (or manual sync)
- Status visible in VolunTeach admin interface immediately after sync
- Status reflected on public website immediately after sync
- Status changes affect event visibility/behavior as appropriate
- Public website reflects correct event state

**Edge Cases:**
- Status change from Published to Cancelled (should remove from public site)
- Status change from Draft to Published (should appear on public site)
- Status change during active sync (should handle race condition)
- Multiple rapid status changes (latest status should prevail)

**Integration Points:**
- VolunTeach admin interface
- Public website event display
- Sync cycle timing
- Event visibility logic

### Error Handling and Monitoring

#### FR-INPERSON-122: Sync Failure Detection

**Covered by:** [TC-104](#tc-104), [TC-200](#tc-200)

**Objective:** Verify that the system detects and reports sync failures with detailed error messages (not silent failures).

**Prerequisites:**
- Salesforce connection configured
- Scenario to trigger sync failure (invalid credentials, network issue, etc.)

**Test Steps:**
1. Induce sync failure condition (e.g., invalid Salesforce credentials)
2. Execute sync operation
3. Verify error is detected
4. Verify detailed error message is generated
5. Verify error is reported to user/admin
6. Verify error is logged

**Expected Results:**
- Sync failures are detected and not silently ignored
- Error messages are specific and actionable
- Errors include context (which operation, which record, etc.)
- Errors are visible in admin interface or logs
- Error reporting includes timestamps and failure details

**Edge Cases:**
- Partial sync failure (some records succeed, others fail)
- Network timeout during sync
- Salesforce API rate limit exceeded
- Invalid data format from Salesforce
- Database constraint violations

**Integration Points:**
- Error handling framework
- Logging system
- Admin interface error display
- Salesforce API error handling

#### FR-INPERSON-123: Idempotent Sync Operations

**Covered by:** [TC-102](#tc-102)

**Objective:** Verify that sync operations are idempotent (no duplicates on re-sync).

**Prerequisites:**
- Event already synced to VolunTeach
- Same event exists in Salesforce

**Test Steps:**
1. Sync event from Salesforce to VolunTeach
2. Verify event exists in VolunTeach
3. Execute sync again for same event
4. Verify no duplicate event created
5. Verify existing event is updated if Salesforce data changed

**Expected Results:**
- Re-syncing same event does not create duplicate
- Existing event is updated with latest Salesforce data
- Salesforce ID is used as unique identifier
- Sync operation can be safely repeated
- No data corruption from multiple syncs

**Edge Cases:**
- Re-sync with unchanged Salesforce data
- Re-sync with modified Salesforce data
- Re-sync immediately after initial sync
- Re-sync after long time period
- Concurrent sync attempts (should handle race condition)

**Integration Points:**
- Salesforce ID uniqueness
- Database upsert logic
- Event matching/identification

#### FR-INPERSON-124: Distinguish No Events vs Sync Failure

**Covered by:** [TC-200](#tc-200)

**Objective:** Verify that the system distinguishes between "no events to sync" and "sync failure" for monitoring purposes.

**Prerequisites:**
- Salesforce connection
- Scenario with no new events (normal state)
- Scenario with sync failure (error state)

**Test Steps:**
1. Execute sync when no new events exist
2. Verify system reports "no events to sync" (not failure)
3. Induce sync failure condition
4. Execute sync
5. Verify system reports sync failure (not "no events")

**Expected Results:**
- "No events to sync" returns success status with 0 records
- Sync failure returns error status with error details
- Status indicators clearly distinguish between scenarios
- Monitoring systems can differentiate between states
- Appropriate alerts/notifications for each scenario

**Edge Cases:**
- Empty result set from valid query (no events)
- Query failure due to connection error (sync failure)
- Query failure due to permission error (sync failure)
- Query timeout (sync failure)

**Integration Points:**
- Sync status reporting
- Monitoring and alerting systems
- Error classification logic

#### FR-INPERSON-125: Failed Sync Logging

**Covered by:** [TC-201](#tc-201)

**Objective:** Verify that failed sync operations are logged with timestamps, error details, and affected record counts.

**Prerequisites:**
- Sync operation that will fail
- Logging system configured
- Access to sync logs

**Test Steps:**
1. Trigger sync operation that will fail
2. Verify failure occurs
3. Review sync logs
4. Verify timestamp is logged
5. Verify error details are logged
6. Verify record counts are logged

**Expected Results:**
- Failed sync operations are logged
- Log entries include precise timestamps
- Error messages include specific failure details
- Log entries indicate number of records attempted
- Log entries indicate number of records that failed
- Log entries include context (which sync, which records)

**Edge Cases:**
- Single record failure in batch
- Complete batch failure
- Multiple consecutive failures
- Intermittent failures over time

**Integration Points:**
- Logging framework
- Error reporting
- Audit trail system

### Historical Data Import

#### FR-VIRTUAL-220: Historical Event Import

**Covered by:** [TC-210](#tc-210)

**Objective:** Verify that the system supports importing historical virtual event data from Salesforce (e.g., 2–4 years of past events).

**Prerequisites:**
- Salesforce with historical event data (2–4 years old)
- Historical import functionality enabled
- Sufficient database storage capacity

**Test Steps:**
1. Configure historical import date range (2–4 years)
2. Execute historical import
3. Monitor import progress
4. Verify events are imported
5. Verify event dates are preserved correctly
6. Verify all historical events are imported

**Expected Results:**
- Historical events are imported successfully
- Event dates from 2–4 years ago are preserved
- All historical events within date range are imported
- Import completes without errors
- Historical data is accessible in system

**Edge Cases:**
- Very old events (5+ years)
- Events at date range boundaries
- Large volume of historical events (1000+)
- Historical events with incomplete data

**Integration Points:**
- Salesforce historical data queries
- Date range filtering
- Batch processing for large datasets

#### FR-VIRTUAL-221: Historical Data Integrity

**Covered by:** [TC-211](#tc-211)

**Objective:** Verify that historical virtual import preserves event-participant relationships and maintains data integrity.

**Prerequisites:**
- Historical events with participant records in Salesforce
- Historical import functionality

**Test Steps:**
1. Execute historical import for events with participants
2. Verify events are imported
3. Verify participant records are imported
4. Verify event-participant relationships are maintained
5. Verify data integrity (no orphaned records)

**Expected Results:**
- Historical events imported with correct relationships
- Participant records linked to correct events
- No orphaned participation records
- Relationship integrity maintained
- All relationships from Salesforce preserved

**Edge Cases:**
- Historical event with participants that don't exist locally
- Historical participant with event that doesn't exist locally
- Complex relationship structures
- Historical data with data quality issues

**Integration Points:**
- Relationship mapping logic
- Data integrity validation
- Foreign key constraints

### Manual Operations

#### FR-INPERSON-128: Manual Sync Batch Sizes

**Covered by:** [TC-212](#tc-212)

**Objective:** Verify that for large datasets, manual sync operations process events in configurable batch sizes.

**Prerequisites:**
- Large dataset of events in Salesforce (500+ events)
- Manual sync interface with batch size configuration
- Admin user access

**Test Steps:**
1. Access manual sync interface
2. Configure batch size (e.g., 100 events per batch)
3. Trigger manual sync for large dataset
4. Monitor batch processing
5. Verify events processed in configured batch sizes

**Expected Results:**
- Batch size is configurable in manual sync interface
- Manual sync respects configured batch size
- Events are processed in batches
- Progress is visible per batch
- All events are processed

**Edge Cases:**
- Batch size of 1 (very small batches)
- Batch size larger than dataset (single batch)
- Changing batch size mid-sync (should apply to remaining batches)
- Invalid batch size (should validate and reject)

**Integration Points:**
- Manual sync interface (admin UI)
- Batch processing logic
- Configuration management

#### FR-INPERSON-129: Progress Indicators and Cancellation

**Covered by:** [TC-213](#tc-213)

**Objective:** Verify that manual sync operations provide progress indicators and allow cancellation/resumption.

**Prerequisites:**
- Large dataset for manual sync
- Manual sync interface
- Long-running sync operation

**Test Steps:**
1. Start manual sync for large dataset
2. Verify progress indicator displays current progress
3. Cancel sync operation mid-way
4. Verify sync is cancelled gracefully
5. Verify partial progress is saved (if supported)
6. Verify sync can be resumed (if supported)

**Expected Results:**
- Progress indicator shows current batch/total batches
- Progress indicator shows percentage complete
- Progress indicator shows elapsed time
- Cancel button is available during sync
- Cancellation is immediate and graceful
- Partial progress is visible/accessible

**Edge Cases:**
- Cancellation during batch processing
- Cancellation during database commit
- Resume after cancellation (if supported)
- Progress indicator for very long operations

**Integration Points:**
- Manual sync interface
- Progress tracking system
- Cancellation signal handling

### Data Completeness Visibility

#### FR-INPERSON-130: Distinguish No Events vs Failure

**Covered by:** [TC-200](#tc-200)

**Objective:** Verify that the system distinguishes "no events to sync" from "event sync failure" (visibility into data completeness).

**Prerequisites:**
- Sync status monitoring interface
- Scenario with no events
- Scenario with sync failure

**Test Steps:**
1. Check sync status when no events to sync
2. Verify status indicates "no events" (not failure)
3. Induce sync failure
4. Check sync status
5. Verify status indicates failure (not "no events")

**Expected Results:**
- Status clearly distinguishes "no events" from "failure"
- "No events" shows as success with 0 count
- "Failure" shows as error with error details
- Status indicators are visually distinct
- Monitoring systems can differentiate

**Edge Cases:**
- Transition from "no events" to "failure"
- Transition from "failure" to "no events"
- Multiple consecutive "no events" states
- Intermittent failures

**Integration Points:**
- Status monitoring interface
- Sync status reporting
- Error classification

#### FR-INPERSON-131: Sync Status Indicators

**Covered by:** [TC-220](#tc-220)

**Objective:** Verify that sync status indicators show last successful sync time, record counts, and any pending errors.

**Prerequisites:**
- Sync status monitoring interface
- Completed sync operations
- Pending errors (if any)

**Test Steps:**
1. Access sync status dashboard
2. Verify last successful sync time is displayed
3. Verify record counts are displayed
4. Check for pending errors section
5. Verify error details are accessible

**Expected Results:**
- Last successful sync timestamp is displayed
- Record counts (total, successful, failed) are displayed
- Pending errors list is visible
- Error details are accessible for each error
- Status is updated in real-time or near real-time

**Edge Cases:**
- No successful syncs yet (should show appropriate message)
- Multiple pending errors
- Errors from different sync operations
- Very old last sync time

**Integration Points:**
- Sync status dashboard
- Error tracking system
- Timestamp tracking

### Reporting Integration

#### FR-INPERSON-132: Cache Invalidation on Event Sync

**Covered by:** [TC-221](#tc-221)

**Objective:** Verify that event sync operations trigger cache invalidation for reports that depend on event data.

**Prerequisites:**
- Event-based reports with cached data
- Cached report data exists
- Event sync operation

**Test Steps:**
1. Generate and cache event-based report
2. Verify cached data exists
3. Sync new/modified events
4. Verify cache is invalidated
5. Generate report again
6. Verify report uses fresh data

**Expected Results:**
- Event sync triggers cache invalidation
- Cached report data is marked as stale
- Reports regenerate with fresh data on next access
- Cache invalidation is immediate after sync
- Multiple dependent reports are invalidated

**Edge Cases:**
- Sync with no event changes (cache may remain valid)
- Partial event sync (should invalidate affected reports)
- Multiple concurrent syncs (cache invalidation should handle)
- Report generation during cache invalidation

**Integration Points:**
- Event sync process
- Cache management system
- Report generation system

#### FR-INPERSON-133: Manual Cache Refresh

**Covered by:** [TC-222](#tc-222)

**Objective:** Verify that manual cache refresh for event-based reports is available when automated sync is insufficient for large datasets.

**Prerequisites:**
- Event-based reports with cache
- Large dataset scenario
- Admin user access

**Test Steps:**
1. Access cache management interface
2. Identify event-based reports
3. Trigger manual cache refresh for event reports
4. Monitor refresh progress
5. Verify cache is refreshed
6. Verify reports use refreshed data

**Expected Results:**
- Manual cache refresh option is available
- Manual refresh can target specific report types
- Refresh process shows progress
- Refresh completes successfully
- Reports use refreshed cache data
- Refresh is available independent of sync

**Edge Cases:**
- Manual refresh during active sync
- Manual refresh for large dataset (timeout considerations)
- Manual refresh failure (should report error)
- Selective refresh (specific reports vs all reports)

**Integration Points:**
- Cache management interface (routes/management/cache_management.py)
- Cache refresh system (utils/cache_refresh_scheduler.py)
- Report generation system

---

*Last updated: January 2026*
*Version: 1.0*
