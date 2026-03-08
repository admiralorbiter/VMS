#!/usr/bin/env python
"""
Production → Development Data Copy Tool
========================================

Copies app-only data (not from Salesforce/Pathful) between SQLite databases.
Useful for bringing production data into a local dev environment.

Usage:
    python scripts/utilities/copy_prod_data.py                    # Copy all tables
    python scripts/utilities/copy_prod_data.py --tables users     # Copy specific tables
    python scripts/utilities/copy_prod_data.py --dry-run          # Preview only
    python scripts/utilities/copy_prod_data.py --source instance/prod.db  # Custom source

Supported tables (app-only data that doesn't come from Salesforce/Pathful):
    - users: App users, credentials, tenant assignments
    - bug_reports: Bug report records
    - google_sheets: Google Sheet configurations (encrypted sheet IDs)
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

# Ensure repository root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

# ── Configuration ────────────────────────────────────────────────────

DEFAULT_SOURCE = os.path.join("instance", "old.db")
DEFAULT_TARGET = os.path.join("instance", "your_database.db")

# Tables that contain app-only data (safe to copy without Salesforce/Pathful)
# Each entry: table_name -> unique key columns for upsert matching
SUPPORTED_TABLES = {
    "users": {
        "match_keys": ["username", "email"],
        "description": "App users, credentials, roles, tenant assignments",
    },
    "bug_reports": {
        "match_keys": ["id"],
        "description": "Bug report records and metadata",
    },
    "google_sheets": {
        "match_keys": ["id"],
        "description": "Google Sheet configurations",
    },
}

# ── Helpers ───────────────────────────────────────────────────────────


def get_table_columns(conn, table_name):
    """Get column names for a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def copy_table(source_conn, target_conn, table_name, config, dry_run=False):
    """
    Copy all rows from a table in source to target using upsert logic.

    Returns (inserted, updated, skipped, errors) counts.
    """
    if not table_exists(source_conn, table_name):
        print(f"  ⚠ Table '{table_name}' not found in source — skipping")
        return 0, 0, 0, 0

    if not table_exists(target_conn, table_name):
        print(f"  ⚠ Table '{table_name}' not found in target — skipping")
        return 0, 0, 0, 0

    source_cols = get_table_columns(source_conn, table_name)
    target_cols = get_table_columns(target_conn, table_name)

    # Only copy columns that exist in both source and target
    common_cols = [c for c in source_cols if c in target_cols]
    if not common_cols:
        print(f"  ⚠ No common columns between source and target for '{table_name}'")
        return 0, 0, 0, 0

    # Read all rows from source
    source_cursor = source_conn.cursor()
    col_list = ", ".join(common_cols)
    source_cursor.execute(f"SELECT {col_list} FROM {table_name}")
    rows = source_cursor.fetchall()

    inserted = updated = skipped = errors = 0
    match_keys = config["match_keys"]
    target_cursor = target_conn.cursor()

    for row in rows:
        row_dict = dict(zip(common_cols, row))

        try:
            # Build match condition
            conditions = []
            params = []
            for key in match_keys:
                if key in row_dict and row_dict[key] is not None:
                    conditions.append(f"{key} = ?")
                    params.append(row_dict[key])

            if not conditions:
                skipped += 1
                continue

            # Check if record exists
            where_clause = " OR ".join(conditions)
            target_cursor.execute(
                f"SELECT id FROM {table_name} WHERE {where_clause}", params
            )
            existing = target_cursor.fetchone()

            if dry_run:
                if existing:
                    updated += 1
                else:
                    inserted += 1
                continue

            # Non-ID columns for insert/update
            data_cols = [c for c in common_cols if c != "id"]

            if existing:
                # Update existing record
                set_clause = ", ".join(f"{c} = ?" for c in data_cols)
                values = [row_dict.get(c) for c in data_cols]
                values.append(existing[0])
                target_cursor.execute(
                    f"UPDATE {table_name} SET {set_clause} WHERE id = ?", values
                )
                updated += 1
            else:
                # Insert new record
                placeholders = ", ".join("?" for _ in data_cols)
                col_names = ", ".join(data_cols)
                values = [row_dict.get(c) for c in data_cols]
                target_cursor.execute(
                    f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                    values,
                )
                inserted += 1

            target_conn.commit()

        except Exception as e:
            target_conn.rollback()
            errors += 1
            print(f"    Error: {e}")

    return inserted, updated, skipped, errors


# ── Main ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Copy app-only data from production to development database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Copy all supported tables
  %(prog)s --tables users bug_reports   Copy specific tables only
  %(prog)s --dry-run                    Preview without writing
  %(prog)s --source instance/prod.db    Use a different source database
        """,
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Source database path (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help=f"Target database path (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        choices=list(SUPPORTED_TABLES.keys()),
        default=list(SUPPORTED_TABLES.keys()),
        help="Tables to copy (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing to the database",
    )
    args = parser.parse_args()

    # Validate paths
    if not os.path.exists(args.source):
        print(f"✗ Source database not found: {args.source}")
        sys.exit(1)
    if not os.path.exists(args.target):
        print(f"✗ Target database not found: {args.target}")
        print("  Run 'flask db upgrade' or 'python app.py' to initialize it first.")
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  Production → Development Data Copy [{mode}]")
    print(f"{'='*60}")
    print(f"  Source: {args.source}")
    print(f"  Target: {args.target}")
    print(f"  Tables: {', '.join(args.tables)}")
    print(f"{'='*60}\n")

    source_conn = sqlite3.connect(args.source)
    source_conn.row_factory = sqlite3.Row
    target_conn = sqlite3.connect(args.target)

    total_inserted = total_updated = total_skipped = total_errors = 0

    for table_name in args.tables:
        config = SUPPORTED_TABLES[table_name]
        print(f"► {table_name} — {config['description']}")

        inserted, updated, skipped, errors = copy_table(
            source_conn, target_conn, table_name, config, dry_run=args.dry_run
        )

        total_inserted += inserted
        total_updated += updated
        total_skipped += skipped
        total_errors += errors

        print(
            f"  ✓ {inserted} inserted, {updated} updated, {skipped} skipped, {errors} errors\n"
        )

    source_conn.close()
    target_conn.close()

    print(f"{'='*60}")
    print(
        f"  Total: {total_inserted} inserted, {total_updated} updated, {total_skipped} skipped, {total_errors} errors"
    )
    if args.dry_run:
        print(f"  (Dry run — no changes were written)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
