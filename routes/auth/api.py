from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import User, db
from datetime import datetime, timezone
import json

api_bp = Blueprint('api', __name__)

def token_required(f):
    """Decorator to check valid API token for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token')
        
        if not token:
            return jsonify({'error': 'API token is missing'}), 401
            
        user = User.find_by_api_token(token)
        if not user or not user.check_api_token(token):
            return jsonify({'error': 'Invalid or expired API token'}), 401
            
        # Add user to request context
        request.user = user
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/token', methods=['POST'])
def get_token():
    """
    Generate API token for user authentication.
    Requires username/email and password.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request data'}), 400
        
    username = data.get('username')
    password = data.get('password')
    expiration = data.get('expiration', 30)  # Default 30 days
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
        
    # Find and authenticate user
    from werkzeug.security import check_password_hash
    user = User.find_by_username_or_email(username)
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
        
    # Generate token
    token = user.generate_api_token(expiration=expiration)
    
    return jsonify({
        'token': token,
        'expires': user.token_expiry.isoformat()
    })

@api_bp.route('/token/revoke', methods=['POST'])
@token_required
def revoke_token():
    """Revoke the current API token."""
    request.user.revoke_api_token()
    return jsonify({'message': 'Token revoked successfully'})

@api_bp.route('/token/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Refresh the current API token."""
    expiration = request.json.get('expiration', 30)
    token = request.user.generate_api_token(expiration=expiration)
    
    return jsonify({
        'token': token,
        'expires': request.user.token_expiry.isoformat()
    })

@api_bp.route('/users/sync', methods=['GET'])
@token_required
def sync_users():
    """
    Sync user data.
    Optional parameter 'since' for incremental sync (ISO datetime).
    """
    # Only users with MANAGER level or higher can sync all users
    if not request.user.has_permission_level(2):  # SecurityLevel.MANAGER
        return jsonify({'error': 'Permission denied'}), 403
    
    # Check for 'since' parameter for incremental sync
    since = request.args.get('since')
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid date format for "since" parameter'}), 400
        
        users = User.query.filter(User.updated_at >= since_dt).all()
    else:
        users = User.query.all()
    
    # Convert users to dictionaries
    user_data = [user.to_dict() for user in users]
    
    return jsonify({
        'users': user_data,
        'count': len(user_data),
        'sync_time': datetime.now(timezone.utc).isoformat()
    })

@api_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(user_id):
    """Get specific user data by ID."""
    # Check permissions
    if not request.user.has_permission_level(1) and request.user.id != user_id:
        return jsonify({'error': 'Permission denied'}), 403
        
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())
