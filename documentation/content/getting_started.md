# Polaris Documentation Hub

**Volunteer Management System · VolunTeach · Salesforce · Pathful**

This documentation covers the integrated system for managing K–12 student connections with career professionals through in-person and virtual events.

## System URLs and Locations

| System | URL | Purpose |
|--------|-----|---------|
| **Salesforce** | [https://prep-kc.my.salesforce.com/](https://prep-kc.my.salesforce.com/) | Core CRM system for data entry, in-person events, student attendance, and email logging |
| **VolunTeach** | [https://voluntold-prepkc.pythonanywhere.com/dashboard](https://voluntold-prepkc.pythonanywhere.com/dashboard) | Admin interface for event management, sync controls, and publishing toggles |
| **Public Website** | [https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html) | Volunteer hub with links to signup pages for different event types |

## Quick Navigation

- 🎯 **[Purpose & Scope](purpose_scope)**
  System purpose, boundaries, and functional coverage
- 📋 **[Requirements](#requirements)**
  Functional requirements (FR-xxx) with test traceability
- 📖 **[User Stories](user_stories)**
  Business intent by epic with acceptance criteria
- 🔄 **[Use Cases](use_cases)**
  End-to-end workflows for key system functions
- 📋 **[Non-Functional Requirements](non_functional_requirements)**
  Quality attributes and system constraints
- 🏗️ **[Architecture](architecture)**
  System context, integration flows, and source-of-truth ownership
- 📊 **[Data Dictionary](data_dictionary)**
  Canonical entity definitions, field specs, and sensitivity levels
- 🔗 **[Field Mappings](field_mappings)**
  Cross-system data flow specifications
- 📐 **[Metrics Bible](metrics_bible)**
  How every metric is calculated—the single source of truth for reporting
- 🔐 **[RBAC Matrix](rbac_matrix)**
  Role permissions and data access controls
- 🔒 **[Privacy & Data Handling](privacy_data_handling)**
  Data protection rules and retention policies
- 🔌 **[Integration Contracts](contracts)**
  API specs for SF↔VT, Website, Gmail sync, Pathful import
- 🧪 **[Test Packs](#test-packs)**
  Comprehensive test cases for all major workflows (6 packs)
- 📈 **Reports**
  Reporting documentation and available report types
- 🚀 **[Deployment](deployment)**
  Deployment guide and operational procedures
- 📋 **[Import Playbook](import_playbook)**
  Step-by-step guide for importing historical data
- 🔍 **Data Quality**
  Data quality dashboard and validation rules
- 📚 **User Guide**
  Step-by-step instructions for common tasks
- 🔌 **API Reference**
  API documentation for integrations
- 🔒 **[Audit Requirements](audit_requirements)**
  Audit logging and compliance requirements

## Document Hierarchy

This documentation follows a **requirements → design → test** traceability chain:

| Layer | Documents | Purpose |
|-------|-----------|---------|
| Requirements | **[Purpose & Scope](purpose_scope)**, **[Use Cases](use_cases)**, **[Functional Reqs](#requirements)**, **[User Stories](user_stories)**, **[NFRs](non_functional_requirements)** | What the system must do and why |
| Design | **[Architecture](architecture)**, **[Data Dictionary](data_dictionary)**, **[Field Mappings](field_mappings)**, **[Metrics Bible](metrics_bible)**, **[RBAC Matrix](rbac_matrix)** | How the system is structured |
| Contracts | **[Contracts Overview](contracts)**, **[Contract A](contract_a)**, **[Contract B](contract_b)**, **[Contract C](contract_c)**, **[Contract D](contract_d)** | Integration boundaries and behaviors |
| Operations | **[Import Playbook](import_playbook)**, **[Monitoring](monitoring)**, **[Runbook](runbook)**, **[Smoke Tests](smoke_tests)**, **[Deployment](deployment)** | How to operate and troubleshoot |
| Security | **[Privacy & Data Handling](privacy_data_handling)**, **[Audit Requirements](audit_requirements)** | Security, privacy, and compliance |
| Testing | **[Test Packs Overview](test_packs/index)**, **[Test Pack 1](test_packs/test_pack_1)**, **[Test Pack 2](test_packs/test_pack_2)**, **[Test Pack 3](test_packs/test_pack_3)**, **[Test Pack 4](test_packs/test_pack_4)**, **[Test Pack 5](test_packs/test_pack_5)**, **[Test Pack 6](test_packs/test_pack_6)** | Verify requirements are met |

## Core Systems

| System | Purpose | Owns |
|--------|---------|------|
| **Salesforce (SF)** | Core data entry, CRM, in-person events, student attendance, email logging | Event details, student data, communication logs |
| **VolunTeach (VT)** | Event sync + website publishing controls | Publish toggle, district links |
| **Website (WEB)** | Public event display + volunteer signup | Signup capture (input only) |
| **Polaris (POL)** | Virtual events, recruitment, dashboards, reporting | Virtual events, teacher roster, metrics |
| **Pathful (PATH)** | Virtual signup + reminders + attendance | Session signups, attendance status |

## Public Website Structure

The public website volunteer hub ([https://prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)) provides access to multiple volunteer signup pages:

- **In-Person Events**: Signup for traditional in-person career events
- **Data in Action (DIA) Events**: Signup for data-focused events
- **Virtual Events**: Signup for virtual career sessions
- **Other Opportunities**: Additional volunteer programs

These pages are controlled by VolunTeach visibility toggles and district linking settings. Events synced from Salesforce to VolunTeach can be made visible on the appropriate website pages based on staff configuration in the VolunTeach admin interface.

## Document Relationships

### How to use this documentation

**Source of Truth (SoT) documents** are authoritative—other docs reference them, never duplicate.

- **[Purpose & Scope](purpose_scope)** → defines system boundaries and what's in/out of scope
- **[Data Dictionary](data_dictionary)** → defines all entities and fields
- **[Metrics Bible](metrics_bible)** → defines all calculations
- **[RBAC Matrix](rbac_matrix)** → defines all permissions

All other documents reference these sources rather than restating definitions.

### Document Types

**Source of Truth (SoT):**
- Single authoritative definition
- Referenced by other documents
- Updated through formal change process

**Reference Documents:**
- Link to SoT documents
- Provide context and usage examples
- Never duplicate SoT definitions

**Operational Documents:**
- Procedures and playbooks
- Troubleshooting guides
- Monitoring and alerting

## Open Decisions

> [!INFO]
> This section tracks open architectural and design decisions that require resolution.

*No open decisions at this time. Check back for updates.*

---

*Last updated: January 2026*
*Version: 1.0*
