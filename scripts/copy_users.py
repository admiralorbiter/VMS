#!/usr/bin/env python

import os
import sqlite3
import sys
from datetime import datetime, timezone

# Add the parent directory to the path so we can import the app and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import User, db
from models.user import SecurityLevel

OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")


def copy_users():
    """
    Copy all rows from the 'users' table in old.db to your_database.db.
    Skips duplicate entries based on username or email.
    Ensures timestamps are in UTC format.
    """
    with app.app_context():
        # Connect to old database
        old_conn = sqlite3.connect(OLD_DB_PATH)
        old_cursor = old_conn.cursor()

        # Fetch all user rows from old.db
        old_cursor.execute("SELECT * FROM users")
        rows = old_cursor.fetchall()

        # Get column names
        old_cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in old_cursor.fetchall()]

        # Track statistics
        total = len(rows)
        skipped = 0
        copied = 0

        for row in rows:
            # Create a dict of the current row data
            row_dict = dict(zip(columns, row))

            # Check if user already exists using SQLAlchemy
            existing_user = User.query.filter(
                (User.username == row_dict.get("username"))
                | (User.email == row_dict.get("email"))
            ).first()

            if existing_user is not None:
                skipped += 1
                continue

            try:
                # Create new user using SQLAlchemy model
                new_user = User(
                    username=row_dict.get("username"),
                    email=row_dict.get("email"),
                    password_hash=row_dict.get("password_hash"),
                    first_name=row_dict.get("first_name"),
                    last_name=row_dict.get("last_name"),
                    security_level=row_dict.get("security_level", SecurityLevel.USER),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                # Add to session and commit
                db.session.add(new_user)
                db.session.commit()
                copied += 1

            except Exception as e:
                print(f"Skipping user: {row_dict.get('username')} - {str(e)}")
                db.session.rollback()
                skipped += 1
                continue

        old_conn.close()

        print(f"\nMigration complete:")
        print(f"Total users processed: {total}")
        print(f"Users copied: {copied}")
        print(f"Users skipped: {skipped}")


if __name__ == "__main__":
    copy_users()
