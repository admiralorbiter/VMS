# Non-Functional Requirements

**Quality attributes and system constraints**

## Overview

Non-functional requirements (NFRs) define quality attributes, system constraints, and cross-cutting concerns that apply across functional requirements. These requirements ensure the system meets usability, reliability, security, privacy, and performance expectations.

**Related Documentation:**
- [Functional Requirements](requirements) - What the system must do
- [User Stories](user_stories) - Business intent and acceptance criteria
- [Use Cases](use_cases) - End-to-end workflows

## Non-Functional Requirements

| ID | Category | Requirement | Related Functional Requirements |
|----|----------|-------------|--------------------------------|
| <a id="nfr-1"></a>**NFR-1** | Usability | The system shall be usable by non-technical users (staff, district, teachers) with minimal training. | *Applies across all user-facing features* |
| <a id="nfr-2"></a>**NFR-2** | Reliability | Sync/import workflows shall provide clear failure feedback (no silent drops). | [FR-INPERSON-102](requirements#fr-inperson-102), [FR-INPERSON-103](requirements#fr-inperson-103), [FR-INPERSON-122](requirements#fr-inperson-122), [FR-INPERSON-123](requirements#fr-inperson-123), [FR-INPERSON-124](requirements#fr-inperson-124), [FR-VIRTUAL-206](requirements#fr-virtual-206), [FR-RECRUIT-308](requirements#fr-recruit-308), [FR-RECRUIT-309](requirements#fr-recruit-309) |
| <a id="nfr-3"></a>**NFR-3** | Security | Access shall be restricted by role and district scope; teacher links must be strictly self-scoped. | [FR-DISTRICT-501](requirements#fr-district-501), [FR-DISTRICT-521](requirements#fr-district-521), [FR-DISTRICT-522](requirements#fr-district-522), [FR-DISTRICT-523](requirements#fr-district-523), [FR-DISTRICT-506](requirements#fr-district-506) |
| <a id="nfr-4"></a>**NFR-4** | Privacy | Demographic fields (gender, race/ethnicity, education attainment) shall be protected and only visible to authorized roles; auditability is preferred. | [FR-SIGNUP-126](requirements#fr-signup-126), [FR-SIGNUP-127](requirements#fr-signup-127), [Privacy & Data Handling](privacy_data_handling) |
| <a id="nfr-5"></a>**NFR-5** | Auditability | Key actions (publishing toggles, district linking, imports, teacher flags) shall be logged. | [FR-INPERSON-104](requirements#fr-inperson-104), [FR-INPERSON-107](requirements#fr-inperson-107), [FR-VIRTUAL-206](requirements#fr-virtual-206), [FR-DISTRICT-507](requirements#fr-district-507) |
| <a id="nfr-6"></a>**NFR-6** | Maintainability | Integrations (Salesforce, Pathful, VolunTeach) should be modular and diagnosable. | *Applies to all integration-related FRs* |
| <a id="nfr-7"></a>**NFR-7** | Data Integrity | Syncs/imports should be idempotent where practical (re-runs do not duplicate). | [FR-INPERSON-123](requirements#fr-inperson-123), [FR-VIRTUAL-206](requirements#fr-virtual-206), [FR-VIRTUAL-204](requirements#fr-virtual-204) |
| <a id="nfr-8"></a>**NFR-8** | Performance | Search and dashboards should return results quickly enough for interactive use. | [FR-RECRUIT-301](requirements#fr-recruit-301), [FR-RECRUIT-302](requirements#fr-recruit-302), [FR-DISTRICT-501](requirements#fr-district-501), [FR-DISTRICT-502](requirements#fr-district-502), [FR-REPORTING-401](requirements#fr-reporting-401), [FR-REPORTING-402](requirements#fr-reporting-402), [FR-REPORTING-403](requirements#fr-reporting-403) |

## Constraints

System boundaries and architectural constraints that shape design decisions:

- **Salesforce remains system of record** for much of data entry and attendance workflows. VolunTeach and Polaris sync from Salesforce but do not replace it as the primary data entry system.
- **Pathful handles virtual signup and reminders today**. Polaris imports attendance data from Pathful but does not replace Pathful's signup and reminder email functionality.
- **Website is currently unauthenticated for volunteers**. Volunteer signup forms do not require login or account creation, allowing quick registration.

## Dependencies

External systems and infrastructure dependencies:

- **Salesforce schema + Gmail logging behavior**: System depends on Salesforce data model and Gmail add-on logging functionality for communication history tracking.
- **Pathful export access and format stability**: Virtual event attendance imports depend on Pathful export availability and consistent data format.
- **Email/calendar deliverability infrastructure**: Confirmation emails and calendar invites depend on reliable email delivery infrastructure (Mailjet integration).

---

*Last updated: January 2026*
*Version: 1.0*
