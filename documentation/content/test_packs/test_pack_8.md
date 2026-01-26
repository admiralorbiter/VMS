# Test Pack 8: Tenant Management

District Suite tenant CRUD, configuration, and infrastructure

> [!INFO]
> **Coverage**
> - [FR-TENANT-101](requirements#fr-tenant-101) (Create tenants)
> - [FR-TENANT-102](requirements#fr-tenant-102) (View/Edit/Deactivate)
> - [FR-TENANT-103](requirements#fr-tenant-103) (Database routing) *Pending Phase 2*
> - [FR-TENANT-104](requirements#fr-tenant-104) (Reference data provisioning)
> - [FR-TENANT-106](requirements#fr-tenant-106) (Separate SQLite files)
> - [FR-TENANT-107](requirements#fr-tenant-107) (Feature flags)

> [!TIP]
> **Automated Tests**: `tests/unit/models/test_tenant.py` (10 tests), `tests/unit/utils/test_db_manager.py` (11 tests), `tests/integration/test_tenant_routes.py` (15 tests)

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

### G. Tenant Database Infrastructure (FR-TENANT-106)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-860"></a>**TC-860** | Tenant database created on provisioning | `polaris_{slug}.db` file created in instance/ | Automated | 2026-01-26 |
| <a id="tc-861"></a>**TC-861** | Tenant database has correct schema | All tables from main DB present in tenant DB | Automated | 2026-01-26 |
| <a id="tc-862"></a>**TC-862** | Tenant database path generation | `get_tenant_db_path(slug)` returns correct path | Automated | 2026-01-26 |
| <a id="tc-863"></a>**TC-863** | Tenant database URI generation | `get_tenant_db_uri(slug)` returns SQLite URI | Automated | 2026-01-26 |
| <a id="tc-864"></a>**TC-864** | Database creation is idempotent | Second call returns False, doesn't error | Automated | 2026-01-26 |
| <a id="tc-865"></a>**TC-865** | Delete tenant database | `delete_tenant_database(slug)` removes file | Automated | 2026-01-26 |

### H. Reference Data Provisioning (FR-TENANT-104)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-870"></a>**TC-870** | Districts copied to tenant DB | All district records from main DB copied | Automated | 2026-01-26 |
| <a id="tc-871"></a>**TC-871** | Schools copied to tenant DB | All school records from main DB copied | Automated | 2026-01-26 |
| <a id="tc-872"></a>**TC-872** | Skills copied to tenant DB | All skill records from main DB copied | Automated | 2026-01-26 |
| <a id="tc-873"></a>**TC-873** | Career types copied to tenant DB | All career_type records from main DB copied | Automated | 2026-01-26 |
| <a id="tc-874"></a>**TC-874** | Provisioning returns counts | `provision_reference_data()` returns record counts | Automated | 2026-01-26 |
| <a id="tc-875"></a>**TC-875** | KCK migration verified | polaris_kck.db created with 461 teachers, 462 progress | Manual | 2026-01-26 |

### I. Feature Flags (FR-TENANT-107)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-880"></a>**TC-880** | Default feature flags set | events + volunteers enabled, recruitment disabled | Automated | 2026-01-26 |
| <a id="tc-881"></a>**TC-881** | `is_feature_enabled()` returns correct state | True for enabled, False for disabled features | Automated | 2026-01-26 |
| <a id="tc-882"></a>**TC-882** | Unknown feature returns False | `is_feature_enabled('nonexistent')` returns False | Automated | 2026-01-26 |

### J. Database Routing (FR-TENANT-103)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-890"></a>**TC-890** | Tenant user routed to tenant DB | User with tenant_id queries tenant database | Pending | Phase 2 |
| <a id="tc-891"></a>**TC-891** | PrepKC user queries main DB | User without tenant_id queries main database | Pending | Phase 2 |
| <a id="tc-892"></a>**TC-892** | Tenant data isolation | Tenant cannot see other tenant's data | Pending | Phase 2 |
| <a id="tc-893"></a>**TC-893** | Admin tenant context switch | Admin can switch tenant context with audit trail | Pending | Phase 2 |

---

> [!NOTE]
> **Automated Test Files**
> - `tests/unit/models/test_tenant.py` - Tenant model tests
> - `tests/unit/utils/test_db_manager.py` - Database manager tests (11 tests)
> - `tests/integration/test_tenant_routes.py` - Tenant routes tests

---

*Last updated: 2026-01-26*
*Version: 1.2 - Added infrastructure test coverage (FR-TENANT-103, 104, 106, 107)*
