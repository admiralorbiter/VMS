#!/usr/bin/env python3
"""Verify SQL changes applied to database."""

import sqlite3
import sys


def verify_changes():
    """Verify the district scoping SQL changes."""
    try:
        conn = sqlite3.connect("instance/your_database.db")
        cursor = conn.cursor()

        # Check table structure
        print("=== Users Table Columns ===")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # Check for district-scoped users
        print("\n=== District-Scoped Users ===")
        cursor.execute(
            """
            SELECT id, username, email, security_level, scope_type, allowed_districts
            FROM users
            WHERE scope_type = 'district' OR security_level = -1
        """
        )
        users = cursor.fetchall()
        if users:
            for user in users:
                print(f"  ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
                print(f"    Security Level: {user[3]}, Scope Type: {user[4]}")
                print(f"    Allowed Districts: {user[5]}")
        else:
            print("  No district-scoped users found")

        conn.close()
        print("\nDatabase verification complete")

    except Exception as e:
        print(f"Error verifying database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_changes()
