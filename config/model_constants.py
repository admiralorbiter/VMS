"""
Model Constants Module
=====================

This module defines constants used across VMS models for validation, formatting,
and business logic. Centralizing these constants improves maintainability and
ensures consistency across the application.

Key Constants:
- Student grade boundaries (GRADE_MIN, GRADE_MAX)
- Geographic zone definitions for local status
- Salesforce ID format specifications
- Date/time boundaries and intervals

Usage:
    from config.model_constants import GRADE_MIN, GRADE_MAX, SALESFORCE_ID_LENGTH

    if not (GRADE_MIN <= grade <= GRADE_MAX):
        raise ValueError(f"Grade must be between {GRADE_MIN} and {GRADE_MAX}")

Author: VMS Development Team
Last Updated: 2025-10-31
"""

# ==============================================================================
# Student Grade Constants
# ==============================================================================

GRADE_MIN = 0
"""Minimum valid grade level (Pre-K/K)."""

GRADE_MAX = 12
"""Maximum valid grade level (High school senior)."""

# ==============================================================================
# Geographic Zone Constants
# ==============================================================================

KC_METRO_ZIP_PREFIXES = ("640", "641", "660", "661", "664", "665", "666")
"""
Kansas City Metro zip code prefixes.

These zip codes indicate local status for the Kansas City metropolitan area.
Used in contact local status calculation in models/contact.py.

Examples:
    - 64030: Kansas City, MO
    - 64118: Kansas City, MO
    - 66002: Overland Park, KS
    - 66102: Kansas City, KS
"""

KC_REGION_ZIP_PREFIXES = ("644", "645", "646", "670", "671", "672", "673", "674")
"""
Kansas City Regional zip code prefixes.

These zip codes indicate partial/local status for areas within driving distance
of the Kansas City metro area. Used in contact local status calculation.

Examples:
    - 64477: St. Joseph, MO
    - 67037: Derby, KS
    - 67208: Wichita, KS
"""

# ==============================================================================
# Salesforce ID Format Constants
# ==============================================================================

SALESFORCE_ID_LENGTH = 18
"""
Standard Salesforce ID length in characters.

Salesforce IDs are 18 alphanumeric characters and uniquely identify records
in Salesforce. Used for validation in models with Salesforce integration.

Usage:
    from config.model_constants import SALESFORCE_ID_LENGTH

    if len(sf_id) != SALESFORCE_ID_LENGTH:
        raise ValueError(f"Salesforce ID must be {SALESFORCE_ID_LENGTH} characters")
"""

SALESFORCE_BASE_URL = "https://prep-kc.lightning.force.com/lightning/r"
"""
Base URL for Salesforce Lightning record links.

Used to generate direct links to Salesforce records from VMS.
"""

# ==============================================================================
# Academic Year Constants
# ==============================================================================

ACADEMIC_YEAR_FORMAT = "YYZZ"
"""
Academic year format pattern.

Format: YYZZ where YY is the starting year and ZZ is the ending year.
Example: "2425" = 2024-2025 academic year
"""

# ==============================================================================
# Date/Time Constants
# ==============================================================================

RECENT_ACTIVITY_DAYS = 30
"""
Number of days considered "recent" for activity tracking.

Used in models to determine if activities, emails, or other events are recent.
"""

# ==============================================================================
# Validation Constants
# ==============================================================================

MIN_DATE = None  # Use None or set to earliest valid date if needed
"""Minimum valid date for date fields. None means no minimum."""

MAX_DATE = None  # Use None or set to latest valid date if needed
"""Maximum valid date for date fields. None means no maximum."""

# ==============================================================================
# Business Logic Constants
# ==============================================================================

DEFAULT_VOLUNTEER_COUNT_TARGET = 1
"""
Default target for volunteer session counts.

Used in teacher progress tracking and similar metrics.
"""

# ==============================================================================
# Export all public constants
# ==============================================================================

__all__ = [
    # Student grades
    "GRADE_MIN",
    "GRADE_MAX",
    # Geographic zones
    "KC_METRO_ZIP_PREFIXES",
    "KC_REGION_ZIP_PREFIXES",
    # Salesforce
    "SALESFORCE_ID_LENGTH",
    "SALESFORCE_BASE_URL",
    # Academic year
    "ACADEMIC_YEAR_FORMAT",
    # Date/time
    "RECENT_ACTIVITY_DAYS",
    # Validation
    "MIN_DATE",
    "MAX_DATE",
    # Business logic
    "DEFAULT_VOLUNTEER_COUNT_TARGET",
]
