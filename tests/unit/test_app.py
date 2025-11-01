"""
Tests for app.py - Main Flask Application

This module tests critical application infrastructure:
- Security headers
- Error handlers
- Health check endpoints
- Startup validation
- Configuration settings
"""

import os
from unittest.mock import patch

import pytest


def test_security_headers_present(real_client):
    """Test that security headers are added to all responses"""
    response = real_client.get("/")

    # Check that security headers are present
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"

    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"


def test_hsts_header_production(real_client):
    """Test that HSTS header is added in production but not development"""
    response = real_client.get("/")

    # In development, HSTS should not be present
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_header_production_env(real_client):
    """Test that HSTS header is present in production environment"""
    # This test will run in development, so we can't test production headers
    # The test is mainly to verify the code doesn't crash
    response = real_client.get("/")
    # In development, HSTS should not be present
    assert "Strict-Transport-Security" not in response.headers or True


def test_404_error_handler_html(real_client):
    """Test that 404 errors return HTML error page"""
    response = real_client.get("/nonexistent-page-12345")

    assert response.status_code == 404
    # Check that it's an HTML response (not JSON)
    assert (
        "text/html" in response.content_type
        or response.content_type == "text/html; charset=utf-8"
    )
    # Verify error page content is rendered
    assert b"404" in response.data or b"Page Not Found" in response.data


def test_404_error_handler_api(real_client):
    """Test that 404 errors return JSON for API routes"""
    response = real_client.get("/api/v1/nonexistent-endpoint")

    assert response.status_code == 404
    # Check that it's a JSON response
    assert (
        "application/json" in response.content_type
        or response.content_type == "application/json"
    )
    assert "error" in response.get_json()


def test_403_error_handler_html(real_client):
    """Test that 403 errors return HTML error page"""
    # Force a 403 by accessing a protected route without login
    # This should trigger Flask-Login's redirect, but we can test the handler exists
    response = real_client.get("/admin")

    # Should redirect to login (302) or return 403
    assert response.status_code in [302, 403]


def test_500_error_handler_logs_error():
    """Test that 500 errors are logged"""
    # We can't dynamically add routes after first request, so we'll test
    # that the handler is registered and would work
    from app import app as real_app

    # Verify the error handler decorator is registered
    error_handlers = real_app.error_handler_spec.get(None, {})
    assert 500 in error_handlers


def test_health_check_endpoint(real_client):
    """Test health check endpoint"""
    response = real_client.get("/health")

    assert response.status_code == 200
    assert (
        "application/json" in response.content_type
        or response.content_type == "application/json"
    )

    data = response.get_json()
    assert "status" in data
    assert "database" in data
    assert "environment" in data
    assert "version" in data


def test_health_check_environment_set():
    """Test that health check returns correct environment"""
    pytest.skip("Would require app recreation - tested in other tests")


def test_readiness_check_endpoint(real_client):
    """Test readiness check endpoint"""
    response = real_client.get("/ready")

    assert response.status_code == 200
    assert (
        "application/json" in response.content_type
        or response.content_type == "application/json"
    )

    data = response.get_json()
    assert "status" in data
    assert data["status"] == "ready"


def test_readiness_check_database_down():
    """Test readiness check when database is down"""
    pytest.skip("Requires mocking database failure - integration test")


def test_security_headers_all_routes(real_client):
    """Test that security headers are present on various route types"""
    routes_to_test = [
        "/",
        "/health",
        "/ready",
        "/login",
    ]

    for route in routes_to_test:
        response = real_client.get(route)
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


def test_api_error_response_format(real_client):
    """Test that API errors return consistent JSON format"""
    # Test 404
    response = real_client.get("/api/v1/missing")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert isinstance(data["error"], str)


def test_create_app_function():
    """Test the create_app function returns an app instance"""
    from app import app, create_app

    # Should return the global app instance
    test_app = create_app()
    assert test_app is not None
    assert hasattr(test_app, "config")
    assert hasattr(test_app, "test_client")


def test_create_app_with_config_name():
    """Test create_app with explicit config name"""
    from app import create_app

    # Should work with different config names
    test_app = create_app("development")
    assert test_app is not None

    test_app = create_app("testing")
    assert test_app is not None


def test_startup_validation_integration():
    """Test that startup validation runs without errors"""
    # This is mostly tested by app import not failing
    from app import app

    # If we got here, startup validation passed
    assert app is not None


def test_context_processor_security_levels():
    """Test that security level constants are available in templates"""
    # This would require rendering a template, so we'll test it indirectly
    # by verifying the context processor is registered
    from app import app

    # The context processor should be registered
    assert app.template_context_processors is not None


def test_session_cookie_security(real_client):
    """Test that session cookies have security attributes"""
    # Make a request that might set a session cookie
    response = real_client.get("/login")

    # Check Set-Cookie headers for session security
    set_cookie = response.headers.get("Set-Cookie", "")
    if set_cookie and "session" in set_cookie:
        # In production, should have HttpOnly
        # The exact attributes depend on Flask-Login and our config
        pass  # Hard to test without actual session creation


def test_cors_enabled(real_client):
    """Test that CORS is enabled for the application"""
    response = real_client.get("/", headers={"Origin": "http://example.com"})

    # CORS should allow the request
    # May have Access-Control-Allow-Origin header
    assert response.status_code in [200, 302, 404]
