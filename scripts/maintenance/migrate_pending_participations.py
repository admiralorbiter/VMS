"""
Migration script to create the pending_participation_imports table.
Run this script to apply the schema changes for TD-057 Phase 2.
"""

import os
import sys

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text

from app import create_app
from models import db


def migrate():
    print("Starting migration to add pending_participation_imports table...")
    app = create_app()
    with app.app_context():
        # Check if table already exists
        result = db.session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_participation_imports'"
            )
        ).fetchone()

        if result:
            print("Table 'pending_participation_imports' already exists. Skipping.")
            return

        # Execute DDL
        db.session.execute(
            text(
                """
            CREATE TABLE pending_participation_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_participation_id VARCHAR(18) NOT NULL UNIQUE,
                sf_contact_id VARCHAR(18),
                sf_session_id VARCHAR(18),
                status VARCHAR(50),
                delivery_hours FLOAT,
                age_group VARCHAR(50),
                email VARCHAR(255),
                title VARCHAR(100),
                first_seen_at DATETIME,
                retry_count INTEGER DEFAULT 0,
                last_retry_at DATETIME,
                resolved_at DATETIME,
                error_reason VARCHAR(200)
            )
        """
            )
        )

        db.session.execute(
            text(
                "CREATE INDEX ix_pending_participation_imports_sf_participation_id ON pending_participation_imports (sf_participation_id)"
            )
        )
        db.session.execute(
            text(
                "CREATE INDEX ix_pending_participation_imports_sf_contact_id ON pending_participation_imports (sf_contact_id)"
            )
        )
        db.session.execute(
            text(
                "CREATE INDEX ix_pending_participation_imports_sf_session_id ON pending_participation_imports (sf_session_id)"
            )
        )

        db.session.commit()
        print("Successfully created pending_participation_imports table and indexes.")


if __name__ == "__main__":
    migrate()
