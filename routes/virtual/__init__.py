"""
Virtual Routes Package
======================

This package contains PREP-KC staff-facing routes for virtual session management,
including Pathful imports, usage reports, and session breakdowns.

District-facing routes (portal, magic links, teacher dashboard) have been moved
to routes/district/. Legacy redirects in legacy_redirects.py ensure backward
compatibility for old /virtual/<slug> URLs.
"""

from routes.virtual.usage import load_usage_routes

# Register usage routes with the virtual blueprint
load_usage_routes()

# Register district issue reporting routes
from routes.virtual import issues  # noqa: F401, E402
