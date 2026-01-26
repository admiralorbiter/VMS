# Test Pack 1: District Progress Dashboard

Teacher magic links + progress status validation

> [!INFO]
> **Coverage**
> [FR-DISTRICT-501](requirements#fr-district-501)–[FR-DISTRICT-503](requirements#fr-district-503) (Dashboard), [FR-DISTRICT-508](requirements#fr-district-508) (Status definitions), [FR-DISTRICT-505](requirements#fr-district-505)–[FR-DISTRICT-507](requirements#fr-district-507) (Magic links), [FR-DISTRICT-521](requirements#fr-district-521)–[FR-DISTRICT-524](requirements#fr-district-524) (RBAC/Scoping), [FR-DISTRICT-540](requirements#fr-district-540)–[FR-DISTRICT-543](requirements#fr-district-543) (Semester Reset)

---

## Test Data Setup

**District: KCK (Test District)**

- School A, School B

#### Teacher Roster

| Teacher | Email | School | Expected Status |
|---------|-------|--------|-----------------|
| Alice Achieved | alice@kck.edu | A | **Achieved** (≥1 completed) |
| Ian InProgress | ian@kck.edu | A | **In Progress** (future signup, 0 completed) |
| Nora NotStarted | nora@kck.edu | B | **Not Started** (no signups) |
| Evan Edgecase | evan@kck.edu | B | **Achieved** (completed + future = still Achieved) |
| Zack Other | zack@other.edu | C (Other) | **Excluded** (Different district) |

## Test Cases

### A. Auth / Access Control

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-001"></a>**TC-001** | District Viewer login | Dashboard loads for own district | Automated | 2026-01-25 |
| <a id="tc-002"></a>**TC-002** | District scoping via URL tampering | Access denied to other districts (Security validation) | Automated | 2026-01-25 |
| <a id="tc-003"></a>**TC-003** | Magic link scoping | Cannot view other teachers via URL change | Manual | TBD |

### B. Dashboard Summary + Status Math

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-010"></a>**TC-010** | Summary counts | Schools=2, Teachers=4, Achieved=2, etc. | Automated (Partial) | 2026-01-25 |
| <a id="tc-011"></a>**TC-011** | School A drilldown | Shows Alice + Ian only | Automated | 2026-01-25 |
| <a id="tc-012"></a>**TC-012** | Status labels correct | Alice=Achieved, Ian=In Progress | Automated | 2026-01-25 |
| <a id="tc-013"></a>**TC-013** | Edgecase: completed + future | Evan=Achieved (precedence rule) | Automated | 2026-01-25 |
| <a id="tc-014"></a>**TC-014** | Not Started definition | Nora=Not Started | Automated | 2026-01-25 |

### C. Teacher Magic Link

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-020"></a>**TC-020** | Request for roster teacher | Email received with link | Manual | TBD |
| <a id="tc-021"></a>**TC-021** | Request for unknown email | Generic response (no roster leak) | Manual | TBD |
| <a id="tc-022"></a>**TC-022** | Link shows correct data | Alice sees Achieved status | Manual | TBD |
| <a id="tc-023"></a>**TC-023** | Flag submission | Flag stored, visible to staff | Manual | TBD |
| <a id="tc-024"></a>**TC-024** | Single-teacher scope | URL tampering fails | Manual | TBD |

### D. Roster Import

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-030"></a>**TC-030** | New teacher appears | Count increases, shows Not Started | Automated | 2026-01-25 |
| <a id="tc-031"></a>**TC-031** | Removed teacher behavior | Consistent with chosen policy (Soft Delete) | Automated | 2026-01-25 |
| <a id="tc-032"></a>**TC-032** | Auto-match by email | Teacher matched to DB record by exact email | Automated | 2026-01-25 |
| <a id="tc-033"></a>**TC-033** | Auto-match by fuzzy name | Teacher matched by name if email differs (85%+) | Automated | 2026-01-25 |
| <a id="tc-034"></a>**TC-034** | Manual match | Admin can manually link unmatched teacher | Manual | 2026-01-25 |

### E. Semester Reset

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-040"></a>**TC-040** | Semester reset on January 1 | All teacher statuses reset to "Not Started" | Automated | 2026-01-26 |
| <a id="tc-041"></a>**TC-041** | Semester reset on June 30 | All teacher statuses reset to "Not Started" | Automated | 2026-01-26 |
| <a id="tc-042"></a>**TC-042** | Archive creation | Previous semester data archived with correct counts/dates | Automated | 2026-01-26 |
| <a id="tc-043"></a>**TC-043** | Historical data viewable | Archived semester appears in historical view | Manual | 2026-01-26 |
| <a id="tc-044"></a>**TC-044** | Reset operation logging | Log entry created with timestamp and record counts | Automated | 2026-01-26 |
| <a id="tc-045"></a>**TC-045** | Reset idempotency | Running reset twice on same day does not duplicate archive | Automated | 2026-01-26 |

---

*Last updated: January 2026*
*Version: 1.1*
