# Privacy & Data Handling

**Data protection rules and retention policies**

## Source of Truth

This document is authoritative for all data protection, privacy, and retention policies. Any deviation requires documented exception.

**Related Documentation:**
- [RBAC Matrix](rbac_matrix) - Access controls and role-based permissions
- [Data Dictionary](data_dictionary) - Field sensitivity levels and entity definitions
- [Non-Functional Requirements - NFR-4](non_functional_requirements#nfr-4) - Privacy requirements

## Core Principles

### Minimization
Collect only fields with documented purpose. Each data field must have a clear business justification.

### Least Privilege
Default to no access; grant only what's needed. Users see only data required for their role and scope.

### Aggregation
Prefer aggregates over individual records. District viewers see counts and summaries, not student-level PII.

### Transparency
Document why we collect each field. Data collection purposes are documented in this policy.

## Data Collection Purposes

| Category | Examples | Purpose |
|----------|----------|---------|
| Volunteer Identity | name, email, org, title | Participation tracking, communications, recognition |
| Volunteer Demographics | age, education, gender, race | Program evaluation, equity analysis, grant reporting (aggregated) |
| Teacher Roster | name, email, school, grade | Progress tracking, magic links, dashboard scoping |
| Student Attendance | student ID, attendance status | Impact metrics, district reporting (aggregated) |
| Communication Logs | subject, snippet, timestamp | Recruitment continuity, relationship tracking |

**Reference:** [Data Dictionary - Sensitivity Levels](data_dictionary#sensitivity-levels) for field-level sensitivity classifications.

## Retention Defaults

> [!INFO]
> **TBD:** Final retention periods pending organizational/legal review. See [Open Decisions](#open-decisions).

| Data | Recommended Retention | Notes |
|------|----------------------|-------|
| Volunteer PII + participation | 7 years after last activity | Then archive/delete |
| Volunteer demographics | 3–7 years | Review annually |
| Teacher roster | 2 years after school year | Align to district agreement |
| Student attendance | Per district policy | Prefer aggregates in Polaris |
| Communication logs | 3–7 years | Snippets over full body |

## Security Requirements

### Transmission & Storage

- **HTTPS/TLS** for all API communication
- **Secrets in secure secret manager** (not code)
- **Encrypt sensitive data at rest** where feasible

**Implementation:**
- All API endpoints require HTTPS
- Environment variables for secrets (not hardcoded)
- Database connections use encrypted channels

### Logging

- **No full PII in application logs**
- **Use hashed email for identifiers** when logging user actions
- **Log access to exports and sensitive reports**

**Implementation:**
- Application logs exclude student names, full email addresses
- Audit logs track who accessed what data and when
- Export operations logged with user ID and timestamp
- Reference: [Audit Requirements](audit_requirements) for detailed audit logging requirements

### Magic Links

**Token Requirements:**
- Tokens must be **unguessable** (cryptographically random)
- **Time-limited** (recommended expiration)
- **Bound to teacher email** (self-only scope)
- **Don't reveal roster membership** on unknown email requests

**Implementation:**
- Token generation: `secrets.token_hex(32)` (64-character hex string)
- Token validation checks expiration and email binding
- Unknown emails return generic "check your email" message (no roster confirmation)
- Reference: [RBAC Matrix - Teacher Magic Link System](rbac_matrix#teacher-magic-link-system)

### Incident Response

If you suspect data leakage (e.g., teacher sees wrong data):

1. **Treat as SEV1** - Highest priority security incident
2. **Disable affected endpoint** if possible
3. **Document scope** - What data was exposed, to whom, when
4. **Notify leadership** - Escalate immediately
5. **Follow Runbook** - [Runbook 10.2 - Case D: Wrong Data (SEV1)](runbook#case-d-wrong-data-sev1)

> [!WARNING]
> **Incident Response:** Any suspected data leakage should be treated as a critical security incident. Follow organizational incident response procedures immediately.

**Reference:** [Runbook](runbook) for detailed troubleshooting procedures

## Access Control

Access to sensitive data is controlled by role and scope:

- **District Viewers:** Aggregates only, no student-level PII
- **Teachers (Magic Links):** Self-only data, no other teachers or students
- **Global Users:** Full access within their security level
- **Admins:** Full system access

**Reference:** [RBAC Matrix](rbac_matrix) for detailed access control rules.

## Data Sensitivity Levels

Fields are classified by sensitivity level:

| Level | Description | Access Rules |
|-------|-------------|--------------|
| **Public** | Safe to show publicly | No restrictions |
| **Internal** | Internal-only, not sensitive | Authenticated users only |
| **Sensitive** | PII like name/email | Role-based access, no District Viewers |
| **Highly Sensitive** | Students, demographics | Admin/Manager only, aggregated for District Viewers |

**Reference:** [Data Dictionary - Sensitivity Levels](data_dictionary#sensitivity-levels)

## Open Decisions

1. **Final Retention Periods:** Pending organizational/legal review
2. **Encryption at Rest:** Specific implementation details TBD

## Related Requirements

- [NFR-4](non_functional_requirements#nfr-4): Privacy - Demographic fields protected
- [FR-DISTRICT-501](requirements#fr-district-501): District Viewer authentication
- [FR-DISTRICT-521](requirements#fr-district-521): District Viewer data access restrictions
- [FR-DISTRICT-522](requirements#fr-district-522): District Viewer export restrictions

---

*Last updated: January 2026*
*Version: 1.0*
