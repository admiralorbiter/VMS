"""
Management Package
==================

Extracted from the monolithic management.py (1,410 lines) as part of TD-019.

Modules:
    routes: Blueprint + admin panel, logs, cache refresh, user management
    data_integrity: Data flags, student participation dedup
    google_sheets: Google Sheets CRUD
    import_data: File import, Salesforce import, school/district management
    bug_reports: Bug report listing, resolution, deletion
    cache_management: Cache status and scheduler (pre-existing)
"""

# Re-export update_school_levels for backward compat
# (used by routes/salesforce/school_import.py)
from routes.management.import_data import update_school_levels

# Blueprint is created in routes.py and sub-modules register onto it
from routes.management.routes import management_bp

__all__ = [
    "management_bp",
    "update_school_levels",
]
