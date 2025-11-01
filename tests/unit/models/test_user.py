from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from models.user import SecurityLevel, User


def test_new_user():
    """
    Test creating a new user with basic attributes.
    Verifies that all fields are correctly set during initialization.
    """
    user = User(
        username="newuser",
        email="new@example.com",
        password_hash=generate_password_hash("password123"),
        first_name="New",
        last_name="User",
        is_admin=False,
    )

    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.is_admin is False
    assert user.security_level == SecurityLevel.USER
    # Note: Timestamps use server_default and won't be set until flush/commit
    # For this unit test without a database session, we just verify the attributes exist
    assert hasattr(user, "created_at")
    assert hasattr(user, "updated_at")


def test_user_admin_flag():
    """
    Test admin flag functionality and its effect on security level.
    Verifies both the getter and setter work correctly.
    """
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True,
    )
    assert admin.is_admin is True
    assert admin.security_level == SecurityLevel.ADMIN

    # Test changing admin status
    admin.is_admin = False
    assert admin.is_admin is False
    assert admin.security_level == SecurityLevel.USER


def test_security_levels():
    """Test permission checking between different security levels"""
    admin = User(username="admin", security_level=SecurityLevel.ADMIN)
    manager = User(username="manager", security_level=SecurityLevel.MANAGER)
    supervisor = User(username="super", security_level=SecurityLevel.SUPERVISOR)
    user = User(username="user", security_level=SecurityLevel.USER)

    # Test permission hierarchy
    assert admin.can_manage_user(manager) is True
    assert manager.can_manage_user(admin) is False
    assert manager.can_manage_user(supervisor) is True
    assert supervisor.can_manage_user(user) is True
    assert user.can_manage_user(supervisor) is False


def test_has_permission_level():
    """Test permission level checking"""
    manager = User(username="manager", security_level=SecurityLevel.MANAGER)

    assert manager.has_permission_level(SecurityLevel.USER) is True
    assert manager.has_permission_level(SecurityLevel.SUPERVISOR) is True
    assert manager.has_permission_level(SecurityLevel.MANAGER) is True
    assert manager.has_permission_level(SecurityLevel.ADMIN) is False


def test_find_by_username_or_email():
    """
    Test user lookup by username or email.
    Note: This test requires database integration - mark as integration test
    """
    # This is a placeholder - implement with proper database setup
    pytest.skip("Requires database integration")


def test_string_representations():
    """Test string and repr representations of User model"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        security_level=SecurityLevel.USER,
    )

    assert str(user) == "<User testuser>"
    assert (
        repr(user)
        == "<User(id=1, username='testuser', email='test@example.com', security_level=0)>"
    )
