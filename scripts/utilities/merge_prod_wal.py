#!/usr/bin/env python
"""
Merge SQLite WAL File Utility
=============================

This script safely merges a Write-Ahead Log (.db-wal) file into its main SQLite
database (.db) file. This is useful when downloading raw database files from
a production environment where the server was actively running.

Usage:
    python scripts/utilities/merge_prod_wal.py                  # auto-detects DB in instance/prod/
    python scripts/utilities/merge_prod_wal.py instance/prod/your_database.db
"""

import argparse
import os
import sqlite3
import sys

# Default search directory relative to the repo root (where this script is typically run from)
_DEFAULT_PROD_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "instance", "prod"
)


def _find_default_db(prod_dir: str) -> str:
    """Auto-discover the single .db file in the default prod directory."""
    candidates = [
        f
        for f in os.listdir(prod_dir)
        if f.endswith(".db") and not f.endswith("-wal") and not f.endswith("-shm")
    ]
    if len(candidates) == 0:
        print(f"[!] No .db file found in '{prod_dir}'. Please pass db_path explicitly.")
        sys.exit(1)
    if len(candidates) > 1:
        print(f"[!] Multiple .db files found in '{prod_dir}': {candidates}")
        print("[!] Please pass db_path explicitly to avoid ambiguity.")
        sys.exit(1)
    return os.path.abspath(os.path.join(prod_dir, candidates[0]))


def main():
    parser = argparse.ArgumentParser(
        description="Merge SQLite .db-wal file into the main .db file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        default=None,
        help="Path to the main .db file (the .db-wal must be in the same directory). "
        "Defaults to the single .db file found in instance/prod/.",
    )

    args = parser.parse_args()

    if args.db_path is None:
        prod_dir = os.path.abspath(_DEFAULT_PROD_DIR)
        print(f"[*] No db_path provided — auto-detecting in '{prod_dir}' ...")
        db_path = _find_default_db(prod_dir)
        print(f"[*] Found: {db_path}")
    else:
        db_path = os.path.abspath(args.db_path)

    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.")
        sys.exit(1)

    print(f"[*] Analyzing: {db_path}")
    wal_path = f"{db_path}-wal"
    shm_path = f"{db_path}-shm"

    if not os.path.exists(wal_path):
        print(f"[-] No WAL file found at '{wal_path}'.")
        print("[*] No merge necessary. The database is already consolidated.")
        sys.exit(0)

    wal_size = os.path.getsize(wal_path)
    if wal_size == 0:
        print("[*] WAL file exists but is empty (0 bytes). No merge necessary.")
        sys.exit(0)

    print(
        f"[+] Found WAL file '{os.path.basename(wal_path)}' ({wal_size / 1024:.2f} KB)"
    )
    print("[*] Connecting and forcing SQLite checkpoint to merge WAL data...")

    try:
        # Connecting automatically detects -wal and -shm in the same directory
        con = sqlite3.connect(db_path)
        cursor = con.cursor()

        # PRAGMA wal_checkpoint(TRUNCATE) moves everything to .db and resets the WAL file.
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        result = cursor.fetchone()
        con.close()

        print("[+] Optimization complete!")
        print(
            f"[*] Checkpoint result: {result} (0=OK, 1=Busy, 2=Checkpoint OK, 3=Restarted)"
        )

        # Verify new file sizes
        if os.path.exists(wal_path) and os.path.getsize(wal_path) == 0:
            print(
                "[+] The WAL file has been successfully merged and truncated to 0 bytes."
            )
            print(
                "[*] Note: You can now safely delete the .db-wal and .db-shm files if desired."
            )
        else:
            print(
                "[-] Warning: The WAL file might not have fully truncated. Check file sizes."
            )

    except sqlite3.Error as e:
        print(f"[!] SQLite Error during merge: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
