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

# Flask-Caching settings (Redis not used in this project)
CACHE_CONFIG = {
    "cache_type": "simple",  # Use simple memory cache
    "cache_default_timeout": int(
        os.environ.get("VALIDATION_CACHE_TTL", 3600)
    ),  # 1 hour default
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
        "title": "title",
        "start_date": "start_date",
        "end_date": "end_date",
        "school": "school",
        "status": "status",
        "type": "type",
        "format": "format",
        "location": "location",
        "description": "description",
        "duration": "duration",
        "participant_count": "participant_count",
        "volunteers_needed": "volunteers_needed",
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
        "organization": ["Name"],  # Type, BillingCity, BillingState are optional
        "event": [
            "title",
            "type",
            "format",
            "start_date",
            "end_date",
            "status",
        ],  # All required fields from EventForm
        "student": [
            "first_name",
            "last_name",
        ],  # Only first_name and last_name are required
        "teacher": [
            "first_name",
            "last_name",
        ],  # Only first_name and last_name are required
        "school": ["id", "name"],  # Only id and name are required
        "district": ["id", "name"],  # Only id and name are required
    },
    "field_formats": {
        "volunteer": {"Email": {"type": "email"}, "Phone": {"type": "phone"}},
        "organization": {
            "Phone": {"type": "phone"},
            "Website": {"regex": r"^https?://.*"},
        },
        "event": {
            "title": {"type": "string", "min_length": 1, "max_length": 255},
            "type": {
                "type": "enum",
                "values": [
                    "IN_PERSON",
                    "VIRTUAL_SESSION",
                    "CONNECTOR_SESSION",
                    "CAREER_FAIR",
                    "CLASSROOM_SPEAKER",
                    "MENTORING",
                    "INTERNSHIP",
                ],
            },
            "format": {"type": "enum", "values": ["IN_PERSON", "VIRTUAL"]},
            "start_date": {"type": "datetime"},
            "end_date": {"type": "datetime"},
            "status": {
                "type": "enum",
                "values": [
                    "Draft",
                    "Requested",
                    "Confirmed",
                    "Published",
                    "Completed",
                    "Cancelled",
                    "No Show",
                    "Simulcast",
                    "Count",
                ],
            },
        },  # All required fields with proper validation
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
                "required": False,  # Address fields are optional
                "severity": "info",
            },
            "BillingState": {
                "type": "string",
                "min_length": 2,
                "max_length": 2,
                "required": False,  # Address fields are optional
                "severity": "info",
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
            "first_name": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "last_name": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "current_grade": {
                "type": "integer",
                "min_value": 0,
                "max_value": 12,
                "required": False,
                "severity": "info",
            },
            "student_id": {
                "type": "string",
                "max_length": 50,
                "required": False,
                "severity": "info",
            },
        },
        "teacher": {
            "first_name": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "last_name": {
                "type": "string",
                "min_length": 1,
                "max_length": 100,
                "required": True,
                "severity": "error",
            },
            "status": {
                "type": "enum",
                "allowed_values": ["active", "inactive", "on_leave", "retired"],
                "required": False,
                "severity": "warning",
            },
            "department": {
                "type": "string",
                "max_length": 50,
                "required": False,
                "severity": "info",
            },
            "connector_role": {
                "type": "string",
                "max_length": 50,
                "required": False,
                "severity": "info",
            },
        },
        "school": {
            "id": {
                "type": "string",
                "min_length": 15,
                "max_length": 18,
                "required": True,
                "severity": "error",
                "pattern": r"^[a-zA-Z0-9]{15,18}$",  # Salesforce ID format
                "description": "School Salesforce ID must be 15-18 alphanumeric characters",
            },
            "name": {
                "type": "string",
                "min_length": 2,
                "max_length": 255,
                "required": True,
                "severity": "error",
                "no_whitespace_only": True,
                "description": "School name must be 2-255 characters and not whitespace only",
            },
            "level": {
                "type": "enum",
                "allowed_values": ["Elementary", "Middle", "High", "Other"],
                "required": False,
                "severity": "info",
                "description": "School level must be one of the allowed values",
            },
            "school_code": {
                "type": "string",
                "max_length": 50,
                "required": False,
                "severity": "info",
                "description": "School code must be 50 characters or less",
            },
            "district_id": {
                "type": "integer",
                "required": False,
                "severity": "info",
                "description": "District ID must be a valid integer",
            },
        },
        "district": {
            "id": {
                "type": "integer",
                "required": True,
                "severity": "error",
                "auto_increment": True,
                "description": "District ID must be an auto-incrementing integer",
            },
            "name": {
                "type": "string",
                "min_length": 2,
                "max_length": 255,
                "required": True,
                "severity": "error",
                "no_whitespace_only": True,
                "description": "District name must be 2-255 characters and not whitespace only",
            },
            "district_code": {
                "type": "string",
                "max_length": 20,
                "required": False,
                "severity": "info",
                "description": "District code must be 20 characters or less",
            },
            "salesforce_id": {
                "type": "string",
                "min_length": 15,
                "max_length": 18,
                "required": False,
                "severity": "info",
                "pattern": r"^[a-zA-Z0-9]{15,18}$",  # Salesforce ID format
                "description": "District Salesforce ID must be 15-18 alphanumeric characters",
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
                "first_name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "First name is required",
                },
                "last_name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "Last name is required",
                },
            },
            "optional_relationships": {
                "school_id": {
                    "type": "lookup",
                    "target_object": "School",
                    "required": False,
                    "severity": "info",
                    "description": "School association is optional",
                },
                "teacher_id": {
                    "type": "lookup",
                    "target_object": "Teacher",
                    "required": False,
                    "severity": "info",
                    "description": "Teacher assignment is optional",
                },
                "class_salesforce_id": {
                    "type": "lookup",
                    "target_object": "Class",
                    "required": False,
                    "severity": "info",
                    "description": "Class assignment is optional",
                },
            },
        },
        "teacher": {
            "required_relationships": {
                "first_name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "First name is required",
                },
                "last_name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "Last name is required",
                },
            },
            "optional_relationships": {
                "school_id": {
                    "type": "lookup",
                    "target_object": "School",
                    "required": False,
                    "severity": "info",
                    "description": "School association is optional",
                },
                "department": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "Department assignment is optional",
                },
                "connector_role": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "Connector program role is optional",
                },
            },
        },
        "school": {
            "required_relationships": {
                "name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "School name is required",
                },
                "id": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "School Salesforce ID is required",
                },
            },
            "optional_relationships": {
                "district_id": {
                    "type": "foreign_key",
                    "target_object": "District",
                    "target_field": "id",
                    "required": False,
                    "severity": "info",
                    "description": "District association is optional but must be valid if present",
                },
                "level": {
                    "type": "enum",
                    "allowed_values": ["Elementary", "Middle", "High", "Other"],
                    "required": False,
                    "severity": "info",
                    "description": "School level categorization is optional",
                },
            },
            "relationship_integrity": {
                "district_reference": {
                    "type": "foreign_key_check",
                    "source_field": "district_id",
                    "target_table": "district",
                    "target_field": "id",
                    "severity": "warning",
                    "description": "School district_id must reference valid district.id",
                }
            },
        },
        "district": {
            "required_relationships": {
                "name": {
                    "type": "string",
                    "required": True,
                    "severity": "error",
                    "description": "District name is required",
                },
                "id": {
                    "type": "integer",
                    "required": True,
                    "severity": "error",
                    "description": "District internal ID is required",
                },
            },
            "optional_relationships": {
                "salesforce_id": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "Salesforce ID is optional",
                },
                "district_code": {
                    "type": "string",
                    "required": False,
                    "severity": "info",
                    "description": "District code is optional",
                },
            },
            "relationship_integrity": {
                "schools_reference": {
                    "type": "reverse_foreign_key_check",
                    "source_table": "school",
                    "source_field": "district_id",
                    "target_field": "id",
                    "severity": "info",
                    "description": "District can have multiple schools referencing it",
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
        "required_fields": ["first_name", "last_name"],
        "form_required_fields": ["first_name", "last_name", "email"],
        "unique_fields": ["salesforce_individual_id"],
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
        "required_fields": ["name"],
        "unique_fields": ["salesforce_id"],
        "type_validation": {
            "allowed_types": [
                "School",
                "Business",
                "Non-profit",
                "Government",
                "Other",
            ],
            "description": "Organization type must be one of the predefined values",
        },
        "address_validation": {
            "city_state_consistency": True,
            "postal_code_format": True,
            "country_validation": True,
        },
        "volunteer_relationship_validation": {
            "max_volunteers_per_org": 1000,
            "primary_organization_limit": 1,
            "relationship_status_required": True,
        },
        "salesforce_integration": {
            "import_strategy": "selective",
            "exclude_types": ["Draft", "Test"],
            "required_fields_on_import": ["name", "type"],
        },
    },
    "event": {
        "required_fields": ["title", "start_date", "format", "status"],
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
    "school": {
        "required_fields": ["id", "name"],
        "unique_fields": ["id"],
        "field_validation": {
            "level": {
                "allowed_values": ["Elementary", "Middle", "High", "Other"],
                "required": False,
            },
            "school_code": {
                "max_length": 50,
                "required": False,
            },
        },
        "relationship_validation": {
            "district_id": {
                "target_table": "district",
                "required": False,
                "cascade_delete": False,
            }
        },
    },
    "district": {
        "required_fields": ["id", "name"],
        "unique_fields": ["id", "salesforce_id"],
        "field_validation": {
            "district_code": {
                "max_length": 20,
                "required": False,
            },
            "salesforce_id": {
                "format": "salesforce_id",
                "required": False,
            },
        },
        "relationship_validation": {
            "schools": {
                "target_table": "school",
                "relationship_type": "one_to_many",
                "cascade_delete": True,
            }
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
        "enable_cross_field_validation": True,
        "enable_workflow_validation": True,
    },
    "business_rules": {
        "volunteer": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["first_name", "last_name", "email"],
                "required": True,
                "severity": "error",
                "description": "First name, last name, and email are required fields for volunteers",
            }
        },
        "organization": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["name"],
                "required": True,
                "severity": "error",
                "description": "Organization name is required",
            },
            "organization_type_validation": {
                "type": "business_constraint",
                "fields": ["type"],
                "allowed_values": [
                    "School",
                    "Business",
                    "Non-profit",
                    "Government",
                    "Other",
                ],
                "severity": "warning",
                "description": "Organization type should be one of the predefined values",
            },
            "address_consistency_validation": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "billing_city",
                        "then_field": "billing_state",
                        "validation": "both_or_neither",
                        "message": "If city is provided, state should also be provided",
                        "severity": "warning",
                    },
                    {
                        "if_field": "billing_state",
                        "then_field": "billing_postal_code",
                        "validation": "state_requires_postal",
                        "message": "State requires postal code for proper addressing",
                        "severity": "info",
                    },
                ],
                "severity": "info",
                "description": "Address field consistency validation",
            },
            "volunteer_relationship_validation": {
                "type": "business_constraint",
                "fields": ["volunteer_organizations"],
                "rules": {"max_volunteers": 1000, "primary_org_limit": 1},
                "severity": "warning",
                "description": "Volunteer-organization relationship validation",
            },
            "salesforce_import_validation": {
                "type": "business_constraint",
                "fields": ["salesforce_id"],
                "rules": {
                    "import_required_fields": ["name", "type"],
                    "exclude_patterns": ["Draft", "Test", "Sample"],
                },
                "severity": "info",
                "description": "Salesforce import strategy validation",
            },
        },
        "teacher": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["first_name", "last_name"],
                "required": True,
                "severity": "error",
                "description": "First name and last name are required for teachers",
            },
            "teacher_status_workflow": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "basic_info",
                        "required_fields": ["first_name", "last_name"],
                        "description": "Basic teacher information required",
                    },
                    {
                        "step": "status_assignment",
                        "required_fields": ["status"],
                        "description": "Teacher status assignment",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "school_assignment",
                        "required_fields": [],
                        "description": "School assignment is optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "department_assignment",
                        "required_fields": [],
                        "description": "Department assignment is optional",
                        "depends_on": ["basic_info"],
                    },
                ],
                "severity": "info",
                "description": "Teacher onboarding workflow validation",
            },
            "teacher_status_validation": {
                "type": "business_constraint",
                "fields": ["status"],
                "rules": {
                    "allowed_values": ["active", "inactive", "on_leave", "retired"],
                    "status_transitions": {
                        "active": ["inactive", "on_leave", "retired"],
                        "inactive": ["active", "retired"],
                        "on_leave": ["active", "inactive", "retired"],
                        "retired": [],
                    },
                },
                "severity": "warning",
                "description": "Teacher status must be valid and follow transition rules",
            },
            "connector_program_validation": {
                "type": "business_constraint",
                "fields": [
                    "connector_role",
                    "connector_active",
                    "connector_start_date",
                    "connector_end_date",
                ],
                "rules": {
                    "role_capitalization": True,
                    "date_range_validation": True,
                    "active_status_consistency": True,
                },
                "severity": "warning",
                "description": "Connector program participation validation",
            },
            "school_relationship_validation": {
                "type": "business_constraint",
                "fields": ["school_id"],
                "rules": {
                    "school_id_format": "salesforce_id",
                    "relationship_optional": True,
                    "cascade_delete": False,
                },
                "severity": "info",
                "description": "Teacher-school relationship validation",
            },
        },
        "student": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["first_name", "last_name"],
                "required": True,
                "severity": "error",
                "description": "First name and last name are required for students",
            },
            "student_enrollment_workflow": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "basic_info",
                        "required_fields": ["first_name", "last_name"],
                        "description": "Basic student information required",
                    },
                    {
                        "step": "academic_info",
                        "required_fields": [],
                        "description": "Academic information is optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "school_assignment",
                        "required_fields": [],
                        "description": "School assignment is optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "demographic_info",
                        "required_fields": [],
                        "description": "Demographic information is optional",
                        "depends_on": ["basic_info"],
                    },
                ],
                "severity": "info",
                "description": "Student enrollment workflow validation",
            },
            "grade_level_validation": {
                "type": "business_constraint",
                "fields": ["current_grade"],
                "rules": {
                    "min_grade": 0,
                    "max_grade": 12,
                    "grade_progression": "sequential",
                },
                "severity": "warning",
                "description": "Grade level must be between 0-12",
            },
            "student_id_uniqueness": {
                "type": "business_constraint",
                "fields": ["student_id"],
                "rules": {"unique_per_school": True, "format": "alphanumeric"},
                "severity": "warning",
                "description": "Student ID should be unique within school",
            },
            "academic_relationship_validation": {
                "type": "business_constraint",
                "fields": ["school_id", "teacher_id", "class_salesforce_id"],
                "rules": {
                    "school_required_for_grade": False,
                    "teacher_required_for_class": False,
                    "class_required_for_attendance": False,
                },
                "severity": "info",
                "description": "Academic relationships are optional but should be consistent",
            },
        },
        "event": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["title", "start_date"],
                "required": True,
                "severity": "error",
                "description": "Event title and start date are required",
            }
        },
        "school": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["id", "name"],
                "required": True,
                "severity": "error",
                "description": "School ID and name are required fields",
            },
            "field_format_validation": {
                "type": "business_constraint",
                "fields": ["id", "name", "level", "school_code"],
                "rules": {
                    "id": {
                        "format": "salesforce_id",
                        "min_length": 15,
                        "max_length": 18,
                    },
                    "name": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                    },
                    "level": {
                        "allowed_values": ["Elementary", "Middle", "High", "Other"],
                        "required": False,
                    },
                    "school_code": {"max_length": 50, "required": False},
                },
                "severity": "warning",
                "description": "School field format validation",
            },
            "data_quality_validation": {
                "type": "business_constraint",
                "fields": ["name"],
                "rules": {
                    "name": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "pattern": r"^[A-Za-z0-9\s\-\.']+$",
                    }
                },
                "severity": "warning",
                "description": "School name quality validation",
            },
            "level_validation": {
                "type": "business_constraint",
                "fields": ["level"],
                "rules": {
                    "level": {
                        "allowed_values": ["Elementary", "Middle", "High", "Other"],
                        "required": False,
                    }
                },
                "severity": "info",
                "description": "School level validation",
            },
            "naming_convention_validation": {
                "type": "business_constraint",
                "fields": ["name"],
                "rules": {
                    "name": {
                        "pattern": r"^(?!.*\b(?:School|Elementary|Middle|High|Academy|Institute)\b).*$",
                        "required": False,
                    }
                },
                "severity": "warning",
                "description": "School name should not contain generic terms like 'School', 'Elementary', etc.",
            },
            "relationship_validation": {
                "type": "business_constraint",
                "fields": ["district_id"],
                "rules": {
                    "district_id": {
                        "type": "foreign_key",
                        "target": "district.id",
                        "required": False,
                    }
                },
                "severity": "info",
                "description": "School district relationship validation",
            },
        },
        "district": {
            "required_fields_validation": {
                "type": "business_constraint",
                "fields": ["id", "name"],
                "required": True,
                "severity": "error",
                "description": "District ID and name are required fields",
            },
            "field_format_validation": {
                "type": "business_constraint",
                "fields": ["name", "district_code", "salesforce_id"],
                "rules": {
                    "name": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                    },
                    "district_code": {"max_length": 20, "required": False},
                    "salesforce_id": {
                        "format": "salesforce_id",
                        "min_length": 15,
                        "max_length": 18,
                        "required": False,
                    },
                },
                "severity": "warning",
                "description": "District field format validation",
            },
            "data_quality_validation": {
                "type": "business_constraint",
                "fields": ["name"],
                "rules": {
                    "name": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "pattern": r"^[A-Za-z0-9\s\-\.']+$",
                    }
                },
                "severity": "warning",
                "description": "District name quality validation",
            },
            "code_validation": {
                "type": "business_constraint",
                "fields": ["district_code"],
                "rules": {
                    "district_code": {
                        "max_length": 20,
                        "pattern": r"^[A-Z0-9\-_]*$",
                        "required": False,
                    }
                },
                "severity": "info",
                "description": "District code format validation",
            },
            "relationship_validation": {
                "type": "business_constraint",
                "fields": ["id"],
                "rules": {"id": {"type": "primary_key", "auto_increment": True}},
                "severity": "info",
                "description": "District primary key validation",
            },
        },
        "event": {
            "event_status_transitions": {
                "type": "status_transition",
                "status_field": "status",
                "allowed_transitions": {
                    "Draft": ["Requested", "Cancelled"],
                    "Requested": ["Confirmed", "Cancelled"],
                    "Confirmed": ["Published", "Cancelled"],
                    "Published": ["Completed", "Cancelled"],
                    "Completed": ["Cancelled"],
                    "Cancelled": [],
                    "No Show": ["Cancelled"],
                    "Simulcast": ["Completed", "Cancelled"],
                },
                "invalid_transitions": {
                    "Completed": ["Draft", "Requested", "Confirmed", "Published"],
                    "Cancelled": [
                        "Draft",
                        "Requested",
                        "Confirmed",
                        "Published",
                        "Completed",
                    ],
                },
                "severity": "error",
                "description": "VMS Event status transition validation",
            },
            "event_data_consistency": {
                "type": "cross_field",
                "field_rules": [
                    {
                        "if_field": "start_date",
                        "then_field": "end_date",
                        "validation": "end_date_after_start",
                        "message": "End date must be after start date",
                        "severity": "error",
                    },
                    {
                        "if_field": "registered_count",
                        "then_field": "attended_count",
                        "validation": "attended_less_than_registered",
                        "message": "Attended count cannot exceed registered count",
                        "severity": "error",
                    },
                ],
                "severity": "error",
                "description": "VMS Event data consistency validation",
            },
            "event_field_format_validation": {
                "type": "business_constraint",
                "fields": [
                    "title",
                    "start_date",
                    "end_date",
                    "location",
                    "description",
                ],
                "rules": {
                    "title": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "pattern": r"^[A-Za-z0-9\s\-\.'&()]+$",
                    },
                    "start_date": {
                        "format": "datetime",
                        "timezone_aware": True,
                        "future_date_allowed": True,
                    },
                    "end_date": {
                        "format": "datetime",
                        "timezone_aware": True,
                        "after_start_date": True,
                    },
                    "location": {
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "pattern": r"^[A-Za-z0-9\s\-\.',&()]+$",
                    },
                    "description": {
                        "max_length": 10000,
                        "no_whitespace_only": True,
                    },
                },
                "severity": "warning",
                "description": "VMS Event field format validation",
            },
            "event_data_quality_validation": {
                "type": "business_constraint",
                "fields": ["title", "location", "description"],
                "rules": {
                    "title": {
                        "min_length": 2,
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "descriptive_required": True,
                    },
                    "location": {
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "address_format": True,
                    },
                    "description": {
                        "max_length": 10000,
                        "no_whitespace_only": True,
                        "content_quality": True,
                    },
                },
                "severity": "warning",
                "description": "VMS Event data quality validation",
            },
            "event_capacity_validation": {
                "type": "business_constraint",
                "fields": [
                    "volunteers_needed",
                    "participant_count",
                    "registered_count",
                    "attended_count",
                    "available_slots",
                ],
                "rules": {
                    "volunteers_needed": {
                        "min_value": 0,
                        "max_value": 1000,
                        "non_negative": True,
                    },
                    "participant_count": {
                        "min_value": 0,
                        "max_value": 10000,
                        "non_negative": True,
                    },
                    "registered_count": {
                        "min_value": 0,
                        "max_value": 10000,
                        "non_negative": True,
                    },
                    "attended_count": {
                        "min_value": 0,
                        "max_value": 10000,
                        "non_negative": True,
                        "less_than_registered": True,
                    },
                    "available_slots": {
                        "min_value": 0,
                        "max_value": 10000,
                        "non_negative": True,
                    },
                },
                "severity": "warning",
                "description": "VMS Event capacity and participant validation",
            },
            "event_workflow_validation": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "basic_info",
                        "required_fields": ["title", "start_date", "format", "status"],
                        "description": "Basic event information required",
                    },
                    {
                        "step": "timing_details",
                        "required_fields": [],
                        "description": "End date and duration are optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "location_info",
                        "required_fields": [],
                        "description": "Location and school assignment are optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "capacity_planning",
                        "required_fields": [],
                        "description": "Volunteer and participant capacity planning",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "skills_assignment",
                        "required_fields": [],
                        "description": "Skills and requirements assignment",
                        "depends_on": ["basic_info"],
                    },
                ],
                "severity": "info",
                "description": "VMS Event creation and management workflow validation",
            },
            "event_skills_validation": {
                "type": "business_constraint",
                "fields": ["skills"],
                "rules": {
                    "skills": {
                        "max_skills_per_event": 20,
                        "skill_name_format": "alphanumeric_with_spaces",
                        "duplicate_prevention": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event skills validation",
            },
            "event_location_validation": {
                "type": "business_constraint",
                "fields": ["location", "school"],
                "rules": {
                    "location": {
                        "format": "address",
                        "max_length": 255,
                        "no_whitespace_only": True,
                    },
                    "school": {
                        "format": "salesforce_id",
                        "valid_reference": True,
                    },
                },
                "severity": "info",
                "description": "VMS Event location and school validation",
            },
            "event_duration_validation": {
                "type": "business_constraint",
                "fields": ["start_date", "end_date", "duration"],
                "rules": {
                    "duration": {
                        "min_minutes": 15,
                        "max_days": 30,
                        "calculated_from_dates": True,
                    },
                    "date_range": {
                        "start_before_end": True,
                        "max_future_months": 24,
                        "min_notice_hours": 1,
                    },
                },
                "severity": "warning",
                "description": "VMS Event duration and timing validation",
            },
            "event_participant_validation": {
                "type": "business_constraint",
                "fields": ["participant_count", "registered_count", "attended_count"],
                "rules": {
                    "count_consistency": {
                        "attended_less_than_registered": True,
                        "registered_less_than_capacity": True,
                        "participant_count_accurate": True,
                    },
                    "count_ranges": {
                        "min_participants": 0,
                        "max_participants": 10000,
                        "reasonable_attendance_rate": True,
                    },
                },
                "severity": "warning",
                "description": "VMS Event participant count validation",
            },
            "event_volunteer_validation": {
                "type": "business_constraint",
                "fields": ["volunteers_needed", "volunteers"],
                "rules": {
                    "volunteer_requirements": {
                        "min_volunteers": 0,
                        "max_volunteers": 1000,
                        "reasonable_ratio": True,
                    },
                    "volunteer_assignment": {
                        "max_volunteers_per_event": 1000,
                        "volunteer_availability": True,
                        "skill_matching": True,
                    },
                },
                "severity": "info",
                "description": "VMS Event volunteer validation",
            },
            "event_school_validation": {
                "type": "business_constraint",
                "fields": ["school"],
                "rules": {
                    "school": {
                        "format": "salesforce_id",
                        "valid_reference": True,
                        "district_consistency": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event school assignment validation",
            },
            "event_district_validation": {
                "type": "business_constraint",
                "fields": ["districts"],
                "rules": {
                    "districts": {
                        "max_districts_per_event": 10,
                        "district_consistency": True,
                        "school_district_alignment": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event district relationship validation",
            },
            "event_series_validation": {
                "type": "business_constraint",
                "fields": ["series"],
                "rules": {
                    "series": {
                        "max_length": 255,
                        "no_whitespace_only": True,
                        "series_consistency": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event series validation",
            },
            "event_session_validation": {
                "type": "business_constraint",
                "fields": ["session_id", "session_host"],
                "rules": {
                    "session_id": {
                        "max_length": 255,
                        "unique_per_host": True,
                        "format": "alphanumeric_with_dashes",
                    },
                    "session_host": {
                        "max_length": 255,
                        "allowed_hosts": ["PREPKC", "Other"],
                        "default_value": "PREPKC",
                    },
                },
                "severity": "info",
                "description": "VMS Event session validation",
            },
            "event_registration_validation": {
                "type": "business_constraint",
                "fields": ["registration_link"],
                "rules": {
                    "registration_link": {
                        "max_length": 1300,
                        "url_format": True,
                        "secure_protocol": True,
                    }
                },
                "severity": "warning",
                "description": "VMS Event registration validation",
            },
            "event_cancellation_validation": {
                "type": "business_constraint",
                "fields": ["cancellation_reason"],
                "rules": {
                    "cancellation_reason": {
                        "required_when_cancelled": True,
                        "allowed_reasons": [
                            "weather",
                            "low_enrollment",
                            "instructor_unavailable",
                            "facility_issue",
                            "other",
                        ],
                        "reason_description": True,
                    }
                },
                "severity": "warning",
                "description": "VMS Event cancellation validation",
            },
            "event_attendance_validation": {
                "type": "business_constraint",
                "fields": ["attendance"],
                "rules": {
                    "attendance": {
                        "status_tracking": True,
                        "count_accuracy": True,
                        "timestamp_validation": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event attendance tracking validation",
            },
            "event_comment_validation": {
                "type": "business_constraint",
                "fields": ["comments"],
                "rules": {
                    "comments": {
                        "max_length": 10000,
                        "no_whitespace_only": True,
                        "timestamp_tracking": True,
                    }
                },
                "severity": "info",
                "description": "VMS Event comment validation",
            },
            "event_metadata_validation": {
                "type": "business_constraint",
                "fields": [
                    "additional_information",
                    "educators",
                    "educator_ids",
                    "professionals",
                    "professional_ids",
                ],
                "rules": {
                    "additional_information": {
                        "max_length": 10000,
                        "no_whitespace_only": True,
                    },
                    "educators": {
                        "max_length": 1000,
                        "semicolon_separated": True,
                        "no_whitespace_only": True,
                    },
                    "educator_ids": {
                        "max_length": 1000,
                        "semicolon_separated": True,
                        "no_whitespace_only": True,
                    },
                    "professionals": {
                        "max_length": 1000,
                        "semicolon_separated": True,
                        "no_whitespace_only": True,
                    },
                    "professional_ids": {
                        "max_length": 1000,
                        "semicolon_separated": True,
                        "no_whitespace_only": True,
                    },
                },
                "severity": "info",
                "description": "VMS Event metadata validation",
            },
            "event_timing_validation": {
                "type": "business_constraint",
                "fields": ["start_date", "end_date", "created_at", "updated_at"],
                "rules": {
                    "timing": {
                        "start_date_future_allowed": True,
                        "end_date_after_start": True,
                        "created_before_start": True,
                        "updated_after_created": True,
                    },
                    "timezone": {
                        "timezone_aware": True,
                        "consistent_timezone": True,
                    },
                },
                "severity": "warning",
                "description": "VMS Event timing validation",
            },
        },
        "volunteer": {
            "volunteer_registration_workflow": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "basic_info",
                        "required_fields": ["first_name", "last_name"],
                        "description": "Basic contact information required",
                    },
                    {
                        "step": "contact_methods",
                        "required_fields": ["email"],
                        "description": "Email required for communication",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "professional_info",
                        "required_fields": [],
                        "description": "Professional information is optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "skills_assessment",
                        "required_fields": [],
                        "description": "Skills assessment is optional",
                        "depends_on": ["basic_info"],
                    },
                ],
                "severity": "info",
                "description": "VMS Volunteer registration workflow validation",
            }
        },
        "organization": {
            "organization_creation_workflow": {
                "type": "workflow",
                "workflow_steps": [
                    {
                        "step": "basic_info",
                        "required_fields": ["name"],
                        "description": "Organization name is required",
                    },
                    {
                        "step": "classification",
                        "required_fields": ["type"],
                        "description": "Organization type classification",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "address_info",
                        "required_fields": [],
                        "description": "Address information is optional",
                        "depends_on": ["basic_info"],
                    },
                    {
                        "step": "volunteer_associations",
                        "required_fields": [],
                        "description": "Volunteer associations created separately",
                        "depends_on": ["basic_info"],
                    },
                ],
                "severity": "info",
                "description": "VMS Organization creation workflow validation",
            },
            "organization_volunteer_relationships": {
                "type": "business_constraint",
                "rules": {
                    "max_volunteers_per_org": 1000,
                    "primary_organization_limit": 1,
                    "relationship_status_required": True,
                    "cascade_delete_volunteer_orgs": True,
                },
                "severity": "warning",
                "description": "VMS Organization-volunteer relationship validation",
            },
        },
        "import_strategy_awareness": {
            "event_import_strategy": {
                "type": "business_constraint",
                "description": "Event import strategy intentionally filters certain types",
                "expected_discrepancies": {
                    "draft_events": {
                        "reason": "Intentionally excluded from Salesforce import",
                        "expected_count": "70 events",
                        "severity": "info",
                    },
                    "connector_sessions": {
                        "reason": "Intentionally excluded from Salesforce import",
                        "expected_count": "966 events",
                        "severity": "info",
                    },
                    "virtual_sessions": {
                        "reason": "Created locally, not in Salesforce",
                        "expected_count": "367 events",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS Event import strategy awareness",
            },
            "volunteer_import_strategy": {
                "type": "business_constraint",
                "description": "Volunteers can exist without Salesforce IDs",
                "expected_scenarios": {
                    "local_creation": {
                        "reason": "Created through web interface or local processes",
                        "severity": "info",
                    },
                    "virtual_session_volunteers": {
                        "reason": "Volunteers for virtual sessions",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS Volunteer import strategy awareness",
            },
            "organization_import_strategy": {
                "type": "business_constraint",
                "description": "Organizations imported from Salesforce with selective filtering",
                "expected_scenarios": {
                    "salesforce_import": {
                        "reason": "Primary source from Salesforce Account records",
                        "required_fields": ["name", "type"],
                        "severity": "info",
                    },
                    "local_creation": {
                        "reason": "Created through web interface for local organizations",
                        "severity": "info",
                    },
                    "excluded_types": {
                        "reason": "Draft, Test, and Sample organizations excluded",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS Organization import strategy awareness",
            },
            "student_import_strategy": {
                "type": "business_constraint",
                "description": "Students can exist without Salesforce IDs",
                "expected_scenarios": {
                    "local_creation": {
                        "reason": "Created through web interface or local processes",
                        "severity": "info",
                    },
                    "salesforce_import": {
                        "reason": "Imported from Salesforce with Contact_Type__c = 'Student'",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS Student import strategy awareness",
            },
            "teacher_import_strategy": {
                "type": "business_constraint",
                "description": "Teachers can exist without Salesforce IDs",
                "expected_scenarios": {
                    "local_creation": {
                        "reason": "Created through web interface or local processes",
                        "severity": "info",
                    },
                    "salesforce_import": {
                        "reason": "Imported from Salesforce with Contact_Type__c = 'Teacher'",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS Teacher import strategy awareness",
            },
            "school_import_strategy": {
                "type": "business_constraint",
                "description": "Schools imported from Salesforce with district relationships",
                "expected_scenarios": {
                    "salesforce_import": {
                        "reason": "Primary source from Salesforce Account records",
                        "required_fields": ["id", "name"],
                        "severity": "info",
                    },
                    "local_creation": {
                        "reason": "Created through web interface for local schools",
                        "severity": "info",
                    },
                    "virtual_session_schools": {
                        "reason": "Schools created for virtual sessions",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS School import strategy awareness",
            },
            "district_import_strategy": {
                "type": "business_constraint",
                "description": "Districts imported from Salesforce with school relationships",
                "expected_scenarios": {
                    "salesforce_import": {
                        "reason": "Primary source from Salesforce Account records",
                        "required_fields": ["id", "name"],
                        "severity": "info",
                    },
                    "local_creation": {
                        "reason": "Created through web interface for local districts",
                        "severity": "info",
                    },
                    "school_district_association": {
                        "reason": "Districts created when schools are imported",
                        "severity": "info",
                    },
                },
                "severity": "info",
                "description": "VMS District import strategy awareness",
            },
        },
    },
}

# Main validation configuration dictionary
VALIDATION_CONFIG = {
    "thresholds": VALIDATION_THRESHOLDS,
    "salesforce": SALESFORCE_CONFIG,
    "cache": CACHE_CONFIG,
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

    # Cache configuration validation not needed for Flask-Caching

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
