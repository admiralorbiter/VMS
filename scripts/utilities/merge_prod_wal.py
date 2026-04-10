#!/usr/bin/env python
"""
Merge SQLite WAL File Utility
=============================

This script safely merges a Write-Ahead Log (.db-wal) file into its main SQLite 
database (.db) file. This is useful when downloading raw database files from 
a production environment where the server was actively running.

Usage:
    python scripts/utilities/merge_prod_wal.py instance/prod/your_database.db
"""

import argparse
import os
import sqlite3
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Merge SQLite .db-wal file into the main .db file.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "db_path", 
        help="Path to the main .db file (the .db-wal must be in the same directory)"
    )
    
    args = parser.parse_args()
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

    print(f"[+] Found WAL file '{os.path.basename(wal_path)}' ({wal_size / 1024:.2f} KB)")
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
        print(f"[*] Checkpoint result: {result} (0=OK, 1=Busy, 2=Checkpoint OK, 3=Restarted)")

        # Verify new file sizes
        if os.path.exists(wal_path) and os.path.getsize(wal_path) == 0:
            print("[+] The WAL file has been successfully merged and truncated to 0 bytes.")
            print("[*] Note: You can now safely delete the .db-wal and .db-shm files if desired.")
        else:
            print("[-] Warning: The WAL file might not have fully truncated. Check file sizes.")

    except sqlite3.Error as e:
        print(f"[!] SQLite Error during merge: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
