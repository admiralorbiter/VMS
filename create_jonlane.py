from getpass import getpass
import sys
from models.user import db, User
from werkzeug.security import generate_password_hash
from app import app

def create_accounts():
    with app.app_context():
        # Create Jon Lane's admin account
        username = 'jonlane'
        email = 'jlane@prepkc.org'
        password = 'nihlism'

        if User.query.filter_by(username=username).first():
            print('Error: Username jonlane already exists.')
            sys.exit(1)

        if User.query.filter_by(email=email).first():
            print('Error: Email jlane@prepkc.org already exists.')
            sys.exit(1)

        new_admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        print(f"Admin security level: {new_admin.security_level}") 

        db.session.add(new_admin)
        db.session.commit()
        print('Admin account created successfully.')

if __name__ == '__main__':
    create_accounts()
