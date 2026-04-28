"""
Migration: Add recovery_buffer_hours to sync_logs (TD-055)

Adds a column to track how many hours of lookback buffer the next
delta sync should apply when reading this watermark. Default 1 (normal),
48 after a failed sync to catch records in the gap.

Run: python scripts/maintenance/migrate_sync_log_recovery_buffer.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text

from app import create_app
from models import db


def run_migration():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(sync_logs)")).fetchall()
            cols = [row[1] for row in result]

            if "recovery_buffer_hours" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE sync_logs ADD COLUMN recovery_buffer_hours INTEGER NOT NULL DEFAULT 1"
                    )
                )
                conn.commit()
                print("✅ Added recovery_buffer_hours column to sync_logs (default: 1)")
            else:
                print("ℹ Column already exists — skipping")


if __name__ == "__main__":
    run_migration()
