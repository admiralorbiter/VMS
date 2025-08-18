#!/usr/bin/env python

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

# Add the parent directory to the path so we can import the app and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app import app
from models import db
from models.bug_report import BugReport, BugReportType

OLD_DB_PATH = os.path.join("instance", "old.db")
NEW_DB_PATH = os.path.join("instance", "your_database.db")


def copy_bugs_fast():
    """
    Fast bulk copy of bug report data using optimized database operations.
    """
    with app.app_context():
        print("Starting fast bug report migration...")
        start_time = time.time()

        # Connect to both databases
        old_conn = sqlite3.connect(OLD_DB_PATH)
        old_conn.row_factory = sqlite3.Row
        new_conn = sqlite3.connect(NEW_DB_PATH)

        try:
            # Get existing bug report IDs to avoid duplicates
            print("Checking for existing bug reports...")
            existing_bugs = set()
            existing_result = db.session.execute(
                text("SELECT id FROM bug_reports")
            ).fetchall()
            existing_bugs = {row[0] for row in existing_result}
            print(f"Found {len(existing_bugs)} existing bug reports in target database")

            # Get all bug report data in one query
            print("Fetching bug report data from old database...")
            query = """
            SELECT
                id, type, description, page_url, page_title,
                submitted_by_id, resolved, resolved_by_id, resolution_notes,
                created_at, resolved_at
            FROM bug_reports
            WHERE description IS NOT NULL
            AND description != ''
            ORDER BY id
            """

            old_cursor = old_conn.cursor()
            old_cursor.execute(query)

            # Process in chunks for better memory management
            chunk_size = 1000
            total_processed = 0
            total_copied = 0
            total_skipped = 0

            print("Processing bug report records in chunks...")

            while True:
                rows = old_cursor.fetchmany(chunk_size)
                if not rows:
                    break

                chunk_start_time = time.time()

                # Filter out existing bug reports
                new_bugs = []
                for row in rows:
                    if row["id"] not in existing_bugs:
                        new_bugs.append(dict(row))
                    else:
                        total_skipped += 1

                if new_bugs:
                    # Bulk insert using raw SQL for speed
                    bug_values = []

                    for bug_data in new_bugs:
                        # Convert type to integer if it's a string
                        bug_type = bug_data.get("type", 0)
                        if isinstance(bug_type, str):
                            try:
                                bug_type = int(bug_type)
                            except ValueError:
                                bug_type = 0

                        # Handle timestamps - convert to UTC if needed
                        created_at = bug_data.get("created_at")
                        if created_at:
                            if isinstance(created_at, str):
                                try:
                                    # Try to parse the timestamp
                                    created_at = datetime.fromisoformat(
                                        created_at.replace("Z", "+00:00")
                                    )
                                except ValueError:
                                    created_at = datetime.now(timezone.utc)
                            elif not created_at.tzinfo:
                                created_at = created_at.replace(tzinfo=timezone.utc)
                        else:
                            created_at = datetime.now(timezone.utc)

                        resolved_at = bug_data.get("resolved_at")
                        if resolved_at:
                            if isinstance(resolved_at, str):
                                try:
                                    resolved_at = datetime.fromisoformat(
                                        resolved_at.replace("Z", "+00:00")
                                    )
                                except ValueError:
                                    resolved_at = None
                            elif not resolved_at.tzinfo:
                                resolved_at = resolved_at.replace(tzinfo=timezone.utc)
                        else:
                            resolved_at = None

                        # Prepare bug report data
                        bug_values.append(
                            (
                                bug_data["id"],
                                bug_type,
                                bug_data["description"],
                                bug_data.get("page_url", ""),
                                bug_data.get("page_title", ""),
                                bug_data["submitted_by_id"],
                                bool(bug_data.get("resolved", False)),
                                bug_data.get("resolved_by_id"),
                                bug_data.get("resolution_notes"),
                                created_at,
                                resolved_at,
                            )
                        )

                    # Bulk insert bug reports
                    bug_sql = """
                    INSERT INTO bug_reports (
                        id, type, description, page_url, page_title,
                        submitted_by_id, resolved, resolved_by_id, resolution_notes,
                        created_at, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    new_cursor = new_conn.cursor()
                    new_cursor.executemany(bug_sql, bug_values)
                    new_conn.commit()

                    total_copied += len(new_bugs)

                    # Update existing bugs set to avoid duplicates in next chunks
                    for bug_data in new_bugs:
                        existing_bugs.add(bug_data["id"])

                total_processed += len(rows)
                chunk_time = time.time() - chunk_start_time

                # Progress update
                elapsed_time = time.time() - start_time
                rate = total_processed / elapsed_time if elapsed_time > 0 else 0

                print(
                    f"Processed: {total_processed:,} records | Copied: {total_copied:,} | Skipped: {total_skipped:,} | Rate: {rate:.1f} records/sec | Chunk time: {chunk_time:.2f}s"
                )

            total_time = time.time() - start_time
            print(f"\nFast Migration Complete!")
            print(f"Total records processed: {total_processed:,}")
            print(f"Bug reports copied: {total_copied:,}")
            print(f"Bug reports skipped (already exist): {total_skipped:,}")
            print(f"Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
            print(f"Average rate: {total_processed/total_time:.1f} records/second")

        except Exception as e:
            print(f"Error during migration: {e}")
            import traceback

            traceback.print_exc()
        finally:
            old_conn.close()
            new_conn.close()


if __name__ == "__main__":
    # Ensure the instance directory exists
    if not os.path.exists("instance"):
        os.makedirs("instance")
        print("Created 'instance' directory.")

    # Basic check if databases exist
    if not os.path.exists(OLD_DB_PATH):
        print(f"Error: Old database not found at {OLD_DB_PATH}")
    elif not os.path.exists(NEW_DB_PATH):
        print(f"Error: New database not found at {NEW_DB_PATH}")
        print(
            "Please ensure the new database is initialized (e.g., using Flask-Migrate or db.create_all())."
        )
    else:
        copy_bugs_fast()
