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
        """Calculate quality scores for different validation dimensions."""
        dimension_scores = {}

        # Group results by validation type
        results_by_type = {}
        for result in results:
            if result.validation_type not in results_by_type:
                results_by_type[result.validation_type] = []
            results_by_type[result.validation_type].append(result)

        # Calculate score for each dimension
        for validation_type, type_results in results_by_type.items():
            score = self.score_calculator.calculate_dimension_score(
                validation_type=validation_type,
                results=type_results,
                entity_type=entity_type,
            )
            dimension_scores[validation_type] = score

        return dimension_scores

    def _calculate_composite_score(
        self, dimension_scores: Dict, entity_type: str
    ) -> float:
        """Calculate composite quality score from dimension scores."""
        if not dimension_scores:
            return 0.0

        # Get weights for this entity type
        weights = self.weighting_engine.get_entity_weights(entity_type)

        # Calculate weighted composite score
        total_weighted_score = 0.0
        total_weight = 0.0

        for dimension, score in dimension_scores.items():
            weight = weights.get(dimension, 1.0)  # Default weight of 1.0
            total_weighted_score += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return total_weighted_score / total_weight

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
