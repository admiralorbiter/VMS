# Polaris Documentation Hub

**Volunteer Management System · VolunTeach · Salesforce · Pathful**

This documentation covers the integrated system for managing K–12 student connections with career professionals through in-person and virtual events.

![VMS Data Flow Architecture](content/images/vms_architecture_optimized.png)

## Start Here by Role

| Role | Start With |
|------|------------|
| **New Staff** | [Purpose & Scope](purpose_scope) → [User Guide](../user_guide/index) |
| **District Admin** | [District Self-Service](../user_guide/district_self_service) → [Tenant Management](../user_guide/tenant_management) |
| **Developer** | [Developer Guide](../developer/index) → [Codebase Structure](../technical/codebase_structure) |
| **Operations** | [Deployment](../operations/deployment) → [Runbook](../operations/runbook) |
| **Reports User** | [Reports Overview](../reports/index) → [Metrics Bible](../technical/metrics_bible) |

## System URLs

| System | URL | Purpose |
|--------|-----|---------|
| **Salesforce** | [prep-kc.my.salesforce.com](https://prep-kc.my.salesforce.com/) | Core CRM, in-person events, student attendance |
| **VolunTeach** | [voluntold-prepkc.pythonanywhere.com](https://voluntold-prepkc.pythonanywhere.com/dashboard) | Event sync and publishing controls |
| **Public Website** | [prepkc.org/volunteer.html](https://prepkc.org/volunteer.html) | Volunteer signup pages |

---

## Quick Navigation

### Getting Started
- [Purpose & Scope](purpose_scope) — System boundaries and functional coverage
- [Glossary](glossary) — Key terms and definitions
- [Roadmap](roadmap) — Development phases and planned features

### Requirements
- [Functional Requirements](../requirements/index) — FR-xxx specifications
- [User Stories](../requirements/user_stories) — Business intent by epic
- [Use Cases](../requirements/use_cases) — End-to-end workflows
- [Non-Functional Requirements](../requirements/non_functional) — Quality attributes

### User Guides
- [User Guide Overview](../user_guide/index) — Step-by-step instructions
- [Virtual Events](../user_guide/virtual_events) — Virtual session management
- [In-Person Events](../user_guide/in_person_events) — Traditional event workflows
- [Volunteer Recruitment](../user_guide/volunteer_recruitment) — Finding and matching volunteers

### Reports
- [Reports Overview](../reports/index) — Available report types
- [Impact & KPIs](../reports/impact) — Key metrics and dashboards
- [Volunteer Engagement](../reports/volunteer_engagement) — Volunteer activity reports

### District Suite
- [Development Phases](../district_suite/phases) — District Suite roadmap
- [District Self-Service](../user_guide/district_self_service) — District admin workflows
- [Tenant Management](../user_guide/tenant_management) — Multi-tenant configuration

### Technical
- [Architecture](../technical/architecture) — System context and integrations
- [Codebase Structure](../technical/codebase_structure) — Directory layout
- [Data Dictionary](../technical/data_dictionary) — Entity definitions
- [Field Mappings](../technical/field_mappings) — Cross-system data flow
- [Metrics Bible](../technical/metrics_bible) — Calculation definitions
- [Integration Contracts](../technical/contracts/index) — API specs
- [ADR](../technical/adr) — Architecture Decision Records

### Developer
- [Developer Guide](../developer/index) — Getting started for developers
- [CLI Reference](../developer/cli_reference) — Command-line tools
- [API Reference](../developer/api_reference) — API documentation

### Operations
- [Deployment](../operations/deployment) — Deployment procedures
- [Import Playbook](../operations/import_playbook) — Data import guide
- [Monitoring](../operations/monitoring) — Alerting and dashboards
- [Runbook](../operations/runbook) — Troubleshooting procedures
- [Cache Management](../operations/cache_management) — Cache operations

### Security
- [RBAC Matrix](../security/rbac_matrix) — Role permissions
- [Privacy & Data Handling](../security/privacy_data_handling) — Data protection
- [Audit Requirements](../security/audit_requirements) — Compliance

### Testing
- [Test Packs Overview](../test_packs/index) — 8 comprehensive test packs

---

## Core Systems

| System | Purpose | Owns |
|--------|---------|------|
| **Salesforce** | Core CRM, in-person events, student attendance | Event details, student data |
| **VolunTeach** | Event sync + website publishing | Publish toggle, district links |
| **Website** | Public event display + volunteer signup | Signup capture |
| **Polaris** | Virtual events, recruitment, dashboards | Virtual events, metrics |
| **Pathful** | Virtual signup + attendance | Session signups, attendance |

---

*Last updated: February 2026 · Version 1.2*
