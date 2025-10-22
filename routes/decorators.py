"""
Security decorators for district and school scoping.

These decorators provide flexible permission checking for routes
that need to restrict access based on user scope (global/district/school).
"""

from functools import wraps

from flask import jsonify, request
from flask_login import current_user


def district_scoped_required(func):
    """
    Decorator to check if user can access the requested district.

    Allows global users full access, checks district-scoped users
    have permission for the specific district in the request.

    Usage:
        @district_scoped_required
        def district_report(district_name):
            # User already validated for district access
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Global users have access to everything
        if current_user.scope_type == "global":
            return func(*args, **kwargs)

        # Extract district name from route parameters or query string
        district_name = kwargs.get("district_name") or request.args.get("district_name")

        if not district_name:
            return jsonify({"error": "District name required"}), 400

        # Check if district-scoped user has access
        if not current_user.can_view_district(district_name):
            return jsonify({"error": "Access denied to this district"}), 403

        return func(*args, **kwargs)

    return wrapper


def security_level_required(required_level):
    """
    Decorator to require minimum security level.

    Args:
        required_level: SecurityLevel enum value (USER, SUPERVISOR, MANAGER, ADMIN)

    Usage:
        @security_level_required(SecurityLevel.MANAGER)
        def manager_only_route():
            # Only managers and admins can access
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.has_permission_level(required_level):
                return (
                    jsonify(
                        {
                            "error": "Insufficient permissions",
                            "required_level": required_level.name,
                            "user_level": current_user.security_level,
                        }
                    ),
                    403,
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def school_scoped_required(func):
    """
    Decorator to check if user can access the requested school.
    Future implementation for school-level scoping.

    Usage:
        @school_scoped_required
        def school_report(school_id):
            # User already validated for school access
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Global users have access to everything
        if current_user.scope_type == "global":
            return func(*args, **kwargs)

        # Extract school ID from route parameters or query string
        school_id = kwargs.get("school_id") or request.args.get("school_id")

        if not school_id:
            return jsonify({"error": "School ID required"}), 400

        # Check if school-scoped user has access
        if not current_user.can_view_school(school_id):
            return jsonify({"error": "Access denied to this school"}), 403

        return func(*args, **kwargs)

    return wrapper
