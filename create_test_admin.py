#!/usr/bin/env python3
"""
Create a test admin user for accessing the Prefect dashboard.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from models.user import User
from werkzeug.security import generate_password_hash

def create_test_admin():
    """Create a test admin user."""
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("Admin user 'admin' already exists.")
            print("Username: admin")
            print("Password: admin123")
            return
        
        # Create new admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("Test admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("\nYou can now login at http://localhost:5050/login")
        print("Then access the Prefect dashboard at http://localhost:5050/prefect/dashboard")

if __name__ == '__main__':
    create_test_admin() 