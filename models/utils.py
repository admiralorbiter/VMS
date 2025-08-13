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

Utility Functions:
- get_utc_now(): Get current UTC datetime with timezone awareness
- Standardized datetime handling across models
- Timezone-aware operations for consistency

Usage Examples:
    # Get current UTC time
    current_time = get_utc_now()

    # Use in model default values
    created_at = db.Column(db.DateTime, default=get_utc_now)

    # Use in model updates
    model.updated_at = get_utc_now()
"""

from datetime import datetime, timezone


def get_utc_now():
    """
    Get current UTC datetime with timezone awareness.

    This function provides a standardized way to get the current
    UTC datetime across all models. It ensures timezone awareness
    and consistency in datetime handling.

    Returns:
        datetime: Current UTC datetime with timezone information

    Usage:
        # In model default values (legacy; prefer DB-side defaults)
        created_at = db.Column(db.DateTime, default=get_utc_now)

        # In model updates
        model.updated_at = get_utc_now()

        # For timestamp comparisons
        if model.created_at < get_utc_now():
            # Model was created in the past
    """
    # Prefer DB-side defaults (server_default=func.now()) for most timestamp fields.
    return datetime.now(timezone.utc)
