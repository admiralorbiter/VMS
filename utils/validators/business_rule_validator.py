"""
Business rule validation for Salesforce data quality.

This validator checks that data follows business logic rules, including:
- Status transition validation
- Date range validation
- Capacity limit validation
- Business constraint validation
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from utils.salesforce_client import SalesforceClient
from utils.validation_base import DataValidator

logger = logging.getLogger(__name__)


class BusinessRuleValidator(DataValidator):
    """
    Validates business rules for Salesforce records.

    This validator ensures that:
    - Status transitions follow business logic
    - Date ranges are logical and valid
    - Capacity limits are respected
    - Business constraints are satisfied
    """

    def __init__(self, run_id: Optional[int] = None, entity_type: str = "all"):
        super().__init__(run_id=run_id)
        self.entity_type = entity_type
        self.salesforce_client = None

        # Get business rule validation configuration
        self.business_config = get_config_section("business_rules")
        self.validation_settings = self.business_config.get("validation_settings", {})
        self.business_rules = self.business_config.get("business_rules", {})

        logger.debug(
            f"Initialized BusinessRuleValidator for entity type: {entity_type}"
        )

    def validate(self) -> List[ValidationResult]:
        """Run business rule validation."""
        try:
            if not self.salesforce_client:
                self.salesforce_client = SalesforceClient()

            results = []
            entity_types = (
                [self.entity_type]
                if self.entity_type != "all"
                else ["volunteer", "organization", "event", "student", "teacher"]
            )

            for entity_type in entity_types:
                if entity_type in self.business_rules:
                    logger.info(f"Validating business rules for {entity_type}...")
                    entity_results = self._validate_entity_business_rules(entity_type)
                    results.extend(entity_results)

            # Add summary metrics
            self._add_summary_metrics(results)

            logger.info(
                f"Business rule validation completed with {len(results)} results"
            )
            return results

        except Exception as e:
            logger.error(f"Business rule validation failed: {e}")
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="business_rules",
                    field_name="business_rules",
                    severity="error",
                    metadata={"error": str(e)},
                )
            )
            raise

    def _validate_entity_business_rules(
        self, entity_type: str
    ) -> List[ValidationResult]:
        """Validate business rules for a specific entity type."""
        results = []

        try:
            # Get sample data for validation
            sample_data = self._get_salesforce_sample(entity_type)
            logger.debug(f"Got {len(sample_data)} sample records for {entity_type}")

            if not sample_data:
                logger.warning(f"No sample data available for {entity_type}")
                return results

            # Get business rules for this entity type
            entity_rules = self.business_rules.get(entity_type, {})
            logger.debug(
                f"Found {len(entity_rules)} business rules for {entity_type}: {list(entity_rules.keys())}"
            )

            # Validate each business rule
            for rule_name, rule_config in entity_rules.items():
                logger.debug(f"Validating rule: {rule_name} with config: {rule_config}")
                rule_results = self._validate_business_rule(
                    entity_type, rule_name, rule_config, sample_data
                )
                logger.debug(f"Rule {rule_name} produced {len(rule_results)} results")
                results.extend(rule_results)

        except Exception as e:
            logger.error(f"Error validating business rules for {entity_type}: {e}")
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="business_rules",
                    field_name="business_rules",
                    severity="error",
                    message=f"Error validating business rules: {str(e)}",
                    metadata={"error": str(e)},
                )
            )

        return results

    def _validate_business_rule(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate a specific business rule."""
        results = []
        rule_type = rule_config.get("type", "unknown")

        try:
            if rule_type == "status_transition":
                rule_results = self._validate_status_transitions(
                    entity_type, rule_name, rule_config, sample_data
                )
            elif rule_type == "date_range":
                rule_results = self._validate_date_ranges(
                    entity_type, rule_name, rule_config, sample_data
                )
            elif rule_type == "capacity_limit":
                rule_results = self._validate_capacity_limits(
                    entity_type, rule_name, rule_config, sample_data
                )
            elif rule_type == "business_constraint":
                rule_results = self._validate_business_constraints(
                    entity_type, rule_name, rule_config, sample_data
                )
            elif rule_type == "cross_field":
                rule_results = self._validate_cross_field_rules(
                    entity_type, rule_name, rule_config, sample_data
                )
            elif rule_type == "workflow":
                rule_results = self._validate_workflow_rules(
                    entity_type, rule_name, rule_config, sample_data
                )
            else:
                logger.warning(f"Unknown business rule type: {rule_type}")
                return results

            results.extend(rule_results)

        except Exception as e:
            logger.error(f"Error validating business rule {rule_name}: {e}")
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="business_rules",
                    field_name=rule_name,
                    severity="error",
                    message=f"Error validating business rule {rule_name}: {str(e)}",
                    metadata={"error": str(e)},
                )
            )

        return results

    def _validate_status_transitions(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate status transition rules."""
        results = []

        # Get status field and allowed transitions
        status_field = rule_config.get("status_field", "Status")
        allowed_transitions = rule_config.get("allowed_transitions", {})

        if not allowed_transitions:
            logger.debug(
                f"No allowed transitions defined for {entity_type} status validation"
            )
            return results

        # Get all valid statuses from allowed transitions
        valid_statuses = set()
        for current_status, allowed_next in allowed_transitions.items():
            valid_statuses.add(current_status)
            valid_statuses.update(allowed_next)

        logger.debug(f"Valid statuses for {entity_type}: {valid_statuses}")

        for record in sample_data:
            current_status = record.get(status_field)
            if current_status:
                # Check if current status is valid
                if current_status not in valid_statuses:
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="business_rules",
                            field_name=status_field,
                            severity="warning",
                            message=f"Invalid status '{current_status}' for {entity_type}",
                            expected_value=f"One of: {list(valid_statuses)}",
                            actual_value=current_status,
                            metadata={
                                "rule_name": rule_name,
                                "record_id": record.get("Id"),
                            },
                        )
                    )
                else:
                    # Status is valid - could add transition logic here in the future
                    logger.debug(
                        f"Valid status '{current_status}' for {entity_type} record {record.get('Id')}"
                    )
            else:
                # Status field is missing - this might be acceptable for some entities
                logger.debug(
                    f"Status field '{status_field}' missing for {entity_type} record {record.get('Id')}"
                )

        return results

    def _validate_date_ranges(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate date range rules."""
        results = []

        # Get date fields and validation rules
        start_field = rule_config.get("start_field")
        end_field = rule_config.get("end_field")
        min_duration = rule_config.get("min_duration_days", 0)
        max_duration = rule_config.get("max_duration_days", 365)

        if not start_field or not end_field:
            logger.warning(
                f"Date range validation requires both start_field and end_field for {entity_type}"
            )
            return results

        logger.debug(
            f"Validating date range for {entity_type}: {start_field} to {end_field}"
        )
        logger.debug(f"Duration constraints: {min_duration} to {max_duration} days")

        for record in sample_data:
            start_date = record.get(start_field)
            end_date = record.get(end_field)

            if start_date and end_date:
                try:
                    # Parse dates (handle multiple formats)
                    start_dt = self._parse_date(start_date)
                    end_dt = self._parse_date(end_date)

                    if start_dt and end_dt:
                        # Check if start < end
                        if start_dt >= end_dt:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=f"{start_field}_{end_field}",
                                    severity="error",
                                    message=f"Invalid date range: start date must be before end date",
                                    expected_value=f"start_date < end_date",
                                    actual_value=f"start_date={start_dt}, end_date={end_dt}",
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )
                        else:
                            # Check duration constraints
                            duration_days = (end_dt - start_dt).days
                            logger.debug(
                                f"Duration: {duration_days} days for {entity_type} record {record.get('Id')}"
                            )

                            if min_duration > 0 and duration_days < min_duration:
                                results.append(
                                    ValidationResult(
                                        run_id=self.run_id,
                                        entity_type=entity_type,
                                        validation_type="business_rules",
                                        field_name=f"{start_field}_{end_field}",
                                        severity="warning",
                                        message=f"Duration too short: {duration_days} days (minimum: {min_duration})",
                                        expected_value=f"≥{min_duration} days",
                                        actual_value=f"{duration_days} days",
                                        metadata={
                                            "rule_name": rule_name,
                                            "record_id": record.get("Id"),
                                        },
                                    )
                                )

                            if max_duration > 0 and duration_days > max_duration:
                                results.append(
                                    ValidationResult(
                                        run_id=self.run_id,
                                        entity_type=entity_type,
                                        validation_type="business_rules",
                                        field_name=f"{start_field}_{end_field}",
                                        severity="warning",
                                        message=f"Duration too long: {duration_days} days (maximum: {max_duration})",
                                        expected_value=f"≤{max_duration} days",
                                        actual_value=f"{duration_days} days",
                                        metadata={
                                            "rule_name": rule_name,
                                            "record_id": record.get("Id"),
                                        },
                                    )
                                )
                    else:
                        # Date parsing failed
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=f"{start_field}_{end_field}",
                                severity="error",
                                message=f"Could not parse date values",
                                expected_value="Valid date format",
                                actual_value=f"start_date={start_date}, end_date={end_date}",
                                metadata={
                                    "rule_name": rule_name,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )

                except Exception as e:
                    logger.error(
                        f"Error validating date range for {entity_type} record {record.get('Id')}: {e}"
                    )
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="business_rules",
                            field_name=f"{start_field}_{end_field}",
                            severity="error",
                            message=f"Date validation error: {str(e)}",
                            expected_value="Valid date format",
                            actual_value=f"start_date={start_date}, end_date={end_date}",
                            metadata={
                                "rule_name": rule_name,
                                "record_id": record.get("Id"),
                            },
                        )
                    )
            else:
                # Missing date fields
                missing_fields = []
                if not start_date:
                    missing_fields.append(start_field)
                if not end_date:
                    missing_fields.append(end_field)

                logger.debug(
                    f"Missing date fields for {entity_type} record {record.get('Id')}: {missing_fields}"
                )

        return results

    def _parse_date(self, date_value) -> Optional[datetime]:
        """Parse date value from various formats."""
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())
        elif isinstance(date_value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(date_value, fmt)
                        except ValueError:
                            continue
                except Exception:
                    pass

                logger.debug(f"Could not parse date string: {date_value}")
                return None
        else:
            logger.debug(
                f"Unsupported date type: {type(date_value)} for value: {date_value}"
            )
            return None

    def _validate_capacity_limits(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate capacity limit rules."""
        results = []

        # Get capacity fields and limits
        capacity_field = rule_config.get("capacity_field")
        current_field = rule_config.get("current_field")
        max_capacity = rule_config.get("max_capacity", 100)

        if not capacity_field or not current_field:
            logger.warning(
                f"Capacity validation requires both capacity_field and current_field for {entity_type}"
            )
            return results

        logger.debug(
            f"Validating capacity limits for {entity_type}: {capacity_field} vs {current_field}"
        )
        logger.debug(f"Maximum allowed capacity: {max_capacity}")

        for record in sample_data:
            capacity = record.get(capacity_field)
            current = record.get(current_field)

            if capacity is not None and current is not None:
                try:
                    capacity_val = int(capacity)
                    current_val = int(current)

                    logger.debug(
                        f"Record {record.get('Id')}: capacity={capacity_val}, current={current_val}"
                    )

                    # Check if current exceeds capacity
                    if current_val > capacity_val:
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=f"{capacity_field}_{current_field}",
                                severity="error",
                                message=f"Capacity exceeded: current ({current_val}) > capacity ({capacity_val})",
                                expected_value=f"current ≤ {capacity_val}",
                                actual_value=f"current={current_val}, capacity={capacity_val}",
                                metadata={
                                    "rule_name": rule_name,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )

                    # Check if approaching capacity limit
                    if capacity_val > 0:
                        utilization_rate = (current_val / capacity_val) * 100
                        logger.debug(f"Utilization rate: {utilization_rate:.1f}%")

                        if utilization_rate > 90:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=f"{capacity_field}_{current_field}",
                                    severity="warning",
                                    message=f"High capacity utilization: {utilization_rate:.1f}%",
                                    expected_value="<90% utilization",
                                    actual_value=f"{utilization_rate:.1f}% utilization",
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )

                        # Check if capacity is unreasonably low
                        if capacity_val < 1:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=capacity_field,
                                    severity="warning",
                                    message=f"Capacity value seems too low: {capacity_val}",
                                    expected_value="≥1",
                                    actual_value=capacity_val,
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )

                        # Check if capacity exceeds maximum allowed
                        if max_capacity > 0 and capacity_val > max_capacity:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=capacity_field,
                                    severity="warning",
                                    message=f"Capacity value seems too high: {capacity_val} (max allowed: {max_capacity})",
                                    expected_value=f"≤{max_capacity}",
                                    actual_value=capacity_val,
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )

                except (ValueError, TypeError) as e:
                    logger.debug(
                        f"Could not convert capacity values to integers for {entity_type} record {record.get('Id')}: {e}"
                    )
                    # Skip records with invalid numeric values
                    continue
            else:
                # Missing capacity fields
                missing_fields = []
                if capacity is None:
                    missing_fields.append(capacity_field)
                if current is None:
                    missing_fields.append(current_field)

                logger.debug(
                    f"Missing capacity fields for {entity_type} record {record.get('Id')}: {missing_fields}"
                )

        return results

    def _validate_business_constraints(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate business constraint rules."""
        results = []

        # Get constraint configuration
        constraint_type = rule_config.get("constraint_type")
        field_name = rule_config.get("field_name")
        allowed_values = rule_config.get("allowed_values", [])
        min_value = rule_config.get("min_value")
        max_value = rule_config.get("max_value")
        required = rule_config.get("required", False)

        if not field_name:
            return results

        for i, record in enumerate(
            sample_data[:3]
        ):  # Only check first 3 records for debug
            field_value = record.get(field_name)

            # Check if required field is missing
            if required and (field_value is None or field_value == ""):
                results.append(
                    ValidationResult(
                        run_id=self.run_id,
                        entity_type=entity_type,
                        validation_type="business_rules",
                        field_name=field_name,
                        severity="warning",
                        message=f"Required field '{field_name}' is missing",
                        expected_value="Required field",
                        actual_value="Missing",
                        metadata={
                            "rule_name": rule_name,
                            "record_id": record.get("Id"),
                        },
                    )
                )
                continue

            if field_value is not None and field_value != "":
                # Check allowed values
                if allowed_values and field_value not in allowed_values:
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="business_rules",
                            field_name=field_name,
                            severity="warning",
                            message=f"Value '{field_value}' not in allowed values",
                            expected_value=f"One of: {allowed_values}",
                            actual_value=field_value,
                            metadata={
                                "rule_name": rule_name,
                                "record_id": record.get("Id"),
                            },
                        )
                    )
                else:
                    pass  # No debug print for allowed_values check

                # Check string length constraints (for text fields)
                if isinstance(field_value, str):
                    string_length = len(field_value)

                    if min_value is not None and string_length < min_value:
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=field_name,
                                severity="warning",
                                message=f"Field '{field_name}' too short: {string_length} characters (minimum: {min_value})",
                                expected_value=f"≥{min_value} characters",
                                actual_value=f"{string_length} characters",
                                metadata={
                                    "rule_name": rule_name,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )

                    if max_value is not None and string_length > max_value:
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=field_name,
                                severity="warning",
                                message=f"Field '{field_name}' too long: {string_length} characters (maximum: {max_value})",
                                expected_value=f"≤{max_value} characters",
                                actual_value=f"{string_length} characters",
                                metadata={
                                    "rule_name": rule_name,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )

                # Check numeric range constraints (for numeric fields)
                elif min_value is not None or max_value is not None:
                    try:
                        numeric_value = float(field_value)

                        if min_value is not None and numeric_value < min_value:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=field_name,
                                    severity="warning",
                                    message=f"Value {numeric_value} below minimum {min_value}",
                                    expected_value=f"≥{min_value}",
                                    actual_value=numeric_value,
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )

                        if max_value is not None and numeric_value > max_value:
                            results.append(
                                ValidationResult(
                                    run_id=self.run_id,
                                    entity_type=entity_type,
                                    validation_type="business_rules",
                                    field_name=field_name,
                                    severity="warning",
                                    message=f"Value {numeric_value} above maximum {max_value}",
                                    expected_value=f"≤{max_value}",
                                    actual_value=numeric_value,
                                    metadata={
                                        "rule_name": rule_name,
                                        "record_id": record.get("Id"),
                                    },
                                )
                            )

                    except (ValueError, TypeError):
                        # Skip non-numeric values for range validation
                        continue
            else:
                pass  # No debug print for None or empty field

        return results

    def _validate_cross_field_rules(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate cross-field business rules."""
        results = []

        # Get the field rules configuration
        field_rules = rule_config.get("field_rules", [])

        if not field_rules:
            logger.warning(
                f"No field rules defined for cross-field validation in {entity_type}"
            )
            return results

        logger.debug(
            f"Validating {len(field_rules)} cross-field rules for {entity_type}"
        )

        for record in sample_data:
            for rule in field_rules:
                # Get rule configuration
                if_field = rule.get("if_field")
                if_value = rule.get("if_value")
                then_field = rule.get("then_field")
                then_required = rule.get("then_required", False)
                then_min_value = rule.get("then_min_value")
                then_max_value = rule.get("then_max_value")
                message = rule.get("message", "Cross-field validation failed")

                if not if_field or not then_field:
                    logger.warning(
                        f"Cross-field rule missing required fields: if_field={if_field}, then_field={then_field}"
                    )
                    continue

                # Check if the condition is met
                if_field_value = record.get(if_field)
                condition_met = if_field_value == if_value

                if condition_met:
                    logger.debug(
                        f"Condition met for {entity_type} record {record.get('Id')}: {if_field}={if_field_value}"
                    )

                    # Validate the dependent field based on the condition
                    then_field_value = record.get(then_field)

                    # Check if required field is missing
                    if then_required and (
                        then_field_value is None or then_field_value == ""
                    ):
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=then_field,
                                severity="warning",
                                message=message,
                                expected_value="Required field (due to cross-field rule)",
                                actual_value="Missing",
                                metadata={
                                    "rule_name": rule_name,
                                    "cross_field_rule": rule,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )
                        continue

                    # Check numeric range constraints if specified
                    if (
                        then_field_value is not None
                        and then_field_value != ""
                        and (then_min_value is not None or then_max_value is not None)
                    ):
                        try:
                            numeric_value = float(then_field_value)

                            if (
                                then_min_value is not None
                                and numeric_value < then_min_value
                            ):
                                results.append(
                                    ValidationResult(
                                        run_id=self.run_id,
                                        entity_type=entity_type,
                                        validation_type="business_rules",
                                        field_name=then_field,
                                        severity="warning",
                                        message=f"{message} - Value below minimum",
                                        expected_value=f"≥{then_min_value}",
                                        actual_value=numeric_value,
                                        metadata={
                                            "rule_name": rule_name,
                                            "cross_field_rule": rule,
                                            "record_id": record.get("Id"),
                                        },
                                    )
                                )

                            if (
                                then_max_value is not None
                                and numeric_value > then_max_value
                            ):
                                results.append(
                                    ValidationResult(
                                        run_id=self.run_id,
                                        entity_type=entity_type,
                                        validation_type="business_rules",
                                        field_name=then_field,
                                        severity="warning",
                                        message=f"{message} - Value above maximum",
                                        expected_value=f"≤{then_max_value}",
                                        actual_value=numeric_value,
                                        metadata={
                                            "rule_name": rule_name,
                                            "cross_field_rule": rule,
                                            "record_id": record.get("Id"),
                                        },
                                    )
                                )

                        except (ValueError, TypeError):
                            # Skip non-numeric values for range validation
                            logger.debug(
                                f"Could not convert {then_field} value to numeric for range validation: {then_field_value}"
                            )
                            continue

                    # If all validations pass, add a success result
                    if then_field_value is not None and then_field_value != "":
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=f"{if_field}_{then_field}",
                                severity="info",
                                message=f"Cross-field rule passed: {if_field}={if_value} -> {then_field} is valid",
                                expected_value=f"Valid {then_field} when {if_field}={if_value}",
                                actual_value=f"{then_field}={then_field_value}",
                                metadata={
                                    "rule_name": rule_name,
                                    "cross_field_rule": rule,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )
                else:
                    # Condition not met - this is fine, no validation needed
                    logger.debug(
                        f"Condition not met for {entity_type} record {record.get('Id')}: {if_field}={if_field_value} != {if_value}"
                    )

        return results

    def _validate_workflow_rules(
        self,
        entity_type: str,
        rule_name: str,
        rule_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate workflow step dependency and required field rules."""
        results = []

        # Get workflow configuration
        workflow_steps = rule_config.get("workflow_steps", [])

        if not workflow_steps:
            logger.warning(
                f"No workflow steps defined for workflow validation in {entity_type}"
            )
            return results

        logger.debug(
            f"Validating {len(workflow_steps)} workflow steps for {entity_type}"
        )

        for record in sample_data:
            for step in workflow_steps:
                # Get step configuration
                step_name = step.get("step")
                if not step_name:
                    logger.warning(f"Workflow step missing step name: {step}")
                    continue

                # Get required fields for the step
                required_fields = step.get("required_fields", [])
                if not required_fields:
                    logger.debug(
                        f"No required fields defined for workflow step '{step_name}' in {entity_type}"
                    )
                    continue

                # Check if all required fields are present
                missing_required_fields = [
                    f
                    for f in required_fields
                    if record.get(f) is None or record.get(f) == ""
                ]
                if missing_required_fields:
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="business_rules",
                            field_name=f"workflow_step_{step_name}_required_fields",
                            severity="warning",
                            message=f"Missing required fields for workflow step '{step_name}': {missing_required_fields}",
                            expected_value=f"All required fields for {step_name}",
                            actual_value=f"Missing: {missing_required_fields}",
                            metadata={
                                "rule_name": rule_name,
                                "workflow_step": step,
                                "record_id": record.get("Id"),
                            },
                        )
                    )
                    continue

                # Check workflow dependencies if specified
                depends_on = step.get("depends_on")
                if depends_on:
                    # Check if dependency fields are present
                    if isinstance(depends_on, str):
                        depends_on = [depends_on]

                    missing_dependencies = []
                    for dependency in depends_on:
                        # Look for a field that indicates this dependency step was completed
                        dependency_field = f"{dependency}_Completed__c"
                        if record.get(dependency_field) not in [
                            True,
                            "true",
                            "Yes",
                            "yes",
                        ]:
                            missing_dependencies.append(dependency)

                    if missing_dependencies:
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="business_rules",
                                field_name=f"workflow_step_{step_name}_dependencies",
                                severity="warning",
                                message=f"Missing workflow dependencies for step '{step_name}': {missing_dependencies}",
                                expected_value=f"All dependencies completed: {depends_on}",
                                actual_value=f"Missing: {missing_dependencies}",
                                metadata={
                                    "rule_name": rule_name,
                                    "workflow_step": step,
                                    "record_id": record.get("Id"),
                                },
                            )
                        )
                        continue

                # If all validations pass, add a success result
                results.append(
                    ValidationResult(
                        run_id=self.run_id,
                        entity_type=entity_type,
                        validation_type="business_rules",
                        field_name=f"workflow_step_{step_name}",
                        severity="info",
                        message=f"Workflow step '{step_name}' passed: all required fields present",
                        expected_value=f"All required fields for {step_name}",
                        actual_value=f"Required fields: {required_fields}",
                        metadata={
                            "rule_name": rule_name,
                            "workflow_step": step,
                            "record_id": record.get("Id"),
                        },
                    )
                )

        return results

    def _add_summary_metrics(self, results: List[ValidationResult]):
        """Add summary metrics for the validation run."""
        if not results:
            return

        # Calculate metrics
        total_checks = len(results)
        passed_checks = len([r for r in results if r.severity == "info"])
        warnings = len([r for r in results if r.severity == "warning"])
        errors = len([r for r in results if r.severity == "error"])
        critical = len([r for r in results if r.severity == "critical"])

        # Calculate data quality score
        quality_score = self._calculate_quality_score(results)

        # Add overall metrics
        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_total_checks",
                metric_value=total_checks,
                entity_type="all",
            )
        )

        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_passed_checks",
                metric_value=passed_checks,
                entity_type="all",
            )
        )

        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_warnings",
                metric_value=warnings,
                entity_type="all",
            )
        )

        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_errors",
                metric_value=errors,
                entity_type="all",
            )
        )

        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_critical",
                metric_value=critical,
                entity_type="all",
            )
        )

        # Calculate success rate
        if total_checks > 0:
            success_rate = ((total_checks - errors - critical) / total_checks) * 100
            self.add_metric(
                ValidationMetric(
                    run_id=self.run_id,
                    metric_name="business_rule_success_rate",
                    metric_value=success_rate,
                    entity_type="all",
                )
            )

        # Add data quality score metric
        self.add_metric(
            ValidationMetric(
                run_id=self.run_id,
                metric_name="business_rule_quality_score",
                metric_value=quality_score,
                entity_type="all",
            )
        )

        # Add trend analysis metrics if enabled
        if self.validation_settings.get("enable_trend_analysis", False):
            self._add_trend_metrics(results, quality_score)

    def _calculate_quality_score(self, results: List[ValidationResult]) -> float:
        """Calculate data quality score based on validation results."""
        if not results:
            return 100.0

        # Get quality scoring configuration
        scoring_config = self.validation_settings.get("quality_scoring", {})
        base_score = scoring_config.get("base_score", 100.0)

        # Calculate penalty based on violations
        total_penalty = 0.0

        for result in results:
            if result.severity == "critical":
                penalty = scoring_config.get("critical_violation_weight", 10.0)
            elif result.severity == "error":
                penalty = scoring_config.get("error_violation_weight", 5.0)
            elif result.severity == "warning":
                penalty = scoring_config.get("warning_violation_weight", 2.0)
            elif result.severity == "info":
                penalty = scoring_config.get("info_violation_weight", 0.5)
            else:
                penalty = 0.0

            total_penalty += penalty

        # Calculate final score
        final_score = max(0.0, base_score - total_penalty)

        logger.debug(
            f"Quality score calculation: base={base_score}, penalty={total_penalty}, final={final_score}"
        )
        return round(final_score, 2)

    def _add_trend_metrics(self, results: List[ValidationResult], quality_score: float):
        """Add trend analysis metrics for monitoring data quality over time."""
        try:
            # Get trend analysis configuration
            trend_config = self.validation_settings.get("trend_analysis", {})

            # Add trend-related metrics
            self.add_metric(
                ValidationMetric(
                    run_id=self.run_id,
                    metric_name="trend_quality_score_current",
                    metric_value=quality_score,
                    entity_type="all",
                )
            )

            # Add violation trend metrics
            critical_count = len([r for r in results if r.severity == "critical"])
            error_count = len([r for r in results if r.severity == "error"])
            warning_count = len([r for r in results if r.severity == "warning"])

            self.add_metric(
                ValidationMetric(
                    run_id=self.run_id,
                    metric_name="trend_critical_violations_current",
                    metric_value=critical_count,
                    entity_type="all",
                )
            )

            self.add_metric(
                ValidationMetric(
                    run_id=self.run_id,
                    metric_name="trend_error_violations_current",
                    metric_value=error_count,
                    entity_type="all",
                )
            )

            self.add_metric(
                ValidationMetric(
                    run_id=self.run_id,
                    metric_name="trend_warning_violations_current",
                    metric_value=warning_count,
                    entity_type="all",
                )
            )

            logger.debug(
                f"Added trend metrics: quality_score={quality_score}, violations={critical_count}/{error_count}/{warning_count}"
            )

        except Exception as e:
            logger.warning(f"Could not add trend metrics: {e}")

    def _get_salesforce_sample(
        self, entity_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get sample data from Salesforce for validation with smart sampling."""
        try:
            # Get performance configuration
            perf_config = self.validation_settings.get("performance", {})
            smart_sampling = perf_config.get("smart_sampling_enabled", True)
            max_sample = perf_config.get("max_sample_size", 1000)
            min_sample = perf_config.get("min_sample_size", 100)

            # Adjust sample size based on configuration
            if smart_sampling:
                # Use smaller samples for faster validation
                adjusted_limit = min(limit, max_sample)
                adjusted_limit = max(adjusted_limit, min_sample)
                logger.debug(
                    f"Smart sampling: adjusted limit from {limit} to {adjusted_limit}"
                )
                limit = adjusted_limit

            if entity_type == "volunteer":
                return self.salesforce_client.get_volunteer_sample(limit)
            elif entity_type == "organization":
                return self.salesforce_client.get_organization_sample(limit)
            elif entity_type == "event":
                return self.salesforce_client.get_event_sample(limit)
            elif entity_type == "student":
                return self.salesforce_client.get_student_sample(limit)
            elif entity_type == "teacher":
                return self.salesforce_client.get_teacher_sample(limit)
            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return []

        except Exception as e:
            logger.error(f"Error getting sample data for {entity_type}: {e}")
            return []

    def _load_custom_rules(self) -> Dict[str, Any]:
        """Load custom business rules from external sources."""
        try:
            custom_config = self.validation_settings.get("custom_rules", {})
            if not custom_config.get("enabled", False):
                return {}

            rule_sources = custom_config.get("rule_sources", [])
            custom_rules = {}

            for source in rule_sources:
                try:
                    if source == "config/validation.py":
                        # Rules already loaded from main config
                        continue
                    elif source.startswith("rules/"):
                        # Load from external rule files
                        logger.debug(f"Loading custom rules from {source}")
                        # This would implement file-based rule loading
                        # For now, we'll just log the intent
                        pass
                except Exception as e:
                    logger.warning(f"Could not load rules from {source}: {e}")

            return custom_rules

        except Exception as e:
            logger.error(f"Error loading custom rules: {e}")
            return {}

    def _apply_rule_templates(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule templates to simplify rule configuration."""
        try:
            custom_config = self.validation_settings.get("custom_rules", {})
            if not custom_config.get("enabled", False):
                return rule_config

            templates = custom_config.get("rule_templates", {})

            # Check if this rule uses a template
            template_name = rule_config.get("template")
            if template_name and template_name in templates:
                template = templates[template_name]
                logger.debug(f"Applying template '{template_name}' to rule")

                # Merge template with rule config
                merged_config = template.copy()
                merged_config.update(rule_config)
                return merged_config

            return rule_config

        except Exception as e:
            logger.warning(f"Could not apply rule template: {e}")
            return rule_config
