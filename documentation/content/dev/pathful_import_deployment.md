# Pathful Import Deployment Plan

**Implementation roadmap for US-304 and US-306**

---

## Overview

This document defines the phased deployment plan for replacing the legacy Google Sheets-based virtual session import workflow with direct Pathful export ingestion. This consolidates two user stories into a single implementation path.

| User Story | Title | Status |
|------------|-------|--------|
| [US-304](user_stories#us-304) | Import Pathful export into Polaris | **Primary focus** |
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

### Phase 1: Pathful Import Implementation (US-304)

**Priority:** CRITICAL — Replaces departed staff workflow
**Timeline:** Week 1-2
**Owner:** TBD

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

**Pre-deployment validation:**

- [ ] Import route accepts Pathful CSV format
- [ ] Missing columns produce clear error message listing missing columns
- [ ] Valid rows create `EventTeacher` participation records
- [ ] Existing records updated (not duplicated) on re-import
- [ ] Unknown teachers flagged with actionable message
- [ ] Unknown events flagged with actionable message
- [ ] Import completes within acceptable time (<60s for typical file)
- [ ] Audit log captures: timestamp, filename, user, rows processed, rows flagged

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

### Phase 2: Historical Data Load (US-306)

**Priority:** HIGH — Completes reporting history
**Timeline:** Week 3
**Dependency:** Phase 1 complete

#### 2.1 Historical Load Strategy

The same import pipeline handles historical data. The only difference is the source file date range.

| Load | Date Range | Estimated Rows | Notes |
|------|------------|----------------|-------|
| Historical Year 1 | Aug 2022 - Jul 2023 | TBD | Oldest data |
| Historical Year 2 | Aug 2023 - Jul 2024 | TBD | |
| Historical Year 3 | Aug 2024 - Jul 2025 | TBD | Recent history |
| Current | Aug 2025 - Present | TBD | Already loaded in Phase 1 |

#### 2.2 Historical Load Tasks

| # | Task | Notes |
|---|------|-------|
| 1 | Obtain historical Pathful exports | Request exports by date range |
| 2 | Load Year 1 (oldest first) | Verify counts and teacher matching |
| 3 | Load Year 2 | Verify idempotency with any overlap |
| 4 | Load Year 3 | Verify idempotency with any overlap |
| 5 | Validate teacher progress | Spot-check status calculations |
| 6 | Validate reporting | Run district dashboards, verify metrics |

#### 2.3 Validation Checklist

- [ ] All historical years loaded
- [ ] No duplicate events created
- [ ] No duplicate participation records
- [ ] Teacher progress statuses calculate correctly
- [ ] District dashboards show complete history
- [ ] Unmatched teacher count is acceptable (documented)

---

### Phase 3: Process Documentation & Training

**Priority:** MEDIUM
**Timeline:** Week 3-4
**Dependency:** Phase 1 complete

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

*Last updated: January 2026*
*Version: 1.0*
