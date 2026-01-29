# Integration Contracts

**Integration boundaries and behaviors**

## Overview

Integration contracts define the boundaries and behaviors for data exchange between systems. They specify required fields, idempotency rules, error handling, and observability requirements.

**Purpose:**
- Define integration boundaries between systems
- Specify data exchange requirements
- Document error handling and retry policies
- Establish observability requirements

**Related Documentation:**
- [Architecture](architecture) - System integration flows
- [Field Mappings](field_mappings) - Detailed field-level mappings
- [Use Cases](use_cases) - End-to-end workflows
- [Import Playbook](import_playbook) - Operational procedures

## Contract Index

| Contract | Integration | Description | Related Use Cases |
|----------|-------------|-------------|-------------------|
| [Contract A](contract_a) | Salesforce → VolunTeach | In-person event sync specification | [UC-1](use_cases#uc-1), [UC-2](use_cases#uc-2) |
| [Contract B](contract_b) | Website ↔ VolunTeach API | Event display + volunteer signup | [UC-3](use_cases#uc-3) |
| [Contract C](contract_c) | Gmail Logging → Polaris | Salesforce communication history sync | — |
| [Contract D](contract_d) | Pathful Export → Polaris | Virtual attendance import specification | [UC-5](use_cases#uc-5) |

## Contract Summaries

### Contract A: Salesforce → VolunTeach

**Purpose:** Sync in-person event records from Salesforce into VolunTeach so staff can publish events to the public page, link events to districts, and power the website event listing API.

**Key Points:**
- One-way sync: Salesforce → VolunTeach
- Trigger modes: Scheduled (hourly), Manual
- Idempotent on `sf_event_id`
- SF is authoritative for mapped fields

**Reference:** [Contract A](contract_a) for complete specification

### Contract B: Website ↔ VolunTeach API

**Purpose:** Website consumes VolunTeach data to display event listings and accept volunteer signups.

**Key Points:**
- B1: Event Listing API (Read) - GET /api/events
- B2: Signup Submission API (Write) - POST /api/events/{event_id}/signup
- Visibility rules: `inperson_page_visible`, `district_links`
- Idempotent on `event_id + normalized_email`

**Reference:** [Contract B](contract_b) for complete specification

### Contract C: Gmail Logging → Polaris

**Purpose:** Staff log emails through Salesforce Gmail add-on; Polaris displays comm history per volunteer for recruitment context.

**Key Points:**
- One-way sync: Salesforce → Polaris
- Trigger modes: Scheduled (hourly), Manual
- Idempotent on `sf_activity_id`
- Association: SF ContactId preferred, email fallback

**Reference:** [Contract C](contract_c) for complete specification

### Contract D: Pathful Export → Polaris

**Purpose:** Import Pathful export files to update teacher session attendance/signups, driving teacher progress dashboard and virtual event participation stats.

**Key Points:**
- Interface: CSV/XLSX, manual upload (future: automated)
- Idempotent on `external_row_id` (SessionId) or composite key
- Row-level validation with unmatched/invalid reporting
- Status mapping: Pathful status → normalized enum

**Reference:** [Contract D](contract_d) for complete specification

## Related Documentation

- [Architecture](architecture) - System integration flows and sync cadences
- [Field Mappings](field_mappings) - Cross-system data flow specifications
- [Use Cases](use_cases) - End-to-end workflows that use these contracts
- [Import Playbook](import_playbook) - Operational procedures for imports
- [Monitoring and Alert](monitoring) - Sync timestamp monitoring

---

*Last updated: January 2026*
*Version: 1.0*
