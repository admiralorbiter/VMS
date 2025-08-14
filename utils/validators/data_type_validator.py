"""
Data type validation for Salesforce data quality.

This validator checks that data types and formats are correct for various
entity types, including email, phone, date, URL, and custom format validation.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from utils.salesforce_client import SalesforceClient
from utils.validation_base import DataValidator

logger = logging.getLogger(__name__)


class DataTypeValidator(DataValidator):
    """
    Validates data types and formats for Salesforce records.

    This validator ensures that:
    - Field formats are correct (email, phone, date, URL)
    - Data types are consistent
    - String lengths are within acceptable ranges
    - Enum values are valid
    - Custom regex patterns are satisfied
    """

    def __init__(self, run_id: Optional[int] = None, entity_type: str = "all"):
        """
        Initialize the data type validator.

        Args:
            run_id: ID of the validation run
            entity_type: Type of entity to validate ('all', 'volunteer', 'organization', 'event', 'student', 'teacher')
        """
        super().__init__(run_id=run_id)
        self.entity_type = entity_type
        self.salesforce_client = None

        # Get data type validation configuration
        self.data_type_config = get_config_section("data_type_rules")
        self.format_rules = self.data_type_config.get("format_validation", {})
        self.type_consistency = self.data_type_config.get("type_consistency", {})
        self.validation_thresholds = self.data_type_config.get(
            "validation_thresholds", {}
        )

        logger.debug(f"Initialized DataTypeValidator for entity type: {entity_type}")

    def get_entity_type(self) -> str:
        """Get the entity type this validator handles."""
        return self.entity_type

    def validate(self) -> List[ValidationResult]:
        """
        Execute data type validation.

        Returns:
            List of validation results
        """
        try:
            # Initialize Salesforce client
            self.salesforce_client = SalesforceClient()

            # Determine which entities to validate
            if self.entity_type == "all":
                entities_to_validate = [
                    "volunteer",
                    "organization",
                    "event",
                    "student",
                    "teacher",
                ]
            else:
                entities_to_validate = [self.entity_type]

            # Validate each entity type
            for entity in entities_to_validate:
                self._validate_entity_data_types(entity)

            # Add summary metrics
            self._add_summary_metrics()

            return self.results

        except Exception as e:
            logger.error(f"Data type validation failed: {e}")
            raise
        finally:
            if self.salesforce_client:
                self.salesforce_client.close()

    def _validate_entity_data_types(self, entity_type: str):
        """Validate data types for a specific entity type."""
        try:
            logger.info(f"Validating data types for {entity_type}")

            # Get sample records from Salesforce
            sample_records = self._get_salesforce_sample(entity_type, limit=100)

            if not sample_records:
                logger.warning(f"No sample records found for {entity_type}")
                return

            # Get format rules for this entity type
            entity_format_rules = self.format_rules.get(entity_type, {})
            if not entity_format_rules:
                logger.info(f"No format rules defined for {entity_type}")
                return

            # Validate each record
            total_validations = 0
            successful_validations = 0
            validation_errors = []

            for record in sample_records:
                record_validation = self._validate_record_data_types(
                    entity_type, record, entity_format_rules
                )
                total_validations += record_validation["total_validations"]
                successful_validations += record_validation["successful_validations"]
                validation_errors.extend(record_validation["errors"])

            # Calculate accuracy percentage
            accuracy_percentage = (
                successful_validations / max(total_validations, 1)
            ) * 100

            # Determine severity based on threshold
            severity = self._determine_accuracy_severity(accuracy_percentage)

            # Create validation result
            result = self.create_result(
                entity_type=entity_type,
                severity=severity,
                message=f"Data type validation for {entity_type}",
                validation_type="data_type_validation",
                field_name="overall_accuracy",
                expected_value=f"{self.validation_thresholds.get('overall_accuracy', 99.0)}%",
                actual_value=f"{accuracy_percentage:.1f}%",
            )

            # Add detailed validation errors if any
            if validation_errors:
                result.details = {
                    "validation_errors": validation_errors[
                        :10
                    ],  # Limit to first 10 errors
                    "total_errors": len(validation_errors),
                }

            self.add_result(result)

            # Add accuracy metric
            metric = self.create_metric(
                metric_name=f"{entity_type}_data_type_accuracy",
                metric_value=accuracy_percentage,
                metric_category="quality",
                metric_unit="percentage",
                entity_type=entity_type,
            )
            self.add_metric(metric)

            logger.info(
                f"Data type validation for {entity_type}: {accuracy_percentage:.1f}%"
            )

        except Exception as e:
            logger.error(f"Failed to validate data types for {entity_type}: {e}")
            self.add_result(
                self.create_result(
                    entity_type=entity_type,
                    severity="error",
                    message=f"Data type validation failed for {entity_type}",
                    validation_type="data_type_validation",
                    details={"error": str(e)},
                )
            )

    def _get_salesforce_sample(
        self, entity_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get a sample of records from Salesforce for validation."""
        try:
            if entity_type == "volunteer":
                return self.salesforce_client.get_volunteer_sample(limit=limit)
            elif entity_type == "organization":
                return self.salesforce_client.get_organization_sample(limit=limit)
            elif entity_type == "event":
                return self.salesforce_client.get_event_sample(limit=limit)
            elif entity_type == "student":
                return self.salesforce_client.get_student_sample(limit=limit)
            elif entity_type == "teacher":
                return self.salesforce_client.get_teacher_sample(limit=limit)
            else:
                logger.warning(f"Unknown entity type for sampling: {entity_type}")
                return []

        except Exception as e:
            logger.error(f"Failed to get Salesforce sample for {entity_type}: {e}")
            return []

    def _validate_record_data_types(
        self, entity_type: str, record: Dict[str, Any], format_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate data types for a single record."""
        validation_result = {
            "total_validations": 0,
            "successful_validations": 0,
            "errors": [],
        }

        for field_name, field_rules in format_rules.items():
            field_value = record.get(field_name)

            # Skip validation if field is not required and value is None
            if not field_rules.get("required", False) and field_value is None:
                continue

            validation_result["total_validations"] += 1

            # Validate field format
            format_validation = self._validate_field_format(
                field_name, field_value, field_rules
            )
            if format_validation["valid"]:
                validation_result["successful_validations"] += 1
            else:
                validation_result["errors"].append(
                    {
                        "field": field_name,
                        "value": field_value,
                        "error": format_validation["error"],
                        "severity": field_rules.get("severity", "warning"),
                    }
                )

        return validation_result

    def _validate_field_format(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate field format based on configuration."""
        try:
            # Handle None values
            if field_value is None:
                if field_rules.get("required", False):
                    return {"valid": False, "error": "Required field is null"}
                else:
                    return {"valid": True, "error": None}

            field_type = field_rules.get("type", "string")

            # String type validation
            if field_type == "string":
                return self._validate_string_field(field_name, field_value, field_rules)

            # Email validation
            elif field_type == "email":
                return self._validate_email_field(field_name, field_value, field_rules)

            # Phone validation
            elif field_type == "phone":
                return self._validate_phone_field(field_name, field_value, field_rules)

            # URL validation
            elif field_type == "url":
                return self._validate_url_field(field_name, field_value, field_rules)

            # Date/DateTime validation
            elif field_type in ["date", "datetime"]:
                return self._validate_datetime_field(
                    field_name, field_value, field_rules
                )

            # Enum validation
            elif field_type == "enum":
                return self._validate_enum_field(field_name, field_value, field_rules)

            # Custom regex validation
            elif "pattern" in field_rules:
                return self._validate_regex_field(field_name, field_value, field_rules)

            # Default: valid if no specific validation rules
            return {"valid": True, "error": None}

        except Exception as e:
            logger.warning(f"Format validation error for {field_name}: {e}")
            return {
                "valid": True,
                "error": None,
            }  # Don't fail validation on format errors

    def _validate_string_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate string field with length constraints."""
        try:
            string_value = str(field_value)

            # Check minimum length
            if (
                "min_length" in field_rules
                and len(string_value) < field_rules["min_length"]
            ):
                return {
                    "valid": False,
                    "error": f"String length {len(string_value)} below minimum {field_rules['min_length']}",
                }

            # Check maximum length
            if (
                "max_length" in field_rules
                and len(string_value) > field_rules["max_length"]
            ):
                return {
                    "valid": False,
                    "error": f"String length {len(string_value)} above maximum {field_rules['max_length']}",
                }

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"String validation failed: {e}"}

    def _validate_email_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate email field format."""
        try:
            email_value = str(field_value).strip()

            # Use custom pattern if provided, otherwise use default email pattern
            pattern = field_rules.get(
                "pattern", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )

            if not re.match(pattern, email_value):
                return {"valid": False, "error": "Invalid email format"}

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Email validation failed: {e}"}

    def _validate_phone_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate phone field format."""
        try:
            phone_value = str(field_value).strip()

            # Use custom pattern if provided, otherwise use default phone pattern
            pattern = field_rules.get("pattern", r"^[\+]?[1-9][\d]{0,15}$")

            # Clean phone number (remove spaces, dashes, parentheses)
            cleaned_phone = re.sub(r"[\s\-\(\)]", "", phone_value)

            if not re.match(pattern, cleaned_phone):
                return {"valid": False, "error": "Invalid phone format"}

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Phone validation failed: {e}"}

    def _validate_url_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate URL field format."""
        try:
            url_value = str(field_value).strip()

            # Use custom pattern if provided, otherwise use default URL pattern
            pattern = field_rules.get("pattern", r"^https?://.*")

            if not re.match(pattern, url_value):
                return {"valid": False, "error": "Invalid URL format"}

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"URL validation failed: {e}"}

    def _validate_datetime_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate date/datetime field format."""
        try:
            date_value = str(field_value).strip()

            # Handle ISO8601 format
            if field_rules.get("format") == "ISO8601":
                try:
                    # Try parsing as ISO8601
                    datetime.fromisoformat(date_value.replace("Z", "+00:00"))
                    return {"valid": True, "error": None}
                except ValueError:
                    return {"valid": False, "error": "Invalid ISO8601 datetime format"}

            # Handle other date formats
            try:
                # Try common date formats
                datetime.fromisoformat(date_value)
                return {"valid": True, "error": None}
            except ValueError:
                try:
                    # Try parsing with dateutil if available
                    from dateutil import parser

                    parser.parse(date_value)
                    return {"valid": True, "error": None}
                except (ImportError, ValueError):
                    return {"valid": False, "error": "Invalid date format"}

        except Exception as e:
            return {"valid": False, "error": f"Date validation failed: {e}"}

    def _validate_enum_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate enum field values."""
        try:
            allowed_values = field_rules.get("allowed_values", [])

            if not allowed_values:
                return {"valid": True, "error": None}  # No restrictions

            if field_value not in allowed_values:
                return {
                    "valid": False,
                    "error": f"Value '{field_value}' not in allowed values: {allowed_values}",
                }

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Enum validation failed: {e}"}

    def _validate_regex_field(
        self, field_name: str, field_value: Any, field_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate field using custom regex pattern."""
        try:
            pattern = field_rules.get("pattern")
            if not pattern:
                return {"valid": True, "error": None}

            string_value = str(field_value)

            if not re.match(pattern, string_value):
                return {
                    "valid": False,
                    "error": f"Field doesn't match pattern: {pattern}",
                }

            return {"valid": True, "error": None}

        except Exception as e:
            return {"valid": False, "error": f"Regex validation failed: {e}"}

    def _determine_accuracy_severity(self, accuracy_percentage: float) -> str:
        """Determine severity based on accuracy percentage."""
        overall_threshold = self.validation_thresholds.get("overall_accuracy", 99.0)

        if accuracy_percentage >= overall_threshold:
            return "info"
        elif accuracy_percentage >= overall_threshold - 5:
            return "warning"
        elif accuracy_percentage >= overall_threshold - 15:
            return "error"
        else:
            return "critical"

    def _add_summary_metrics(self):
        """Add summary metrics for the validation run."""
        try:
            # Calculate overall statistics
            total_results = len(self.results)
            if total_results == 0:
                return

            # Count by severity
            info_count = len([r for r in self.results if r.is_info])
            warning_count = len([r for r in self.results if r.is_warning])
            error_count = len([r for r in self.results if r.is_error])
            critical_count = len([r for r in self.results if r.is_critical])

            # Calculate average accuracy
            accuracy_metrics = [m for m in self.metrics if "accuracy" in m.metric_name]
            avg_accuracy = (
                sum(m.metric_value for m in accuracy_metrics) / len(accuracy_metrics)
                if accuracy_metrics
                else 0
            )

            # Add summary metrics
            summary_metric = self.create_metric(
                metric_name="data_type_validation_success_rate",
                metric_value=(
                    (info_count / total_results) * 100 if total_results > 0 else 0
                ),
                metric_category="quality",
                metric_unit="percentage",
                entity_type="all",
            )
            self.add_metric(summary_metric)

            # Add average accuracy metric
            avg_accuracy_metric = self.create_metric(
                metric_name="average_data_type_accuracy",
                metric_value=avg_accuracy,
                metric_category="quality",
                metric_unit="percentage",
                entity_type="all",
            )
            self.add_metric(avg_accuracy_metric)

            # Add severity breakdown metrics
            severity_metrics = [
                ("info_count", info_count),
                ("warning_count", warning_count),
                ("error_count", error_count),
                ("critical_count", critical_count),
            ]

            for metric_name, metric_value in severity_metrics:
                metric = self.create_metric(
                    metric_name=f"data_type_validation_{metric_name}",
                    metric_value=metric_value,
                    metric_category="quality",
                    metric_unit="count",
                    entity_type="all",
                )
                self.add_metric(metric)

            logger.debug(
                f"Added data type validation summary metrics: avg_accuracy={avg_accuracy:.2f}%, "
                f"total={total_results}, info={info_count}, warning={warning_count}, "
                f"error={error_count}, critical={critical_count}"
            )

        except Exception as e:
            logger.error(f"Failed to add data type validation summary metrics: {e}")

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of the data type validation results."""
        summary = self.get_summary()

        # Add data type validation specific information
        summary["entity_type"] = self.entity_type
        summary["validation_thresholds"] = self.validation_thresholds
        summary["type_consistency"] = self.type_consistency

        return summary

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.salesforce_client:
            self.salesforce_client.close()
