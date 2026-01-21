# Test Pack 1: District Progress Dashboard

Teacher magic links + progress status validation

> [!INFO]
> **Coverage**
> [FR-501](requirements#fr-501)–[FR-503](requirements#fr-503) (Dashboard), [FR-508](requirements#fr-508) (Status definitions), [FR-505](requirements#fr-505)–[FR-507](requirements#fr-507) (Magic links), [FR-521](requirements#fr-521)–[FR-524](requirements#fr-524) (RBAC/Scoping)

---

## Test Data Setup

**District: KCK**

- School A, School B

#### Teacher Roster

| Teacher | Email | School | Expected Status |
|---------|-------|--------|-----------------|
| Alice Achieved | alice@kck.edu | A | **Achieved** (≥1 completed) |
| Ian InProgress | ian@kck.edu | A | **In Progress** (future signup, 0 completed) |
| Nora NotStarted | nora@kck.edu | B | **Not Started** (no signups) |
| Evan Edgecase | evan@kck.edu | B | **Achieved** (completed + future = still Achieved) |

## Test Cases

### Auth / Access Control

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-001"></a>**TC-001** | District Viewer login | Dashboard loads for own district |
| <a id="tc-002"></a>**TC-002** | District scoping via URL tampering | Access denied to other districts |
| <a id="tc-003"></a>**TC-003** | Magic link scoping | Cannot view other teachers via URL change |

### Dashboard Summary + Status Math

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-010"></a>**TC-010** | Summary counts | Schools=2, Teachers=4, Achieved=2, In Progress=1, Not Started=1 |
| <a id="tc-011"></a>**TC-011** | School A drilldown | Shows Alice + Ian only |
| <a id="tc-012"></a>**TC-012** | Status labels correct | Alice=Achieved, Ian=In Progress |
| <a id="tc-013"></a>**TC-013** | Edgecase: completed + future | Evan=Achieved (precedence rule) |
| <a id="tc-014"></a>**TC-014** | Not Started definition | Nora=Not Started |

### Teacher Magic Link

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-020"></a>**TC-020** | Request for roster teacher | Email received with link |
| <a id="tc-021"></a>**TC-021** | Request for unknown email | Generic response (no roster leak) |
| <a id="tc-022"></a>**TC-022** | Link shows correct data | Alice sees Achieved status |
| <a id="tc-023"></a>**TC-023** | Flag submission | Flag stored, visible to staff |
| <a id="tc-024"></a>**TC-024** | Single-teacher scope | URL tampering fails |

### Roster Import

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-030"></a>**TC-030** | New teacher appears | Count increases, shows Not Started |
| <a id="tc-031"></a>**TC-031** | Removed teacher behavior | Consistent with chosen policy |

---

*Last updated: January 2026*
*Version: 1.0*
