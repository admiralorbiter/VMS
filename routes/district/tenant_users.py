"""
District Tenant User Management Routes
======================================

Routes for tenant administrators to manage users within their own tenant.

Requirements:
- FR-TENANT-109: Tenant administrators can create/edit/deactivate users
- FR-TENANT-110: Tenant role hierarchy (Admin, Coordinator, User)
"""

from functools import wraps

from flask import flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from models import TenantRole, User, db
from routes.district import district_bp


def require_tenant_admin(f):
    """Decorator to require tenant admin access (FR-TENANT-109)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not g.get("tenant"):
            flash("District access required.", "error")
            return redirect(url_for("index"))
        # Check if user is tenant admin within their tenant
        if not current_user.is_tenant_admin:
            flash("You must be a tenant administrator to access this page.", "error")
            return redirect(url_for("district.settings"))
        return f(*args, **kwargs)

    return decorated_function


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
            "district/settings/user_form.html",
            tenant=tenant,
            user=None,
            roles=TenantRole.CHOICES,
            page_title="Add User",
        )

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        tenant_id=tenant.id,
        tenant_role=tenant_role,
        is_active=is_active,
    )

    db.session.add(user)
    db.session.commit()

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

    if password:
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
            "district/settings/user_form.html",
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

    if password:
        user.password_hash = generate_password_hash(password)

    db.session.commit()

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
