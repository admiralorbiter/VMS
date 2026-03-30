"""
District Tenant User Management Routes
======================================

Routes for tenant administrators to manage users within their own tenant.

Requirements:
- FR-TENANT-109: Tenant administrators can create/edit/deactivate users
- FR-TENANT-110: Tenant role hierarchy
"""

from flask import flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import TenantRole, User, db
from routes.decorators import require_tenant_admin
from routes.district import district_bp
from services.user_service import check_role_escalation
from services.user_service import create_user as service_create_user
from services.user_service import (
    update_user_fields,
    validate_new_user,
    validate_user_update,
)


@district_bp.route("/settings/users")
@login_required
@require_tenant_admin
def user_list():
    """List users in the current tenant (FR-TENANT-109)."""
    tenant = g.tenant
    users = User.query.filter_by(tenant_id=tenant.id).order_by(User.username).all()

    return render_template(
        "district/settings/user_list.html",
        tenant=tenant,
        users=users,
        page_title=f"Users - {tenant.name}",
    )


@district_bp.route("/settings/users/new", methods=["GET"])
@login_required
@require_tenant_admin
def create_user_form():
    """Show form to create a new tenant user (FR-TENANT-109)."""
    return render_template(
        "district/settings/user_form.html",
        tenant=g.tenant,
        user=None,
        roles=TenantRole.CHOICES,
        page_title="Add User",
    )


@district_bp.route("/settings/users", methods=["POST"])
@login_required
@require_tenant_admin
def create_user():
    """Create a new user in the current tenant (FR-TENANT-109)."""
    tenant = g.tenant

    # Get form data
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    tenant_role = request.form.get("tenant_role", TenantRole.USER)
    is_active = "is_active" in request.form

    # Validation (via service)
    errors = validate_new_user(username, email, password, confirm_password)

    # Role validation
    if tenant_role not in TenantRole.CHOICES:
        errors.append("Invalid role selected.")

    # Privilege escalation guard
    escalation_error = check_role_escalation(
        current_user, tenant_role, context="tenant"
    )
    if escalation_error:
        errors.append(escalation_error)

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "district/settings/user_form.html",
            tenant=tenant,
            user=None,
            roles=TenantRole.CHOICES,
            page_title="Add User",
        )

    # Create user (via service)
    user, error = service_create_user(
        username=username,
        email=email,
        password=password,
        tenant_id=tenant.id,
        tenant_role=tenant_role,
        is_active=is_active,
    )

    if error:
        flash(error, "error")
        return redirect(url_for("district.user_list"))

    flash(f"User '{username}' created successfully.", "success")
    return redirect(url_for("district.user_list"))


@district_bp.route("/settings/users/<int:user_id>/edit", methods=["GET"])
@login_required
@require_tenant_admin
def edit_user_form(user_id):
    """Show form to edit a tenant user."""
    tenant = g.tenant
    user = User.query.filter_by(id=user_id, tenant_id=tenant.id).first_or_404()

    return render_template(
        "district/settings/user_form.html",
        tenant=tenant,
        user=user,
        roles=TenantRole.CHOICES,
        page_title=f"Edit User: {user.username}",
    )


@district_bp.route("/settings/users/<int:user_id>", methods=["POST"])
@login_required
@require_tenant_admin
def update_user(user_id):
    """Update a tenant user."""
    tenant = g.tenant
    user = User.query.filter_by(id=user_id, tenant_id=tenant.id).first_or_404()

    # Get form data
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    tenant_role = request.form.get("tenant_role", user.tenant_role)
    is_active = "is_active" in request.form

    # Validation (via service)
    errors = validate_user_update(user, username, email, password, confirm_password)

    # Role validation
    if tenant_role not in TenantRole.CHOICES:
        errors.append("Invalid role selected.")

    # Privilege escalation guard
    escalation_error = check_role_escalation(
        current_user, tenant_role, context="tenant"
    )
    if escalation_error:
        errors.append(escalation_error)

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template(
            "district/settings/user_form.html",
            tenant=tenant,
            user=user,
            roles=TenantRole.CHOICES,
            page_title=f"Edit User: {user.username}",
        )

    # Update user (via service)
    success, error = update_user_fields(
        user,
        username=username,
        email=email,
        password=password if password else None,
        tenant_role=tenant_role,
        is_active=is_active,
    )

    if error:
        flash(error, "error")
    else:
        flash(f"User '{username}' updated successfully.", "success")
    return redirect(url_for("district.user_list"))


@district_bp.route("/settings/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@require_tenant_admin
def toggle_user_active(user_id):
    """Toggle user active status."""
    tenant = g.tenant
    user = User.query.filter_by(id=user_id, tenant_id=tenant.id).first_or_404()

    # Prevent deactivating yourself
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("district.user_list"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for("district.user_list"))
