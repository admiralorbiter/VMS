"""
Virtual Session Reports Package
================================

Extracted from the monolithic virtual_session.py (5,287 lines) as part of TD-020.

Modules:
    cache: Cache CRUD operations for virtual session report data
    computation: Data processing, filtering, and computation functions
    exports: Excel file generation for teacher progress reports
    teacher_progress: Teacher progress tracking computation

This __init__.py re-exports all public symbols for backward compatibility.
Existing imports like `from routes.reports.virtual_session import X` continue to work.
"""

from flask import Blueprint

# Create blueprint (preserved from original file)
virtual_bp = Blueprint("virtual", __name__)

# --- Cache functions ---
from routes.reports.virtual_session.cache import (  # noqa: E402
    get_virtual_session_cache,
    get_virtual_session_district_cache,
    invalidate_virtual_session_caches,
    save_virtual_session_cache,
    save_virtual_session_district_cache,
)

# --- Computation functions ---
from routes.reports.virtual_session.computation import (  # noqa: E402
    _district_name_matches,
    _get_primary_org_name_for_volunteer,
    apply_runtime_filters,
    apply_sorting_and_pagination,
    calculate_summaries_from_sessions,
    compute_virtual_session_data,
    compute_virtual_session_district_data,
    get_google_sheet_url,
    get_school_year_dates,
)

# --- Export functions ---
from routes.reports.virtual_session.exports import (  # noqa: E402
    generate_teacher_progress_excel,
)

# --- Teacher progress functions ---
from routes.reports.virtual_session.teacher_progress import (  # noqa: E402
    compute_teacher_progress_tracking,
    compute_teacher_school_breakdown,
)

__all__ = [
    # Blueprint
    "virtual_bp",
    # Cache
    "get_virtual_session_cache",
    "save_virtual_session_cache",
    "get_virtual_session_district_cache",
    "save_virtual_session_district_cache",
    "invalidate_virtual_session_caches",
    # Computation
    "get_school_year_dates",
    "apply_runtime_filters",
    "calculate_summaries_from_sessions",
    "apply_sorting_and_pagination",
    "get_google_sheet_url",
    "_get_primary_org_name_for_volunteer",
    "compute_virtual_session_data",
    "_district_name_matches",
    "compute_virtual_session_district_data",
    # Exports
    "generate_teacher_progress_excel",
    # Teacher Progress
    "compute_teacher_school_breakdown",
    "compute_teacher_progress_tracking",
]
