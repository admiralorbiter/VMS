# Contract C: Gmail Logging → Polaris

**Salesforce communication history sync**

## Reference

- CommunicationLog entity in [Data Dictionary - History](data_dictionary#entity-history)
- Architecture: [Architecture - Gmail Add-on → Salesforce → Polaris](architecture#gmail-add-on--salesforce--polaris)
- Import procedures: [Import Playbook - Salesforce History Import](import_playbook#playbook-d6-salesforce-history-import)

## Purpose

Staff log emails through Salesforce Gmail add-on; Polaris displays comm history per volunteer for recruitment context.

## Direction

- SF stores logged email activities
- Polaris ingests/syncs into CommunicationLog store

## Trigger Modes

- **Scheduled:** Hourly (recommended)
- **Manual:** Optional "sync comms" button

**Reference:** [Architecture - Sync Cadences](architecture#sync-cadences)

## Required Fields

- SF activity ID (for idempotency)
- Volunteer association: SF ContactId OR email address
- `sent_at` timestamp

## Idempotency

**Idempotency key:** `sf_activity_id`

**Behavior:** Re-import does not duplicate

**Reference:** [Field Mappings - Canonical Join Keys](field_mappings#canonical-join-keys)

## Association Rules

1. **Preferred:** SF ContactId maps to POL volunteer record
2. **Fallback:** Match by normalized email

**Reference:** [Field Mappings - Canonical Join Keys](field_mappings#canonical-join-keys)

## Error Handling

- Unassociated activity → store as "unmatched" for admin review OR skip with error count
- SF API fails → set comm sync health = Failed

## Sync Health UX Contract

> [!DANGER]
> **Critical UX Rule:** Polaris **must** differentiate:

- "No comms logged" — valid empty state
- "Comms sync failed" — integration failure state

**Reference:** [Architecture - Sync Cadences](architecture#sync-cadences) for sync health monitoring

## Observability

Metrics:
- New comms imported
- Duplicates skipped
- Unmatched count
- `last_successful_sync_at`
- `last_failed_sync_at` + error reason

**Reference:** [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring)

## Related Documentation

- [Architecture - Gmail Add-on → Salesforce → Polaris](architecture#gmail-add-on--salesforce--polaris)
- [Data Dictionary - History](data_dictionary#entity-history)
- [Import Playbook - Salesforce History Import](import_playbook#playbook-d6-salesforce-history-import)
- [Monitoring and Alert - Sync Timestamp Monitoring](monitoring#sync-timestamp-monitoring)

---

*Last updated: January 2026*
*Version: 1.0*
