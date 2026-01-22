# System Architecture

**Integration flows and source-of-truth ownership**

## Source of Truth

This document is authoritative for all integration design decisions. Any deviation requires documented exception.

**Related Documentation:**
- [Field Mappings](field_mappings) - Cross-system data flow specifications
- [Data Dictionary](data_dictionary) - Entity and field definitions
- [Metrics Bible](metrics_bible) - Metric calculation definitions
- [RBAC Matrix](rbac_matrix) - Role-based access control (Security section)
- [Privacy & Data Handling](privacy_data_handling) - Data protection and retention policies (Security section)

## System Context

The VMS integrates five core systems:

| System | Purpose | Owns |
|--------|---------|------|
| **Salesforce (SF)** | Core data entry, CRM, in-person events, student attendance, email logging | Event details, student data, communication logs |
| **VolunTeach (VT)** | Event sync + website publishing controls | Publish toggle, district links |
| **Website (WEB)** | Public event display + volunteer signup | Signup capture (input only) |
| **Polaris (POL)** | Virtual events, recruitment, dashboards, reporting | Virtual events, teacher roster, metrics |
| **Pathful (PATH)** | Virtual signup + reminders + attendance | Session signups, attendance status |

**Reference:** [Getting Started - Core Systems](getting_started#core-systems)

## Integration Diagram

```
(staff create)                 (publish controls)
Salesforce Events  ───────sync──────►  VolunTeach  ───API──► Website listings
│   ▲                                  │               │
│   │                                  │               └──►Volunteer Signup (public)
│   │                                  │                          │
│   │                                  └────district links────────┘
│   │
│   └────Gmail add-on logs────► SF Email Logs ──sync──► Polaris Comms History
│
└────Student attendance────► SF Student Participation ─ETL─► Polaris Reporting

Pathful (virtual signup + attendance export)
└──────────export──────────► Polaris Import ──► Teacher progress

District Roster Import ──────────────────────► Polaris ──► Dashboards + Magic Links
```

**Integration Details:**

- **SF → VolunTeach**: Event sync (idempotent on `salesforce_id`)
- **VolunTeach → Website**: API for event listings, volunteer signup
- **SF → Polaris**: Daily ETL imports (events, volunteers, students, organizations, history)
- **Pathful → Polaris**: Virtual session data via Google Sheets import
- **Website → Polaris**: Volunteer signup creates Volunteer records
- **Gmail → SF → Polaris**: Email logging syncs to Polaris History

## Source of Truth Ownership

**Golden Rule:** Every field has exactly one owner. Downstream systems copy but never edit owned fields.

| Domain | Owner | Downstream Readers | Notes |
|--------|-------|-------------------|-------|
| In-person event core fields | Salesforce | VolunTeach, Website, Polaris | Title, dates, location, status, etc. |
| In-person page visibility | VolunTeach | Website | `Event.inperson_page_visible` field |
| District event linking | VolunTeach | Website | `Event.district_links[]` array |
| Virtual event definition | Polaris | — | Created/managed in Polaris |
| Virtual attendance/signup | Pathful | Polaris (derived) | Imported via Google Sheets |
| Teacher roster (eligible set) | Polaris (import) | Dashboards, magic links | `TeacherProgress` table |
| Student attendance | Salesforce | Polaris (aggregates) | Row-level data in SF, aggregates in Polaris |
| Communication logs | Salesforce | Polaris | Email logs via Gmail add-on |
| Volunteer identity | Polaris | — | Normalized email is primary key |
| Volunteer demographics | Salesforce | Polaris | Race, gender, education, age |
| Organization data | Salesforce | Polaris | Account records |

**VT-Owned Fields (preserved during SF sync):**

- `Event.inperson_page_visible`: Boolean flag controlled by VolunTeach
- `Event.district_links[]`: Array of district links controlled by VolunTeach

**Implementation:**
- Reference: [Field Mappings](field_mappings) for detailed field mappings
- Reference: [Data Dictionary](data_dictionary) for entity definitions

## Conflict Resolution Rules

### R1 — In-person event: Salesforce wins

If SF and VT disagree on mapped fields, VT is overwritten on next sync.

**Exceptions:** VT-owned fields are preserved:
- `inperson_page_visible` (VT-controlled)
- `district_links[]` (VT-controlled)

**Implementation:**
- Sync behavior: Idempotent on `salesforce_id`
- SF edits overwrite VT on next sync
- VT-owned fields preserved during sync
- Reference: `routes/events/routes.py`, `routes/events/pathway_events.py`
- Reference: [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync)

### R2 — Volunteer identity: Polaris wins

Normalized email is the identity key. SF contact linkage is secondary.

**Implementation:**
- Primary key: `Email.email` (normalized lowercase)
- Deduplication: By normalized email
- SF linkage: `Volunteer.salesforce_individual_id` (optional, for sync)
- Reference: [Field Mappings - Canonical Join Keys](field_mappings#canonical-join-keys)

### R3 — Teacher roster: Import wins

Unmatched Pathful teachers are flagged, not auto-created. Roster name beats Pathful name.

**Implementation:**
- TeacherProgress is authoritative list
- Pathful imports match to TeacherProgress by email
- Unmatched teachers flagged, not auto-created
- Reference: [Field Mappings - Pathful Export](field_mappings#3-pathful-export--polaris)

### R4 — Teacher progress: Derived from Pathful

Achieved/In Progress/Not Started always computed from imported participation + current date.

**Implementation:**
- Calculated via `TeacherProgress.get_progress_status()`
- Uses `EventTeacher.attendance_confirmed_at` for completed sessions
- Uses `Event.start_date` for planned sessions
- Reference: [Metrics Bible - Teacher Progress Statuses](metrics_bible#teacher-progress-statuses)

### R5 — Student counts: Salesforce wins

Metrics derived from SF attendance. Polaris surfaces freshness timestamps.

**Implementation:**
- Student attendance data from Salesforce
- Polaris aggregates for reporting
- Data freshness timestamps shown in dashboards
- Reference: [Metrics Bible - Student Metrics](metrics_bible#student-metrics)

### R6 — Timezone normalization

All timestamps stored as ISO-8601 with timezone. Default: America/Chicago.

**Implementation:**
- All datetime fields: `DateTime(timezone=True)`
- Parsing: `parse_date()` function handles multiple formats
- Storage: UTC in database, displayed in America/Chicago
- Reference: [Field Mappings - Normalization Rules](field_mappings#normalization-rules-apply-everywhere)

## Sync Cadences

**Automation:** All automated syncs are managed and triggered by PythonAnywhere scheduled tasks.

| Integration | Cadence | Manual Trigger | Implementation |
|-------------|---------|----------------|----------------|
| SF → VolunTeach | Hourly | Yes | VolunTeach sync process |
| SF Comms → Polaris | Daily | Yes | `routes/history/routes.py` `/history/import-from-salesforce` |
| SF In-Person Events → Polaris | Daily | Yes | `routes/events/routes.py` `/events/import-from-salesforce` |
| SF Volunteers → Polaris | Daily | Yes | `routes/volunteers/routes.py` `/volunteers/import-from-salesforce` |
| SF Students → Polaris | Daily | Yes | `routes/students/routes.py` `/students/import-from-salesforce` |
| SF Organizations → Polaris | Daily | Yes | `routes/organizations/routes.py` `/organizations/import-from-salesforce` |
| SF Schools/Classes → Polaris | Weekly | Yes | `routes/management/management.py` import routes |
| Pathful → Polaris | Daily | Yes | `routes/virtual/routes.py` `/virtual/import-sheet` |
| Roster → Polaris | Manual (2 week cadence) | Yes | `routes/virtual/usage.py` teacher progress import |

**Daily Import Script:**
- Script: `scripts/daily_imports/daily_imports.py`
- Schedule: Daily at 2:00 AM (PythonAnywhere)
- Command: `python scripts/daily_imports/daily_imports.py --daily`
- Sequence: Organizations → Volunteers → Affiliations → Events → History

**Weekly Import Script:**
- Same script with `--weekly` flag
- Includes: Daily imports + Schools + Classes + Teachers

**Virtual Session Import:**
- Script: `scripts/daily_imports/run_virtual_import_2025_26_standalone.py`
- Schedule: As needed (often daily or weekly)
- Source: Google Sheets (configured in admin panel)

**Reference:** [Import Playbook](import_playbook) for detailed procedures

## Integration Details

### Salesforce → VolunTeach

**Purpose:** Sync in-person events for website publishing

**Flow:**
1. Staff creates event in Salesforce
2. VolunTeach syncs event (hourly or manual)
3. Staff configures publish controls in VolunTeach
4. Event appears on website based on visibility settings

**Key Fields:**
- SF owns: Event core fields (title, dates, location, etc.)
- VT owns: `inperson_page_visible`, `district_links[]`

**Sync Behavior:**
- Idempotent on `salesforce_id`
- SF edits overwrite VT on next sync
- VT-owned fields preserved during sync

**Implementation:**
- Reference: [Field Mappings - Salesforce → VolunTeach](field_mappings#1-salesforce--volunteach-in-person-sync)

### VolunTeach → Website

**Purpose:** Display events and capture volunteer signups

**Flow:**
1. VolunTeach API provides event listings
2. Website displays events based on visibility settings
3. Volunteers sign up via website forms
4. Signup data flows to Polaris (and optionally Salesforce)

**Visibility Rules:**
- `inperson_page_visible = True`: Event appears on public in-person page
- `district_links[]` contains district: Event appears on district-specific page
- Both can be true (event appears in both places)

**Implementation:**
- Website: [https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)
- Reference: [User Stories - Event Publishing](user_stories#us-102), [US-103](user_stories#us-103), [US-104](user_stories#us-104)

### Salesforce → Polaris

**Purpose:** Import core data for reporting and dashboards

**Flow:**
1. Daily import script runs at 2:00 AM
2. Connects to Salesforce API
3. Queries Contact, Event, Account records
4. Creates/updates Polaris records
5. Idempotent (safe to re-run)

**Import Types:**
- Volunteers, Teachers, Students (Contact records)
- Events (Session__c records)
- Organizations (Account records)
- History (Task and EmailMessage records)
- Schools, Classes (Account and Class records)

**Implementation:**
- Daily script: `scripts/daily_imports/daily_imports.py`
- Reference: [Import Playbook - Salesforce Imports](import_playbook#playbook-d-salesforce-imports)

### Pathful → Polaris

**Purpose:** Import virtual session attendance and update teacher progress

**Flow:**
1. Pathful exports session data
2. Data formatted in Google Sheet
3. Polaris imports via `/virtual/import-sheet`
4. Creates/updates EventTeacher records
5. Teacher progress statuses recalculated

**Implementation:**
- Route: `routes/virtual/routes.py` `/virtual/import-sheet`
- Reference: [Field Mappings - Pathful Export](field_mappings#3-pathful-export--polaris)
- Reference: [Import Playbook - Pathful Import](import_playbook#playbook-a-pathful-export--polaris-via-virtual-session-import)

### Gmail Add-on → Salesforce → Polaris

**Purpose:** Track email communications with volunteers

**Flow:**
1. Staff sends email via Gmail
2. Gmail add-on logs email to Salesforce
3. Polaris imports email logs daily
4. Email appears in volunteer communication history

**Implementation:**
- Route: `routes/history/routes.py` `/history/import-from-salesforce`
- Source: Salesforce Task and EmailMessage records
- Reference: [User Stories - Communication History](user_stories#us-404)

### Website → Polaris

**Purpose:** Create volunteer records from public signups

**Flow:**
1. Volunteer signs up on website
2. Form data creates Volunteer record in Polaris
3. Deduplication by normalized email
4. May sync to Salesforce separately

**Implementation:**
- Forms: `forms.py`
- Routes: `routes/volunteers/routes.py`
- Reference: [Field Mappings - Website Signup](field_mappings#2-website-signup--sf--polaris)

### District Roster Import → Polaris

**Purpose:** Establish teacher list for progress tracking

**Flow:**
1. Staff imports teacher roster from Google Sheet
2. Creates TeacherProgress records
3. Teachers become eligible for magic links
4. Progress tracking enabled

**Implementation:**
- Route: `routes/virtual/usage.py` teacher progress import
- Model: `models/teacher_progress.py`
- Reference: [Field Mappings - Teacher Roster Import](field_mappings#4-teacher-roster-import)

## Data Flow Diagrams

### Salesforce to Polaris Integration

```mermaid
graph LR
    SF[Salesforce API] -->|Daily Import| POL[Polaris Database]
    SF -->|Hourly Sync| VT[VolunTeach]
    VT -->|API| WEB[Public Website]
    WEB -->|Signup| POL
    PATH[Pathful Export] -->|Google Sheets| POL
    ROSTER[District Roster] -->|Import| POL
```

### Virtual Session Data Flow

```mermaid
graph LR
    PATH[Pathful Export] -->|Google Sheets| IMPORT[Polaris Import]
    IMPORT -->|Create/Update| ET[EventTeacher Records]
    ET -->|Calculate| TP[Teacher Progress]
    TP -->|Display| DASH[Dashboards]
    TP -->|Enable| ML[Magic Links]
```

### In-Person Event Publishing Flow

```mermaid
graph LR
    STAFF[Staff] -->|Create| SF[Salesforce Event]
    SF -->|Hourly Sync| VT[VolunTeach]
    STAFF -->|Configure| VT
    VT -->|API| WEB[Website]
    VOL[Volunteer] -->|Signup| WEB
    WEB -->|Create| POL[Polaris Volunteer]
```

## System URLs

| System | URL | Purpose |
|--------|-----|---------|
| **Salesforce** | [https://prep-kc.my.salesforce.com/](https://prep-kc.my.salesforce.com/) | Core CRM system |
| **VolunTeach** | [https://voluntold-prepkc.pythonanywhere.com/dashboard](https://voluntold-prepkc.pythonanywhere.com/dashboard) | Admin interface for event management |
| **Public Website** | [https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html) | Volunteer hub with signup pages |
| **Polaris** | Internal system | Virtual events, dashboards, reporting |

**Reference:** [Getting Started - System URLs](getting_started#system-urls-and-locations)

## Related Requirements

- [FR-INPERSON-108](requirements#fr-inperson-108): Scheduled daily imports
- [FR-INPERSON-110](requirements#fr-inperson-110): Batch processing for large datasets
- [FR-RECRUIT-305](requirements#fr-recruit-305): Communication history from Salesforce
- [FR-DISTRICT-501](requirements#fr-district-501): District viewer access

## Related User Stories

- [US-102](user_stories#us-102): Toggle publish visibility
- [US-104](user_stories#us-104): Link events to districts
- [US-404](user_stories#us-404): View communication history

---

*Last updated: January 2026*
*Version: 1.0*
