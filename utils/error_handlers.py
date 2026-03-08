"""
Flask Error Handler Middleware
===============================

Registers centralized error handlers for AppError subclasses and
unhandled exceptions. Provides the safety net that makes removing
individual try/except blocks safe.

Usage in app.py:
    from utils.error_handlers import register_error_handlers
    register_error_handlers(app)

Behavior:
    - JSON requests → structured JSON error response
    - HTML requests → flash message + redirect (or error template for 404/500)
    - Always logs full traceback via app.logger.exception()
"""

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from utils.errors import AppError


def _wants_json():
    """Check if the current request expects a JSON response."""
    if request.is_json:
        return True
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "text/html" not in accept


def register_error_handlers(app):
    """Register all error handlers on the Flask app.

    Call this once during app initialization, after extensions are loaded.
    This supplements (does not replace) existing 404/403/413 handlers.
    """

    @app.errorhandler(AppError)
    def handle_app_error(error):
        """Handle all AppError subclasses with structured responses."""
        # Always log the full context
        if error.detail:
            current_app.logger.error(
                "%s [%s]: %s — detail: %s",
                type(error).__name__,
                error.status_code,
                error.safe_message,
                error.detail,
                exc_info=True,
            )
        else:
            current_app.logger.error(
                "%s [%s]: %s",
                type(error).__name__,
                error.status_code,
                error.safe_message,
                exc_info=True,
            )

        if _wants_json():
            response = {
                "error": error.safe_message,
                "type": type(error).__name__,
            }
            return jsonify(response), error.status_code

        # HTML response — flash and redirect for most errors
        if error.status_code == 404:
            return render_template("errors/404.html"), 404
        elif error.status_code == 403:
            flash(error.safe_message, "error")
            return render_template("errors/403.html"), 403

        # For 400/500/502 — flash and redirect to referrer or index
        flash(error.safe_message, "error")
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for("index"))

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """Handle unhandled SQLAlchemy errors that bubble up to Flask."""
        from models import db

        db.session.rollback()
        current_app.logger.exception("Unhandled database error: %s", str(error))

        if _wants_json():
            return (
                jsonify(
                    {
                        "error": "A database error occurred",
                        "type": "DatabaseError",
                    }
                ),
                500,
            )

        flash("A database error occurred. Please try again.", "error")
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for("index"))

    # Enhanced 500 handler — replaces the basic one in app.py
    @app.errorhandler(500)
    def handle_500(error):
        """Catch-all for unhandled 500 errors with full traceback logging."""
        from models import db

        db.session.rollback()
        current_app.logger.exception("Unhandled 500 error: %s", error)

        if _wants_json():
            return (
                jsonify(
                    {
                        "error": "An internal error occurred",
                        "type": "InternalServerError",
                    }
                ),
                500,
            )

        return render_template("errors/500.html"), 500
