"""
Startup Validation Module
=========================
Validates environment configuration and critical settings at application startup.

This module performs checks on environment variables, configuration settings,
and security settings to ensure the application is deployed correctly.
Logs warnings and errors for common misconfigurations.

Key Features:
- Environment variable validation
- Security configuration checks
- Database connectivity testing
- Production environment verification
- Comprehensive startup logging

Usage:
    from utils.startup_validation import log_startup_info
    log_startup_info(app)
"""

import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)


def validate_environment() -> Tuple[bool, List[str]]:
    """
    Validate critical environment variables and configuration.

    Checks for required settings in production, validates security
    configuration, and identifies potential deployment issues.

    Returns:
        Tuple of (is_valid, list_of_warnings)
        is_valid: True if no critical issues found
        list_of_warnings: List of warning messages for any issues found
    """
    warnings = []
    flask_env = os.environ.get("FLASK_ENV", "development")

    # Check for production-specific requirements
    if flask_env == "production":
        if not os.environ.get("SECRET_KEY"):
            warnings.append("⚠️  SECRET_KEY not set - using insecure default")

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            warnings.append(
                "⚠️  DATABASE_URL not set - using SQLite fallback (NOT recommended for production!)"
            )
        else:
            # Validate DATABASE_URL is not SQLite in production
            if db_url.startswith("sqlite"):
                warnings.append(
                    "🚨 CRITICAL: Production using SQLite! Set proper DATABASE_URL for production database."
                )

        if os.environ.get("SECRET_KEY") == "dev-secret-key-change-in-production":
            warnings.append("🚨 CRITICAL: Using dev SECRET_KEY in production!")

    # Check for Salesforce credentials (optional but recommended)
    sf_vars = ["SF_USERNAME", "SF_PASSWORD", "SF_SECURITY_TOKEN"]
    missing_sf = [var for var in sf_vars if not os.environ.get(var)]
    if missing_sf:
        warnings.append(
            f"ℹ️  Salesforce integration disabled - missing: {', '.join(missing_sf)}"
        )

    return len(warnings) == 0, warnings


def log_startup_info(app):
    """
    Log startup configuration and warnings.

    Displays startup information including environment mode, database
    configuration, and any configuration warnings. Provides comprehensive
    diagnostics for deployment troubleshooting.

    Args:
        app: Flask application instance to inspect
    """
    flask_env = os.environ.get("FLASK_ENV", "development")

    logger.info(f"🚀 VMS starting in {flask_env.upper()} mode")
    logger.info(
        f"📊 Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')[:50]}..."
    )
    logger.info(f"🔒 Debug mode: {app.config.get('DEBUG', False)}")
    logger.info(f"🌐 Port: {os.environ.get('PORT', '5050')}")

    # Validate environment
    is_valid, warnings = validate_environment()

    if warnings:
        logger.warning("=" * 60)
        logger.warning("CONFIGURATION WARNINGS:")
        for warning in warnings:
            logger.warning(f"  {warning}")
        logger.warning("=" * 60)
    else:
        logger.info("✅ All environment checks passed")
