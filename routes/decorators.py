"""
Security decorators for route access control.

Provides unified permission decorators for the application:
- admin_required: Requires admin privileges (context-aware error responses)
- global_admin_required: Requires admin + non-tenant scope (for tenant management)
- district_scoped_required: District-level access checks
- school_scoped_required: School-level access checks
- security_level_required: Minimum security level enforcement
- global_users_only: Restricts to global-scoped users
"""

from functools import wraps

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user


def _is_json_request():
    """Check if the current request expects a JSON response."""
    if request.is_json:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def admin_required(func):
    """
    Decorator to require admin privileges.

    Auto-detects request context:
    - API/AJAX requests → JSON 403 response
    - Page requests → redirect to login with flash message

    Usage:
        @admin_required
        def admin_only_route():
            # Only admins can access
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False):
            if _is_json_request():
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login"))

        if not getattr(current_user, "is_admin", False):
            if _is_json_request():
                return jsonify({"error": "Unauthorized"}), 403
            flash("Admin access required.", "error")
            return redirect(url_for("index"))

        return func(*args, **kwargs)

    return wrapper


def global_admin_required(func):
    """
    Decorator to require admin privileges AND non-tenant scope.

    Used for tenant management routes where tenant-scoped admins
    should not have access (only PrepKC global admins).

    Usage:
        @global_admin_required
        def manage_tenants():
            # Only global (non-tenant) admins can access
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False):
            if _is_json_request():
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login"))

        if not getattr(current_user, "is_admin", False):
            if _is_json_request():
                return jsonify({"error": "Unauthorized"}), 403
            flash("Admin access required.", "error")
            return redirect(url_for("index"))

        if current_user.tenant_id is not None:
            if _is_json_request():
                return (
                    jsonify(
                        {"error": "Tenant management requires PrepKC admin access"}
                    ),
                    403,
                )
            flash("Tenant management requires PrepKC admin access.", "error")
            return redirect(url_for("index"))

        return func(*args, **kwargs)

    return wrapper


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


def global_users_only(func):
    """
    Decorator to restrict access to global users only.

    Blocks district-scoped and school-scoped users from accessing
    routes that should only be available to global users.

    Usage:
        @global_users_only
        def admin_only_route():
            # Only global users can access
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.scope_type != "global":
            return (
                jsonify(
                    {
                        "error": "Access denied",
                        "message": "This feature is only available to global users",
                    }
                ),
                403,
            )

        return func(*args, **kwargs)

    return wrapper
