"""add_recovery_buffer_hours_to_sync_logs

Backfills the missing migration for sync_logs.recovery_buffer_hours.
This column exists in the model (models/sync_log.py:64) and in the local
dev database, but was never added to any Alembic migration file, so it
is absent from prod.

Revision ID: 1eb5f270181b
Revises: 4ad62fb9fdbd
Create Date: 2026-05-03 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1eb5f270181b"
down_revision: Union[str, Sequence[str], None] = (
    "4ad62fb9fdbd"  # inserts between date_source and entity_sf_id
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add recovery_buffer_hours to sync_logs."""
    with op.batch_alter_table("sync_logs", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "recovery_buffer_hours",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )


def downgrade() -> None:
    """Remove recovery_buffer_hours from sync_logs."""
    with op.batch_alter_table("sync_logs", schema=None) as batch_op:
        batch_op.drop_column("recovery_buffer_hours")
