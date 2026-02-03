# utils/logging_config.py
"""
Structured Logging Configuration for Production

Provides JSON-formatted logging in production for easier parsing by log
aggregation tools, while maintaining human-readable logs in development.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs in JSON format for production environments,
    making them easier to parse with log aggregation tools.
    """

    def format(self, record):
        import json

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        return json.dumps(log_entry)


def configure_logging(app):
    """
    Configure logging for the Flask application.

    In production: Uses JSON formatting for structured logging
    In development: Uses standard human-readable format

    Args:
        app: Flask application instance
    """
    flask_env = os.environ.get("FLASK_ENV", "development")
    log_level = os.environ.get(
        "LOG_LEVEL", "INFO" if flask_env == "production" else "DEBUG"
    )

    # Get the numeric log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Clear existing handlers
    app.logger.handlers.clear()

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    if flask_env == "production":
        # Production: JSON structured logging to file
        formatter = JSONFormatter()

        # File handler with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        app.logger.addHandler(file_handler)

        # Also log errors to stderr for PythonAnywhere error logs
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)

    else:
        # Development: Human-readable console logging
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        app.logger.addHandler(console_handler)

    app.logger.setLevel(numeric_level)
    app.logger.info(f"Logging configured: level={log_level}, env={flask_env}")
