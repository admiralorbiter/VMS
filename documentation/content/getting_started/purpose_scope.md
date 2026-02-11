# Purpose and Scope

> [!NOTE]
> **Executive Summary**
>
> **Polaris (VMS)** is the centralized hub for managing the volunteer lifecycle at PrepKC. It connects data from **Salesforce**, **VolunTeach**, and **Pathful** to provide a unified platform for event management, volunteer recruitment, and impact reporting.

## Purpose

The Volunteer Management System (VMS), also known as **Polaris**, is an integrated system designed to manage K–12 student connections with career professionals through in-person and virtual events. The system serves as a centralized platform for volunteer data management, event tracking, recruitment, and reporting across multiple integrated systems.

### Mission Statement

Polaris enables educational organizations to efficiently connect students with career professionals by providing a unified system for managing volunteer events, tracking participation, monitoring district and teacher progress, and generating comprehensive impact reports.

### Primary Goals

- **Centralize volunteer data** from multiple sources (Salesforce, Pathful, Google Sheets, internal datasets)
- **Streamline event management** for both in-person and virtual career events
- **Enable volunteer recruitment** through searchable volunteer databases and communication history
- **Track district and teacher progress** toward program goals with self-service dashboards
- **Provide comprehensive reporting** for grant reporting, district impact analysis, and volunteer recognition
- **Support data-driven decisions** through analytics, dashboards, and ad hoc querying capabilities

### Business Value

| Value | Description |
|-------|-------------|
| **Operational Efficiency** | Reduces manual data entry and duplicate work across systems |
| **Visibility** | Provides real-time visibility into event status, volunteer participation, and district progress |
| **Compliance** | Supports grant reporting and district accountability requirements |
| **Engagement** | Enables proactive volunteer recruitment and relationship management |
| **Impact Measurement** | Tracks unique students reached, volunteer hours, and organizational engagement |

---

## Scope

### In Scope

The system includes the following functional domains, each defined by functional requirements in [Requirements](../requirements/index):

#### In-Person Event Management
- Event creation and maintenance in Salesforce
- Automated and manual synchronization from Salesforce to VolunTeach
- Public website event listings with visibility controls
- District-specific event pages
- Volunteer and student participation tracking
- Event status management (Draft, Requested, Confirmed, Published, Completed, Cancelled)
- Historical data import capabilities

**Related Requirements:** [FR-INPERSON-101](../requirements/index#fr-inperson-101) through [FR-INPERSON-133](../requirements/index#fr-inperson-133)

#### Public Volunteer Signup
- Public volunteer signup forms (no authentication required)
- Volunteer demographic data collection (name, email, organization, skills, demographics)
- Automatic confirmation emails and calendar invites
- Signup data storage for reporting and recruitment

**Related Requirements:** [FR-SIGNUP-121](../requirements/index#fr-signup-121) through [FR-SIGNUP-127](../requirements/index#fr-signup-127)

#### Virtual Events
- Virtual event creation and management in Polaris
- Teacher and presenter tagging for virtual sessions
- Pathful export import for attendance and participation
- Historical virtual event data import from Google Sheets
- Presenter recruitment view with urgency indicators
- Local vs. non-local volunteer tracking

**Related Requirements:** [FR-VIRTUAL-201](../requirements/index#fr-virtual-201) through [FR-VIRTUAL-219](../requirements/index#fr-virtual-219)

#### Volunteer Search & Intelligent Matching
- Searchable volunteer database with filtering capabilities
- **Algorithmic candidate ranking** (scoring by history, location, keywords)
- **Custom keyword targeting** for precise skill matching
- Volunteer participation history tracking
- Communication history from Salesforce email logging
- Recruitment notes and outcome tracking
- Volunteer search by name, organization, role, skills, and career type

**Related Requirements:** [FR-RECRUIT-301](../requirements/index#fr-recruit-301) through [FR-RECRUIT-311](../requirements/index#fr-recruit-311)

#### Reporting and Dashboards
- Volunteer thank-you dashboards (top volunteers by hours/events)
- Organization participation reports
- District/school impact dashboards
- **Partner Data Reconciliation** (e.g., KCTAA) matching external lists against internal data
- **Fuzzy Name Matching** to identify near-matches across systems
- Ad hoc querying capabilities
- Export functionality (CSV) for grant and district reporting

**Related Requirements:** [FR-REPORTING-401](../requirements/index#fr-reporting-401) through [FR-REPORTING-408](../requirements/index#fr-reporting-408)

#### District and Teacher Progress
- District viewer authentication and access control
- District dashboards with school and teacher drilldown
- Teacher progress status computation (Achieved, In Progress, Not Started)
- Teacher roster import and management
- Teacher magic link self-service access
- Teacher data flagging and issue reporting

**Related Requirements:** [FR-DISTRICT-501](../requirements/index#fr-district-501) through [FR-DISTRICT-530](../requirements/index#fr-district-530)

#### Student Roster and Attendance
- Student association with events (roster management)
- Student attendance status tracking per event
- Student reach metrics by district, school, event type, and date range
- Integration with Salesforce student participation data

**Related Requirements:** [FR-STUDENT-601](../requirements/index#fr-student-601) through [FR-STUDENT-604](../requirements/index#fr-student-604)

#### Email System Management
- Email template creation and versioning
- Email delivery monitoring and status tracking
- Admin email sending with safety controls
- Environment-based delivery gates and non-production allowlist
- Quality checks and delivery attempt tracking
- Automatic bug report creation for failed deliveries

**Related Requirements:** [FR-EMAIL-801](../requirements/index#fr-email-801) through [FR-EMAIL-808](../requirements/index#fr-email-808)

#### Tenant Infrastructure (District Suite)
- Multi-tenant database isolation (SQLite per tenant)
- Tenant provisioning and lifecycle management
- Reference data duplication to tenant databases
- Cross-tenant administrative access for PrepKC staff
- Feature flag management per tenant
- API key generation and management

**Related Requirements:** [FR-TENANT-101](../requirements/index#fr-tenant-101) through [FR-TENANT-107](../requirements/index#fr-tenant-107)

#### District Self-Service (District Suite)
- District event creation, editing, and cancellation
- Event calendar and list views for district staff
- District volunteer pool management and import
- Volunteer-to-event assignment and participation tracking
- Recruitment dashboard with volunteer recommendations
- Public signup forms for district events
- Read-only visibility of PrepKC events at district schools

**Related Requirements:** [FR-SELFSERV-201](../requirements/index#fr-selfserv-201) through [FR-SELFSERV-503](../requirements/index#fr-selfserv-503)

#### Public Event API (District Suite)
- REST API for district website event embedding
- API key authentication per tenant
- Rate limiting and CORS configuration
- Event listing and detail endpoints

**Related Requirements:** [FR-API-101](../requirements/index#fr-api-101) through [FR-API-108](../requirements/index#fr-api-108)

---

### Out of Scope

The following capabilities are **explicitly excluded** from the current system scope:

#### Data Entry Systems
- **Salesforce remains the system of record** for in-person event creation, student attendance entry, and email logging. Polaris/VolunTeach sync from Salesforce but do not replace Salesforce as the primary data entry interface.
- **Pathful handles virtual event signup and reminder emails**. Polaris imports attendance data from Pathful but does not replace Pathful's signup workflow or automated reminder functionality.

#### Authentication and Access
- **Volunteer account management**: Public volunteer signup does not require account creation or login. Volunteers sign up using email-based identity only.
- **Salesforce authentication**: Staff access to Salesforce is managed separately and is not part of Polaris scope.

#### Direct Student/Volunteer Features
- **Student self-service portals**: Students do not directly interact with Polaris. Student data is managed through Salesforce and reported in Polaris.
- **Volunteer self-service dashboards**: Volunteers do not have self-service access to view their participation history or manage their profiles (except through public signup forms).

#### External System Features
- **Website content management**: The public website ([prepkc.org/volunteer.html](https://prepkc.org/volunteer.html)) content and structure are managed separately. Polaris provides data via API but does not manage website design or content.
- **Salesforce workflow automation**: Salesforce-specific workflows, automation rules, and process builders are outside Polaris scope.

#### Future Considerations (Near-Term)
Some features are planned but not yet implemented:
- **Automated reminder emails to teachers** based on progress status
- **Automated Pathful export pulling** and loading into Polaris
- **Automated communications connecting local volunteers**

These are marked as "near-term" in requirements and may be added to scope in future releases.

---

## System Boundaries

### Integration Points

Polaris integrates with core systems to provide a unified experience.

![VMS Data Flow Architecture](content/images/vms_architecture_optimized.png)

| System | Role |
|--------|------|
| **Salesforce** | Core CRM, System of Record for In-Person Events |
| **VolunTeach** | Sync engine and publishing control for In-Person Events |
| **Polaris** | Core application for Virtual Events, Reporting, and District Dashboards |
| **Pathful** | Platform for Virtual Session hosting and attendance tracking |

**Reference:** [System Architecture](../technical/architecture) for detailed integration flows and source-of-truth ownership.

### Source of Truth Ownership

**Golden Rule:** Every field has exactly one owner. Downstream systems copy but never edit owned fields.

| Data | Owner |
|------|-------|
| In-person event core fields | Salesforce (title, dates, location, status) |
| In-person page visibility | VolunTeach (`Event.inperson_page_visible`) |
| District event linking | VolunTeach (`Event.district_links[]`) |
| Virtual event definition | Polaris |
| Virtual attendance/signup | Pathful (imported to Polaris) |
| Teacher roster | Polaris (imported from district-provided rosters) |
| Student attendance | Salesforce (aggregated in Polaris) |
| Communication logs | Salesforce (synced to Polaris) |
| Volunteer identity | Polaris (normalized email is primary key) |
| District-created events | Tenant's Polaris instance (District Suite) |
| District volunteer pools | Tenant's Polaris instance (District Suite) |
| Tenant configuration | Main Polaris instance (District Suite) |

**Reference:** [Field Mappings](../technical/field_mappings) for detailed field ownership and mapping specifications.

---

## Target Users

| Role | Access | Use Cases |
|------|--------|-----------|
| **Admin Users** | Full system access | Email templates, system configuration, event management |
| **User Role** | Standard staff access | Events, volunteers, reports, dashboards |
| **District Viewer** | District-specific dashboards | Monitor progress, view teacher status, flag data issues |
| **Teachers** | Magic link self-service | View session history, flag incorrect data |
| **Volunteers (Public)** | Signup forms only | Sign up for events (no account required) |
| **District Admin** (District Suite) | Full tenant access | Create events, manage volunteers, configure settings |
| **District Coordinator** (District Suite) | Event/volunteer management | Create events, assign volunteers, track participation |

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Functional Requirements](../requirements/index) | FR-xxx specifications by domain |
| [User Stories](../requirements/user_stories) | Business intent and acceptance criteria |
| [Use Cases](../requirements/use_cases) | End-to-end workflows |
| [System Architecture](../technical/architecture) | Integration flows and source-of-truth |
| [Non-Functional Requirements](../requirements/non_functional) | Quality attributes and constraints |
| [Data Dictionary](../technical/data_dictionary) | Entity definitions and field specs |
| [Field Mappings](../technical/field_mappings) | Cross-system data flow |
| [Integration Contracts](../technical/contracts/index) | API specifications |
| [District Suite Phases](../district_suite/phases) | Multi-tenant development roadmap |
| [Tenant Management Guide](../user_guide/tenant_management) | PrepKC admin guide for tenants |
| [District Self-Service Guide](../user_guide/district_self_service) | District user guide |

---

> [!NOTE]
> **Source of Truth**
>
> This document is authoritative for system purpose and scope. Any changes to system boundaries or scope must be reflected here and may require updates to related requirements documents.

---

*Last updated: February 2026 · Version 1.3*
