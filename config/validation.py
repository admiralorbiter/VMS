# config/validation.py
"""
Validation configuration for Salesforce Data Validation System.
Integrates with existing VMS configuration structure.
"""

import os
from typing import Any, Dict, List

# Validation thresholds and tolerances
VALIDATION_THRESHOLDS = {
    "record_count_tolerance": float(
        os.environ.get("VALIDATION_RECORD_COUNT_TOLERANCE", 5.0)
    ),  # Percentage tolerance for record counts
    "field_completeness_threshold": float(
        os.environ.get("VALIDATION_FIELD_COMPLETENESS_THRESHOLD", 95.0)
    ),  # Minimum completeness percentage
    "data_type_accuracy_threshold": float(
        os.environ.get("VALIDATION_DATA_TYPE_ACCURACY_THRESHOLD", 99.0)
    ),  # Minimum accuracy percentage
    "relationship_integrity_threshold": float(
        os.environ.get("VALIDATION_RELATIONSHIP_INTEGRITY_THRESHOLD", 1.0)
    ),  # Maximum orphaned record percentage
    "critical_severity_threshold": float(
        os.environ.get("VALIDATION_CRITICAL_SEVERITY_THRESHOLD", 0.1)
    ),  # Maximum critical issues percentage
    "warning_severity_threshold": float(
        os.environ.get("VALIDATION_WARNING_SEVERITY_THRESHOLD", 5.0)
    ),  # Maximum warning issues percentage
}

# Salesforce settings (integrated with existing VMS config)
SALESFORCE_CONFIG = {
    "username": os.environ.get("SF_USERNAME"),
    "password": os.environ.get("SF_PASSWORD"),
    "security_token": os.environ.get("SF_SECURITY_TOKEN"),
    "max_requests_per_second": int(
        os.environ.get("VALIDATION_SF_MAX_REQUESTS_PER_SECOND", 100)
    ),
    "retry_attempts": int(os.environ.get("VALIDATION_SF_RETRY_ATTEMPTS", 3)),
    "retry_delay": float(os.environ.get("VALIDATION_SF_RETRY_DELAY", 1.0)),
    "timeout": int(os.environ.get("VALIDATION_SF_TIMEOUT", 30)),
    "batch_size": int(os.environ.get("VALIDATION_SF_BATCH_SIZE", 200)),
}

# Redis settings for caching
REDIS_CONFIG = {
    "host": os.environ.get("VALIDATION_REDIS_HOST", "localhost"),
    "port": int(os.environ.get("VALIDATION_REDIS_PORT", 6379)),
    "db": int(os.environ.get("VALIDATION_REDIS_DB", 0)),
    "password": os.environ.get("VALIDATION_REDIS_PASSWORD"),
    "cache_ttl": int(os.environ.get("VALIDATION_CACHE_TTL", 3600)),  # 1 hour default
    "max_cache_size": int(os.environ.get("VALIDATION_MAX_CACHE_SIZE", 100)),  # MB
}

# Validation schedules
VALIDATION_SCHEDULES = {
    "fast_validation_interval": int(
        os.environ.get("VALIDATION_FAST_INTERVAL", 3600)
    ),  # 1 hour
    "slow_validation_interval": int(
        os.environ.get("VALIDATION_SLOW_INTERVAL", 86400)
    ),  # 24 hours
    "realtime_validation_enabled": os.environ.get(
        "VALIDATION_REALTIME_ENABLED", "true"
    ).lower()
    == "true",
    "background_validation_enabled": os.environ.get(
        "VALIDATION_BACKGROUND_ENABLED", "true"
    ).lower()
    == "true",
}

# Alerting and notification settings
ALERT_CONFIG = {
    "alert_on_critical": os.environ.get("VALIDATION_ALERT_ON_CRITICAL", "true").lower()
    == "true",
    "alert_on_error": os.environ.get("VALIDATION_ALERT_ON_ERROR", "true").lower()
    == "true",
    "alert_on_warning": os.environ.get("VALIDATION_ALERT_ON_WARNING", "false").lower()
    == "true",
    "alert_emails": (
        os.environ.get("VALIDATION_ALERT_EMAILS", "").split(",")
        if os.environ.get("VALIDATION_ALERT_EMAILS")
        else []
    ),
    "alert_slack_webhook": os.environ.get("VALIDATION_SLACK_WEBHOOK"),
    "alert_threshold_critical": int(
        os.environ.get("VALIDATION_ALERT_THRESHOLD_CRITICAL", 5)
    ),
    "alert_threshold_error": int(
        os.environ.get("VALIDATION_ALERT_THRESHOLD_ERROR", 20)
    ),
}

# Reporting and export settings
REPORTING_CONFIG = {
    "daily_report_enabled": os.environ.get(
        "VALIDATION_DAILY_REPORT_ENABLED", "true"
    ).lower()
    == "true",
    "weekly_report_enabled": os.environ.get(
        "VALIDATION_WEEKLY_REPORT_ENABLED", "true"
    ).lower()
    == "true",
    "monthly_report_enabled": os.environ.get(
        "VALIDATION_MONTHLY_REPORT_ENABLED", "true"
    ).lower()
    == "true",
    "export_formats": os.environ.get("VALIDATION_EXPORT_FORMATS", "csv,json,pdf").split(
        ","
    ),
    "report_retention_days": int(
        os.environ.get("VALIDATION_REPORT_RETENTION_DAYS", 90)
    ),
    "max_export_size": int(
        os.environ.get("VALIDATION_MAX_EXPORT_SIZE", 10000)
    ),  # records
}

# Performance and monitoring settings
PERFORMANCE_CONFIG = {
    "max_validation_runtime": int(
        os.environ.get("VALIDATION_MAX_RUNTIME", 3600)
    ),  # 1 hour max
    "max_memory_usage": int(os.environ.get("VALIDATION_MAX_MEMORY_USAGE", 512)),  # MB
    "enable_performance_monitoring": os.environ.get(
        "VALIDATION_ENABLE_PERFORMANCE_MONITORING", "true"
    ).lower()
    == "true",
    "slow_query_threshold": float(
        os.environ.get("VALIDATION_SLOW_QUERY_THRESHOLD", 5.0)
    ),  # seconds
    "enable_query_logging": os.environ.get(
        "VALIDATION_ENABLE_QUERY_LOGGING", "false"
    ).lower()
    == "true",
}

# Field mapping configurations for Salesforce to VMS
FIELD_MAPPINGS = {
    "volunteer": {
        "salesforce_individual_id": "salesforce_individual_id",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "phone": "phone",
        "organization": "salesforce_account_id",
        "status": "status",
        "skills": "skills",
        "availability": "availability",
        "engagement_level": "engagement_level",
    },
    "organization": {
        "salesforce_account_id": "salesforce_id",
        "name": "name",
        "type": "type",
        "address": "address",
        "phone": "phone",
        "website": "website",
        "status": "status",
    },
    "event": {
        "salesforce_id": "salesforce_id",
        "name": "name",
        "start_date": "start_date",
        "end_date": "end_date",
        "school": "school",
        "status": "status",
        "type": "type",
        "capacity": "capacity",
    },
    "student": {
        "salesforce_individual_id": "salesforce_individual_id",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "school": "school",
        "grade": "grade",
        "status": "status",
    },
}

# Field completeness validation rules
VALIDATION_FIELD_COMPLETENESS_RULES = {
    "required_fields": {
        "volunteer": ["Id", "FirstName", "LastName"],  # Email is often optional
        "organization": ["Name", "Type", "BillingCity", "BillingState"],
        "event": ["Subject", "StartDateTime", "EndDateTime"],
        "student": ["FirstName", "LastName", "Contact_Type__c"],
        "teacher": ["FirstName", "LastName", "Contact_Type__c", "Title"],
    },
    "field_formats": {
        "volunteer": {"Email": {"type": "email"}, "Phone": {"type": "phone"}},
        "organization": {
            "Phone": {"type": "phone"},
            "Website": {"regex": r"^https?://.*"},
        },
        "event": {"StartDateTime": {"type": "date"}, "EndDateTime": {"type": "date"}},
    },
    "field_ranges": {
        "volunteer": {
            "FirstName": {"min_length": 1, "max_length": 100},
            "LastName": {"min_length": 1, "max_length": 100},
        },
        "organization": {"Name": {"min_length": 1, "max_length": 255}},
    },
    "min_completeness_threshold": VALIDATION_THRESHOLDS["field_completeness_threshold"],
}

# Business rule definitions
BUSINESS_RULES = {
    "volunteer": {
        "required_fields": ["first_name", "last_name", "salesforce_individual_id"],
        "unique_fields": ["salesforce_individual_id", "email"],
        "status_transitions": {
            "active": ["inactive", "suspended"],
            "inactive": ["active"],
            "suspended": ["active", "inactive"],
        },
        "engagement_calculation": {
            "events_attended_weight": 0.4,
            "hours_contributed_weight": 0.3,
            "skills_matched_weight": 0.2,
            "feedback_score_weight": 0.1,
        },
    },
    "organization": {
        "required_fields": ["name", "salesforce_id"],
        "unique_fields": ["salesforce_id"],
        "status_transitions": {
            "active": ["inactive", "suspended"],
            "inactive": ["active"],
            "suspended": ["active", "inactive"],
        },
    },
    "event": {
        "required_fields": ["name", "start_date", "school"],
        "unique_fields": ["salesforce_id"],
        "date_validation": {
            "start_date_future": True,
            "end_date_after_start": True,
            "max_duration_days": 30,
        },
        "capacity_validation": {
            "min_capacity": 1,
            "max_capacity": 1000,
        },
    },
}

# Validation rule configurations
VALIDATION_RULES = {
    "count_validation": {
        "enabled": True,
        "tolerance_percentage": VALIDATION_THRESHOLDS["record_count_tolerance"],
        "max_retry_attempts": 3,
    },
    "field_completeness": {
        "enabled": True,
        "threshold_percentage": VALIDATION_THRESHOLDS["field_completeness_threshold"],
        "sample_size": 1000,  # For large datasets
    },
    "data_type_validation": {
        "enabled": True,
        "accuracy_threshold": VALIDATION_THRESHOLDS["data_type_accuracy_threshold"],
        "strict_mode": False,  # Allow some flexibility in data types
    },
    "relationship_validation": {
        "enabled": True,
        "orphaned_threshold": VALIDATION_THRESHOLDS["relationship_integrity_threshold"],
        "circular_reference_check": True,
    },
    "business_logic_validation": {
        "enabled": True,
        "status_transition_validation": True,
        "date_range_validation": True,
        "capacity_validation": True,
    },
}

# Logging configuration
LOGGING_CONFIG = {
    "level": os.environ.get("VALIDATION_LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.environ.get("VALIDATION_LOG_FILE", "logs/validation.log"),
    "max_file_size": int(os.environ.get("VALIDATION_LOG_MAX_SIZE", 10)),  # MB
    "backup_count": int(os.environ.get("VALIDATION_LOG_BACKUP_COUNT", 5)),
    "enable_structured_logging": os.environ.get(
        "VALIDATION_STRUCTURED_LOGGING", "true"
    ).lower()
    == "true",
}

# Main validation configuration dictionary
VALIDATION_CONFIG = {
    "thresholds": VALIDATION_THRESHOLDS,
    "salesforce": SALESFORCE_CONFIG,
    "redis": REDIS_CONFIG,
    "schedules": VALIDATION_SCHEDULES,
    "alerts": ALERT_CONFIG,
    "reporting": REPORTING_CONFIG,
    "performance": PERFORMANCE_CONFIG,
    "field_mappings": FIELD_MAPPINGS,
    "business_rules": BUSINESS_RULES,
    "validation_rules": VALIDATION_RULES,
    "field_completeness_rules": VALIDATION_FIELD_COMPLETENESS_RULES,
    "logging": LOGGING_CONFIG,
}


def validate_config() -> List[str]:
    """
    Validate the validation configuration and return any errors.

    Returns:
        List of error messages, empty if configuration is valid
    """
    errors = []

    # Check required Salesforce credentials
    if not SALESFORCE_CONFIG["username"]:
        errors.append("SF_USERNAME environment variable is required")
    if not SALESFORCE_CONFIG["password"]:
        errors.append("SF_PASSWORD environment variable is required")
    if not SALESFORCE_CONFIG["security_token"]:
        errors.append("SF_SECURITY_TOKEN environment variable is required")

    # Check threshold values
    if (
        VALIDATION_THRESHOLDS["record_count_tolerance"] < 0
        or VALIDATION_THRESHOLDS["record_count_tolerance"] > 100
    ):
        errors.append("VALIDATION_RECORD_COUNT_TOLERANCE must be between 0 and 100")

    if (
        VALIDATION_THRESHOLDS["field_completeness_threshold"] < 0
        or VALIDATION_THRESHOLDS["field_completeness_threshold"] > 100
    ):
        errors.append(
            "VALIDATION_FIELD_COMPLETENESS_THRESHOLD must be between 0 and 100"
        )

    # Check Redis configuration
    if REDIS_CONFIG["port"] < 1 or REDIS_CONFIG["port"] > 65535:
        errors.append("VALIDATION_REDIS_PORT must be between 1 and 65535")

    # Check schedule intervals
    if VALIDATION_SCHEDULES["fast_validation_interval"] < 60:
        errors.append("VALIDATION_FAST_INTERVAL must be at least 60 seconds")

    if VALIDATION_SCHEDULES["slow_validation_interval"] < 3600:
        errors.append("VALIDATION_SLOW_INTERVAL must be at least 3600 seconds")

    return errors


def get_config() -> Dict[str, Any]:
    """
    Get the complete validation configuration.

    Returns:
        Complete validation configuration dictionary
    """
    return VALIDATION_CONFIG.copy()


def get_config_section(section: str) -> Dict[str, Any]:
    """
    Get a specific section of the validation configuration.

    Args:
        section: Configuration section name

    Returns:
        Configuration section dictionary

    Raises:
        KeyError: If section doesn't exist
    """
    if section not in VALIDATION_CONFIG:
        raise KeyError(f"Configuration section '{section}' not found")
    return VALIDATION_CONFIG[section].copy()


# Validate configuration on import
config_errors = validate_config()
if config_errors:
    import logging

    logger = logging.getLogger(__name__)
    for error in config_errors:
        logger.error(f"Validation configuration error: {error}")
    if os.environ.get("VALIDATION_STRICT_CONFIG", "false").lower() == "true":
        raise ValueError(f"Validation configuration errors: {'; '.join(config_errors)}")
