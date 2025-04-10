#!/usr/bin/env python

import sqlite3
import os
from datetime import datetime, timezone
from models.user import db, User

OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")

def copy_users():
    """
    Copy all rows from the 'users' table in old.db to your_database.db.
    Skips duplicate entries based on username or email.
    Ensures timestamps are in UTC format.
    """
    # Connect to both old and new databases
    
    old_conn = sqlite3.connect(OLD_DB_PATH)
    new_conn = sqlite3.connect(NEW_DB_PATH)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

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
        
        # Check if user already exists
        new_cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?",
                         (row_dict.get('username'), row_dict.get('email')))
        
        if new_cursor.fetchone() is not None:
            skipped += 1
            continue

        try:
            new_cursor.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    first_name,
                    last_name,
                    security_level,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict.get('username'),
                row_dict.get('email'),
                row_dict.get('password_hash'),
                row_dict.get('first_name'),
                row_dict.get('last_name'),
                row_dict.get('security_level', 0),  # Default to USER level if not specified
                datetime.now(timezone.utc),  # New UTC timestamp for created_at
                datetime.now(timezone.utc)   # New UTC timestamp for updated_at
            ))
            copied += 1
        except sqlite3.IntegrityError as e:
            print(f"Skipping duplicate user: {row_dict.get('username')} - {str(e)}")
            skipped += 1
            continue

    new_conn.commit()

    print(f"\nMigration complete:")
    print(f"Total users processed: {total}")
    print(f"Users copied: {copied}")
    print(f"Users skipped: {skipped}")

    old_conn.close()
    new_conn.close()

def copy_upcoming_events():
    """
    Copy all rows from the 'upcoming_events' table in old.db to your_database.db.
    Skips duplicate entries based on salesforce_id.
    Ensures timestamps are in UTC format.
    """
    # Connect to both old and new databases
    old_conn = sqlite3.connect(OLD_DB_PATH)
    new_conn = sqlite3.connect(NEW_DB_PATH)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Fetch all upcoming_events rows from old.db
    old_cursor.execute("SELECT * FROM upcoming_events")
    rows = old_cursor.fetchall()

    # Get column names
    old_cursor.execute("PRAGMA table_info(upcoming_events)")
    columns = [col[1] for col in old_cursor.fetchall()]

    # Track statistics
    total = len(rows)
    skipped = 0
    copied = 0

    for row in rows:
        # Create a dict of the current row data
        row_dict = dict(zip(columns, row))
        
        # Check if event already exists
        new_cursor.execute("SELECT id FROM upcoming_events WHERE salesforce_id = ?",
                         (row_dict.get('salesforce_id'),))
        
        if new_cursor.fetchone() is not None:
            skipped += 1
            continue

        try:
            new_cursor.execute("""
                INSERT INTO upcoming_events (
                    salesforce_id,
                    name,
                    available_slots,
                    filled_volunteer_jobs,
                    date_and_time,
                    event_type,
                    registration_link,
                    display_on_website,
                    created_at,
                    updated_at,
                    start_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row_dict.get('salesforce_id'),
                row_dict.get('name'),
                row_dict.get('available_slots'),
                row_dict.get('filled_volunteer_jobs'),
                row_dict.get('date_and_time'),
                row_dict.get('event_type'),
                row_dict.get('registration_link'),
                row_dict.get('display_on_website', False),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                row_dict.get('start_date')
            ))
            copied += 1
        except sqlite3.IntegrityError as e:
            print(f"Skipping duplicate event: {row_dict.get('name')} - {str(e)}")
            skipped += 1
            continue

    new_conn.commit()

    print(f"\nUpcoming Events Migration complete:")
    print(f"Total events processed: {total}")
    print(f"Events copied: {copied}")
    print(f"Events skipped: {skipped}")

    old_conn.close()
    new_conn.close()

if __name__ == "__main__":
    copy_users()
    copy_upcoming_events()
