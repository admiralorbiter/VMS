# Phase 3.4 User Guide: Comprehensive Validation & Quality Scoring

**Version**: Complete ✅
**Date**: December 2024
**Status**: All Validation Types Running for All Entities with Auto-Refresh Dashboard

## 🚀 **Quick Start Guide**

### **Prerequisites**
- Phase 3.3 (Business Rule Validation) completed
- Database migrations applied successfully
- Validation runs executed to generate metrics

### **What's New in Phase 3.4**
- **Historical Data Tracking**: Comprehensive validation history with quality scores
- **Advanced Metrics**: Trend analysis and aggregation capabilities
- **Data Aggregation Engine**: Rolling averages, pattern detection, and optimization
- **Enhanced Reporting**: Period-based summaries and trend analysis
- **Local Entity Support**: School and District entities with comprehensive validation
- **Enhanced Business Rules**: Advanced validation including field format, data quality, and naming conventions
- **Auto-Refresh Dashboard**: Real-time updates when switching entity types or time periods

## 📊 **Getting Started with Historical Data**

### **Step 1: Generate Validation Data**
Before using the new features, you need validation runs with metrics:

```bash
# Run business rule validation to generate metrics
python scripts/validation/run_validation.py business-rules --entity-type volunteer

# Run field completeness validation
python scripts/validation/run_validation.py field-completeness --entity-type volunteer

# Run data type validation
python scripts/validation/run_validation.py data-types --entity-type volunteer
```

### **Step 2: Create Historical Records**
Automatically create historical tracking records:

```bash
# Create history from recent validation runs
python scripts/validation/test_history_service.py

# Or create history for a specific run
python scripts/validation/test_history_service.py <run_id>
```

### **Step 3: Test Data Aggregation**
Test the new aggregation capabilities:

```bash
# Test all aggregation features
python scripts/validation/test_aggregation_service.py
```

### **Step 4: Validate Local Entities**
Test the new School and District entity validation:

```bash
# Run comprehensive validation for School entity
python scripts/validation/run_validation.py comprehensive --entity-type school

# Run comprehensive validation for District entity
python scripts/validation/run_validation.py comprehensive --entity-type district

# Run all validations for all entities (including School and District)
python scripts/validation/run_validation.py comprehensive --entity-type all
```

## 🏫 **School & District Entity Validation**

### **Local Entity Support**
Phase 3.4 introduces comprehensive validation for School and District entities, which are local VMS entities (not imported from Salesforce).

#### **School Entity Validation**
- **Required Fields**: ID (Salesforce format), Name
- **Optional Fields**: Level, School Code, District ID
- **Business Rules**: Field format validation, data quality validation, level validation, naming conventions
- **Count Validation**: Expects 0% discrepancy with Salesforce (local-only entity)

#### **District Entity Validation**
- **Required Fields**: ID (auto-increment), Name
- **Optional Fields**: District Code, Salesforce ID
- **Business Rules**: Field format validation, data quality validation, code validation
- **Count Validation**: Expects 0% discrepancy with Salesforce (local-only entity)

### **Enhanced Business Rules**
The business rule validator now supports advanced validation features:

- **Field Format Validation**: Length constraints, pattern matching, enumeration validation
- **Data Quality Validation**: Whitespace checks, pattern validation, format requirements
- **Naming Convention Validation**: School naming rules, district code format validation
- **Relationship Validation**: District-School associations and integrity checks

## 🔍 **Using the Historical Data Service**

### **Automatic History Creation**
The `ValidationHistoryService` automatically creates historical records from validation runs:

```python
from utils.services.history_service import ValidationHistoryService

# Initialize the service
history_service = ValidationHistoryService()

# Create history from a specific run
history_records = history_service.create_history_from_run(run_id=123)

# Populate history from recent runs (last 7 days)
total_created = history_service.populate_history_from_recent_runs(days=7)
```

### **Querying Historical Data**
Access historical validation data:

```python
from models.validation import ValidationHistory

# Get entity history
volunteer_history = ValidationHistory.get_entity_history(
    entity_type='volunteer',
    days=30
)

# Get quality trends
trends = ValidationHistory.get_quality_trends(
    entity_type='volunteer',
    days=90
)

# Get anomalies
anomalies = ValidationHistory.get_anomalies(
    entity_type='volunteer',
    days=30
)
```

## 📈 **Using the Data Aggregation Service**

### **Rolling Averages**
Calculate rolling averages for quality metrics:

```python
from utils.services.aggregation_service import DataAggregationService

# Initialize the service
agg_service = DataAggregationService()

# Calculate 7-day rolling averages
rolling_avg = agg_service.calculate_rolling_averages(
    metric_name='field_completeness',
    entity_type='volunteer',
    window_size=7,
    days=30
)

# Calculate multiple window sizes
moving_windows = agg_service.calculate_moving_windows(
    metric_name='business_rule_compliance',
    entity_type='volunteer',
    window_sizes=[3, 7, 14, 30],
    days=30
)
```

### **Trend Pattern Detection**
Detect patterns in your data:

```python
# Detect trend patterns
patterns = agg_service.detect_trend_patterns(
    metric_name='data_type_accuracy',
    entity_type='volunteer',
    days=90,
    min_pattern_length=5
)

# Generate comprehensive data summary
summary = agg_service.generate_data_summary(
    entity_type='volunteer',
    days=30,
    include_patterns=True
)
```

### **Performance Optimization**
Get recommendations for large datasets:

```python
# Get optimization recommendations
optimization = agg_service.optimize_aggregation_performance(
    metric_name='field_completeness',
    entity_type='volunteer',
    target_response_time=1.0
)
```

## 📊 **Enhanced ValidationMetric Features**

### **Trend Analysis Methods**
Use the new trend analysis methods directly on metrics:

```python
from models.validation import ValidationMetric

# Calculate trends for a metric
trends = ValidationMetric.calculate_trends_for_metric(
    metric_name='field_completeness',
    entity_type='volunteer',
    days=30
)

# Get period-based summaries
daily_summary = ValidationMetric.get_metric_summary_by_period(
    metric_name='field_completeness',
    period='daily',
    entity_type='volunteer',
    days=30
)

# Get aggregated metrics
aggregated = ValidationMetric.get_aggregated_metrics(
    metric_name='field_completeness',
    aggregation_period='daily',
    entity_type='volunteer',
    days=30
)
```

## 🗄️ **Database Schema Changes**

### **New Fields in ValidationMetric**
The `ValidationMetric` table now includes:

- **Trend Fields**: `trend_period`, `trend_direction`, `trend_magnitude`, `trend_confidence`
- **Aggregation Fields**: `aggregation_type`, `aggregation_period`, `aggregation_start`, `aggregation_end`
- **Comparison Fields**: `baseline_value`, `change_percentage`

### **New ValidationHistory Table**
Complete historical tracking with:

- Quality scores and violation counts
- Trend data and anomaly detection
- Performance metrics and execution times
- Metadata and notes for analysis

## 📋 **Common Use Cases**

### **1. Quality Trend Monitoring**
```python
# Monitor quality trends over time
trends = ValidationHistory.get_quality_trends('volunteer', days=90)
for record in trends:
    if record.trend_direction == 'declining':
        print(f"Quality declining: {record.trend_description}")
```

### **2. Anomaly Detection**
```python
# Detect quality anomalies
anomalies = ValidationHistory.get_anomalies('volunteer', days=30)
for anomaly in anomalies:
    print(f"Anomaly detected: {anomaly.anomaly_type}")
```

### **3. Performance Analysis**
```python
# Analyze validation performance
summary = agg_service.generate_data_summary('volunteer', days=30)
print(f"Average quality score: {summary['metrics_summary']['quality_score']['mean']:.2f}")
```

### **4. Rolling Quality Assessment**
```python
# Get rolling quality scores
rolling_quality = agg_service.calculate_rolling_averages(
    metric_name='quality_score',
    entity_type='volunteer',
    window_size=7,
    days=30
)
```

## ⚠️ **Troubleshooting**

### **Common Issues**

1. **"No metrics found" errors**
   - Ensure validation runs have been executed
   - Check that metrics are being generated
   - Verify entity type names match exactly

2. **Insufficient data for trend analysis**
   - Need at least 3-5 data points for basic trends
   - Need 30+ days for seasonal patterns
   - Run more validation tests to generate data

3. **Database migration errors**
   - Ensure all migrations are applied: `alembic upgrade head`
   - Check for migration conflicts
   - Verify database schema matches models

### **Data Requirements**

| Feature | Minimum Data Points | Recommended Period |
|---------|-------------------|-------------------|
| Basic Trends | 3 | 7 days |
| Rolling Averages | 7 | 30 days |
| Seasonal Patterns | 30 | 90 days |
| Anomaly Detection | 5 | 30 days |
| Comprehensive Analysis | 10 | 60 days |

## 🔧 **Configuration Options**

### **Aggregation Service Settings**
```python
# Customize aggregation service
agg_service = DataAggregationService()
agg_service.anomaly_threshold = 2.5  # Standard deviations
agg_service.trend_confidence_threshold = 0.8  # Minimum confidence
```

### **History Service Settings**
```python
# Customize history service
history_service = ValidationHistoryService()
# Default quality threshold is 70.0
# Default retention period is 365 days
```

## 📈 **Next Steps**

### **Week 3-4: Quality Scoring Engine**
- Weighted scoring algorithms
- Configurable quality thresholds
- Multi-dimensional quality assessment

### **Week 5-6: Advanced Analytics**
- Correlation analysis
- Root cause analysis
- Predictive modeling

### **Week 7-8: Reporting & Dashboards**
- Automated reporting
- Real-time dashboards
- Export capabilities

## 📞 **Support & Resources**

- **Documentation**: Check `docs/` folder for detailed technical docs
- **Test Scripts**: Use test scripts to verify functionality
- **Models**: Review `models/validation/` for data structure
- **Services**: Check `utils/services/` for implementation details

---

**Need Help?** Run the test scripts to verify your setup, or check the troubleshooting section above.
