"""add delta sync watermark to sync_logs

Revision ID: d4e5f6a7b8c9
Revises: 3c47e3e6ff2b
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "f2a1119853e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add delta sync watermark and is_delta_sync columns to sync_logs table."""
    # Check if columns exist before adding (makes migration idempotent)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [c['name'] for c in inspector.get_columns('sync_logs')]
    
    # Add last_sync_watermark column for tracking the timestamp for delta syncs
    if 'last_sync_watermark' not in existing_columns:
        op.add_column(
            "sync_logs",
            sa.Column("last_sync_watermark", sa.DateTime(timezone=True), nullable=True),
        )

    # Add is_delta_sync column to track whether this was a delta or full sync
    if 'is_delta_sync' not in existing_columns:
        op.add_column(
            "sync_logs",
            sa.Column("is_delta_sync", sa.Boolean(), nullable=True, server_default="0"),
        )


def downgrade() -> None:
    """Remove delta sync columns from sync_logs table."""
    op.drop_column("sync_logs", "is_delta_sync")
    op.drop_column("sync_logs", "last_sync_watermark")
