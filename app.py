# app.py

import os

from dotenv import load_dotenv

# Load environment variables from .env file FIRST, before any other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_login import LoginManager
from sqlalchemy import text

from models import db
from models.user import SecurityLevel


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------
def create_app(config_class=None):
    """
    Application factory for the VMS Flask application.

    Args:
        config_class: Configuration class to use. If None, auto-detects
                      from FLASK_ENV environment variable.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    if config_class:
        app.config.from_object(config_class)
    else:
        flask_env = os.environ.get("FLASK_ENV", "development")
        if flask_env == "production":
            from config import ProductionConfig

            app.config.from_object(ProductionConfig)
            # Enforce SECRET_KEY in production - fail fast if not set properly
            if app.config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
                raise RuntimeError(
                    "CRITICAL: SECRET_KEY must be set in production. "
                    "Do not use the default development key."
                )
            if (
                app.config.get("WTF_CSRF_SECRET_KEY")
                == "csrf-secret-key-change-in-production"
            ):
                raise RuntimeError(
                    "CRITICAL: WTF_CSRF_SECRET_KEY must be set in production. "
                    "Do not use the default development key."
                )
        else:
            from config import DevelopmentConfig

            app.config.from_object(DevelopmentConfig)

    # Security: Request size limit (16MB max)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    flask_env = os.environ.get("FLASK_ENV", "development")
    if flask_env == "production":
        allowed_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        allowed_origins = [
            origin.strip() for origin in allowed_origins if origin.strip()
        ]
        if allowed_origins:
            CORS(app, origins=allowed_origins)
        else:
            # Default to same-origin only in production if not specified
            CORS(app, origins=[os.environ.get("APP_BASE_URL", "").rstrip("/")])
    else:
        # Allow all origins in development
        CORS(app)

    # ------------------------------------------------------------------
    # Initialize extensions
    # ------------------------------------------------------------------
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from models import User

        return db.session.get(User, int(user_id))

    # ------------------------------------------------------------------
    # Database initialization
    # ------------------------------------------------------------------
    # Create instance directory if it doesn't exist
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    # Create DB tables on startup (idempotent)
    # In test mode, conftest handles DB setup with PRAGMA and safety checks
    if not app.config.get("TESTING", False):
        with app.app_context():
            try:
                db.create_all()
                # Auto-sync file-based email templates to the database
                from utils.template_sync import sync_file_templates

                sync_file_templates()
            except Exception as e:
                inspector = db.inspect(db.engine)
                existing_tables = inspector.get_table_names()
                print(f"Database initialization error: {e}")
                print(f"Existing tables: {existing_tables}")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    from utils.logging_config import configure_logging

    configure_logging(app)

    # ------------------------------------------------------------------
    # Rate limiter
    # ------------------------------------------------------------------
    from utils.rate_limiter import init_rate_limiter

    init_rate_limiter(app)

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
    from utils.error_handlers import register_error_handlers

    register_error_handlers(app)

    # ------------------------------------------------------------------
    # Context processors
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_security_levels():
        return {
            "SecurityLevel": SecurityLevel,
            "USER": SecurityLevel.USER,
            "SUPERVISOR": SecurityLevel.SUPERVISOR,
            "MANAGER": SecurityLevel.MANAGER,
            "ADMIN": SecurityLevel.ADMIN,
        }

    @app.context_processor
    def inject_tenant_context():
        """Make tenant context available in all templates."""
        from utils.tenant_context import get_current_tenant, is_admin_viewing_as_tenant

        return {
            "current_tenant": get_current_tenant(),
            "is_admin_viewing_as_tenant": is_admin_viewing_as_tenant(),
        }

    # ------------------------------------------------------------------
    # Before-request hooks
    # ------------------------------------------------------------------
    @app.before_request
    def set_tenant_context():
        """Set tenant context from authenticated user or admin override."""
        from utils.tenant_context import init_tenant_context

        init_tenant_context()

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    from routes.routes import init_routes

    init_routes(app)

    # ------------------------------------------------------------------
    # Jinja filters
    # ------------------------------------------------------------------
    import json

    from utils import format_event_type_for_badge, short_date

    app.jinja_env.filters["short_date"] = short_date
    app.jinja_env.filters["event_type_badge"] = format_event_type_for_badge

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

    # ------------------------------------------------------------------
    # HTTP error handlers (HTML responses)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Health check endpoint
    # ------------------------------------------------------------------
    @app.route("/health")
    def health_check():
        """
        Health check endpoint for monitoring and load balancers.

        Returns:
            200: System is healthy (database connected)
            503: System is unhealthy (database connection failed)
        """
        try:
            db.session.execute(text("SELECT 1"))
            return (
                jsonify(
                    {
                        "status": "healthy",
                        "database": "connected",
                        "environment": flask_env,
                    }
                ),
                200,
            )
        except Exception as e:
            app.logger.error("Health check failed: %s", e)
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "database": "disconnected",
                        "error": str(e),
                    }
                ),
                503,
            )

    return app


# ---------------------------------------------------------------------------
# Module-level app instance (backward compatibility for scripts & WSGI)
# ---------------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":
    from utils.cache_refresh_scheduler import start_cache_refresh_scheduler

    flask_env = os.environ.get("FLASK_ENV", "development")

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
