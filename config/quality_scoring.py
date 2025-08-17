# config/quality_scoring.py
"""
Quality Scoring Configuration for Phase 3.4.

This file contains configuration for quality scoring weights, thresholds,
and scoring algorithms that can be customized based on business needs.
"""

# Quality scoring weights for different entity types
# Weights are normalized to sum to 1.0
QUALITY_WEIGHTS = {
    "volunteer": {
        "field_completeness": 0.30,  # 30% - Critical for volunteer management
        "data_types": 0.25,  # 25% - Important for data integrity
        "business_rules": 0.25,  # 25% - Business logic compliance
        "relationships": 0.20,  # 20% - Relationship validation
    },
    "organization": {
        "field_completeness": 0.35,  # 35% - Very critical for org data
        "data_types": 0.20,  # 20% - Data type accuracy
        "business_rules": 0.25,  # 25% - Business rule compliance
        "relationships": 0.20,  # 20% - Relationship validation
    },
    "event": {
        "field_completeness": 0.25,  # 25% - Event details
        "data_types": 0.20,  # 20% - Data type accuracy
        "business_rules": 0.35,  # 35% - Critical for event logic
        "relationships": 0.20,  # 20% - Relationship validation
    },
    "student": {
        "field_completeness": 0.30,  # 30% - Student information
        "data_types": 0.25,  # 25% - Data type accuracy
        "business_rules": 0.25,  # 25% - Business rule compliance
        "relationships": 0.20,  # 20% - Relationship validation
    },
    "teacher": {
        "field_completeness": 0.30,  # 30% - Teacher information
        "data_types": 0.25,  # 25% - Data type accuracy
        "business_rules": 0.25,  # 25% - Business rule compliance
        "relationships": 0.20,  # 20% - Relationship validation
    },
    # Default weights for any entity type not specifically defined
    "default": {
        "field_completeness": 0.25,  # 25% - Standard field completeness
        "data_types": 0.25,  # 25% - Standard data type accuracy
        "business_rules": 0.25,  # 25% - Standard business rule compliance
        "relationships": 0.25,  # 25% - Standard relationship validation
    },
}

# Severity-based weights for different validation result severities
# Higher weights mean more impact on quality score
SEVERITY_WEIGHTS = {
    "critical": 1.0,  # 100% impact - Critical issues
    "error": 0.8,  # 80% impact - Error issues
    "warning": 0.5,  # 50% impact - Warning issues
    "info": 0.2,  # 20% impact - Informational issues
}

# Quality thresholds for different entity types
# Scores below these thresholds are considered poor quality
QUALITY_THRESHOLDS = {
    "volunteer": 80.0,  # 80% - Volunteers need high data quality
    "organization": 85.0,  # 85% - Organizations need very high data quality
    "event": 75.0,  # 75% - Events can tolerate some data issues
    "student": 80.0,  # 80% - Students need high data quality
    "teacher": 80.0,  # 80% - Teachers need high data quality
    "default": 75.0,  # 75% - Default threshold
}

# Penalty multipliers for different types of validation failures
# Higher multipliers mean more score reduction
PENALTY_MULTIPLIERS = {
    "critical_error": 10.0,  # 10x penalty for critical errors
    "data_type_mismatch": 5.0,  # 5x penalty for data type issues
    "missing_required_field": 8.0,  # 8x penalty for missing required fields
    "invalid_relationship": 6.0,  # 6x penalty for relationship issues
    "business_rule_violation": 7.0,  # 7x penalty for business rule violations
    "field_validation_error": 4.0,  # 4x penalty for field validation errors
}

# Scoring algorithm configurations
SCORING_ALGORITHMS = {
    "field_completeness": {
        "type": "percentage_based",
        "required_fields_weight": 2.0,  # Required fields count double
        "optional_fields_weight": 1.0,  # Optional fields count normally
        "missing_field_penalty": 8.0,  # Penalty for missing required fields
    },
    "data_types": {
        "type": "penalty_based",
        "base_score": 100.0,  # Start with 100%
        "type_mismatch_penalty": 5.0,  # Penalty per type mismatch
        "format_error_penalty": 3.0,  # Penalty per format error
        "max_penalty": 50.0,  # Maximum penalty (50%)
    },
    "business_rules": {
        "type": "severity_weighted",
        "base_score": 100.0,  # Start with 100%
        "rule_violation_penalty": 7.0,  # Base penalty for rule violations
        "severity_multipliers": {  # Severity-based multipliers
            "critical": 2.0,
            "error": 1.5,
            "warning": 1.0,
            "info": 0.5,
        },
    },
    "relationships": {
        "type": "percentage_based",
        "valid_relationship_weight": 1.0,  # Valid relationships count normally
        "invalid_relationship_penalty": 6.0,  # Penalty for invalid relationships
        "orphaned_record_penalty": 8.0,  # Penalty for orphaned records
    },
}

# Quality score ranges and status definitions
QUALITY_SCORE_RANGES = {
    "excellent": {
        "min": 90.0,
        "max": 100.0,
        "color": "#28a745",  # Green
        "description": "Excellent data quality",
    },
    "good": {
        "min": 80.0,
        "max": 89.9,
        "color": "#17a2b8",  # Blue
        "description": "Good data quality",
    },
    "fair": {
        "min": 70.0,
        "max": 79.9,
        "color": "#ffc107",  # Yellow
        "description": "Fair data quality - needs attention",
    },
    "poor": {
        "min": 0.0,
        "max": 69.9,
        "color": "#dc3545",  # Red
        "description": "Poor data quality - immediate action required",
    },
}

# Trend analysis configuration
TREND_ANALYSIS = {
    "min_data_points": 3,  # Minimum data points for trend analysis
    "confidence_threshold": 0.7,  # Minimum confidence for trend detection
    "trend_strength_thresholds": {
        "weak": 0.1,  # Weak trend threshold
        "moderate": 0.5,  # Moderate trend threshold
        "strong": 1.0,  # Strong trend threshold
    },
}

# Performance optimization settings
PERFORMANCE_SETTINGS = {
    "batch_size": 1000,  # Process validation results in batches
    "cache_ttl": 300,  # Cache TTL in seconds (5 minutes)
    "max_concurrent_calculations": 4,  # Maximum concurrent score calculations
    "timeout_seconds": 30,  # Timeout for score calculation operations
}

# Reporting configuration
REPORTING_CONFIG = {
    "default_report_period": 30,  # Default days for reports
    "max_report_period": 365,  # Maximum days for reports
    "include_trends_by_default": True,  # Include trends in reports by default
    "include_details_by_default": True,  # Include detailed breakdowns by default
    "export_formats": ["json", "csv", "html"],  # Supported export formats
    "max_export_records": 10000,  # Maximum records for export
}
