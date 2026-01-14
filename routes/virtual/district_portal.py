"""
District Portal Routes Module
============================

This module provides district-specific portal landing pages for the virtual
feature. It supports multiple districts through a configuration registry,
allowing easy expansion to new districts without code duplication.

Key Features:
- Scalable district portal system with registry-based configuration
- Landing pages with separate login options for teachers and district staff
- District-specific branding and messaging
- Easy expansion to new districts via configuration

Main Endpoints:
- GET /virtual/<district_slug>: District portal landing page

District Registry:
- Each district is configured with a slug, display name, and portal settings
- Supports district-specific branding and messaging
- Can be extended with additional configuration as needed

Future Expansion:
- Teacher-specific routes (e.g., /virtual/<district_slug>/teacher/*)
- District staff routes (e.g., /virtual/<district_slug>/staff/*)
- District progress tracking features
"""

from flask import abort, render_template

from routes.virtual.routes import virtual_bp

# Reserved route names that cannot be used as district slugs
RESERVED_SLUGS = {
    "usage",
    "events",
    "event",
    "virtual",
    "purge",
    "import-sheet",
    "google-sheets",
}

# District Portal Registry
# Add new districts by adding entries to this dictionary
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
        # Staff login redirects to main login page
        "teacher_login_url": "/virtual/kck/teacher/select",  # Teacher selection page
        "staff_login_url": "/login",
    },
    # Future districts can be added here:
    # "hmsd": {
    #     "slug": "hmsd",
    #     "display_name": "HMSD District",
    #     ...
    # },
}


def get_district_portal(district_slug: str) -> dict:
    """
    Get district portal configuration by slug.

    Args:
        district_slug: The district slug (e.g., 'kck')

    Returns:
        Dictionary containing district portal configuration

    Raises:
        KeyError: If district slug is not found in registry
    """
    if district_slug not in DISTRICT_PORTALS:
        raise KeyError(f"District portal '{district_slug}' not found")
    return DISTRICT_PORTALS[district_slug]


@virtual_bp.route("/<district_slug>")
def district_portal_landing(district_slug: str):
    """
    Display the district portal landing page.

    Provides a landing page with two separate login options:
    - Teacher login
    - District staff login

    Args:
        district_slug: The district slug from the URL (e.g., 'kck')

    Returns:
        Rendered district portal landing page template

    Raises:
        404: If district slug is not found in registry or is a reserved name
    """
    # Check if slug is reserved (should be handled by more specific routes, but safeguard)
    if district_slug.lower() in RESERVED_SLUGS:
        abort(404, description=f"Invalid district portal slug: '{district_slug}'")

    try:
        portal_config = get_district_portal(district_slug)
    except KeyError:
        abort(404, description=f"District portal '{district_slug}' not found")

    return render_template(
        "virtual/district_portal/landing.html",
        district=portal_config,
    )
