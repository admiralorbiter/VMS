# RBAC Matrix

**Role-based access control — Source of Truth**

## Source of Truth

This matrix is authoritative for all permission decisions. Any deviation requires documented exception.

**Related Documentation:**
- [Data Dictionary](data_dictionary) - Entity and field definitions
- [Metrics Bible](metrics_bible) - Metric calculation definitions

## Role System

The VMS uses a two-dimensional role system:

1. **Security Level** (hierarchical): Controls functional permissions
2. **Scope Type** (data access): Controls which data a user can access

### Security Levels

Hierarchical permission levels stored in `User.security_level`:

| Level | Value | Description |
|-------|-------|-------------|
| **USER** | 0 | Basic access to view data and perform limited operations |
| **SUPERVISOR** | 1 | Can supervise regular users and access additional features |
| **MANAGER** | 2 | Can manage supervisors and users, access administrative features |
| **ADMIN** | 3 | Full system access with all privileges |

**Implementation:**
- Stored as Integer in `User.security_level`
- Checked via `User.has_permission_level(required_level)`
- `User.is_admin` property returns `True` if `security_level == ADMIN (3)`
- Reference: `models/user.py` `SecurityLevel` enum

### Scope Types

Data access scope stored in `User.scope_type`:

| Scope | Description | Access |
|-------|-------------|--------|
| **global** | Full access to all districts and schools (default) | All data |
| **district** | Limited to specific assigned districts | Only `allowed_districts` |
| **school** | Limited to specific schools | Future implementation |

**Implementation:**
- Stored as String in `User.scope_type` (default: `'global'`)
- District access via `User.allowed_districts` (JSON array of district names)
- Checked via `User.can_view_district(district_name)`
- Reference: `models/user.py`, `routes/decorators.py`

### Primary Role Combinations

| Role | Security Level | Scope Type | Description |
|------|---------------|------------|-------------|
| **Admin** | ADMIN (3) | global | Full system access, user/role management, config |
| **User** | USER/SUPERVISOR/MANAGER (0-2) | global | Internal staff; full operational access to data/workflows |
| **District Viewer** | Any | district | Read-only access to own district's dashboards |
| **Teacher** | N/A | N/A | Magic-link access; self-only progress view |

**Note:** Teacher access is not a User record. Teachers access via magic link token bound to `TeacherProgress.email`.

## Capability Matrix

✅ Allowed · 🔒 Scoped (restricted to assigned districts) · 🚫 Not allowed

### Authentication & User Management

| Capability | Admin | User | District Viewer | Teacher |
|------------|-------|------|-----------------|---------|
| Create/disable users | ✅ | 🚫 | 🚫 | 🚫 |
| Assign roles | ✅ | 🚫 | 🚫 | 🚫 |
| View audit logs | ✅ | 🔒 | 🚫 | 🚫 |
| Change own password | ✅ | ✅ | ✅ | 🚫 |

**Implementation:**
- User management: `routes/management/management.py` with `@admin_required`
- Password changes: Available to all authenticated users via `/admin`
- Audit logs: `models/audit_log.py` (Admin only)

### Events & Publishing

| Capability | Admin | User | District Viewer | Teacher |
|------------|-------|------|-----------------|---------|
| Create/edit SF events | ✅ | ✅ | 🚫 | 🚫 |
| Toggle publish visibility | ✅ | ✅ | 🚫 | 🚫 |
| Link district to event | ✅ | ✅ | 🚫 | 🚫 |
| Create virtual event | ✅ | ✅ | 🚫 | 🚫 |
| Import Pathful/roster | ✅ | ✅ | 🚫 | 🚫 |

**Implementation:**
- Event management: `routes/events/routes.py` with `@global_users_only`
- Virtual events: `routes/virtual/routes.py` with `@global_users_only`
- Pathful import: Admin-only routes in `routes/virtual/usage.py`

**Note:** All event management capabilities require `scope_type = 'global'` (enforced via `@global_users_only` decorator).

### Recruitment

| Capability | Admin | User | District Viewer | Teacher |
|------------|-------|------|-----------------|---------|
| Search volunteers | ✅ | ✅ | 🚫 | 🚫 |
| View volunteer profile | ✅ | ✅ | 🚫 | 🚫 |
| View comms history | ✅ | ✅ | 🚫 | 🚫 |
| Export volunteer lists | ✅ | ✅ | 🚫 | 🚫 |

**Implementation:**
- Volunteer routes: `routes/volunteers/routes.py` with `@global_users_only`
- Recruitment: `routes/reports/recruitment.py` with `@login_required` and `@global_users_only`

**Note:** Volunteer data is not accessible to District Viewers or Teachers (see Data Access Matrix).

### Dashboards & Reporting

| Capability | Admin | User | District Viewer | Teacher |
|------------|-------|------|-----------------|---------|
| Global dashboards (volunteer/org) | ✅ | ✅ | 🚫 | 🚫 |
| District impact dashboard | ✅ | ✅ | 🔒 | 🚫 |
| District progress dashboard | ✅ | ✅ | 🔒 | 🚫 |
| School/teacher drilldown | ✅ | ✅ | 🔒 | 🚫 |
| Teacher self-view (magic link) | ✅ | ✅ | 🚫 | ✅ |

**Implementation:**
- Global dashboards: `routes/reports/organization_report.py`, `routes/reports/volunteer_thankyou.py`
- District dashboards: `routes/virtual/usage.py` with `@district_scoped_required`
- Teacher dashboard: `routes/virtual/teacher_dashboard.py` (magic link access)

**Scoping:**
- District Viewers see only their assigned districts (enforced via `@district_scoped_required`)
- Teachers see only their own progress data (enforced via magic link token)

## Data Access Matrix

### Volunteer Fields

| Data | Admin | User | District Viewer | Teacher |
|------|-------|------|-----------------|---------|
| Name / Email | ✅ | ✅ | 🚫 | 🚫 |
| Organization / Title | ✅ | ✅ | 🚫 | 🚫 |
| Skills | ✅ | ✅ | 🚫 | 🚫 |
| Demographics | ✅ | ✅ | 🚫 | 🚫 |

**Demographics include:**
- Race/ethnicity (`Volunteer.race_ethnicity`)
- Gender (`Volunteer.gender`)
- Education (`Volunteer.education`)
- Age group (`Contact.age_group`)

> [!DANGER]
> **Hard Rule:** Demographics (race/ethnicity, gender, education, age) are never visible to District Viewers or Teachers.

**Implementation:**
- Volunteer routes: `routes/volunteers/routes.py` with `@global_users_only`
- Volunteer entity: See [Data Dictionary](data_dictionary#entity-volunteer)

### Student Fields

| Data | Admin | User | District Viewer | Teacher |
|------|-------|------|-----------------|---------|
| Student identity (name, ID) | ✅ | ✅ | 🚫 | 🚫 |
| Row-level attendance | ✅ | ✅ | 🚫 | 🚫 |
| Aggregate counts | ✅ | ✅ | 🔒 | 🚫 |

**Student identity includes:**
- Name (`Student.first_name`, `Student.last_name`)
- Student ID (`Student.student_id`)
- School ID (`Student.school_id`)

> [!DANGER]
> **Hard Rule:** District Viewers get aggregates only, never student-level PII.

**Implementation:**
- Student routes: `routes/students/routes.py` with `@global_users_only`
- Aggregate counts: District dashboards show counts only, no individual student records
- Student entity: See [Data Dictionary](data_dictionary#entity-student)

### Teacher Fields

| Data | Admin | User | District Viewer | Teacher |
|------|-------|------|-----------------|---------|
| Teacher name | ✅ | ✅ | 🔒 | ✅ (self-only) |
| Teacher email | ✅ | ✅ | 🔒 | ✅ (self-only) |
| Teacher progress status | ✅ | ✅ | 🔒 | ✅ (self-only) |
| Teacher school | ✅ | ✅ | 🔒 | 🚫 |

**Implementation:**
- Teacher routes: `routes/teachers/routes.py` with `@global_users_only`
- District dashboards: Show teacher names and progress for assigned districts
- Teacher dashboard: Magic link shows only own progress
- Teacher entity: See [Data Dictionary](data_dictionary#entity-teacher)

### Event Fields

| Data | Admin | User | District Viewer | Teacher |
|------|-------|------|-----------------|---------|
| Event details | ✅ | ✅ | 🔒 | 🚫 |
| Event participation | ✅ | ✅ | 🔒 (aggregates) | 🚫 |

**Event details include:**
- Title, description, dates
- Location, format, type
- School, district associations

**Event participation:**
- Volunteer participation (aggregate counts for District Viewers)
- Student participation (aggregate counts only for District Viewers)
- Teacher participation (visible to District Viewers for their districts)

**Implementation:**
- Event routes: `routes/events/routes.py` with `@global_users_only`
- District dashboards: Filter events by `allowed_districts`
- Event entity: See [Data Dictionary](data_dictionary#entity-event)

## Scope Enforcement Rules

### S1 — District Scoping

District Viewer sees only data for districts in `allowed_districts`.

**Enforcement:**
- URL tampering must not bypass (enforced via `@district_scoped_required` decorator)
- Database queries filtered by `User.can_view_district(district_name)`
- District name extracted from route parameters or query string

**Implementation:**
```python
@district_scoped_required
def district_report(district_name):
    # User already validated for district access
    # Query filtered by district_name
```

**Reference:**
- Decorator: `routes/decorators.py` `district_scoped_required()`
- User method: `models/user.py` `User.can_view_district(district_name)`
- Usage: `routes/virtual/usage.py` district dashboard routes

**Example:**
- District Viewer with `allowed_districts = ["Kansas City Kansas Public Schools"]`
- Can access: `/virtual/usage/district/Kansas City Kansas Public Schools/...`
- Cannot access: `/virtual/usage/district/Hickman Mills School District/...` (403 Forbidden)

### S2 — Teacher Scoping

Magic link token bound to `TeacherProgress.email`. Time-limited, unguessable.

**Enforcement:**
- Token generated from `TeacherProgress.email` (normalized)
- Teacher can only view their own progress data
- Token validated server-side before rendering dashboard

**Implementation:**
- Route: `routes/virtual/teacher_dashboard.py` `/kck/teacher/<teacher_id>`
- Token validation: Checks teacher email matches token
- Data filtering: Only shows `EventTeacher` records for that teacher

**Reference:**
- Teacher dashboard: `routes/virtual/teacher_dashboard.py`
- Teacher progress: `models/teacher_progress.py`
- Requirements: [FR-DISTRICT-505](requirements#fr-district-505), [FR-DISTRICT-506](requirements#fr-district-506)

**Access Scope:**
- Teacher sees: Own name, email, progress status, past/upcoming sessions
- Teacher cannot see: Other teachers, district aggregates, student data

### S3 — Export Scoping

If enabled for District Viewer, filter server-side and omit restricted fields.

**Enforcement:**
- Export functions check `User.scope_type`
- Apply district filter to exported data
- Omit restricted fields (demographics, student PII) from exports

**Restricted Fields in Exports:**
- Volunteer demographics (race/ethnicity, gender, education, age)
- Student PII (name, student_id, row-level attendance)
- Volunteer contact information (for District Viewers)

**Implementation:**
- Export routes: `routes/reports/` with scope checks
- Filtering: Applied before data serialization
- Field omission: Conditional based on user scope

**Example:**
- District Viewer exports district report
- Export includes: Aggregate student counts, teacher names, event summaries
- Export excludes: Student names, volunteer emails, demographics

## Decorators Reference

Access control decorators used throughout the application:

### @login_required

**Source:** Flask-Login

**Purpose:** Requires user authentication

**Usage:**
```python
from flask_login import login_required

@login_required
def protected_route():
    # User must be authenticated
```

**Implementation:**
- Provided by Flask-Login
- Redirects to login if not authenticated
- Sets `current_user` for authenticated requests

### @admin_required

**Source:** `routes/utils.py`

**Purpose:** Requires admin privileges (`is_admin = True`)

**Usage:**
```python
from routes.utils import admin_required

@admin_required
def admin_only_route():
    # User must be admin
```

**Implementation:**
- Checks `current_user.is_admin` (security_level == ADMIN)
- Returns 403 Forbidden if not admin
- Reference: `routes/utils.py` `admin_required()`

### @global_users_only

**Source:** `routes/decorators.py`

**Purpose:** Restricts access to global users only

**Usage:**
```python
from routes.decorators import global_users_only

@global_users_only
def global_only_route():
    # User must have scope_type = 'global'
```

**Implementation:**
- Checks `current_user.scope_type == 'global'`
- Blocks district-scoped and school-scoped users
- Returns 403 Forbidden if not global
- Reference: `routes/decorators.py` `global_users_only()`

### @district_scoped_required

**Source:** `routes/decorators.py`

**Purpose:** Validates district access for district-scoped users

**Usage:**
```python
from routes.decorators import district_scoped_required

@district_scoped_required
def district_report(district_name):
    # User validated for district access
```

**Implementation:**
- Global users: Always allowed
- District users: Checks `User.can_view_district(district_name)`
- Returns 403 Forbidden if access denied
- Reference: `routes/decorators.py` `district_scoped_required()`

### @school_scoped_required

**Source:** `routes/decorators.py`

**Purpose:** Validates school access (future implementation)

**Usage:**
```python
from routes.decorators import school_scoped_required

@school_scoped_required
def school_report(school_id):
    # User validated for school access
```

**Implementation:**
- Framework ready, not yet implemented
- Will check `User.can_view_school(school_id)`
- Reference: `routes/decorators.py` `school_scoped_required()`

### @security_level_required(level)

**Source:** `routes/decorators.py`

**Purpose:** Requires minimum security level

**Usage:**
```python
from routes.decorators import security_level_required
from models.user import SecurityLevel

@security_level_required(SecurityLevel.MANAGER)
def manager_only_route():
    # User must be MANAGER or ADMIN
```

**Implementation:**
- Checks `User.has_permission_level(required_level)`
- Returns 403 Forbidden if insufficient level
- Reference: `routes/decorators.py` `security_level_required()`

## Teacher Magic Link System

Self-service access for teachers to view their own progress data.

### Request Flow

1. Teacher enters email address on magic link request page
2. System validates email exists in `TeacherProgress` table
3. System generates time-limited, unguessable token
4. Email sent with magic link containing token
5. Teacher clicks link and views their progress dashboard

### Token Generation

**Binding:**
- Token bound to `TeacherProgress.email` (normalized)
- One token per teacher email
- Token includes teacher ID for dashboard routing

**Security:**
- Time-limited expiration
- Unguessable (cryptographically secure)
- Single-use or time-window validation

### Access Scope

**Teacher can view:**
- Own name and email
- Own progress status (Achieved, In Progress, Not Started)
- Past virtual sessions (completed)
- Upcoming virtual sessions (scheduled)
- Target sessions vs. completed sessions

**Teacher cannot view:**
- Other teachers' data
- District aggregates
- Student data
- Volunteer information
- Event details beyond own participation

### Issue Reporting

Teachers can flag incorrect data and submit notes to internal staff:

**Issue Categories:**
- Missing Data
- Incorrect Data

**Implementation:**
- Issue button on teacher dashboard
- Submits to admin review queue
- Links issue to teacher and specific data points

**Reference:**
- Teacher dashboard: `routes/virtual/teacher_dashboard.py`
- Requirements: [FR-DISTRICT-507](requirements#fr-district-507)
- User Stories: [US-505](user_stories#us-505)

## Implementation Examples

### Example 1: District Dashboard Access

```python
@virtual_bp.route("/usage/district/<district_name>/teacher-progress")
@login_required
@district_scoped_required
def district_teacher_progress(district_name):
    # Global users: Full access
    # District users: Validated for district_name
    # Returns 403 if district not in allowed_districts
```

### Example 2: Volunteer Search (Global Only)

```python
@volunteers_bp.route("/volunteers")
@login_required
@global_users_only
def list_volunteers():
    # Only global users can access
    # District Viewers and Teachers: 403 Forbidden
```

### Example 3: Admin-Only User Management

```python
@management_bp.route("/admin/users/create", methods=["POST"])
@login_required
@admin_required
def create_user():
    # Only admins can create users
    # Other users: 403 Forbidden
```

### Example 4: Teacher Self-View

```python
@virtual_bp.route("/kck/teacher/<int:teacher_id>")
def teacher_dashboard(teacher_id):
    # Magic link token validated
    # Shows only that teacher's data
    # Admin/User can also access (for support)
```

## Related Requirements

- [FR-DISTRICT-501](requirements#fr-district-501): District Viewer authentication
- [FR-DISTRICT-505](requirements#fr-district-505): Teacher magic link request
- [FR-DISTRICT-506](requirements#fr-district-506): Teacher magic link scoping
- [FR-DISTRICT-521](requirements#fr-district-521): Role-based access enforcement

## Related User Stories

- [US-501](user_stories#us-501): District viewer dashboard access
- [US-505](user_stories#us-505): Teacher magic link self-service

---

*Last updated: January 2026*
*Version: 1.0*
