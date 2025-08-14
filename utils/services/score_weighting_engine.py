# utils/services/score_weighting_engine.py
"""
Score Weighting Engine for Phase 3.4.

This service manages weights and scoring algorithms for different
validation types and entity types, providing configurable scoring
that can be adjusted based on business priorities.
"""

import logging
from typing import Dict, List, Optional

from config.quality_scoring import QUALITY_WEIGHTS, SEVERITY_WEIGHTS


class ScoreWeightingEngine:
    """
    Engine for managing scoring weights and algorithms.

    This service provides configurable weights for different validation
    dimensions and severity levels, allowing business-driven quality scoring.
    """

    def __init__(self):
        """Initialize the score weighting engine."""
        self.logger = logging.getLogger(__name__)

        # Load default weights from configuration
        self.default_weights = QUALITY_WEIGHTS
        self.severity_weights = SEVERITY_WEIGHTS

        # Entity-specific weight overrides
        self.entity_weight_overrides = {}

        # Validation type weight overrides
        self.validation_type_overrides = {}

    def get_entity_weights(self, entity_type: str) -> Dict[str, float]:
        """
        Get weights for a specific entity type.

        Args:
            entity_type: Type of entity (e.g., 'volunteer', 'organization')

        Returns:
            Dictionary of validation type weights
        """
        try:
            # Check for entity-specific overrides
            if entity_type in self.entity_weight_overrides:
                return self.entity_weight_overrides[entity_type]

            # Get default weights for entity type
            entity_weights = self.default_weights.get(entity_type, {})

            if not entity_weights:
                # Fall back to default weights
                entity_weights = self.default_weights.get("default", {})

            # Validate and normalize weights
            normalized_weights = self._normalize_weights(entity_weights)

            self.logger.debug(f"Weights for {entity_type}: {normalized_weights}")
            return normalized_weights

        except Exception as e:
            self.logger.error(f"Error getting weights for {entity_type}: {e}")
            return self._get_fallback_weights()

    def get_validation_type_weight(
        self, entity_type: str, validation_type: str
    ) -> float:
        """
        Get weight for a specific validation type within an entity type.

        Args:
            entity_type: Type of entity
            validation_type: Type of validation

        Returns:
            Weight value (float)
        """
        try:
            entity_weights = self.get_entity_weights(entity_type)
            weight = entity_weights.get(validation_type, 1.0)

            # Check for validation type overrides
            if validation_type in self.validation_type_overrides:
                weight = self.validation_type_overrides[validation_type]

            return weight

        except Exception as e:
            self.logger.error(
                f"Error getting weight for {validation_type} in {entity_type}: {e}"
            )
            return 1.0

    def get_severity_weight(self, severity: str) -> float:
        """
        Get weight for a specific severity level.

        Args:
            severity: Severity level ('critical', 'error', 'warning', 'info')

        Returns:
            Weight value (float)
        """
        try:
            return self.severity_weights.get(severity, 1.0)
        except Exception as e:
            self.logger.error(f"Error getting severity weight for {severity}: {e}")
            return 1.0

    def set_entity_weight_override(self, entity_type: str, weights: Dict[str, float]):
        """
        Set custom weights for a specific entity type.

        Args:
            entity_type: Type of entity
            weights: Dictionary of validation type weights
        """
        try:
            # Validate weights
            validated_weights = self._validate_weights(weights)

            # Normalize weights
            normalized_weights = self._normalize_weights(validated_weights)

            self.entity_weight_overrides[entity_type] = normalized_weights

            self.logger.info(
                f"Set weight override for {entity_type}: {normalized_weights}"
            )

        except Exception as e:
            self.logger.error(f"Error setting weight override for {entity_type}: {e}")

    def set_validation_type_override(self, validation_type: str, weight: float):
        """
        Set custom weight for a specific validation type across all entities.

        Args:
            validation_type: Type of validation
            weight: Weight value
        """
        try:
            if weight < 0:
                raise ValueError("Weight must be non-negative")

            self.validation_type_overrides[validation_type] = weight

            self.logger.info(
                f"Set validation type override for {validation_type}: {weight}"
            )

        except Exception as e:
            self.logger.error(
                f"Error setting validation type override for {validation_type}: {e}"
            )

    def reset_entity_weights(self, entity_type: str = None):
        """
        Reset weight overrides for entity types.

        Args:
            entity_type: Specific entity type to reset, or None for all
        """
        try:
            if entity_type:
                if entity_type in self.entity_weight_overrides:
                    del self.entity_weight_overrides[entity_type]
                    self.logger.info(f"Reset weights for {entity_type}")
            else:
                self.entity_weight_overrides.clear()
                self.logger.info("Reset all entity weight overrides")

        except Exception as e:
            self.logger.error(f"Error resetting entity weights: {e}")

    def reset_validation_type_overrides(self):
        """Reset all validation type weight overrides."""
        try:
            self.validation_type_overrides.clear()
            self.logger.info("Reset all validation type weight overrides")

        except Exception as e:
            self.logger.error(f"Error resetting validation type overrides: {e}")

    def get_weight_summary(self) -> Dict:
        """
        Get summary of all current weights and overrides.

        Returns:
            Dictionary containing weight summary
        """
        try:
            summary = {
                "default_weights": self.default_weights,
                "severity_weights": self.severity_weights,
                "entity_overrides": self.entity_weight_overrides,
                "validation_type_overrides": self.validation_type_overrides,
                "total_entities": len(self.default_weights),
                "overridden_entities": len(self.entity_weight_overrides),
                "overridden_validation_types": len(self.validation_type_overrides),
            }

            return summary

        except Exception as e:
            self.logger.error(f"Error getting weight summary: {e}")
            return {"error": str(e)}

    def validate_weights(self, weights: Dict[str, float]) -> bool:
        """
        Validate that weights are properly formatted.

        Args:
            weights: Dictionary of weights to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(weights, dict):
                return False

            for key, value in weights.items():
                if not isinstance(key, str):
                    return False
                if not isinstance(value, (int, float)) or value < 0:
                    return False

            return True

        except Exception:
            return False

    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize weights to ensure they sum to a reasonable total.

        Args:
            weights: Dictionary of weights to normalize

        Returns:
            Normalized weights dictionary
        """
        try:
            if not weights:
                return self._get_fallback_weights()

            # Calculate total weight
            total_weight = sum(weights.values())

            if total_weight == 0:
                # All weights are zero, use fallback
                return self._get_fallback_weights()

            # Normalize to sum to 1.0
            normalized = {}
            for key, value in weights.items():
                normalized[key] = value / total_weight

            return normalized

        except Exception as e:
            self.logger.error(f"Error normalizing weights: {e}")
            return self._get_fallback_weights()

    def _validate_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Validate and clean weights dictionary.

        Args:
            weights: Dictionary of weights to validate

        Returns:
            Validated weights dictionary
        """
        try:
            if not self.validate_weights(weights):
                raise ValueError("Invalid weights format")

            # Ensure all values are positive
            validated = {}
            for key, value in weights.items():
                if value < 0:
                    self.logger.warning(f"Negative weight for {key}, setting to 0")
                    validated[key] = 0.0
                else:
                    validated[key] = float(value)

            return validated

        except Exception as e:
            self.logger.error(f"Error validating weights: {e}")
            return self._get_fallback_weights()

    def _get_fallback_weights(self) -> Dict[str, float]:
        """
        Get fallback weights when normal weights are unavailable.

        Returns:
            Dictionary of fallback weights
        """
        return {
            "field_completeness": 0.25,
            "data_types": 0.25,
            "business_rules": 0.25,
            "relationships": 0.25,
        }

    def calculate_weighted_score(
        self,
        scores: Dict[str, float],
        entity_type: str,
        validation_types: List[str] = None,
    ) -> float:
        """
        Calculate weighted score from individual dimension scores.

        Args:
            scores: Dictionary of validation type scores
            entity_type: Type of entity
            validation_types: List of validation types to include

        Returns:
            Weighted composite score
        """
        try:
            if not scores:
                return 0.0

            # Get weights for this entity type
            weights = self.get_entity_weights(entity_type)

            # Filter validation types if specified
            if validation_types:
                scores = {k: v for k, v in scores.items() if k in validation_types}
                weights = {k: v for k, v in weights.items() if k in validation_types}

            # Calculate weighted score
            total_weighted_score = 0.0
            total_weight = 0.0

            for validation_type, score in scores.items():
                weight = weights.get(validation_type, 1.0)
                total_weighted_score += score * weight
                total_weight += weight

            if total_weight == 0:
                return 0.0

            weighted_score = total_weighted_score / total_weight

            self.logger.debug(f"Weighted score for {entity_type}: {weighted_score:.2f}")
            return weighted_score

        except Exception as e:
            self.logger.error(f"Error calculating weighted score: {e}")
            return 0.0

    def get_scoring_algorithm(self, validation_type: str) -> str:
        """
        Get the scoring algorithm for a validation type.

        Args:
            validation_type: Type of validation

        Returns:
            Algorithm name/type
        """
        try:
            # Define scoring algorithms for different validation types
            algorithms = {
                "field_completeness": "percentage_based",
                "data_types": "penalty_based",
                "business_rules": "severity_weighted",
                "relationships": "percentage_based",
            }

            return algorithms.get(validation_type, "default")

        except Exception as e:
            self.logger.error(
                f"Error getting scoring algorithm for {validation_type}: {e}"
            )
            return "default"
