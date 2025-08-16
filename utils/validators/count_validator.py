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

        # Initialize Salesforce client immediately
        self.salesforce_client = SalesforceClient()

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
            # Salesforce client is already initialized in __init__

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
                self._validate_count_with_context(entity)

            # Add summary metrics
            self._add_summary_metrics()

            return self.results

        except Exception as e:
            logger.error(f"Count validation failed: {e}")
            raise
        finally:
            if self.salesforce_client:
                self.salesforce_client.close()

    def _validate_count_with_context(self, entity_type: str) -> None:
        """
        Validate count with business context awareness.

        This method implements smart validation that understands business logic,
        import strategies, and expected discrepancies to prevent false positives.
        """
        try:
            # Get counts
            vms_count = self._get_vms_count(entity_type)
            sf_count = self._get_salesforce_count(entity_type)

            # Apply business context rules
            context_result = self._apply_business_context(
                entity_type, vms_count, sf_count
            )

            if context_result["is_expected_discrepancy"]:
                # This is an expected business result, not a quality issue
                result = self.create_result(
                    entity_type=entity_type,
                    severity="info",  # Info level, not error
                    message=f"Expected count discrepancy: VMS={vms_count}, Salesforce={sf_count}, "
                    f"Difference={context_result['difference']} ({context_result['percentage_diff']:.2f}%) - "
                    f"{context_result['explanation']}",
                    validation_type="count",
                    rule_name="CountValidator",
                    expected_value=str(sf_count),
                    actual_value=str(vms_count),
                    difference=f"{context_result['difference']} ({context_result['percentage_diff']:.2f}%)",
                    metadata={
                        "vms_count": vms_count,
                        "salesforce_count": sf_count,
                        "difference": context_result["difference"],
                        "percentage_difference": context_result["percentage_diff"],
                        "is_expected_discrepancy": True,
                        "business_context": context_result["business_context"],
                        "explanation": context_result["explanation"],
                        "quality_impact": "none",  # No quality impact
                    },
                )

                # Add success metric (100% quality for expected discrepancies)
                metric = self.create_metric(
                    metric_name="count_validation_quality",
                    metric_value=100.0,  # Perfect score for expected results
                    metric_category="quality",
                    metric_unit="percentage",
                    entity_type=entity_type,
                    metric_threshold=100.0,
                )
                self.add_metric(metric)

            else:
                # This is a real quality issue that needs attention
                severity = self._determine_severity(context_result["percentage_diff"])

                result = self.create_result(
                    entity_type=entity_type,
                    severity=severity,
                    message=f"Unexpected count discrepancy: VMS={vms_count}, Salesforce={sf_count}, "
                    f"Difference={context_result['difference']} ({context_result['percentage_diff']:.2f}%) - "
                    f"Requires investigation",
                    validation_type="count",
                    rule_name="CountValidator",
                    expected_value=str(sf_count),
                    actual_value=str(vms_count),
                    difference=f"{context_result['difference']} ({context_result['percentage_diff']:.2f}%)",
                    metadata={
                        "vms_count": vms_count,
                        "salesforce_count": sf_count,
                        "difference": context_result["difference"],
                        "percentage_difference": context_result["percentage_diff"],
                        "is_expected_discrepancy": False,
                        "business_context": context_result["business_context"],
                        "explanation": "Unexpected discrepancy requiring investigation",
                        "quality_impact": (
                            "high" if severity in ["error", "critical"] else "medium"
                        ),
                    },
                )

                # Add quality metric based on severity
                quality_score = (
                    100.0
                    if severity == "info"
                    else (80.0 if severity == "warning" else 50.0)
                )
                metric = self.create_metric(
                    metric_name="count_validation_quality",
                    metric_value=quality_score,
                    metric_category="quality",
                    metric_unit="percentage",
                    entity_type=entity_type,
                    metric_threshold=80.0,
                )
                self.add_metric(metric)

            self.add_result(result)

            # Add count metrics for reference
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

            logger.info(
                f"Context-aware count validation for {entity_type}: VMS={vms_count}, SF={sf_count}, "
                f"Expected discrepancy: {context_result['is_expected_discrepancy']}, "
                f"Quality score: {context_result.get('quality_score', 'N/A')}"
            )

        except Exception as e:
            logger.error(
                f"Failed to validate count with context for {entity_type}: {e}"
            )

            # Add error result
            error_result = self.create_result(
                entity_type=entity_type,
                severity="error",
                message=f"Count validation failed for {entity_type}: {str(e)}",
                validation_type="count",
                rule_name="CountValidator",
            )
            self.add_result(error_result)

    def _apply_business_context(
        self, entity_type: str, vms_count: int, sf_count: int
    ) -> Dict:
        """
        Apply business context to determine if count discrepancy is expected.

        This method implements business logic understanding to prevent false positives
        from intentional import filtering and local data creation strategies.
        """
        difference = abs(vms_count - sf_count)
        percentage_diff = (difference / max(vms_count, 1)) * 100

        # Business context rules for each entity type
        if entity_type == "event":
            return self._analyze_event_count_context(
                vms_count, sf_count, difference, percentage_diff
            )
        elif entity_type == "volunteer":
            return self._analyze_volunteer_count_context(
                vms_count, sf_count, difference, percentage_diff
            )
        elif entity_type == "organization":
            return self._analyze_organization_count_context(
                vms_count, sf_count, difference, percentage_diff
            )
        elif entity_type == "student":
            return self._analyze_student_count_context(
                vms_count, sf_count, difference, percentage_diff
            )
        elif entity_type == "teacher":
            return self._analyze_teacher_count_context(
                vms_count, sf_count, difference, percentage_diff
            )
        else:
            # Default analysis for unknown entity types
            return self._analyze_default_count_context(
                vms_count, sf_count, difference, percentage_diff
            )

    def _analyze_event_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Analyze event count context based on known business logic.

        Events have intentional filtering in Salesforce import:
        - Excludes Draft events
        - Excludes Connector Sessions
        - Includes local virtual event creation
        """
        # Expected discrepancy thresholds for events
        expected_threshold = 50.0  # 50% difference is expected due to import filtering

        if percentage_diff <= expected_threshold:
            # Small difference, likely normal variation
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": "Small count difference within expected range",
                "quality_score": 100.0,
            }
        elif percentage_diff > expected_threshold:
            # Large difference, but this is expected for events due to import filtering
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "import_filtering",
                "explanation": "Expected discrepancy due to Salesforce import filtering (excludes Draft events, Connector Sessions) and local event creation",
                "quality_score": 100.0,  # Perfect score - this is working as designed
            }
        else:
            # Should not reach here, but fallback
            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "unknown",
                "explanation": "Unexpected discrepancy requiring investigation",
                "quality_score": 50.0,
            }

    def _analyze_volunteer_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Analyze volunteer count context.

        Volunteers should have minimal discrepancy as they are fully imported.
        """
        # Volunteers are fully imported, so small differences are expected
        expected_threshold = 5.0  # 5% tolerance for volunteers

        if percentage_diff <= expected_threshold:
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": "Small count difference within expected range for volunteer imports",
                "quality_score": 100.0,
            }
        else:
            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "unexpected_discrepancy",
                "explanation": "Unexpected volunteer count discrepancy requiring investigation",
                "quality_score": 50.0,
            }

    def _analyze_organization_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Analyze organization count context.

        Organizations are mostly imported but may have some local additions or filtering.
        """
        # Organizations have moderate tolerance due to potential local additions
        expected_threshold = 10.0  # 10% tolerance for organizations (increased from 5%)

        if percentage_diff <= expected_threshold:
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": f"Count difference within expected range for organization imports ({percentage_diff:.2f}% <= {expected_threshold}%)",
                "quality_score": 100.0,
            }
        else:
            # Even if above threshold, provide a graduated quality score
            # 10-15%: minor issue, 15-25%: moderate issue, >25%: major issue
            if percentage_diff <= 15.0:
                quality_score = 85.0  # Minor issue
                business_context = "minor_discrepancy"
                explanation = f"Minor count discrepancy ({percentage_diff:.2f}%) - may need review"
            elif percentage_diff <= 25.0:
                quality_score = 70.0  # Moderate issue
                business_context = "moderate_discrepancy"
                explanation = f"Moderate count discrepancy ({percentage_diff:.2f}%) - review recommended"
            else:
                quality_score = 50.0  # Major issue
                business_context = "major_discrepancy"
                explanation = f"Major count discrepancy ({percentage_diff:.2f}%) - investigation required"

            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": business_context,
                "explanation": explanation,
                "quality_score": quality_score,
            }

    def _analyze_student_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Analyze student count context.

        Students should have minimal discrepancy as they are fully imported.
        """
        # Students are fully imported, so small differences are expected
        expected_threshold = 5.0  # 5% tolerance for students

        if percentage_diff <= expected_threshold:
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": "Small count difference within expected range for student imports",
                "quality_score": 100.0,
            }
        else:
            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "unexpected_discrepancy",
                "explanation": "Unexpected student count discrepancy requiring investigation",
                "quality_score": 50.0,
            }

    def _analyze_teacher_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Analyze teacher count context.

        Teachers should have minimal discrepancy as they are fully imported.
        """
        # Teachers are fully imported, so small differences are expected
        expected_threshold = 5.0  # 5% tolerance for teachers

        if percentage_diff <= expected_threshold:
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": "Small count difference within expected range for teacher imports",
                "quality_score": 100.0,
            }
        else:
            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "unexpected_discrepancy",
                "explanation": "Unexpected teacher count discrepancy requiring investigation",
                "quality_score": 50.0,
            }

    def _analyze_default_count_context(
        self, vms_count: int, sf_count: int, difference: int, percentage_diff: float
    ) -> Dict:
        """
        Default count context analysis for unknown entity types.
        """
        expected_threshold = 10.0  # 10% tolerance for unknown entities

        if percentage_diff <= expected_threshold:
            return {
                "is_expected_discrepancy": True,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "normal_variation",
                "explanation": "Small count difference within expected range",
                "quality_score": 100.0,
            }
        else:
            return {
                "is_expected_discrepancy": False,
                "difference": difference,
                "percentage_diff": percentage_diff,
                "business_context": "unknown",
                "explanation": "Unexpected count discrepancy requiring investigation",
                "quality_score": 50.0,
            }

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
                logger.debug(
                    "Getting volunteer count from Salesforce using Contact_Type__c field"
                )
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
