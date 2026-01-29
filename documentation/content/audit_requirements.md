# Audit Requirements

**What to log and how**

## Source of Truth

This document is authoritative for all audit logging requirements. Any deviation requires documented exception.

**Related Documentation:**
- [RBAC Matrix](rbac_matrix) - Access controls (Admin-only audit log viewing)
- [Privacy & Data Handling](privacy_data_handling) - Data protection and logging practices
- [Non-Functional Requirements - NFR-5](non_functional_requirements#nfr-5) - Auditability requirements

## Purpose

Audit logs provide:
- **Debugging**: Trace actions and diagnose issues
- **Accountability**: Know who did what and when
- **Security Monitoring**: Detect unauthorized access or suspicious activity
- **Operational Forensics**: Investigate incidents and understand system behavior

Audit logs are structured, queryable event records—not application logs. They focus on actions, not data.

## Core Principles

### 1. Log the action, not the data
Avoid storing full PII. Log identifiers and metadata, not sensitive content.

### 2. Every event identifies: who, what, when, where, outcome
Each audit event must include actor, action, timestamp, context, and result.

### 3. Immutable: append-only
Audit logs are never modified or deleted. They are append-only records.

### 4. Correlatable: include request_id for tracing
Include request identifiers to trace actions across systems and correlate related events.

### 5. Least access: only Admin can view (per RBAC)
Audit logs are sensitive. Only Admin users can view them per [RBAC Matrix](rbac_matrix).

## Required Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audit_event_id` | UUID | ✅ | Unique, immutable identifier |
| `timestamp` | ISO-8601 | ✅ | With timezone (UTC stored, displayed in America/Chicago) |
| `env` | String | ✅ | Environment: `prod` or `staging` |
| `actor_type` | Enum | ✅ | `user`, `system`, `service` |
| `actor_id` | String | ✅ | Internal user/service ID |
| `actor_role` | Enum | ⛔️ | `Admin`, `User`, `District`, `Teacher` (optional) |
| `actor_email_hash` | String | ⛔️ | Hashed email, not raw (optional) |
| `action` | String | ✅ | Action identifier (e.g., `vt.event.publish_toggle.updated`) |
| `resource_type` | String | ✅ | Resource type: `event`, `import_run`, `user`, etc. |
| `resource_id` | String | ✅ | The affected resource identifier |
| `request_id` | String | ✅ | Correlation ID for tracing |
| `result` | Enum | ✅ | `success` or `failure` |
| `metadata` | JSON | ⛔️ | Per-event details (optional) |

**Implementation Notes:**
- Current implementation: `models/audit_log.py` has basic fields (id, created_at, user_id, action, resource_type, resource_id, method, path, ip, meta)
- Missing fields to be added: `audit_event_id` (UUID), `env`, `actor_type`, `actor_role`, `actor_email_hash`, `request_id`, `result`
- Reference: `routes/utils.py` `log_audit_action()` function

## Required Event Categories

### A) Publishing Toggles

**Action:** `vt.event.publish_toggle.updated`

**Metadata:**
- `sf_event_id`: Salesforce event ID
- `previous_value`: Previous visibility state
- `new_value`: New visibility state
- `ui_source`: Where the change was made (e.g., `volunteach_admin`, `api`)

**When to log:**
- When `Event.inperson_page_visible` is toggled
- When event visibility changes in VolunTeach

**Reference:** [Architecture - VolunTeach → Website](architecture#volunteach--website)

### B) District Linking

**Actions:**
- `vt.event.district_link.added`
- `vt.event.district_link.removed`

**Metadata:**
- `sf_event_id`: Salesforce event ID
- `district_id`: District identifier
- `district_name`: District name (for readability)

**When to log:**
- When district is added to `Event.district_links[]`
- When district is removed from `Event.district_links[]`

**Reference:** [Architecture - VolunTeach → Website](architecture#volunteach--website)

### C) Imports

**Actions:**
- `pol.import.started`
- `pol.import.completed`
- `pol.import.failed`

**Metadata for `completed`:**
- `counts.processed`: Number of rows processed
- `counts.created`: Number of records created
- `counts.updated`: Number of records updated
- `counts.skipped`: Number of records skipped (duplicates)
- `counts.invalid`: Number of invalid records
- `import_type`: Type of import (e.g., `salesforce_volunteers`, `pathful_virtual_sessions`, `teacher_roster`)

**Metadata for `failed`:**
- `error_message`: Error description
- `error_type`: Error category
- `rows_processed_before_failure`: Number of rows processed before failure

**When to log:**
- When import process starts
- When import completes (success or failure)
- For all import types: Salesforce, Pathful, Teacher Roster

**Reference:** [Import Playbook](import_playbook)

### D) Exports

**Actions:**
- `pol.export.started`
- `pol.export.completed`

**Metadata for `completed`:**
- `export_type`: Type of export (e.g., `volunteer_list`, `district_report`, `student_aggregates`)
- `filters`: Applied filters (district, date range, etc.)
- `row_count`: Number of rows exported
- `redaction_profile`: What data was redacted (for District Viewer exports)

**When to log:**
- When export process starts
- When export completes
- Include what data was exported and any redaction applied

**Reference:** [RBAC Matrix - Export Scoping](rbac_matrix#scope-enforcement-rules)

### E) Teacher Flags

**Actions:**
- `pol.teacher_flag.created`
- `pol.teacher_flag.status.updated`

**Metadata:**
- `teacher_id`: Teacher identifier
- `teacher_email_hash`: Hashed teacher email
- `flag_type`: Type of flag (e.g., `missing_data`, `incorrect_data`)
- `previous_status`: Previous flag status (for updates)
- `new_status`: New flag status

**When to log:**
- When teacher submits a flag via magic link dashboard
- When staff updates flag status

**Reference:** [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)

### F) Permission Changes (SEV1-worthy)

**Actions:**
- `pol.rbac.user.created`
- `pol.rbac.user.disabled`
- `pol.rbac.role.updated`
- `pol.rbac.scope.updated`

**Metadata:**
- `target_user_id`: User whose permissions changed
- `target_user_email_hash`: Hashed email of target user
- `previous_role`: Previous role/security level
- `new_role`: New role/security level
- `previous_scope`: Previous scope (for scope updates)
- `new_scope`: New scope (for scope updates)

**When to log:**
- When new user is created
- When user is disabled/deactivated
- When user's role or security level changes
- When user's scope (district access) changes

**Severity:** These events are SEV1-worthy security incidents. Immediate notification may be required.

**Reference:** [RBAC Matrix](rbac_matrix)

## Retention

Minimum retention periods:

| Event Type | Minimum Retention | Notes |
|------------|------------------|-------|
| Audit events (general) | 2 years | All audit log entries |
| Security/auth events | 1 year minimum | Permission changes, user creation/disable |
| Export events | 2 years minimum | Track data exports and redaction |

**Implementation:**
- Retention policies enforced via automated cleanup jobs
- Events older than retention period are archived or deleted
- Security events may require longer retention per organizational policy

**Reference:** [Privacy & Data Handling - Retention Defaults](privacy_data_handling#retention-defaults)

## Access Control

**Who can view:**
- **Admin only** - Per [RBAC Matrix](rbac_matrix), only Admin users can view audit logs

**Implementation:**
- Route: `routes/management/management.py` `/admin/audit-logs`
- Access check: `current_user.is_admin`
- Filtering: By action, resource_type, user_id, date range

**Viewer Capabilities:**
- View audit log entries
- Filter by action, resource type, user, date range
- Export audit logs (Admin only)

**Reference:** [RBAC Matrix - Capability Matrix](rbac_matrix#capability-matrix)

## Implementation

### Current Implementation

**Model:** `models/audit_log.py`
- Basic fields: `id`, `created_at`, `user_id`, `action`, `resource_type`, `resource_id`, `method`, `path`, `ip`, `meta`
- Missing: `audit_event_id` (UUID), `env`, `actor_type`, `actor_role`, `actor_email_hash`, `request_id`, `result`

**Utility Function:** `routes/utils.py` `log_audit_action()`
- Safe to call in routes
- Non-blocking (failures don't raise exceptions)
- Captures user, action, resource, request context

**Viewer:** `routes/management/management.py` `/admin/audit-logs`
- Admin-only access
- Filtering and pagination
- Template: `templates/management/audit_logs.html`

### Future Enhancements

To fully meet these requirements:
1. Add missing schema fields (UUID, env, actor details, request_id, result)
2. Implement all required event categories
3. Add request_id generation and correlation
4. Implement retention policy enforcement
5. Add email hashing for actor_email_hash field

## Related Requirements

- [NFR-5](non_functional_requirements#nfr-5): Auditability - Key actions must be logged
- [FR-INPERSON-104](requirements#fr-inperson-104): Publishing toggle changes
- [FR-INPERSON-107](requirements#fr-inperson-107): District linking changes
- [FR-VIRTUAL-206](requirements#fr-virtual-206): Virtual session imports
- [FR-DISTRICT-507](requirements#fr-district-507): Teacher flag submissions

## Event Naming Convention

Actions use dot-separated hierarchical naming:

**Format:** `{system}.{resource}.{action}`

**Examples:**
- `vt.event.publish_toggle.updated` - VolunTeach event publish toggle
- `pol.import.completed` - Polaris import completed
- `pol.rbac.user.created` - Polaris RBAC user creation

**Systems:**
- `vt` - VolunTeach
- `pol` - Polaris
- `sf` - Salesforce (if logging SF actions)

**Resource Types:**
- `event` - Event-related actions
- `import` - Import operations
- `export` - Export operations
- `rbac` - Role-based access control
- `teacher_flag` - Teacher flag submissions

---

*Last updated: January 2026*
*Version: 1.0*
