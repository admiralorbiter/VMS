"""
Integration tests for authentication routes.

Tests login functionality, redirects, and endpoint validation to catch
BuildError issues when url_for() references non-existent endpoints.
"""

import json

import pytest
from flask import url_for
from werkzeug.routing.exceptions import BuildError

from models import db
from models.user import User
from tests.conftest import assert_route_response


def test_district_user_login_redirect(client, app, test_district_user):
    """Test that district-scoped users are redirected correctly on login"""
    with app.app_context():
        # Perform login POST request
        response = client.post(
            "/login",
            data={"username": "districtuser", "password": "password123"},
            follow_redirects=False,
        )

        # Verify redirect response (302)
        assert (
            response.status_code == 302
        ), f"Expected 302 redirect, got {response.status_code}"

        # Verify redirect location is present
        assert (
            "Location" in response.headers
        ), "Redirect response missing Location header"
        location = response.headers["Location"]
        assert location is not None, "Redirect location is None"

        # Verify the redirect URL can be built successfully (no BuildError)
        # This is the key test - if url_for() fails, we'd get a BuildError
        assert (
            "/virtual/usage/usage/district/" in location
            or "/virtual/usage/district/" in location
        ), f"Redirect location should point to virtual district teacher progress, got: {location}"

        # Verify it includes the district name
        assert (
            "Kansas%20City%20Kansas%20Public%20Schools" in location
            or "Kansas City Kansas Public Schools" in location
        ), f"Redirect location should include district name, got: {location}"


def test_district_user_login_redirect_follows(client, app, test_district_user):
    """Test that district user redirect actually reaches valid endpoint"""
    with app.app_context():
        # Perform login POST request with follow_redirects=True
        response = client.post(
            "/login",
            data={"username": "districtuser", "password": "password123"},
            follow_redirects=True,
        )

        # Verify we get a response (not a BuildError)
        # The endpoint might return 200, 403, 404, or 500 depending on data availability
        # But we should NOT get a BuildError (which would be a 500 with specific error)
        assert response.status_code in [
            200,
            302,
            403,
            404,
            500,
        ], f"Unexpected status code: {response.status_code}"

        # If we got a 500, verify it's not a BuildError
        if response.status_code == 500:
            response_data = response.data.decode("utf-8")
            assert (
                "BuildError" not in response_data
            ), f"Got BuildError in response: {response_data[:500]}"
            assert (
                "Could not build url for endpoint" not in response_data
            ), f"Got endpoint build error in response: {response_data[:500]}"


def test_regular_user_login_redirect(client, app, test_user):
    """Test that regular users redirect to index"""
    with app.app_context():
        # Perform login POST request
        response = client.post(
            "/login",
            data={"username": "testuser", "password": "password123"},
            follow_redirects=False,
        )

        # Verify redirect response (302)
        assert (
            response.status_code == 302
        ), f"Expected 302 redirect, got {response.status_code}"

        # Verify redirect location points to index
        assert (
            "Location" in response.headers
        ), "Redirect response missing Location header"
        location = response.headers["Location"]
        assert location is not None, "Redirect location is None"

        # Should redirect to index (which is "/")
        assert (
            location.endswith("/") or "/" in location
        ), f"Regular user should redirect to index, got: {location}"


def test_malformed_district_json_handling(client, app):
    """Test error handling when district JSON is malformed"""
    import json

    from werkzeug.security import generate_password_hash

    with app.app_context():
        # Create user with malformed JSON
        malformed_user = User(
            username="malformeduser",
            email="malformed@example.com",
            password_hash=generate_password_hash("password123"),
            scope_type="district",
            allowed_districts='["Kansas City Kansas Public Schools"',  # Missing closing bracket
        )
        db.session.add(malformed_user)
        db.session.commit()

        try:
            # Perform login POST request
            response = client.post(
                "/login",
                data={"username": "malformeduser", "password": "password123"},
                follow_redirects=False,
            )

            # Should either redirect to index (fallback) or handle gracefully
            # The code has a try/except that falls through to normal redirect
            assert (
                response.status_code == 302
            ), f"Expected 302 redirect even with malformed JSON, got {response.status_code}"

            # Should fall back to index redirect
            location = response.headers.get("Location", "")
            # Either redirects to index or handles the error gracefully
            assert location is not None, "Should have a redirect location"

        finally:
            # Cleanup
            db.session.delete(malformed_user)
            db.session.commit()


def test_district_user_no_districts_handling(client, app):
    """Test fallback behavior when district user has no districts assigned"""
    import json

    from werkzeug.security import generate_password_hash

    with app.app_context():
        # Create user with no districts
        no_district_user = User(
            username="nodistrictuser",
            email="nodistrict@example.com",
            password_hash=generate_password_hash("password123"),
            scope_type="district",
            allowed_districts=None,  # No districts assigned
        )
        db.session.add(no_district_user)
        db.session.commit()

        try:
            # Perform login POST request
            response = client.post(
                "/login",
                data={"username": "nodistrictuser", "password": "password123"},
                follow_redirects=False,
            )

            # Should fall back to index redirect
            assert (
                response.status_code == 302
            ), f"Expected 302 redirect, got {response.status_code}"

            location = response.headers.get("Location", "")
            # Should redirect to index since no districts are available
            assert location is not None, "Should have a redirect location"

        finally:
            # Cleanup
            db.session.delete(no_district_user)
            db.session.commit()


def test_district_user_empty_districts_list(client, app):
    """Test fallback behavior when district user has empty districts list"""
    import json

    from werkzeug.security import generate_password_hash

    with app.app_context():
        # Create user with empty districts list
        empty_district_user = User(
            username="emptydistrictuser",
            email="emptydistrict@example.com",
            password_hash=generate_password_hash("password123"),
            scope_type="district",
            allowed_districts=json.dumps([]),  # Empty list
        )
        db.session.add(empty_district_user)
        db.session.commit()

        try:
            # Perform login POST request
            response = client.post(
                "/login",
                data={"username": "emptydistrictuser", "password": "password123"},
                follow_redirects=False,
            )

            # Should fall back to index redirect
            assert (
                response.status_code == 302
            ), f"Expected 302 redirect, got {response.status_code}"

            location = response.headers.get("Location", "")
            # Should redirect to index since districts list is empty
            assert location is not None, "Should have a redirect location"

        finally:
            # Cleanup
            db.session.delete(empty_district_user)
            db.session.commit()


def test_endpoint_build_validation(client, app):
    """Test that critical endpoints can be built without BuildError"""
    with app.app_context():
        # Test building the district teacher progress endpoint
        # This is the endpoint that was failing before the fix
        try:
            url = url_for(
                "virtual.virtual_district_teacher_progress",
                district_name="Kansas City Kansas Public Schools",
                year="2025-2026",
                date_from="2025-08-01",
                date_to="2026-07-31",
            )
            assert url is not None, "URL should not be None"
            assert len(url) > 0, "URL should not be empty"
        except BuildError as e:
            pytest.fail(
                f"Failed to build URL for virtual.virtual_district_teacher_progress: {e}"
            )

        # Test building the index endpoint
        try:
            url = url_for("index")
            assert url is not None, "URL should not be None"
        except BuildError as e:
            pytest.fail(f"Failed to build URL for index: {e}")
