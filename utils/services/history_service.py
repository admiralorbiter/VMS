# utils/services/history_service.py
"""
History Service for managing ValidationHistory records.

This service automatically creates and manages ValidationHistory records
from validation runs, enabling trend analysis and quality monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from models import db
from models.validation import (
    ValidationHistory,
    ValidationMetric,
    ValidationResult,
    ValidationRun,
)

logger = logging.getLogger(__name__)


class ValidationHistoryService:
    """
    Service for managing validation history and trend analysis.

    This service provides functionality to:
    - Automatically create history records from validation runs
    - Calculate quality scores and violation counts
    - Generate trend analysis data
    - Manage data retention and cleanup
    """

    def __init__(self):
        """Initialize the validation history service."""
        self.logger = logging.getLogger(__name__)

    def create_history_from_run(
        self, run_id: int, entity_type: str = None
    ) -> List[ValidationHistory]:
        """
        Create ValidationHistory records from a validation run.

        Args:
            run_id: ID of the validation run
            entity_type: Optional entity type filter

        Returns:
            List of created ValidationHistory records
        """
        try:
            # Get the validation run
            run = ValidationRun.query.get(run_id)
            if not run:
                self.logger.error(f"Validation run {run_id} not found")
                return []

            # Get validation results
            results = run.results.all()
            if not results:
                self.logger.warning(f"No results found for run {run_id}")
                return []

            # Get validation metrics
            metrics = run.metrics.all()

            # Group results by entity type and validation type
            history_records = []

            if entity_type:
                # Create history for specific entity type
                history_record = self._create_entity_history(
                    run, results, metrics, entity_type
                )
                if history_record:
                    history_records.append(history_record)
            else:
                # Create history for all entity types found in results
                entity_types = set(
                    result.entity_type for result in results if result.entity_type
                )
                for entity_type in entity_types:
                    history_record = self._create_entity_history(
                        run, results, metrics, entity_type
                    )
                    if history_record:
                        history_records.append(history_record)

            # Save all history records
            if history_records:
                db.session.add_all(history_records)
                db.session.commit()
                self.logger.info(
                    f"Created {len(history_records)} history records for run {run_id}"
                )

            return history_records

        except Exception as e:
            self.logger.error(f"Error creating history from run {run_id}: {e}")
            db.session.rollback()
            return []

    def _create_entity_history(
        self,
        run: ValidationRun,
        results: List[ValidationResult],
        metrics: List[ValidationMetric],
        entity_type: str,
    ) -> Optional[ValidationHistory]:
        """
        Create a history record for a specific entity type.

        Args:
            run: Validation run object
            results: List of validation results
            metrics: List of validation metrics
            entity_type: Entity type to create history for

        Returns:
            ValidationHistory record or None if creation fails
        """
        try:
            # Filter results for this entity type
            entity_results = [r for r in results if r.entity_type == entity_type]
            if not entity_results:
                return None

            # Calculate violation counts by severity
            violation_counts = self._calculate_violation_counts(entity_results)

            # Calculate quality score
            quality_score = self._calculate_quality_score(entity_results)

            # Get metrics summary for this entity type
            metrics_summary = self._get_metrics_summary(metrics, entity_type)

            # Calculate derived metrics
            field_completeness = self._extract_metric_value(
                metrics, "field_completeness", entity_type
            )
            data_type_accuracy = self._extract_metric_value(
                metrics, "data_type_accuracy", entity_type
            )
            relationship_integrity = self._extract_metric_value(
                metrics, "relationship_integrity", entity_type
            )
            business_rule_compliance = self._extract_metric_value(
                metrics, "business_rule_compliance", entity_type
            )

            # Determine validation type from run
            validation_type = self._determine_validation_type(
                run.run_type, entity_results
            )

            # Create history record
            history_record = ValidationHistory.create_from_validation_run(
                run_id=run.id,
                entity_type=entity_type,
                validation_type=validation_type,
                quality_score=quality_score,
                violation_counts=violation_counts,
                total_checks=len(entity_results),
                passed_checks=len([r for r in entity_results if r.severity == "info"]),
                failed_checks=len([r for r in entity_results if r.severity != "info"]),
                execution_time=run.execution_time_seconds,
                memory_usage=run.memory_usage_mb,
                cpu_usage=run.cpu_usage_percent,
                metrics_summary=metrics_summary,
                quality_threshold=70.0,  # Default threshold
                validation_metadata={
                    "run_type": run.run_type,
                    "run_name": run.name,
                    "total_run_results": len(results),
                    "total_run_metrics": len(metrics),
                },
                notes=f"History record created from {run.run_type} validation run",
            )

            # Calculate and set trend data
            self._calculate_trend_data(history_record, entity_type, validation_type)

            return history_record

        except Exception as e:
            self.logger.error(f"Error creating entity history for {entity_type}: {e}")
            return None

    def _calculate_violation_counts(
        self, results: List[ValidationResult]
    ) -> Dict[str, int]:
        """Calculate violation counts by severity level."""
        counts = {"critical": 0, "error": 0, "warning": 0, "info": 0}

        for result in results:
            severity = result.severity.lower()
            if severity in counts:
                counts[severity] += 1

        return counts

    def _calculate_quality_score(self, results: List[ValidationResult]) -> float:
        """Calculate quality score based on validation results."""
        if not results:
            return 100.0

        # Base score
        base_score = 100.0

        # Penalty weights
        penalties = {
            "critical": 10.0,
            "error": 5.0,
            "warning": 2.0,
            "info": 0.0,  # Info results don't reduce quality
        }

        # Calculate total penalty
        total_penalty = 0.0
        for result in results:
            severity = result.severity.lower()
            if severity in penalties:
                total_penalty += penalties[severity]

        # Calculate final score
        final_score = max(0.0, base_score - total_penalty)
        return round(final_score, 2)

    def _get_metrics_summary(
        self, metrics: List[ValidationMetric], entity_type: str
    ) -> Dict:
        """Get metrics summary for a specific entity type."""
        summary = {}

        for metric in metrics:
            if metric.entity_type == entity_type or metric.entity_type == "all":
                # Convert Decimal to float for JSON serialization
                metric_value = (
                    float(metric.metric_value) if metric.metric_value else None
                )
                summary[metric.metric_name] = {
                    "value": metric_value,
                    "category": metric.metric_category,
                    "unit": metric.metric_unit,
                }

        return summary

    def _extract_metric_value(
        self, metrics: List[ValidationMetric], metric_name: str, entity_type: str
    ) -> Optional[float]:
        """Extract a specific metric value for an entity type."""
        for metric in metrics:
            if metric.metric_name == metric_name and (
                metric.entity_type == entity_type or metric.entity_type == "all"
            ):
                return float(metric.metric_value) if metric.metric_value else None
        return None

    def _determine_validation_type(
        self, run_type: str, results: List[ValidationResult]
    ) -> str:
        """Determine the validation type from run type and results."""
        # Map run types to validation types
        type_mapping = {
            "business_rule_validation": "business_rules",
            "field_completeness": "field_completeness",
            "data_type_validation": "data_types",
            "relationship_validation": "relationships",
            "count_validation": "count",
        }

        return type_mapping.get(run_type, run_type)

    def _calculate_trend_data(
        self, history_record: ValidationHistory, entity_type: str, validation_type: str
    ):
        """Calculate trend data for the history record."""
        try:
            # Get historical data for trend analysis
            historical_records = ValidationHistory.get_entity_history(
                entity_type=entity_type,
                validation_type=validation_type,
                days=30,
                limit=10,
            )

            if len(historical_records) >= 2:
                # Calculate trend direction and magnitude
                recent_scores = [
                    record.quality_score for record in historical_records[-5:]
                ]
                if len(recent_scores) >= 2:
                    # Simple trend calculation
                    first_score = recent_scores[0]
                    last_score = recent_scores[-1]
                    change = last_score - first_score

                    if change > 2.0:
                        history_record.trend_direction = "improving"
                        history_record.trend_magnitude = min(100.0, abs(change))
                    elif change < -2.0:
                        history_record.trend_direction = "declining"
                        history_record.trend_magnitude = min(100.0, abs(change))
                    else:
                        history_record.trend_direction = "stable"
                        history_record.trend_magnitude = 0.0

                    # Calculate confidence based on data points
                    history_record.trend_confidence = min(
                        1.0, len(recent_scores) / 10.0
                    )

                    # Store trend data
                    history_record.trend_data = {
                        "recent_scores": recent_scores,
                        "score_change": change,
                        "data_points": len(recent_scores),
                    }

        except Exception as e:
            self.logger.warning(f"Error calculating trend data: {e}")

    def populate_history_from_recent_runs(self, days: int = 7) -> int:
        """
        Populate history from recent validation runs.

        Args:
            days: Number of days to look back

        Returns:
            Number of history records created
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_runs = ValidationRun.query.filter(
                ValidationRun.completed_at >= cutoff_date,
                ValidationRun.status == "completed",
            ).all()

            total_created = 0
            for run in recent_runs:
                # Check if history already exists for this run
                existing_history = ValidationHistory.query.filter_by(
                    run_id=run.id
                ).first()
                if not existing_history:
                    history_records = self.create_history_from_run(run.id)
                    total_created += len(history_records)

            self.logger.info(
                f"Created {total_created} history records from {len(recent_runs)} recent runs"
            )
            return total_created

        except Exception as e:
            self.logger.error(f"Error populating history from recent runs: {e}")
            return 0

    def get_quality_trends(
        self, entity_type: str, validation_type: str = None, days: int = 30
    ) -> Dict:
        """Get quality trends for an entity type."""
        return ValidationHistory.get_quality_trends(
            entity_type=entity_type, validation_type=validation_type, days=days
        )

    def get_summary_statistics(
        self, entity_type: str = None, validation_type: str = None, days: int = 30
    ) -> Dict:
        """Get summary statistics for validation history."""
        return ValidationHistory.get_summary_statistics(
            entity_type=entity_type, validation_type=validation_type, days=days
        )

    def cleanup_old_records(self, retention_days: int = 365) -> int:
        """Clean up old validation history records."""
        return ValidationHistory.cleanup_old_records(retention_days)
