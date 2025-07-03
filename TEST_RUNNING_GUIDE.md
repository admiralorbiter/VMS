# VMS Test Running Guide

## Overview
This guide explains how to run the different types of tests in the VMS application, including the new integration tests we've created.

## Quick Start

### 1. Run Fast Tests (Recommended for Development)
```bash
python run_tests.py --type fast
```
This runs all tests except slow ones (like Salesforce imports).

### 2. Run Unit Tests Only
```bash
python run_tests.py --type unit
```

### 3. Run Integration Tests Only
```bash
python run_tests.py --type integration
```

## Test Types

### Fast Tests (Default)
- **What**: All tests except slow ones
- **Duration**: 1-5 minutes
- **Use Case**: Daily development, CI/CD
- **Command**: `python run_tests.py --type fast`

### Unit Tests
- **What**: Model tests, utility function tests
- **Duration**: 30 seconds - 2 minutes
- **Use Case**: Testing individual components
- **Command**: `python run_tests.py --type unit`

### Integration Tests
- **What**: Route tests, database integration, API tests
- **Duration**: 2-10 minutes
- **Use Case**: Testing complete workflows
- **Command**: `python run_tests.py --type integration`

### Salesforce Tests (SKIPPED by default)
- **What**: Salesforce integration tests
- **Duration**: 30-60 minutes
- **Use Case**: Full Salesforce sync testing
- **Command**: `python run_tests.py --type salesforce`

## Direct Pytest Commands

### Basic Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Run only unit tests
python -m pytest tests/unit/ -v

# Run only integration tests
python -m pytest tests/integration/ -v

# Run fast tests (exclude slow ones)
python -m pytest tests/ -m "not slow" -v
```

### Specific Test Files
```bash
# Run specific integration test file
python -m pytest tests/integration/test_organization_routes.py -v

# Run specific unit test file
python -m pytest tests/unit/models/test_organization.py -v
```

### Specific Test Functions
```bash
# Run specific test function
python -m pytest tests/integration/test_organization_routes.py::test_organizations_list_view -v

# Run tests matching a pattern
python -m pytest tests/integration/ -k "organization" -v
```

### Salesforce Tests (When Needed)
```bash
# Run Salesforce tests (takes 30-60 minutes)
python -m pytest tests/integration/ -m "salesforce" -v

# Run specific Salesforce test
python -m pytest tests/integration/test_organization_routes.py::test_organization_salesforce_import -v
```

## Test Runner Script Options

### Basic Usage
```bash
# Run fast tests (default)
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Run with coverage report
python run_tests.py --coverage
```

### Specific Tests
```bash
# Run specific test file
python run_tests.py --file tests/integration/test_organization_routes.py

# Run specific test function
python run_tests.py --file tests/integration/test_organization_routes.py --function test_organizations_list_view
```

### Different Test Types
```bash
# Run unit tests
python run_tests.py --type unit

# Run integration tests
python run_tests.py --type integration

# Run all tests
python run_tests.py --type all

# Run Salesforce tests
python run_tests.py --type salesforce
```

## Test Categories

### Unit Tests (tests/unit/)
- **Model Tests**: Test individual model behavior
- **Utility Tests**: Test helper functions
- **Validation Tests**: Test data validation logic

### Integration Tests (tests/integration/)
- **Organization Tests**: CRUD operations, imports, relationships
- **Attendance Tests**: Student/teacher management, CSV imports
- **Report Tests**: All report types, filtering, exports
- **Management Tests**: Admin functions, Google Sheets, bug reports

## Test Markers

The tests use pytest markers to categorize them:

- `@pytest.mark.slow`: Tests that take a long time (skipped by default)
- `@pytest.mark.salesforce`: Tests requiring Salesforce integration
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.performance`: Performance tests

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Errors**: Tests use a test database that gets created automatically

3. **Salesforce Tests Failing**: This is expected - they require proper credentials

4. **Linter Warnings**: Some linter warnings about model fields are expected in test files

### Environment Setup

Make sure you have these environment variables set:
```bash
export ENCRYPTION_KEY="your-encryption-key"
export FLASK_ENV="testing"
```

### Test Database

Tests automatically:
- Create a test database
- Run migrations
- Clean up after tests
- Use isolated sessions

## Performance Tips

1. **Use Fast Tests for Development**: `python run_tests.py --type fast`
2. **Run Specific Tests**: Only run tests you're working on
3. **Use Coverage Sparingly**: Coverage reports slow down test execution
4. **Skip Salesforce Tests**: Only run when needed for full integration testing

## CI/CD Integration

For continuous integration, use:
```bash
# Fast tests for quick feedback
python run_tests.py --type fast --coverage

# Full test suite for releases
python run_tests.py --type all --coverage
```

## Test Results

### Success Indicators
- ✅ All tests pass
- ✅ No critical errors
- ✅ Coverage meets requirements

### Common Failures
- ❌ Salesforce connection issues (expected without credentials)
- ❌ Missing test data files (some tests expect CSV files)
- ❌ Database constraint violations (indicates model issues)

## Next Steps

After running tests:
1. Fix any failing tests
2. Review coverage reports
3. Add new tests for new features
4. Update integration tests when routes change 