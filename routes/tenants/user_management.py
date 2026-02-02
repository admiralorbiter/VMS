"""
Tenant User Management Routes
============================

Provides routes for managing users within tenants, accessible by:
- Polaris administrators (for any tenant)
- Tenant administrators (for their own tenant)

Requirements:
- FR-TENANT-108: Polaris admin creates tenant users
- FR-TENANT-109: Tenant admin manages users
- FR-TENANT-110: Tenant role hierarchy
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.security import generate_password_hash

from models import Tenant, TenantRole, User, db
from routes.tenants.routes import admin_required

tenant_users_bp = Blueprint("tenant_users", __name__, url_prefix="/management/tenants")


@tenant_users_bp.route("/<int:tenant_id>/users/new", methods=["GET"])
@login_required
@admin_required
def create_user_form(tenant_id):
    """Show form to create a new user for a tenant (FR-TENANT-108)."""
    tenant = Tenant.query.get_or_404(tenant_id)

    return render_template(
        "management/tenants/user_form.html",
        tenant=tenant,
        user=None,
        roles=TenantRole.CHOICES,
        page_title=f"Add User to {tenant.name}",
    )


@tenant_users_bp.route("/<int:tenant_id>/users", methods=["POST"])
@login_required
@admin_required
def create_user(tenant_id):
    """Create a new user assigned to a tenant (FR-TENANT-108)."""
    tenant = Tenant.query.get_or_404(tenant_id)

    # Get form data
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    tenant_role = request.form.get("tenant_role", TenantRole.USER)
    is_active = "is_active" in request.form

    # Validation
    errors = []

    if not username:
        errors.append("Username is required.")
    elif User.query.filter_by(username=username).first():
        errors.append("Username already exists.")

    if not email:
        errors.append("Email is required.")
    elif User.query.filter_by(email=email).first():
        errors.append("Email already exists.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != confirm_password:
        errors.append("Passwords do not match.")

    if tenant_role not in TenantRole.CHOICES:
        errors.append("Invalid role selected.")

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "management/tenants/user_form.html",
            tenant=tenant,
            user=None,
            roles=TenantRole.CHOICES,
            page_title=f"Add User to {tenant.name}",
        )

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        tenant_id=tenant_id,
        tenant_role=tenant_role,
        is_active=is_active,
    )

    db.session.add(user)
    db.session.commit()

    flash(f"User '{username}' created successfully for {tenant.name}.", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant_id))


@tenant_users_bp.route("/<int:tenant_id>/users/<int:user_id>/edit", methods=["GET"])
@login_required
@admin_required
def edit_user_form(tenant_id, user_id):
    """Show form to edit an existing tenant user."""
    tenant = Tenant.query.get_or_404(tenant_id)
    user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first_or_404()

    return render_template(
        "management/tenants/user_form.html",
        tenant=tenant,
        user=user,
        roles=TenantRole.CHOICES,
        page_title=f"Edit User: {user.username}",
    )


@tenant_users_bp.route("/<int:tenant_id>/users/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def update_user(tenant_id, user_id):
    """Update an existing tenant user."""
    tenant = Tenant.query.get_or_404(tenant_id)
    user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first_or_404()

    # Get form data
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    tenant_role = request.form.get("tenant_role", user.tenant_role)
    is_active = "is_active" in request.form

    # Validation
    errors = []

    if not username:
        errors.append("Username is required.")
    elif username != user.username and User.query.filter_by(username=username).first():
        errors.append("Username already exists.")

    if not email:
        errors.append("Email is required.")
    elif email != user.email and User.query.filter_by(email=email).first():
        errors.append("Email already exists.")

    if password:  # Only validate if changing password
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

    if tenant_role not in TenantRole.CHOICES:
        errors.append("Invalid role selected.")

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "management/tenants/user_form.html",
            tenant=tenant,
            user=user,
            roles=TenantRole.CHOICES,
            page_title=f"Edit User: {user.username}",
        )

    # Update user
    user.username = username
    user.email = email
    user.tenant_role = tenant_role
    user.is_active = is_active

    if password:  # Only update password if provided
        user.password_hash = generate_password_hash(password)

    db.session.commit()

    flash(f"User '{username}' updated successfully.", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant_id))


@tenant_users_bp.route("/<int:tenant_id>/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(tenant_id, user_id):
    """Toggle user active status (soft activate/deactivate)."""
    tenant = Tenant.query.get_or_404(tenant_id)
    user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first_or_404()

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for("tenants.view_tenant", tenant_id=tenant_id))
