# create_admin.py

import sys
import os
# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from getpass import getpass

from werkzeug.security import generate_password_hash

from app import app
from models.user import User, db


def create_admin():
    with app.app_context():
        username = input("Enter username: ").strip()
        email = input("Enter email: ").strip()

        if User.query.filter_by(username=username).first():
            print("Error: Username already exists.")
            sys.exit(1)

        if User.query.filter_by(email=email).first():
            print("Error: Email already exists.")
            sys.exit(1)

        password = getpass("Enter password: ")
        password2 = getpass("Confirm password: ")

        if password != password2:
            print("Error: Passwords do not match.")
            sys.exit(1)

        if not password:
            print("Error: Password cannot be empty.")
            sys.exit(1)

        new_admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
        )

        db.session.add(new_admin)
        db.session.commit()
        print("Admin account created successfully.")


if __name__ == "__main__":
    create_admin()
