from getpass import getpass
import sys
from models.user import db, User
from werkzeug.security import generate_password_hash
from app import app

def create_jonlane():
    with app.app_context():
        username = 'jonlane'
        email = 'jlane@prepkc.org'
        password = 'nihlism'

        if User.query.filter_by(username=username).first():
            print('Error: Username already exists.')
            sys.exit(1)

        if User.query.filter_by(email=email).first():
            print('Error: Email already exists.')
            sys.exit(1)

        new_admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_admin)
        db.session.commit()
        print('Jon Lane account created successfully.')

if __name__ == '__main__':
    create_jonlane()
