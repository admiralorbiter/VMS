"""
District Portal Routes Module
============================

This module provides district-specific portal landing pages.
It supports database-driven tenant configuration via the Tenant
model (District Suite), with backward compatibility for legacy hardcoded config.

Key Features:
- Database-driven tenant configuration (primary)
- Legacy registry fallback for backward compatibility
- Landing pages with separate login options for teachers and district staff
- District-specific branding and messaging from tenant settings

Main Endpoints:
- GET /district/<slug>/portal: District portal landing page

Tenant Configuration:
- Tenants are stored in the database with configurable settings
- Feature flags control available functionality
- API key support for district website integration

Legacy Support:
- DISTRICT_PORTALS dict still checked as fallback
- Will be removed after all districts are migrated to database
"""

from flask import abort, render_template

from models import Tenant
from routes.district import district_bp

# Reserved route names that cannot be used as district slugs
RESERVED_SLUGS = {
    "events",
    "volunteers",
    "recruitment",
    "settings",
    "signup",
    "users",
    "calendar",
}

# Legacy District Portal Registry (backward compatibility)
# TODO: Remove after migrating all districts to database
DISTRICT_PORTALS = {
    "kck": {
        "slug": "kck",
        "display_name": "Kansas City Kansas Public Schools",
        "short_name": "KCK",
        "welcome_message": "Welcome to the KCK District Portal",
        "teacher_login_label": "Teacher Login",
        "teacher_login_description": "Access your virtual session progress and resources",
        "staff_login_label": "District Staff Login",
        "staff_login_description": "View district-wide progress and analytics",
        "teacher_login_url": "/district/kck/teacher/request-link",
        "staff_login_url": "/login",
    },
}


def get_district_portal(district_slug: str) -> dict:
    """
    Get district portal configuration by slug.

    Checks database first (Tenant model), then falls back to
    legacy DISTRICT_PORTALS dict for backward compatibility.

    Args:
        district_slug: The district slug (e.g., 'kck')

    Returns:
        Dictionary containing district portal configuration

    Raises:
        KeyError: If district slug is not found in database or legacy registry
    """
    # Try database first (new Tenant model)
    tenant = Tenant.query.filter_by(slug=district_slug, is_active=True).first()
    if tenant:
        config = tenant.get_portal_config()
        # Update URLs to new /district/ paths
        config["teacher_login_url"] = f"/district/{district_slug}/teacher/request-link"
        return config

    # Fall back to legacy registry for backward compatibility
    if district_slug in DISTRICT_PORTALS:
        return DISTRICT_PORTALS[district_slug]

    raise KeyError(f"District portal '{district_slug}' not found")


@district_bp.route("/<slug>/portal")
def portal_landing(slug: str):
    """
    Display the district portal landing page.

    Provides a landing page with two separate login options:
    - Teacher login
    - District staff login

    Configuration is loaded from the Tenant model (database) first,
    with fallback to the legacy DISTRICT_PORTALS dict.

    Args:
        slug: The district slug from the URL (e.g., 'kck')

    Returns:
        Rendered district portal landing page template

    Raises:
        404: If district slug is not found or is a reserved name
    """
    # Check if slug is reserved (should be handled by more specific routes, but safeguard)
    if slug.lower() in RESERVED_SLUGS:
        abort(404, description=f"Invalid district portal slug: '{slug}'")

    try:
        portal_config = get_district_portal(slug)
    except KeyError:
        abort(404, description=f"District portal '{slug}' not found")

    return render_template(
        "district/portal/landing.html",
        district=portal_config,
    )
