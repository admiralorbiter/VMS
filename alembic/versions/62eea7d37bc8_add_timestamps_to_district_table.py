"""add_timestamps_to_district_table

Revision ID: 62eea7d37bc8
Revises: 73a3b405b2f6
Create Date: 2025-11-05 10:22:58.740397

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62eea7d37bc8"
down_revision: Union[str, Sequence[str], None] = "73a3b405b2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add created_at and updated_at timestamp columns to district table
    # For SQLite compatibility, we'll add columns and set defaults for existing rows

    # Step 1: Add columns as nullable first (to allow existing rows)
    with op.batch_alter_table("district", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Step 2: Set default values for existing rows
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
        UPDATE district
        SET created_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL OR updated_at IS NULL
    """
        )
    )

    # Step 3: Make columns NOT NULL now that all rows have values
    with op.batch_alter_table("district", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )

    # Note: onupdate behavior for updated_at is handled by SQLAlchemy in application code


def downgrade() -> None:
    """Downgrade schema."""
    # Remove timestamp columns from district table
    with op.batch_alter_table("district", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
