# District Suite Requirements

**Multi-Tenant Platform**

> [!NOTE]
> **District Suite** extends Polaris from a single-tenant system to a multi-tenant platform. Each district operates in an isolated environment with its own database, users, and data.

---

## Tenant Infrastructure

### Tenant Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-tenant-101"></a>**FR-TENANT-101** | PrepKC administrators shall be able to create new district tenants, provisioning isolated databases with schema and reference data. | [TC-801](test-pack-8#tc-801), [TC-806](test-pack-8#tc-806) | [US-1001](user-stories#us-1001) |
| <a id="fr-tenant-102"></a>**FR-TENANT-102** | PrepKC administrators shall be able to view, edit, and deactivate tenants via a tenant management interface. | [TC-810](test-pack-8#tc-810), [TC-811](test-pack-8#tc-811), [TC-820](test-pack-8#tc-820), [TC-830](test-pack-8#tc-830) | [US-1001](user-stories#us-1001) |
| <a id="fr-tenant-103"></a>**FR-TENANT-103** | The system shall route authenticated users to their tenant's database and enforce tenant-scoped access for all operations. | [TC-890](test-pack-8#tc-890)–[TC-892](test-pack-8#tc-892) | *Technical* |
| <a id="fr-tenant-104"></a>**FR-TENANT-104** | Reference data (schools, districts, skills, career types) shall be duplicated to each tenant database during provisioning. | [TC-870](test-pack-8#tc-870)–[TC-875](test-pack-8#tc-875) | *Technical* |
| <a id="fr-tenant-105"></a>**FR-TENANT-105** | PrepKC administrators shall be able to switch tenant context to support any tenant while maintaining audit trails. | [TC-893](test-pack-8#tc-893) | [US-1002](user-stories#us-1002) |
| <a id="fr-tenant-106"></a>**FR-TENANT-106** | Tenant databases shall use separate SQLite files with tenant identifier in filename (e.g., `polaris_kckps.db`). | [TC-860](test-pack-8#tc-860)–[TC-865](test-pack-8#tc-865) | *Technical* |
| <a id="fr-tenant-107"></a>**FR-TENANT-107** | The system shall support feature flags per tenant to enable/disable specific capabilities during phased rollout. | [TC-806](test-pack-8#tc-806), [TC-822](test-pack-8#tc-822), [TC-880](test-pack-8#tc-880)–[TC-882](test-pack-8#tc-882) | *Technical* |

### Tenant User Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-tenant-108"></a>**FR-TENANT-108** | Polaris administrators shall be able to create, edit, and deactivate user accounts for any tenant via the tenant management interface. | [TC-1200](test-pack-8#tc-1200)–[TC-1205](test-pack-8#tc-1205) | [US-1003](user-stories#us-1003) |
| <a id="fr-tenant-109"></a>**FR-TENANT-109** | Tenant administrators shall be able to create, edit, and deactivate user accounts within their own tenant. | [TC-1210](test-pack-8#tc-1210)–[TC-1215](test-pack-8#tc-1215) | [US-1004](user-stories#us-1004) |
| <a id="fr-tenant-110"></a>**FR-TENANT-110** | The system shall support a tenant role hierarchy: Tenant Admin (full tenant access), Tenant Coordinator (event/volunteer management), and Tenant User (read-only dashboard access). | [TC-1201](test-pack-8#tc-1201), [TC-1215](test-pack-8#tc-1215) | [US-1004](user-stories#us-1004) |
| <a id="fr-tenant-111"></a>**FR-TENANT-111** | Tenant user passwords shall be securely hashed using the same mechanism as Polaris users, with support for password reset via email. | [TC-1202](test-pack-8#tc-1202) | *Technical* |
| <a id="fr-tenant-112"></a>**FR-TENANT-112** | Tenant users shall see a navigation menu scoped to their tenant's enabled features, without access to Polaris administrative functions. | [TC-1216](test-pack-8#tc-1216)–[TC-1218](test-pack-8#tc-1218) | [US-1004](user-stories#us-1004) |

### Tenant Teacher Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-tenant-113"></a>**FR-TENANT-113** | Tenant administrators shall be able to import teacher rosters via CSV file or Google Sheets URL with automatic school association. | *TBD* | [US-1005](user-stories#us-1005) |
| <a id="fr-tenant-114"></a>**FR-TENANT-114** | Teacher roster import shall use upsert logic based on email address, updating existing records and creating new ones. | *TBD* | [US-1005](user-stories#us-1005) |
| <a id="fr-tenant-115"></a>**FR-TENANT-115** | Tenant administrators shall be able to view a teacher usage dashboard showing virtual session counts per teacher, grouped by building. | *TBD* | [US-1006](user-stories#us-1006) |
| <a id="fr-tenant-116"></a>**FR-TENANT-116** | The teacher usage dashboard shall support filtering by academic semester (Fall: Aug-Dec, Spring: Jan-May). | *TBD* | [US-1006](user-stories#us-1006) |
| <a id="fr-tenant-117"></a>**FR-TENANT-117** | The teacher usage dashboard shall support Excel export with teacher names, schools, and session counts. | *TBD* | [US-1006](user-stories#us-1006) |

---

## District Self-Service

### District Event Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-selfserv-201"></a>**FR-SELFSERV-201** | District administrators/coordinators shall be able to create events with title, date, time, location, description, and volunteer needs. | [TC-901](test-pack-8#tc-901)–[TC-904](test-pack-8#tc-904) | [US-1101](user-stories#us-1101) |
| <a id="fr-selfserv-202"></a>**FR-SELFSERV-202** | District administrators/coordinators shall be able to edit event details up until event completion. | [TC-910](test-pack-8#tc-910)–[TC-912](test-pack-8#tc-912) | [US-1101](user-stories#us-1101) |
| <a id="fr-selfserv-203"></a>**FR-SELFSERV-203** | District administrators/coordinators shall be able to cancel events with optional reason; notifications sent to signed-up volunteers. | [TC-920](test-pack-8#tc-920), [TC-921](test-pack-8#tc-921) | [US-1101](user-stories#us-1101) |
| <a id="fr-selfserv-204"></a>**FR-SELFSERV-204** | The system shall provide a calendar view of district events with month/week/day navigation. | [TC-940](test-pack-8#tc-940)–[TC-944](test-pack-8#tc-944) | [US-1102](user-stories#us-1102) |
| <a id="fr-selfserv-205"></a>**FR-SELFSERV-205** | The system shall provide a searchable, sortable list view of district events with filtering by status and date range. | [TC-930](test-pack-8#tc-930), [TC-931](test-pack-8#tc-931) | [US-1102](user-stories#us-1102) |
| <a id="fr-selfserv-206"></a>**FR-SELFSERV-206** | District events shall track lifecycle status: Draft, Confirmed, Published, Completed, Cancelled. | [TC-903](test-pack-8#tc-903), [TC-904](test-pack-8#tc-904) | *Technical* |

### District Volunteer Management

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-selfserv-301"></a>**FR-SELFSERV-301** | District administrators shall be able to add, edit, and view volunteer profiles within their tenant. | [TC-1001](test-pack-8#tc-1001)–[TC-1008](test-pack-8#tc-1008) | [US-1103](user-stories#us-1103) |
| <a id="fr-selfserv-302"></a>**FR-SELFSERV-302** | District administrators shall be able to import volunteers via CSV or Excel with field mapping and validation. | [TC-1010](test-pack-8#tc-1010)–[TC-1014](test-pack-8#tc-1014) | [US-1103](user-stories#us-1103) |
| <a id="fr-selfserv-303"></a>**FR-SELFSERV-303** | District staff shall be able to search and filter volunteers by name, organization, skills, and career type within their tenant. | [TC-1020](test-pack-8#tc-1020)–[TC-1024](test-pack-8#tc-1024) | [US-1103](user-stories#us-1103) |
| <a id="fr-selfserv-304"></a>**FR-SELFSERV-304** | District staff shall be able to assign volunteers to events with participation type and confirmation status tracking. | [TC-1030](test-pack-8#tc-1030)–[TC-1033](test-pack-8#tc-1033) | [US-1104](user-stories#us-1104) |
| <a id="fr-selfserv-305"></a>**FR-SELFSERV-305** | Volunteer data shall be strictly isolated to the owning tenant with no cross-tenant visibility. | [TC-1040](test-pack-8#tc-1040)–[TC-1043](test-pack-8#tc-1043) | *Technical* |

### District Recruitment Tools

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-selfserv-401"></a>**FR-SELFSERV-401** | The system shall provide a recruitment dashboard showing events needing volunteers with urgency indicators. | [TC-1101](test-pack-8#tc-1101)–[TC-1104](test-pack-8#tc-1104) | [US-1105](user-stories#us-1105) |
| <a id="fr-selfserv-402"></a>**FR-SELFSERV-402** | The system shall rank volunteer candidates using scoring based on participation history, skills match, and location. | [TC-1110](test-pack-8#tc-1110)–[TC-1113](test-pack-8#tc-1113) | [US-1105](user-stories#us-1105) |
| <a id="fr-selfserv-403"></a>**FR-SELFSERV-403** | District staff shall be able to log outreach attempts and track outcomes (No Response, Interested, Declined, Confirmed). | [TC-1120](test-pack-8#tc-1120)–[TC-1123](test-pack-8#tc-1123) | [US-1105](user-stories#us-1105) |
| <a id="fr-selfserv-404"></a>**FR-SELFSERV-404** | The system shall provide public signup forms for district events that create volunteer records and send confirmation emails. | [TC-1130](test-pack-8#tc-1130)–[TC-1132](test-pack-8#tc-1132) | [US-1106](user-stories#us-1106) |
| <a id="fr-selfserv-405"></a>**FR-SELFSERV-405** | Public signup shall attach calendar invites to confirmation emails with event details. | [TC-1133](test-pack-8#tc-1133), [TC-1134](test-pack-8#tc-1134) | [US-1106](user-stories#us-1106) |

### PrepKC Event Visibility

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-selfserv-501"></a>**FR-SELFSERV-501** | District users shall be able to view PrepKC events occurring at their schools (read-only). | *Phase 5* | [US-1107](user-stories#us-1107) |
| <a id="fr-selfserv-502"></a>**FR-SELFSERV-502** | PrepKC events shall appear on the district calendar with distinct styling indicating PrepKC ownership. | *Phase 5* | [US-1107](user-stories#us-1107) |
| <a id="fr-selfserv-503"></a>**FR-SELFSERV-503** | The system shall provide aggregate statistics for PrepKC events at district schools (events count, students reached, volunteer hours). | *Phase 5* | [US-1107](user-stories#us-1107) |

---

## Public Event API

> [!NOTE]
> The Public Event API enables districts to embed their event listings on their own websites. The API is read-only and authenticated via tenant-specific API keys.

| ID | Requirement | Test Coverage | Related Stories |
|----|-------------|---------------|-----------------|
| <a id="fr-api-101"></a>**FR-API-101** | The system shall provide a REST endpoint `GET /api/v1/district/{tenant}/events` returning published events for the tenant. | [TC-950](test-pack-8#tc-950)–[TC-952](test-pack-8#tc-952) | [US-1201](user-stories#us-1201) |
| <a id="fr-api-102"></a>**FR-API-102** | The system shall provide a REST endpoint `GET /api/v1/district/{tenant}/events/{slug}` returning single event details. | [TC-951](test-pack-8#tc-951) | [US-1201](user-stories#us-1201) |
| <a id="fr-api-103"></a>**FR-API-103** | API requests shall be authenticated via tenant-specific API keys passed in the `X-API-Key` header. | [TC-960](test-pack-8#tc-960)–[TC-962](test-pack-8#tc-962) | *Technical* |
| <a id="fr-api-104"></a>**FR-API-104** | The API shall enforce rate limits: 60 requests/minute, 1000 requests/hour, 10000 requests/day per API key. | [TC-970](test-pack-8#tc-970), [TC-971](test-pack-8#tc-971) | *Technical* |
| <a id="fr-api-105"></a>**FR-API-105** | The API shall support CORS to allow embedding on district websites. | ✅ Implemented | *Technical* |
| <a id="fr-api-106"></a>**FR-API-106** | District administrators shall be able to rotate their API key via the tenant settings interface. | [TC-990](test-pack-8#tc-990), [TC-991](test-pack-8#tc-991) | [US-1202](user-stories#us-1202) |
| <a id="fr-api-107"></a>**FR-API-107** | API responses shall use JSON format with consistent envelope structure including success status, data payload, and pagination. | [TC-980](test-pack-8#tc-980), [TC-982](test-pack-8#tc-982) | *Technical* |
| <a id="fr-api-108"></a>**FR-API-108** | Event objects in API responses shall include: id, title, description, event_type, date, times, location, volunteers_needed, signup_url. | [TC-981](test-pack-8#tc-981) | [US-1201](user-stories#us-1201) |

---

## Related Documentation

- [Requirements Overview](requirements) — Summary and traceability matrix
- [User Stories](user-stories) — Business value context
- [District Suite Phases](district-suite-phases) — Development roadmap
- [Tenant Management Guide](user-guide-tenant-management) — User documentation

---

*Last updated: February 2026 · Version 1.0*
