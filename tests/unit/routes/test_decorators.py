"""
Unit tests for routes/decorators.py security decorators.
"""

import json

import pytest
from flask import Flask, jsonify

from models.user import SecurityLevel, User
from routes.decorators import (
    district_scoped_required,
    global_users_only,
    school_scoped_required,
    security_level_required,
)


@pytest.fixture
def mock_global_user():
    """Create a mock global user."""
    user = User(
        username="global_user",
        email="global@test.com",
        password_hash="dummy",
        scope_type="global",
        security_level=SecurityLevel.ADMIN,
    )
    return user


@pytest.fixture
def mock_district_user():
    """Create a mock district-scoped user."""
    user = User(
        username="district_user",
        email="district@test.com",
        password_hash="dummy",
        scope_type="district",
        allowed_districts='["Test District"]',
        security_level=SecurityLevel.USER,
    )
    return user


@pytest.fixture
def mock_route_func():
    """Create a mock route function for testing."""

    def route_func(*args, **kwargs):
        return jsonify({"success": True, "args": args, "kwargs": kwargs}), 200

    return route_func


class TestDistrictScopedRequired:
    """Test district_scoped_required decorator."""

    def test_global_user_allows(self, app, mock_global_user, mock_route_func):
        """Test that global users bypass checks."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_global_user)

            decorated_func = district_scoped_required(mock_route_func)
            response, status = decorated_func(district_name="Any District")
            assert status == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_district_user_with_access(self, app, mock_district_user, mock_route_func):
        """Test district-scoped user with allowed district."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = district_scoped_required(mock_route_func)
            response, status = decorated_func(district_name="Test District")
            assert status == 200
            data = json.loads(response.data)
            assert data["success"] is True

    def test_district_user_denied(self, app, mock_district_user, mock_route_func):
        """Test district-scoped user denied access to other district."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = district_scoped_required(mock_route_func)
            response, status = decorated_func(district_name="Other District")
            assert status == 403
            data = json.loads(response.data)
            assert "error" in data
            assert "denied" in data["error"].lower()

    def test_missing_district_name_returns_400(
        self, app, mock_district_user, mock_route_func
    ):
        """Test that missing district_name returns 400."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = district_scoped_required(mock_route_func)
            response, status = decorated_func()
            assert status == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "required" in data["error"].lower()

    def test_district_name_from_query_string(
        self, app, mock_district_user, mock_route_func
    ):
        """Test that district_name can come from query string."""
        with app.app_context():
            from unittest.mock import patch

            from flask import request
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = district_scoped_required(mock_route_func)

            # Mock request.args
            with patch.object(request, "args", {"district_name": "Test District"}):
                response, status = decorated_func()
                assert status == 200


class TestSecurityLevelRequired:
    """Test security_level_required decorator."""

    def test_user_exact_level_allows(self, app, mock_global_user, mock_route_func):
        """Test user at exact required level is allowed."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_global_user)

            decorated_func = security_level_required(SecurityLevel.ADMIN)(
                mock_route_func
            )
            response, status = decorated_func()
            assert status == 200

    def test_user_above_level_allows(self, app, mock_global_user, mock_route_func):
        """Test user above required level is allowed."""
        with app.app_context():
            from flask_login import login_user

            # Make user MANAGER, require USER
            mock_global_user.security_level = SecurityLevel.MANAGER
            login_user(mock_global_user)

            decorated_func = security_level_required(SecurityLevel.USER)(
                mock_route_func
            )
            response, status = decorated_func()
            assert status == 200

    def test_user_below_level_denied(self, app, mock_district_user, mock_route_func):
        """Test user below required level is denied with structured payload."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = security_level_required(SecurityLevel.MANAGER)(
                mock_route_func
            )
            response, status = decorated_func()
            assert status == 403
            data = json.loads(response.data)
            assert "error" in data
            assert "required_level" in data
            assert "user_level" in data
            assert data["required_level"] == SecurityLevel.MANAGER.name


class TestSchoolScopedRequired:
    """Test school_scoped_required decorator."""

    def test_global_user_allows(self, app, mock_global_user, mock_route_func):
        """Test that global users bypass school checks."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_global_user)

            decorated_func = school_scoped_required(mock_route_func)
            response, status = decorated_func(school_id="123")
            assert status == 200

    def test_missing_school_id_returns_400(
        self, app, mock_district_user, mock_route_func
    ):
        """Test that missing school_id returns 400."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = school_scoped_required(mock_route_func)
            response, status = decorated_func()
            assert status == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "required" in data["error"].lower()

    def test_school_scoped_user_denied(self, app, mock_district_user, mock_route_func):
        """Test school-scoped user denied when can_view_school returns False."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)
            # Mock can_view_school to return False
            mock_district_user.can_view_school = lambda x: False

            decorated_func = school_scoped_required(mock_route_func)
            response, status = decorated_func(school_id="123")
            assert status == 403
            data = json.loads(response.data)
            assert "error" in data
            assert "denied" in data["error"].lower()


class TestGlobalUsersOnly:
    """Test global_users_only decorator."""

    def test_global_user_allowed(self, app, mock_global_user, mock_route_func):
        """Test that global users are allowed."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_global_user)

            decorated_func = global_users_only(mock_route_func)
            response, status = decorated_func()
            assert status == 200

    def test_district_user_denied(self, app, mock_district_user, mock_route_func):
        """Test that district-scoped users are denied with proper payload."""
        with app.app_context():
            from flask_login import login_user

            login_user(mock_district_user)

            decorated_func = global_users_only(mock_route_func)
            response, status = decorated_func()
            assert status == 403
            data = json.loads(response.data)
            assert "error" in data
            assert "message" in data
            assert "global users" in data["message"].lower()
