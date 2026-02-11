# Test Pack 6: Reporting Dashboards

Exports + ad hoc queries + access control

> [!NOTE]
> **Coverage**
> [FR-REPORTING-401](requirements-reporting#fr-reporting-401)–[FR-REPORTING-406](requirements-reporting#fr-reporting-406) (Dashboards + exports), [FR-DISTRICT-521](requirements-district#fr-district-521)–[FR-DISTRICT-522](requirements-district#fr-district-522) (RBAC)

---

## Test Data: Leaderboards

| Volunteer | Events | Hours |
|-----------|--------|-------|
| V1 Victor | 4 | 10 |
| V7 Jordan | 2 | 8 |
| V6 Casey | 3 | 6 |
| V2 Ella | 2 | 3 |
| V3 Sam | 1 | 1 |

## Test Cases

### A. Volunteer Thank-You Dashboard

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-700"></a>**TC-700** | Leaderboard by hours | Victor > Jordan > Casey > Ella > Sam | Automated (Polaris) | 2026-01-25 |
| <a id="tc-701"></a>**TC-701** | Leaderboard by events | Ranked by event count | Automated (Polaris) | 2026-01-25 |
| <a id="tc-702"></a>**TC-702** | Tie handling | Consistent tie-breaker | Automated (Polaris) | 2026-01-25 |
| <a id="tc-703"></a>**TC-703** | Time range filter | Rankings update | Automated (Polaris) | 2026-01-25 | Time range filter | Rankings update |

### B. Organization Dashboard

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-720"></a>**TC-720** | Org totals | TechCorp highest | Automated (Polaris) | 2026-01-25 |
| <a id="tc-721"></a>**TC-721** | Unique org count | Correct count | Automated (Polaris) | 2026-01-25 |
| <a id="tc-722"></a>**TC-722** | Org drilldown | Lists volunteers correctly | Automated (Polaris) | 2026-01-25 |

### C. District Impact Dashboard

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-740"></a>**TC-740** | Required metrics shown | Students, volunteers, hours, orgs | Automated (Polaris) | 2026-01-25 |
| <a id="tc-741"></a>**TC-741** | Metrics match data | Numbers match fixtures | Automated (Polaris) | 2026-01-25 |
| <a id="tc-742"></a>**TC-742** | School drilldown | School totals correct | Automated (Polaris) | 2026-01-25 |
| <a id="tc-743"></a>**TC-743** | Event type filter | In-person only works | Automated (Polaris) | 2026-01-25 |
| <a id="tc-744"></a>**TC-744** | Date range filter | Metrics update correctly | Automated (Polaris) | 2026-01-25 |

### D. Ad Hoc Queries

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-760"></a>**TC-760** | Query specific org | Returns correct counts |
| <a id="tc-761"></a>**TC-761** | Query date range | Results match filters |
| <a id="tc-762"></a>**TC-762** | Query performance | Results load within timeout |

### E. Exports

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-780"></a>**TC-780** | Export volunteer report | CSV matches UI |
| <a id="tc-781"></a>**TC-781** | Export org report | CSV matches UI |
| <a id="tc-782"></a>**TC-782** | Export district report | Filters respected |
| <a id="tc-783"></a>**TC-783** | CSV formatting | Proper headers, no corruption |

### F. Access Control

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-800"></a>**TC-800** | District Viewer → district dashboards | Access allowed, scoped |
| <a id="tc-801"></a>**TC-801** | District Viewer → global dashboards | Denied or restricted |
| <a id="tc-802"></a>**TC-802** | District Viewer → restricted export | Blocked or scoped |
| <a id="tc-803"></a>**TC-803** | No student PII in reports | Aggregates only |

### G. Reliability

| TC | Description | Expected |
|----|-------------|----------|
| <a id="tc-820"></a>**TC-820** | Report failure visible | Clear error, not partial |
| <a id="tc-821"></a>**TC-821** | Export failure visible | No silent empty file |
| <a id="tc-822"></a>**TC-822** | Export audit logged | User, report, timestamp recorded |

---

*Last updated: February 2026*
*Version: 1.0*
