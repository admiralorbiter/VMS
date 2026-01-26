# Test Pack 8: Tenant Management

District Suite tenant CRUD + configuration

> [!INFO]
> **Coverage**
> [FR-TENANT-101](requirements#fr-tenant-101) (Create tenants), [FR-TENANT-102](requirements#fr-tenant-102) (View/Edit/Deactivate)

> [!TIP]
> **Automated Tests**: `tests/unit/models/test_tenant.py` (10 tests), `tests/integration/test_tenant_routes.py` (15 tests)

---

## Test Data Setup

**PrepKC Admin User**

- Username: `admin@prepkc.org`
- Role: Admin (PrepKC staff)

#### Test Tenants

| Tenant | Slug | District | Status |
|--------|------|----------|--------|
| KCK Test | `kck-test` | Kansas City Kansas Public Schools | Active |
| HMSD Test | `hmsd-test` | Hickman Mills School District | Active |
| Inactive Tenant | `inactive-test` | None | Inactive |

## Test Cases

### A. Tenant Creation (FR-TENANT-101)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-801"></a>**TC-801** | Create tenant with valid slug | Tenant created, appears in list | Automated | 2026-01-26 |
| <a id="tc-802"></a>**TC-802** | Create tenant with duplicate slug | Error: slug already exists | Automated | 2026-01-26 |
| <a id="tc-803"></a>**TC-803** | Create tenant with invalid slug | Error: invalid characters | Manual | TBD |
| <a id="tc-804"></a>**TC-804** | Create tenant linked to district | Tenant shows district name | Automated | 2026-01-26 |
| <a id="tc-805"></a>**TC-805** | Create tenant without district | Tenant created with null district | Manual | TBD |
| <a id="tc-806"></a>**TC-806** | Default feature flags on create | events + volunteers enabled by default | Automated | 2026-01-26 |

### B. Tenant Viewing (FR-TENANT-102)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-810"></a>**TC-810** | View tenant list | All tenants shown with status badges | Automated | 2026-01-26 |
| <a id="tc-811"></a>**TC-811** | View tenant detail | Shows slug, name, status, features, users | Automated | 2026-01-26 |
| <a id="tc-812"></a>**TC-812** | View inactive tenant | Shows inactive badge, activate button | Manual | TBD |
| <a id="tc-813"></a>**TC-813** | View tenant with API key | Shows "Configured" badge, rotate button | Manual | TBD |
| <a id="tc-814"></a>**TC-814** | View tenant without API key | Shows "Not Set", generate button | Manual | TBD |

### C. Tenant Editing (FR-TENANT-102)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-820"></a>**TC-820** | Edit tenant name | Name updated, slug unchanged | Automated | 2026-01-26 |
| <a id="tc-821"></a>**TC-821** | Slug is immutable | Edit form does not show slug field | Manual | TBD |
| <a id="tc-822"></a>**TC-822** | Toggle feature flag | Feature state persisted | Automated | 2026-01-26 |
| <a id="tc-823"></a>**TC-823** | Update portal settings | Welcome message persisted | Automated | 2026-01-26 |
| <a id="tc-824"></a>**TC-824** | Change linked district | District association updated | Manual | TBD |
| <a id="tc-825"></a>**TC-825** | Update CORS origins | Origins saved correctly | Manual | TBD |

### D. Tenant Deactivation (FR-TENANT-102)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-830"></a>**TC-830** | Deactivate active tenant | Status changes to inactive | Automated | 2026-01-26 |
| <a id="tc-831"></a>**TC-831** | Deactivated tenant portal | Returns 404 on /virtual/<slug> | Automated | 2026-01-26 |
| <a id="tc-832"></a>**TC-832** | Reactivate tenant | Status changes to active, portal works | Manual | TBD |
| <a id="tc-833"></a>**TC-833** | Deactivation confirmation | Confirm dialog shown before deactivate | Manual | TBD |

### E. API Key Management

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-840"></a>**TC-840** | Generate API key | Key shown once in flash message | Automated | 2026-01-26 |
| <a id="tc-841"></a>**TC-841** | Rotate API key | New key generated, old invalidated | Automated | 2026-01-26 |
| <a id="tc-842"></a>**TC-842** | Revoke API key | API key cleared, status shows "Not Set" | Manual | TBD |
| <a id="tc-843"></a>**TC-843** | Key hashing | Only hash stored, not plaintext | Automated | 2026-01-26 |

### F. Access Control

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-850"></a>**TC-850** | Admin access only | Non-admin users cannot access /management/tenants | Automated | 2026-01-26 |
| <a id="tc-851"></a>**TC-851** | Unauthenticated access | Redirects to login | Automated | 2026-01-26 |

---

*Last updated: 2026-01-26*
*Version: 1.1 - Added automated test coverage*
