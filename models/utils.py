"""
Models Utilities Module
======================

This module provides utility functions for the models package in the VMS system.
It contains common helper functions used across multiple model classes.

Key Features:
- UTC datetime utilities
- Timezone-aware datetime handling
- Common model utility functions
- Standardized datetime formatting
- Salesforce ID validation

Utility Functions:
- get_utc_now(): Get current UTC datetime with timezone awareness
- validate_salesforce_id(): Validate Salesforce ID format
- Standardized datetime handling across models
- Timezone-aware operations for consistency

Usage Examples:
    # Get current UTC time
    current_time = get_utc_now()

    # Use in model updates
    model.updated_at = get_utc_now()

    # Validate Salesforce ID
    sf_id = validate_salesforce_id("0011234567890ABCD")
"""

from datetime import datetime, timezone

try:
    from config.model_constants import SALESFORCE_ID_LENGTH
except ImportError:
    # Fallback if constants not available
    SALESFORCE_ID_LENGTH = 18


def get_utc_now():
    """
    Get current UTC datetime with timezone awareness.

    This function provides a standardized way to get the current
    UTC datetime across all models. It ensures timezone awareness
    and consistency in datetime handling.

    Returns:
        datetime: Current UTC datetime with timezone information

    Usage:
        # In model updates (NOT for column defaults)
        model.updated_at = get_utc_now()

        # For timestamp comparisons
        if model.created_at < get_utc_now():
            # Model was created in the past

    Note:
        For column defaults, use server_default=func.now() instead.
        This function is only for setting timestamps in model methods.
    """
    # Prefer DB-side defaults (server_default=func.now()) for most timestamp fields.
    return datetime.now(timezone.utc)


def validate_salesforce_id(value):
    """
    Validate Salesforce ID format.

    Salesforce IDs must be exactly 18 alphanumeric characters. This validator
    checks the format and raises ValueError if invalid.

    Args:
        value: Salesforce ID to validate (string or None)

    Returns:
        str: Validated Salesforce ID

    Raises:
        ValueError: If the ID format is invalid

    Usage:
        # In model validators
        @validates("salesforce_id")
        def validate_salesforce_id_field(self, key, value):
            return validate_salesforce_id(value)

        # Or use directly
        validated_id = validate_salesforce_id("0011234567890ABCDE")

    Examples:
        >>> validate_salesforce_id("0011234567890ABCDE")
        '0011234567890ABCDE'

        >>> validate_salesforce_id("invalid")
        ValueError: Salesforce ID must be exactly 18 alphanumeric characters

        >>> validate_salesforce_id(None)
        None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("Salesforce ID must be a string")
    
    # Allow empty strings (treated as None)
    if value == "":
        return None

    if len(value) != SALESFORCE_ID_LENGTH:
        raise ValueError(
            f"Salesforce ID must be exactly {SALESFORCE_ID_LENGTH} alphanumeric characters"
        )

    if not value.isalnum():
        raise ValueError(
            f"Salesforce ID must be exactly {SALESFORCE_ID_LENGTH} alphanumeric characters"
        )

    return value
