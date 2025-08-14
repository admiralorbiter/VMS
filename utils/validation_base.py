# utils/validation_base.py
"""
Base validator class for Salesforce data validation.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

from config.validation import get_config_section
from models.validation.metric import ValidationMetric
from models.validation.result import ValidationResult

logger = logging.getLogger(__name__)


class DataValidator(ABC):
    """
    Abstract base class for data validators.

    This class provides common validation functionality including:
    - Result and metric collection
    - Performance monitoring
    - Error handling
    - Configuration management
    """

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, run_id: Optional[int] = None
    ):
        """
        Initialize the validator.

        Args:
            config: Validation configuration
            run_id: ID of the validation run
        """
        if config is None:
            config = get_config_section("validation_rules")

        self.config = config
        self.run_id = run_id
        self.results: List[ValidationResult] = []
        self.metrics: List[ValidationMetric] = []
        self.start_time = None
        self.end_time = None

        # Performance monitoring
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory

        logger.debug(f"Initialized {self.__class__.__name__} validator")

    @abstractmethod
    def validate(self) -> List[ValidationResult]:
        """
        Execute validation and return results.

        Returns:
            List of validation results
        """
        pass

    def add_result(self, result: ValidationResult):
        """Add a validation result."""
        if self.run_id:
            result.run_id = self.run_id
        self.results.append(result)
        logger.debug(
            f"Added validation result: {result.severity} - {result.message[:100]}..."
        )

    def add_metric(self, metric: ValidationMetric):
        """Add a validation metric."""
        if self.run_id:
            metric.run_id = self.run_id
        self.metrics.append(metric)
        logger.debug(
            f"Added validation metric: {metric.metric_name} = {metric.metric_value}"
        )

    def create_result(
        self, entity_type: str, severity: str, message: str, **kwargs
    ) -> ValidationResult:
        """
        Create a validation result with common parameters.

        Args:
            entity_type: Type of entity being validated
            severity: Severity level
            message: Human-readable message
            **kwargs: Additional parameters for ValidationResult

        Returns:
            ValidationResult instance
        """
        return ValidationResult.create_result(
            run_id=self.run_id,
            entity_type=entity_type,
            severity=severity,
            message=message,
            **kwargs,
        )

    def create_metric(
        self, metric_name: str, metric_value: float, **kwargs
    ) -> ValidationMetric:
        """
        Create a validation metric with common parameters.

        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            **kwargs: Additional parameters for ValidationMetric

        Returns:
            ValidationMetric instance
        """
        return ValidationMetric.create_metric(
            metric_name=metric_name,
            metric_value=metric_value,
            run_id=self.run_id,
            **kwargs,
        )

    def start_validation(self):
        """Start validation and record start time."""
        self.start_time = datetime.utcnow()
        logger.info(f"Starting validation: {self.__class__.__name__}")

    def end_validation(self):
        """End validation and record end time."""
        self.end_time = datetime.utcnow()
        self._update_performance_metrics()
        logger.info(
            f"Completed validation: {self.__class__.__name__} in {self.execution_time_seconds}s"
        )

    def _update_performance_metrics(self):
        """Update performance metrics."""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = max(self.peak_memory, current_memory)

        # Add performance metrics
        if self.start_time and self.end_time:
            execution_time = (self.end_time - self.start_time).total_seconds()

            # Add execution time metric
            execution_metric = self.create_metric(
                metric_name="execution_time",
                metric_value=execution_time,
                metric_category="performance",
                metric_unit="seconds",
                entity_type=self.get_entity_type(),
            )
            self.add_metric(execution_metric)

            # Add memory usage metric
            memory_metric = self.create_metric(
                metric_name="memory_usage",
                metric_value=self.peak_memory,
                metric_category="performance",
                metric_unit="mb",
                entity_type=self.get_entity_type(),
            )
            self.add_metric(memory_metric)

    @property
    def execution_time_seconds(self) -> float:
        """Get the execution time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def memory_usage_mb(self) -> float:
        """Get the peak memory usage in MB."""
        return self.peak_memory

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary statistics."""
        total = len(self.results)
        if total == 0:
            return {}

        summary = {
            "total": total,
            "passed": len([r for r in self.results if r.is_info]),
            "warnings": len([r for r in self.results if r.is_warning]),
            "errors": len([r for r in self.results if r.is_error]),
            "critical": len([r for r in self.results if r.is_critical]),
            "issues": len([r for r in self.results if r.is_issue]),
            "execution_time_seconds": self.execution_time_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "metrics_count": len(self.metrics),
        }

        # Add entity type breakdown
        entity_breakdown = {}
        for result in self.results:
            if result.entity_type not in entity_breakdown:
                entity_breakdown[result.entity_type] = {
                    "total": 0,
                    "info": 0,
                    "warnings": 0,
                    "errors": 0,
                    "critical": 0,
                }

            entity_breakdown[result.entity_type]["total"] += 1
            if result.is_info:
                entity_breakdown[result.entity_type]["info"] += 1
            elif result.is_warning:
                entity_breakdown[result.entity_type]["warnings"] += 1
            elif result.is_error:
                entity_breakdown[result.entity_type]["errors"] += 1
            elif result.is_critical:
                entity_breakdown[result.entity_type]["critical"] += 1

        summary["entity_breakdown"] = entity_breakdown

        return summary

    def get_entity_type(self) -> str:
        """Get the entity type this validator handles."""
        # Default implementation - subclasses should override
        return "unknown"

    def validate_with_timing(self) -> List[ValidationResult]:
        """
        Execute validation with timing and performance monitoring.

        Returns:
            List of validation results
        """
        try:
            self.start_validation()
            results = self.validate()
            self.end_validation()
            return results
        except Exception as e:
            logger.error(f"Validation failed in {self.__class__.__name__}: {e}")
            self.end_validation()

            # Add error result
            error_result = self.create_result(
                entity_type=self.get_entity_type(),
                severity="error",
                message=f"Validation failed: {str(e)}",
                validation_type="system",
                rule_name=self.__class__.__name__,
            )
            self.add_result(error_result)

            raise

    def log_summary(self):
        """Log a summary of validation results."""
        summary = self.get_summary()
        if summary:
            logger.info(
                f"Validation summary for {self.__class__.__name__}: "
                f"{summary['total']} total, {summary['issues']} issues, "
                f"{summary['execution_time_seconds']:.2f}s execution time"
            )

            # Log critical issues
            critical_results = [r for r in self.results if r.is_critical]
            if critical_results:
                logger.warning(f"Found {len(critical_results)} critical issues:")
                for result in critical_results[:5]:  # Log first 5
                    logger.warning(f"  - {result.message}")
                if len(critical_results) > 5:
                    logger.warning(f"  ... and {len(critical_results) - 5} more")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback to defaults."""
        return self.config.get(key, default)

    def get_threshold(self, threshold_name: str, default: float = None) -> float:
        """Get a threshold value from configuration."""
        thresholds = get_config_section("thresholds")
        return thresholds.get(threshold_name, default)

    def is_validation_enabled(self, validation_type: str) -> bool:
        """Check if a specific validation type is enabled."""
        validation_rules = get_config_section("validation_rules")
        rule_config = validation_rules.get(validation_type, {})
        return rule_config.get("enabled", True)

    def get_sample_size(self, validation_type: str) -> int:
        """Get the sample size for a validation type."""
        validation_rules = get_config_section("validation_rules")
        rule_config = validation_rules.get(validation_type, {})
        return rule_config.get("sample_size", 1000)

    def should_continue_on_error(self) -> bool:
        """Check if validation should continue when errors occur."""
        return self.get_config_value("continue_on_error", True)

    def get_max_execution_time(self) -> int:
        """Get the maximum execution time in seconds."""
        performance_config = get_config_section("performance")
        return performance_config.get("max_validation_runtime", 3600)

    def check_execution_time_limit(self) -> bool:
        """Check if execution time limit has been exceeded."""
        max_time = self.get_max_execution_time()
        if max_time and self.execution_time_seconds > max_time:
            logger.warning(
                f"Execution time limit exceeded: {self.execution_time_seconds}s > {max_time}s"
            )
            return False
        return True

    def cleanup(self):
        """Clean up resources used by the validator."""
        # Clear results and metrics to free memory
        self.results.clear()
        self.metrics.clear()
        logger.debug(f"Cleaned up {self.__class__.__name__} validator")


class ValidationRule(ABC):
    """
    Abstract interface for validation rules.

    This class defines the interface for implementing specific validation rules.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the validation rule."""
        self.config = config or {}

    @abstractmethod
    def evaluate(self, data: Any) -> ValidationResult:
        """
        Evaluate the rule against the provided data.

        Args:
            data: Data to validate

        Returns:
            ValidationResult instance
        """
        pass

    @abstractmethod
    def get_rule_name(self) -> str:
        """Get the name of this validation rule."""
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def is_enabled(self) -> bool:
        """Check if this rule is enabled."""
        return self.config.get("enabled", True)

    def get_severity(self, default: str = "warning") -> str:
        """Get the severity level for this rule."""
        return self.config.get("severity", default)

    def get_threshold(self, default: float = None) -> float:
        """Get the threshold value for this rule."""
        return self.config.get("threshold", default)


class ValidationContext:
    """
    Context object for validation execution.

    This class provides context information and utilities for validators.
    """

    def __init__(self, run_id: int, user_id: Optional[int] = None):
        """
        Initialize the validation context.

        Args:
            run_id: ID of the validation run
            user_id: ID of the user initiating validation
        """
        self.run_id = run_id
        self.user_id = user_id
        self.start_time = datetime.utcnow()
        self.config = get_config_section("validation_rules")

        logger.debug(f"Created validation context for run {run_id}")

    def get_elapsed_time(self) -> float:
        """Get elapsed time since context creation."""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def is_timeout_reached(self) -> bool:
        """Check if validation timeout has been reached."""
        performance_config = get_config_section("performance")
        max_time = performance_config.get("max_validation_runtime", 3600)
        return self.get_elapsed_time() > max_time

    def get_config_section(self, section: str) -> Dict[str, Any]:
        """Get a configuration section."""
        return get_config_section(section)
