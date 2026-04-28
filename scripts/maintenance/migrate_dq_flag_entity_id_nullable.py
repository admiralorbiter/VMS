"""
Migration: Make data_quality_flag.entity_id nullable (Bug 1 fix)

SF-origin flags (entity_sf_id IS NOT NULL) have no local integer entity,
so they previously used the sentinel value 0. This allows NULL instead,
which is semantically correct and avoids false uniqueness collisions on
the (entity_type, entity_id, issue_type) unique constraint.

Run: python scripts/maintenance/migrate_dq_flag_entity_id_nullable.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text

from app import create_app
from models import db


def run_migration():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # SQLite cannot ALTER COLUMN to change nullability.
            # We need to rebuild the table.
            print("Migrating data_quality_flag.entity_id to nullable...")

            # Check current schema
            result = conn.execute(
                text("PRAGMA table_info(data_quality_flag)")
            ).fetchall()
            cols = {row[1]: row for row in result}

            if "entity_id" not in cols:
                print("Column entity_id not found - skipping")
                return

            # SQLite approach: rename -> create -> copy -> drop old
            conn.execute(text("ALTER TABLE data_quality_flag RENAME TO _dqf_old"))

            # Create new table with entity_id nullable
            conn.execute(
                text(
                    """
                CREATE TABLE data_quality_flag (
                    id INTEGER NOT NULL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id INTEGER,
                    issue_type VARCHAR(50) NOT NULL,
                    details TEXT,
                    salesforce_id VARCHAR(18),
                    entity_sf_id VARCHAR(18),
                    status VARCHAR(20) NOT NULL DEFAULT 'open',
                    created_at DATETIME NOT NULL,
                    resolved_at DATETIME,
                    resolved_by INTEGER REFERENCES users(id),
                    resolution_notes TEXT,
                    UNIQUE (entity_type, entity_id, issue_type)
                )
            """
                )
            )

            # Recreate indexes
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_entity_type ON data_quality_flag (entity_type)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_entity_id ON data_quality_flag (entity_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_issue_type ON data_quality_flag (issue_type)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_salesforce_id ON data_quality_flag (salesforce_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_entity_sf_id ON data_quality_flag (entity_sf_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_dqf_status ON data_quality_flag (status)"
                )
            )

            # Copy data, converting sentinel 0 to NULL for SF-origin flags
            conn.execute(
                text(
                    """
                INSERT INTO data_quality_flag
                SELECT
                    id,
                    entity_type,
                    CASE WHEN entity_sf_id IS NOT NULL AND entity_id = 0 THEN NULL ELSE entity_id END,
                    issue_type,
                    details,
                    salesforce_id,
                    entity_sf_id,
                    status,
                    created_at,
                    resolved_at,
                    resolved_by,
                    resolution_notes
                FROM _dqf_old
            """
                )
            )

            # Drop old table
            conn.execute(text("DROP TABLE _dqf_old"))
            conn.commit()

            print(
                "Done. entity_id is now nullable; existing sentinel-0 SF flags converted to NULL."
            )


if __name__ == "__main__":
    run_migration()
