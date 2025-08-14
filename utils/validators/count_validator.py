# utils/validators/count_validator.py
"""
Count validation for comparing record counts between VMS and Salesforce.
"""

import logging
from typing import Any, Dict, List, Optional

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from utils.salesforce_client import SalesforceClient
from utils.validation_base import DataValidator

logger = logging.getLogger(__name__)


class CountValidator(DataValidator):
    """
    Validates record counts between VMS and Salesforce.

    This validator compares the number of records in VMS vs Salesforce
    for various entity types and reports discrepancies.
    """

    def __init__(self, run_id: Optional[int] = None, entity_type: str = "all"):
        """
        Initialize the count validator.

        Args:
            run_id: ID of the validation run
            entity_type: Type of entity to validate ('all', 'volunteer', 'organization', 'event', 'student', 'teacher')
        """
        super().__init__(run_id=run_id)
        self.entity_type = entity_type
        self.salesforce_client = None

        # Get count validation configuration
        self.count_config = get_config_section("validation_rules").get(
            "count_validation", {}
        )
        self.tolerance_percentage = self.count_config.get("tolerance_percentage", 5.0)
        self.max_retry_attempts = self.count_config.get("max_retry_attempts", 3)

        logger.debug(f"Initialized CountValidator for entity type: {entity_type}")

    def get_entity_type(self) -> str:
        """Get the entity type this validator handles."""
        return self.entity_type

    def validate(self) -> List[ValidationResult]:
        """
        Execute count validation.

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
                self._validate_entity_count(entity)

            # Add summary metrics
            self._add_summary_metrics()

            return self.results

        except Exception as e:
            logger.error(f"Count validation failed: {e}")
            raise
        finally:
            if self.salesforce_client:
                self.salesforce_client.close()

    def _validate_entity_count(self, entity_type: str):
        """Validate count for a specific entity type."""
        try:
            # Get VMS count
            vms_count = self._get_vms_count(entity_type)

            # Get Salesforce count
            sf_count = self._get_salesforce_count(entity_type)

            # Calculate difference and percentage
            difference = abs(vms_count - sf_count)
            percentage_diff = (difference / max(vms_count, 1)) * 100

            # Determine severity based on tolerance
            severity = self._determine_severity(percentage_diff)

            # Create validation result
            result = self.create_result(
                entity_type=entity_type,
                severity=severity,
                message=f"Record count comparison: VMS={vms_count}, Salesforce={sf_count}, "
                f"Difference={difference} ({percentage_diff:.2f}%)",
                validation_type="count",
                rule_name="CountValidator",
                expected_value=str(sf_count),
                actual_value=str(vms_count),
                difference=f"{difference} ({percentage_diff:.2f}%)",
                metadata={
                    "vms_count": vms_count,
                    "salesforce_count": sf_count,
                    "difference": difference,
                    "percentage_difference": percentage_diff,
                    "tolerance_percentage": self.tolerance_percentage,
                },
            )

            self.add_result(result)

            # Add metric
            metric = self.create_metric(
                metric_name="count_difference_percentage",
                metric_value=percentage_diff,
                metric_category="quality",
                metric_unit="percentage",
                entity_type=entity_type,
                metric_threshold=self.tolerance_percentage,
            )
            self.add_metric(metric)

            # Add count metrics
            vms_metric = self.create_metric(
                metric_name="vms_record_count",
                metric_value=vms_count,
                metric_category="business",
                metric_unit="count",
                entity_type=entity_type,
            )
            self.add_metric(vms_metric)

            sf_metric = self.create_metric(
                metric_name="salesforce_record_count",
                metric_value=sf_count,
                metric_category="business",
                metric_unit="count",
                entity_type=entity_type,
            )
            self.add_metric(sf_metric)

            logger.debug(
                f"Count validation for {entity_type}: VMS={vms_count}, SF={sf_count}, "
                f"Diff={percentage_diff:.2f}%, Severity={severity}"
            )

        except Exception as e:
            logger.error(f"Failed to validate count for {entity_type}: {e}")

            # Add error result
            error_result = self.create_result(
                entity_type=entity_type,
                severity="error",
                message=f"Count validation failed for {entity_type}: {str(e)}",
                validation_type="count",
                rule_name="CountValidator",
            )
            self.add_result(error_result)

    def _get_vms_count(self, entity_type: str) -> int:
        """Get record count from VMS database."""
        try:
            from models import db

            if entity_type == "volunteer":
                from models.volunteer import Volunteer

                count = Volunteer.query.count()
            elif entity_type == "organization":
                from models.organization import Organization

                count = Organization.query.count()
            elif entity_type == "event":
                from models.event import Event

                count = Event.query.count()
            elif entity_type == "student":
                from models.student import Student

                count = Student.query.count()
            elif entity_type == "teacher":
                from models.teacher import Teacher

                count = Teacher.query.count()
            else:
                raise ValueError(f"Unknown entity type: {entity_type}")

            return count

        except Exception as e:
            logger.error(f"Failed to get VMS count for {entity_type}: {e}")
            raise

    def _get_salesforce_count(self, entity_type: str) -> int:
        """Get record count from Salesforce."""
        try:
            if entity_type == "volunteer":
                return self.salesforce_client.get_volunteer_count()
            elif entity_type == "organization":
                return self.salesforce_client.get_organization_count()
            elif entity_type == "event":
                return self.salesforce_client.get_event_count()
            elif entity_type == "student":
                return self.salesforce_client.get_student_count()
            elif entity_type == "teacher":
                return self.salesforce_client.get_teacher_count()
            else:
                raise ValueError(f"Unknown entity type: {entity_type}")

        except Exception as e:
            logger.error(f"Failed to get Salesforce count for {entity_type}: {e}")
            raise

    def _determine_severity(self, percentage_diff: float) -> str:
        """
        Determine severity based on percentage difference.

        Args:
            percentage_diff: Percentage difference between VMS and Salesforce counts

        Returns:
            Severity level ('info', 'warning', 'error', 'critical')
        """
        if percentage_diff <= self.tolerance_percentage:
            return "info"
        elif percentage_diff <= self.tolerance_percentage * 2:
            return "warning"
        elif percentage_diff <= self.tolerance_percentage * 5:
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

            # Calculate success rate
            success_rate = (
                (info_count / total_results) * 100 if total_results > 0 else 0
            )

            # Add summary metrics
            summary_metric = self.create_metric(
                metric_name="count_validation_success_rate",
                metric_value=success_rate,
                metric_category="quality",
                metric_unit="percentage",
                entity_type="all",
            )
            self.add_metric(summary_metric)

            # Add severity breakdown metrics
            severity_metrics = [
                ("info_count", info_count),
                ("warning_count", warning_count),
                ("error_count", error_count),
                ("critical_count", critical_count),
            ]

            for metric_name, metric_value in severity_metrics:
                metric = self.create_metric(
                    metric_name=f"count_validation_{metric_name}",
                    metric_value=metric_value,
                    metric_category="quality",
                    metric_unit="count",
                    entity_type="all",
                )
                self.add_metric(metric)

            logger.debug(
                f"Added summary metrics: success_rate={success_rate:.2f}%, "
                f"total={total_results}, info={info_count}, warning={warning_count}, "
                f"error={error_count}, critical={critical_count}"
            )

        except Exception as e:
            logger.error(f"Failed to add summary metrics: {e}")

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of the count validation results."""
        summary = self.get_summary()

        # Add count-specific information
        summary["entity_type"] = self.entity_type
        summary["tolerance_percentage"] = self.tolerance_percentage
        summary["max_retry_attempts"] = self.max_retry_attempts

        return summary

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.salesforce_client:
            self.salesforce_client.close()
            self.salesforce_client = None


class VolunteerCountValidator(CountValidator):
    """Specialized validator for volunteer count validation."""

    def __init__(self, run_id: Optional[int] = None):
        super().__init__(run_id=run_id, entity_type="volunteer")

    def get_entity_type(self) -> str:
        return "volunteer"


class OrganizationCountValidator(CountValidator):
    """Specialized validator for organization count validation."""

    def __init__(self, run_id: Optional[int] = None):
        super().__init__(run_id=run_id, entity_type="organization")

    def get_entity_type(self) -> str:
        return "organization"


class EventCountValidator(CountValidator):
    """Specialized validator for event count validation."""

    def __init__(self, run_id: Optional[int] = None):
        super().__init__(run_id=run_id, entity_type="event")

    def get_entity_type(self) -> str:
        return "event"


class StudentCountValidator(CountValidator):
    """Specialized validator for student count validation."""

    def __init__(self, run_id: Optional[int] = None):
        super().__init__(run_id=run_id, entity_type="student")

    def get_entity_type(self) -> str:
        return "student"


class TeacherCountValidator(CountValidator):
    """Specialized validator for teacher count validation."""

    def __init__(self, run_id: Optional[int] = None):
        super().__init__(run_id=run_id, entity_type="teacher")

    def get_entity_type(self) -> str:
        return "teacher"
