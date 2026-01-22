# Purpose and Scope

**System purpose, boundaries, and functional coverage**

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

- **Operational Efficiency**: Reduces manual data entry and duplicate work across systems
- **Visibility**: Provides real-time visibility into event status, volunteer participation, and district progress
- **Compliance**: Supports grant reporting and district accountability requirements
- **Engagement**: Enables proactive volunteer recruitment and relationship management
- **Impact Measurement**: Tracks unique students reached, volunteer hours, and organizational engagement

## Scope

### In Scope

The system includes the following functional domains, each defined by functional requirements in [Requirements](requirements):

#### 7.1 In-Person Event Management
- Event creation and maintenance in Salesforce
- Automated and manual synchronization from Salesforce to VolunTeach
- Public website event listings with visibility controls
- District-specific event pages
- Volunteer and student participation tracking
- Event status management (Draft, Requested, Confirmed, Published, Completed, Cancelled)
- Historical data import capabilities

**Related Requirements:** [FR-INPERSON-101](requirements#fr-inperson-101) through [FR-INPERSON-133](requirements#fr-inperson-133)

#### 7.2 Public Volunteer Signup
- Public volunteer signup forms (no authentication required)
- Volunteer demographic data collection (name, email, organization, skills, demographics)
- Automatic confirmation emails and calendar invites
- Signup data storage for reporting and recruitment

**Related Requirements:** [FR-SIGNUP-121](requirements#fr-signup-121) through [FR-SIGNUP-127](requirements#fr-signup-127)

#### 7.3 Virtual Events
- Virtual event creation and management in Polaris
- Teacher and presenter tagging for virtual sessions
- Pathful export import for attendance and participation
- Historical virtual event data import from Google Sheets
- Presenter recruitment view with urgency indicators
- Local vs. non-local volunteer tracking

**Related Requirements:** [FR-VIRTUAL-201](requirements#fr-virtual-201) through [FR-VIRTUAL-219](requirements#fr-virtual-219)

#### 7.4 Volunteer Search, Recruitment & Communication History
- Searchable volunteer database with filtering capabilities
- Volunteer participation history tracking
- Communication history from Salesforce email logging
- Recruitment notes and outcome tracking
- Volunteer search by name, organization, role, skills, and career type

**Related Requirements:** [FR-RECRUIT-301](requirements#fr-recruit-301) through [FR-RECRUIT-309](requirements#fr-recruit-309)

#### 7.5 Reporting and Dashboards
- Volunteer thank-you dashboards (top volunteers by hours/events)
- Organization participation reports
- District/school impact dashboards
- Ad hoc querying capabilities
- Export functionality (CSV) for grant and district reporting

**Related Requirements:** [FR-REPORTING-401](requirements#fr-reporting-401) through [FR-REPORTING-406](requirements#fr-reporting-406)

#### 7.6 District and Teacher Progress
- District viewer authentication and access control
- District dashboards with school and teacher drilldown
- Teacher progress status computation (Achieved, In Progress, Not Started)
- Teacher roster import and management
- Teacher magic link self-service access
- Teacher data flagging and issue reporting

**Related Requirements:** [FR-DISTRICT-501](requirements#fr-district-501) through [FR-DISTRICT-530](requirements#fr-district-530)

#### 7.7 Student Roster and Attendance
- Student association with events (roster management)
- Student attendance status tracking per event
- Student reach metrics by district, school, event type, and date range
- Integration with Salesforce student participation data

**Related Requirements:** [FR-STUDENT-601](requirements#fr-student-601) through [FR-STUDENT-604](requirements#fr-student-604)

#### 7.8 Email System Management
- Email template creation and versioning
- Email delivery monitoring and status tracking
- Admin email sending with safety controls
- Environment-based delivery gates and non-production allowlist
- Quality checks and delivery attempt tracking
- Automatic bug report creation for failed deliveries

**Related Requirements:** [FR-EMAIL-801](requirements#fr-email-801) through [FR-EMAIL-808](requirements#fr-email-808)

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
- **Automated reminder emails to teachers** based on progress status ([FR-DISTRICT-504](requirements#fr-district-504))
- **Automated Pathful export pulling** and loading into Polaris ([FR-VIRTUAL-207](requirements#fr-virtual-207))
- **Automated communications connecting local volunteers** ([FR-VIRTUAL-209](requirements#fr-virtual-209))

These are marked as "near-term" in requirements and may be added to scope in future releases.

## System Boundaries

### Integration Points

Polaris integrates with five core systems, each with distinct ownership and responsibilities:

| System | Purpose | Owns | Polaris Role |
|--------|---------|------|--------------|
| **Salesforce (SF)** | Core CRM, data entry, in-person events, student attendance, email logging | Event details, student data, communication logs | Syncs and aggregates data from Salesforce |
| **VolunTeach (VT)** | Event sync + website publishing controls | Publish toggle, district links | Provides sync interface and publishing controls |
| **Website (WEB)** | Public event display + volunteer signup | Signup capture (input only) | Provides event data via API, receives signup submissions |
| **Polaris (POL)** | Virtual events, recruitment, dashboards, reporting | Virtual events, teacher roster, metrics | Core system - manages virtual events and reporting |
| **Pathful (PATH)** | Virtual signup + reminders + attendance | Session signups, attendance status | Imports attendance data from Pathful exports |

**Reference:** [System Architecture](architecture) for detailed integration flows and source-of-truth ownership.

### Source of Truth Ownership

**Golden Rule:** Every field has exactly one owner. Downstream systems copy but never edit owned fields.

- **In-person event core fields**: Owned by Salesforce (title, dates, location, status)
- **In-person page visibility**: Owned by VolunTeach (`Event.inperson_page_visible`)
- **District event linking**: Owned by VolunTeach (`Event.district_links[]`)
- **Virtual event definition**: Owned by Polaris
- **Virtual attendance/signup**: Owned by Pathful (imported to Polaris)
- **Teacher roster**: Owned by Polaris (imported from district-provided rosters)
- **Student attendance**: Owned by Salesforce (aggregated in Polaris)
- **Communication logs**: Owned by Salesforce (synced to Polaris)
- **Volunteer identity**: Owned by Polaris (normalized email is primary key)

**Reference:** [Field Mappings](field_mappings) for detailed field ownership and mapping specifications.

## Target Users

### Internal Staff
- **Admin Users**: Full system access, email template management, system configuration
- **User Role**: Standard staff access to events, volunteers, reports, and dashboards
- **Use Cases**: Event management, volunteer recruitment, report generation, district oversight

### District Coordinators
- **District Viewer Role**: Access to district-specific dashboards and teacher progress data
- **Use Cases**: Monitor district progress, view teacher completion status, flag data issues
- **Access Scope**: Limited to their assigned district(s)

### Teachers
- **Teacher Magic Link Access**: Self-service access via email-based magic link
- **Use Cases**: View personal session history, flag incorrect data
- **Access Scope**: Single teacher identity only (matched by email)

### Volunteers (Public)
- **Unauthenticated Access**: Public signup forms for events
- **Use Cases**: Sign up for in-person, virtual, or DIA events
- **Access Scope**: Signup forms only (no account or dashboard access)

## Related Documentation

This document provides the foundational understanding of system purpose and boundaries. For detailed information, see:

- **[Requirements](requirements)** - Complete functional requirements (FR-xxx) organized by domain
- **[User Stories](user_stories)** - Business intent and acceptance criteria for each feature
- **[Use Cases](use_cases)** - End-to-end workflows showing how users accomplish tasks
- **[System Architecture](architecture)** - Integration flows, source-of-truth ownership, and system context
- **[Non-Functional Requirements](non_functional_requirements)** - Quality attributes, constraints, and cross-cutting concerns
- **[Data Dictionary](data_dictionary)** - Canonical entity definitions and field specifications
- **[Field Mappings](field_mappings)** - Cross-system data flow specifications
- **[Integration Contracts](contracts)** - API specifications and integration boundaries

## Document Status

> [!NOTE]
> **Source of Truth**
>
> This document is authoritative for system purpose and scope. Any changes to system boundaries or scope must be reflected here and may require updates to related requirements documents.

---

*Last updated: January 2026*
*Version: 1.0*
