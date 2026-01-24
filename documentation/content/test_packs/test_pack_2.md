# Test Pack 2: In-Person Event Public Features

Event creation, Website display, Volunteer signup, and Email notifications.

> [!INFO]
> **Coverage**
> [FR-INPERSON-101](requirements#fr-inperson-101)–[FR-INPERSON-109](requirements#fr-inperson-109) (Events + visibility), [FR-SIGNUP-121](requirements#fr-signup-121)–[FR-SIGNUP-127](requirements#fr-signup-127) (Signup + email)

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
