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
from datetime import datetime, timezone  # Keep this as it might be used elsewhere

from dotenv import load_dotenv

# Load environment variables from .env file FIRST, before any other imports
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


# Initialize routes from all blueprints
# This registers all application routes (auth, volunteers, events, etc.)
init_routes(app)

# Register custom Jinja2 template filters
# These filters are available in all templates for data formatting and display
app.jinja_env.filters["short_date"] = short_date
app.jinja_env.filters["event_type_badge"] = format_event_type_for_badge

# Add custom JSON filter for district scoping and data serialization
import json


def from_json_filter(json_string):
    """
    Custom Jinja2 filter to parse JSON strings.

    Safely converts JSON strings to Python objects, returning empty list
    for invalid or empty values. Used for deserializing stored JSON data
    in templates.

    Args:
        json_string: JSON string to parse, or already-parsed object

    Returns:
        Parsed Python object (list/dict) or empty list on failure
    """
    if not json_string or json_string == "None" or json_string == "null":
        return []
    try:
        if isinstance(json_string, str):
            return json.loads(json_string)
        return json_string
    except (json.JSONDecodeError, TypeError):
        return []


app.jinja_env.filters["from_json"] = from_json_filter


@app.route("/docs/<path:filename>")
def documentation(filename):
    return send_from_directory("documentation", filename)


def create_app():
    """
    Minimal app factory to integrate with WSGI servers and tests.

    This function provides a standard WSGI application interface for deployment
    to production servers (Gunicorn, uWSGI, etc.) and for testing frameworks.

    Returns:
        Configured Flask application instance
    """
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
