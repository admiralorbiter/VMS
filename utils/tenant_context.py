"""
Tenant Context Management

Provides utilities for managing tenant context in multi-tenant requests.

Requirements:
- FR-TENANT-103: Route authenticated users to their tenant's database
- FR-TENANT-105: PrepKC admins can switch tenant context
"""

from typing import Optional

from flask import current_app, g, session
from flask_login import current_user


def get_current_tenant():
    """
    Get the current tenant object for this request.

    Returns:
        Tenant object or None if no tenant context is set
    """
    return getattr(g, "tenant", None)


def get_current_tenant_id() -> Optional[int]:
    """
    Get current tenant ID from admin override or user's tenant.

    Priority:
    1. Admin tenant override (from session)
    2. User's assigned tenant_id

    Returns:
        Tenant ID or None
    """
    # Check if admin has switched context
    if session.get("admin_tenant_override"):
        return session.get("admin_tenant_id")

    # Otherwise use user's tenant
    if current_user.is_authenticated and hasattr(current_user, "tenant_id"):
        return current_user.tenant_id

    return None


def set_tenant_context(tenant) -> None:
    """
    Set tenant context for the current request.

    Args:
        tenant: Tenant model instance or None
    """
    g.tenant = tenant
    g.tenant_id = tenant.id if tenant else None


def clear_tenant_context() -> None:
    """Clear tenant context from current request."""
    g.tenant = None
    g.tenant_id = None


def is_admin_viewing_as_tenant() -> bool:
    """
    Check if current user is an admin viewing as a different tenant.

    Returns:
        True if authenticated admin has switched tenant context
    """
    from flask_login import current_user

    # Must be authenticated and be an admin to show override banner
    if not current_user.is_authenticated:
        return False
    if not current_user.is_admin:
        return False
    return bool(session.get("admin_tenant_override"))


def set_admin_tenant_override(tenant_id: int) -> None:
    """
    Set admin tenant context override.

    Args:
        tenant_id: ID of tenant to view as
    """
    session["admin_tenant_override"] = True
    session["admin_tenant_id"] = tenant_id

    # Log the context switch
    if current_user.is_authenticated:
        current_app.logger.info(
            f"Admin user {current_user.id} ({current_user.username}) "
            f"switched to tenant context: {tenant_id}"
        )


def clear_admin_tenant_override() -> None:
    """Clear admin tenant context override."""
    tenant_id = session.get("admin_tenant_id")

    session.pop("admin_tenant_override", None)
    session.pop("admin_tenant_id", None)

    # Log the context switch
    if current_user.is_authenticated:
        current_app.logger.info(
            f"Admin user {current_user.id} ({current_user.username}) "
            f"cleared tenant context (was: {tenant_id})"
        )


def init_tenant_context() -> None:
    """
    Initialize tenant context for the current request.

    This should be called in a before_request handler.
    Sets g.tenant and g.tenant_id based on:
    1. Admin override (if set)
    2. User's assigned tenant
    """
    from models.tenant import Tenant

    # Clear any existing context
    g.tenant = None
    g.tenant_id = None

    # Get tenant ID from override or user
    tenant_id = get_current_tenant_id()

    if tenant_id:
        tenant = Tenant.query.get(tenant_id)
        if tenant and tenant.is_active:
            set_tenant_context(tenant)
        elif tenant and not tenant.is_active:
            # Tenant is inactive - clear override if it was set
            if is_admin_viewing_as_tenant():
                clear_admin_tenant_override()
                current_app.logger.warning(
                    f"Cleared admin override for inactive tenant: {tenant_id}"
                )


def require_tenant_context(func):
    """
    Decorator to require tenant context for a route.

    Usage:
        @app.route('/tenant-only')
        @require_tenant_context
        def tenant_only_view():
            # g.tenant is guaranteed to be set
            pass
    """
    from functools import wraps

    from flask import abort

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not get_current_tenant():
            abort(403, "This page requires tenant context")
        return func(*args, **kwargs)

    return decorated_function
