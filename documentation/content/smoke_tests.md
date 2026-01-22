# Smoke Tests

**Basic functionality verification**

## Purpose

Smoke tests are quick, high-level tests that verify basic system functionality is working. They are designed to catch major issues early and provide fast feedback.

**When to run smoke tests:**
- **Pre-deployment**: Before deploying code changes
- **Post-deployment**: Immediately after deployment to verify system is operational
- **After code changes**: When modifying critical functionality
- **Regular health checks**: As part of routine system verification

**Reference:**
- [Testing Guide](docs/living/Testing.md) - Complete testing setup and strategy
- [Runbook](runbook) - Troubleshooting procedures
- [Monitoring and Alert](monitoring) - System health monitoring

## Existing Smoke Tests

### District Scoping Smoke Test

**File:** `tests/smoke/test_district_scoping.py`

**Purpose:** Verify district scoping functionality works correctly

**Tests Included:**
1. **`test_can_view_district_method()`** - Tests `User.can_view_district()` method
   - Global users can view any district
   - District-scoped users can view only assigned districts
   - Users with no districts cannot view any district

2. **`test_is_district_scoped_property()`** - Tests `User.is_district_scoped` property
   - Verifies scope type detection

3. **`test_is_school_scoped_property()`** - Tests `User.is_school_scoped` property
   - Verifies school scope detection

4. **`test_district_scoped_kck_access()`** - Tests KCK district access
   - Verifies specific district (Kansas City Kansas Public Schools) access

5. **`test_json_parsing_edge_cases()`** - Tests JSON parsing edge cases
   - Malformed JSON handling
   - Empty string handling
   - Already parsed list handling

**Running the test:**
```bash
# Using pytest
python -m pytest tests/smoke/test_district_scoping.py

# Direct execution
python tests/smoke/test_district_scoping.py
```

**Reference:** [RBAC Matrix](rbac_matrix) for district scoping rules

## Critical Paths

These are the essential system functions that should be smoke tested to ensure basic functionality:

### Authentication and Authorization

**What to test:**
- Login functionality works
- Protected routes require authentication
- Role-based access control functions correctly
- District scoping works as expected

**Test files:**
- `tests/integration/test_auth_routes.py` - Authentication route tests
- `tests/smoke/test_district_scoping.py` - District scoping tests

**Quick check:**
```bash
# Run auth tests
python -m pytest tests/integration/test_auth_routes.py

# Run district scoping smoke test
python -m pytest tests/smoke/test_district_scoping.py
```

**Reference:** [RBAC Matrix](rbac_matrix) for access control rules

### Database Connectivity

**What to test:**
- Database connection is established
- Basic queries execute successfully
- Database integrity is maintained

**Quick check:**
```bash
# Run health check (includes database check)
python scripts/utilities/pythonanywhere_cache_manager.py health
```

**Reference:** [Monitoring and Alert - Health Checks](monitoring#health-checks)

### API Endpoints

**What to test:**
- Health check endpoint responds
- Protected routes work with authentication
- API rate limiting functions
- Endpoints return expected status codes

**Test files:**
- `tests/integration/test_api_endpoints.py` - API endpoint tests

**Quick check:**
```bash
# Run API endpoint tests
python -m pytest tests/integration/test_api_endpoints.py
```

### Import Functionality

**What to test:**
- Import scripts can execute
- Basic import validation passes
- Import health monitoring works

**Quick check:**
```bash
# Run import health check
python scripts/cli/monitor_import_health.py
```

**Reference:** [Import Playbook](import_playbook) for import procedures

### Cache System

**What to test:**
- Cache refresh functionality works
- Cache status can be retrieved
- Cache management routes are accessible

**Quick check:**
- Visit `/management/cache/status` (Admin only)
- Run cache health check via health check script

**Reference:** [Monitoring and Alert - Cache Status Dashboard](monitoring#cache-status-dashboard)

### Email System

**What to test:**
- Email configuration is valid
- Email sending capability works
- Email management routes are accessible

**Quick check:**
- Visit `/management/email` (Admin only)
- Check email system status

**Reference:** [Monitoring and Alert - Email Overview Dashboard](monitoring#email-overview-dashboard)

## Running Smoke Tests

### Using pytest

**Run all smoke tests:**
```bash
python -m pytest tests/smoke/
```

**Run specific smoke test:**
```bash
python -m pytest tests/smoke/test_district_scoping.py
```

**Run with verbose output:**
```bash
python -m pytest tests/smoke/ -v
```

**Run with coverage:**
```bash
python -m pytest tests/smoke/ --cov=tests/smoke
```

### Using Test Runner

**Run fast tests (excludes slow and salesforce):**
```bash
python run_tests.py --type fast
```

**Run all tests:**
```bash
python run_tests.py --type all
```

**Run with verbose output:**
```bash
python run_tests.py --type fast --verbose
```

**Run specific test file:**
```bash
python run_tests.py --type fast --file tests/smoke/test_district_scoping.py
```

**Reference:** `run_tests.py` - Test runner script

### Direct Execution

**Run smoke test directly:**
```bash
python tests/smoke/test_district_scoping.py
```

This will execute the test and print "All smoke tests passed!" if successful.

### Pytest Configuration

**Configuration file:** `pytest.ini`

**Default behavior:**
- Skips slow tests (`-m "not slow"`)
- Skips Salesforce tests (`-m "not salesforce"`)
- Verbose output (`-v`)
- Short traceback format (`--tb=short`)

**Run with different markers:**
```bash
# Include slow tests
python -m pytest tests/ -m "not salesforce"

# Include Salesforce tests (requires Salesforce connection)
python -m pytest tests/ -m "salesforce"
```

## Smoke Test Checklist

### Pre-Deployment

Before deploying code changes:

- [ ] Run all smoke tests: `python -m pytest tests/smoke/`
- [ ] Verify critical paths:
  - [ ] Authentication works
  - [ ] Database connectivity
  - [ ] API endpoints respond
  - [ ] District scoping functions
- [ ] Check database connectivity: `python scripts/utilities/pythonanywhere_cache_manager.py health`
- [ ] Verify authentication works: `python -m pytest tests/integration/test_auth_routes.py`
- [ ] Run fast test suite: `python run_tests.py --type fast`

### Post-Deployment

Immediately after deployment:

- [ ] Run smoke tests: `python -m pytest tests/smoke/`
- [ ] Verify no regressions in critical paths
- [ ] Check health endpoints: Visit `/management/cache/status`
- [ ] Verify imports can run: `python scripts/cli/monitor_import_health.py`
- [ ] Test authentication: Log in and verify access
- [ ] Check API endpoints: `python -m pytest tests/integration/test_api_endpoints.py`

**Reference:** [Deployment Guide - Deployment Updates](deployment#deployment-updates) for complete update procedures

### After Code Changes

When modifying critical functionality:

- [ ] Run relevant smoke tests for changed functionality
- [ ] Verify affected functionality still works
- [ ] Check for breaking changes in related systems
- [ ] Run integration tests for modified routes/models

**Example:** If modifying district scoping:
```bash
# Run district scoping smoke test
python -m pytest tests/smoke/test_district_scoping.py

# Run auth route tests
python -m pytest tests/integration/test_auth_routes.py
```

## Integration with Health Checks

### Relationship

**Smoke Tests:**
- Verify **functionality** - Does the code work as expected?
- Test **business logic** - Are features functioning correctly?
- Fast execution - Run in seconds
- Focus on critical paths

**Health Checks:**
- Verify **system status** - Is infrastructure operational?
- Test **connectivity** - Can systems communicate?
- Infrastructure focus - Database, cache, Flask app
- System-level verification

**Both should pass** for the system to be considered fully operational.

### When Smoke Tests Fail

**Indicates:** Functional issue in code

**Actions:**
1. Review test output for specific failures
2. Check code changes that might have caused the issue
3. Verify related functionality
4. Check [Runbook](runbook) for troubleshooting procedures
5. Fix code and re-run tests

**Example:** District scoping test fails → Check RBAC implementation, verify User model changes

### When Health Checks Fail

**Indicates:** System/infrastructure issue

**Actions:**
1. Check system health: `python scripts/utilities/pythonanywhere_cache_manager.py health`
2. Verify database connectivity
3. Check cache system status
4. Review [Monitoring and Alert](monitoring) for procedures
5. Check infrastructure logs

**Example:** Database health check fails → Check database connection, verify database is running

### Combined Verification

**Complete system verification:**
1. Run health check: `python scripts/utilities/pythonanywhere_cache_manager.py health`
2. Run smoke tests: `python -m pytest tests/smoke/`
3. Both should pass for system to be operational

**Reference:** [Monitoring and Alert - Health Checks](monitoring#health-checks)

## Adding New Smoke Tests

When adding new critical functionality, consider adding smoke tests:

**Guidelines:**
- Test critical paths only
- Keep tests fast (< 1 second each)
- Test happy path (basic functionality)
- Avoid external dependencies when possible
- Place in `tests/smoke/` directory

**Example structure:**
```python
"""Smoke test for [feature name]."""

import pytest

def test_feature_basic_functionality():
    """Test basic [feature] functionality."""
    # Test critical path
    assert feature_works() == True

if __name__ == "__main__":
    test_feature_basic_functionality()
    print("All smoke tests passed!")
```

**Reference:** [Testing Guide](docs/living/Testing.md) for test patterns

## Related Requirements

- [NFR-2](non_functional_requirements#nfr-2): Reliability - Clear failure feedback
- [NFR-3](non_functional_requirements#nfr-3): Security - Access restricted by role and district scope
- [FR-DISTRICT-501](requirements#fr-district-501): District Viewer authentication

## Related Documentation

- [Testing Guide](docs/living/Testing.md) - Complete testing setup and patterns
- [Runbook](runbook) - Troubleshooting procedures
- [Monitoring and Alert](monitoring) - System health monitoring
- [RBAC Matrix](rbac_matrix) - Access control rules
- [Import Playbook](import_playbook) - Import procedures

---

*Last updated: January 2026*
*Version: 1.0*
