# Test Packs

Comprehensive test cases for all major workflows

## Overview

This documentation contains **8 test packs** that verify functional requirements are met across the entire VMS system. Each test pack focuses on specific workflows and includes detailed test cases with expected outcomes.

## Test Pack Summary

| Pack | Title | Focus Area | Requirements Covered |
|------|-------|------------|---------------------|
| [Test Pack 1](#test-pack-1) | District Progress Dashboard | Teacher magic links + progress status validation | [FR-DISTRICT-501](requirements#fr-district-501)–[FR-DISTRICT-503](requirements#fr-district-503), [FR-DISTRICT-505](requirements#fr-district-505)–[FR-DISTRICT-508](requirements#fr-district-508), [FR-DISTRICT-521](requirements#fr-district-521)–[FR-DISTRICT-524](requirements#fr-district-524) |
| [Test Pack 2](#test-pack-2) | In-Person Event Public Features | Event creation + website signup + email | [FR-INPERSON-101](requirements#fr-inperson-101)–[FR-INPERSON-109](requirements#fr-inperson-109), [FR-SIGNUP-121](requirements#fr-signup-121)–[FR-SIGNUP-127](requirements#fr-signup-127) |
| [Test Pack 3](#test-pack-3) | Virtual Events | Polaris creation + Pathful import + historical data | [FR-VIRTUAL-201](requirements#fr-virtual-201)–[FR-VIRTUAL-206](requirements#fr-virtual-206), [FR-VIRTUAL-208](requirements#fr-virtual-208), [FR-VIRTUAL-210](requirements#fr-virtual-210)–[FR-VIRTUAL-219](requirements#fr-virtual-219) |
| [Test Pack 4](#test-pack-4) | Volunteer Recruitment | Search + communication history + sync health | [FR-RECRUIT-301](requirements#fr-recruit-301)–[FR-RECRUIT-306](requirements#fr-recruit-306), [FR-RECRUIT-308](requirements#fr-recruit-308)–[FR-RECRUIT-309](requirements#fr-recruit-309) |
| [Test Pack 5](#test-pack-5) | Student Attendance | Roster + attendance + impact metrics | [FR-STUDENT-601](requirements#fr-student-601)–[FR-STUDENT-604](requirements#fr-student-604) |
| [Test Pack 6](#test-pack-6) | Reporting Dashboards | Exports + ad hoc queries + access control | [FR-REPORTING-401](requirements#fr-reporting-401)–[FR-REPORTING-406](requirements#fr-reporting-406), [FR-DISTRICT-521](requirements#fr-district-521)–[FR-DISTRICT-522](requirements#fr-district-522) |
| [Test Pack 7](#test-pack-7) | Data Integrity & Operations | Duplicates + Sync + Admin Safety + Imports | [FR-DATA-901](requirements#fr-data-901)–[FR-DATA-903](requirements#fr-data-903), [FR-OPS-904](requirements#fr-ops-904)–[FR-OPS-907](requirements#fr-ops-907), [FR-INPERSON-108](requirements#fr-inperson-108)–[FR-INPERSON-133](requirements#fr-inperson-133) |
| [Test Pack 8](#test-pack-8) | Tenant Management | District Suite tenant CRUD + configuration | [FR-TENANT-101](requirements#fr-tenant-101)–[FR-TENANT-102](requirements#fr-tenant-102) |

## Test Pack Details

### Test Pack 1: District Progress Dashboard

**Focus:** Teacher magic links + progress status validation

**Coverage:**
- [FR-DISTRICT-501](requirements#fr-district-501)–[FR-DISTRICT-503](requirements#fr-district-503) (Dashboard)
- [FR-DISTRICT-508](requirements#fr-district-508) (Status definitions)
- [FR-DISTRICT-505](requirements#fr-district-505)–[FR-DISTRICT-507](requirements#fr-district-507) (Magic links)
- [FR-DISTRICT-521](requirements#fr-district-521)–[FR-DISTRICT-524](requirements#fr-district-524) (RBAC/Scoping)

**Test Cases:** TC-001 through TC-031

[View Test Pack 1 →](#test-pack-1)

### Test Pack 2: In-Person Event Public Features

**Focus:** Event creation + website signup + email

**Coverage:**
- [FR-INPERSON-101](requirements#fr-inperson-101)–[FR-INPERSON-109](requirements#fr-inperson-109) (Events + visibility)
- [FR-SIGNUP-121](requirements#fr-signup-121)–[FR-SIGNUP-127](requirements#fr-signup-127) (Signup + email)

**Test Cases:** TC-100 through TC-152

[View Test Pack 2 →](#test-pack-2)

### Test Pack 3: Virtual Events

**Focus:** Polaris creation + Pathful import + historical data

**Coverage:**
- [FR-VIRTUAL-201](requirements#fr-virtual-201)–[FR-VIRTUAL-206](requirements#fr-virtual-206) (Virtual events)
- [FR-VIRTUAL-208](requirements#fr-virtual-208) (Local/non-local)
- [FR-VIRTUAL-204](requirements#fr-virtual-204) (Historical import)
- [FR-VIRTUAL-210](requirements#fr-virtual-210)–[FR-VIRTUAL-219](requirements#fr-virtual-219) (Presenter recruitment)

**Test Cases:** TC-200 through TC-299

[View Test Pack 3 →](#test-pack-3)

### Test Pack 4: Volunteer Recruitment

**Focus:** Search + communication history + sync health

**Coverage:**
- [FR-RECRUIT-301](requirements#fr-recruit-301)–[FR-RECRUIT-306](requirements#fr-recruit-306) (Search + history)
- [FR-RECRUIT-308](requirements#fr-recruit-308)–[FR-RECRUIT-309](requirements#fr-recruit-309) (Comm sync + health UX)

**Test Cases:** TC-300 through TC-381

[View Test Pack 4 →](#test-pack-4)

### Test Pack 5: Student Attendance

**Focus:** Roster + attendance + impact metrics

**Coverage:**
- [FR-STUDENT-601](requirements#fr-student-601)–[FR-STUDENT-604](requirements#fr-student-604) (Student roster + attendance + metrics)

**Test Cases:** TC-600 through TC-691

[View Test Pack 5 →](#test-pack-5)

### Test Pack 6: Reporting Dashboards

**Focus:** Exports + ad hoc queries + access control

**Coverage:**
- [FR-REPORTING-401](requirements#fr-reporting-401)–[FR-REPORTING-406](requirements#fr-reporting-406) (Dashboards + exports)
- [FR-DISTRICT-521](requirements#fr-district-521)–[FR-DISTRICT-522](requirements#fr-district-522) (RBAC)

**Test Cases:** TC-700 through TC-822

[View Test Pack 6 →](#test-pack-6)

### Test Pack 7: Data Integrity & Operations

**Focus:** Duplicates + Sync + Admin Safety + Import Logic

**Coverage:**
- [FR-DATA-901](requirements#fr-data-901)–[FR-DATA-903](requirements#fr-data-903) (Data Integrity)
- [FR-OPS-904](requirements#fr-ops-904)–[FR-OPS-907](requirements#fr-ops-907) (Operational Workflows)
- [FR-INPERSON-108](requirements#fr-inperson-108)–[FR-INPERSON-133](requirements#fr-inperson-133) (Scheduled Imports, Sync, Error Handling)

**Test Cases:** TC-901 through TC-913, TC-160 through TC-222

[View Test Pack 7 →](#test-pack-7)

### Test Pack 8: Tenant Management

**Focus:** District Suite tenant CRUD + configuration

**Coverage:**
- [FR-TENANT-101](requirements#fr-tenant-101) (Create tenants)
- [FR-TENANT-102](requirements#fr-tenant-102) (View/Edit/Deactivate)

**Test Cases:** TC-801 through TC-851

[View Test Pack 8 →](#test-pack-8)

## Traceability

Each test case (TC-xxx) is linked to one or more functional requirements (FR-xxx). This bidirectional linking ensures:

- **Requirements → Tests:** Each requirement shows which test cases verify it
- **Tests → Requirements:** Each test case shows which requirements it covers

See the [Functional Requirements](#requirements) page for complete requirement-to-test mapping.

## Test Case Numbering

Test cases are organized by test pack:

- **TC-001–TC-031:** Test Pack 1 (District Progress)
- **TC-100–TC-152:** Test Pack 2 (In-Person Public Features)
- **TC-160–TC-222:** Test Pack 7 (Data Ops - moved from TP2)
- **TC-200–TC-299:** Test Pack 3 (Virtual Events)
- **TC-300–TC-381:** Test Pack 4 (Volunteer Recruitment)
- **TC-600–TC-691:** Test Pack 5 (Student Attendance)
- **TC-700–TC-822:** Test Pack 6 (Reporting)
- **TC-901–TC-913:** Test Pack 7 (Data Integrity & Ops)
- **TC-801–TC-851:** Test Pack 8 (Tenant Management)

## Using Test Packs

1. **For Testers:** Follow test cases in order, verify expected outcomes
2. **For Developers:** Use as acceptance criteria during development
3. **For QA:** Reference when creating automated test suites
4. **For Documentation:** Link from requirements to verify coverage

---

*Last updated: January 2026*
*Version: 1.0*
