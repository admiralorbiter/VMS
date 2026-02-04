"""
Salesforce Integration Services
===============================

Centralized services for Salesforce data synchronization.

This package provides:
- Client: Salesforce API connection and query helpers
- Mappers: Enum and field value mappings
- Utils: Common utility functions for data processing
- Delta Sync: Incremental sync watermark management
- Processors: Row-level data processing logic

Usage:
    from services.salesforce import get_salesforce_client, safe_query_all
    from services.salesforce.processors.event import process_event_row
"""

# Re-export client functions
from services.salesforce.client import get_salesforce_client, safe_query, safe_query_all

# Re-export delta sync
from services.salesforce.delta_sync import DeltaSyncHelper

# Re-export mapper functions
from services.salesforce.mappers import (
    map_age_group,
    map_education_level,
    map_grade_level,
    map_race_ethnicity,
)

# Re-export utility functions
from services.salesforce.utils import (
    QUERY_CHUNK_SIZE,
    chunked_in_query,
    get_sf_bool,
    get_sf_int,
    get_sf_list,
    get_sf_string,
    safe_lower,
    safe_parse_delivery_hours,
    safe_strip,
)

__all__ = [
    # Client
    "get_salesforce_client",
    "safe_query",
    "safe_query_all",
    # Mappers
    "map_age_group",
    "map_education_level",
    "map_grade_level",
    "map_race_ethnicity",
    # Utils
    "chunked_in_query",
    "get_sf_bool",
    "get_sf_int",
    "get_sf_list",
    "get_sf_string",
    "safe_lower",
    "safe_parse_delivery_hours",
    "safe_strip",
    "QUERY_CHUNK_SIZE",
    # Delta sync
    "DeltaSyncHelper",
]
