#!/usr/bin/env python3
"""
SQL Script Application Tool

Safely applies SQL scripts to the database with proper error handling
and rollback capabilities.

Usage:
    python scripts/apply_sql.py <sql_file> <database_path>

Example:
    python scripts/apply_sql.py scripts/sql/add_district_scoping.sql instance/your_database.db
"""

import sqlite3
import sys
from pathlib import Path


def apply_sql_script(sql_file, database_path):
    """
    Apply SQL script to database safely.

    Args:
        sql_file: Path to SQL script file
        database_path: Path to SQLite database file
    """
    # Validate inputs
    if not Path(sql_file).exists():
        print(f"Error: SQL file not found: {sql_file}")
        sys.exit(1)

    if not Path(database_path).exists():
        print(f"Error: Database file not found: {database_path}")
        sys.exit(1)

    print(f"Applying SQL script: {sql_file}")
    print(f"Target database: {database_path}")

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_script = f.read()

        print("Executing SQL commands...")
        cursor.executescript(sql_script)
        conn.commit()

        print(f"Successfully applied {sql_file}")
        print("Changes committed to database")

    except Exception as e:
        conn.rollback()
        print(f"Error applying SQL: {e}")
        print("Database rolled back to previous state")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python apply_sql.py <sql_file> <database_path>")
        print("")
        print("Examples:")
        print(
            "  python apply_sql.py scripts/sql/add_district_scoping.sql instance/your_database.db"
        )
        print(
            "  python apply_sql.py scripts/sql/rollback_district_scoping.sql instance/your_database.db"
        )
        sys.exit(1)

    sql_file = sys.argv[1]
    database_path = sys.argv[2]

    apply_sql_script(sql_file, database_path)
