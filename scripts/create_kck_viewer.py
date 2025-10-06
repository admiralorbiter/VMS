#!/usr/bin/env python3
"""
KCK Viewer User Creation Script
==============================

This script helps create a KCK viewer user account for testing and setup purposes.
Run this script from the project root directory.

Usage:
    python scripts/create_kck_viewer.py

The script will prompt for:
- Username
- Email
- Password
- First Name
- Last Name

The user will be created with KCK_VIEWER security level (-1).
"""

import sys
import os
from getpass import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, User
from models.user import SecurityLevel
from werkzeug.security import generate_password_hash
from app import create_app

def create_kck_viewer():
    """Create a new KCK viewer user account."""
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("=== KCK Viewer User Creation ===")
        print("This script will create a new KCK viewer user account.")
        print("KCK viewers have restricted access to only the Kansas City Kansas Public Schools teacher progress page.\n")
        
        # Get user input
        username = input("Username: ").strip()
        if not username:
            print("Username is required!")
            return
        
        email = input("Email: ").strip()
        if not email:
            print("Email is required!")
            return
        
        password = getpass("Password: ")
        if not password:
            print("Password is required!")
            return
        
        first_name = input("First Name (optional): ").strip()
        last_name = input("Last Name (optional): ").strip()
        
        # Check if user already exists
        existing_user = User.query.filter(
            db.or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            print(f"Error: User with username '{username}' or email '{email}' already exists!")
            return
        
        try:
            # Create the user
            kck_viewer = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                security_level=SecurityLevel.KCK_VIEWER,
                first_name=first_name or None,
                last_name=last_name or None
            )
            
            db.session.add(kck_viewer)
            db.session.commit()
            
            print(f"\n✅ Successfully created KCK viewer user: {username}")
            print(f"   Email: {email}")
            print(f"   Security Level: KCK_VIEWER (-1)")
            print(f"   Full Name: {first_name} {last_name}".strip())
            print(f"\nThe user can now log in and will be automatically redirected to:")
            print("http://127.0.0.1:5050/reports/virtual/usage/district/Kansas%20City%20Kansas%20Public%20Schools/teacher-progress?year=2025-2026&date_from=2025-08-01&date_to=2026-07-31")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {str(e)}")
            return

if __name__ == "__main__":
    create_kck_viewer()
