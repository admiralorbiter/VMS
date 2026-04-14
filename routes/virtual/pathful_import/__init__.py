"""
Pathful Import Package
======================

Extracted from the monolithic pathful_import.py (3,039 lines) as part of TD-020.

Modules:
    parsing: Date/name parsing, type coercion, constants, validation
    matching: Entity matching/creation for teachers, volunteers, events, districts
    processing: Row-level import processing
    routes: Flask route handler registration (load_pathful_routes)

This __init__.py re-exports all public symbols for backward compatibility.
"""

# --- Matching functions ---
from routes.virtual.pathful_import.matching import (  # noqa: E402
    build_import_caches,
    match_or_create_event,
    match_teacher,
    match_volunteer,
    upsert_district,
)

# --- Parsing utilities & constants ---
from routes.virtual.pathful_import.parsing import (  # noqa: E402
    EXPECTED_COLUMNS,
    OPTIONAL_SESSION_COLUMNS,
    PARTNER_FILTER,
    REQUIRED_SESSION_COLUMNS,
    admin_or_tenant_required,
    parse_name,
    parse_pathful_date,
    safe_int,
    safe_str,
    serialize_row_for_json,
    validate_session_report_columns,
)

# --- Processing functions ---
from routes.virtual.pathful_import.processing import (  # noqa: E402
    process_session_report_row,
)

# --- Route loader ---
from routes.virtual.pathful_import.routes import load_pathful_routes  # noqa: E402

__all__ = [
    # Parsing
    "REQUIRED_SESSION_COLUMNS",
    "OPTIONAL_SESSION_COLUMNS",
    "EXPECTED_COLUMNS",
    "PARTNER_FILTER",
    "admin_or_tenant_required",
    "parse_pathful_date",
    "parse_name",
    "safe_int",
    "safe_str",
    "serialize_row_for_json",
    "validate_session_report_columns",
    # Matching
    "build_import_caches",
    "upsert_district",
    "match_or_create_event",
    "match_teacher",
    "match_volunteer",
    # Processing
    "process_session_report_row",
    # Routes
    "load_pathful_routes",
]
