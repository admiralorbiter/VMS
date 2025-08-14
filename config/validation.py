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

# Data type validation rules
VALIDATION_DATA_TYPE_RULES = {
    "format_validation": {
        "volunteer": {
            "Email": {
                "type": "email",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "required": False,
                "severity": "warning",
            },
            "Phone": {
                "type": "phone",
                "pattern": r"^[\+]?[1-9][\d]{0,15}$",
                "required": False,
                "severity": "info",
            },
            "FirstName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "LastName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
        },
        "organization": {
            "Name": {
                "type": "string",
                "min_length": 1,
                "max_length": 255,
                "required": True,
                "severity": "error",
            },
            "Phone": {
                "type": "phone",
                "pattern": r"^[\+]?[1-9][\d]{0,15}$",
                "required": False,
                "severity": "info",
            },
            "Website": {
                "type": "url",
                "pattern": r"^https?://.*",
                "required": False,
                "severity": "warning",
            },
            "BillingCity": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "BillingState": {
                "type": "string",
                "min_length": 2,
                "max_length": 2,
                "required": True,
                "severity": "error",
            },
        },
        "event": {
            "Subject": {
                "type": "string",
                "min_length": 1,
                "max_length": 255,
                "required": True,
                "severity": "error",
            },
            "StartDateTime": {
                "type": "datetime",
                "format": "ISO8601",
                "required": True,
                "severity": "error",
            },
            "EndDateTime": {
                "type": "datetime",
                "format": "ISO8601",
                "required": True,
                "severity": "error",
            },
        },
        "student": {
            "FirstName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "LastName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "Contact_Type__c": {
                "type": "enum",
                "allowed_values": ["Student", "Student - Active", "Student - Inactive"],
                "required": True,
                "severity": "error",
            },
        },
        "teacher": {
            "FirstName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "LastName": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "Title": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "Contact_Type__c": {
                "type": "enum",
                "allowed_values": ["Teacher", "Teacher - Active", "Teacher - Inactive"],
                "required": True,
                "severity": "error",
            },
        },
    },
    "type_consistency": {
        "enforce_strict_types": True,
        "allow_type_conversion": False,
        "null_handling": "strict",
    },
    "validation_thresholds": {
        "format_accuracy": 99.0,
        "type_consistency": 99.5,
        "overall_accuracy": 99.0,
    },
}

# Relationship integrity validation rules
VALIDATION_RELATIONSHIP_RULES = {
    "entity_relationships": {
        "volunteer": {
            "required_relationships": {
                "Contact_Type__c": {
                    "type": "picklist",
                    "required": True,
                    "severity": "error",
                    "description": "Contact type must be specified",
                }
            },
            "optional_relationships": {
                "AccountId": {
                    "type": "lookup",
                    "target_object": "Account",
                    "required": False,
                    "severity": "info",
                    "description": "Organization association is optional",
                },
                "npsp__Primary_Affiliation__c": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "Primary affiliation is optional",
                },
            },
        },
        "organization": {
            "required_relationships": {
                "Type": {
                    "type": "picklist",
                    "required": True,
                    "severity": "error",
                    "description": "Organization type must be specified",
                }
            },
            "optional_relationships": {
                "BillingCity": {
                    "type": "string",
                    "required": False,
                    "severity": "warning",
                    "description": "Billing city should be specified",
                },
                "BillingState": {
                    "type": "string",
                    "required": False,
                    "severity": "warning",
                    "description": "Billing state should be specified",
                },
            },
        },
        "event": {
            "required_relationships": {
                "Subject": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "Event subject is required",
                },
                "StartDateTime": {
                    "type": "datetime",
                    "required": True,
                    "severity": "error",
                    "description": "Start date/time is required",
                },
            },
            "optional_relationships": {
                "Location": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "Event location is optional",
                }
            },
        },
        "student": {
            "required_relationships": {
                "Contact_Type__c": {
                    "type": "picklist",
                    "required": True,
                    "severity": "error",
                    "description": "Student contact type must be specified",
                },
                "FirstName": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "First name is required",
                },
                "LastName": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "Last name is required",
                },
            },
            "optional_relationships": {
                "AccountId": {
                    "type": "lookup",
                    "target_object": "Account",
                    "required": False,
                    "severity": "info",
                    "description": "School/organization association is optional",
                }
            },
        },
        "teacher": {
            "required_relationships": {
                "Contact_Type__c": {
                    "type": "picklist",
                    "required": True,
                    "severity": "error",
                    "description": "Teacher contact type must be specified",
                },
                "Title": {
                    "type": "string",
                    "required": False,  # Changed to False since not all teachers have titles
                    "severity": "warning",
                    "description": "Job title should be specified",
                },
            },
            "optional_relationships": {
                "AccountId": {
                    "type": "lookup",
                    "target_object": "Account",
                    "required": False,
                    "severity": "info",
                    "description": "School/organization association is optional",
                }
            },
        },
    },
    "relationship_validation": {
        "orphaned_record_detection": True,
        "circular_reference_detection": True,
        "foreign_key_validation": True,
        "relationship_completeness_checks": True,
        "max_relationship_depth": 3,
        "validation_thresholds": {
            "relationship_completeness": 80.0,  # Lowered threshold since some relationships are optional
            "orphaned_records": 20.0,  # Increased threshold since not all volunteers need organizations
            "circular_references": 0.0,
        },
    },
    "business_rules": {
        "volunteer_organization_rule": "Volunteers may be associated with organizations but it's not required",
        "event_volunteer_rule": "Events can have multiple volunteer registrations",
        "student_teacher_rule": "Students can be assigned to teachers, teachers can have multiple students",
        "organization_type_rule": "Organizations should have valid types and addresses when possible",
    },
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

# Business rule validation rules
VALIDATION_BUSINESS_RULES = {
    "validation_settings": {
        "enable_status_transition_validation": True,
        "enable_date_range_validation": True,
        "enable_capacity_limit_validation": True,
        "enable_business_constraint_validation": True,
        "enable_workflow_validation": True,
        "enable_data_quality_scoring": True,
        "enable_trend_analysis": True,
        "enable_custom_rules": True,
        "validation_thresholds": {
            "min_success_rate": 80.0,
            "max_warning_rate": 15.0,
            "max_error_rate": 5.0,
        },
        "quality_scoring": {
            "critical_violation_weight": 10.0,
            "error_violation_weight": 5.0,
            "warning_violation_weight": 2.0,
            "info_violation_weight": 0.5,
            "base_score": 100.0,
            "min_acceptable_score": 70.0,
        },
        "performance": {
            "max_parallel_validators": 4,
            "enable_caching": True,
            "cache_ttl_seconds": 3600,
            "smart_sampling_enabled": True,
            "max_sample_size": 1000,
            "min_sample_size": 100,
        },
    },
    "custom_rules": {
        "rule_sources": ["config/validation.py", "rules/external/", "rules/dynamic/"],
        "rule_templates": {
            "field_required_when": {
                "type": "cross_field",
                "description": "Field is required when another field has specific value",
                "parameters": ["if_field", "if_value", "then_field", "then_required"],
            },
            "numeric_range": {
                "type": "business_constraint",
                "description": "Numeric field must be within specified range",
                "parameters": ["field_name", "min_value", "max_value", "severity"],
            },
            "date_sequence": {
                "type": "date_range",
                "description": "Date fields must follow logical sequence",
                "parameters": [
                    "start_field",
                    "end_field",
                    "min_duration",
                    "max_duration",
                ],
            },
        },
        "rule_versioning": {
            "enabled": True,
            "track_changes": True,
            "impact_analysis": True,
        },
    },
    "trend_analysis": {
        "enabled": True,
        "analysis_periods": ["daily", "weekly", "monthly"],
        "metrics_to_track": [
            "overall_quality_score",
            "critical_violations",
            "error_violations",
            "warning_violations",
            "success_rate",
        ],
        "alerting": {
            "quality_decline_threshold": 5.0,  # 5% decline triggers alert
            "violation_spike_threshold": 20.0,  # 20% increase triggers alert
            "trend_detection_window": 7,  # days
        },
    },
    "business_rules": {
        "volunteer": {
            "contact_type_validation": {
                "type": "business_constraint",
                "field_name": "Contact_Type__c",
                "allowed_values": ["Volunteer", "Student", "Teacher", "Staff"],
                "severity": "warning",
                "description": "Contact type must be from predefined list",
            },
            "organization_association_validation": {
                "type": "business_constraint",
                "field_name": "AccountId",
                "min_value": 1,  # Should have a valid organization ID
                "severity": "info",
                "description": "Volunteer should be associated with an organization",
            },
            "name_validation": {
                "type": "business_constraint",
                "field_name": "FirstName",
                "min_value": 1,  # Minimum characters
                "max_value": 50,  # Maximum characters
                "required": True,  # Required field
                "severity": "warning",
                "description": "First name should have reasonable length",
            },
            "email_format_validation": {
                "type": "business_constraint",
                "field_name": "Email",
                "min_value": 1,  # Should have email if provided
                "max_value": 100,  # Maximum email length
                "required": False,  # Not required but should be valid if present
                "severity": "info",
                "description": "Email should have reasonable format and length",
            },
            "status_transition_validation": {
                "type": "status_transition",
                "status_field": "Status__c",
                "allowed_transitions": {
                    "Active": ["Inactive", "Suspended"],
                    "Inactive": ["Active"],
                    "Suspended": ["Active", "Inactive"],
                },
                "severity": "warning",
                "description": "Volunteer status transitions must follow business logic",
            },
            "cross_field_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Contact_Type__c",
                        "if_value": "Volunteer",
                        "then_field": "Volunteer_Skills__c",
                        "then_required": True,
                        "message": "Volunteers must have skills specified",
                    },
                    {
                        "if_field": "Contact_Type__c",
                        "if_value": "Volunteer",
                        "then_field": "Availability__c",
                        "then_required": True,
                        "message": "Volunteers must specify availability",
                    },
                ],
                "severity": "warning",
                "description": "Cross-field validation for volunteer requirements",
            },
            "workflow_validation": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "Registration",
                        "required_fields": ["FirstName", "Email", "Contact_Type__c"],
                        "next_steps": ["Background_Check", "Skills_Assessment"],
                    },
                    {
                        "step": "Background_Check",
                        "required_fields": ["Background_Check_Status__c"],
                        "next_steps": ["Approval", "Rejection"],
                        "depends_on": "Registration",
                    },
                    {
                        "step": "Skills_Assessment",
                        "required_fields": ["Volunteer_Skills__c"],
                        "next_steps": ["Approval", "Training_Required"],
                        "depends_on": "Registration",
                    },
                    {
                        "step": "Approval",
                        "required_fields": ["Approval_Date__c", "Approved_By__c"],
                        "next_steps": ["Active"],
                        "depends_on": ["Background_Check", "Skills_Assessment"],
                    },
                ],
                "severity": "warning",
                "description": "Volunteer onboarding workflow validation",
            },
        },
        "organization": {
            "type_validation": {
                "type": "business_constraint",
                "field_name": "Type",
                "allowed_values": [
                    "School",
                    "Non-Profit",
                    "Government",
                    "Corporate",
                    "Community",
                ],
                "severity": "warning",
                "description": "Organization type must be from predefined list",
            },
            "name_validation": {
                "type": "business_constraint",
                "field_name": "Name",
                "min_value": 2,  # Minimum characters
                "max_value": 100,  # Maximum characters
                "severity": "warning",
                "description": "Organization name should have reasonable length",
            },
            "address_validation": {
                "type": "business_constraint",
                "field_name": "BillingCity",
                "min_value": 1,  # Should have city if provided
                "max_value": 50,  # Maximum city name length
                "severity": "info",
                "description": "Billing city should have reasonable length",
            },
            "status_transition_validation": {
                "type": "status_transition",
                "status_field": "Status__c",
                "allowed_transitions": {
                    "Active": ["Inactive", "Suspended"],
                    "Inactive": ["Active"],
                    "Suspended": ["Active", "Inactive"],
                },
                "severity": "warning",
                "description": "Organization status transitions must follow business logic",
            },
            "cross_field_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Type",
                        "if_value": "School",
                        "then_field": "School_District__c",
                        "then_required": True,
                        "message": "Schools must specify school district",
                    },
                    {
                        "if_field": "Type",
                        "if_value": "Non-Profit",
                        "then_field": "Tax_ID__c",
                        "then_required": True,
                        "message": "Non-profits must have tax ID",
                    },
                ],
                "severity": "warning",
                "description": "Cross-field validation for organization requirements",
            },
        },
        "event": {
            "subject_validation": {
                "type": "business_constraint",
                "field_name": "Subject",
                "min_value": 5,  # Minimum characters for meaningful subject
                "max_value": 200,  # Maximum subject length
                "severity": "warning",
                "description": "Event subject should have reasonable length",
            },
            "start_date_validation": {
                "type": "business_constraint",
                "field_name": "StartDateTime",
                "min_value": 1,  # Should have start date
                "severity": "error",
                "description": "Event must have a start date",
            },
            "location_validation": {
                "type": "business_constraint",
                "field_name": "Location",
                "min_value": 1,  # Minimum characters
                "max_value": 200,  # Maximum location length
                "severity": "info",
                "description": "Event location should have reasonable length",
            },
            "date_range_validation": {
                "type": "date_range",
                "start_field": "StartDateTime",
                "end_field": "EndDateTime",
                "min_duration_days": 0.1,  # 2.4 hours minimum
                "max_duration_days": 30,  # 30 days maximum
                "severity": "error",
                "description": "Event dates must be logical with reasonable duration",
            },
            "capacity_validation": {
                "type": "capacity_limit",
                "capacity_field": "Max_Volunteers__c",
                "current_field": "Registered_Volunteers__c",
                "max_capacity": 1000,
                "severity": "warning",
                "description": "Event capacity must be reasonable and not exceeded",
            },
            "cross_field_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Event_Type__c",
                        "if_value": "Virtual",
                        "then_field": "Virtual_Platform__c",
                        "then_required": True,
                        "message": "Virtual events must specify platform",
                    },
                    {
                        "if_field": "Event_Type__c",
                        "if_value": "In-Person",
                        "then_field": "Location",
                        "then_required": True,
                        "message": "In-person events must have location",
                    },
                ],
                "severity": "warning",
                "description": "Cross-field validation for event requirements",
            },
            "workflow_validation": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "Planning",
                        "required_fields": [
                            "Subject",
                            "StartDateTime",
                            "Event_Type__c",
                        ],
                        "next_steps": ["Approval", "Cancelled"],
                    },
                    {
                        "step": "Approval",
                        "required_fields": ["Approved_By__c", "Approval_Date__c"],
                        "next_steps": ["Registration_Open", "Cancelled"],
                        "depends_on": "Planning",
                    },
                    {
                        "step": "Registration_Open",
                        "required_fields": [
                            "Max_Volunteers__c",
                            "Registration_Deadline__c",
                        ],
                        "next_steps": ["Registration_Closed", "Cancelled"],
                        "depends_on": "Approval",
                    },
                    {
                        "step": "Registration_Closed",
                        "required_fields": ["Registered_Volunteers__c"],
                        "next_steps": ["Event_Execution", "Cancelled"],
                        "depends_on": "Registration_Open",
                    },
                    {
                        "step": "Event_Execution",
                        "required_fields": ["Actual_Start_Time__c"],
                        "next_steps": ["Completed", "Cancelled"],
                        "depends_on": "Registration_Closed",
                    },
                ],
                "severity": "warning",
                "description": "Event lifecycle workflow validation",
            },
        },
        "student": {
            "contact_type_validation": {
                "type": "business_constraint",
                "field_name": "Contact_Type__c",
                "allowed_values": ["Student", "Volunteer", "Teacher", "Staff"],
                "severity": "warning",
                "description": "Student contact type must be valid",
            },
            "name_validation": {
                "type": "business_constraint",
                "field_name": "FirstName",
                "min_value": 1,  # Minimum characters
                "max_value": 50,  # Maximum characters
                "required": True,  # Required field
                "severity": "warning",
                "description": "Student first name should have reasonable length",
            },
            "organization_association_validation": {
                "type": "business_constraint",
                "field_name": "AccountId",
                "min_value": 1,  # Should have a valid school ID
                "required": True,  # Required field
                "severity": "warning",
                "description": "Student should be associated with a school",
            },
            "enrollment_validation": {
                "type": "date_range",
                "start_field": "Enrollment_Date__c",
                "end_field": "Graduation_Date__c",
                "min_duration_days": 30,  # Minimum 1 month
                "max_duration_days": 2555,  # Maximum 7 years (K-12)
                "severity": "warning",
                "description": "Student enrollment period must be reasonable",
            },
            "cross_field_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Grade_Level__c",
                        "if_value": "K",
                        "then_field": "Age__c",
                        "then_min_value": 4,
                        "then_max_value": 6,
                        "message": "Kindergarten students should be 4-6 years old",
                    },
                    {
                        "if_field": "Grade_Level__c",
                        "if_value": "12",
                        "then_field": "Age__c",
                        "then_min_value": 16,
                        "then_max_value": 19,
                        "message": "12th grade students should be 16-19 years old",
                    },
                ],
                "severity": "warning",
                "description": "Cross-field validation for student age/grade consistency",
            },
        },
        "teacher": {
            "contact_type_validation": {
                "type": "business_constraint",
                "field_name": "Contact_Type__c",
                "allowed_values": ["Teacher", "Volunteer", "Student", "Staff"],
                "severity": "warning",
                "description": "Teacher contact type must be valid",
            },
            "name_validation": {
                "type": "business_constraint",
                "field_name": "FirstName",
                "min_value": 1,  # Minimum characters
                "max_value": 50,  # Maximum characters
                "required": True,  # Required field
                "severity": "warning",
                "description": "Teacher first name should have reasonable length",
            },
            "organization_association_validation": {
                "type": "business_constraint",
                "field_name": "AccountId",
                "min_value": 1,  # Should have a valid school ID
                "required": True,  # Required field
                "severity": "warning",
                "description": "Teacher should be associated with a school",
            },
            "title_validation": {
                "type": "business_constraint",
                "field_name": "Title",
                "min_value": 2,  # Minimum characters
                "max_value": 100,  # Maximum characters
                "required": False,  # Not required but should be valid if present
                "severity": "info",
                "description": "Teacher title should have reasonable length",
            },
            "cross_field_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "Title",
                        "if_value": "Principal",
                        "then_field": "Years_Experience__c",
                        "then_min_value": 5,
                        "message": "Principals should have at least 5 years experience",
                    },
                    {
                        "if_field": "Title",
                        "if_value": "Substitute",
                        "then_field": "Certification_Status__c",
                        "then_required": True,
                        "message": "Substitute teachers must have certification status",
                    },
                ],
                "severity": "warning",
                "description": "Cross-field validation for teacher qualifications",
            },
        },
    },
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
    "data_type_rules": VALIDATION_DATA_TYPE_RULES,
    "relationship_rules": VALIDATION_RELATIONSHIP_RULES,
    "business_rules": VALIDATION_BUSINESS_RULES,  # NEW
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
