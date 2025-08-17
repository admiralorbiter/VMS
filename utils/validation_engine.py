# utils/validation_engine.py
"""
Validation engine for orchestrating Salesforce data validation.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult
from models.validation.run import ValidationRun
from utils.validation_base import DataValidator, ValidationContext
from utils.validators.business_rule_validator import BusinessRuleValidator
from utils.validators.count_validator import CountValidator
from utils.validators.data_type_validator import DataTypeValidator
from utils.validators.field_completeness_validator import FieldCompletenessValidator
from utils.validators.relationship_validator import RelationshipValidator

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Main validation engine for orchestrating Salesforce data validation.

    This engine provides:
    - Validation run management
    - Parallel validation execution
    - Progress tracking
    - Result aggregation
    - Error handling and recovery
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation engine.

        Args:
            config: Validation configuration
        """
        self.config = config or get_config_section("validation_rules")
        self.executor = ThreadPoolExecutor(max_workers=4)  # Configurable
        self.active_runs: Dict[int, ValidationRun] = {}
        self.run_lock = threading.Lock()

        logger.info("Validation engine initialized")

    def create_validation_run(
        self,
        run_type: str,
        name: str = None,
        description: str = None,
        user_id: Optional[int] = None,
    ) -> ValidationRun:
        """
        Create a new validation run.

        Args:
            run_type: Type of validation ('fast', 'slow', 'realtime')
            name: Human-readable name for the run
            description: Optional description
            user_id: ID of the user initiating the validation

        Returns:
            ValidationRun instance
        """
        try:
            run = ValidationRun(
                run_type=run_type,
                name=name or f"{run_type.title()} Validation Run",
                description=description,
                created_by=user_id,
                status="running",
            )

            from models import db

            db.session.add(run)
            db.session.commit()

            with self.run_lock:
                self.active_runs[run.id] = run

            logger.info(f"Created validation run {run.id} of type {run_type}")
            return run

        except Exception as e:
            logger.error(f"Failed to create validation run: {e}")
            raise

    def run_fast_validation(self, user_id: Optional[int] = None) -> ValidationRun:
        """
        Run fast validation checks.

        Args:
            user_id: ID of the user initiating the validation

        Returns:
            ValidationRun instance
        """
        run = self.create_validation_run("fast", user_id=user_id)

        try:
            # Fast validations that can run quickly
            validators = [CountValidator(run_id=run.id, entity_type="all")]

            # Execute validations
            self._execute_validations(run, validators)

            return run

        except Exception as e:
            logger.error(f"Fast validation failed: {e}")
            run.mark_failed(str(e))
            self._finalize_run(run)
            raise

    def run_slow_validation(self, user_id: Optional[int] = None) -> ValidationRun:
        """
        Run slow validation checks.

        Args:
            user_id: ID of the user initiating the validation

        Returns:
            ValidationRun instance
        """
        run = self.create_validation_run("slow", user_id=user_id)

        try:
            # Slow validations that take more time
            validators = [
                CountValidator(run_id=run.id, entity_type="all"),
                FieldCompletenessValidator(run_id=run.id, entity_type="all"),
                DataTypeValidator(run_id=run.id, entity_type="all"),
                RelationshipValidator(run_id=run.id, entity_type="all"),
                BusinessRuleValidator(run_id=run.id, entity_type="all"),
                # Add more validators as they're implemented
            ]

            # Execute validations
            self._execute_validations(run, validators)

            return run

        except Exception as e:
            logger.error(f"Slow validation failed: {e}")
            run.mark_failed(str(e))
            self._finalize_run(run)
            raise

    def run_custom_validation(
        self,
        validators: List[DataValidator],
        run_type: str = "custom",
        name: str = None,
        user_id: Optional[int] = None,
    ) -> ValidationRun:
        """
        Run custom validation with specified validators.

        Args:
            validators: List of validators to execute
            run_type: Type of validation run
            name: Name for the validation run
            user_id: ID of the user initiating the validation

        Returns:
            ValidationRun instance
        """
        run = self.create_validation_run(run_type, name=name, user_id=user_id)

        try:
            # Set run_id for all validators
            for validator in validators:
                validator.run_id = run.id

            # Execute validations
            self._execute_validations(run, validators)

            return run

        except Exception as e:
            logger.error(f"Custom validation failed: {e}")
            run.mark_failed(str(e))
            self._finalize_run(run)
            raise

    def run_comprehensive_validation(
        self,
        entity_type: str = "all",
        run_type: str = "comprehensive",
        name: str = None,
        user_id: Optional[int] = None,
    ) -> ValidationRun:
        """
        Run comprehensive validation for all validation types on specified entity.

        Args:
            entity_type: Type of entity to validate ('all', 'volunteer', 'organization', 'event', 'student', 'teacher', 'school', 'district')
            run_type: Type of validation run
            name: Name for the validation run
            user_id: ID of the user initiating the validation

        Returns:
            ValidationRun instance
        """
        # Create all validators for the entity type
        validators = self._create_comprehensive_validators(entity_type)

        run_name = name or f"Comprehensive {entity_type.title()} Validation"
        run = self.create_validation_run(run_type, name=run_name, user_id=user_id)

        try:
            # Set run_id for all validators
            for validator in validators:
                validator.run_id = run.id

            # Execute validations
            self._execute_validations(run, validators)

            return run

        except Exception as e:
            logger.error(f"Comprehensive validation failed: {e}")
            run.mark_failed(str(e))
            self._finalize_run(run)
            raise

    def _create_comprehensive_validators(self, entity_type: str) -> List[DataValidator]:
        """
        Create all available validators for comprehensive validation.

        Args:
            entity_type: Type of entity to validate

        Returns:
            List of configured validators
        """
        validators = []

        # Count validation (always included)
        count_validator = CountValidator(run_id=None, entity_type=entity_type)
        validators.append(count_validator)

        # Field completeness validation
        field_validator = FieldCompletenessValidator(
            run_id=None, entity_type=entity_type
        )
        validators.append(field_validator)

        # Data type validation
        data_type_validator = DataTypeValidator(run_id=None, entity_type=entity_type)
        validators.append(data_type_validator)

        # Business rule validation
        business_rule_validator = BusinessRuleValidator(
            run_id=None, entity_type=entity_type
        )
        validators.append(business_rule_validator)

        # Relationship validation
        relationship_validator = RelationshipValidator(
            run_id=None, entity_type=entity_type
        )
        validators.append(relationship_validator)

        logger.info(
            f"Created {len(validators)} validators for comprehensive {entity_type} validation"
        )
        return validators

    def _execute_validations(self, run: ValidationRun, validators: List[DataValidator]):
        """
        Execute a list of validators and collect results.

        Args:
            run: Validation run instance
            validators: List of validators to execute
        """
        try:
            total_validators = len(validators)
            completed_validators = 0

            # Execute validators (can be parallel in the future)
            all_results = []
            all_metrics = []

            for validator in validators:
                try:
                    logger.info(f"Executing validator: {validator.__class__.__name__}")

                    # Execute validation
                    results = validator.validate_with_timing()
                    metrics = validator.metrics

                    # Collect results and metrics
                    all_results.extend(results)
                    all_metrics.extend(metrics)

                    # Update progress
                    completed_validators += 1
                    run.update_progress(completed_validators, total_validators)

                    logger.info(
                        f"Completed validator {validator.__class__.__name__}: "
                        f"{len(results)} results, {len(metrics)} metrics"
                    )

                except Exception as e:
                    logger.error(
                        f"Validator {validator.__class__.__name__} failed: {e}"
                    )

                    # Add error result
                    error_result = ValidationResult.create_result(
                        run_id=run.id,
                        entity_type=validator.get_entity_type(),
                        severity="error",
                        message=f"Validator {validator.__class__.__name__} failed: {str(e)}",
                        validation_type="system",
                        rule_name=validator.__class__.__name__,
                    )
                    all_results.append(error_result)

                    # Continue with other validators if configured
                    if not self._should_continue_on_error():
                        raise

                finally:
                    # Clean up validator resources
                    validator.cleanup()

            # Save all results and metrics
            self._save_validation_data(run, all_results, all_metrics)

            # Update run statistics with actual result counts
            run.total_checks = len(all_results)
            self._update_run_statistics(run, all_results)

            # Mark run as completed
            run.mark_completed()

            logger.info(
                f"Validation run {run.id} completed successfully: "
                f"{len(all_results)} results, {len(all_metrics)} metrics"
            )

        except Exception as e:
            logger.error(f"Validation execution failed: {e}")
            run.mark_failed(str(e))
            raise
        finally:
            self._finalize_run(run)

    def _save_validation_data(
        self,
        run: ValidationRun,
        results: List[ValidationResult],
        metrics: List[ValidationMetric],
    ):
        """Save validation results and metrics to database."""
        try:
            from models import db

            # Save results
            for result in results:
                db.session.add(result)

            # Save metrics
            for metric in metrics:
                db.session.add(metric)

            db.session.commit()
            logger.debug(
                f"Saved {len(results)} results and {len(metrics)} metrics for run {run.id}"
            )

        except Exception as e:
            logger.error(f"Failed to save validation data: {e}")
            db.session.rollback()
            raise

    def _update_run_statistics(
        self, run: ValidationRun, results: List[ValidationResult]
    ):
        """Update run statistics based on results."""
        try:
            # Count by severity
            passed = len([r for r in results if r.is_info])
            warnings = len([r for r in results if r.is_warning])
            errors = len([r for r in results if r.is_error])
            critical = len([r for r in results if r.is_critical])

            # Update run statistics
            run.update_summary_stats(
                passed=passed,
                failed=0,  # No "failed" severity in our system
                warnings=warnings,
                errors=errors,
                critical=critical,
            )

            logger.debug(
                f"Updated run {run.id} statistics: passed={passed}, warnings={warnings}, "
                f"errors={errors}, critical={critical}"
            )

        except Exception as e:
            logger.error(f"Failed to update run statistics: {e}")

    def _should_continue_on_error(self) -> bool:
        """Check if validation should continue when errors occur."""
        return self.config.get("continue_on_error", True)

    def _finalize_run(self, run: ValidationRun):
        """Finalize a validation run and clean up."""
        try:
            from models import db

            db.session.commit()

            with self.run_lock:
                if run.id in self.active_runs:
                    del self.active_runs[run.id]

            logger.debug(f"Finalized validation run {run.id}")

        except Exception as e:
            logger.error(f"Failed to finalize run {run.id}: {e}")
            db.session.rollback()

    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get the status of a validation run."""
        try:
            run = ValidationRun.query.get(run_id)
            if run:
                return run.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to get run status for {run_id}: {e}")
            return None

    def get_active_runs(self) -> List[Dict[str, Any]]:
        """Get all active validation runs."""
        try:
            with self.run_lock:
                return [run.to_dict() for run in self.active_runs.values()]
        except Exception as e:
            logger.error(f"Failed to get active runs: {e}")
            return []

    def cancel_run(self, run_id: int) -> bool:
        """Cancel a running validation run."""
        try:
            with self.run_lock:
                if run_id in self.active_runs:
                    run = self.active_runs[run_id]
                    run.mark_cancelled()
                    del self.active_runs[run_id]

                    from models import db

                    db.session.commit()

                    logger.info(f"Cancelled validation run {run_id}")
                    return True
                else:
                    logger.warning(f"Run {run_id} not found in active runs")
                    return False

        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
            return False

    def get_recent_runs(
        self, limit: int = 10, run_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get recent validation runs."""
        try:
            runs = ValidationRun.get_recent_runs(limit=limit, run_type=run_type)
            return [run.to_dict() for run in runs]
        except Exception as e:
            logger.error(f"Failed to get recent runs: {e}")
            return []

    def get_run_results(
        self, run_id: int, severity: str = None, entity_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get results for a specific validation run."""
        try:
            results = ValidationResult.get_results_by_run(
                run_id=run_id, severity=severity, entity_type=entity_type
            )
            return [result.to_dict() for result in results]
        except Exception as e:
            logger.error(f"Failed to get run results for {run_id}: {e}")
            return []

    def get_run_metrics(self, run_id: int) -> List[Dict[str, Any]]:
        """Get metrics for a specific validation run."""
        try:
            metrics = ValidationMetric.get_metrics_by_run(run_id=run_id)
            return [metric.to_dict() for metric in metrics]
        except Exception as e:
            logger.error(f"Failed to get run metrics for {run_id}: {e}")
            return []

    def cleanup_old_runs(self, days: int = 90) -> int:
        """Clean up old validation runs and their associated data."""
        try:
            count = ValidationRun.cleanup_old_runs(days=days)
            logger.info(f"Cleaned up {count} old validation runs")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup old runs: {e}")
            return 0

    def get_validation_summary(self, run_id: int) -> Dict[str, Any]:
        """Get a comprehensive summary of a validation run."""
        try:
            run = ValidationRun.query.get(run_id)
            if not run:
                return {}

            # Get run data
            summary = run.to_dict()

            # Get results summary
            results_summary = ValidationResult.get_error_summary(run_id)
            summary["results_summary"] = results_summary

            # Get metrics summary
            metrics_summary = ValidationMetric.get_metric_summary(run_id)
            summary["metrics_summary"] = metrics_summary

            return summary

        except Exception as e:
            logger.error(f"Failed to get validation summary for {run_id}: {e}")
            return {}

    def shutdown(self):
        """Shutdown the validation engine and clean up resources."""
        try:
            # Cancel all active runs
            with self.run_lock:
                for run_id in list(self.active_runs.keys()):
                    self.cancel_run(run_id)

            # Shutdown executor
            self.executor.shutdown(wait=True)

            logger.info("Validation engine shutdown complete")

        except Exception as e:
            logger.error(f"Error during validation engine shutdown: {e}")


# Global validation engine instance
_validation_engine = None


def get_validation_engine() -> ValidationEngine:
    """Get the global validation engine instance."""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ValidationEngine()
    return _validation_engine


def shutdown_validation_engine():
    """Shutdown the global validation engine."""
    global _validation_engine
    if _validation_engine:
        _validation_engine.shutdown()
        _validation_engine = None
