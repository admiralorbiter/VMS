# utils/validators/field_completeness_validator.py
"""
Field completeness validation for Salesforce data quality.

This validator checks that required fields are populated and data quality
standards are met for various entity types.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from utils.salesforce_client import SalesforceClient
from utils.validation_base import DataValidator

logger = logging.getLogger(__name__)


class FieldCompletenessValidator(DataValidator):
    """
    Validates field completeness and data quality for Salesforce records.

    This validator ensures that:
    - Required fields are populated
    - Data formats are correct
    - Field values are within expected ranges
    - Business rules are followed
    """

    def __init__(self, run_id: Optional[int] = None, entity_type: str = "all"):
        """
        Initialize the field completeness validator.

        Args:
            run_id: ID of the validation run
            entity_type: Type of entity to validate ('all', 'volunteer', 'organization', 'event', 'student', 'teacher')
        """
        super().__init__(run_id=run_id)
        self.entity_type = entity_type
        self.salesforce_client = None

        # Get field completeness configuration
        self.completeness_config = get_config_section("field_completeness_rules")
        self.required_fields = self.completeness_config.get("required_fields", {})
        self.field_formats = self.completeness_config.get("field_formats", {})
        self.field_ranges = self.completeness_config.get("field_ranges", {})
        self.min_completeness_threshold = self.completeness_config.get(
            "min_completeness_threshold", 95.0
        )

        logger.debug(
            f"Initialized FieldCompletenessValidator for entity type: {entity_type}"
        )

    def get_entity_type(self) -> str:
        """Get the entity type this validator handles."""
        return self.entity_type

    def validate(self) -> List[ValidationResult]:
        """
        Execute field completeness validation.

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
                self._validate_entity_completeness(entity)

            # Add summary metrics
            self._add_summary_metrics()

            return self.results

        except Exception as e:
            logger.error(f"Field completeness validation failed: {e}")
            raise
        finally:
            if self.salesforce_client:
                self.salesforce_client.close()

    def _validate_entity_completeness(self, entity_type: str):
        """Validate field completeness for a specific entity type."""
        try:
            logger.info(f"Validating field completeness for {entity_type}")

            # Get sample records from Salesforce
            sample_records = self._get_salesforce_sample(entity_type, limit=100)

            if not sample_records:
                logger.warning(f"No sample records found for {entity_type}")
                return

            # Validate each record
            total_fields = 0
            populated_fields = 0
            validation_errors = []

            for record in sample_records:
                record_validation = self._validate_record_fields(entity_type, record)
                total_fields += record_validation["total_fields"]
                populated_fields += record_validation["populated_fields"]
                validation_errors.extend(record_validation["errors"])

            logger.debug(
                f"Total validation: total_fields={total_fields}, populated_fields={populated_fields}"
            )

            # Calculate completeness percentage
            completeness_percentage = (populated_fields / max(total_fields, 1)) * 100

            # Determine severity based on threshold
            severity = self._determine_completeness_severity(completeness_percentage)

            # Create validation result
            result = self.create_result(
                entity_type=entity_type,
                severity=severity,
                message=f"Field completeness validation for {entity_type}",
                validation_type="field_completeness",
                field_name="overall_completeness",
                expected_value=f"{self.min_completeness_threshold}%",
                actual_value=f"{completeness_percentage:.1f}%",
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

            # Add completeness metric
            metric = self.create_metric(
                metric_name=f"{entity_type}_field_completeness",
                metric_value=completeness_percentage,
                metric_category="quality",
                metric_unit="percentage",
                entity_type=entity_type,
            )
            self.add_metric(metric)

            logger.info(
                f"Field completeness validation for {entity_type}: {completeness_percentage:.1f}%"
            )

        except Exception as e:
            logger.error(
                f"Failed to validate field completeness for {entity_type}: {e}"
            )
            self.add_result(
                self.create_result(
                    entity_type=entity_type,
                    severity="error",
                    message=f"Field completeness validation failed for {entity_type}",
                    validation_type="field_completeness",
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

    def _validate_record_fields(
        self, entity_type: str, record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate fields for a single record."""
        validation_result = {"total_fields": 0, "populated_fields": 0, "errors": []}

        # Get required fields for this entity type
        entity_required_fields = self.required_fields.get(entity_type, [])

        for field_name in entity_required_fields:
            validation_result["total_fields"] += 1

            # Check if field is populated
            field_value = record.get(field_name)
            if field_value and str(field_value).strip():
                validation_result["populated_fields"] += 1

                # Validate field format if specified
                format_validation = self._validate_field_format(
                    entity_type, field_name, field_value
                )
                if not format_validation["valid"]:
                    validation_result["errors"].append(
                        {
                            "field": field_name,
                            "value": field_value,
                            "error": format_validation["error"],
                        }
                    )

                # Validate field range if specified
                range_validation = self._validate_field_range(
                    entity_type, field_name, field_value
                )
                if not range_validation["valid"]:
                    validation_result["errors"].append(
                        {
                            "field": field_name,
                            "value": field_value,
                            "error": range_validation["error"],
                        }
                    )
            else:
                # Field is empty or null
                validation_result["errors"].append(
                    {
                        "field": field_name,
                        "value": field_value,
                        "error": "Required field is empty or null",
                    }
                )

        return validation_result

    def _validate_field_format(
        self, entity_type: str, field_name: str, field_value: Any
    ) -> Dict[str, Any]:
        """Validate field format based on configuration."""
        format_rules = self.field_formats.get(entity_type, {}).get(field_name, {})

        if not format_rules:
            return {"valid": True, "error": None}

        try:
            # Email format validation
            if format_rules.get("type") == "email":
                import re

                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, str(field_value)):
                    return {"valid": False, "error": "Invalid email format"}

            # Phone format validation
            elif format_rules.get("type") == "phone":
                import re

                phone_pattern = r"^[\+]?[1-9][\d]{0,15}$"
                cleaned_phone = re.sub(r"[^\d+]", "", str(field_value))
                if not re.match(phone_pattern, cleaned_phone):
                    return {"valid": False, "error": "Invalid phone format"}

            # Date format validation
            elif format_rules.get("type") == "date":
                try:
                    datetime.fromisoformat(str(field_value).replace("Z", "+00:00"))
                except ValueError:
                    return {"valid": False, "error": "Invalid date format"}

            # Custom regex validation
            elif format_rules.get("regex"):
                import re

                if not re.match(format_rules["regex"], str(field_value)):
                    return {
                        "valid": False,
                        "error": f"Field doesn't match pattern: {format_rules['regex']}",
                    }

            return {"valid": True, "error": None}

        except Exception as e:
            logger.warning(
                f"Format validation error for {entity_type}.{field_name}: {e}"
            )
            return {
                "valid": True,
                "error": None,
            }  # Don't fail validation on format errors

    def _validate_field_range(
        self, entity_type: str, field_name: str, field_value: Any
    ) -> Dict[str, Any]:
        """Validate field value is within expected range."""
        range_rules = self.field_ranges.get(entity_type, {}).get(field_name, {})

        if not range_rules:
            return {"valid": True, "error": None}

        try:
            # Numeric range validation
            if "min" in range_rules or "max" in range_rules:
                try:
                    numeric_value = float(field_value)

                    if "min" in range_rules and numeric_value < range_rules["min"]:
                        return {
                            "valid": False,
                            "error": f"Value {numeric_value} below minimum {range_rules['min']}",
                        }

                    if "max" in range_rules and numeric_value > range_rules["max"]:
                        return {
                            "valid": False,
                            "error": f"Value {numeric_value} above maximum {range_rules['max']}",
                        }

                except (ValueError, TypeError):
                    return {"valid": False, "error": "Field value is not numeric"}

            # String length validation
            if "min_length" in range_rules or "max_length" in range_rules:
                string_value = str(field_value)

                if (
                    "min_length" in range_rules
                    and len(string_value) < range_rules["min_length"]
                ):
                    return {
                        "valid": False,
                        "error": f"String length {len(string_value)} below minimum {range_rules['min_length']}",
                    }

                if (
                    "max_length" in range_rules
                    and len(string_value) > range_rules["max_length"]
                ):
                    return {
                        "valid": False,
                        "error": f"String length {len(string_value)} above maximum {range_rules['max_length']}",
                    }

            # Enum value validation
            if "allowed_values" in range_rules:
                if field_value not in range_rules["allowed_values"]:
                    return {
                        "valid": False,
                        "error": f"Value '{field_value}' not in allowed values: {range_rules['allowed_values']}",
                    }

            return {"valid": True, "error": None}

        except Exception as e:
            logger.warning(
                f"Range validation error for {entity_type}.{field_name}: {e}"
            )
            return {
                "valid": True,
                "error": None,
            }  # Don't fail validation on range errors

    def _determine_completeness_severity(self, completeness_percentage: float) -> str:
        """Determine severity based on completeness percentage."""
        if completeness_percentage >= self.min_completeness_threshold:
            return "info"
        elif completeness_percentage >= self.min_completeness_threshold - 10:
            return "warning"
        elif completeness_percentage >= self.min_completeness_threshold - 25:
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

            # Calculate average completeness
            completeness_metrics = [
                m for m in self.metrics if "completeness" in m.metric_name
            ]
            avg_completeness = (
                sum(m.metric_value for m in completeness_metrics)
                / len(completeness_metrics)
                if completeness_metrics
                else 0
            )

            # Add summary metrics
            summary_metric = self.create_metric(
                metric_name="field_completeness_validation_success_rate",
                metric_value=(
                    (info_count / total_results) * 100 if total_results > 0 else 0
                ),
                metric_category="quality",
                metric_unit="percentage",
                entity_type="all",
            )
            self.add_metric(summary_metric)

            # Add average completeness metric
            avg_completeness_metric = self.create_metric(
                metric_name="average_field_completeness",
                metric_value=avg_completeness,
                metric_category="quality",
                metric_unit="percentage",
                entity_type="all",
            )
            self.add_metric(avg_completeness_metric)

            # Add severity breakdown metrics
            severity_metrics = [
                ("info_count", info_count),
                ("warning_count", warning_count),
                ("error_count", error_count),
                ("critical_count", critical_count),
            ]

            for metric_name, metric_value in severity_metrics:
                metric = self.create_metric(
                    metric_name=f"field_completeness_{metric_name}",
                    metric_value=metric_value,
                    metric_category="quality",
                    metric_unit="count",
                    entity_type="all",
                )
                self.add_metric(metric)

            logger.debug(
                f"Added field completeness summary metrics: avg_completeness={avg_completeness:.2f}%, "
                f"total={total_results}, info={info_count}, warning={warning_count}, "
                f"error={error_count}, critical={critical_count}"
            )

        except Exception as e:
            logger.error(f"Failed to add field completeness summary metrics: {e}")

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of the field completeness validation results."""
        summary = self.get_summary()

        # Add field completeness specific information
        summary["entity_type"] = self.entity_type
        summary["min_completeness_threshold"] = self.min_completeness_threshold
        summary["required_fields"] = self.required_fields

        return summary

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.salesforce_client:
            self.salesforce_client.close()
