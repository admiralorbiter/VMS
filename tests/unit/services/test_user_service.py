"""
Unit tests for services/user_service.py

Tests cover validation, role escalation checks, user creation and updates.
"""

import pytest
from werkzeug.security import check_password_hash

from models import User, db
from models.user import TenantRole
from services.user_service import (
    MIN_PASSWORD_LENGTH,
    check_role_escalation,
    create_user,
    update_user_fields,
    validate_new_user,
    validate_user_update,
)

# ── validate_new_user ─────────────────────────────────────────────────


class TestValidateNewUser:

    def test_valid_input(self, app):
        with app.app_context():
            errors = validate_new_user("newuser", "new@test.com", "password123")
            assert errors == []

    def test_missing_username(self, app):
        with app.app_context():
            errors = validate_new_user("", "test@test.com", "password123")
            assert any("Username" in e for e in errors)

    def test_whitespace_username(self, app):
        with app.app_context():
            errors = validate_new_user("   ", "test@test.com", "password123")
            assert any("Username" in e for e in errors)

    def test_missing_email(self, app):
        with app.app_context():
            errors = validate_new_user("user", "", "password123")
            assert any("Email" in e for e in errors)

    def test_missing_password(self, app):
        with app.app_context():
            errors = validate_new_user("user", "test@test.com", "")
            assert any("Password" in e for e in errors)

    def test_short_password(self, app):
        with app.app_context():
            short = "x" * (MIN_PASSWORD_LENGTH - 1)
            errors = validate_new_user("user", "test@test.com", short)
            assert any("at least" in e for e in errors)

    def test_password_mismatch(self, app):
        with app.app_context():
            errors = validate_new_user(
                "user", "test@test.com", "password123", "different"
            )
            assert any("match" in e for e in errors)

    def test_password_match(self, app):
        with app.app_context():
            errors = validate_new_user(
                "user", "test@test.com", "password123", "password123"
            )
            assert errors == []

    def test_duplicate_username(self, app, test_admin):
        with app.app_context():
            errors = validate_new_user("admin", "other@test.com", "password123")
            assert any("already exists" in e for e in errors)

    def test_duplicate_email(self, app, test_admin):
        with app.app_context():
            errors = validate_new_user("otheruser", "admin@example.com", "password123")
            assert any("already exists" in e for e in errors)


# ── validate_user_update ──────────────────────────────────────────────


class TestValidateUserUpdate:

    def test_no_changes_is_valid(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            errors = validate_user_update(user)
            assert errors == []

    def test_same_username_is_valid(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            errors = validate_user_update(user, username=user.username)
            assert errors == []

    def test_new_unique_username_is_valid(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            errors = validate_user_update(user, username="brand_new_name")
            assert errors == []

    def test_short_password_rejected(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            errors = validate_user_update(user, password="short")
            assert any("at least" in e for e in errors)

    def test_password_mismatch(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            errors = validate_user_update(
                user, password="newpassword123", confirm_password="different"
            )
            assert any("match" in e for e in errors)


# ── check_role_escalation ─────────────────────────────────────────────


class TestCheckRoleEscalation:

    def test_polaris_admin_can_assign_any_tenant_role(self, app, test_admin):
        with app.app_context():
            admin = db.session.get(User, test_admin.id)
            result = check_role_escalation(admin, "admin", context="tenant")
            assert result is None

    def test_tenant_admin_cannot_assign_admin_role(self, app, test_admin):
        with app.app_context():
            # Simulate a tenant admin (not a global admin)
            admin = db.session.get(User, test_admin.id)
            admin.is_admin = False
            result = check_role_escalation(admin, "admin", context="tenant")
            assert result is not None
            assert "Polaris" in result

    def test_tenant_admin_can_assign_coordinator(self, app, test_admin):
        with app.app_context():
            admin = db.session.get(User, test_admin.id)
            admin.is_admin = False
            result = check_role_escalation(admin, "coordinator", context="tenant")
            assert result is None

    def test_global_admin_can_assign_any_level(self, app, test_admin):
        with app.app_context():
            admin = db.session.get(User, test_admin.id)
            result = check_role_escalation(admin, 100, context="global")
            assert result is None


# ── create_user ──────────────────────────────────────────────────────


class TestCreateUser:

    def test_creates_user_successfully(self, app):
        with app.app_context():
            user, error = create_user(
                username="testcreate",
                email="testcreate@test.com",
                password="securepassword123",
            )
            assert error is None
            assert user is not None
            assert user.username == "testcreate"
            assert user.email == "testcreate@test.com"
            assert check_password_hash(user.password_hash, "securepassword123")

            # Cleanup
            db.session.delete(user)
            db.session.commit()

    def test_password_is_hashed(self, app):
        with app.app_context():
            user, _ = create_user(
                username="hashtest",
                email="hashtest@test.com",
                password="plaintext",
            )
            assert user.password_hash != "plaintext"

            db.session.delete(user)
            db.session.commit()

    def test_extra_fields_applied(self, app):
        with app.app_context():
            user, _ = create_user(
                username="extrafields",
                email="extra@test.com",
                password="securepassword123",
                is_active=False,
                first_name="Test",
                last_name="User",
            )
            assert user.is_active is False
            assert user.first_name == "Test"

            db.session.delete(user)
            db.session.commit()

    def test_whitespace_stripped(self, app):
        with app.app_context():
            user, _ = create_user(
                username="  spacey  ",
                email="  UPPER@TEST.COM  ",
                password="securepassword123",
            )
            assert user.username == "spacey"
            assert user.email == "upper@test.com"

            db.session.delete(user)
            db.session.commit()

    def test_duplicate_username_returns_error(self, app, test_admin):
        """Creating a user with an existing username should return error, not crash."""
        with app.app_context():
            user, error = create_user(
                username="admin",
                email="unique@test.com",
                password="securepassword123",
            )
            assert user is None
            assert error is not None
            assert "Error" in error


# ── update_user_fields ────────────────────────────────────────────────


class TestUpdateUserFields:

    def test_update_email(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            original_email = user.email
            success, error = update_user_fields(user, email="updated@test.com")
            assert success is True
            assert error is None
            assert user.email == "updated@test.com"

            # Restore
            user.email = original_email
            db.session.commit()

    def test_update_password(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            original_hash = user.password_hash
            success, _ = update_user_fields(user, password="newpassword123")
            assert success is True
            assert check_password_hash(user.password_hash, "newpassword123")

            # Restore
            user.password_hash = original_hash
            db.session.commit()

    def test_skip_none_email(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            original_email = user.email
            success, _ = update_user_fields(user, email=None)
            assert success is True
            assert user.email == original_email

    def test_skip_empty_password(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            original_hash = user.password_hash
            success, _ = update_user_fields(user, password="")
            assert success is True
            assert user.password_hash == original_hash

    def test_extra_fields_applied(self, app, test_admin):
        with app.app_context():
            user = db.session.get(User, test_admin.id)
            original_first = user.first_name
            success, _ = update_user_fields(user, first_name="Updated")
            assert success is True
            assert user.first_name == "Updated"

            # Restore
            user.first_name = original_first
            db.session.commit()
