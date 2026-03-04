# app.py

import os

from dotenv import load_dotenv

# Load environment variables from .env file FIRST, before any other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_login import LoginManager
from sqlalchemy import text

from config import DevelopmentConfig, ProductionConfig
from models import User, db
from models.user import SecurityLevel
from routes.routes import init_routes
from utils import format_event_type_for_badge, short_date
from utils.cache_refresh_scheduler import start_cache_refresh_scheduler

app = Flask(__name__)

# Load configuration based on the environment
flask_env = os.environ.get("FLASK_ENV", "development")

if flask_env == "production":
    app.config.from_object(ProductionConfig)
    # Enforce SECRET_KEY in production - fail fast if not set properly
    if app.config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
        raise RuntimeError(
            "CRITICAL: SECRET_KEY must be set in production. "
            "Do not use the default development key."
        )
else:
    app.config.from_object(DevelopmentConfig)

# Security: Request size limit (16MB max)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# CORS configuration - restrict origins in production
if flask_env == "production":
    allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
    if allowed_origins:
        CORS(app, origins=allowed_origins)
    else:
        # Default to same-origin only in production if not specified
        CORS(app, origins=[os.environ.get("APP_BASE_URL", "").rstrip("/")])
else:
    # Allow all origins in development
    CORS(app)

# Initialize extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # Redirect to 'login' view if unauthorized
login_manager.login_message_category = "info"

# Create instance directory if it doesn't exist
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Create DB tables on startup (idempotent). This will create any missing tables for new models.
with app.app_context():
    try:
        # Always call create_all; it only creates tables that don't exist
        db.create_all()

        # Auto-sync file-based email templates to the database
        from utils.template_sync import sync_file_templates

        sync_file_templates()
    except Exception as e:
        # Fallback/diagnostic output if something goes wrong creating tables
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"Database initialization error: {e}")
        print(f"Existing tables: {existing_tables}")

# Configure structured logging (JSON in production, readable in development)
from utils.logging_config import configure_logging

configure_logging(app)

# Initialize rate limiter (Flask-Limiter)
from utils.rate_limiter import init_rate_limiter

init_rate_limiter(app)

# Register centralized error handlers (AppError hierarchy + SQLAlchemy + catch-all 500)
from utils.error_handlers import register_error_handlers

register_error_handlers(app)


# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Add SecurityLevel to Flask's template context
@app.context_processor
def inject_security_levels():
    return {
        "SecurityLevel": SecurityLevel,
        "USER": SecurityLevel.USER,
        "SUPERVISOR": SecurityLevel.SUPERVISOR,
        "MANAGER": SecurityLevel.MANAGER,
        "ADMIN": SecurityLevel.ADMIN,
    }


# Tenant context middleware (FR-TENANT-103)
@app.before_request
def set_tenant_context():
    """Set tenant context from authenticated user or admin override."""
    from flask import g

    from utils.tenant_context import init_tenant_context

    # Initialize tenant context for this request
    init_tenant_context()


# Add tenant context to template context (FR-TENANT-105)
@app.context_processor
def inject_tenant_context():
    """Make tenant context available in all templates."""
    from flask import g, session

    from utils.tenant_context import get_current_tenant, is_admin_viewing_as_tenant

    return {
        "current_tenant": get_current_tenant(),
        "is_admin_viewing_as_tenant": is_admin_viewing_as_tenant(),
    }


# Initialize routes
init_routes(app)

app.jinja_env.filters["short_date"] = short_date
app.jinja_env.filters["event_type_badge"] = format_event_type_for_badge

# Add custom JSON filter for district scoping
import json


def from_json_filter(json_string):
    """Custom Jinja2 filter to parse JSON strings."""
    if not json_string or json_string == "None" or json_string == "null":
        return []
    try:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    except (json.JSONDecodeError, TypeError):
        return []


app.jinja_env.filters["from_json"] = from_json_filter


# =============================================================================
# Global Error Handlers (Production Hardening)
# =============================================================================
# NOTE: The 500 handler is now in utils/error_handlers.py (registered above via
# register_error_handlers). The 404/403/413 handlers remain here because they
# handle standard HTTP errors with HTML templates, while the middleware handles
# AppError subclasses and SQLAlchemy errors.


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors."""
    app.logger.warning("404 error: %s", request.url)
    return render_template("errors/404.html"), 404


@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors."""
    app.logger.warning("403 error: %s - %s", request.url, error)
    return render_template("errors/403.html"), 403


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle 413 Request Entity Too Large errors."""
    app.logger.warning("413 error: File too large - %s", request.url)
    return (
        jsonify(
            {
                "error": "File too large",
                "message": "The uploaded file exceeds the maximum allowed size (16MB).",
            }
        ),
        413,
    )


# =============================================================================
# Health Check Endpoint (For Monitoring & Load Balancers)
# =============================================================================
@app.route("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        200: System is healthy (database connected)
        503: System is unhealthy (database connection failed)
    """
    try:
        # Verify database connectivity
        db.session.execute(text("SELECT 1"))
        return (
            jsonify(
                {"status": "healthy", "database": "connected", "environment": flask_env}
            ),
            200,
        )
    except Exception as e:
        app.logger.error("Health check failed: %s", e)
        return (
            jsonify(
                {"status": "unhealthy", "database": "disconnected", "error": str(e)}
            ),
            503,
        )


def create_app():
    """Minimal app factory to integrate with WSGI servers and tests."""
    return app


if __name__ == "__main__":
    # Start cache refresh scheduler in production
    if flask_env == "production":
        try:
            start_cache_refresh_scheduler()
            app.logger.info("Cache refresh scheduler started")
        except Exception as e:
            app.logger.error("Failed to start cache refresh scheduler: %s", e)

    # Use production-ready server configuration
    port = int(os.environ.get("PORT", 5050))
    bind_all = os.environ.get("BIND_ALL", "0") in ("1", "true", "True")
    host = "0.0.0.0" if (flask_env == "production" or bind_all) else "127.0.0.1"
    app.run(host=host, port=port)
