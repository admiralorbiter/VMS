# utils/services/quality_scoring_service.py
"""
Quality Scoring Service for Phase 3.4.

This service provides comprehensive quality scoring capabilities including:
- Weighted scoring algorithms for different validation types
- Configurable quality thresholds per entity and validation type
- Multi-dimensional quality assessment
- Historical score comparison and improvement tracking
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
from utils.services.score_calculator import ScoreCalculator
from utils.services.score_weighting_engine import ScoreWeightingEngine
from utils.services.threshold_manager import ThresholdManager


class QualityScoringService:
    """
    Main service for calculating and managing quality scores.

    This service orchestrates the quality scoring process, integrating
    with the weighting engine, threshold manager, and score calculator
    to provide comprehensive quality assessment.
    """

    def __init__(self):
        """Initialize the quality scoring service."""
        self.logger = logging.getLogger(__name__)

        # Initialize sub-services
        self.weighting_engine = ScoreWeightingEngine()
        self.threshold_manager = ThresholdManager()
        self.score_calculator = ScoreCalculator()

        # Default configuration
        self.default_entity_types = [
            "volunteer",
            "organization",
            "event",
            "student",
            "teacher",
        ]
        self.default_validation_types = [
            "field_completeness",
            "data_types",
            "business_rules",
            "relationships",
        ]

    def calculate_entity_quality_score(
        self,
        entity_type: str,
        run_id: int = None,
        days: int = 7,
        include_details: bool = True,
    ) -> Dict:
        """
        Calculate comprehensive quality score for a specific entity type.

        Args:
            entity_type: Type of entity to score (e.g., 'volunteer', 'organization')
            run_id: Optional specific validation run ID
            days: Number of days to look back for data
            include_details: Whether to include detailed scoring breakdown

        Returns:
            Dictionary containing quality score and details
        """
        try:
            self.logger.info(f"Calculating quality score for {entity_type}")

            # Get validation results for the entity
            if run_id:
                results = self._get_validation_results_by_run(run_id, entity_type)
            else:
                results = self._get_validation_results_by_entity(entity_type, days)

            if not results:
                return {
                    "entity_type": entity_type,
                    "run_id": run_id,
                    "quality_score": 0.0,
                    "message": "No validation results found",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Calculate individual dimension scores
            dimension_scores = self._calculate_dimension_scores(results, entity_type)

            # Calculate composite quality score
            composite_score = self._calculate_composite_score(
                dimension_scores, entity_type
            )

            # Get quality threshold and status
            threshold = self.threshold_manager.get_entity_threshold(entity_type)
            quality_status = self._determine_quality_status(composite_score, threshold)

            # Prepare result
            result = {
                "entity_type": entity_type,
                "run_id": run_id,
                "quality_score": round(composite_score, 2),
                "quality_status": quality_status,
                "threshold": threshold,
                "timestamp": datetime.utcnow().isoformat(),
                "dimension_scores": dimension_scores if include_details else None,
                "total_checks": len(results),
                "passed_checks": sum(
                    1 for r in results if r.severity in ["info", "warning"]
                ),
                "failed_checks": sum(
                    1 for r in results if r.severity in ["error", "critical"]
                ),
                "context_aware": True,  # Indicate this uses context-aware validation
                "expected_discrepancies": self._count_expected_discrepancies(results),
                "quality_issues": self._count_quality_issues(results),
            }

            # Add trend information if available
            if not run_id:  # Only for historical analysis
                trend_info = self._get_quality_trend(entity_type, days)
                result["trend"] = trend_info

            self.logger.info(
                f"Quality score calculated: {composite_score:.2f} for {entity_type}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error calculating quality score for {entity_type}: {e}")
            return {
                "entity_type": entity_type,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def calculate_comprehensive_quality_report(
        self,
        entity_types: List[str] = None,
        days: int = 30,
        include_trends: bool = True,
    ) -> Dict:
        """
        Calculate comprehensive quality report for multiple entities.

        Args:
            entity_types: List of entity types to analyze (default: all)
            days: Number of days to look back
            include_trends: Whether to include trend analysis

        Returns:
            Dictionary containing comprehensive quality report
        """
        try:
            if entity_types is None:
                entity_types = self.default_entity_types

            self.logger.info(
                f"Generating comprehensive quality report for {len(entity_types)} entities"
            )

            report = {
                "report_date": datetime.utcnow().isoformat(),
                "analysis_period_days": days,
                "entity_scores": {},
                "overall_summary": {},
                "trends": {} if include_trends else None,
            }

            # Calculate scores for each entity type
            total_score = 0.0
            entity_count = 0

            for entity_type in entity_types:
                entity_score = self.calculate_entity_quality_score(
                    entity_type=entity_type, days=days, include_details=True
                )

                report["entity_scores"][entity_type] = entity_score

                if "quality_score" in entity_score and isinstance(
                    entity_score["quality_score"], (int, float)
                ):
                    total_score += entity_score["quality_score"]
                    entity_count += 1

            # Calculate overall summary
            if entity_count > 0:
                overall_score = total_score / entity_count
                report["overall_summary"] = {
                    "average_quality_score": round(overall_score, 2),
                    "total_entities": entity_count,
                    "quality_distribution": self._calculate_quality_distribution(
                        report["entity_scores"]
                    ),
                    "top_performers": self._get_top_performers(report["entity_scores"]),
                    "improvement_opportunities": self._get_improvement_opportunities(
                        report["entity_scores"]
                    ),
                }

            # Add trend analysis if requested
            if include_trends:
                report["trends"] = self._calculate_overall_trends(entity_types, days)

            self.logger.info(f"Comprehensive quality report generated successfully")
            return report

        except Exception as e:
            self.logger.error(f"Error generating comprehensive quality report: {e}")
            return {"error": str(e), "report_date": datetime.utcnow().isoformat()}

    def _get_validation_results_by_run(
        self, run_id: int, entity_type: str
    ) -> List[ValidationResult]:
        """Get validation results for a specific run and entity type."""
        return ValidationResult.query.filter_by(
            run_id=run_id, entity_type=entity_type
        ).all()

    def _get_validation_results_by_entity(
        self, entity_type: str, days: int
    ) -> List[ValidationResult]:
        """Get validation results for an entity type over a time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get recent validation runs
        recent_runs = ValidationRun.query.filter(
            ValidationRun.completed_at >= cutoff_date,
            ValidationRun.status == "completed",
        ).all()

        run_ids = [run.id for run in recent_runs]

        if not run_ids:
            return []

        return ValidationResult.query.filter(
            ValidationResult.run_id.in_(run_ids),
            ValidationResult.entity_type == entity_type,
        ).all()

    def _calculate_dimension_scores(
        self, results: List[ValidationResult], entity_type: str
    ) -> Dict:
        """
        Calculate individual dimension scores from validation results.

        This method now handles context-aware validation results that distinguish
        between expected discrepancies and actual quality issues.
        """
        try:
            # Initialize dimension scores
            dimension_scores = {
                "field_completeness": 0.0,
                "data_types": 0.0,
                "business_rules": 0.0,
                "relationships": 0.0,
                "count_validation": 0.0,
            }

            # Group results by validation type
            results_by_type = {}
            for result in results:
                validation_type = result.validation_type
                if validation_type not in results_by_type:
                    results_by_type[validation_type] = []
                results_by_type[validation_type].append(result)

            # Initialize relationship results list
            relationship_results = []

            # Calculate scores for each dimension
            for validation_type, type_results in results_by_type.items():
                if validation_type == "count":
                    dimension_scores["count_validation"] = (
                        self._calculate_count_validation_score(type_results)
                    )
                elif validation_type == "field_completeness":
                    dimension_scores["field_completeness"] = (
                        self._calculate_field_completeness_score(type_results)
                    )
                elif (
                    validation_type == "data_type_validation"
                ):  # Fix: match actual validation type
                    dimension_scores["data_types"] = self._calculate_data_type_score(
                        type_results
                    )
                elif validation_type == "business_rules":
                    dimension_scores["business_rules"] = (
                        self._calculate_business_rule_score(type_results)
                    )
                elif validation_type in [
                    "relationships",
                    "orphaned_record",
                    "optional_relationship_population",
                    "relationship_completeness",
                    "required_relationship",
                ]:
                    # Group all relationship-related validation types
                    relationship_results.extend(type_results)

            # Calculate relationship score from all grouped results
            if relationship_results:
                dimension_scores["relationships"] = self._calculate_relationship_score(
                    relationship_results
                )

            return dimension_scores

        except Exception as e:
            self.logger.error(f"Error calculating dimension scores: {e}")
            return {
                "field_completeness": 0.0,
                "data_types": 0.0,
                "business_rules": 0.0,
                "relationships": 0.0,
                "count_validation": 0.0,
            }

    def _calculate_count_validation_score(
        self, count_results: List[ValidationResult]
    ) -> float:
        """
        Calculate count validation score with context awareness.

        This method now properly handles expected discrepancies as quality successes,
        and uses graduated quality scores for unexpected discrepancies.
        """
        if not count_results:
            return 0.0

        total_results = len(count_results)
        total_score = 0.0

        for result in count_results:
            metadata = result.metadata_dict or {}
            is_expected = metadata.get("is_expected_discrepancy", False)

            if is_expected:
                # Expected discrepancy = quality success (100%)
                total_score += 100.0
            else:
                # Use the quality score from metadata if available
                quality_score = metadata.get(
                    "quality_score", 50.0
                )  # Default to 50% for unknown issues
                total_score += quality_score

        # Return average score across all results
        return total_score / total_results

    def _count_expected_discrepancies(self, results: List[ValidationResult]) -> int:
        """Count the number of expected discrepancies in validation results."""
        count = 0
        for result in results:
            metadata = result.metadata_dict or {}
            if metadata.get("is_expected_discrepancy", False):
                count += 1
        return count

    def _count_quality_issues(self, results: List[ValidationResult]) -> int:
        """Count the number of actual quality issues in validation results."""
        count = 0
        for result in results:
            metadata = result.metadata_dict or {}
            if not metadata.get("is_expected_discrepancy", False):
                count += 1
        return count

    def _calculate_field_completeness_score(
        self, field_results: List[ValidationResult]
    ) -> float:
        """Calculate field completeness score with graduated scoring."""
        if not field_results:
            return 0.0

        total_results = len(field_results)
        total_score = 0.0

        for result in field_results:
            if result.severity == "info":
                total_score += 100.0  # Perfect
            elif result.severity == "warning":
                total_score += 85.0  # Good with minor issues
            elif result.severity == "error":
                total_score += 60.0  # Moderate issues
            elif result.severity == "critical":
                total_score += 30.0  # Significant issues
            else:
                total_score += 0.0  # Unknown severity

        # Return average score across all results
        return total_score / total_results if total_results > 0 else 0.0

    def _calculate_data_type_score(
        self, data_type_results: List[ValidationResult]
    ) -> float:
        """Calculate data type validation score with graduated scoring."""
        if not data_type_results:
            return 0.0

        total_results = len(data_type_results)
        total_score = 0.0

        for result in data_type_results:
            if result.severity == "info":
                total_score += 100.0  # Perfect
            elif result.severity == "warning":
                total_score += 85.0  # Good with minor issues
            elif result.severity == "error":
                total_score += 60.0  # Moderate issues
            elif result.severity == "critical":
                total_score += 30.0  # Significant issues
            else:
                total_score += 0.0  # Unknown severity

        # Return average score across all results
        return total_score / total_results if total_results > 0 else 0.0

    def _calculate_business_rule_score(
        self, business_rule_results: List[ValidationResult]
    ) -> float:
        """Calculate business rule validation score with graduated scoring."""
        if not business_rule_results:
            return 0.0

        total_results = len(business_rule_results)
        total_score = 0.0

        for result in business_rule_results:
            if result.severity == "info":
                total_score += 100.0  # Perfect
            elif result.severity == "warning":
                total_score += 85.0  # Good with minor issues
            elif result.severity == "error":
                total_score += 60.0  # Moderate issues
            elif result.severity == "critical":
                total_score += 30.0  # Significant issues
            else:
                total_score += 0.0  # Unknown severity

        # Return average score across all results
        return total_score / total_results if total_results > 0 else 0.0

    def _calculate_relationship_score(
        self, relationship_results: List[ValidationResult]
    ) -> float:
        """Calculate relationship validation score with graduated scoring."""
        if not relationship_results:
            return 0.0

        total_results = len(relationship_results)
        total_score = 0.0

        for result in relationship_results:
            if result.severity == "info":
                total_score += 100.0  # Perfect
            elif result.severity == "warning":
                total_score += 85.0  # Good with minor issues
            elif result.severity == "error":
                total_score += 60.0  # Moderate issues
            elif result.severity == "critical":
                total_score += 30.0  # Significant issues
            else:
                total_score += 0.0  # Unknown severity

        # Return average score across all results
        return total_score / total_results if total_results > 0 else 0.0

    def _calculate_composite_score(
        self, dimension_scores: Dict, entity_type: str
    ) -> float:
        """Calculate composite quality score from dimension scores."""
        if not dimension_scores:
            return 0.0

        # Get weights for this entity type
        weights = self.weighting_engine.get_entity_weights(entity_type)

        # Smart composite score calculation that handles missing dimensions
        available_dimensions = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for dimension, score in dimension_scores.items():
            # Only include dimensions that have meaningful scores
            if score > 0.0:
                available_dimensions[dimension] = score
                weight = weights.get(dimension, 1.0)
                total_weighted_score += score * weight
                total_weight += weight

        # If no dimensions have scores, return 0
        if total_weight == 0:
            return 0.0

        # Special handling for events with expected discrepancies
        if entity_type == "event" and "count_validation" in available_dimensions:
            count_score = available_dimensions["count_validation"]
            if count_score >= 95.0:  # If count validation shows expected discrepancies
                # Events should get full credit for working as designed
                return 100.0

        # Calculate weighted average of available dimensions
        composite_score = total_weighted_score / total_weight

        # If we only have count validation data and it's perfect, give full credit
        if (
            len(available_dimensions) == 1
            and "count_validation" in available_dimensions
        ):
            count_score = available_dimensions["count_validation"]
            if count_score >= 95.0:
                return 100.0

        return composite_score

    def _determine_quality_status(self, score: float, threshold: float) -> str:
        """Determine quality status based on score and threshold."""
        if score >= threshold:
            return "excellent"
        elif score >= threshold * 0.8:
            return "good"
        elif score >= threshold * 0.6:
            return "fair"
        else:
            return "poor"

    def _get_quality_trend(self, entity_type: str, days: int) -> Dict:
        """Get quality trend information for an entity type."""
        try:
            # Get historical quality scores
            history_records = ValidationHistory.get_entity_history(
                entity_type=entity_type, days=days
            )

            if len(history_records) < 2:
                return {
                    "trend": "insufficient_data",
                    "data_points": len(history_records),
                }

            # Calculate trend
            scores = [record.quality_score for record in history_records]
            if len(scores) >= 2:
                trend_slope = (scores[-1] - scores[0]) / len(scores)

                if abs(trend_slope) < 0.1:
                    trend_direction = "stable"
                elif trend_slope > 0:
                    trend_direction = "improving"
                else:
                    trend_direction = "declining"

                return {
                    "trend": trend_direction,
                    "trend_slope": round(trend_slope, 3),
                    "data_points": len(scores),
                    "score_range": {"min": min(scores), "max": max(scores)},
                    "average_score": round(sum(scores) / len(scores), 2),
                }

            return {"trend": "insufficient_data", "data_points": len(scores)}

        except Exception as e:
            self.logger.error(f"Error calculating quality trend: {e}")
            return {"trend": "error", "error": str(e)}

    def _calculate_quality_distribution(self, entity_scores: Dict) -> Dict:
        """Calculate distribution of quality scores across entities."""
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}

        for entity_type, score_data in entity_scores.items():
            if "quality_status" in score_data:
                status = score_data["quality_status"]
                if status in distribution:
                    distribution[status] += 1

        return distribution

    def _get_top_performers(self, entity_scores: Dict) -> List[Dict]:
        """Get top performing entities by quality score."""
        performers = []

        for entity_type, score_data in entity_scores.items():
            if "quality_score" in score_data and isinstance(
                score_data["quality_score"], (int, float)
            ):
                performers.append(
                    {
                        "entity_type": entity_type,
                        "quality_score": score_data["quality_score"],
                        "quality_status": score_data.get("quality_status", "unknown"),
                    }
                )

        # Sort by quality score (descending)
        performers.sort(key=lambda x: x["quality_score"], reverse=True)

        return performers[:3]  # Top 3

    def _get_improvement_opportunities(self, entity_scores: Dict) -> List[Dict]:
        """Get entities with improvement opportunities."""
        opportunities = []

        for entity_type, score_data in entity_scores.items():
            if "quality_score" in score_data and isinstance(
                score_data["quality_score"], (int, float)
            ):
                score = score_data["quality_score"]
                if score < 80.0:  # Below 80% threshold
                    opportunities.append(
                        {
                            "entity_type": entity_type,
                            "current_score": score,
                            "improvement_needed": round(80.0 - score, 2),
                            "priority": "high" if score < 60.0 else "medium",
                        }
                    )

        # Sort by improvement needed (descending)
        opportunities.sort(key=lambda x: x["improvement_needed"], reverse=True)

        return opportunities

    def _calculate_overall_trends(self, entity_types: List[str], days: int) -> Dict:
        """Calculate overall quality trends across all entities."""
        try:
            overall_trends = {}

            for entity_type in entity_types:
                trend_info = self._get_quality_trend(entity_type, days)
                overall_trends[entity_type] = trend_info

            return overall_trends

        except Exception as e:
            self.logger.error(f"Error calculating overall trends: {e}")
            return {"error": str(e)}
