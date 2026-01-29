# Contract A: Salesforce → VolunTeach

**In-person event sync specification**

## Reference

- Field mappings in [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync)
- Monitoring in [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring)
- Architecture: [Architecture - Salesforce → VolunTeach](architecture#salesforce--volunteach)
- Use Cases: [UC-1](use_cases#uc-1), [UC-2](use_cases#uc-2)

## Purpose

Sync in-person event records from Salesforce into VolunTeach so staff can publish events to the public page, link events to districts, and power the website event listing API.

## Direction

- **Primary:** Salesforce → VolunTeach (events + updates)
- **Write-back:** None (v0.1)

## Trigger Modes

| Mode | Cadence | Notes |
|------|---------|-------|
| Scheduled sync | Hourly | Current behavior |
| Manual sync | On-demand | "Sync now" button |

**Reference:** [Architecture - Sync Cadences](architecture#sync-cadences)

## Required Fields

Incoming SF event **must** provide:

- `sf_event_id` (SF Session__c.Id) — **join key**
- `name` (SF Session__c.Name)
- `start_date` (SF Session__c.Start_Date__c)

**Additional imported fields**:
- `available_slots` (SF Session__c.Available_Slots__c) — defaults to 0
- `filled_volunteer_jobs` (SF Session__c.Filled_Volunteer_Jobs__c) — defaults to 0
- `event_type` (SF Session__c.Session_Type__c)
- `date_and_time` (SF Session__c.Date_and_Time_for_Cal__c) — display string
- `registration_link` (SF Session__c.Registration_Link__c)
- `session_status` (SF Session__c.Session_Status__c) — raw status
- `display_on_website` (SF Session__c.Display_on_Website__c) — creation only

**Reference:** [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync) for complete field mappings

## Sync Filters

Events are imported only if they meet ALL criteria:
- `Start_Date__c > TODAY` (future events only)
- `Available_Slots__c > 0` (available slots required)
- `Session_Status__c != 'Draft'` (draft sessions excluded)

## Idempotency Rules

**Primary join key:** `sf_event_id`

**Idempotency rule:** Multiple sync runs → one VT event per SF event (no duplicates)

**Update rule:** SF is authoritative for mapped fields; VT overwrites on re-sync

**Exception:** VT-owned fields are preserved:
- `display_on_website` (imported on creation, then VT-controlled)
- `status` (VT-managed: 'active' or 'archived')
- `note` (VT-only field)
- `districts` (VT-managed via EventDistrictMapping)

**Reference:** [Architecture - Conflict Resolution R1](architecture#r1--in-person-event-salesforce-wins)

## Automatic Cleanup

- **Past events deleted**: `start_date < yesterday`
- **Full events archived**: `available_slots == 0 AND filled_volunteer_jobs > 0`
- **Missing from SF deleted**: Events not in query results (includes Draft sessions)

## Error Handling

### Input validation failures

- Mark event as **SyncError** with missing fields list
- Do NOT publish invalid events to website
- Show actionable message to staff

### SF API failure

- Job status = **Failed**
- Events remain in last known good state
- UI shows "sync failed" (distinct from "no changes")

**Reference:** [Runbook - Dashboard Numbers Wrong](runbook#runbook-101-dashboard-numbers-wrong) for troubleshooting

## Retry Rules

- **Scheduled:** Exponential backoff, 3 attempts
- **Manual:** 1 immediate retry, then show failure
- **Rate-limited:** Respect SF retry-after headers

## Observability

Log per sync run:
- Start/end time
- Events processed/created/updated/failed
- Failure reasons
- Track `last_successful_sync_at`

**Reference:** [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring)

## Related Documentation

- [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync)
- [Architecture - Salesforce → VolunTeach](architecture#salesforce--volunteach)
- [Architecture - Conflict Resolution R1](architecture#r1--in-person-event-salesforce-wins)
- [Use Cases - UC-1, UC-2](use_cases#uc-1)
- [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring)

---

*Last updated: January 2026*
*Version: 1.0*
