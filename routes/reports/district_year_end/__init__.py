"""
District Year-End Report Package
=================================

Extracted from district_year_end.py (2,406 lines) as part of TD-020.

Modules:
    computation: Stats calculation, caching, school-level grouping, format helpers
    routes: Blueprint creation and load_routes() with 14 route handlers
"""

# Re-export from common (backward compat for cache_refresh_scheduler.py)
from routes.reports.common import generate_district_stats  # noqa: F401

# --- Computation functions ---
from routes.reports.district_year_end.computation import (
    cache_district_stats_with_events,
    calculate_enhanced_district_stats,
    convert_academic_year_format,
    convert_school_year_format,
    generate_schools_by_level_data,
    refresh_district_cache,
)

# --- Routes & Blueprint ---
from routes.reports.district_year_end.routes import district_year_end_bp, load_routes

__all__ = [
    "district_year_end_bp",
    "load_routes",
    "cache_district_stats_with_events",
    "calculate_enhanced_district_stats",
    "convert_academic_year_format",
    "convert_school_year_format",
    "generate_schools_by_level_data",
    "generate_district_stats",
    "refresh_district_cache",
]
