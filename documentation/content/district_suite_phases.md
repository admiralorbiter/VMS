# District Suite Development Phases

**Multi-tenant platform implementation roadmap**

> [!NOTE]
> This document outlines the phased implementation plan for District Suite, enabling partner districts to manage their own volunteer programs within isolated Polaris environments.

## Executive Summary

District Suite transforms Polaris from a single-tenant system to a multi-tenant platform. Each phase builds incrementally, with production releases between phases.

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **Phase 1** | Foundation | 4-6 weeks | Tenant provisioning, database isolation, basic auth |
| **Phase 2** | District Events | 4-6 weeks | Event CRUD, calendar views, public API |
| **Phase 3** | District Volunteers | 4-6 weeks | Volunteer management, import, search |
| **Phase 4** | District Recruitment | 6-8 weeks | Recruitment tools, matching, public signup |
| **Phase 5** | PrepKC Visibility | 2-4 weeks | Read-only PrepKC event access |

---

## Phase 1: Foundation

**Objective:** Establish multi-tenant infrastructure with database isolation.

### Deliverables

| Component | Description | Requirements |
|-----------|-------------|--------------|
| Tenant Model | Registry of district tenants in main DB | [FR-TENANT-101](requirements#fr-tenant-101) |
| Database Provisioning | SQLite file creation per tenant | [FR-TENANT-106](requirements#fr-tenant-106) |
| Tenant Management UI | Admin interface for tenant CRUD | [FR-TENANT-102](requirements#fr-tenant-102) |
| Request Routing | Middleware to set tenant context | [FR-TENANT-103](requirements#fr-tenant-103) |
| Reference Data Copy | Duplicate schools/skills to tenant DB | [FR-TENANT-104](requirements#fr-tenant-104) |
| Cross-Tenant Access | PrepKC admin can switch tenants | [FR-TENANT-105](requirements#fr-tenant-105) |
| Feature Flags | Per-tenant feature configuration | [FR-TENANT-107](requirements#fr-tenant-107) |

### Technical Tasks

1. **Create Tenant model** in main database
2. **Implement tenant middleware** for request routing
3. **Build database provisioning script** with Alembic migrations
4. **Create TenantUser model** in tenant database schema
5. **Build tenant management admin interface**
6. **Implement reference data duplication** during provisioning
7. **Add tenant context to Flask's `g` object**
8. **Create tenant selection UI** for PrepKC admins

### Success Criteria

- [x] PrepKC admin can create new tenant
- [x] New tenant database is created with full schema
- [x] Reference data is copied to tenant database
- [ ] District admin can log in to their tenant
- [x] District admin cannot access other tenants (via `@require_tenant_context`)
- [x] PrepKC admin can switch between tenants

---

## Phase 2: District Events

**Objective:** Enable districts to create and manage their own events.

### Deliverables

| Component | Description | Requirements |
|-----------|-------------|--------------|
| Event CRUD | Create, edit, cancel events | [FR-SELFSERV-201](requirements#fr-selfserv-201)-203 |
| Calendar View | Month/week/day event calendar | [FR-SELFSERV-204](requirements#fr-selfserv-204) |
| List View | Searchable, filterable event list | [FR-SELFSERV-205](requirements#fr-selfserv-205) |
| Event Status | Draft → Published → Completed workflow | [FR-SELFSERV-206](requirements#fr-selfserv-206) |
| Public Event API | REST endpoints for website integration | [FR-API-101](requirements#fr-api-101)-108 |
| API Key Management | Generate, rotate, revoke keys | [FR-API-106](requirements#fr-api-106) |

### Technical Tasks

1. **Create Event model extensions** for district events
2. **Build event CRUD routes and templates**
3. **Implement calendar component** (FullCalendar.js or similar)
4. **Build event list with filtering/sorting**
5. **Create event status workflow** with transitions
6. **Implement public API endpoints** (`/api/v1/district/{slug}/events`)
7. **Add API key authentication** middleware
8. **Implement rate limiting** for API
9. **Configure CORS** per tenant
10. **Create API settings page** for key management

### Success Criteria

- [ ] District admin can create events with all required fields
- [ ] Events appear in calendar and list views
- [ ] Events can transition through status workflow
- [ ] API returns published events with valid API key
- [ ] API rejects requests without valid key
- [ ] Rate limits are enforced

---

## Phase 3: District Volunteers

**Objective:** Enable districts to manage their own volunteer pool.

### Deliverables

| Component | Description | Requirements |
|-----------|-------------|--------------|
| Volunteer CRUD | Add, edit, view volunteer profiles | [FR-SELFSERV-301](requirements#fr-selfserv-301) |
| Volunteer Import | CSV/Excel import with mapping | [FR-SELFSERV-302](requirements#fr-selfserv-302) |
| Volunteer Search | Filter by name, org, skills | [FR-SELFSERV-303](requirements#fr-selfserv-303) |
| Event Assignment | Assign volunteers to events | [FR-SELFSERV-304](requirements#fr-selfserv-304) |
| Data Isolation | Strict tenant-scoped queries | [FR-SELFSERV-305](requirements#fr-selfserv-305) |

### Technical Tasks

1. **Create tenant-scoped Volunteer queries**
2. **Build volunteer CRUD routes and templates**
3. **Implement volunteer import** with column mapping
4. **Add validation and error reporting** for imports
5. **Build volunteer search** with filters
6. **Create event assignment interface**
7. **Implement participation tracking**
8. **Add audit logging** for volunteer data changes

### Success Criteria

- [ ] District admin can add volunteers manually
- [ ] Import creates volunteers from CSV with validation
- [ ] Search returns only tenant's volunteers
- [ ] Volunteers can be assigned to events
- [ ] No cross-tenant volunteer data access

---

## Phase 4: District Recruitment

**Objective:** Provide recruitment tools for proactive volunteer management.

### Deliverables

| Component | Description | Requirements |
|-----------|-------------|--------------|
| Recruitment Dashboard | Events needing volunteers | [FR-SELFSERV-401](requirements#fr-selfserv-401) |
| Volunteer Matching | Score-based recommendations | [FR-SELFSERV-402](requirements#fr-selfserv-402) |
| Outreach Tracking | Log attempts and outcomes | [FR-SELFSERV-403](requirements#fr-selfserv-403) |
| Public Signup Forms | No-login volunteer registration | [FR-SELFSERV-404](requirements#fr-selfserv-404) |
| Confirmation Emails | Email + calendar invite | [FR-SELFSERV-405](requirements#fr-selfserv-405) |

### Technical Tasks

1. **Build recruitment dashboard** with urgency indicators
2. **Implement volunteer scoring algorithm**
3. **Create volunteer recommendation component**
4. **Build outreach logging interface**
5. **Create public signup form** per event
6. **Implement confirmation email** with calendar attachment
7. **Add volunteer to pool** on signup
8. **Create participation record** on signup

### Success Criteria

- [ ] Dashboard shows events needing volunteers
- [ ] Volunteers are ranked by relevance
- [ ] Outreach can be logged with outcomes
- [ ] Public can sign up without login
- [ ] Confirmation email sent with calendar invite
- [ ] Signup creates volunteer record if new

---

## Phase 5: PrepKC Visibility

**Objective:** Allow districts to see PrepKC events at their schools.

### Deliverables

| Component | Description | Requirements |
|-----------|-------------|--------------|
| PrepKC Event View | Read-only view of PrepKC events | [FR-SELFSERV-501](requirements#fr-selfserv-501) |
| Calendar Integration | PrepKC events on district calendar | [FR-SELFSERV-502](requirements#fr-selfserv-502) |
| Statistics | Aggregate impact metrics | [FR-SELFSERV-503](requirements#fr-selfserv-503) |

### Technical Tasks

1. **Implement cross-database query** for PrepKC events
2. **Filter events by district's schools**
3. **Add PrepKC events to calendar** with distinct styling
4. **Create event detail view** (read-only)
5. **Build statistics dashboard** for PrepKC impact
6. **Implement caching** for PrepKC event data

### Success Criteria

- [ ] District can see PrepKC events at their schools
- [ ] PrepKC events appear on calendar with distinct styling
- [ ] Event details are read-only
- [ ] Statistics show aggregate metrics

---

## Quality Gates

Each phase must pass these gates before production release:

| Gate | Criteria |
|------|----------|
| **Code Review** | All PRs reviewed and approved |
| **Unit Tests** | 80%+ coverage for new code |
| **Integration Tests** | Key workflows tested end-to-end |
| **Security Review** | Tenant isolation verified, no data leaks |
| **Performance** | Response times <500ms for key operations |
| **Documentation** | User guides updated |
| **Stakeholder Demo** | Sign-off from product owner |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tenant data leak | Critical | Query scoping audit, integration tests |
| Database growth | Medium | SQLite per tenant limits size |
| API abuse | Medium | Rate limiting, key rotation |
| Feature creep | Medium | Strict phase scope, defer to next phase |
| Migration complexity | High | Alembic for schema changes |

---

## Related Documentation

- **Requirements:** [FR-TENANT-xxx](requirements#tenant-infrastructure), [FR-SELFSERV-xxx](requirements#district-self-service), [FR-API-xxx](requirements#public-event-api)
- **User Stories:** [US-1001](user_stories#us-1001) through [US-1202](user_stories#us-1202)
- **Use Cases:** [UC-14](use_cases#uc-14) through [UC-18](use_cases#uc-18)
- **Architecture:** [Multi-Tenancy Architecture](architecture#multi-tenancy-architecture-district-suite)
- **API Reference:** [Public Event API](api_reference)

---

*Last updated: January 2026*
*Version: 1.0*
