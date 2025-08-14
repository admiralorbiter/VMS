# Salesforce Data Validation System

## Overview

The Salesforce Data Validation System is a comprehensive framework for validating data integrity between the VMS (Volunteer Management System) and Salesforce. It ensures that imported data is not only complete in terms of record counts but also accurate in terms of field values, relationships, and business logic.

## 🎯 **Current Status - Phase 1 Complete** ✅

**Phase 1: Record Count Validation** - ✅ **OPERATIONAL**
- ✅ Fast validation working
- ✅ Slow validation working
- ✅ Count validation working
- ✅ Salesforce schema correctly configured
- ✅ Database integration operational
- ✅ CLI interface functional
- ✅ Results storage and retrieval working

**Phase 2: Field Completeness Validation** - ✅ **COMPLETED**
- ✅ Field completeness checks for all entity types
- ✅ Data quality validation (format, range, consistency)
- ✅ Required field validation with configurable thresholds
- ✅ Multi-entity validation (volunteer, organization, event, student, teacher)
- ✅ Detailed error reporting and metrics

**Phase 3: Advanced Data Validation** - 🚧 **PLANNED**
- 🔄 Data type validation (format, range, consistency)
- 🔄 Relationship integrity validation
- 🔄 Business rule validation
- 🔄 Data quality scoring and trends

## Features

- **Multi-tier Validation**: Fast, slow, and real-time validation modes
- **Comprehensive Coverage**: Validates volunteers, organizations, events, students, and teachers
- **Performance Monitoring**: Tracks execution time, memory usage, and performance metrics
- **Flexible Configuration**: Environment-based configuration with customizable thresholds
- **Caching**: Redis-based caching for Salesforce queries to improve performance
- **Error Handling**: Robust error handling with retry logic and graceful degradation
- **Reporting**: Detailed validation reports with severity levels and trend analysis
- **CLI Interface**: Command-line tools for running validations and viewing results

## Architecture

The system is built with a modular architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VMS System   │    │ Validation Engine│    │  Salesforce     │
│                │◄──►│                  │◄──►│                 │
│                │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Validation Models│
                       │                  │
                       │ - ValidationRun  │
                       │ - ValidationResult│
                       │ - ValidationMetric│
                       └──────────────────┘
```

## Quick Start

### 1. Environment Setup

Set the following environment variables:

```bash
# Salesforce credentials
export SF_USERNAME="your_salesforce_username"
export SF_PASSWORD="your_salesforce_password"
export SF_SECURITY_TOKEN="your_salesforce_security_token"

# Redis configuration (optional, for caching)
export VALIDATION_REDIS_HOST="localhost"
export VALIDATION_REDIS_PORT="6379"
export VALIDATION_REDIS_PASSWORD=""

# Validation thresholds
export VALIDATION_RECORD_COUNT_TOLERANCE="5.0"
export VALIDATION_FIELD_COMPLETENESS_THRESHOLD="95.0"
export VALIDATION_DATA_TYPE_ACCURACY_THRESHOLD="99.0"
```

### 2. Database Migration

Run the Alembic migration to create validation tables:

```bash
alembic upgrade head
```

### 3. Test the System

Run the test script to verify everything is working:

```bash
python test_validation_system.py
```

### 4. Run Your First Validation

```bash
# Run fast validation (count checks only)
python run_validation.py fast

# Run count validation for volunteers only
python run_validation.py count --entity-type volunteer

# Run slow validation (comprehensive checks)
python run_validation.py slow
```

## Usage

### Command Line Interface

The system provides a comprehensive CLI for running validations and viewing results:

```bash
# Run validations
python run_validation.py fast                    # Fast validation
python run_validation.py slow                    # Slow validation
python run_validation.py count --entity-type volunteer  # Count validation

# View results
python run_validation.py status --run-id 123     # Check run status
python run_validation.py recent --limit 5        # Show recent runs
python run_validation.py results --run-id 123   # Show validation results
```

### Programmatic Usage

```python
from utils.validation_engine import get_validation_engine

# Get the validation engine
engine = get_validation_engine()

# Run fast validation
run = engine.run_fast_validation(user_id=1)

# Check status
status = engine.get_run_status(run.id)

# Get results
results = engine.get_run_results(run.id)

# Get metrics
metrics = engine.get_run_metrics(run.id)
```

### Custom Validators

Create custom validators by extending the `DataValidator` base class:

```python
from utils.validation_base import DataValidator

class CustomValidator(DataValidator):
    def get_entity_type(self) -> str:
        return 'custom_entity'

    def validate(self) -> List[ValidationResult]:
        # Your validation logic here
        results = []

        # Add validation results
        result = self.create_result(
            entity_type='custom_entity',
            severity='info',
            message='Custom validation passed',
            validation_type='custom'
        )
        self.add_result(result)

        return results
```

## Configuration

### Validation Thresholds

Configure validation thresholds in `config/validation.py` or via environment variables:

```python
VALIDATION_THRESHOLDS = {
    'record_count_tolerance': 5.0,           # ±5% tolerance for record counts
    'field_completeness_threshold': 95.0,    # >95% required fields
    'data_type_accuracy_threshold': 99.0,    # >99% data type accuracy
    'relationship_integrity_threshold': 1.0,  # <1% orphaned records
}
```

### Salesforce Settings

```python
SALESFORCE_CONFIG = {
    'max_requests_per_second': 100,    # API rate limiting
    'retry_attempts': 3,               # Retry failed requests
    'timeout': 30,                     # Request timeout in seconds
    'batch_size': 200,                 # Batch size for queries
}
```

### Redis Caching

```python
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'cache_ttl': 3600,                # 1 hour cache TTL
    'max_cache_size': 100,             # 100 MB max cache size
}
```

## Validation Types

### 1. Count Validation

Compares record counts between VMS and Salesforce:

- **Fast**: Basic count comparison
- **Configurable**: Tolerance thresholds for acceptable differences
- **Comprehensive**: Covers all entity types

### 2. Field Completeness Validation

Checks required field completion rates:

- **Sample-based**: Uses configurable sample sizes for large datasets
- **Threshold-based**: Configurable completion thresholds
- **Detailed reporting**: Field-level completion statistics

### 3. Data Type Validation

Validates data type consistency:

- **Format checking**: Email, phone, date formats
- **Type validation**: String, numeric, boolean types
- **Custom rules**: Business-specific validation rules

### 4. Relationship Validation

Ensures referential integrity:

- **Orphaned records**: Identifies records without proper relationships
- **Circular references**: Detects circular relationship patterns
- **Business rules**: Validates relationship business logic

### 5. Business Logic Validation

Validates business-specific rules:

- **Status transitions**: Validates allowed status changes
- **Date ranges**: Ensures logical date relationships
- **Capacity limits**: Validates business constraints

## Monitoring and Reporting

### Validation Metrics

The system tracks comprehensive metrics:

- **Performance metrics**: Execution time, memory usage, CPU usage
- **Quality metrics**: Success rates, error rates, warning rates
- **Business metrics**: Record counts, completion rates, accuracy rates

### Trend Analysis

Track validation performance over time:

```python
from models.validation.metric import ValidationMetric

# Get trend data for a specific metric
trend_data = ValidationMetric.get_trend_data(
    metric_name='count_difference_percentage',
    entity_type='volunteer',
    days=30
)
```

### Alerting

Configure alerts for critical issues:

```python
ALERT_CONFIG = {
    'alert_on_critical': True,         # Alert on critical issues
    'alert_on_error': True,            # Alert on errors
    'alert_threshold_critical': 5,     # Alert if >5 critical issues
    'alert_threshold_error': 20,       # Alert if >20 errors
}
```

## Performance Considerations

### Caching Strategy

- **Query caching**: Cache Salesforce query results
- **TTL management**: Configurable cache expiration
- **Cache invalidation**: Automatic cache cleanup

### Rate Limiting

- **API quotas**: Respect Salesforce API limits
- **Request batching**: Batch multiple requests
- **Retry logic**: Exponential backoff for failures

### Resource Management

- **Memory monitoring**: Track memory usage during validation
- **Timeout handling**: Prevent long-running validations
- **Cleanup**: Automatic resource cleanup after validation

## Troubleshooting

### Common Issues

1. **Salesforce Connection Failed**
   - Check credentials and security token
   - Verify network connectivity
   - Check Salesforce service status

2. **Redis Connection Failed**
   - Verify Redis server is running
   - Check host/port configuration
   - Validation will continue without caching

3. **Validation Timeout**
   - Increase timeout thresholds
   - Use smaller sample sizes
   - Run validations during off-peak hours

### Debug Mode

Enable debug logging:

```bash
export VALIDATION_LOG_LEVEL="DEBUG"
```

### Health Checks

Check system health:

```python
from utils.salesforce_client import SalesforceClient

client = SalesforceClient()
health = client.get_health_status()
print(health)
```

## Development

### Adding New Validators

1. Create a new validator class extending `DataValidator`
2. Implement the `validate()` method
3. Add to the validation engine
4. Update configuration as needed

### Testing

Run the test suite:

```bash
python test_validation_system.py
```

### Code Style

Follow the existing code style:
- Use type hints
- Add comprehensive docstrings
- Follow PEP 8 guidelines
- Include error handling

## API Reference

### ValidationEngine

Main orchestrator for validation runs:

```python
class ValidationEngine:
    def run_fast_validation(self, user_id: int = None) -> ValidationRun
    def run_slow_validation(self, user_id: int = None) -> ValidationRun
    def run_custom_validation(self, validators: List[DataValidator], ...) -> ValidationRun
    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]
    def get_run_results(self, run_id: int, ...) -> List[Dict[str, Any]]
```

### DataValidator

Base class for all validators:

```python
class DataValidator(ABC):
    def validate(self) -> List[ValidationResult]
    def add_result(self, result: ValidationResult)
    def add_metric(self, metric: ValidationMetric)
    def get_summary(self) -> Dict[str, Any]
```

### ValidationResult

Represents individual validation findings:

```python
class ValidationResult:
    severity: str                    # 'info', 'warning', 'error', 'critical'
    entity_type: str                # Type of entity validated
    message: str                    # Human-readable message
    expected_value: str             # Expected value
    actual_value: str               # Actual value found
```

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Check configuration settings
4. Verify environment variables
5. Test with the validation test script

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Follow the coding standards
5. Test thoroughly before submitting

## License

This system is part of the VMS project and follows the same licensing terms.
