#!/usr/bin/env python3
"""
Database Comparison Utility
===========================

Compares the table schemas and row counts between two SQLite databases.
Useful for validating migrations, checking data drift between production
and local environments, and ensuring no data loss occurred during refactors.

Usage:
    python scripts/maintenance/compare_databases.py [db1_path] [db2_path]

Example:
    python scripts/maintenance/compare_databases.py instance/prod/your_database.db instance/your_database.db
"""

import argparse
import os
import sqlite3
import sys


def get_table_counts(db_path):
    """Returns a dictionary of {table_name: row_count} for the given SQLite database."""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at '{db_path}'")
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all user tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [row[0] for row in cursor.fetchall()]

        counts = {}
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass

        conn.close()
        return counts
    except Exception as e:
        print(f"Error reading {db_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Compare row counts between two SQLite databases"
    )
    parser.add_argument(
        "db1",
        nargs="?",
        default="instance/prod/your_database.db",
        help="Path to the first database (Prod)",
    )
    parser.add_argument(
        "db2",
        nargs="?",
        default="instance/your_database.db",
        help="Path to the second database (Local)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all tables, even those with matching row counts",
    )

    parser.add_argument(
        "--ignore-logs",
        action="store_true",
        help="Ignore log tables and caches that naturally drift",
    )

    args = parser.parse_args()

    print(f"\nComparing Databases:")
    print(f" DB 1: {args.db1}")
    print(f" DB 2: {args.db2}")
    print("-" * 85)

    counts1 = get_table_counts(args.db1)
    counts2 = get_table_counts(args.db2)

    if counts1 is None or counts2 is None:
        sys.exit(1)

    all_tables = sorted(set(list(counts1.keys()) + list(counts2.keys())))

    LOG_TABLES = [
        "audit_log",
        "sync_logs",
        "pathful_import_log",
        "roster_import_log",
        "bug_reports",
        "email_delivery_attempts",
        "pathful_unmatched_record",
        "email_messages",
        "validation_runs",
        "validation_history",
        "validation_results",
        "alembic_version",
    ]

    CORE_TABLES = [
        "volunteer",
        "teacher",
        "organization",
        "event",
        "student",
        "school",
        "district",
        "contact",
    ]

    def get_category(curr_table):
        if curr_table in LOG_TABLES or "cache" in curr_table:
            return "Low Importance (Logs & Caches)"
        if curr_table in CORE_TABLES:
            return "High Importance (Core Data)"
        return "Medium Importance (Linkages & Attributes)"

    categories = {
        "High Importance (Core Data)": [],
        "Medium Importance (Linkages & Attributes)": [],
        "Low Importance (Logs & Caches)": [],
    }

    for table in all_tables:
        if args.ignore_logs and (table in LOG_TABLES or "cache" in table):
            continue

        c1 = counts1.get(table, 0)
        c2 = counts2.get(table, 0)
        diff = c1 - c2
        diff_str = f"{diff:+d}" if diff != 0 else ""

        # Calculate Percentage Drift
        pct_str = ""
        if diff != 0:
            if c1 == 0:
                pct_str = "(100.0%)"
            else:
                pct_drift = (abs(diff) / c1) * 100
                pct_str = f"({pct_drift:.1f}%)"

        if diff != 0 or args.all:
            categories[get_category(table)].append((table, c1, c2, diff_str, pct_str))

    differences_found = False

    for category_name, current_tables in categories.items():
        if not current_tables:
            continue

        differences_found = True
        print(f"\n[{category_name}]")
        print(
            f"{'Table Name':<35} | {'DB 1 Count':<10} | {'DB 2 Count':<10} | {'Diff':<8} | {'Drift %'}"
        )
        print("-" * 85)
        for t, c1, c2, d_str, p_str in current_tables:
            print(f"{t:<35} | {c1:<10} | {c2:<10} | {d_str:<8} | {p_str}")

    if not differences_found:
        print(
            "\nBoth databases have the exact same number of rows across all tables checked."
        )
    elif not args.all:
        print("-" * 85)
        print(
            "Note: Showing only tables with row count differences. Use --all to see everything."
        )

    # Check for missing tables
    missing_in_db1 = [t for t in all_tables if t not in counts1]
    missing_in_db2 = [t for t in all_tables if t not in counts2]

    if missing_in_db1 or missing_in_db2:
        print("\nSchema Differences (Missing Tables):")
        for table in missing_in_db1:
            print(f" - '{table}' exists in DB 2 but is missing from DB 1")
        for table in missing_in_db2:
            print(f" - '{table}' exists in DB 1 but is missing from DB 2")


if __name__ == "__main__":
    main()
