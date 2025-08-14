"""
Relationship integrity validation for Salesforce data quality.

This validator checks that relationships between entities are valid and complete,
including orphaned record detection, circular reference detection, and foreign key validation.
"""

import json
import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from utils.salesforce_client import SalesforceClient
from utils.validation_base import DataValidator

logger = logging.getLogger(__name__)


class RelationshipValidator(DataValidator):
    """
    Validates relationship integrity for Salesforce records.

    This validator ensures that:
    - Required relationships are properly established
    - No orphaned records exist
    - No circular references exist
    - Foreign key relationships are valid
    - Relationship fields are properly populated
    """

    def __init__(self, run_id: Optional[int] = None, entity_type: str = "all"):
        super().__init__(run_id=run_id)
        self.entity_type = entity_type
        self.salesforce_client = None

        # Get relationship validation configuration
        self.relationship_config = get_config_section("relationship_rules")
        self.entity_relationships = self.relationship_config.get(
            "entity_relationships", {}
        )
        self.validation_settings = self.relationship_config.get(
            "relationship_validation", {}
        )
        self.business_rules = self.relationship_config.get("business_rules", {})

        logger.debug(
            f"Initialized RelationshipValidator for entity type: {entity_type}"
        )

    def validate(self) -> List[ValidationResult]:
        """Run relationship integrity validation."""
        try:
            if not self.salesforce_client:
                self.salesforce_client = SalesforceClient()

            results = []
            entity_types = (
                [self.entity_type]
                if self.entity_type != "all"
                else list(self.entity_relationships.keys())
            )

            for entity_type in entity_types:
                if entity_type in self.entity_relationships:
                    logger.info(f"Validating relationships for {entity_type}...")
                    entity_results = self._validate_entity_relationships(entity_type)
                    results.extend(entity_results)

            # Add summary metrics
            self._add_summary_metrics(results)

            logger.info(
                f"Relationship validation completed with {len(results)} results"
            )
            return results

        except Exception as e:
            logger.error(f"Relationship validation failed: {e}")
            raise

    def _validate_entity_relationships(
        self, entity_type: str
    ) -> List[ValidationResult]:
        """Validate relationships for a specific entity type."""
        results = []

        try:
            # Get entity configuration
            entity_config = self.entity_relationships.get(entity_type, {})
            required_relationships = entity_config.get("required_relationships", {})
            optional_relationships = entity_config.get("optional_relationships", {})

            # Get sample data for validation
            sample_data = self._get_salesforce_sample(entity_type, limit=100)

            if not sample_data:
                logger.warning(f"No sample data found for {entity_type}")
                return results

            # Validate required relationships
            for field_name, field_config in required_relationships.items():
                field_results = self._validate_required_relationship(
                    entity_type, field_name, field_config, sample_data
                )
                results.extend(field_results)

            # Validate optional relationships
            for field_name, field_config in optional_relationships.items():
                field_results = self._validate_optional_relationship(
                    entity_type, field_name, field_config, sample_data
                )
                results.extend(field_results)

            # Check for orphaned records
            if self.validation_settings.get("orphaned_record_detection", False):
                orphaned_results = self._detect_orphaned_records(
                    entity_type, sample_data
                )
                results.extend(orphaned_results)

            # Check for circular references
            if self.validation_settings.get("circular_reference_detection", False):
                circular_results = self._detect_circular_references(
                    entity_type, sample_data
                )
                results.extend(circular_results)

        except Exception as e:
            logger.error(f"Error validating relationships for {entity_type}: {e}")
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="relationship_integrity",
                    field_name="relationships",
                    severity="error",
                    message=f"Failed to validate relationships: {e}",
                    metadata={"error": str(e)},
                )
            )

        return results

    def _validate_required_relationship(
        self,
        entity_type: str,
        field_name: str,
        field_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate that required relationships are properly established."""
        results = []
        missing_count = 0
        total_count = len(sample_data)

        for record in sample_data:
            field_value = record.get(field_name)

            if not field_value or field_value == "" or field_value == "null":
                missing_count += 1
                results.append(
                    ValidationResult(
                        run_id=self.run_id,
                        entity_type=entity_type,
                        validation_type="required_relationship",
                        field_name=field_name,
                        severity=field_config.get("severity", "error"),
                        message=f"Required relationship field '{field_name}' is missing",
                        metadata={
                            "record_id": record.get("Id"),
                            "field_config": field_config,
                            "business_rule": field_config.get("description", ""),
                        },
                    )
                )

        # Add summary metric
        completeness_percentage = (
            ((total_count - missing_count) / total_count) * 100
            if total_count > 0
            else 0
        )

        if missing_count > 0:
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="relationship_completeness",
                    field_name=field_name,
                    severity="warning" if completeness_percentage >= 90 else "error",
                    message=f"Required relationship '{field_name}' completeness: {completeness_percentage:.1f}%",
                    metadata={
                        "total_records": total_count,
                        "missing_records": missing_count,
                        "completeness_percentage": completeness_percentage,
                        "threshold": self.validation_settings.get(
                            "validation_thresholds", {}
                        ).get("relationship_completeness", 95.0),
                    },
                )
            )

        return results

    def _validate_optional_relationship(
        self,
        entity_type: str,
        field_name: str,
        field_config: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """Validate that optional relationships are properly formatted when present."""
        results = []
        populated_count = 0
        total_count = len(sample_data)

        for record in sample_data:
            field_value = record.get(field_name)

            if field_value and field_value != "" and field_value != "null":
                populated_count += 1
                # Validate the relationship format if it exists
                format_result = self._validate_relationship_format(
                    entity_type, field_name, field_value, field_config, record
                )
                if format_result:
                    results.append(format_result)

        # Add summary metric for optional relationships
        if total_count > 0:
            results.append(
                ValidationResult(
                    run_id=self.run_id,
                    entity_type=entity_type,
                    validation_type="optional_relationship_population",
                    field_name=field_name,
                    severity="info",
                    message=f"Optional relationship '{field_name}' population: {populated_count}/{total_count} ({populated_count/total_count*100:.1f}%)",
                    metadata={
                        "total_records": total_count,
                        "populated_records": populated_count,
                        "population_percentage": (populated_count / total_count) * 100,
                    },
                )
            )

        return results

    def _validate_relationship_format(
        self,
        entity_type: str,
        field_name: str,
        field_value: Any,
        field_config: Dict[str, Any],
        record: Dict[str, Any],
    ) -> Optional[ValidationResult]:
        """Validate the format of a relationship field value."""
        try:
            field_type = field_config.get("type", "lookup")

            if field_type == "lookup":
                # Validate that lookup ID is properly formatted (18-character Salesforce ID)
                if not self._is_valid_salesforce_id(field_value):
                    return ValidationResult(
                        run_id=self.run_id,
                        entity_type=entity_type,
                        validation_type="relationship_format",
                        field_name=field_name,
                        severity="warning",
                        message=f"Invalid lookup ID format for '{field_name}'",
                        metadata={
                            "record_id": record.get("Id"),
                            "field_value": field_value,
                            "expected_format": "18-character Salesforce ID",
                            "field_config": field_config,
                        },
                    )

            elif field_type == "picklist":
                # Validate picklist values
                allowed_values = field_config.get("allowed_values", [])
                if allowed_values and field_value not in allowed_values:
                    return ValidationResult(
                        run_id=self.run_id,
                        entity_type=entity_type,
                        validation_type="relationship_format",
                        field_name=field_name,
                        severity="warning",
                        message=f"Invalid picklist value for '{field_name}'",
                        metadata={
                            "record_id": record.get("Id"),
                            "field_value": field_value,
                            "allowed_values": allowed_values,
                            "field_config": field_config,
                        },
                    )

        except Exception as e:
            logger.warning(
                f"Error validating relationship format for {field_name}: {e}"
            )

        return None

    def _detect_orphaned_records(
        self, entity_type: str, sample_data: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Detect orphaned records that have no valid relationships."""
        results = []

        try:
            entity_config = self.entity_relationships.get(entity_type, {})
            required_relationships = entity_config.get("required_relationships", {})

            orphaned_count = 0
            total_count = len(sample_data)

            for record in sample_data:
                is_orphaned = True

                # Check if record has at least one valid required relationship
                for field_name, field_config in required_relationships.items():
                    field_value = record.get(field_name)
                    if field_value and field_value != "" and field_value != "null":
                        is_orphaned = False
                        break

                if is_orphaned:
                    orphaned_count += 1
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="orphaned_record",
                            field_name="relationships",
                            severity="error",
                            message=f"Orphaned record detected - no valid required relationships",
                            metadata={
                                "record_id": record.get("Id"),
                                "required_relationships": list(
                                    required_relationships.keys()
                                ),
                                "record_data": {
                                    k: v
                                    for k, v in record.items()
                                    if k in required_relationships
                                },
                            },
                        )
                    )

            # Add summary metric
            if total_count > 0:
                orphaned_percentage = (orphaned_count / total_count) * 100
                threshold = self.validation_settings.get(
                    "validation_thresholds", {}
                ).get("orphaned_records", 5.0)

                if orphaned_percentage > threshold:
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="orphaned_records_summary",
                            field_name="relationships",
                            severity=(
                                "warning" if orphaned_percentage <= 10 else "error"
                            ),
                            message=f"Orphaned records detected: {orphaned_count}/{total_count} ({orphaned_percentage:.1f}%)",
                            metadata={
                                "total_records": total_count,
                                "orphaned_records": orphaned_count,
                                "orphaned_percentage": orphaned_percentage,
                                "threshold": threshold,
                            },
                        )
                    )

        except Exception as e:
            logger.error(f"Error detecting orphaned records for {entity_type}: {e}")

        return results

    def _detect_circular_references(
        self, entity_type: str, sample_data: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Detect circular references in relationship data."""
        results = []

        try:
            # This is a simplified circular reference detection
            # In a real implementation, you would need to traverse the relationship graph
            # For now, we'll check for basic self-references

            circular_count = 0
            total_count = len(sample_data)

            for record in sample_data:
                record_id = record.get("Id")

                # Check for self-references in relationship fields
                for field_name in self.entity_relationships.get(entity_type, {}).get(
                    "required_relationships", {}
                ):
                    field_value = record.get(field_name)
                    if field_value == record_id:
                        circular_count += 1
                        results.append(
                            ValidationResult(
                                run_id=self.run_id,
                                entity_type=entity_type,
                                validation_type="circular_reference",
                                field_name=field_name,
                                severity="error",
                                message=f"Circular reference detected - record references itself",
                                metadata={
                                    "record_id": record_id,
                                    "field_name": field_name,
                                    "field_value": field_value,
                                },
                            )
                        )

            # Add summary metric
            if total_count > 0:
                circular_percentage = (circular_count / total_count) * 100
                threshold = self.validation_settings.get(
                    "validation_thresholds", {}
                ).get("circular_references", 0.0)

                if circular_percentage > threshold:
                    results.append(
                        ValidationResult(
                            run_id=self.run_id,
                            entity_type=entity_type,
                            validation_type="circular_references_summary",
                            field_name="relationships",
                            severity="error",
                            message=f"Circular references detected: {circular_count}/{total_count} ({circular_percentage:.1f}%)",
                            metadata={
                                "total_records": total_count,
                                "circular_records": circular_count,
                                "circular_percentage": circular_percentage,
                                "threshold": threshold,
                            },
                        )
                    )

        except Exception as e:
            logger.error(f"Error detecting circular references for {entity_type}: {e}")

        return results

    def _get_salesforce_sample(
        self, entity_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get a sample of records from Salesforce for relationship validation."""
        try:
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
                logger.warning(f"Unknown entity type for sampling: {entity_type}")
                return []
        except Exception as e:
            logger.error(f"Error getting Salesforce sample for {entity_type}: {e}")
            return []

    def _is_valid_salesforce_id(self, value: Any) -> bool:
        """Check if a value is a valid Salesforce ID format."""
        if not value or not isinstance(value, str):
            return False

        # Salesforce IDs are 15 or 18 characters long and contain only alphanumeric characters
        return len(value) in [15, 18] and value.isalnum()

    def _add_summary_metrics(self, results: List[ValidationResult]):
        """Add summary metrics for the validation run."""
        try:
            if not results:
                return

            # Calculate overall metrics
            total_checks = len(results)
            error_count = len([r for r in results if r.severity == "error"])
            warning_count = len([r for r in results if r.severity == "warning"])
            info_count = len([r for r in results if r.severity == "info"])

            # Calculate relationship completeness
            relationship_results = [
                r for r in results if r.validation_type == "relationship_completeness"
            ]
            if relationship_results:
                avg_completeness = sum(
                    r.metadata_dict.get("completeness_percentage", 0)
                    for r in relationship_results
                ) / len(relationship_results)
            else:
                avg_completeness = 100.0

            # Add summary metric
            summary_metric = ValidationMetric(
                run_id=self.run_id,
                metric_name="relationship_integrity_summary",
                metric_value=avg_completeness,
                metric_unit="percentage",
                metadata=json.dumps(
                    {
                        "total_checks": total_checks,
                        "error_count": error_count,
                        "warning_count": warning_count,
                        "info_count": info_count,
                        "average_completeness": avg_completeness,
                        "validation_thresholds": self.validation_settings.get(
                            "validation_thresholds", {}
                        ),
                    }
                ),
            )

            self.add_metric(summary_metric)

        except Exception as e:
            logger.error(f"Error adding summary metrics: {e}")
