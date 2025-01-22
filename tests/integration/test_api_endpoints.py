import pytest
from flask import url_for
from werkzeug.security import generate_password_hash
from models.user import User
from models import db

def test_login_success(client, app):
    """Test successful login"""
    # Create test user
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()

    # Attempt login
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=False)
    
    assert response.status_code == 302  # Redirect after successful login

def test_protected_route_with_auth(client, auth_headers):
    """Test accessing protected route with authentication"""
    response = client.get('/admin', headers=auth_headers)
    assert response.status_code == 200

def test_protected_route_without_auth(client):
    """Test accessing protected route without authentication"""
    response = client.get('/admin')
    assert response.status_code == 302  # Redirect to login 