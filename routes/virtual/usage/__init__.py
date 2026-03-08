"""
Virtual Session Usage Package
==============================

This package was extracted from the monolithic usage.py (7,472 lines)
into domain-specific modules for maintainability.

Modules:
    cache               - Cache CRUD for session/district report caches
    computation         - Data processing, filtering, summary calculation
    exports             - Excel export generation
    session_routes      - Session CRUD routes (view, search, create, edit, delete)
    district_routes     - District reporting and export routes
    teacher_progress_routes - Teacher progress tracking and recruitment routes
    teacher_progress    - Standalone teacher progress computation helpers
"""

# Re-export items from routes.reports.common that were previously
# accessible through usage.py's module namespace
from routes.reports.common import (
    generate_school_year_options,
    get_current_virtual_year,
    get_semester_dates,
    get_virtual_year_dates,
)

from .cache import (
    get_virtual_session_cache,
    get_virtual_session_district_cache,
    invalidate_virtual_session_caches,
    save_virtual_session_cache,
    save_virtual_session_district_cache,
)

# Re-export public API for backward compatibility
from .computation import (
    _district_name_matches,
    apply_runtime_filters,
    apply_sorting_and_pagination,
    calculate_summaries_from_sessions,
    compute_virtual_session_data,
    compute_virtual_session_district_data,
    get_school_year_dates,
)
from .district_routes import load_district_routes
from .exports import generate_teacher_progress_excel
from .session_routes import load_session_routes
from .teacher_progress import (
    compute_teacher_progress_tracking,
    compute_teacher_school_breakdown,
    match_teacher_progress_to_teachers,
    name_similarity,
    normalize_name,
    snapshot_semester_progress,
)
from .teacher_progress_routes import load_teacher_progress_routes


def load_usage_routes():
    """Register all usage routes on virtual_bp."""
    load_session_routes()
    load_district_routes()
    load_teacher_progress_routes()
