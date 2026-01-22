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

- `sf_event_id` (SF Event.Id) — **join key**
- `title`
- `start_datetime`
- `end_datetime` (or duration)
- `school_id` or `school_name` (ID preferred)
- `volunteer_slots_needed`

**Recommended:** location fields (address/city/state/zip) for calendar/map

**Reference:** [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync) for complete field mappings

## Idempotency Rules

**Primary join key:** `sf_event_id`

**Idempotency rule:** Multiple sync runs → one VT event per SF event (no duplicates)

**Update rule:** SF is authoritative for mapped fields; VT overwrites on re-sync

**Exception:** VT-owned fields are preserved:
- `inperson_page_visible` (VT-controlled)
- `district_links[]` (VT-controlled)

**Reference:** [Architecture - Conflict Resolution R1](architecture#r1--in-person-event-salesforce-wins)

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
