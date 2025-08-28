#!/usr/bin/env python

import os
import sqlite3
import sys

print("Script starting...")

SOURCE_DB_PATH = os.path.join("instance", "your_database.db")
TARGET_DB_PATH = os.path.join("instance", "voluntold.db")

print(f"Source path: {SOURCE_DB_PATH}")
print(f"Target path: {TARGET_DB_PATH}")

# Check if files exist
print(f"Source exists: {os.path.exists(SOURCE_DB_PATH)}")
print(f"Target exists: {os.path.exists(TARGET_DB_PATH)}")

try:
    print("Attempting to connect to source database...")
    source_conn = sqlite3.connect(SOURCE_DB_PATH)
    print("Source connection successful")

    source_cursor = source_conn.cursor()
    source_cursor.execute("SELECT COUNT(*) FROM users")
    source_count = source_cursor.fetchone()[0]
    print(f"Source users count: {source_count}")

    print("Attempting to connect to target database...")
    target_conn = sqlite3.connect(TARGET_DB_PATH)
    print("Target connection successful")

    target_cursor = target_conn.cursor()
    target_cursor.execute("SELECT COUNT(*) FROM users")
    target_count = target_cursor.fetchone()[0]
    print(f"Target users count: {target_count}")

    # Get column names from source
    source_cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in source_cursor.fetchall()]
    print(f"Source columns: {columns}")

    # Fetch all users from source
    source_cursor.execute("SELECT * FROM users")
    rows = source_cursor.fetchall()

    # Track statistics
    total = len(rows)
    updated = 0
    inserted = 0
    skipped = 0

    print(f"\nProcessing {total} users...")

    for i, row in enumerate(rows):
        username = row[1] if row[1] else "Unknown"
        print(f"Processing user {i+1}/{total}: {username}")

        # Create a dict of the current row data
        row_dict = dict(zip(columns, row))

        # Check if user already exists in target database
        target_cursor.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (row_dict.get("username"), row_dict.get("email")),
        )
        existing_user = target_cursor.fetchone()

        try:
            if existing_user is not None:
                # Update existing user
                target_cursor.execute(
                    """
                    UPDATE users SET
                        email = ?, password_hash = ?, first_name = ?, last_name = ?,
                        security_level = ?, api_token = ?, token_expiry = ?,
                        created_at = ?, updated_at = ?
                    WHERE username = ?
                """,
                    (
                        row_dict.get("email"),
                        row_dict.get("password_hash"),
                        row_dict.get("first_name"),
                        row_dict.get("last_name"),
                        row_dict.get("security_level", 0),
                        row_dict.get("api_token"),
                        row_dict.get("token_expiry"),
                        row_dict.get("created_at"),
                        row_dict.get("updated_at"),
                        row_dict.get("username"),
                    ),
                )
                updated += 1
                print(f"  Updated {username} successfully")
            else:
                # Insert new user
                target_cursor.execute(
                    """
                    INSERT INTO users (
                        username, email, password_hash, first_name, last_name,
                        security_level, api_token, token_expiry, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        row_dict.get("username"),
                        row_dict.get("email"),
                        row_dict.get("password_hash"),
                        row_dict.get("first_name"),
                        row_dict.get("last_name"),
                        row_dict.get("security_level", 0),
                        row_dict.get("api_token"),
                        row_dict.get("token_expiry"),
                        row_dict.get("created_at"),
                        row_dict.get("updated_at"),
                    ),
                )
                inserted += 1
                print(f"  Inserted {username} successfully")

            target_conn.commit()

        except Exception as e:
            print(f"  Error processing user {username}: {str(e)}")
            target_conn.rollback()
            skipped += 1
            continue

    # Get final count
    target_cursor.execute("SELECT COUNT(*) FROM users")
    final_count = target_cursor.fetchone()[0]

    print(f"\nMigration complete:")
    print(f"Total users processed: {total}")
    print(f"Users inserted: {inserted}")
    print(f"Users updated: {updated}")
    print(f"Users skipped: {skipped}")
    print(f"Final target count: {final_count}")

    source_conn.close()
    target_conn.close()
    print("Database connections closed")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback

    traceback.print_exc()
