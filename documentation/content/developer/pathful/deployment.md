# Pathful Import Deployment Plan

**Implementation roadmap for US-304 and US-306**

---

## Overview

This document defines the phased deployment plan for replacing the legacy Google Sheets-based virtual session import workflow with direct Pathful export ingestion. This consolidates two user stories into a single implementation path.

| User Story | Title | Status |
|------------|-------|--------|
| [US-304](user_stories#us-304) | Import Pathful export into Polaris | ✅ **Phase 1 Complete** |
| [US-306](user_stories#us-306) | Import historical virtual data from Google Sheets | Consolidated into US-304 |

**Related Requirements:**
- [FR-VIRTUAL-206](requirements#fr-virtual-206): Pathful data ingestion
- [FR-VIRTUAL-204](requirements#fr-virtual-204): Historical virtual event import
- [FR-VIRTUAL-207](requirements#fr-virtual-207): Automated Pathful export pulling *(near-term)*

**Related Use Cases:**
- [UC-5](use_cases#uc-5): Import Virtual Signup/Attendance

---

## Strategic Decision

> [!INFO]
> **Consolidation Rationale**
>
> The legacy workflow involved downloading Pathful data and manually reformatting it in Google Sheets before import. Since Pathful exports contain the complete historical record (2-4 years), we consolidate both user stories into a single Pathful-direct import pipeline. This eliminates the intermediate Google Sheets step and reduces manual data handling.

### Before (Legacy Flow)

```
Pathful → Manual Download → Google Sheets (manual formatting) → Polaris Import
```

### After (New Flow)

```
Pathful → Export → Polaris Import (direct)
```

---

## Deployment Phases

### Phase 1: Pathful Import Implementation (US-304) ✅ COMPLETE

**Priority:** CRITICAL — Replaces departed staff workflow
**Timeline:** Week 1-2 (Completed January 2026)
**Status:** ✅ COMPLETE

#### 1.1 Data Discovery

| Task | Description | Output |
|------|-------------|--------|
| Obtain Pathful export | Request fresh export from Pathful platform | `pathful_export_sample.csv` |
| Document column schema | Map all Pathful columns and data types | Column mapping table |
| Identify required fields | Determine minimum fields for valid import | Required fields list |
| Identify key fields | Determine composite key for idempotency | Key specification |

#### 1.2 Field Mapping Specification

**Session Report Columns (19 total):**

| Pathful Column | Polaris Field | Transform | Required |
|----------------|---------------|-----------|----------|
| Session ID | `Event.pathful_session_id` | str(), store as unique ID | Yes |
| Title | `Event.title` | strip() | Yes |
| Date | `Event.start_date` | Parse datetime (format: `YYYY-MM-DD HH:MM:SS`) | Yes |
| Status | `Event.status` | Map: Completed→COMPLETED, Draft→DRAFT, etc. | Yes |
| Duration | `Event.duration` | int(), minutes | No |
| User Auth Id | `TeacherProgress.pathful_user_id` / `Volunteer.pathful_user_id` | str() | No |
| Name | `Teacher.name` / `Volunteer.name` | Parse first/last | Yes |
| SignUp Role | *determines target model* | Educator→Teacher, Professional→Volunteer | Yes |
| School | `School.name` | Lookup or create | No |
| District or Company | `District.name` / `Organization.name` | Context-dependent | No |
| Partner | *filter only* | Only import where Partner == "PREP-KC" | Yes |
| Registered Student Count | `Event.participant_count` | int() | No |
| Attended Student Count | *for impact calculation* | int() | No |
| Career Cluster | `Event.career_cluster` (new field) | strip() | No |

**SignUp Role Distribution (27,995 PREP-KC rows):**
- Educator: 20,523 rows → Map to `TeacherProgress`
- Professional: 2,929 rows → Map to `Volunteer` (presenters)
- Student: 4,533 rows → Aggregate for counts only
- Parent: 10 rows → Skip

**Status Mapping:**
- Completed (24,068) → `EventStatus.COMPLETED`
- Draft (2,748) → `EventStatus.DRAFT`
- Published (622) → `EventStatus.PUBLISHED`
- Confirmed (361) → `EventStatus.CONFIRMED`
- Requested (196) → `EventStatus.REQUESTED`

> [!NOTE]
> **File Naming Convention**
>
> Pathful exports have dynamic filenames:
> - Session Report: `Session Report_reports_<UUID>.xlsx`
> - User Report: `User Report_reports_<UUID>.xlsx`
>
> Import should accept file uploads rather than expecting fixed filenames.

#### 1.3 Implementation Tasks

| # | Task | Acceptance Criteria | Test Coverage |
|---|------|---------------------|---------------|
| 1 | Create/modify import route | Route accepts Pathful CSV format | TC-250 |
| 2 | Implement column validation | Missing required columns → clear error message | TC-251 |
| 3 | Implement row parsing | Valid rows → participation records created | TC-252 |
| 4 | Implement teacher matching | Match by normalized email to `TeacherProgress` | TC-253 |
| 5 | Implement event matching | Match by composite key (date + identifier) | TC-254 |
| 6 | Implement unmatched handling | Unknown teachers/events → flagged, not created | TC-255 |
| 7 | Implement idempotency | Same file twice → no duplicates, updates only | TC-256 |
| 8 | Add import audit logging | Log import timestamp, row counts, user | TC-257 |

#### 1.4 Validation Checklist

**Pre-deployment validation:** ✅ All verified

- [x] Import route accepts Pathful Excel format
- [x] Missing columns produce clear error message listing missing columns
- [x] Valid rows create/update Event and TeacherProgress/Volunteer records
- [x] Existing records updated (not duplicated) on re-import via pathful_session_id
- [x] Unknown teachers flagged in PathfulUnmatchedRecord table
- [x] Unknown events flagged with actionable message
- [x] Import completes within acceptable time (<60s for typical file)
- [x] Audit log captures: timestamp, filename, user, rows processed, rows flagged

#### 1.5 Rollout

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Deploy to staging/test environment | Route accessible |
| 2 | Import test file (small sample) | Records created correctly |
| 3 | Import same file again | No duplicates |
| 4 | Import file with unknown teachers | Teachers flagged |
| 5 | Deploy to production | Route accessible |
| 6 | Import current Pathful export | Verify against expected counts |
| 7 | Document process for staff | Runbook complete |

---

### Phase A: UI Expansion — Imported Data Views ✅ IN PROGRESS

**Priority:** HIGH — Enables staff data verification
**Timeline:** January 2026 (ongoing)
**Dependency:** Phase 1 complete

This phase expands the admin UI to provide comprehensive views of imported Pathful data without requiring database queries.

#### Phase A-1: Imported Events List ✅ COMPLETE

**Route:** `/virtual/pathful/events`
**Status:** ✅ Deployed (January 29, 2026)

| Feature | Description | Status |
|---------|-------------|--------|
| Events table | Paginated list of all imported sessions | ✅ |
| Summary cards | Total events, total students | ✅ |
| Career cluster filter | Filter by career cluster | ✅ |
| Status filter | Filter by event status | ✅ |
| Search | Search by title, career cluster, Pathful ID | ✅ |
| Event detail links | Click to view event details | ✅ |

**Implementation:**
- [pathful_events.html](file:///c:/Users/admir/Github/VMS/templates/virtual/pathful_events.html)
- [pathful_import.py#pathful_events](file:///c:/Users/admir/Github/VMS/routes/virtual/pathful_import.py)

---

#### Phase A-2: User Report Import ✅ COMPLETE

**Routes:**
- `/virtual/pathful/import-users` — Upload User Report
- `/virtual/pathful/users` — View imported profiles
- `/api/pathful/users/<id>/link` — Manual linking API

**Status:** ✅ Deployed (January 30, 2026)

**Key Features:**

| Feature | Description | Status |
|---------|-------------|--------|
| Excel upload | Upload User Report exports | ✅ |
| Profile model | `PathfulUserProfile` with 20+ fields | ✅ |
| Auto-linking | Links to TeacherProgress/Volunteer by `pathful_user_id` | ✅ |
| Filtering | Filter by role (Educator/Professional), link status | ✅ |
| Detail modals | View full profile data | ✅ |

**Database Changes:**
- New table: `pathful_user_profile`
- Migration: `f2a1119853e6_add_pathful_user_profile_table.py`

**Implementation:**
- [PathfulUserProfile model](file:///c:/Users/admir/Github/VMS/models/pathful_import.py)
- [pathful_import_users.html](file:///c:/Users/admir/Github/VMS/templates/virtual/pathful_import_users.html)
- [pathful_users.html](file:///c:/Users/admir/Github/VMS/templates/virtual/pathful_users.html)

---

#### Phase A-3: Participants List ✅ COMPLETE

**Route:** `/virtual/pathful/participants`
**Status:** ✅ Deployed

| Feature | Description | Status |
|---------|-------------|--------|
| Participants table | List of matched educators & professionals | ✅ |
| Role badges | Visual distinction (Educator/Professional) | ✅ |
| Session count | Count of sessions per participant | ✅ |

---

#### Phase B: Enhanced Unmatched Record Resolution ✅ COMPLETE

**Route:** `/virtual/pathful/unmatched`
**Status:** ✅ Deployed (January 30, 2026)

| Feature | Description | Status |
|---------|-------------|--------|
| Email display | Show User Profile email in unmatched list | ✅ |
| School display | Show school from User Profile | ✅ |
| Match suggestions | Search TeacherProgress/Volunteer by email | ✅ |
| Bulk resolution | Select multiple + batch ignore (max 100) | ✅ |
| Summary stats | Pending/resolved/ignored counts | ✅ |
| Pagination | 50 records per page | ✅ |

**Implementation:**
- [get_match_suggestions()](file:///c:/Users/admir/Github/VMS/routes/virtual/pathful_import.py) helper
- [bulk_resolve_unmatched()](file:///c:/Users/admir/Github/VMS/routes/virtual/pathful_import.py) route
- [pathful_unmatched.html](file:///c:/Users/admir/Github/VMS/templates/virtual/pathful_unmatched.html)

---

#### Phase C: Advanced Audit & Analytics — FUTURE

**Priority:** LOW
**Dependency:** Phases A-B complete

| Feature | Description |
|---------|-------------|
| Import comparison | Compare imports to detect changes |
| Trend analytics | Session counts over time |
| Email-based linking | Use User Report emails for unmatched resolution |

---

### Phase 2: Historical Data Load (US-306) ✅ COMPLETE

**Priority:** HIGH — Completes reporting history
**Timeline:** Completed January 2026
**Status:** ✅ COMPLETE — 4 years of historical data loaded

#### 2.1 Historical Load Summary

All historical Pathful exports have been loaded using the Phase 1 import pipeline.

| Load | Date Range | Status |
|------|------------|--------|
| Historical Year 1 | Aug 2022 - Jul 2023 | ✅ Loaded |
| Historical Year 2 | Aug 2023 - Jul 2024 | ✅ Loaded |
| Historical Year 3 | Aug 2024 - Jul 2025 | ✅ Loaded |
| Current | Aug 2025 - Present | ✅ Loaded |

#### 2.2 Validation Checklist ✅

- [x] All historical years loaded (4 years total)
- [x] No duplicate events created (idempotent import)
- [x] No duplicate participation records
- [x] Teacher progress statuses calculate correctly
- [x] District dashboards show complete history
- [x] Unmatched records documented in PathfulUnmatchedRecord table

---

### Phase 3: Process Documentation & Training ✅ COMPLETE

**Priority:** MEDIUM
**Timeline:** Week 3-4
**Dependency:** Phase 1 complete
**Status:** ✅ **COMPLETE** (January 30, 2026)

#### 3.1 Documentation Deliverables

| Document | Audience | Location |
|----------|----------|----------|
| Import Runbook | Staff running imports | `user_guide/pathful_import` |
| Troubleshooting Guide | Staff + Dev | `user_guide/pathful_import#troubleshooting` |
| Field Mapping Reference | Dev | `field_mappings#pathful-export` |
| Contract Specification | Dev | `contract_d` (update existing) |

#### 3.2 Training

| Session | Audience | Duration | Content |
|---------|----------|----------|---------|
| Import Process | Staff | 30 min | How to obtain export, run import, verify |
| Error Handling | Staff | 15 min | What to do when teachers/events don't match |
| Technical Overview | Dev | 30 min | Code walkthrough, extension points |

---

### Phase 4: Legacy Cleanup

**Priority:** LOW
**Timeline:** Week 5+
**Dependency:** Phase 2 complete, Phase 3 complete

#### 4.1 Cleanup Tasks

| # | Task | Notes |
|---|------|-------|
| 1 | Archive Google Sheets | Set to read-only, document location |
| 2 | Remove/deprecate old import code | If separate from new code |
| 3 | Update architecture documentation | Reflect new data flow |
| 4 | Close US-306 if separate ticket | Reference US-304 as resolution |

#### 4.2 Google Sheets Archive

**Archive location:** TBD (Google Drive folder)
**Retention:** 1 year minimum (for reference if data questions arise)
**Access:** Read-only, PrepKC admin staff

---

### Phase 5: Automation (Future — FR-VIRTUAL-207)

**Priority:** NEAR-TERM (not in current scope)
**Timeline:** TBD
**Dependency:** Phase 1-3 complete

> [!INFO]
> **Future Enhancement**
>
> [FR-VIRTUAL-207](requirements#fr-virtual-207) specifies automated Pathful export pulling. This phase documents the path toward automation but is not in current deployment scope.

#### 5.1 Automation Options

| Option | Description | Complexity |
|--------|-------------|------------|
| Scheduled pull | Polaris pulls from Pathful API (if available) | Medium |
| Scheduled file pickup | Pathful drops file to shared location, Polaris picks up | Low |
| Webhook trigger | Pathful notifies Polaris when export ready | Medium |

#### 5.2 Prerequisites for Automation

- [ ] Manual import process stable (30+ days)
- [ ] Error handling robust (unattended operation)
- [ ] Alerting configured (failures notify staff)
- [ ] Pathful API or file drop mechanism confirmed

---

### Phase D: Post-Import Data Management Features

**Priority:** HIGH — Enables data quality management workflow
**Timeline:** February 2026
**Dependency:** Phases 1-3 complete
**Status:** 📋 PLANNED

> [!INFO]
> **Phase Purpose**
>
> This phase adds the tooling needed to manage virtual session data after Pathful import. It enables staff and district admins to flag issues, make corrections, set cancellation reasons, and verify data accuracy — all with full audit logging.

#### D-1: Auto-Flagging System

**Priority:** HIGH
**Dependency:** None (builds on existing import)

| Task | Description | Status |
|------|-------------|--------|
| Create `EventFlag` model | Flag type enum, resolution tracking | 📋 Planned |
| Implement flag scanner | Auto-flag after import completes | 📋 Planned |
| Create flag queue UI | `/virtual/flags` with filtering | 📋 Planned |

**Flag Types:**
- `NEEDS_ATTENTION` — Draft events with past session dates
- `MISSING_TEACHER` — Events without teacher tags
- `MISSING_PRESENTER` — Completed events without presenter
- `NEEDS_REASON` — Cancelled events without cancellation reason

**Reference:** [DEC-007](pathful_import_recommendations#dec-007)

---

#### D-2: Cancellation Reasons

**Priority:** HIGH
**Dependency:** D-1 complete

| Task | Description | Status |
|------|-------------|--------|
| Add `CancellationReason` enum | 8 predefined reasons + OTHER | 📋 Planned |
| Add Event model fields | `cancellation_reason`, `cancellation_notes` | 📋 Planned |
| Update event edit UI | Reason dropdown for cancelled events | 📋 Planned |
| Validation logic | Notes required when reason=OTHER | 📋 Planned |

**Reason Codes:** WEATHER, PRESENTER_CANCELLED, TEACHER_CANCELLED, SCHOOL_CONFLICT, TECHNICAL_ISSUES, LOW_ENROLLMENT, SCHEDULING_ERROR, OTHER

**Reference:** [DEC-008](pathful_import_recommendations#dec-008), [Cancellation Reasons Reference](user_guide/cancellation_reasons)

---

#### D-3: District Admin Access

**Priority:** HIGH
**Dependency:** D-1, D-2 complete

| Task | Description | Status |
|------|-------------|--------|
| Implement scoped queries | Filter events by user's districts | 📋 Planned |
| Add edit permissions | Can edit within scope only | 📋 Planned |
| Update event list UI | District admin sees scoped view | 📋 Planned |
| Update flag queue | District admin sees their flags | 📋 Planned |

**Editable by District Admin:**
- ✅ Tag/untag teachers and presenters
- ✅ Set cancellation reasons
- ✅ Change status: Draft → Cancelled only
- ❌ Cannot edit Pathful-owned fields (title, date, students)

**Reference:** [DEC-009](pathful_import_recommendations#dec-009)

---

#### D-4: Audit Logging

**Priority:** MEDIUM (implement alongside D-3)
**Dependency:** D-3 started

| Task | Description | Status |
|------|-------------|--------|
| Create `VirtualEventAuditLog` model | Comprehensive change tracking | 📋 Planned |
| Integrate with edit actions | Log on every change | 📋 Planned |
| Create audit view UI | `/virtual/audit/*` routes | 📋 Planned |

**Logged Actions:** TEACHER_ADDED, TEACHER_REMOVED, PRESENTER_ADDED, PRESENTER_REMOVED, STATUS_CHANGED, CANCELLATION_REASON_SET, FLAG_RESOLVED, IMPORTED

**Reference:** [DEC-010](pathful_import_recommendations#dec-010)

---

#### Phase D Rollout Checklist

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Run database migrations | Tables created |
| 2 | Deploy flag scanner | Flags created on next import |
| 3 | Deploy flag queue UI | Staff can view/resolve flags |
| 4 | Deploy cancellation reasons | Can set reasons on cancelled events |
| 5 | Create district_admin test user | User can log in |
| 6 | Deploy scoped views | District admin sees only their data |
| 7 | Deploy edit capabilities | District admin can make edits |
| 8 | Verify audit logging | All edits logged |

#### Phase D Success Criteria

| Metric | Target |
|--------|--------|
| Flag resolution rate | >80% within 7 days |
| Cancellation reason coverage | >95% of cancelled events |
| District admin adoption | 100% of districts |
| Audit completeness | 100% of edits logged |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Pathful format changes | Import breaks | Low | Version detection, column validation |
| Historical data gaps | Incomplete reporting | Medium | Reconciliation with Google Sheets if needed |
| High unmatched teacher rate | Manual cleanup needed | Medium | Pre-import teacher roster sync |
| Performance on large files | Timeout/failure | Low | Batch processing, progress indicator |
| Loss of manual corrections | Data quality issues | Medium | Document correction process (see Recommendations) |

---

## Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Import success rate | >95% of rows | Rows imported / Total rows |
| Unmatched teacher rate | <10% | Flagged teachers / Total teachers |
| Import duration | <60 seconds | For typical weekly file |
| Duplicate rate | 0% | Duplicates created / Total records |
| Staff adoption | 100% | Staff using new process vs. old |

---

## Related Documentation

- [User Stories - US-304, US-306](user_stories#us-304)
- [Requirements - FR-VIRTUAL-204, FR-VIRTUAL-206](requirements#fr-virtual-204)
- [Use Cases - UC-5](use_cases#uc-5)
- [Architecture - Pathful Integration](architecture#pathful--polaris)
- [Pathful Import Recommendations](pathful_import_recommendations) — Decision log and options analysis

---

*Last updated: January 30, 2026*
*Version: 2.1 — Added Phase B: Enhanced Unmatched Resolution*
