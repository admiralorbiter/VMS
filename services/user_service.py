"""
User Service
=============

Shared validation, creation, and update logic for user accounts.

Consolidated from (TD-043):
  - routes/auth/routes.py         (global admin user creation)
  - routes/district/tenant_users.py  (tenant admin self-service)
  - routes/tenants/user_management.py (Polaris admin managing any tenant)
  - routes/management/routes.py      (supervisor/admin user editing)

Route handlers remain responsible for:
  - Permission checks and decorators
  - Tenant scoping (g.tenant, current_user.tenant_id)
  - Role assignment (SecurityLevel vs TenantRole)
  - Response format (HTML template vs JSON)
  - Redirect targets

Usage:
    from services.user_service import (
        validate_new_user,
        validate_user_update,
        check_role_escalation,
        create_user,
        update_user_fields,
    )
"""

import logging

from werkzeug.security import generate_password_hash

from models import User, db

logger = logging.getLogger(__name__)

# Minimum password length (standardized across all contexts)
MIN_PASSWORD_LENGTH = 8


def validate_new_user(username, email, password, confirm_password=None):
    """
    Validate data for creating a new user. Context-agnostic.

    Args:
        username: Desired username (will be checked for uniqueness)
        email: Desired email (will be checked for uniqueness)
        password: Password (must be >= MIN_PASSWORD_LENGTH)
        confirm_password: Optional confirmation (must match if provided)

    Returns:
        list[str]: Validation error messages (empty if valid)
    """
    errors = []

    # Username
    if not username or not username.strip():
        errors.append("Username is required.")
    elif User.query.filter_by(username=username.strip()).first():
        errors.append("Username already exists.")

    # Email
    if not email or not email.strip():
        errors.append("Email is required.")
    elif User.query.filter_by(email=email.strip().lower()).first():
        errors.append("Email already exists.")

    # Password
    if not password:
        errors.append("Password is required.")
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    elif confirm_password is not None and password != confirm_password:
        errors.append("Passwords do not match.")

    return errors


def validate_user_update(
    user, username=None, email=None, password=None, confirm_password=None
):
    """
    Validate data for updating an existing user. Skips unchanged fields.

    Args:
        user: Existing User instance being updated
        username: New username (None to skip)
        email: New email (None to skip)
        password: New password (None/empty to skip)
        confirm_password: Confirmation (must match if password provided)

    Returns:
        list[str]: Validation error messages (empty if valid)
    """
    errors = []

    # Username (only validate if changed)
    if username is not None:
        username = username.strip()
        if not username:
            errors.append("Username is required.")
        elif (
            username != user.username
            and User.query.filter_by(username=username).first()
        ):
            errors.append("Username already exists.")

    # Email (only validate if changed)
    if email is not None:
        email = email.strip().lower()
        if not email:
            errors.append("Email is required.")
        elif email != user.email and User.query.filter_by(email=email).first():
            errors.append("Email already exists.")

    # Password (only validate if provided)
    if password:
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )
        elif confirm_password is not None and password != confirm_password:
            errors.append("Passwords do not match.")

    return errors


def check_role_escalation(actor, target_role, context="tenant"):
    """
    Prevent privilege escalation when assigning roles.

    In tenant context:
      - Only Polaris admins (global admin) can assign TenantRole.ADMIN
      - Tenant admins can assign coordinator, virtual_admin, user roles

    In global context:
      - Users cannot assign a security_level >= their own
        (unless they are admin)

    Args:
        actor: The User performing the action
        target_role: The role/level being assigned (str for tenant, int for global)
        context: 'tenant' or 'global'

    Returns:
        str or None: Error message if escalation detected, None if allowed
    """
    if context == "tenant":
        from models import TenantRole

        # Polaris admins can assign any tenant role
        if actor.is_admin:
            return None

        # Tenant admins cannot create other tenant admins
        if target_role == TenantRole.ADMIN or target_role == "admin":
            return (
                "Only Polaris administrators can assign the Tenant Admin role. "
                "You can assign Coordinator, Virtual Admin, or User roles."
            )

        return None

    elif context == "global":
        # Admins can assign any level
        if actor.is_admin:
            return None

        target_level = int(target_role)
        if target_level >= actor.security_level:
            return "Cannot assign a security level equal to or higher than your own."

        return None

    return None


def create_user(*, username, email, password, **extra_fields):
    """
    Create a new User, hash password, persist to DB.

    Args:
        username: Username (required)
        email: Email address (required)
        password: Plain-text password (will be hashed)
        **extra_fields: Additional User fields (tenant_id, tenant_role,
                        security_level, scope_type, allowed_districts,
                        is_active, etc.)

    Returns:
        tuple: (User instance, None) on success, (None, error_message) on failure
    """
    try:
        user = User(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=generate_password_hash(password),
            **extra_fields,
        )
        db.session.add(user)
        db.session.commit()
        logger.info("User created: %s (id=%s)", user.username, user.id)
        return user, None

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create user %s: %s", username, e)
        return None, f"Error creating user: {str(e)}"


def update_user_fields(user, *, email=None, password=None, **extra_fields):
    """
    Update user fields. Hash password if provided.

    Args:
        user: Existing User instance to update
        email: New email (None to skip)
        password: New plain-text password (None/empty to skip)
        **extra_fields: Additional fields to update (username, tenant_role,
                        security_level, tenant_id, is_active, etc.)

    Returns:
        tuple: (True, None) on success, (False, error_message) on failure
    """
    try:
        if email is not None:
            user.email = email.strip().lower()

        if password:
            user.password_hash = generate_password_hash(password)

        # Apply any additional fields
        for field, value in extra_fields.items():
            if hasattr(user, field):
                setattr(user, field, value)

        db.session.commit()
        logger.info("User updated: %s (id=%s)", user.username, user.id)
        return True, None

    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to update user %s: %s", user.username, e)
        return False, f"Error updating user: {str(e)}"
