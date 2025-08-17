# utils/services/score_calculator.py
"""
Score Calculator for Phase 3.4.

This service implements the actual scoring algorithms for different
validation types, calculating quality scores based on validation results.
"""

import logging
from typing import Dict, List, Optional

from config.quality_scoring import (
    PENALTY_MULTIPLIERS,
    SCORING_ALGORITHMS,
    SEVERITY_WEIGHTS,
)
from models.validation import ValidationResult


class ScoreCalculator:
    """
    Calculator for quality scores based on validation results.

    This service implements various scoring algorithms for different
    validation types, providing accurate and configurable quality assessment.
    """

    def __init__(self):
        """Initialize the score calculator."""
        self.logger = logging.getLogger(__name__)

    def calculate_dimension_score(
        self,
        validation_type: str,
        results: List[ValidationResult],
        entity_type: str = None,
    ) -> float:
        """
        Calculate quality score for a specific validation dimension.

        Args:
            validation_type: Type of validation (e.g., 'field_completeness')
            results: List of validation results
            entity_type: Optional entity type for context

        Returns:
            Quality score (0-100)
        """
        try:
            if not results:
                return 0.0

            # Get the appropriate scoring algorithm
            algorithm = self._get_scoring_algorithm(validation_type)

            # Calculate score based on algorithm type
            if algorithm == "percentage_based":
                return self._calculate_percentage_based_score(validation_type, results)
            elif algorithm == "penalty_based":
                return self._calculate_penalty_based_score(validation_type, results)
            elif algorithm == "severity_weighted":
                return self._calculate_severity_weighted_score(validation_type, results)
            else:
                return self._calculate_default_score(validation_type, results)

        except Exception as e:
            self.logger.error(f"Error calculating {validation_type} score: {e}")
            return 0.0

    def _get_scoring_algorithm(self, validation_type: str) -> str:
        """Get the scoring algorithm for a validation type."""
        try:
            return SCORING_ALGORITHMS.get(validation_type, {}).get("type", "default")
        except Exception:
            return "default"

    def _calculate_percentage_based_score(
        self, validation_type: str, results: List[ValidationResult]
    ) -> float:
        """
        Calculate percentage-based score for validation types like field completeness.

        Formula: (Passed Checks / Total Checks) * 100
        """
        try:
            if not results:
                return 0.0

            total_checks = len(results)
            passed_checks = 0

            for result in results:
                # Consider info and warning as passed, error and critical as failed
                if result.severity in ["info", "warning"]:
                    passed_checks += 1

            if total_checks == 0:
                return 0.0

            score = (passed_checks / total_checks) * 100

            # Apply any specific penalties for this validation type
            score = self._apply_validation_type_penalties(
                validation_type, results, score
            )

            return max(0.0, min(100.0, score))

        except Exception as e:
            self.logger.error(f"Error calculating percentage-based score: {e}")
            return 0.0

    def _calculate_penalty_based_score(
        self, validation_type: str, results: List[ValidationResult]
    ) -> float:
        """
        Calculate penalty-based score for validation types like data types.

        Formula: Base Score - (Penalties * Multipliers)
        """
        try:
            if not results:
                return 0.0

            # Get algorithm configuration
            config = SCORING_ALGORITHMS.get(validation_type, {})
            base_score = config.get("base_score", 100.0)
            max_penalty = config.get("max_penalty", 50.0)

            total_penalty = 0.0

            for result in results:
                if result.severity in ["error", "critical"]:
                    # Calculate penalty based on severity and type
                    penalty = self._calculate_penalty_for_result(
                        result, validation_type
                    )
                    total_penalty += penalty

            # Apply penalty to base score
            final_score = base_score - total_penalty

            # Ensure score doesn't go below minimum
            final_score = max(0.0, final_score)

            # Cap penalty at maximum allowed
            if final_score < (base_score - max_penalty):
                final_score = base_score - max_penalty

            return final_score

        except Exception as e:
            self.logger.error(f"Error calculating penalty-based score: {e}")
            return 0.0

    def _calculate_severity_weighted_score(
        self, validation_type: str, results: List[ValidationResult]
    ) -> float:
        """
        Calculate severity-weighted score for validation types like business rules.

        Formula: Base Score - (Weighted Penalties)
        """
        try:
            if not results:
                return 0.0

            # Get algorithm configuration
            config = SCORING_ALGORITHMS.get(validation_type, {})
            base_score = config.get("base_score", 100.0)
            base_penalty = config.get("rule_violation_penalty", 7.0)
            severity_multipliers = config.get("severity_multipliers", SEVERITY_WEIGHTS)

            total_penalty = 0.0

            for result in results:
                if result.severity in ["warning", "error", "critical"]:
                    # Get severity multiplier
                    multiplier = severity_multipliers.get(result.severity, 1.0)

                    # Calculate penalty for this result
                    penalty = base_penalty * multiplier
                    total_penalty += penalty

            # Apply penalty to base score
            final_score = base_score - total_penalty

            return max(0.0, min(100.0, final_score))

        except Exception as e:
            self.logger.error(f"Error calculating severity-weighted score: {e}")
            return 0.0

    def _calculate_default_score(
        self, validation_type: str, results: List[ValidationResult]
    ) -> float:
        """
        Calculate default score when specific algorithm is not available.

        Uses a simple percentage-based approach.
        """
        try:
            if not results:
                return 0.0

            total_checks = len(results)
            passed_checks = 0

            for result in results:
                if result.severity in ["info", "warning"]:
                    passed_checks += 1

            if total_checks == 0:
                return 0.0

            score = (passed_checks / total_checks) * 100
            return max(0.0, min(100.0, score))

        except Exception as e:
            self.logger.error(f"Error calculating default score: {e}")
            return 0.0

    def _calculate_penalty_for_result(
        self, result: ValidationResult, validation_type: str
    ) -> float:
        """
        Calculate penalty for a specific validation result.

        Args:
            result: Validation result
            validation_type: Type of validation

        Returns:
            Penalty value
        """
        try:
            base_penalty = 1.0

            # Apply severity-based multiplier
            severity_weight = SEVERITY_WEIGHTS.get(result.severity, 1.0)
            base_penalty *= severity_weight

            # Apply validation type specific penalties
            if validation_type == "data_types":
                if result.severity == "critical":
                    base_penalty *= PENALTY_MULTIPLIERS.get("data_type_mismatch", 5.0)
                elif result.severity == "error":
                    base_penalty *= (
                        PENALTY_MULTIPLIERS.get("data_type_mismatch", 5.0) * 0.8
                    )
                elif result.severity == "warning":
                    base_penalty *= (
                        PENALTY_MULTIPLIERS.get("data_type_mismatch", 5.0) * 0.5
                    )

            elif validation_type == "field_completeness":
                if (
                    "missing" in result.message.lower()
                    or "required" in result.message.lower()
                ):
                    base_penalty *= PENALTY_MULTIPLIERS.get(
                        "missing_required_field", 8.0
                    )
                else:
                    base_penalty *= PENALTY_MULTIPLIERS.get(
                        "field_validation_error", 4.0
                    )

            elif validation_type == "business_rules":
                base_penalty *= PENALTY_MULTIPLIERS.get("business_rule_violation", 7.0)

            elif validation_type == "relationships":
                if (
                    "orphaned" in result.message.lower()
                    or "invalid" in result.message.lower()
                ):
                    base_penalty *= PENALTY_MULTIPLIERS.get("invalid_relationship", 6.0)
                else:
                    base_penalty *= (
                        PENALTY_MULTIPLIERS.get("invalid_relationship", 6.0) * 0.5
                    )

            return base_penalty

        except Exception as e:
            self.logger.error(f"Error calculating penalty for result: {e}")
            return 1.0

    def _apply_validation_type_penalties(
        self, validation_type: str, results: List[ValidationResult], base_score: float
    ) -> float:
        """
        Apply additional penalties specific to validation types.

        Args:
            validation_type: Type of validation
            results: List of validation results
            base_score: Base calculated score

        Returns:
            Adjusted score
        """
        try:
            if validation_type == "field_completeness":
                # Apply penalties for missing required fields
                missing_required = sum(
                    1
                    for r in results
                    if r.severity in ["error", "critical"]
                    and (
                        "required" in r.message.lower()
                        or "missing" in r.message.lower()
                    )
                )

                if missing_required > 0:
                    penalty = missing_required * PENALTY_MULTIPLIERS.get(
                        "missing_required_field", 8.0
                    )
                    base_score -= penalty

            elif validation_type == "relationships":
                # Apply penalties for orphaned records
                orphaned_records = sum(
                    1
                    for r in results
                    if r.severity in ["error", "critical"]
                    and "orphaned" in r.message.lower()
                )

                if orphaned_records > 0:
                    penalty = orphaned_records * PENALTY_MULTIPLIERS.get(
                        "invalid_relationship", 6.0
                    )
                    base_score -= penalty

            return max(0.0, base_score)

        except Exception as e:
            self.logger.error(f"Error applying validation type penalties: {e}")
            return base_score

    def calculate_composite_score(
        self, dimension_scores: Dict[str, float], weights: Dict[str, float]
    ) -> float:
        """
        Calculate composite quality score from dimension scores.

        Args:
            dimension_scores: Dictionary of validation type scores
            weights: Dictionary of weights for each validation type

        Returns:
            Composite quality score (0-100)
        """
        try:
            if not dimension_scores or not weights:
                return 0.0

            total_weighted_score = 0.0
            total_weight = 0.0

            for validation_type, score in dimension_scores.items():
                weight = weights.get(validation_type, 1.0)
                total_weighted_score += score * weight
                total_weight += weight

            if total_weight == 0:
                return 0.0

            composite_score = total_weighted_score / total_weight

            return max(0.0, min(100.0, composite_score))

        except Exception as e:
            self.logger.error(f"Error calculating composite score: {e}")
            return 0.0

    def get_score_breakdown(
        self, validation_type: str, results: List[ValidationResult]
    ) -> Dict:
        """
        Get detailed breakdown of score calculation.

        Args:
            validation_type: Type of validation
            results: List of validation results

        Returns:
            Dictionary containing score breakdown
        """
        try:
            breakdown = {
                "validation_type": validation_type,
                "total_checks": len(results),
                "severity_breakdown": {},
                "score_calculation": {},
                "penalties_applied": [],
            }

            # Severity breakdown
            for result in results:
                severity = result.severity
                if severity not in breakdown["severity_breakdown"]:
                    breakdown["severity_breakdown"][severity] = 0
                breakdown["severity_breakdown"][severity] += 1

            # Calculate score
            score = self.calculate_dimension_score(validation_type, results)
            breakdown["final_score"] = score

            # Score calculation details
            algorithm = self._get_scoring_algorithm(validation_type)
            breakdown["algorithm_used"] = algorithm

            if algorithm == "percentage_based":
                passed = breakdown["severity_breakdown"].get("info", 0) + breakdown[
                    "severity_breakdown"
                ].get("warning", 0)
                total = breakdown["total_checks"]
                breakdown["score_calculation"] = {
                    "passed_checks": passed,
                    "failed_checks": total - passed,
                    "percentage": (passed / total * 100) if total > 0 else 0,
                }

            # Penalties applied
            for result in results:
                if result.severity in ["error", "critical"]:
                    penalty = self._calculate_penalty_for_result(
                        result, validation_type
                    )
                    breakdown["penalties_applied"].append(
                        {
                            "result_id": result.id,
                            "severity": result.severity,
                            "message": result.message,
                            "penalty": penalty,
                        }
                    )

            return breakdown

        except Exception as e:
            self.logger.error(f"Error getting score breakdown: {e}")
            return {"validation_type": validation_type, "error": str(e)}
