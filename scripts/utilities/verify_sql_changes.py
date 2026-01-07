#!/usr/bin/env python3
"""Verify SQL changes applied to database."""

import os
import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config


def get_database_path():
    """Get the database path from configuration."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Extract path from SQLite URL (sqlite:///path/to/db.db)
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            # Convert to absolute path if relative
            if not os.path.isabs(db_path):
                # Check if file exists in current directory or instance directory
                if Path(db_path).exists():
                    return os.path.abspath(db_path)
                # Try instance directory
                instance_path = os.path.join(Config.INSTANCE_DIR, os.path.basename(db_path))
                if Path(instance_path).exists():
                    return instance_path
            return os.path.abspath(db_path) if not os.path.isabs(db_path) else db_path
        # For other database types, this script won't work (needs SQLAlchemy)
        print("Warning: DATABASE_URL is not SQLite. This script only works with SQLite databases.")
        return None
    else:
        # Use default database path from config
        return Config.DEFAULT_DB_PATH


def verify_changes():
    """Verify the district scoping SQL changes."""
    try:
        db_path = get_database_path()
        if not db_path:
            print("Error: Could not determine database path")
            sys.exit(1)
        
        if not Path(db_path).exists():
            print(f"Error: Database file not found: {db_path}")
            sys.exit(1)
        
        print(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
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
