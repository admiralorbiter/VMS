"""
Tenant Management Routes Module
==============================

This module provides administrative routes for managing district tenants
in the District Suite multi-tenant system.

Key Features:
- Tenant CRUD operations (create, read, update, deactivate)
- API key management (generate, rotate, revoke)
- Tenant user management
- Feature flag configuration

Access Control:
- All routes require admin authentication
- Only PrepKC admins (not tenant-scoped) can access these routes

Endpoints:
- GET  /management/tenants - List all tenants
- GET  /management/tenants/new - New tenant form
- POST /management/tenants - Create tenant
- GET  /management/tenants/<id> - View tenant details
- GET  /management/tenants/<id>/edit - Edit tenant form
- POST /management/tenants/<id> - Update tenant
- POST /management/tenants/<id>/toggle-active - Toggle active status
- POST /management/tenants/<id>/api-key - Generate/rotate API key
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Tenant, User, db

# Create blueprint
tenants_bp = Blueprint("tenants", __name__, url_prefix="/management/tenants")


def admin_required(f):
    """Decorator to require admin access and non-tenant scope."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("index"))
        if current_user.tenant_id is not None:
            flash("Tenant management requires PrepKC admin access.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def validate_slug(slug):
    """
    Validate tenant slug format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not slug:
        return False, "Slug is required"
    if len(slug) > 50:
        return False, "Slug must be 50 characters or less"
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug):
        return False, "Slug must be lowercase alphanumeric with optional hyphens"

    # Check reserved slugs (from district_portal.py)
    reserved = {
        "usage",
        "events",
        "event",
        "virtual",
        "purge",
        "import-sheet",
        "google-sheets",
    }
    if slug in reserved:
        return False, f"'{slug}' is a reserved name"

    return True, None


@tenants_bp.route("")
@login_required
@admin_required
def list_tenants():
    """List all tenants."""
    tenants = Tenant.query.order_by(Tenant.name).all()
    return render_template(
        "management/tenants/list.html", tenants=tenants, page_title="Tenant Management"
    )


@tenants_bp.route("/new", methods=["GET"])
@login_required
@admin_required
def new_tenant():
    """Show new tenant form."""
    from models.district_model import District

    districts = District.query.order_by(District.name).all()
    return render_template(
        "management/tenants/form.html",
        tenant=None,
        districts=districts,
        page_title="Create Tenant",
    )


@tenants_bp.route("", methods=["POST"])
@login_required
@admin_required
def create_tenant():
    """Create a new tenant."""
    slug = request.form.get("slug", "").strip().lower()
    name = request.form.get("name", "").strip()
    district_id = request.form.get("district_id", "").strip()

    # Validate slug
    is_valid, error = validate_slug(slug)
    if not is_valid:
        flash(error, "error")
        return redirect(url_for("tenants.new_tenant"))

    # Check uniqueness
    existing = Tenant.query.filter_by(slug=slug).first()
    if existing:
        flash(f"Tenant with slug '{slug}' already exists", "error")
        return redirect(url_for("tenants.new_tenant"))

    # Validate name
    if not name:
        flash("Name is required", "error")
        return redirect(url_for("tenants.new_tenant"))

    # Create tenant with proper District FK
    tenant = Tenant(
        slug=slug,
        name=name,
        district_id=int(district_id) if district_id else None,
        created_by=current_user.id,
    )

    # Set initial feature flags from form
    features = {
        "events_enabled": "events_enabled" in request.form,
        "volunteers_enabled": "volunteers_enabled" in request.form,
        "recruitment_enabled": "recruitment_enabled" in request.form,
        "prepkc_visibility_enabled": "prepkc_visibility_enabled" in request.form,
    }
    tenant.set_setting("features", value=features)

    db.session.add(tenant)
    db.session.commit()

    flash(f"Tenant '{name}' created successfully", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant.id))


@tenants_bp.route("/<int:tenant_id>")
@login_required
@admin_required
def view_tenant(tenant_id):
    """View tenant details."""
    tenant = Tenant.query.get_or_404(tenant_id)
    users = User.query.filter_by(tenant_id=tenant_id).order_by(User.username).all()

    return render_template(
        "management/tenants/detail.html",
        tenant=tenant,
        users=users,
        page_title=f"Tenant: {tenant.name}",
    )


@tenants_bp.route("/<int:tenant_id>/edit", methods=["GET"])
@login_required
@admin_required
def edit_tenant(tenant_id):
    """Show edit tenant form."""
    from models.district_model import District

    tenant = Tenant.query.get_or_404(tenant_id)
    districts = District.query.order_by(District.name).all()

    return render_template(
        "management/tenants/form.html",
        tenant=tenant,
        districts=districts,
        page_title=f"Edit Tenant: {tenant.name}",
    )


@tenants_bp.route("/<int:tenant_id>", methods=["POST"])
@login_required
@admin_required
def update_tenant(tenant_id):
    """Update tenant settings."""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Update basic fields
    tenant.name = request.form.get("name", "").strip() or tenant.name

    # Update district FK
    district_id = request.form.get("district_id", "").strip()
    tenant.district_id = int(district_id) if district_id else None

    # Update allowed origins
    origins = request.form.get("allowed_origins", "").strip()
    tenant.allowed_origins = origins if origins else None

    # Update feature flags
    features = {
        "events_enabled": "events_enabled" in request.form,
        "volunteers_enabled": "volunteers_enabled" in request.form,
        "recruitment_enabled": "recruitment_enabled" in request.form,
        "prepkc_visibility_enabled": "prepkc_visibility_enabled" in request.form,
    }
    tenant.set_setting("features", value=features)

    # Update portal settings
    portal = {
        "welcome_message": request.form.get("welcome_message", "").strip(),
        "teacher_login_label": request.form.get("teacher_login_label", "").strip()
        or "Teacher Login",
        "staff_login_label": request.form.get("staff_login_label", "").strip()
        or "District Staff Login",
    }
    tenant.set_setting("portal", value=portal)

    tenant.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    flash(f"Tenant '{tenant.name}' updated successfully", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant.id))


@tenants_bp.route("/<int:tenant_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(tenant_id):
    """Toggle tenant active status."""
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.is_active = not tenant.is_active
    tenant.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    status = "activated" if tenant.is_active else "deactivated"
    flash(f"Tenant '{tenant.name}' {status}", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant.id))


@tenants_bp.route("/<int:tenant_id>/api-key", methods=["POST"])
@login_required
@admin_required
def generate_api_key(tenant_id):
    """Generate or rotate API key."""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Generate new key
    plain_key = tenant.generate_api_key()
    db.session.commit()

    # Flash the key (shown only once)
    flash(
        f"New API key generated. Copy it now - it won't be shown again: {plain_key}",
        "warning",
    )
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant.id))


@tenants_bp.route("/<int:tenant_id>/revoke-api-key", methods=["POST"])
@login_required
@admin_required
def revoke_api_key(tenant_id):
    """Revoke API key."""
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.revoke_api_key()
    db.session.commit()

    flash(f"API key for '{tenant.name}' has been revoked", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant.id))


# FR-TENANT-105: Cross-Tenant Access
@tenants_bp.route("/switch/<int:tenant_id>", methods=["POST"])
@login_required
@admin_required
def switch_tenant_context(tenant_id):
    """
    Switch admin's active tenant context.

    This allows PrepKC admins to view the system as if they were
    logged in as a user of a specific tenant.

    Args:
        tenant_id: ID of tenant to switch to (0 to clear)

    Returns:
        Redirect to tenant view or tenant list
    """

    from utils.tenant_context import (
        clear_admin_tenant_override,
        set_admin_tenant_override,
    )

    # Clear context if tenant_id is 0
    if tenant_id == 0:
        clear_admin_tenant_override()
        flash("Returned to PrepKC admin view", "info")
        return redirect(url_for("tenants.list_tenants"))

    # Get the tenant
    tenant = Tenant.query.get_or_404(tenant_id)

    # Cannot switch to inactive tenant
    if not tenant.is_active:
        flash(f"Cannot switch to inactive tenant: {tenant.name}", "warning")
        return redirect(url_for("tenants.view_tenant", tenant_id=tenant_id))

    # Set the override
    set_admin_tenant_override(tenant_id)

    flash(f"Now viewing as: {tenant.name}", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant_id))
