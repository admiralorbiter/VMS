# VMS Development Status Tracker

**Last Updated:** March 2026
**Total Functional Requirements:** ~203

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | **Implemented** — Has test coverage (TC-xxx) |
| 🔧 | **Partial** — Partially implemented or needs enhancement |
| 📋 | **Pending** — TBD, not yet implemented |
| 🔮 | **Future** — Phase 5, Near-term, or Placeholder |
| ➖ | **N/A** — Implicit/contextual, no explicit testing needed |

---

## Quick Summary

| Domain | Total | ✅ | 🔧 | 📋 | 🔮 |
|--------|-------|-----|-----|-----|-----|
| [In-Person Events](#in-person-events) | 18 | 16 | 0 | 2 | 0 |
| [Virtual Events](#virtual-events) | 23 | 17 | 0 | 4 | 2 |
| [Volunteer Recruitment](#volunteer-recruitment) | 24 | 24 | 0 | 0 | 0 |
| [Reporting](#reporting) | 20 | 9 | 0 | 11 | 0 |
| [District Progress](#district-progress) | 18 | 9 | 0 | 8 | 1 |
| [Student Roster](#student-roster) | 5 | 4 | 0 | 0 | 1 |
| [Email System](#email-system) | 22 | 0 | 0 | 22 | 0 |
| [Data & Operations](#data--operations) | 35 | 35 | 0 | 0 | 0 |
| [District Suite](#district-suite) | 40 | 34 | 0 | 3 | 3 |
| [Tools](#tools) | 15 | 15 | 0 | 0 | 0 |

---

## In-Person Events

> File: [in_person.md](../requirements/in_person.md)

### Core Event Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-INPERSON-101 | Create/maintain events in Salesforce | ✅ | TC-100 |
| FR-INPERSON-102 | Hourly sync from Salesforce | ✅ | TC-101, TC-103 |
| FR-INPERSON-103 | Manual "sync now" action | ✅ | TC-100, TC-102 |
| FR-INPERSON-104 | Visibility toggle for public page | ✅ | TC-110, TC-111 |
| FR-INPERSON-105 | Support non-public events (orientations) | ✅ | TC-112 |
| FR-INPERSON-106 | Website displays event details | ✅ | TC-120, TC-121 |
| FR-INPERSON-107 | Link events to districts | ✅ | TC-113, TC-114 |
| FR-INPERSON-109 | District-linked events appear on district page | ✅ | TC-113, TC-115 |
| FR-INPERSON-128 | DIA events auto-display | ➖ | Context only |

### Reporting Integration

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-INPERSON-132 | Sync triggers cache invalidation | ✅ | TC-221 |
| FR-INPERSON-133 | Manual cache refresh for large datasets | ✅ | TC-222 |

### Public Volunteer Signup

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SIGNUP-121 | Public signup form (Form Assembly) | ✅ | TC-130–TC-140 |
| FR-SIGNUP-122 | Create participation record in Salesforce | ✅ | TC-140, TC-142 |
| FR-SIGNUP-123 | Confirmation email | ✅ | TC-150 |
| FR-SIGNUP-124 | Calendar invite | ✅ | TC-151 |
| FR-SIGNUP-125 | Calendar invite includes location/map | ✅ | TC-152 |
| FR-SIGNUP-126 | Collect demographic fields | ✅ | TC-130–TC-132 |
| FR-SIGNUP-127 | Store signup attributes | ✅ | TC-141 |

---

## Virtual Events

> File: [virtual.md](../requirements/virtual.md)

### Core Virtual Event Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-VIRTUAL-201 | Create/maintain virtual events in Polaris | ✅ | TC-200, TC-201 |
| FR-VIRTUAL-202 | Tag teachers from synced records | ✅ | TC-202, TC-204 |
| FR-VIRTUAL-203 | Tag presenters from synced records | ✅ | TC-203, TC-204 |
| FR-VIRTUAL-204 | Historical import from Google Sheets | ✅ | TC-270–TC-275 |
| FR-VIRTUAL-206 | Pathful import with quality checks | ✅ | TC-250–TC-260; TD-052: alias-based org resolution via `resolve_organization()` + Unmatched Queue |
| FR-VIRTUAL-207 | Automation to pull Pathful exports | 🔮 | Near-term |
| FR-VIRTUAL-208 | Track local vs non-local volunteers | ✅ | TC-230–TC-232 |
| FR-VIRTUAL-209 | Automated comms for local volunteers | 🔮 | Near-term |
| FR-VIRTUAL-220 | Historical import from Salesforce | ✅ | TC-210 |
| FR-VIRTUAL-221 | Preserve event-participant relationships | ✅ | TC-211 |
| FR-VIRTUAL-222 | Quick Create Teacher | ✅ | TC-206 |
| FR-VIRTUAL-223 | Quick Create Presenter | ✅ | TC-207 |

### Presenter Recruitment View

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-VIRTUAL-210 | List events without presenter | ✅ | TC-290–TC-299 |
| FR-VIRTUAL-211 | Filter to future events | ✅ | TC-291 |
| FR-VIRTUAL-212 | Filter by date/school/district/type | ✅ | TC-292–TC-295 |
| FR-VIRTUAL-213 | Display event details | ✅ | TC-298 |
| FR-VIRTUAL-214 | Navigate to recruitment workflow | ✅ | TC-299 |
| FR-VIRTUAL-215 | Remove event once presenter assigned | ✅ | TC-296, TC-297 |
| FR-VIRTUAL-216 | Filter by academic year | ✅ | TC-292 |
| FR-VIRTUAL-217 | Urgency indicators (red/yellow/blue) | ✅ | TC-298 |
| FR-VIRTUAL-218 | Text search | ✅ | TC-292 |
| FR-VIRTUAL-219 | Success message when all assigned | ➖ | Context only |

### Post-Import Data Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-VIRTUAL-224 | Flag draft events with past date | ✅ | TC-285; Draft Review Queue (`/virtual/pathful/draft-review`) provides bulk promote/dismiss with confidence scoring |
| FR-VIRTUAL-225 | Flag events with no teacher | ✅ | TC-286 |
| FR-VIRTUAL-226 | Flag completed events with no presenter | ✅ | TC-287 |
| FR-VIRTUAL-227 | Cancellation reason codes | ✅ | TC-288, TC-289 |
| FR-VIRTUAL-228 | Flag cancelled without reason | ✅ | TC-290 |
| FR-VIRTUAL-229 | District admin view scoped to schools | ✅ | TC-291 |
| FR-VIRTUAL-230 | District admin tag/untag | ✅ | TC-292, TC-293 |
| FR-VIRTUAL-231 | District admin set cancellation reasons | ✅ | TC-294 |
| FR-VIRTUAL-232 | Audit logging for changes | ✅ | TC-295 |
| FR-VIRTUAL-233 | View audit logs with filters | ✅ | TC-296, TC-297 |

---

## Volunteer Recruitment

> File: [recruitment.md](../requirements/recruitment.md)

### Search & Filtering

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-RECRUIT-301 | Searchable volunteer list | ✅ | TC-300 |
| FR-RECRUIT-302 | Filter by name/org/role/skills/career | ✅ | TC-301–TC-308 |
| FR-RECRUIT-303 | Identify virtual-only participants | ✅ | TC-320–TC-322 |

### Participation & Communication History

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-RECRUIT-304 | Display participation history | ✅ | TC-340–TC-343 |
| FR-RECRUIT-305 | Display communication history | ✅ | TC-360–TC-361 |
| FR-RECRUIT-306 | Record recruitment notes | ✅ | TC-380–TC-381 |
| FR-RECRUIT-308 | Sync Salesforce email logs | ✅ | TC-360–TC-366 |
| FR-RECRUIT-309 | Distinguish no-comms vs sync failure | ✅ | TC-363, TC-364 |

### Intelligent Matching

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-RECRUIT-310 | Multi-dimensional scoring algorithm | ✅ | TC-400–TC-410 |
| FR-RECRUIT-311 | Custom keywords (highest priority) | ✅ | TC-411 |
| FR-RECRUIT-312 | Match Score Breakdown UI | ✅ | TC-412 |
| FR-RECRUIT-313 | Matching cache with manual refresh | ✅ | TC-413 |
| FR-RECRUIT-320 | Tiered keyword derivation | ✅ | TC-420 |
| FR-RECRUIT-321 | Event type-based keywords | ✅ | TC-421 |
| FR-RECRUIT-322 | Text analysis extraction | ✅ | TC-422 |
| FR-RECRUIT-323 | Pattern recognition | ✅ | TC-423 |
| FR-RECRUIT-324 | Semantic context | ✅ | TC-424 |
| FR-RECRUIT-325 | Universal fallback keywords | ✅ | TC-425 |
| FR-RECRUIT-330 | Event Type Match scoring (+1.0) | ✅ | TC-430 |
| FR-RECRUIT-331 | Skill Overlap scoring (+0.8) | ✅ | TC-431 |
| FR-RECRUIT-332 | Title/Industry Match (+0.6) | ✅ | TC-432 |
| FR-RECRUIT-333 | Connector Profile (+0.4) | ✅ | TC-433 |
| FR-RECRUIT-334 | Recency Boost | ✅ | TC-434 |
| FR-RECRUIT-335 | Frequency scoring | ✅ | TC-435 |
| FR-RECRUIT-336 | Locality scoring | ✅ | TC-436 |

---

## Reporting

> File: [reporting.md](../requirements/reporting.md)

### Dashboards

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-REPORTING-401 | Volunteer thank-you dashboard | ✅ | TC-700–TC-703 |
| FR-REPORTING-402 | Organization participation dashboard | ✅ | TC-720–TC-722 |
| FR-REPORTING-403 | District/school impact dashboards | ✅ | TC-740–TC-744 |
| FR-REPORTING-404 | Report metrics (students, volunteers, hours) | ✅ | TC-740, TC-741 |

### Ad Hoc & Export

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-REPORTING-405 | Ad hoc querying | ✅ | TC-760–TC-762 |
| FR-REPORTING-406 | Export to CSV/Excel | ✅ | TC-780–TC-783 |

### Partner Reconciliation

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-REPORTING-407 | Partner reconciliation reports | ✅ | TC-800 |
| FR-REPORTING-408 | Fuzzy name matching (difflib) | ✅ | TC-801 |
| FR-REPORTING-409 | Match categorization | ✅ | TC-802 |

### Cache Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-REPORTING-420 | Tiered cache architecture | 📋 | TBD |
| FR-REPORTING-421 | Dashboard served from cache | 📋 | TBD |
| FR-REPORTING-422 | Manual cache invalidation | 📋 | TBD |
| FR-REPORTING-423 | Cache status on admin dashboard | 📋 | TBD |
| FR-REPORTING-424 | Automatic cache warming | 📋 | TBD |
| FR-REPORTING-425 | Cache keys with filter params | 📋 | TBD |

### Year-End Reporting

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-REPORTING-430 | District Year-End Report | 📋 | TBD |
| FR-REPORTING-431 | Annual metrics aggregation | 📋 | TBD |
| FR-REPORTING-432 | Year-over-year comparison | 📋 | TBD |
| FR-REPORTING-433 | PDF/Excel export | 📋 | TBD |
| FR-REPORTING-434 | Automated generation scheduling | 📋 | TBD |

---

## District Progress

> File: [district.md](../requirements/district.md)

### Dashboard Access

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-501 | District Viewer authentication | ✅ | TC-001 |
| FR-DISTRICT-502 | Dashboard displays metrics | ✅ | TC-010 |
| FR-DISTRICT-503 | Drilldown by school | ✅ | TC-011–TC-014 |
| FR-DISTRICT-504 | Automated reminder emails | 🔮 | Placeholder |

### Teacher Self-Service

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-505 | Magic link request by email | ✅ | TC-020, TC-021 |
| FR-DISTRICT-506 | Magic link scoped to teacher | ✅ | TC-022 |
| FR-DISTRICT-507 | Flag incorrect data | ✅ | TC-023 |
| FR-DISTRICT-508 | Progress status computation | ✅ | TC-010–TC-014 |

### Access Control

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-521 | Role-based access (Admin, User, District Viewer, Teacher) | ✅ | TC-002 |
| FR-DISTRICT-522 | District-scoped access | ✅ | TC-002 |
| FR-DISTRICT-523 | Teacher magic link scoped by email | ✅ | TC-003, TC-024 |

### Teacher Roster Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-524 | Import district-provided teacher roster | ✅ | TC-030, TC-031 |
| FR-DISTRICT-531 | Auto/manual teacher matching | ✅ | Email-first + name fallback |
| FR-DISTRICT-532 | Google Sheets per district | ✅ | Implemented |

### Semester Reset & Archiving

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-540 | Auto-reset at semester start | ✅ | TC-040, TC-041 |
| FR-DISTRICT-541 | Archive before reset | ✅ | TC-042 |
| FR-DISTRICT-542 | View archived data | ✅ | TC-043 |
| FR-DISTRICT-543 | Log reset operations | ✅ | TC-044 |
| FR-DISTRICT-544 | Manual Archive Semester action | 📋 | TBD |

### Data Tracker Features

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DISTRICT-525 | District flag data issues | 📋 | TBD |
| FR-DISTRICT-526 | Teacher view session history | 📋 | TBD |
| FR-DISTRICT-527 | Teacher flag incorrect data | 📋 | TBD |
| FR-DISTRICT-528 | BugReport for data issues | 📋 | TBD |
| FR-DISTRICT-529 | Restrict flagging to TeacherProgress list | 📋 | TBD |
| FR-DISTRICT-530 | Portal landing page login options | 📋 | TBD |

---

## Student Roster

> File: [student.md](../requirements/student.md)

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-STUDENT-601 | Associate students with events | ✅ | TC-600–TC-603 |
| FR-STUDENT-602 | Record attendance status | ✅ | TC-610–TC-613 |
| FR-STUDENT-603 | Compute impact metrics | ✅ | TC-620–TC-624 |
| FR-STUDENT-604 | View metrics by district/school/type/date | ✅ | — |
| FR-STUDENT-605 | Estimate 25 students/session for virtual | ➖ | Implicit |

---

## Email System

> File: [email.md](../requirements/email.md)

### Template Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-801 | Create/manage templates | 📋 | TBD |
| FR-EMAIL-802 | HTML and plain text versions | 📋 | TBD |
| FR-EMAIL-803 | Template versioning | 📋 | TBD |
| FR-EMAIL-804 | Required/optional placeholders | 📋 | TBD |
| FR-EMAIL-805 | Preview templates | 📋 | TBD |

### Delivery Monitoring

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-810 | Delivery status dashboard | 📋 | TBD |
| FR-EMAIL-811 | Delivery metrics | 📋 | TBD |
| FR-EMAIL-812 | Track delivery attempts | 📋 | TBD |
| FR-EMAIL-813 | Filter emails | 📋 | TBD |

### Admin Email Sending

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-820 | Compose/send via admin panel | 📋 | TBD |
| FR-EMAIL-821 | Draft → Queued → Sent workflow | 📋 | TBD |
| FR-EMAIL-822 | Cancel queued emails | 📋 | TBD |

### Safety Gates

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-830 | Global kill-switch | 📋 | TBD |
| FR-EMAIL-831 | Non-prod allowlist | 📋 | TBD |
| FR-EMAIL-832 | Log blocked emails | 📋 | TBD |
| FR-EMAIL-833 | Dashboard shows safety gate status | 📋 | TBD |
| FR-EMAIL-834 | Dry-run mode | 📋 | TBD |

### Quality Assurance

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-840 | Validate recipient addresses | 📋 | TBD |
| FR-EMAIL-841 | Validate required placeholders | 📋 | TBD |
| FR-EMAIL-842 | Template rendering validation | 📋 | TBD |
| FR-EMAIL-843 | Auto-create BugReport on failure | 📋 | TBD |

### Infrastructure

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-EMAIL-850 | Mailjet integration | 📋 | TBD |
| FR-EMAIL-851 | Capture Mailjet response | 📋 | TBD |
| FR-EMAIL-852 | Secure credential storage | 📋 | TBD |

---

## Data & Operations

> File: [data_operations.md](../requirements/data_operations.md)

### Data Integrity

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DATA-901 | Duplicate management | ✅ | TC-901; Admin merge UI at `/teachers/merge` |
| FR-DATA-902 | Dynamic profile creation | ✅ | TC-902 |
| FR-DATA-903 | Sync dependencies | ✅ | TC-903, TC-904 |

### Operational Requirements

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-OPS-904 | Attendance workflow tracking | ✅ | TC-910 |
| FR-OPS-905 | Admin Purge capability | ✅ | TC-911 |
| FR-OPS-906 | Granular event categorization | ✅ | TC-913 |
| FR-OPS-907 | Auto-admin provisioning | ✅ | TC-912 |

### Data Synchronization

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-INPERSON-108 | Scheduled daily imports | ✅ | TC-160 |
| FR-INPERSON-110 | Batch processing | ✅ | TC-161 |
| FR-INPERSON-111 | Import status visibility | ✅ | TC-162 |
| FR-INPERSON-112 | Student participation sync | ✅ | TC-170 |
| FR-INPERSON-113 | Attendance status sync | ✅ | TC-171 |
| FR-INPERSON-114 | Volunteer participation sync | ✅ | TC-172 |
| FR-INPERSON-115 | Batch processing for volunteers | ✅ | TC-173 |
| FR-INPERSON-116 | Sync unaffiliated events | ✅ | TC-180 |
| FR-INPERSON-117 | Associate unaffiliated by students | ✅ | TC-181 |
| FR-INPERSON-118 | Update participation records | ✅ | TC-182 |
| FR-INPERSON-119 | Update event status | ✅ | TC-190 |
| FR-INPERSON-120 | Preserve cancellation reasons | ✅ | TC-191 |
| FR-INPERSON-121 | Reflect status changes | ✅ | TC-192 |

### Sync Error Monitoring

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-INPERSON-122 | Detect/report sync failures | ✅ | TC-104 |
| FR-INPERSON-123 | Idempotent syncs | ✅ | TC-102 |
| FR-INPERSON-124 | Distinguish no-events vs failure | ✅ | TC-200 |
| FR-INPERSON-125 | Log failed operations | ✅ | TC-201 |
| FR-INPERSON-130 | Visibility into data completeness | ✅ | TC-200 |
| FR-INPERSON-131 | Sync status indicators | ✅ | TC-220 |

### Delta Sync (Incremental Import)

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-DELTA-001 | Delta sync service (`DeltaSyncHelper`) | ✅ | Feb 2026 |
| FR-DELTA-002 | Watermark tracking in `sync_logs` | ✅ | Feb 2026 |
| FR-DELTA-003 | Events delta sync | ✅ | Feb 2026 |
| FR-DELTA-004 | Volunteers delta sync | ✅ | Feb 2026 |
| FR-DELTA-005 | History delta sync | ✅ | Feb 2026 |
| FR-DELTA-006 | Schools/Districts delta sync | ✅ | Feb 2026 |
| FR-DELTA-007 | Teachers delta sync | ✅ | Feb 2026 |
| FR-DELTA-008 | Students delta sync | ✅ | Feb 2026 |
| FR-DELTA-009 | Organizations delta sync | ✅ | Feb 2026 |
| FR-DELTA-010 | Student participants delta sync | ✅ | Feb 2026 |

---

## District Suite

> File: [district_suite.md](../requirements/district_suite.md)

### Tenant Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-TENANT-101 | Create tenant with isolated DB | ✅ | TC-801, TC-806 |
| FR-TENANT-102 | View/edit/deactivate tenants | ✅ | TC-810–TC-830 |
| FR-TENANT-103 | Route users to tenant DB | ✅ | TC-890–TC-892 |
| FR-TENANT-104 | Duplicate reference data | ✅ | TC-870–TC-875 |
| FR-TENANT-105 | PrepKC switch tenant context | ✅ | TC-893 |
| FR-TENANT-106 | Separate SQLite files per tenant | ✅ | TC-860–TC-865 |
| FR-TENANT-107 | Feature flags per tenant | ✅ | TC-806, TC-822 |

### Tenant User Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-TENANT-108 | Polaris admin manages tenant users | ✅ | TC-1200–TC-1205 |
| FR-TENANT-109 | Tenant admin manages own users | ✅ | TC-1210–TC-1215 |
| FR-TENANT-110 | Tenant role hierarchy | ✅ | TC-1201, TC-1215 |
| FR-TENANT-111 | Secure password hashing + reset | ✅ | TC-1202 |
| FR-TENANT-112 | Scoped navigation menu | ✅ | TC-1216–TC-1218 |

### Tenant Teacher Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-TENANT-113 | Import teacher rosters (CSV/Sheets) | ✅ | Via Google Sheets |
| FR-TENANT-114 | Upsert by email | ✅ | Email-first matching |
| FR-TENANT-115 | Teacher usage dashboard | ✅ | EventTeacher-primary counting |
| FR-TENANT-116 | Filter by semester | ✅ | Virtual year filter |
| FR-TENANT-117 | Excel export | 📋 | TBD |

### District Event Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SELFSERV-201 | Create events | ✅ | TC-901–TC-904 |
| FR-SELFSERV-202 | Edit events | ✅ | TC-910–TC-912 |
| FR-SELFSERV-203 | Cancel events with notifications | ✅ | TC-920, TC-921 |
| FR-SELFSERV-204 | Calendar view | ✅ | TC-940–TC-944 |
| FR-SELFSERV-205 | Searchable list view | ✅ | TC-930, TC-931 |
| FR-SELFSERV-206 | Event lifecycle statuses | ✅ | TC-903, TC-904 |

### District Volunteer Management

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SELFSERV-301 | Add/edit/view volunteer profiles | ✅ | TC-1001–TC-1008 |
| FR-SELFSERV-302 | Import volunteers (CSV/Excel) | ✅ | TC-1010–TC-1014 |
| FR-SELFSERV-303 | Search/filter volunteers | ✅ | TC-1020–TC-1024 |
| FR-SELFSERV-304 | Assign volunteers to events | ✅ | TC-1030–TC-1033 |
| FR-SELFSERV-305 | Tenant data isolation | ✅ | TC-1040–TC-1043 |

### District Recruitment Tools

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SELFSERV-401 | Recruitment dashboard | ✅ | TC-1101–TC-1104 |
| FR-SELFSERV-402 | Candidate scoring | ✅ | TC-1110–TC-1113 |
| FR-SELFSERV-403 | Log outreach attempts | ✅ | TC-1120–TC-1123 |
| FR-SELFSERV-404 | Public signup forms | ✅ | TC-1130–TC-1132 |
| FR-SELFSERV-405 | Calendar invites | ✅ | TC-1133, TC-1134 |

### PrepKC Event Visibility

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-SELFSERV-501 | View PrepKC events (read-only) | 🔮 | Phase 5 |
| FR-SELFSERV-502 | PrepKC events on calendar | 🔮 | Phase 5 |
| FR-SELFSERV-503 | PrepKC aggregate stats | 🔮 | Phase 5 |

### Public Event API

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-API-101 | GET /api/v1/district/{tenant}/events | ✅ | TC-950–TC-952 |
| FR-API-102 | GET /api/v1/district/{tenant}/events/{slug} | ✅ | TC-951 |
| FR-API-103 | API key authentication | ✅ | TC-960–TC-962 |
| FR-API-104 | Rate limits | ✅ | TC-970, TC-971 |
| FR-API-105 | CORS support | ✅ | Implemented |
| FR-API-106 | API key rotation | ✅ | TC-990, TC-991 |
| FR-API-107 | JSON response format | ✅ | TC-980, TC-982 |
| FR-API-108 | Event object schema | ✅ | TC-981 |

---

## Tools

> File: [requirements-tools.md](../requirements/requirements-tools.md)

### Newsletter Formatter

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-TOOLS-101 | Authenticated access | ✅ | `@login_required` |
| FR-TOOLS-102 | Virtual Connector Mode (default) | ✅ | Tab-based mode toggle |
| FR-TOOLS-103 | Grade-level grouping | ✅ | Parsed from title prefix |
| FR-TOOLS-104 | Date/time formatting | ✅ | E.g. "Tues., March 25th, 8:15 AM" |
| FR-TOOLS-105 | Configurable registration URL | ✅ | Editable form URL field |
| FR-TOOLS-106 | Select/deselect sessions | ✅ | Per-session + group All/None |
| FR-TOOLS-107 | Live preview panel | ✅ | Real-time HTML preview |
| FR-TOOLS-108 | Copy to clipboard (rich HTML) | ✅ | `text/html` + `text/plain` fallback |
| FR-TOOLS-109 | Default-off groups | ✅ | "General / KC Series" unchecked |
| FR-TOOLS-110 | Career Exploration Events mode | ✅ | Tab toggle, loads in-person data |
| FR-TOOLS-111 | In-person sessions API | ✅ | `/newsletter-formatter/in-person-sessions` |
| FR-TOOLS-112 | In-person section grouping | ✅ | Career Jumping/Speakers/Fair/Other |
| FR-TOOLS-113 | In-person date/time formatting | ✅ | E.g. "Thursday, April 2nd, from 8:30-10:30 AM" |
| FR-TOOLS-114 | Registration link import | ✅ | `Registration_Link__c` → hyperlinked titles |
| FR-TOOLS-115 | Virtual sessions search-and-add | ✅ | Search endpoint + cart UI + per-session Nepris links |

---

## Priority Action Items

### 🚨 High Priority (User-Facing, TBD)

1. **Email System** — All 22 FRs are TBD
2. **Reporting Cache Management** — FR-420–425 (6 FRs)
3. **Reporting Year-End** — FR-430–434 (5 FRs)
4. **District Data Tracker** — FR-525–530 (6 FRs)

### ⚡ Medium Priority

5. **District Teacher Management** — FR-531–532 *(Implemented)*
6. **Tenant Teacher Management** — FR-TENANT-117 (1 FR remaining: Excel export)
7. **Manual Archive Semester** — FR-DISTRICT-544

### 🔮 Future (Phase 5 / Near-term)

8. **Virtual Pathful Automation** — FR-VIRTUAL-207
9. **Virtual Local Volunteer Comms** — FR-VIRTUAL-209
10. **PrepKC Event Visibility** — FR-SELFSERV-501–503
11. **District Reminder Emails** — FR-DISTRICT-504

---

*This document is a living tracker. Update status as features are implemented.*
