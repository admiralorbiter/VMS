import pytest
from models.user import User
from werkzeug.security import generate_password_hash

def test_new_user():
    """Test creating a new user"""
    user = User(
        username='newuser',
        email='new@example.com',
        password_hash=generate_password_hash('password123'),
        first_name='New',
        last_name='User',
        is_admin=False
    )
    
    assert user.username == 'newuser'
    assert user.email == 'new@example.com'
    assert user.first_name == 'New'
    assert user.last_name == 'User'
    assert user.is_admin is False

def test_user_admin_flag():
    """Test admin flag functionality"""
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('admin123'),
        is_admin=True
    )
    assert admin.is_admin is True 