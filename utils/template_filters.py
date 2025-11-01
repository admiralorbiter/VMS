"""
Template Filters Module
======================
Custom Jinja2 template filters for the VMS application.

This module provides reusable template filters that are registered with the
Flask Jinja2 environment for use across all templates.

Available Filters:
- from_json: Safely parse JSON strings to Python objects
"""

import json


def from_json_filter(json_string):
    """
    Custom Jinja2 filter to parse JSON strings.

    Safely converts JSON strings to Python objects, returning empty list
    for invalid or empty values. Used for deserializing stored JSON data
    in templates.

    Args:
        json_string: JSON string to parse, or already-parsed object

    Returns:
        Parsed Python object (list/dict) or empty list on failure
    """
    if not json_string or json_string == "None" or json_string == "null":
        return []
    try:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    except (json.JSONDecodeError, TypeError):
        return []
