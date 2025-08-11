---
title: "VMS Development Guide"
description: "Complete guide for setting up and developing the Volunteer Management System"
tags: [development, setup, coding-standards, testing]
---

# VMS Development Guide

## 🚀 Getting Started

### Prerequisites

Before setting up the VMS development environment, ensure you have:

- **Python 3.8+** (recommended: 3.11)
- **Git** for version control
- **SQLite** (included with Python)
- **PostgreSQL** (for production deployment)
- **Node.js** (optional, for frontend asset compilation)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/vms.git
   cd vms
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   # Flask Configuration
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here

   # Database Configuration
   DATABASE_URL=sqlite:///instance/your_database.db

   # Salesforce Integration
   SF_USERNAME=your-salesforce-username
   SF_PASSWORD=your-salesforce-password
   SF_SECURITY_TOKEN=your-salesforce-security-token
   SYNC_AUTH_TOKEN=your-sync-auth-token

   # Google Sheets Integration
   CLIENT_PROJECTS_SHEET_ID=your-google-sheet-id
   SCHOOL_MAPPING_GOOGLE_SHEET=your-school-mapping-sheet
   ENCRYPTION_KEY=your-encryption-key
   ```

5. **Initialize the database**
   ```bash
   python app.py
   ```
   This will create the SQLite database with all tables.

6. **Create admin user**
   ```bash
   python scripts/create_admin.py
   ```

7. **Run the application**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5050`

8. **Set up pre-commit (recommended)**
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   pre-commit run --all-files
   ```

9. **Run tests**
   ```bash
   python run_tests.py
   ```

## 📁 Project Structure

```
VMS/
├── app.py                          # Main application entry point
├── config.py                       # Configuration management
├── forms.py                        # Flask-WTF form definitions
├── requirements.txt                 # Python dependencies
├── pytest.ini                      # Pytest configuration
├── run_tests.py                    # Test runner script
├── PLANNING.md                     # Project planning document
├── features.md                     # Feature tracking
├── README.md                       # Project overview
├── docs/                           # Documentation
│   ├── 01-overview.md
│   ├── 02-architecture.md
│   ├── 03-data-model.md
│   ├── 04-api-spec.md
│   ├── 05-dev-guide.md
│   ├── 06-ops-guide.md
│   ├── 07-test-guide.md
│   ├── 09-faq.md
│   └── FEATURE_MATRIX.md
├── models/                         # Database models
│   ├── __init__.py
│   ├── user.py                     # User authentication
│   ├── volunteer.py                # Volunteer management
│   ├── event.py                    # Event management
│   ├── organization.py             # Organization data
│   ├── contact.py                  # Base contact model
│   ├── teacher.py                  # Teacher management
│   ├── student.py                  # Student management
│   ├── school_model.py             # School data
│   ├── district_model.py           # District data
│   ├── class_model.py              # Class management
│   ├── attendance.py               # Attendance tracking
│   ├── history.py                  # Audit trail
│   ├── bug_report.py               # Bug reporting
│   ├── google_sheet.py             # Google Sheets integration
│   ├── client_project_model.py     # Client projects
│   ├── pathways.py                 # Educational pathways
│   ├── reports.py                  # Report models
│   └── utils.py                    # Model utilities
├── routes/                         # Application routes
│   ├── __init__.py
│   ├── routes.py                   # Main route registration
│   ├── auth/                       # Authentication routes
│   │   ├── routes.py
│   │   └── api.py                  # API authentication
│   ├── volunteers/                 # Volunteer management
│   ├── organizations/              # Organization management
│   ├── events/                     # Event management
│   ├── reports/                    # Reporting system
│   ├── management/                 # Admin functions
│   ├── teachers/                   # Teacher management
│   ├── students/                   # Student management
│   ├── virtual/                    # Virtual sessions
│   ├── calendar/                   # Calendar functionality
│   ├── bug_reports/                # Bug reporting
│   ├── client_projects/            # Client projects
│   ├── pathways/                   # Educational pathways
│   ├── attendance/                 # Attendance tracking
│   └── history/                    # History tracking
├── templates/                      # HTML templates
│   ├── base.html                   # Base template
│   ├── base-nonav.html            # Base template without nav
│   ├── nav.html                    # Navigation template
│   ├── login.html                  # Login page
│   ├── index.html                  # Dashboard
│   ├── volunteers/                 # Volunteer templates
│   ├── organizations/              # Organization templates
│   ├── events/                     # Event templates
│   ├── reports/                    # Report templates
│   ├── management/                 # Admin templates
│   └── ...                        # Other template directories
├── static/                         # Static assets
│   ├── css/                        # Stylesheets
│   │   ├── style.css               # Main styles
│   │   ├── admin.css               # Admin styles
│   │   ├── events.css              # Event styles
│   │   └── ...                     # Other CSS files
│   └── js/                         # JavaScript files
│       ├── nav.js                  # Navigation logic
│       ├── volunteers.js           # Volunteer functionality
│       ├── events.js               # Event functionality
│       └── ...                     # Other JS files
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Test configuration
│   ├── unit/                       # Unit tests
│   │   ├── models/                 # Model tests
│   │   │   ├── test_user.py
│   │   │   ├── test_volunteer.py
│   │   │   └── ...
│   │   └── ...
│   └── integration/                # Integration tests
│       ├── test_api_endpoints.py
│       ├── test_volunteer_routes.py
│       └── ...
├── scripts/                        # Utility scripts
│   ├── create_admin.py             # Create admin user
│   ├── copy_students.py            # Data migration
│   ├── copy_users.py               # User migration
│   ├── mark_excluded_volunteers.py # Data cleanup
│   ├── setup_encryption_key.py     # Security setup
│   ├── sync_script.py              # Data synchronization
│   └── test_google_sheets.py       # Google Sheets testing
├── utils/                          # Utility modules
│   ├── __init__.py
│   └── academic_year.py            # Academic year utilities
├── instance/                       # Instance-specific files
│   └── your_database.db           # SQLite database
└── documentation/                  # User documentation
    ├── index.html                  # Documentation index
    ├── README.md                   # User guide
    ├── css/                        # Documentation styles
    └── img/                        # Documentation images
```

## 🛠️ Technology Stack

### Backend
- **Flask 2.3+**: Web framework
- **SQLAlchemy 2.0+**: ORM and database management
- **Flask-SQLAlchemy**: Flask integration with SQLAlchemy
- **Flask-Login**: User session management
- **Flask-WTF**: Form handling and CSRF protection
- **Flask-CORS**: Cross-origin resource sharing
- **Werkzeug**: WSGI utilities
- **Jinja2**: Template engine

### Database
- **SQLite**: Development database
- **PostgreSQL**: Production database
- **psycopg2-binary**: PostgreSQL adapter

### Authentication & Security
- **Flask-Login**: Session management
- **Werkzeug**: Password hashing
- **cryptography**: Encryption for sensitive data

### Data Processing
- **pandas 2.0+**: Data manipulation and analysis
- **openpyxl**: Excel file handling
- **xlsxwriter**: Excel report generation

### External Integrations
- **simple-salesforce**: Salesforce API integration
- **google-sheets-api**: Google Sheets integration (via custom implementation)

### Development Tools
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **python-dotenv**: Environment variable management

### Production
- **gunicorn**: WSGI server
- **nginx**: Web server (production)
- **systemd**: Service management (production)

## 📝 Coding Standards

### Python Code Style

Follow **PEP 8** standards with these specific guidelines:

#### Naming Conventions
```python
# Variables and functions: snake_case
user_name = "john_doe"
def get_user_by_id(user_id):
    pass

# Classes: PascalCase
class UserManager:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_PAGE_SIZE = 20

# Database models: PascalCase
class Volunteer(db.Model):
    pass

# Blueprint names: snake_case
volunteers_bp = Blueprint('volunteers', __name__)
```

#### Import Organization
```python
# Standard library imports
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

# Third-party imports
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String

# Local application imports
from models import db, User
from routes.auth.routes import auth_bp
from utils.academic_year import get_current_academic_year
```

#### Documentation
```python
def calculate_volunteer_hours(volunteer_id: int, start_date: datetime,
                             end_date: datetime) -> float:
    """
    Calculate total volunteer hours for a specific period.

    Args:
        volunteer_id: The volunteer's unique identifier
        start_date: Start of the calculation period
        end_date: End of the calculation period

    Returns:
        Total volunteer hours as a float

    Raises:
        ValueError: If start_date is after end_date
        NotFoundError: If volunteer doesn't exist

    Example:
        >>> hours = calculate_volunteer_hours(1,
        ...     datetime(2024, 1, 1), datetime(2024, 12, 31))
        >>> print(f"Total hours: {hours}")
    """
    if start_date > end_date:
        raise ValueError("Start date must be before end date")

    # Implementation here
    return total_hours
```

### Database Models

#### Model Structure
```python
class Volunteer(Contact):
    """
    Volunteer model inheriting from Contact base class.

    Represents volunteers in the system with specialized fields
    for volunteer management and activity tracking.
    """
    __tablename__ = 'volunteer'

    # Primary key (inherited from Contact)
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)

    # Volunteer-specific fields
    organization_name = db.Column(String(100))
    title = db.Column(String(50))
    local_status = db.Column(Enum(LocalStatusEnum),
                            default=LocalStatusEnum.unknown, index=True)

    # Relationships
    engagements = relationship('Engagement', backref='volunteer',
                             lazy='dynamic', cascade="all, delete-orphan")

    # SQLAlchemy inheritance configuration
    __mapper_args__ = {
        'polymorphic_identity': 'volunteer',
        'confirm_deleted_rows': False,
        'inherit_condition': id == Contact.id
    }

    def __repr__(self):
        return f"<Volunteer {self.full_name}>"
```

#### Validation Methods
```python
@validates('first_volunteer_date', 'last_volunteer_date')
def validate_dates(self, key, value):
    """Validate volunteer activity dates."""
    if value and key == 'last_volunteer_date':
        if self.first_volunteer_date and value < self.first_volunteer_date:
            raise ValueError("Last volunteer date cannot be before first volunteer date")
    return value
```

### Route Organization

#### Blueprint Structure
```python
# routes/volunteers/routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Volunteer, Contact
from forms import VolunteerForm

volunteers_bp = Blueprint('volunteers', __name__)

@volunteers_bp.route('/volunteers')
@login_required
def list_volunteers():
    """Display list of all volunteers."""
    page = request.args.get('page', 1, type=int)
    volunteers = Volunteer.query.paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('volunteers/volunteers.html', volunteers=volunteers)

@volunteers_bp.route('/volunteers/add', methods=['GET', 'POST'])
@login_required
def add_volunteer():
    """Add a new volunteer."""
    form = VolunteerForm()
    if form.validate_on_submit():
        volunteer = Volunteer()
        form.populate_obj(volunteer)
        db.session.add(volunteer)
        db.session.commit()
        flash('Volunteer added successfully!', 'success')
        return redirect(url_for('volunteers.list_volunteers'))

    return render_template('volunteers/add_volunteer.html', form=form)
```

### Template Structure

#### Base Template
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}VMS{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include 'nav.html' %}

    <main class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <script src="{{ url_for('static', filename='js/nav.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

#### Form Templates
```html
<!-- templates/volunteers/add_volunteer.html -->
{% extends "base.html" %}

{% block title %}Add Volunteer - VMS{% endblock %}

{% block content %}
<div class="form-container">
    <h1>Add New Volunteer</h1>

    <form method="POST" class="volunteer-form">
        {{ form.hidden_tag() }}

        <div class="form-group">
            {{ form.first_name.label }}
            {{ form.first_name(class="form-control") }}
            {% if form.first_name.errors %}
                <div class="error-message">
                    {% for error in form.first_name.errors %}
                        <span>{{ error }}</span>
                    {% endfor %}
                </div>
            {% endif %}
        </div>

        <!-- Additional form fields -->

        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Add Volunteer</button>
            <a href="{{ url_for('volunteers.list_volunteers') }}"
               class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>
{% endblock %}
```

## 🧪 Testing

### Running Tests

#### Run All Tests
```bash
# Run all tests
python run_tests.py

# Or using pytest directly
pytest

# With coverage
pytest --cov=.

# With verbose output
pytest -v
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/models/test_volunteer.py

# Specific test function
pytest tests/unit/models/test_volunteer.py::test_volunteer_creation
```

#### Test Configuration
The project uses `pytest.ini` for configuration:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    api: API tests
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/models/test_volunteer.py
import pytest
from datetime import date
from models.volunteer import Volunteer, VolunteerStatus
from models.contact import Contact, GenderEnum

class TestVolunteer:
    """Test cases for Volunteer model."""

    def test_volunteer_creation(self, app):
        """Test creating a new volunteer."""
        with app.app_context():
            # Create contact first (since Volunteer inherits from Contact)
            contact = Contact(
                first_name="John",
                last_name="Doe",
                gender=GenderEnum.male
            )
            db.session.add(contact)
            db.session.flush()

            volunteer = Volunteer(
                id=contact.id,
                organization_name="Tech Corp",
                title="Software Engineer",
                status=VolunteerStatus.ACTIVE
            )
            db.session.add(volunteer)
            db.session.commit()

            assert volunteer.id is not None
            assert volunteer.full_name == "John Doe"
            assert volunteer.status == VolunteerStatus.ACTIVE

    def test_volunteer_local_status_calculation(self, app):
        """Test local status calculation based on address."""
        with app.app_context():
            contact = Contact(
                first_name="Jane",
                last_name="Smith",
                gender=GenderEnum.female
            )
            db.session.add(contact)
            db.session.flush()

            volunteer = Volunteer(id=contact.id)
            db.session.add(volunteer)
            db.session.commit()

            # Test local status calculation
            volunteer.calculate_local_status()
            assert volunteer.local_status in ['local', 'partial', 'non_local', 'unknown']

    def test_volunteer_date_validation(self, app):
        """Test volunteer date validation."""
        with app.app_context():
            contact = Contact(first_name="Test", last_name="User")
            db.session.add(contact)
            db.session.flush()

            volunteer = Volunteer(id=contact.id)
            db.session.add(volunteer)

            # Test invalid date combination
            volunteer.first_volunteer_date = date(2024, 12, 31)
            volunteer.last_volunteer_date = date(2024, 1, 1)

            with pytest.raises(ValueError):
                db.session.commit()
```

#### Integration Test Example
```python
# tests/integration/test_volunteer_routes.py
import pytest
from flask import url_for

class TestVolunteerRoutes:
    """Integration tests for volunteer routes."""

    def test_list_volunteers_page(self, client, auth_headers):
        """Test volunteer list page loads correctly."""
        response = client.get('/volunteers', headers=auth_headers)
        assert response.status_code == 200
        assert b'Volunteers' in response.data

    def test_add_volunteer_form(self, client, auth_headers):
        """Test volunteer add form loads correctly."""
        response = client.get('/volunteers/add', headers=auth_headers)
        assert response.status_code == 200
        assert b'Add Volunteer' in response.data

    def test_create_volunteer(self, client, auth_headers):
        """Test creating a new volunteer."""
        data = {
            'first_name': 'Test',
            'last_name': 'Volunteer',
            'email': 'test@example.com',
            'organization_name': 'Test Org',
            'status': 'active'
        }

        response = client.post('/volunteers/add',
                             data=data, headers=auth_headers)

        # Should redirect to volunteer list
        assert response.status_code in [200, 302]

        # Check volunteer was created
        from models import Volunteer
        volunteer = Volunteer.query.filter_by(
            first_name='Test', last_name='Volunteer'
        ).first()
        assert volunteer is not None
```

#### API Test Example
```python
# tests/integration/test_api_endpoints.py
import pytest
import json

class TestAPIEndpoints:
    """Integration tests for API endpoints."""

    def test_token_generation(self, client):
        """Test API token generation."""
        data = {
            'username': 'test@example.com',
            'password': 'password123'
        }

        response = client.post('/api/v1/token',
                             data=json.dumps(data),
                             content_type='application/json')

        assert response.status_code == 200
        result = json.loads(response.data)
        assert 'token' in result
        assert 'expires_at' in result

    def test_user_sync_with_token(self, client, test_user):
        """Test user synchronization with valid token."""
        # First get a token
        token_response = client.post('/api/v1/token',
                                   data=json.dumps({
                                       'username': test_user.username,
                                       'password': 'password123'
                                   }),
                                   content_type='application/json')

        token_data = json.loads(token_response.data)
        token = token_data['token']

        # Use token to sync users
        headers = {'X-API-Token': token}
        response = client.get('/api/v1/users/sync', headers=headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert 'users' in result
        assert 'total_count' in result
```

### Test Fixtures

The project includes comprehensive test fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = Flask(__name__)
    app.config.from_object(TestingConfig)

    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def test_user(app):
    """Create a test user."""
    user = User(
        username='test@example.com',
        email='test@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='Test',
        last_name='User',
        security_level=SecurityLevel.USER
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def test_volunteer(app):
    """Create a test volunteer."""
    contact = Contact(
        first_name='John',
        last_name='Doe',
        gender=GenderEnum.male
    )
    db.session.add(contact)
    db.session.flush()

    volunteer = Volunteer(
        id=contact.id,
        organization_name='Test Corp',
        status=VolunteerStatus.ACTIVE
    )
    db.session.add(volunteer)
    db.session.commit()
    return volunteer
```

## 🔄 Development Workflow

### Git Workflow

#### Branch Naming
- `feature/volunteer-search`: New features
- `bugfix/login-error`: Bug fixes
- `hotfix/security-patch`: Critical fixes
- `refactor/database-models`: Code refactoring

#### Commit Messages
Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(volunteers): add advanced search functionality

- Add search by skills, organization, and date range
- Implement pagination for search results
- Add export to CSV option

Closes #123
```

```
fix(auth): resolve login redirect issue

The login redirect was not working properly when users
accessed protected pages directly. This fix ensures
proper redirection after successful authentication.

Fixes #456
```

#### Pull Request Process
1. Create feature branch from `main`
2. Make changes with clear commit messages
3. Write/update tests for new functionality
4. Update documentation if needed
5. Create pull request with description
6. Request code review
7. Address feedback and merge

### Code Review Checklist

- [ ] Code follows PEP 8 standards
- [ ] All tests pass
- [ ] New functionality has tests
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] Database queries are optimized

### Pre-commit Hooks

Set up pre-commit hooks for code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
        args: [--line-length=88]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, ., -f, json, -o, bandit-report.json]
```

## 🐛 Debugging

### Flask Debug Mode

Enable debug mode for development:
```python
# In app.py
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5050)
```

### Database Debugging

```python
# Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or in Flask app
app.config['SQLALCHEMY_ECHO'] = True
```

### Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
if not app.debug:
    file_handler = RotatingFileHandler('logs/vms.log',
                                     maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('VMS startup')
```

### Common Debugging Techniques

#### Database Queries
```python
# Debug complex queries
from sqlalchemy import text
query = db.session.query(Volunteer).filter(Volunteer.status == 'active')
print(query.statement.compile(compile_kwargs={"literal_binds": True}))

# Profile query performance
import time
start = time.time()
result = query.all()
print(f"Query took {time.time() - start:.2f} seconds")
```

#### Template Debugging
```html
<!-- Add debug information to templates -->
{% if config.DEBUG %}
<div class="debug-info">
    <p>Template: {{ self._TemplateReference__context.name }}</p>
    <p>Variables: {{ request.view_args }}</p>
</div>
{% endif %}
```

## ⚡ Performance Optimization

### Database Optimization

#### Indexing Strategy
```python
# Add indexes for frequently queried fields
class Volunteer(Contact):
    __table_args__ = (
        db.Index('idx_volunteer_status', 'status'),
        db.Index('idx_volunteer_local_status', 'local_status'),
        db.Index('idx_volunteer_last_activity', 'last_activity_date'),
    )
```

#### Query Optimization
```python
# Use select_from for complex joins
volunteers = db.session.query(Volunteer)\
    .select_from(Volunteer)\
    .join(Contact)\
    .filter(Volunteer.status == 'active')\
    .options(joinedload(Volunteer.organizations))\
    .all()

# Use lazy loading appropriately
volunteers = Volunteer.query.options(
    db.joinedload(Volunteer.organizations),
    db.joinedload(Volunteer.skills)
).all()
```

### Caching Strategy

```python
from functools import lru_cache
from datetime import timedelta

@lru_cache(maxsize=128)
def get_volunteer_count():
    """Cache volunteer count for 5 minutes."""
    return Volunteer.query.count()

# Flask-Caching for more complex caching
from flask_caching import Cache

cache = Cache()

@cache.memoize(timeout=300)
def get_active_volunteers():
    """Cache active volunteers for 5 minutes."""
    return Volunteer.query.filter_by(status='active').all()
```

### Memory Management

```python
# Use generators for large datasets
def get_volunteer_chunks(chunk_size=1000):
    """Yield volunteers in chunks to manage memory."""
    offset = 0
    while True:
        volunteers = Volunteer.query.offset(offset).limit(chunk_size).all()
        if not volunteers:
            break
        yield volunteers
        offset += chunk_size

# Process large datasets efficiently
for chunk in get_volunteer_chunks():
    for volunteer in chunk:
        # Process volunteer
        pass
```

## 🔒 Security Best Practices

### Input Validation

```python
from werkzeug.security import safe_str_cmp
import re

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text):
    """Sanitize user input."""
    if not text:
        return ""
    # Remove potentially dangerous characters
    return text.strip()[:1000]  # Limit length
```

### SQL Injection Prevention

```python
# Always use parameterized queries
# Good
volunteers = Volunteer.query.filter_by(status=status).all()

# Bad - vulnerable to SQL injection
volunteers = Volunteer.query.filter(
    text(f"status = '{status}'")
).all()
```

### XSS Prevention

```python
# In templates, always escape user input
{{ volunteer.name|escape }}

# Or use the |safe filter only for trusted content
{{ trusted_html_content|safe }}
```

### CSRF Protection

```python
# Flask-WTF provides CSRF protection
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In forms
<form method="POST">
    {{ form.hidden_tag() }}  <!-- CSRF token -->
    <!-- form fields -->
</form>
```

## 📚 Related Documentation

- [System Overview](01-overview.md)
- [Architecture](02-architecture.md)
- [Data Model](03-data-model.md)
- [API Specification](04-api-spec.md)
- [Operations Guide](06-ops-guide.md)
- [Test Guide](07-test-guide.md)

---

*Last updated: January 2025*
