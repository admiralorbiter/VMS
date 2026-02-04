"""
Salesforce Field Utilities
==========================

Helper functions for safely processing Salesforce field values.
Provides null-safe operations for common field transformations.

This module consolidates:
- Field extraction helpers (get_sf_string, get_sf_bool, etc.)
- Query chunking utilities for SQLite compatibility
- Parsing helpers for specific field types

Usage:
    from services.salesforce import safe_lower, get_sf_string, chunked_in_query

    # Safe string operations
    preferred_email = safe_lower(row.get("npe01__Preferred_Email__c"))

    # Get value with string coercion
    name = get_sf_string(row, "FirstName", default="Unknown")

    # Chunked query for large datasets
    lookup = chunked_in_query(Model, Model.salesforce_id, id_set)
"""

from typing import Any, Callable, Dict, Optional, Set

from models import db

# =============================================================================
# CONSTANTS
# =============================================================================

# SQLite has a limit on the number of variables in a query (typically 999)
# We chunk large IN queries to avoid this limit
QUERY_CHUNK_SIZE = 500


# =============================================================================
# STRING UTILITIES
# =============================================================================


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


# =============================================================================
# FIELD EXTRACTION UTILITIES
# =============================================================================


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


def get_sf_float(row: dict, field: str, default: float = 0.0) -> float:
    """
    Get a float value from Salesforce row.

    Args:
        row: Salesforce record dictionary
        field: Field name to retrieve
        default: Default value if field is None or invalid

    Returns:
        Float value

    Example:
        >>> get_sf_float({"Hours": "2.5"}, "Hours")
        2.5
        >>> get_sf_float({"Hours": None}, "Hours")
        0.0
    """
    value = row.get(field)
    if value is None:
        return default
    try:
        return float(value)
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


# =============================================================================
# PARSING UTILITIES
# =============================================================================


def safe_parse_delivery_hours(value) -> Optional[float]:
    """
    Safely parse delivery hours from Salesforce data.

    Args:
        value: Raw value from Salesforce Delivery_Hours__c field

    Returns:
        float or None: Parsed hours value or None if invalid
    """
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    try:
        hours = float(value)
        return hours if hours > 0 else None
    except (ValueError, TypeError):
        return None


# =============================================================================
# QUERY UTILITIES
# =============================================================================


def chunked_in_query(model, field, id_set: Set, key_func: Callable = None) -> Dict:
    """
    Execute IN queries in chunks to avoid SQLite's variable limit.

    SQLite has a default limit of 999 bind variables per query.
    This function partitions large ID sets into batches.

    Args:
        model: SQLAlchemy model class to query
        field: Model field to filter on (e.g., Model.salesforce_id)
        id_set: Set of IDs to query for
        key_func: Optional function to extract key from result (defaults to field value)

    Returns:
        Dictionary mapping key to model instance

    Example:
        # Get all volunteers by their Salesforce IDs
        volunteer_lookup = chunked_in_query(
            Volunteer,
            Volunteer.salesforce_id,
            salesforce_ids
        )
        volunteer = volunteer_lookup.get(sf_id)
    """
    if not id_set:
        return {}

    result = {}
    id_list = list(id_set)

    for i in range(0, len(id_list), QUERY_CHUNK_SIZE):
        chunk = id_list[i : i + QUERY_CHUNK_SIZE]
        rows = model.query.filter(field.in_(chunk)).all()
        for row in rows:
            if key_func:
                key = key_func(row)
            else:
                key = getattr(row, field.key)
            result[key] = row

    return result


def build_lightweight_cache(model, id_field, value_field=None) -> Dict:
    """
    Build a lightweight cache mapping ID to primary key or value.

    This is more memory-efficient than loading full ORM objects.

    Args:
        model: SQLAlchemy model class
        id_field: Field containing the lookup key (e.g., salesforce_id)
        value_field: Field to use as value (defaults to primary key 'id')

    Returns:
        Dictionary mapping id_field values to value_field values

    Example:
        # Build cache of salesforce_id -> local_id
        events_cache = build_lightweight_cache(Event, Event.salesforce_id)
        local_id = events_cache.get(sf_id)
    """
    if value_field is None:
        value_field = model.id

    query = db.session.query(value_field, id_field).filter(id_field.isnot(None))
    return {sf_id: local_id for local_id, sf_id in query.all()}
