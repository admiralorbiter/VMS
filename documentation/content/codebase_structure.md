# Codebase Structure

**A developer's guide to the Polaris VMS project layout**

This document describes the directory structure and organization of the Polaris codebase. Use this as a reference when navigating the project, especially when working with AI assistants or onboarding new team members.

## Root Directory Overview

```
VMS/
├── app.py                 # Flask application factory and entry point
├── forms.py               # WTForms definitions for web forms
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies (pytest, etc.)
├── pytest.ini             # Pytest configuration
├── alembic.ini            # Database migration configuration
├── alembic/               # Database migrations (Alembic)
├── config/                # Application configuration
├── models/                # SQLAlchemy database models
├── routes/                # Flask blueprints and route handlers
├── templates/             # Jinja2 HTML templates
├── static/                # CSS, JavaScript, images
├── utils/                 # Utility modules (clients, validators)
├── scripts/               # CLI tools and automation scripts
├── tests/                 # Test suite (unit, integration, smoke)
├── documentation/         # Project documentation (SPA-based)
├── docs/                  # Generated/static docs output
├── data/                  # Data files (spreadsheets, exports)
├── logs/                  # Application logs
└── instance/              # Instance-specific files (SQLite DB)
```

---

## Core Application

### `app.py`
The Flask application factory. Creates and configures the app, registers blueprints, sets up database, authentication, and error handlers.

**Key patterns:**
- Uses `create_app()` factory pattern
- Registers all blueprints from `routes/`
- Configures Flask-Login, Flask-Migrate, Flask-Mail
- Sets up Jinja2 template filters

### `forms.py`
WTForms form classes for HTML form handling and validation.

---

## Models (`models/`)

SQLAlchemy ORM models representing database entities. Each file typically contains one primary model class with relationships and helper methods.

| File | Purpose | Key Models |
|------|---------|------------|
| `__init__.py` | Exports all models, initializes `db` object | `db` (SQLAlchemy instance) |
| `event.py` | Events/sessions | `Event`, `EventType`, `EventStatus`, `EventTeacher` |
| `volunteer.py` | Volunteer profiles | `Volunteer`, `VolunteerOrganization`, `EventParticipation` |
| `contact.py` | Base contact entity (polymorphic) | `Contact`, `Email`, `Phone`, `ContactTypeEnum` |
| `teacher.py` | Teacher profiles (extends Contact) | `Teacher` |
| `student.py` | Student records | `Student`, `StudentParticipation` |
| `organization.py` | Companies/organizations | `Organization` |
| `school_model.py` | Schools and buildings | `School` |
| `district_model.py` | Districts | `District` |
| `teacher_progress.py` | Teacher KCKPS tracking | `TeacherProgress` |
| `teacher_progress_archive.py` | Archived semester snapshots | `TeacherProgressArchive` |
| `user.py` | User authentication | `User`, `Permission`, roles |
| `history.py` | Communication history | `CommunicationHistory` |
| `reports.py` | Report configurations | `SavedReport`, `ReportFilter` |
| `sync_log.py` | Import/sync logging | `SyncLog` |
| `google_sheet.py` | Google Sheets config | `GoogleSheetConfig` |
| `attendance.py` | Attendance tracking | `EventAttendanceDetail` |
| `class_model.py` | Classes (academic) | `Class` |
| `bug_report.py` | Issue tracking | `BugReport` |
| `audit_log.py` | Audit trail | `AuditLog` |

**Polymorphic Inheritance:**
`Contact` is the base class. `Teacher`, `Volunteer`, and other contact types inherit from it using SQLAlchemy's polymorphic mapping.

---

## Routes (`routes/`)

Flask blueprints organized by feature domain. Each subdirectory contains a `routes.py` (or similar) with route handlers and an `__init__.py` for blueprint registration.

| Directory | Blueprint | Purpose |
|-----------|-----------|---------|
| `auth/` | `auth_bp` | Login, logout, password reset |
| `events/` | `events_bp` | In-person event management, Salesforce sync |
| `virtual/` | `virtual_bp` | Virtual sessions, district dashboards, teacher progress |
| `volunteers/` | `volunteers_bp` | Volunteer profiles, search, recruitment |
| `organizations/` | `organizations_bp` | Organization management |
| `students/` | `students_bp` | Student records, participation |
| `teachers/` | `teachers_bp` | Teacher records |
| `history/` | `history_bp` | Communication history |
| `reports/` | `reports_bp` | Reporting and analytics |
| `attendance/` | `attendance_bp` | Attendance tracking |
| `calendar/` | `calendar_bp` | Event calendar views |
| `management/` | `management_bp` | Admin settings, imports |
| `email/` | `email_bp` | Email templates and sending |
| `bug_reports/` | `bug_reports_bp` | Issue reporting |
| `client_projects/` | `client_projects_bp` | Client-connected projects |
| `quality/` | `quality_bp` | Data quality dashboards |

### Key Files in `routes/`

| File | Purpose |
|------|---------|
| `routes.py` | Root-level routes (home, dashboard) |
| `decorators.py` | Custom route decorators (`@admin_required`, `@login_required`) |
| `utils.py` | Shared route utilities (pagination, date parsing) |

### Virtual Routes (`routes/virtual/`)

The largest route module, handling:
- `routes.py` - Session management, Google Sheets import
- `usage.py` - District dashboards, teacher progress tracking, semester reset

---

## Templates (`templates/`)

Jinja2 HTML templates organized to mirror the route structure.

| Directory | Purpose |
|-----------|---------|
| `base.html` | Base layout with navigation |
| `base-nonav.html` | Base layout without navigation (login, etc.) |
| `nav.html` | Navigation component |
| `index.html` | Home/dashboard page |
| `login.html` | Login page |
| `virtual/` | Virtual session templates |
| `reports/` | Report templates |
| `volunteers/` | Volunteer management templates |
| `events/` | Event management templates |
| `management/` | Admin templates |
| `email/` | Email templates (HTML for sending) |

**Template Conventions:**
- Use `{% extends "base.html" %}` for full-page templates
- Partials prefixed with `_` (e.g., `_district_issue_fab.html`)
- CSS blocks: `{% block extra_css %}`, JS blocks: `{% block extra_js %}`

---

## Static Files (`static/`)

| Directory | Purpose |
|-----------|---------|
| `css/` | Stylesheets (reports.css, virtual_usage.css, etc.) |
| `js/` | JavaScript (nav.js, chart.js, etc.) |
| `images/` | Static images and icons |

---

## Utilities (`utils/`)

Shared utility modules used across the application.

| File/Directory | Purpose |
|----------------|---------|
| `salesforce_client.py` | Salesforce API client (simple-salesforce wrapper) |
| `email.py` | Email sending utilities (Mailjet integration) |
| `academic_year.py` | Academic/virtual year date calculations |
| `cache_refresh_scheduler.py` | Background cache refresh scheduling |
| `roster_import.py` | Teacher roster import logic |
| `validation_base.py` | Base validation framework |
| `validation_engine.py` | Data validation engine |
| `validators/` | Field-level validators (email, phone, etc.) |
| `services/` | Service layer classes |

---

## Scripts (`scripts/`)

CLI tools, automation scripts, and maintenance utilities.

| Directory | Purpose |
|-----------|---------|
| `daily_imports/` | Daily Salesforce import scripts |
| `admin/` | Admin utilities (create users, reset passwords) |
| `maintenance/` | Database maintenance and cleanup |
| `validation/` | Data validation scripts |
| `utilities/` | General-purpose utilities |
| `cli/` | CLI command definitions |
| `automation/` | Automated task scripts |
| `sql/` | Raw SQL scripts |

### Key Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `daily_imports/daily_imports.py` | Main daily import orchestrator | `python -m scripts.daily_imports.daily_imports --daily` |
| `monitor_api.py` | API health monitoring | `python scripts/monitor_api.py` |
| `archive_fall_2025.py` | Manual semester archive | `python scripts/archive_fall_2025.py` |

---

## Tests (`tests/`)

Pytest test suite organized by test type.

| Directory | Purpose |
|-----------|---------|
| `conftest.py` | Shared fixtures (client, test_admin, etc.) |
| `unit/` | Unit tests for models and utilities |
| `integration/` | Integration tests for routes and workflows |
| `smoke/` | Smoke tests for critical paths |
| `manual/` | Manual test scripts |

**Test Conventions:**
- Files prefixed with `test_` (e.g., `test_volunteer_routes.py`)
- Use fixtures from `conftest.py` for database and client setup
- Integration tests go in `integration/routes/<feature>/`

---

## Configuration (`config/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Configuration classes (DevelopmentConfig, ProductionConfig) |
| `validation.py` | Validation rules and patterns |
| `quality_scoring.py` | Data quality scoring logic |

---

## Database Migrations (`alembic/`)

Alembic migration files for database schema changes.

| Directory | Purpose |
|-----------|---------|
| `versions/` | Migration version files |
| `env.py` | Alembic environment configuration |

**Migration Commands:**
```bash
# Create new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

---

## Documentation (`documentation/`)

SPA-based documentation system using Markdown files.

| Directory | Purpose |
|-----------|---------|
| `content/` | Markdown documentation files |
| `content/images/` | Documentation images |
| `content/test_packs/` | Test case documentation |
| `content/user_guide/` | User guide articles |
| `content/reports/` | Report documentation |

**Key Documentation Files:**
- `architecture.md` - System architecture
- `requirements.md` - Functional requirements
- `data_dictionary.md` - Entity definitions
- `field_mappings.md` - Field mapping specs
- `metrics_bible.md` - Metric calculations

---

## Common Patterns

### Blueprint Registration
```python
# In routes/<feature>/routes.py
from flask import Blueprint
feature_bp = Blueprint('feature', __name__, url_prefix='/feature')

# In app.py
from routes.feature.routes import feature_bp
app.register_blueprint(feature_bp)
```

### Model Relationships
```python
# One-to-Many
volunteers = db.relationship('Volunteer', backref='organization')

# Many-to-Many
events = db.relationship('Event', secondary=event_volunteers, backref='volunteers')
```

### Route Decorators
```python
@feature_bp.route('/admin-only')
@login_required
@admin_required
def admin_page():
    pass
```

---

## File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Models | `<entity>.py` or `<entity>_model.py` | `volunteer.py`, `school_model.py` |
| Routes | `routes.py` in feature directory | `routes/events/routes.py` |
| Templates | `<feature>_<action>.html` | `volunteer_detail.html` |
| Tests | `test_<feature>_<type>.py` | `test_volunteer_routes.py` |
| Partials | `_<name>.html` | `_district_issue_fab.html` |

---

*Last updated: January 2026*
