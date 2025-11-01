# app.py
"""
Main Flask Application Entry Point
==================================

This module serves as the central configuration and initialization point for the
Volunteer Management System (VMS) Flask application. It handles application setup,
configuration management, route registration, and database initialization.

Key Responsibilities:
- Environment-based configuration (development/production)
- Database initialization and migration
- Flask extension setup (Login, CORS, SQLAlchemy)
- Blueprint registration for modular routes
- Template filter registration
- Application factory pattern

Configuration:
- Port: 5050 (default)
- Database: SQLite or configured DATABASE_URL
- Production: Includes cache refresh scheduler

Security:
- Flask-Login integration for user sessions
- Security level context injection for templates
- CORS enabled for API access

Architecture:
- All business logic routes are organized into blueprints in the routes/ directory
- Quality scoring features are in routes/quality/
- Management features are in routes/management/
- Each feature module has its own routes, templates, and logic
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load environment variables FIRST, before any other imports
# This ensures all environment-dependent code has access to configuration
load_dotenv()

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from config import DevelopmentConfig, ProductionConfig
from models import User, db
from models.user import SecurityLevel
from routes.routes import init_routes
from utils import format_event_type_for_badge, short_date
from utils.cache_refresh_scheduler import start_cache_refresh_scheduler
from utils.startup_validation import log_startup_info
from utils.template_filters import from_json_filter

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for API access

# Load configuration based on the environment
# FLASK_ENV environment variable determines which config class to use
flask_env = os.environ.get("FLASK_ENV", "development")

if flask_env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Validate and log startup configuration
log_startup_info(app)

# Initialize Flask extensions
# SQLAlchemy: Database ORM for all model operations
db.init_app(app)

# Flask-Login: User session management and authentication
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # Redirect to 'login' view if unauthorized
login_manager.login_message_category = "info"

# Create instance directory if it doesn't exist
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Create DB tables on startup (idempotent)
# This will create any missing tables for new models without affecting existing data
# NOTE: For production schema changes, use Alembic migrations instead
with app.app_context():
    try:
        # Always call create_all; it only creates tables that don't exist
        db.create_all()
    except Exception as e:
        # Fallback/diagnostic output if something goes wrong creating tables
        # This helps diagnose database connection or schema issues during startup
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"Database initialization error: {e}")
        print(f"Existing tables: {existing_tables}")


# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Load user by ID for Flask-Login session management."""
    return db.session.get(User, int(user_id))


# Add SecurityLevel to Flask's template context
@app.context_processor
def inject_security_levels() -> Dict[str, Any]:
    """
    Inject security level constants into template context.

    Makes security level enums available in all templates for access control.
    """
    return {
        "SecurityLevel": SecurityLevel,
        "USER": SecurityLevel.USER,
        "SUPERVISOR": SecurityLevel.SUPERVISOR,
        "MANAGER": SecurityLevel.MANAGER,
        "ADMIN": SecurityLevel.ADMIN,
    }


# Global security headers for all responses
@app.after_request
def set_security_headers(response):
    """
    Add security headers to all HTTP responses.

    Implements defense-in-depth security headers to protect against
    common web vulnerabilities and attacks.

    Headers applied:
    - X-Content-Type-Options: Prevents MIME-type sniffing attacks
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables browser XSS filter
    - Strict-Transport-Security: Force HTTPS in production

    Args:
        response: Flask response object to modify

    Returns:
        Modified response with security headers
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Only add HSTS header in production with HTTPS
    if os.environ.get("FLASK_ENV") == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# Global error handlers
@app.errorhandler(500)
def internal_server_error(error):
    """
    Handle 500 Internal Server Error globally.

    Provides user-friendly error page and logs detailed error information
    for debugging. Prevents exposing sensitive stack traces to users.

    Args:
        error: Exception object that triggered the error

    Returns:
        Rendered error template or JSON error response
    """
    app.logger.error(f"Internal Server Error: {error}", exc_info=True)

    # Return JSON for API requests, HTML for browser requests
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error occurred"}), 500

    # For web requests, return error page
    return render_template("errors/500.html"), 500


@app.errorhandler(404)
def not_found_error(error):
    """
    Handle 404 Not Found Error globally.

    Provides user-friendly error page for missing resources.

    Args:
        error: Exception object that triggered the error

    Returns:
        Rendered error template or JSON error response
    """
    # Return JSON for API requests, HTML for browser requests
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404

    # For web requests, return error page
    return render_template("errors/404.html"), 404


@app.errorhandler(403)
def forbidden_error(error):
    """
    Handle 403 Forbidden Error globally.

    Provides user-friendly error page for unauthorized access.

    Args:
        error: Exception object that triggered the error

    Returns:
        Rendered error template or JSON error response
    """
    # Return JSON for API requests, HTML for browser requests
    if request.path.startswith("/api/"):
        return jsonify({"error": "Access forbidden"}), 403

    # For web requests, return error page
    return render_template("errors/403.html"), 403


# Initialize routes from all blueprints
# This registers all application routes (auth, volunteers, events, etc.)
init_routes(app)

# Register custom Jinja2 template filters
# These filters are available in all templates for data formatting and display
app.jinja_env.filters["short_date"] = short_date
app.jinja_env.filters["event_type_badge"] = format_event_type_for_badge
app.jinja_env.filters["from_json"] = from_json_filter


@app.route("/docs/<path:filename>")
def documentation(filename):
    """Serve documentation files."""
    return send_from_directory("documentation", filename)


@app.route("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns JSON with application status, database connectivity, and version.
    Useful for monitoring tools, load balancers, and container orchestration.
    """
    try:
        # Test database connectivity
        db.session.execute(db.text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return jsonify(
        {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "database": db_status,
            "environment": os.environ.get("FLASK_ENV", "development"),
            "version": "1.0.0",
        }
    )


@app.route("/ready")
def readiness_check():
    """
    Readiness check for container orchestration.

    Returns 200 if app is ready to serve traffic, 503 otherwise.
    Used by Kubernetes/Docker to determine when to start routing traffic.
    """
    try:
        # Verify database is accessible
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ready"}), 200
    except Exception:
        return jsonify({"status": "not ready"}), 503


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application factory for creating Flask app instances.

    Supports different configurations for testing, development, and production.
    If config_name is not provided, uses FLASK_ENV environment variable.

    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                     If None, uses FLASK_ENV environment variable

    Returns:
        Configured Flask application instance

    Note:
        Currently returns a pre-configured app instance. Full factory pattern
        would require refactoring this module to avoid circular imports.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    # For now, just return the existing app instance
    # Full factory pattern would require refactoring the entire module
    return app


if __name__ == "__main__":
    # Entry point when running app directly (e.g., development server)

    # Start cache refresh scheduler in production environment
    # NOTE: In production, prefer using a process manager or scheduler system
    if flask_env == "production":
        try:
            start_cache_refresh_scheduler()
            app.logger.info("Cache refresh scheduler started")
        except Exception as e:
            app.logger.error(f"Failed to start cache refresh scheduler: {e}")

    # Configure server host and port
    # PORT: Server port (default: 5050)
    # BIND_ALL: If "1" or "true", bind to 0.0.0.0 (all interfaces)
    port = int(os.environ.get("PORT", 5050))
    bind_all = os.environ.get("BIND_ALL", "0") in ("1", "true", "True")
    host = "0.0.0.0" if (flask_env == "production" or bind_all) else "127.0.0.1"

    # Start Flask development server
    # NOTE: This is NOT suitable for production! Use Gunicorn or uWSGI instead
    app.run(host=host, port=port)
