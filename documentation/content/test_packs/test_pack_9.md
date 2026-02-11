# Test Pack 9: Bug Reporting

User feedback submission + admin management + system-generated reports

> [!NOTE]
> **Coverage**
> [FR-BUG-001](requirements-bug-reporting#fr-bug-001)–[FR-BUG-005](requirements-bug-reporting#fr-bug-005) (Submission), [FR-BUG-006](requirements-bug-reporting#fr-bug-006)–[FR-BUG-012](requirements-bug-reporting#fr-bug-012) (Administration), [FR-BUG-013](requirements-bug-reporting#fr-bug-013) (System Integration)

---

## Test Data Setup

**Users:**

| User | Role | Purpose |
|------|------|---------|
| reporter_user | Authenticated | Submits bug reports |
| admin_user | Admin | Manages bug reports |
| regular_user | Non-Admin | Tests access restrictions |

#### Sample Bug Reports

| Report | Type | Status | Description |
|--------|------|--------|-------------|
| Report A | Bug | Open | "Button not working on dashboard" |
| Report B | Data Error | Open | "Incorrect volunteer count displayed" |
| Report C | Other | Resolved | "Suggestion: add dark mode" |

## Test Cases

### A. Bug Report Submission

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1300"></a>**TC-1300** | Submit valid bug report (type=BUG, description, page_url) | 200 JSON with `{"success": true}`, report persisted in DB | Automated | 2026-02 |
| <a id="tc-1301"></a>**TC-1301** | Submit report with all types (BUG, DATA_ERROR, OTHER) | Each type accepted and stored correctly | Automated | 2026-02 |
| <a id="tc-1302"></a>**TC-1302** | Submit report with page_title auto-captured | page_title stored on report record | Automated | 2026-02 |
| <a id="tc-1303"></a>**TC-1303** | Form renders for authenticated user (GET /bug-report/form) | 200 with form HTML | Automated | 2026-02 |
| <a id="tc-1304"></a>**TC-1304** | Submit with empty description | 400 JSON with error message "Description is required" | Automated | 2026-02 |
| <a id="tc-1305"></a>**TC-1305** | Unauthenticated user accesses form or submits | 302 redirect to login | Automated | 2026-02 |

### B. Admin Bug Report Management

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1306"></a>**TC-1306** | Admin views bug reports list (GET /bug-reports) | 200 with open/resolved sections | Automated | 2026-02 |
| <a id="tc-1307"></a>**TC-1307** | Filter by status (?status=open / ?status=resolved) | Only matching reports returned | Automated | 2026-02 |
| <a id="tc-1308"></a>**TC-1308** | Filter by type (?type=bug / ?type=data_error) | Only matching type returned | Automated | 2026-02 |
| <a id="tc-1309"></a>**TC-1309** | Search by keyword (?search=button) | Only matching reports returned | Automated | 2026-02 |
| <a id="tc-1310"></a>**TC-1310** | Resolve a bug report with notes | resolved=True, resolved_by set, notes stored | Automated | 2026-02 |
| <a id="tc-1311"></a>**TC-1311** | Resolve nonexistent report | 404 response | Automated | 2026-02 |
| <a id="tc-1312"></a>**TC-1312** | Admin deletes bug report | 200 JSON `{"success": true}`, report removed from DB | Automated | 2026-02 |
| <a id="tc-1313"></a>**TC-1313** | Delete creates audit log entry | AuditLog record with action="delete", resource_type="bug_report" | Automated | 2026-02 |
| <a id="tc-1314"></a>**TC-1314** | Non-admin attempts delete | 403 Forbidden | Automated | 2026-02 |

### C. System Integration

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1315"></a>**TC-1315** | Email delivery failure creates auto bug report | BugReport created with type=OTHER, description contains message ID and error | Automated | 2026-02 |

---

*Last updated: February 2026*
*Version: 1.0*
