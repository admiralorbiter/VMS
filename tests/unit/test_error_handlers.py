"""
Tests for error handling infrastructure.

Tests the 3 infrastructure components:
1. Error hierarchy (utils/errors.py)
2. Error handler middleware (utils/error_handlers.py)
3. Route error decorator (routes/decorators.py - handle_route_errors)
"""

import pytest
from flask import Flask, jsonify

from utils.errors import (
    AppError,
    AuthorizationError,
    DatabaseError,
    ExternalServiceError,
    ImportRecordError,
    NotFoundError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Component 1: Error Hierarchy
# ---------------------------------------------------------------------------
class TestErrorHierarchy:
    """Test that error classes have correct attributes and inheritance."""

    def test_app_error_defaults(self):
        err = AppError()
        assert err.status_code == 500
        assert err.safe_message == "An internal error occurred"
        assert err.detail is None
        assert str(err) == "An internal error occurred"

    def test_app_error_custom_message(self):
        err = AppError("Something went wrong", detail="traceback here")
        assert err.safe_message == "Something went wrong"
        assert err.detail == "traceback here"

    def test_app_error_custom_status_code(self):
        err = AppError("Custom", status_code=418)
        assert err.status_code == 418

    def test_not_found_error(self):
        err = NotFoundError("Volunteer not found")
        assert err.status_code == 404
        assert isinstance(err, AppError)

    def test_validation_error(self):
        err = ValidationError("Invalid email format")
        assert err.status_code == 400

    def test_authorization_error(self):
        err = AuthorizationError()
        assert err.status_code == 403
        assert "permission" in err.safe_message.lower()

    def test_external_service_error(self):
        err = ExternalServiceError("Salesforce down", detail="ConnectionError")
        assert err.status_code == 502

    def test_database_error(self):
        err = DatabaseError(detail="IntegrityError on unique constraint")
        assert err.status_code == 500
        assert err.detail == "IntegrityError on unique constraint"

    def test_import_record_error(self):
        err = ImportRecordError(
            "Bad volunteer record",
            record_id="0015f000abc",
            detail="NoneType on email",
        )
        assert err.record_id == "0015f000abc"
        assert err.status_code == 500
        assert isinstance(err, AppError)

    def test_inheritance_chain(self):
        """All custom errors should be catchable as AppError and Exception."""
        for cls in [
            NotFoundError,
            ValidationError,
            AuthorizationError,
            ExternalServiceError,
            DatabaseError,
            ImportRecordError,
        ]:
            err = cls("test")
            assert isinstance(err, AppError)
            assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# Component 2: Error Handler Middleware
# ---------------------------------------------------------------------------
class TestErrorHandlerMiddleware:
    """Test Flask error handler registration and response behavior."""

    @pytest.fixture
    def error_app(self):
        """Create a minimal Flask app with error handlers registered."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        from utils.error_handlers import register_error_handlers

        register_error_handlers(app)

        # Register test routes that raise specific errors
        @app.route("/raise-not-found")
        def raise_not_found():
            raise NotFoundError("Volunteer 999 not found")

        @app.route("/raise-validation")
        def raise_validation():
            raise ValidationError("Email format is invalid")

        @app.route("/raise-app-error")
        def raise_app_error():
            raise AppError("Something broke", detail="secret traceback")

        @app.route("/return-ok")
        def return_ok():
            return jsonify({"status": "ok"})

        return app

    def test_app_error_json_response(self, error_app):
        """JSON requests get structured JSON error responses."""
        with error_app.test_client() as client:
            resp = client.get(
                "/raise-validation",
                headers={"Accept": "application/json"},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["error"] == "Email format is invalid"
            assert data["type"] == "ValidationError"

    def test_app_error_does_not_leak_detail(self, error_app):
        """Internal detail should NOT appear in the response."""
        with error_app.test_client() as client:
            resp = client.get(
                "/raise-app-error",
                headers={"Accept": "application/json"},
            )
            data = resp.get_json()
            assert "secret traceback" not in str(data)

    def test_not_found_json(self, error_app):
        with error_app.test_client() as client:
            resp = client.get(
                "/raise-not-found",
                headers={"Accept": "application/json"},
            )
            assert resp.status_code == 404
            data = resp.get_json()
            assert data["type"] == "NotFoundError"

    def test_ok_route_unaffected(self, error_app):
        """Normal routes should not be affected by error handlers."""
        with error_app.test_client() as client:
            resp = client.get("/return-ok")
            assert resp.status_code == 200
            assert resp.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Component 3: Route Error Decorator
# ---------------------------------------------------------------------------
class TestHandleRouteErrors:
    """Test the @handle_route_errors decorator."""

    @pytest.fixture
    def decorator_app(self):
        """Create a Flask app with routes using @handle_route_errors."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        from utils.error_handlers import register_error_handlers

        register_error_handlers(app)

        from routes.decorators import handle_route_errors

        @app.route("/decorated-ok")
        @handle_route_errors
        def decorated_ok():
            return jsonify({"status": "ok"})

        @app.route("/decorated-app-error")
        @handle_route_errors
        def decorated_app_error():
            raise NotFoundError("Thing not found")

        @app.route("/decorated-generic-error")
        @handle_route_errors
        def decorated_generic_error():
            raise RuntimeError("unexpected crash")

        return app

    def test_happy_path_unaffected(self, decorator_app):
        with decorator_app.test_client() as client:
            resp = client.get("/decorated-ok")
            assert resp.status_code == 200

    def test_app_error_passes_through(self, decorator_app):
        """AppError subclasses should be re-raised for middleware to handle."""
        with decorator_app.test_client() as client:
            resp = client.get(
                "/decorated-app-error",
                headers={"Accept": "application/json"},
            )
            assert resp.status_code == 404
            data = resp.get_json()
            assert data["type"] == "NotFoundError"

    def test_generic_error_wrapped(self, decorator_app):
        """Generic exceptions should be wrapped in AppError (500)."""
        with decorator_app.test_client() as client:
            resp = client.get(
                "/decorated-generic-error",
                headers={"Accept": "application/json"},
            )
            assert resp.status_code == 500
