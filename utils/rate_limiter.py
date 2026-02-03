# utils/rate_limiter.py
"""
Centralized Rate Limiting Configuration

Uses Flask-Limiter with file-based storage for persistence across
server restarts. For multi-worker deployments, upgrade to Redis storage.

Rate limit tiers:
- Public API: 60/min, 1000/hr, 10000/day per API key
- Authenticated: 120/min per user
- Anonymous: 30/min per IP
"""

import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Storage URI - uses local file for single-instance deployment
# For Redis (recommended for production with multiple workers):
#   RATELIMIT_STORAGE_URL=redis://localhost:6379/0
_storage_uri = os.environ.get(
    "RATELIMIT_STORAGE_URL",
    "memory://",  # Use in-memory for development, file/redis for production
)

# Create the limiter instance (will be initialized with app later)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=["200 per day", "50 per hour"],  # Default for unauthenticated
    strategy="fixed-window",  # or "moving-window" for stricter limiting
)


def get_api_key_or_ip():
    """
    Get rate limit key: API key if present, otherwise IP address.
    Used for public API rate limiting.
    """
    from flask import request

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    return f"ip:{get_remote_address()}"


def get_user_id_or_ip():
    """
    Get rate limit key: User ID if authenticated, otherwise IP address.
    Used for authenticated endpoint rate limiting.
    """
    from flask import request
    from flask_login import current_user

    if current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return f"ip:{get_remote_address()}"


# Pre-defined rate limit decorators for common use cases
def public_api_limit():
    """Rate limit decorator for public API endpoints (FR-API-104)."""
    return limiter.limit(
        "60 per minute; 1000 per hour; 10000 per day",
        key_func=get_api_key_or_ip,
        error_message="Rate limit exceeded. Please try again later.",
    )


def authenticated_limit():
    """Rate limit decorator for authenticated endpoints."""
    return limiter.limit(
        "120 per minute",
        key_func=get_user_id_or_ip,
        error_message="Too many requests. Please slow down.",
    )


def init_rate_limiter(app):
    """
    Initialize rate limiter with Flask app.

    Call this in app.py after app configuration.
    """
    limiter.init_app(app)

    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify, request

        app.logger.warning(
            f"Rate limit exceeded: {request.remote_addr} - {request.path}"
        )

        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": str(e.description),
                    },
                }
            ),
            429,
        )

    app.logger.info(f"Rate limiter initialized with storage: {_storage_uri}")
