"""
Authentication API Module
========================

This module provides RESTful API endpoints for authentication and user management
in the Volunteer Management System (VMS). It handles API token management,
user synchronization, and secure API access.

Key Features:
- API token generation and management
- Token-based authentication for API routes
- User data synchronization endpoints
- Permission-based access control
- Token refresh and revocation
- Incremental data sync support

Main Endpoints:
- /api/v1/token: Generate API authentication token
- /api/v1/token/revoke: Revoke current API token
- /api/v1/token/refresh: Refresh API token with new expiration
- /api/v1/users/sync: Synchronize user data (with optional incremental sync)
- /api/v1/users/<id>: Get specific user data

Security Features:
- Token-based authentication with expiration
- Permission level validation
- Secure password verification
- Token revocation capability
- Incremental sync with date filtering

Authentication Flow:
1. Client requests token with username/password
2. Server validates credentials and generates token
3. Client uses token in X-API-Token header
4. Server validates token on each request
5. Token can be refreshed or revoked as needed

Dependencies:
- Flask Blueprint for API routing
- User model for authentication and data
- Werkzeug for password hashing
- JWT or similar for token generation
- Database session for persistence

Models Used:
- User: User authentication and profile data
- Database session for data persistence

API Response Format:
- Success: JSON with data and metadata
- Error: JSON with error message and HTTP status code
"""

import json
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from models import User, db

api_bp = Blueprint("api", __name__)


def token_required(f):
    """
    Decorator to check valid API token for API routes.

    Validates the X-API-Token header and ensures the token is valid
    and not expired. Adds the authenticated user to request context.

    Args:
        f: Function to decorate

    Returns:
        Decorated function with token validation

    Raises:
        401: If token is missing or invalid
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-API-Token")

        if not token:
            return jsonify({"error": "API token is missing"}), 401

        user = User.find_by_api_token(token)
        if not user or not user.check_api_token(token):
            return jsonify({"error": "Invalid or expired API token"}), 401

        # Add user to request context
        request.user = user
        return f(*args, **kwargs)

    return decorated


@api_bp.route("/token", methods=["POST"])
def get_token():
    """
    Generate API token for user authentication.

    Authenticates user with username/email and password, then generates
    an API token for subsequent API requests.

    Request Body:
        username: Username or email address
        password: User password
        expiration: Token expiration in days (optional, default 30)

    Returns:
        JSON response with token and expiration information

    Raises:
        400: Missing request data or credentials
        401: Invalid credentials
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing request data"}), 400

    username = data.get("username")
    password = data.get("password")
    expiration = data.get("expiration", 30)  # Default 30 days

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Find and authenticate user
    from werkzeug.security import check_password_hash

    user = User.find_by_username_or_email(username)

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate token
    token = user.generate_api_token(expiration=expiration)

    return jsonify({"token": token, "expires": user.token_expiry.isoformat()})


@api_bp.route("/token/revoke", methods=["POST"])
@token_required
def revoke_token():
    """
    Revoke the current API token.

    Invalidates the current API token, requiring a new token for
    subsequent API requests.

    Returns:
        JSON response confirming token revocation
    """
    request.user.revoke_api_token()
    return jsonify({"message": "Token revoked successfully"})


@api_bp.route("/token/refresh", methods=["POST"])
@token_required
def refresh_token():
    """
    Refresh the current API token.

    Generates a new API token with optional new expiration time.
    The old token remains valid until the new one is generated.

    Request Body:
        expiration: New expiration time in days (optional, default 30)

    Returns:
        JSON response with new token and expiration information
    """
    expiration = request.json.get("expiration", 30)
    token = request.user.generate_api_token(expiration=expiration)

    return jsonify({"token": token, "expires": request.user.token_expiry.isoformat()})


@api_bp.route("/users/sync", methods=["GET"])
@token_required
def sync_users():
    """
    Synchronize user data.

    Returns user data for synchronization purposes. Supports incremental
    sync using the 'since' parameter to only return users updated after
    a specific date.

    Query Parameters:
        since: ISO datetime string for incremental sync (optional)

    Permission Requirements:
        - MANAGER level (security_level >= 2) for full sync
        - Lower levels may have restricted access

    Returns:
        JSON response with user data and sync metadata

    Raises:
        400: Invalid date format for 'since' parameter
        403: Insufficient permissions
    """
    # Only users with MANAGER level or higher can sync all users
    if not request.user.has_permission_level(2):  # SecurityLevel.MANAGER
        return jsonify({"error": "Permission denied"}), 403

    # Check for 'since' parameter for incremental sync
    since = request.args.get("since")
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": 'Invalid date format for "since" parameter'}), 400

        users = User.query.filter(User.updated_at >= since_dt).all()
    else:
        users = User.query.all()

    # Convert users to dictionaries
    user_data = [user.to_dict() for user in users]

    return jsonify(
        {
            "users": user_data,
            "count": len(user_data),
            "sync_time": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.route("/users/<int:user_id>", methods=["GET"])
@token_required
def get_user(user_id):
    """
    Get specific user data by ID.

    Returns detailed user information for the specified user ID.
    Users can only access their own data unless they have appropriate
    permission levels.

    Args:
        user_id: Database ID of the user to retrieve

    Permission Requirements:
        - Users can access their own data
        - MANAGER level (security_level >= 1) can access any user

    Returns:
        JSON response with user data

    Raises:
        403: Insufficient permissions
        404: User not found
    """
    # Check permissions
    if not request.user.has_permission_level(1) and request.user.id != user_id:
        return jsonify({"error": "Permission denied"}), 403

    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())
