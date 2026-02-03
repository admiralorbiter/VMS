"""
Salesforce Field Utilities
==========================

Helper functions for safely processing Salesforce field values.
Provides null-safe operations for common field transformations.

Usage:
    from services.salesforce_utils import safe_lower, safe_strip, get_sf_string, get_sf_bool

    # Safe string operations
    preferred_email = safe_lower(row.get("npe01__Preferred_Email__c"))

    # Get value with string coercion
    name = get_sf_string(row, "FirstName", default="Unknown")

    # Get boolean from truthy/falsy Salesforce values
    is_active = get_sf_bool(row, "Active__c")
"""

from typing import Any, Optional


def safe_lower(value: Optional[str]) -> str:
    """
    Safely convert value to lowercase, returning empty string for None.

    Args:
        value: String value that may be None

    Returns:
        Lowercase string, or empty string if None

    Example:
        >>> safe_lower(None)
        ''
        >>> safe_lower("HELLO")
        'hello'
    """
    return (value or "").strip().lower()


def safe_strip(value: Optional[str]) -> str:
    """
    Safely strip whitespace from value, returning empty string for None.

    Args:
        value: String value that may be None

    Returns:
        Stripped string, or empty string if None

    Example:
        >>> safe_strip(None)
        ''
        >>> safe_strip("  hello  ")
        'hello'
    """
    return (value or "").strip()


def get_sf_string(row: dict, field: str, default: str = "") -> str:
    """
    Get a string value from Salesforce row, with null coercion.

    Args:
        row: Salesforce record dictionary
        field: Field name to retrieve
        default: Default value if field is None/empty

    Returns:
        String value, stripped of whitespace

    Example:
        >>> get_sf_string({"FirstName": "John"}, "FirstName")
        'John'
        >>> get_sf_string({"FirstName": None}, "FirstName", "Unknown")
        'Unknown'
    """
    value = row.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return str(value).strip()


def get_sf_bool(row: dict, field: str, default: bool = False) -> bool:
    """
    Get a boolean value from Salesforce row, handling various truthy formats.

    Salesforce may return booleans as True/False, 'true'/'false', 1/0, etc.

    Args:
        row: Salesforce record dictionary
        field: Field name to retrieve
        default: Default value if field is None

    Returns:
        Boolean value

    Example:
        >>> get_sf_bool({"Active": "true"}, "Active")
        True
        >>> get_sf_bool({"Active": None}, "Active")
        False
    """
    value = row.get(field)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "t", "y")
    return bool(value)


def get_sf_int(row: dict, field: str, default: int = 0) -> int:
    """
    Get an integer value from Salesforce row.

    Handles float strings like "42.0" by converting to float first.

    Args:
        row: Salesforce record dictionary
        field: Field name to retrieve
        default: Default value if field is None or invalid

    Returns:
        Integer value

    Example:
        >>> get_sf_int({"Count": "42.0"}, "Count")
        42
        >>> get_sf_int({"Count": None}, "Count")
        0
    """
    value = row.get(field)
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def get_sf_list(row: dict, field: str, separator: str = ";") -> list:
    """
    Get a list of values from a Salesforce multi-select picklist or semicolon-separated string.

    Args:
        row: Salesforce record dictionary
        field: Field name to retrieve
        separator: Character used to separate values (default semicolon for Salesforce)

    Returns:
        List of stripped, non-empty string values

    Example:
        >>> get_sf_list({"Skills": "Python;Java;SQL"}, "Skills")
        ['Python', 'Java', 'SQL']
        >>> get_sf_list({"Skills": None}, "Skills")
        []
    """
    value = row.get(field)
    if not value:
        return []
    return [item.strip() for item in str(value).split(separator) if item.strip()]
