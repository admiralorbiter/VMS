"""add_teacher_id_to_teacher_progress

Revision ID: cde2c27b7e84
Revises: 3c47e3e6ff2b
Create Date: 2026-01-12 10:26:45.294550

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cde2c27b7e84"
down_revision: Union[str, Sequence[str], None] = "3c47e3e6ff2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add teacher_id column to teacher_progress table."""
    # Check if column already exists (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("teacher_progress")]

    if "teacher_id" not in columns:
        # Use batch mode for SQLite compatibility
        with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
            batch_op.add_column(sa.Column("teacher_id", sa.Integer(), nullable=True))
            # Note: SQLite doesn't support foreign key constraints via ALTER TABLE
            # The foreign key relationship is handled at the application level
            # For SQLite, we'll just add the column without the constraint


def downgrade() -> None:
    """Remove teacher_id column from teacher_progress table."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
        batch_op.drop_column("teacher_id")
