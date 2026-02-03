# Contract D: Pathful Export → Polaris

**Virtual attendance import specification**

## Reference

- Step-by-step procedures in [Import Playbook - Pathful Import](import_playbook#playbook-a-pathful-export--polaris-via-virtual-session-import)
- Teacher progress definitions in [Metrics Bible - Teacher Progress Statuses](metrics_bible#teacher-progress-statuses)
- Field mappings: [Field Mappings - Pathful Export](field_mappings#6-pathful-export--polaris)
- Architecture: [Architecture - Pathful → Polaris](architecture#pathful--polaris)
- Use Cases: [UC-5](use_cases#uc-5)

## Purpose

Import Pathful export files to update teacher session attendance/signups, driving:

- Teacher progress dashboard (Achieved/In Progress/Not Started)
- Virtual event participation stats
- Downstream reporting

## Interface

| Aspect | Current | Future |
|--------|---------|--------|
| File type | CSV or XLSX | Same |
| Delivery | Manual upload | Automated download |

## Required Columns (Semantic)

| Semantic Field | Required | Notes |
|----------------|----------|-------|
| Session identifier | ✅ | SessionId preferred |
| Event identifier | ✅ | Pathful EventId |
| Teacher email | ✅ | Normalized lowercase |
| Session start datetime | ✅ | ISO-8601 |
| Attendance status | ✅ | Or completion flag |
| Teacher name | ⛔️ | Optional |
| Presenter email | ⛔️ | Optional |

**Reference:** [Field Mappings - Pathful Export](field_mappings#6-pathful-export--polaris) for detailed column mappings

## Idempotency

**Primary key:** `external_row_id` (SessionId)

**Secondary key (if no SessionId):** `event_id + teacher_email + session_start_datetime`

**Behavior:** Re-import same file: update existing records, no duplicates. "Upcoming" → "completed": same row updated.

**Reference:** [Import Playbook - Pathful Import](import_playbook#playbook-a-pathful-export--polaris-via-virtual-session-import)

## Validation Rules

### Hard fail (entire import)

- Missing required semantic columns
- Invalid datetime format in required fields

### Row-level fail (recommended)

- Unknown teacher email → row flagged unmatched
- Unknown event ID → row flagged unmatched
- Invalid status value → row flagged

**Reference:** [Import Playbook - Common Error Resolution](import_playbook#common-error-resolution)

## Import Report

After import, Polaris must report:

- `rows processed`
- `rows created`
- `rows updated`
- `rows skipped` (duplicates)
- `rows unmatched` (teacher/event)
- `rows invalid` (bad status/date)

**Reference:** [Import Playbook - Import Log Template](import_playbook#import-log-template)

## Attendance Status Mapping

| Pathful Status | Normalized Enum |
|----------------|-----------------|
| registered, upcoming | `SignedUp` |
| attended, completed | `Attended` |
| absent, no-show | `Absent` / `NoShow` |
| canceled | `Canceled` |

**Reference:** [Metrics Bible - Teacher Progress Statuses](metrics_bible#teacher-progress-statuses)

## Related Documentation

- [Import Playbook - Pathful Import](import_playbook#playbook-a-pathful-export--polaris-via-virtual-session-import)
- [Field Mappings - Pathful Export](field_mappings#6-pathful-export--polaris)
- [Architecture - Pathful → Polaris](architecture#pathful--polaris)
- [Metrics Bible - Teacher Progress Statuses](metrics_bible#teacher-progress-statuses)
- [Use Cases - UC-5](use_cases#uc-5)
- [Runbook - Pathful Schema Change](runbook#runbook-103-pathful-schema-change)

---

*Last updated: February 2026*
*Version: 1.0*
