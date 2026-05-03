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

import re
from typing import Any, Callable, Dict, Optional, Set

from models import db

# =============================================================================
# HTML / LINK UTILITIES
# =============================================================================


def extract_href_from_html(html_or_url: str | None) -> str | None:
    """Extract a clean URL from a Salesforce HTML anchor tag.

    Salesforce stores several link fields (e.g. ``Registration_Link__c``) as
    HTML anchor tags::

        <a href="https://..." target="_blank">Sign up</a>

    This utility returns just the URL.  If the input is already a plain URL
    it is returned as-is.  Returns ``None`` for blank / ``None`` input.

    Example::

        >>> extract_href_from_html('<a href="https://example.com">Click</a>')
        'https://example.com'
        >>> extract_href_from_html('https://example.com')
        'https://example.com'
        >>> extract_href_from_html(None)
    """
    if not html_or_url:
        return None
    match = re.search(r'href=["\']([^"\']+)["\']', html_or_url)
    if match:
        return match.group(1)
    stripped = html_or_url.strip()
    return stripped if stripped else None


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


def build_participation_caches() -> tuple:
    """
    Pre-load the standard volunteer and event ID caches for participation processing.

    Returns the two dicts that all participation import loops need to avoid N+1 queries.
    Requires an active Flask application context.

    Returns:
        tuple: (volunteers_cache, events_cache) where
            volunteers_cache: {salesforce_individual_id (str) -> volunteer.id (int)}
            events_cache:     {salesforce_id (str)           -> event.id (int)}

    Usage::

        volunteers_cache, events_cache = build_participation_caches()
        process_participation_row(row, ..., volunteers_cache=volunteers_cache,
                                           events_cache=events_cache)

    Note:
        Caches are built at call time and are not updated during the import run.
        Records created *after* this call will not appear in the returned dicts.
        For participation import this is safe because new volunteers/events are
        never created mid-participation-loop.
    """
    from models.event import Event
    from models.volunteer import Volunteer

    volunteers_cache = build_lightweight_cache(
        Volunteer, Volunteer.salesforce_individual_id
    )
    events_cache = build_lightweight_cache(Event, Event.salesforce_id)
    return volunteers_cache, events_cache


def build_history_caches(db_session=None):
    """
    Pre-load caches needed for history imports to eliminate N+1 queries.
    Returns:
        tuple: (contacts_cache, events_cache, emails_cache)
            - contacts_cache: {salesforce_individual_id: contact.id}
            - events_cache: {salesforce_id: event.id}
            - emails_cache: {email_address: contact.id}
    """
    from models import db as _db
    from models.contact import Contact, Email
    from models.event import Event

    session = db_session or _db.session

    # 1. Contacts Cache (covers both Volunteers and Teachers via polymorphic base)
    contacts_cache = {
        sf_id: contact_id
        for contact_id, sf_id in session.query(
            Contact.id, Contact.salesforce_individual_id
        )
        .filter(Contact.salesforce_individual_id.isnot(None))
        .all()
    }

    # 2. Events Cache
    events_cache = {
        sf_id: event_id
        for event_id, sf_id in session.query(Event.id, Event.salesforce_id)
        .filter(Event.salesforce_id.isnot(None))
        .all()
    }

    # 3. Emails Cache
    # We order by ID to guarantee we store the first created match in case of collisions
    emails_cache = {}
    for email_str, contact_id in (
        session.query(Email.email, Email.contact_id)
        .filter(Email.email.isnot(None))
        .order_by(Email.id)
        .all()
    ):
        email_lower = email_str.strip().lower()
        if email_lower and email_lower not in emails_cache:
            emails_cache[email_lower] = contact_id

    return contacts_cache, events_cache, emails_cache
