---
title: "VMS Testing Guide"
status: active
doc_type: guide
project: "global"
owner: "@jlane"
updated: 2025-01-27
tags: ["testing", "test-strategy", "test-setup", "vms"]
summary: "Complete testing guide for VMS development including test setup, patterns, data management, and CI/CD workflow. Essential reference for maintaining code quality."
canonical: "/docs/living/Testing.md"
---

# VMS Testing Guide

## 🎯 **Testing Strategy Overview**

The VMS testing strategy follows the **test pyramid approach** to ensure comprehensive coverage while maintaining fast feedback loops.

### **Test Pyramid**
```
    /\
   /  \     E2E Tests (Few)
  /____\
 /      \   Integration Tests (Some)
/________\  Unit Tests (Many)
```

### **Test Categories**
- **Unit Tests**: Individual functions and methods in isolation
- **Integration Tests**: Component interactions and database operations
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: System performance under load
- **Security Tests**: Security vulnerability assessment

## 🚀 **Test Environment Setup**

### **Prerequisites**
- **Python 3.9+** (development environment)
- **Pytest** testing framework
- **SQLite** test database
- **Virtual environment** activated

### **Quick Setup**
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Set up test database
export FLASK_ENV=testing
flask db upgrade --directory tests/migrations

# Verify setup
python -m pytest --version
```

### **Test Configuration**
```python
# tests/conftest.py - Key configuration
import pytest
from app import create_app
from models import db as _db

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture(scope='function')
def db(app):
    """Create database for testing."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()
```

## 🧪 **Running Tests**

### **Basic Test Commands**
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest tests/unit/test_models.py

# Run with verbose output
python -m pytest -v

# Run with print statements
python -m pytest -s

# Run tests in parallel
python -m pytest -n auto
```

### **Test Selection**
```bash
# Run specific test function
python -m pytest tests/unit/test_models.py::test_volunteer_creation

# Run tests by marker
python -m pytest -m "slow"
python -m pytest -m "integration"

# Run tests by pattern
python -m pytest -k "volunteer"
python -m pytest -k "not slow"
```

### **Coverage Analysis**
```bash
# Generate coverage report
python -m pytest --cov=. --cov-report=html

# Check coverage threshold
python -m pytest --cov=. --cov-fail-under=80

# Generate coverage badge
python -m pytest --cov=. --cov-report=term-missing
```

## 🏗️ **Test Structure & Organization**

### **Directory Structure**
```
tests/
├── conftest.py              # Test configuration and fixtures
├── unit/                    # Unit tests
│   ├── models/             # Model tests
│   ├── routes/             # Route tests
│   └── utils/              # Utility function tests
├── integration/             # Integration tests
│   ├── api/                # API endpoint tests
│   └── database/           # Database operation tests
├── fixtures/                # Test data fixtures
└── helpers/                 # Test helper functions
```

### **Test File Naming**
- **Unit tests**: `test_<module_name>.py`
- **Integration tests**: `test_<feature>_integration.py`
- **Model tests**: `test_<model_name>.py`
- **Route tests**: `test_<route_name>.py`

## 📝 **Writing Tests**

### **Unit Test Example**
```python
# tests/unit/models/test_volunteer.py
import pytest
from models.volunteer import Volunteer
from models import db

def test_volunteer_creation(db):
    """Test volunteer model creation with valid data."""
    volunteer = Volunteer(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1-555-0123",
        status="active"
    )
    
    db.session.add(volunteer)
    db.session.commit()
    
    assert volunteer.id is not None
    assert volunteer.first_name == "John"
    assert volunteer.email == "john.doe@example.com"
    assert volunteer.status == "active"

def test_volunteer_email_validation(db):
    """Test volunteer email validation."""
    with pytest.raises(ValueError):
        volunteer = Volunteer(
            first_name="John",
            last_name="Doe",
            email="invalid-email",
            status="active"
        )
```

### **Integration Test Example**
```python
# tests/integration/test_volunteer_api.py
import pytest
from flask import url_for

def test_create_volunteer_api(client, auth_headers):
    """Test volunteer creation via API."""
    data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "+1-555-0456",
        "status": "active"
    }
    
    response = client.post(
        url_for('volunteers.create_volunteer'),
        json=data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    assert response.json['first_name'] == "Jane"
    assert response.json['email'] == "jane.smith@example.com"
```

### **Route Test Example**
```python
# tests/unit/routes/test_volunteer_routes.py
def test_volunteer_list_route(client, auth_headers):
    """Test volunteer list route."""
    response = client.get(
        url_for('volunteers.list_volunteers'),
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert 'volunteers' in response.json
    assert isinstance(response.json['volunteers'], list)
```

## 🔧 **Test Fixtures & Data Management**

### **Common Fixtures**
```python
# tests/conftest.py
@pytest.fixture
def auth_user(db):
    """Create authenticated user for testing."""
    user = User(
        username='testuser',
        email='test@example.com',
        password_hash=generate_password_hash('password123'),
        role='admin'
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_volunteer(db):
    """Create sample volunteer for testing."""
    volunteer = Volunteer(
        first_name='John',
        last_name='Doe',
        email='john.doe@example.com',
        phone='+1-555-0123',
        status='active'
    )
    db.session.add(volunteer)
    db.session.commit()
    return volunteer

@pytest.fixture
def sample_organization(db):
    """Create sample organization for testing."""
    org = Organization(
        name='Test Organization',
        contact_email='contact@testorg.com',
        status='active'
    )
    db.session.add(org)
    db.session.commit()
    return org
```

### **Test Data Factories**
```python
# tests/fixtures/factories.py
import factory
from models.volunteer import Volunteer
from models.organization import Organization

class VolunteerFactory(factory.SQLAlchemyModelFactory):
    class Meta:
        model = Volunteer
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(
        lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@example.com"
    )
    phone = factory.Faker('phone_number')
    status = 'active'

class OrganizationFactory(factory.SQLAlchemyModelFactory):
    class Meta:
        model = Organization
    
    name = factory.Faker('company')
    contact_email = factory.Faker('company_email')
    status = 'active'
```

## 🚨 **Testing Best Practices**

### **Test Design Principles**
1. **Arrange-Act-Assert**: Clear test structure
2. **One assertion per test**: Focused test cases
3. **Descriptive names**: Clear test purpose
4. **Independent tests**: No test dependencies
5. **Fast execution**: Quick feedback loops

### **Test Data Management**
- **Use factories** for complex test data
- **Clean up** after each test
- **Use transactions** for database tests
- **Mock external services** when possible
- **Use realistic data** for edge cases

### **Performance Testing**
```python
# tests/performance/test_database_performance.py
import pytest
import time

def test_volunteer_query_performance(db, many_volunteers):
    """Test volunteer query performance with large dataset."""
    start_time = time.time()
    
    volunteers = Volunteer.query.filter_by(status='active').all()
    
    end_time = time.time()
    query_time = end_time - start_time
    
    assert query_time < 0.1  # Should complete in under 100ms
    assert len(volunteers) > 0
```

## 🔍 **Debugging Tests**

### **Common Test Issues**
```bash
# Database connection issues
export FLASK_ENV=testing
flask db upgrade --directory tests/migrations

# Import errors
python -c "import sys; print(sys.path)"
which python

# Test discovery issues
python -m pytest --collect-only
```

### **Debugging Commands**
```bash
# Run single test with debugger
python -m pytest tests/unit/test_models.py::test_volunteer_creation -s

# Show test output
python -m pytest -v -s

# Stop on first failure
python -m pytest -x

# Run with maximum verbosity
python -m pytest -vvv
```

## 📊 **Test Metrics & Quality**

### **Coverage Targets**
- **Overall Coverage**: 80% minimum
- **Critical Paths**: 95% minimum
- **New Features**: 90% minimum
- **Bug Fixes**: 100% for affected code

### **Quality Metrics**
- **Test Execution Time**: < 30 seconds for full suite
- **Test Reliability**: 99% pass rate
- **Test Maintenance**: < 10% test code changes per feature
- **Test Documentation**: 100% test method documentation

## 🔄 **CI/CD Integration**

### **GitHub Actions Example**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          python -m pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### **Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest
        language: system
        pass_filenames: false
        always_run: true
```

## 🛠️ **Test Utilities**

### **Custom Assertions**
```python
# tests/helpers/assertions.py
def assert_valid_volunteer_data(data):
    """Assert volunteer data has required fields."""
    required_fields = ['first_name', 'last_name', 'email', 'status']
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    
    assert data['email'].count('@') == 1, "Invalid email format"
    assert data['status'] in ['active', 'inactive', 'pending'], "Invalid status"

def assert_database_consistency(db):
    """Assert database constraints are maintained."""
    # Check for orphaned records
    orphaned_volunteers = db.session.query(Volunteer).filter(
        ~Volunteer.organization_id.in_(
            db.session.query(Organization.id)
        )
    ).all()
    
    assert len(orphaned_volunteers) == 0, "Found orphaned volunteers"
```

### **Test Helpers**
```python
# tests/helpers/test_helpers.py
def create_test_app(config=None):
    """Create test application with custom configuration."""
    app = create_app('testing')
    if config:
        app.config.update(config)
    return app

def create_test_client(app):
    """Create authenticated test client."""
    client = app.test_client()
    with app.app_context():
        user = create_test_user()
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {user.token}'
    return client
```

## 🔗 **Related Documents**

- **Development Setup**: `/docs/living/Onboarding.md`
- **CLI Commands**: `/docs/living/Commands.md`
- **Code Quality**: `/docs/Philosophy.md`
- **Test Configuration**: `tests/conftest.py`

## 📝 **Ask me (examples)**

- "How do I set up the test environment for a new developer?"
- "What's the best way to test database operations?"
- "How do I debug a failing test?"
- "What are the coverage targets for new features?"
- "How do I integrate testing into the CI/CD pipeline?"
