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

### J. Database Routing (FR-TENANT-103) & Cross-Tenant Access (FR-TENANT-105)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-890"></a>**TC-890** | Tenant user routed to tenant context | User with tenant_id has g.tenant set | Automated | 2026-01-26 |
| <a id="tc-891"></a>**TC-891** | PrepKC user has no tenant context | User without tenant_id has g.tenant=None | Automated | 2026-01-26 |
| <a id="tc-892"></a>**TC-892** | Tenant context decorator blocks access | `@require_tenant_context` aborts without tenant | Automated | 2026-01-26 |
| <a id="tc-893"></a>**TC-893** | Admin tenant context switch | Admin override sets session-based tenant context | Automated | 2026-01-26 |

---

## Phase 2: District Events (FR-SELFSERV-201, 202, 203)

### K. District Event Creation (FR-SELFSERV-201)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-901"></a>**TC-901** | Create event with required fields | Event saved with tenant_id set | Automated | 2026-01-26 |
| <a id="tc-902"></a>**TC-902** | Event scoped to tenant | Query filters by tenant_id | Automated | 2026-01-26 |
| <a id="tc-903"></a>**TC-903** | Event has correct initial status | New events have status=Draft | Automated | 2026-01-26 |
| <a id="tc-904"></a>**TC-904** | Publish draft event | Status changes from Draft to Published | Automated | 2026-01-26 |

### L. District Event Editing (FR-SELFSERV-202)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-910"></a>**TC-910** | Edit event updates fields | Changes persist to database | Automated | 2026-01-26 |
| <a id="tc-911"></a>**TC-911** | Cannot edit completed event | Redirect with warning message | Automated | 2026-01-26 |
| <a id="tc-912"></a>**TC-912** | Cannot edit cancelled event | Redirect with warning message | Automated | 2026-01-26 |

### M. District Event Cancellation (FR-SELFSERV-203)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-920"></a>**TC-920** | Cancel event sets status | Event status changes to Cancelled | Automated | 2026-01-26 |
| <a id="tc-921"></a>**TC-921** | Cannot cancel completed event | Redirect with warning message | Automated | 2026-01-26 |

### N. District Event Data Isolation

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-930"></a>**TC-930** | Events list shows only tenant events | Other tenant events not visible | Automated | 2026-01-26 |
| <a id="tc-931"></a>**TC-931** | Cannot view other tenant's event | Returns 404 for wrong tenant | Automated | 2026-01-26 |

### O. District Event Calendar (FR-SELFSERV-204)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-940"></a>**TC-940** | Calendar view loads | `/district/events/calendar` renders template | Automated | 2026-01-26 |
| <a id="tc-941"></a>**TC-941** | Calendar API returns JSON | `/district/events/calendar/api` returns valid JSON array | Automated | 2026-01-26 |
| <a id="tc-942"></a>**TC-942** | Calendar API scopes to tenant | Only returns events with matching tenant_id | Automated | 2026-01-26 |
| <a id="tc-943"></a>**TC-943** | Calendar events have required fields | Each event has id, title, start, color, extendedProps | Automated | 2026-01-26 |
| <a id="tc-944"></a>**TC-944** | Status color mapping works | Each status maps to correct color hex | Automated | 2026-01-26 |

---

## Phase 2: Public Event API (FR-API-101 to FR-API-108)

### P. API Endpoints (FR-API-101, FR-API-102)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-950"></a>**TC-950** | List events endpoint exists | GET `/api/v1/district/{tenant}/events` returns JSON | Automated | 2026-01-26 |
| <a id="tc-951"></a>**TC-951** | Get event endpoint exists | GET `/api/v1/district/{tenant}/events/{id}` returns event | Automated | 2026-01-26 |
| <a id="tc-952"></a>**TC-952** | Only published events returned | Draft/Cancelled events not in response | Automated | 2026-01-26 |

### Q. API Authentication (FR-API-103)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-960"></a>**TC-960** | Missing API key returns 401 | Error: MISSING_API_KEY | Automated | 2026-01-26 |
| <a id="tc-961"></a>**TC-961** | Invalid API key returns 401 | Error: INVALID_API_KEY | Automated | 2026-01-26 |
| <a id="tc-962"></a>**TC-962** | Valid API key returns data | Success response with events | Automated | 2026-01-26 |

### R. Rate Limiting (FR-API-104)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-970"></a>**TC-970** | Rate limiter tracks requests | Count increments per request | Automated | 2026-01-26 |
| <a id="tc-971"></a>**TC-971** | Exceeded limit returns 429 | Error: RATE_LIMIT_EXCEEDED with Retry-After | Automated | 2026-01-26 |

### S. Response Format (FR-API-107, FR-API-108)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-980"></a>**TC-980** | Response has envelope structure | Contains success, data, pagination, meta | Automated | 2026-01-26 |
| <a id="tc-981"></a>**TC-981** | Event object has required fields | id, title, description, event_type, date, location, etc. | Automated | 2026-01-26 |
| <a id="tc-982"></a>**TC-982** | Pagination works correctly | page, per_page, total_items, has_next, has_prev | Automated | 2026-01-26 |

### T. API Key Management (FR-API-106)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-990"></a>**TC-990** | Generate API key | New key returned, hash stored | Automated | 2026-01-26 |
| <a id="tc-991"></a>**TC-991** | Rotate API key | Old key invalidated, new key works | Automated | 2026-01-26 |

---

## Phase 3: District Volunteers (FR-SELFSERV-301 to FR-SELFSERV-305)

### U. Volunteer Profile Management (FR-SELFSERV-301)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1001"></a>**TC-1001** | List volunteers shows tenant volunteers | Only volunteers in current tenant shown | Automated | 2026-01-26 |
| <a id="tc-1002"></a>**TC-1002** | Create volunteer with required fields | Volunteer and DistrictVolunteer created | Automated | 2026-01-26 |
| <a id="tc-1003"></a>**TC-1003** | Create volunteer with email/phone | Email and Phone records created | Automated | 2026-01-26 |
| <a id="tc-1004"></a>**TC-1004** | View volunteer profile | Shows contact info, org, district notes | Automated | 2026-01-26 |
| <a id="tc-1005"></a>**TC-1005** | Edit volunteer updates fields | Changes persisted to database | Automated | 2026-01-26 |
| <a id="tc-1006"></a>**TC-1006** | Toggle volunteer status | Active/Inactive status toggles | Automated | 2026-01-26 |
| <a id="tc-1007"></a>**TC-1007** | Link existing volunteer by email | DistrictVolunteer association created | Automated | 2026-01-26 |
| <a id="tc-1008"></a>**TC-1008** | Reactivate inactive volunteer | Status changes to active | Automated | 2026-01-26 |

### V. CSV Import (FR-SELFSERV-302)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1010"></a>**TC-1010** | Preview import shows columns | Returns detected columns and suggested mappings | Automated | 2026-01-26 |
| <a id="tc-1011"></a>**TC-1011** | Import creates new volunteers | Volunteers with Email/Phone records created | Automated | 2026-01-26 |
| <a id="tc-1012"></a>**TC-1012** | Import links existing volunteers | Matching emails linked to tenant | Automated | 2026-01-26 |
| <a id="tc-1013"></a>**TC-1013** | Import skips duplicate emails | Already-in-tenant volunteers skipped | Automated | 2026-01-26 |
| <a id="tc-1014"></a>**TC-1014** | Import requires name fields | Rows without first/last name skipped | Automated | 2026-01-26 |

### W. Volunteer Search (FR-SELFSERV-303)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1020"></a>**TC-1020** | Search by first name | Matching volunteers returned | Automated | 2026-01-26 |
| <a id="tc-1021"></a>**TC-1021** | Search by last name | Matching volunteers returned | Automated | 2026-01-26 |
| <a id="tc-1022"></a>**TC-1022** | Search by organization | Matching volunteers returned | Automated | 2026-01-26 |
| <a id="tc-1023"></a>**TC-1023** | Filter by status | Active/Inactive volunteers filtered | Automated | 2026-01-26 |
| <a id="tc-1024"></a>**TC-1024** | API search endpoint | Returns JSON for AJAX autocomplete | Automated | 2026-01-26 |

### X. Event Assignment (FR-SELFSERV-304)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1030"></a>**TC-1030** | Assign volunteer to event | DistrictParticipation created with status | Automated | 2026-01-26 |
| <a id="tc-1031"></a>**TC-1031** | Confirm volunteer participation | Status changes to confirmed | Automated | 2026-01-26 |
| <a id="tc-1032"></a>**TC-1032** | Record attendance | Status changes to attended | Automated | 2026-01-26 |
| <a id="tc-1033"></a>**TC-1033** | View volunteer event history | Past participations shown on profile | Automated | 2026-01-26 |

### Y. Tenant Isolation (FR-SELFSERV-305)

| TC | Description | Expected | Type | Last Verified |
|----|-------------|----------|------|---------------|
| <a id="tc-1040"></a>**TC-1040** | Cannot view other tenant volunteers | Returns 404 for wrong tenant | Automated | 2026-01-26 |
| <a id="tc-1041"></a>**TC-1041** | Cannot edit other tenant volunteers | Returns 404 for wrong tenant | Automated | 2026-01-26 |
| <a id="tc-1042"></a>**TC-1042** | Search scoped to tenant | Only current tenant volunteers searchable | Automated | 2026-01-26 |
| <a id="tc-1043"></a>**TC-1043** | Import scoped to tenant | New volunteers associated with current tenant | Automated | 2026-01-26 |

---

> [!NOTE]
> **Automated Test Files**
> - `tests/unit/models/test_tenant.py` - Tenant model tests (10 tests)
> - `tests/unit/utils/test_db_manager.py` - Database manager tests (11 tests)
> - `tests/unit/utils/test_tenant_context.py` - Tenant context tests (14 tests)
> - `tests/integration/test_tenant_routes.py` - Tenant routes tests
> - `tests/integration/test_district_events.py` - District event routes tests (including calendar)
> - `tests/integration/test_public_api.py` - Public Event API tests
> - `tests/integration/test_district_volunteers.py` - District volunteer routes tests

---

*Last updated: 2026-01-26*
*Version: 1.7 - Added Phase 3 District Volunteers tests (TC-1001-1043)*
