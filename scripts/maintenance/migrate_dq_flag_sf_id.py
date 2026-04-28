"""
Migration: Add entity_sf_id to data_quality_flag (TD-056)

Adds a text column for Salesforce-origin flags where no local integer
entity ID exists. Existing flags (entity_type: 'contact', 'organization', etc.)
are unaffected — they continue to use entity_id (Integer).

Run: python scripts/maintenance/migrate_dq_flag_sf_id.py
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
            result = conn.execute(
                text("PRAGMA table_info(data_quality_flag)")
            ).fetchall()
            cols = [row[1] for row in result]

            if "entity_sf_id" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE data_quality_flag ADD COLUMN entity_sf_id VARCHAR(18)"
                    )
                )
                # Add index (SQLite supports CREATE INDEX on existing tables)
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_dqf_entity_sf_id "
                        "ON data_quality_flag (entity_sf_id)"
                    )
                )
                conn.commit()
                print("✅ Added entity_sf_id column + index to data_quality_flag")
            else:
                print("ℹ Column already exists — skipping")


if __name__ == "__main__":
    run_migration()
