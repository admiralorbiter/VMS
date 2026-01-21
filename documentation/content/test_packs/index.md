# Test Packs

Comprehensive test cases for all major workflows

## Overview

This documentation contains **6 test packs** that verify functional requirements are met across the entire VMS system. Each test pack focuses on specific workflows and includes detailed test cases with expected outcomes.

## Test Pack Summary

| Pack | Title | Focus Area | Requirements Covered |
|------|-------|------------|---------------------|
| [Test Pack 1](#test-pack-1) | District Progress Dashboard | Teacher magic links + progress status validation | [FR-501](requirements#fr-501)–[FR-503](requirements#fr-503), [FR-505](requirements#fr-505)–[FR-508](requirements#fr-508), [FR-521](requirements#fr-521)–[FR-524](requirements#fr-524) |
| [Test Pack 2](#test-pack-2) | In-Person Event Publish | SF sync + website signup + email/calendar | [FR-101](requirements#fr-101)–[FR-109](requirements#fr-109), [FR-121](requirements#fr-121)–[FR-127](requirements#fr-127) |
| [Test Pack 3](#test-pack-3) | Virtual Events | Polaris creation + Pathful import + historical data | [FR-201](requirements#fr-201)–[FR-206](requirements#fr-206), [FR-208](requirements#fr-208), [FR-210](requirements#fr-210)–[FR-219](requirements#fr-219) |
| [Test Pack 4](#test-pack-4) | Volunteer Recruitment | Search + communication history + sync health | [FR-301](requirements#fr-301)–[FR-306](requirements#fr-306), [FR-308](requirements#fr-308)–[FR-309](requirements#fr-309) |
| [Test Pack 5](#test-pack-5) | Student Attendance | Roster + attendance + impact metrics | [FR-601](requirements#fr-601)–[FR-604](requirements#fr-604) |
| [Test Pack 6](#test-pack-6) | Reporting Dashboards | Exports + ad hoc queries + access control | [FR-401](requirements#fr-401)–[FR-406](requirements#fr-406), [FR-521](requirements#fr-521)–[FR-522](requirements#fr-522) |

## Test Pack Details

### Test Pack 1: District Progress Dashboard

**Focus:** Teacher magic links + progress status validation

**Coverage:**
- [FR-501](requirements#fr-501)–[FR-503](requirements#fr-503) (Dashboard)
- [FR-508](requirements#fr-508) (Status definitions)
- [FR-505](requirements#fr-505)–[FR-507](requirements#fr-507) (Magic links)
- [FR-521](requirements#fr-521)–[FR-524](requirements#fr-524) (RBAC/Scoping)

**Test Cases:** TC-001 through TC-031

[View Test Pack 1 →](#test-pack-1)

### Test Pack 2: In-Person Event Publish

**Focus:** SF sync + website signup + email/calendar

**Coverage:**
- [FR-101](requirements#fr-101)–[FR-109](requirements#fr-109) (Events + visibility)
- [FR-121](requirements#fr-121)–[FR-127](requirements#fr-127) (Signup + email)

**Test Cases:** TC-100 through TC-152

[View Test Pack 2 →](#test-pack-2)

### Test Pack 3: Virtual Events

**Focus:** Polaris creation + Pathful import + historical data

**Coverage:**
- [FR-201](requirements#fr-201)–[FR-206](requirements#fr-206) (Virtual events)
- [FR-208](requirements#fr-208) (Local/non-local)
- [FR-204](requirements#fr-204) (Historical import)
- [FR-210](requirements#fr-210)–[FR-219](requirements#fr-219) (Presenter recruitment)

**Test Cases:** TC-200 through TC-299

[View Test Pack 3 →](#test-pack-3)

### Test Pack 4: Volunteer Recruitment

**Focus:** Search + communication history + sync health

**Coverage:**
- [FR-301](requirements#fr-301)–[FR-306](requirements#fr-306) (Search + history)
- [FR-308](requirements#fr-308)–[FR-309](requirements#fr-309) (Comm sync + health UX)

**Test Cases:** TC-300 through TC-381

[View Test Pack 4 →](#test-pack-4)

### Test Pack 5: Student Attendance

**Focus:** Roster + attendance + impact metrics

**Coverage:**
- [FR-601](requirements#fr-601)–[FR-604](requirements#fr-604) (Student roster + attendance + metrics)

**Test Cases:** TC-600 through TC-691

[View Test Pack 5 →](#test-pack-5)

### Test Pack 6: Reporting Dashboards

**Focus:** Exports + ad hoc queries + access control

**Coverage:**
- [FR-401](requirements#fr-401)–[FR-406](requirements#fr-406) (Dashboards + exports)
- [FR-521](requirements#fr-521)–[FR-522](requirements#fr-522) (RBAC)

**Test Cases:** TC-700 through TC-822

[View Test Pack 6 →](#test-pack-6)

## Traceability

Each test case (TC-xxx) is linked to one or more functional requirements (FR-xxx). This bidirectional linking ensures:

- **Requirements → Tests:** Each requirement shows which test cases verify it
- **Tests → Requirements:** Each test case shows which requirements it covers

See the [Functional Requirements](#requirements) page for complete requirement-to-test mapping.

## Test Case Numbering

Test cases are organized by test pack:

- **TC-001–TC-031:** Test Pack 1 (District Progress)
- **TC-100–TC-152:** Test Pack 2 (In-Person Events)
- **TC-200–TC-299:** Test Pack 3 (Virtual Events)
- **TC-300–TC-381:** Test Pack 4 (Volunteer Recruitment)
- **TC-600–TC-691:** Test Pack 5 (Student Attendance)
- **TC-700–TC-822:** Test Pack 6 (Reporting)

## Using Test Packs

1. **For Testers:** Follow test cases in order, verify expected outcomes
2. **For Developers:** Use as acceptance criteria during development
3. **For QA:** Reference when creating automated test suites
4. **For Documentation:** Link from requirements to verify coverage

---

*Last updated: January 2026*
*Version: 1.0*
