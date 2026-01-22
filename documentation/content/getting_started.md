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

- 📋 **[Requirements](#requirements)**
  Functional requirements (FR-xxx) with test traceability
- 📖 **[User Stories](user_stories)**
  Business intent by epic with acceptance criteria
- 🔄 **[Use Cases](use_cases)**
  End-to-end workflows for key system functions
- 📋 **[Non-Functional Requirements](non_functional_requirements)**
  Quality attributes and system constraints
- 🏗️ **Architecture**
  System context, integration flows, and source-of-truth ownership
- 📊 **[Data Dictionary](data_dictionary)**
  Canonical entity definitions, field specs, and sensitivity levels
- 🔗 **[Field Mappings](field_mappings)**
  Cross-system data flow specifications
- 📐 **Metrics Bible**
  How every metric is calculated—the single source of truth for reporting
- 🔐 **RBAC Matrix**
  Role permissions and data access controls
- 🔒 **Privacy & Data Handling**
  Data protection rules and retention policies
- 🔌 **[Integration Contracts](contracts)**
  API specs for SF↔VT, Website, Gmail sync, Pathful import
- 🧪 **[Test Packs](#test-packs)**
  Comprehensive test cases for all major workflows (6 packs)
- 📈 **Reports**
  Reporting documentation and available report types
- 🚀 **Deployment**
  Deployment guide and operational procedures
- 🔍 **Data Quality**
  Data quality dashboard and validation rules
- 📚 **User Guide**
  Step-by-step instructions for common tasks
- 🔌 **API Reference**
  API documentation for integrations

## Document Hierarchy

This documentation follows a **requirements → design → test** traceability chain:

| Layer | Documents | Purpose |
|-------|-----------|---------|
| Requirements | **Purpose & Scope**, **Use Cases**, **[Functional Reqs](#requirements)**, **[User Stories](user_stories)**, **[NFRs](non_functional_requirements)** | What the system must do and why |
| Design | **Architecture**, **[Data Dictionary](data_dictionary)**, **[Field Mappings](field_mappings)**, **Metrics**, **RBAC** | How the system is structured |
| Contracts | **[Contract A](contract_a)**, **[Contract B](contract_b)**, **[Contract C](contract_c)**, **[Contract D](contract_d)** | Integration boundaries and behaviors |
| Operations | **Playbooks**, **[Monitoring](monitoring)**, **[Runbook](runbook)**, **[Smoke Tests](smoke_tests)** | How to operate and troubleshoot |
| Testing | **[Test Packs 1–6](#test-packs)** | Verify requirements are met |

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

- **[Data Dictionary](#data-dictionary)** → defines all entities and fields
- **[Metrics Bible](#metrics-bible)** → defines all calculations
- **[RBAC Matrix](#rbac-matrix)** → defines all permissions

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
