# utils/services/threshold_manager.py
"""
Threshold Manager for Phase 3.4.

This service manages quality thresholds and configurations for different
entity types and validation types, providing configurable quality standards.
"""

import logging
from typing import Dict, List, Optional, Union

from config.quality_scoring import QUALITY_SCORE_RANGES, QUALITY_THRESHOLDS


class ThresholdManager:
    """
    Manager for quality thresholds and configurations.

    This service provides configurable quality thresholds per entity type,
    dynamic threshold adjustment, and threshold validation and alerts.
    """

    def __init__(self):
        """Initialize the threshold manager."""
        self.logger = logging.getLogger(__name__)

        # Load default thresholds from configuration
        self.default_thresholds = QUALITY_THRESHOLDS
        self.quality_ranges = QUALITY_SCORE_RANGES

        # Entity-specific threshold overrides
        self.entity_threshold_overrides = {}

        # Validation type specific thresholds
        self.validation_type_thresholds = {}

        # Dynamic threshold adjustment settings
        self.dynamic_adjustment_enabled = True
        self.adjustment_factors = {
            "historical_performance": 0.3,
            "business_criticality": 0.4,
            "data_volume": 0.2,
            "compliance_requirements": 0.1,
        }

    def get_entity_threshold(self, entity_type: str) -> float:
        """
        Get quality threshold for a specific entity type.

        Args:
            entity_type: Type of entity (e.g., 'volunteer', 'organization')

        Returns:
            Quality threshold value (0-100)
        """
        try:
            # Check for entity-specific overrides
            if entity_type in self.entity_threshold_overrides:
                return self.entity_threshold_overrides[entity_type]

            # Get default threshold for entity type
            threshold = self.default_thresholds.get(
                entity_type, self.default_thresholds.get("default", 75.0)
            )

            # Apply dynamic adjustment if enabled
            if self.dynamic_adjustment_enabled:
                threshold = self._apply_dynamic_adjustment(entity_type, threshold)

            self.logger.debug(f"Threshold for {entity_type}: {threshold}")
            return threshold

        except Exception as e:
            self.logger.error(f"Error getting threshold for {entity_type}: {e}")
            return 75.0  # Fallback threshold

    def get_validation_type_threshold(
        self, entity_type: str, validation_type: str
    ) -> float:
        """
        Get threshold for a specific validation type within an entity type.

        Args:
            entity_type: Type of entity
            validation_type: Type of validation

        Returns:
            Threshold value (float)
        """
        try:
            # Check for validation type specific thresholds
            if validation_type in self.validation_type_thresholds:
                return self.validation_type_thresholds[validation_type]

            # Get entity threshold and adjust based on validation type
            entity_threshold = self.get_entity_threshold(entity_type)

            # Adjust threshold based on validation type importance
            adjustment_factor = self._get_validation_type_importance(validation_type)
            adjusted_threshold = entity_threshold * adjustment_factor

            return max(50.0, min(100.0, adjusted_threshold))

        except Exception as e:
            self.logger.error(f"Error getting validation type threshold: {e}")
            return 75.0

    def set_entity_threshold_override(self, entity_type: str, threshold: float):
        """
        Set custom threshold for a specific entity type.

        Args:
            entity_type: Type of entity
            threshold: Quality threshold value (0-100)
        """
        try:
            if not 0 <= threshold <= 100:
                raise ValueError("Threshold must be between 0 and 100")

            self.entity_threshold_overrides[entity_type] = float(threshold)

            self.logger.info(f"Set threshold override for {entity_type}: {threshold}")

        except Exception as e:
            self.logger.error(
                f"Error setting threshold override for {entity_type}: {e}"
            )

    def set_validation_type_threshold(self, validation_type: str, threshold: float):
        """
        Set custom threshold for a specific validation type across all entities.

        Args:
            validation_type: Type of validation
            threshold: Threshold value (0-100)
        """
        try:
            if not 0 <= threshold <= 100:
                raise ValueError("Threshold must be between 0 and 100")

            self.validation_type_thresholds[validation_type] = float(threshold)

            self.logger.info(
                f"Set validation type threshold for {validation_type}: {threshold}"
            )

        except Exception as e:
            self.logger.error(
                f"Error setting validation type threshold for {validation_type}: {e}"
            )

    def reset_entity_thresholds(self, entity_type: str = None):
        """
        Reset threshold overrides for entity types.

        Args:
            entity_type: Specific entity type to reset, or None for all
        """
        try:
            if entity_type:
                if entity_type in self.entity_threshold_overrides:
                    del self.entity_threshold_overrides[entity_type]
                    self.logger.info(f"Reset threshold for {entity_type}")
            else:
                self.entity_threshold_overrides.clear()
                self.logger.info("Reset all entity threshold overrides")

        except Exception as e:
            self.logger.error(f"Error resetting entity thresholds: {e}")

    def reset_validation_type_thresholds(self):
        """Reset all validation type threshold overrides."""
        try:
            self.validation_type_thresholds.clear()
            self.logger.info("Reset all validation type threshold overrides")

        except Exception as e:
            self.logger.error(f"Error resetting validation type thresholds: {e}")

    def get_quality_status(self, score: float, entity_type: str = None) -> str:
        """
        Get quality status based on score and entity type.

        Args:
            score: Quality score (0-100)
            entity_type: Optional entity type for context

        Returns:
            Quality status string
        """
        try:
            # Get threshold for entity type if provided
            threshold = None
            if entity_type:
                threshold = self.get_entity_threshold(entity_type)

            # Determine status based on score ranges
            for status, range_info in self.quality_ranges.items():
                if range_info["min"] <= score <= range_info["max"]:
                    return status

            # Fallback to poor if score doesn't match any range
            return "poor"

        except Exception as e:
            self.logger.error(f"Error getting quality status: {e}")
            return "unknown"

    def get_quality_color(self, status: str) -> str:
        """
        Get color associated with a quality status.

        Args:
            status: Quality status string

        Returns:
            Color hex code
        """
        try:
            return self.quality_ranges.get(status, {}).get("color", "#6c757d")
        except Exception:
            return "#6c757d"

    def get_quality_description(self, status: str) -> str:
        """
        Get description for a quality status.

        Args:
            status: Quality status string

        Returns:
            Description string
        """
        try:
            return self.quality_ranges.get(status, {}).get(
                "description", "Unknown quality status"
            )
        except Exception:
            return "Unknown quality status"

    def validate_threshold(self, threshold: float) -> bool:
        """
        Validate that a threshold value is within acceptable range.

        Args:
            threshold: Threshold value to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            return isinstance(threshold, (int, float)) and 0 <= threshold <= 100
        except Exception:
            return False

    def get_threshold_summary(self) -> Dict:
        """
        Get summary of all current thresholds and overrides.

        Returns:
            Dictionary containing threshold summary
        """
        try:
            summary = {
                "default_thresholds": self.default_thresholds,
                "entity_overrides": self.entity_threshold_overrides,
                "validation_type_thresholds": self.validation_type_thresholds,
                "quality_ranges": self.quality_ranges,
                "total_entities": len(self.default_thresholds),
                "overridden_entities": len(self.entity_threshold_overrides),
                "overridden_validation_types": len(self.validation_type_thresholds),
                "dynamic_adjustment_enabled": self.dynamic_adjustment_enabled,
            }

            return summary

        except Exception as e:
            self.logger.error(f"Error getting threshold summary: {e}")
            return {"error": str(e)}

    def enable_dynamic_adjustment(self, enabled: bool = True):
        """
        Enable or disable dynamic threshold adjustment.

        Args:
            enabled: Whether to enable dynamic adjustment
        """
        try:
            self.dynamic_adjustment_enabled = enabled
            self.logger.info(
                f"Dynamic threshold adjustment {'enabled' if enabled else 'disabled'}"
            )

        except Exception as e:
            self.logger.error(f"Error setting dynamic adjustment: {e}")

    def set_adjustment_factors(self, factors: Dict[str, float]):
        """
        Set factors for dynamic threshold adjustment.

        Args:
            factors: Dictionary of adjustment factors
        """
        try:
            # Validate factors
            total_factor = sum(factors.values())
            if abs(total_factor - 1.0) > 0.01:
                self.logger.warning(
                    f"Adjustment factors sum to {total_factor}, should sum to 1.0"
                )

            self.adjustment_factors.update(factors)
            self.logger.info(f"Updated adjustment factors: {factors}")

        except Exception as e:
            self.logger.error(f"Error setting adjustment factors: {e}")

    def _apply_dynamic_adjustment(
        self, entity_type: str, base_threshold: float
    ) -> float:
        """
        Apply dynamic adjustment to base threshold based on various factors.

        Args:
            entity_type: Type of entity
            base_threshold: Base threshold value

        Returns:
            Adjusted threshold value
        """
        try:
            if not self.dynamic_adjustment_enabled:
                return base_threshold

            adjustment = 0.0

            # Historical performance factor
            historical_factor = self._get_historical_performance_factor(entity_type)
            adjustment += (
                historical_factor * self.adjustment_factors["historical_performance"]
            )

            # Business criticality factor
            business_factor = self._get_business_criticality_factor(entity_type)
            adjustment += (
                business_factor * self.adjustment_factors["business_criticality"]
            )

            # Data volume factor
            volume_factor = self._get_data_volume_factor(entity_type)
            adjustment += volume_factor * self.adjustment_factors["data_volume"]

            # Compliance requirements factor
            compliance_factor = self._get_compliance_requirements_factor(entity_type)
            adjustment += (
                compliance_factor * self.adjustment_factors["compliance_requirements"]
            )

            # Apply adjustment to base threshold
            adjusted_threshold = base_threshold + adjustment

            # Ensure threshold stays within reasonable bounds
            adjusted_threshold = max(50.0, min(95.0, adjusted_threshold))

            return adjusted_threshold

        except Exception as e:
            self.logger.error(f"Error applying dynamic adjustment: {e}")
            return base_threshold

    def _get_validation_type_importance(self, validation_type: str) -> float:
        """
        Get importance factor for a validation type.

        Args:
            validation_type: Type of validation

        Returns:
            Importance factor (0.5-1.5)
        """
        try:
            # Define importance factors for different validation types
            importance_factors = {
                "field_completeness": 1.0,  # Standard importance
                "data_types": 1.1,  # Slightly more important
                "business_rules": 1.2,  # More important
                "relationships": 0.9,  # Slightly less important
            }

            return importance_factors.get(validation_type, 1.0)

        except Exception:
            return 1.0

    def _get_historical_performance_factor(self, entity_type: str) -> float:
        """
        Get historical performance adjustment factor.

        Args:
            entity_type: Type of entity

        Returns:
            Adjustment factor (-10 to +10)
        """
        try:
            # This would typically query historical data
            # For now, return a neutral factor
            return 0.0

        except Exception:
            return 0.0

    def _get_business_criticality_factor(self, entity_type: str) -> float:
        """
        Get business criticality adjustment factor.

        Args:
            entity_type: Type of entity

        Returns:
            Adjustment factor (-10 to +10)
        """
        try:
            # Define business criticality factors
            criticality_factors = {
                "volunteer": 5.0,  # High criticality
                "organization": 8.0,  # Very high criticality
                "event": 3.0,  # Medium criticality
                "student": 6.0,  # High criticality
                "teacher": 6.0,  # High criticality
            }

            return criticality_factors.get(entity_type, 0.0)

        except Exception:
            return 0.0

    def _get_data_volume_factor(self, entity_type: str) -> float:
        """
        Get data volume adjustment factor.

        Args:
            entity_type: Type of entity

        Returns:
            Adjustment factor (-5 to +5)
        """
        try:
            # This would typically query actual data volumes
            # For now, return a neutral factor
            return 0.0

        except Exception:
            return 0.0

    def _get_compliance_requirements_factor(self, entity_type: str) -> float:
        """
        Get compliance requirements adjustment factor.

        Args:
            entity_type: Type of entity

        Returns:
            Adjustment factor (-5 to +5)
        """
        try:
            # Define compliance requirement factors
            compliance_factors = {
                "volunteer": 3.0,  # Medium compliance requirements
                "organization": 5.0,  # High compliance requirements
                "event": 2.0,  # Low compliance requirements
                "student": 4.0,  # Medium-high compliance requirements
                "teacher": 4.0,  # Medium-high compliance requirements
            }

            return compliance_factors.get(entity_type, 0.0)

        except Exception:
            return 0.0
