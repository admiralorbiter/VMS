"""
Cache management functions for virtual session reports.

DEPRECATED: This module now re-exports from services.cache_service.
All consumers should import directly from services.cache_service instead.
This file is kept for backward compatibility only.
"""

# Re-export from canonical location (services/cache_service.py)
from services.cache_service import (  # noqa: F401
    get_virtual_session_cache,
    get_virtual_session_district_cache,
    invalidate_virtual_session_caches,
    save_virtual_session_cache,
    save_virtual_session_district_cache,
)
