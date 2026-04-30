"""add_entity_sf_id_and_pending_participation_imports

Revision ID: 334af5895d87
Revises: 4ad62fb9fdbd
Create Date: 2026-04-29 09:51:57.389183

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "334af5895d87"
down_revision: Union[str, Sequence[str], None] = "4ad62fb9fdbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pending_participation_imports table
    op.create_table(
        "pending_participation_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sf_participation_id", sa.String(length=18), nullable=False),
        sa.Column("sf_contact_id", sa.String(length=18), nullable=True),
        sa.Column("sf_session_id", sa.String(length=18), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("delivery_hours", sa.Float(), nullable=True),
        sa.Column("age_group", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_reason", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("pending_participation_imports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_pending_participation_imports_sf_contact_id"),
            ["sf_contact_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_pending_participation_imports_sf_participation_id"),
            ["sf_participation_id"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_pending_participation_imports_sf_session_id"),
            ["sf_session_id"],
            unique=False,
        )

    # Add entity_sf_id to data_quality_flag and update constraint
    with op.batch_alter_table("data_quality_flag", schema=None) as batch_op:
        # We use a batch operation to add the column
        batch_op.add_column(
            sa.Column("entity_sf_id", sa.String(length=18), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_data_quality_flag_entity_sf_id"),
            ["entity_sf_id"],
            unique=False,
        )
        # Drop the old unique constraint and create a new one that includes entity_sf_id (SQLite handles this via table recreation under the hood)
        batch_op.drop_constraint("uix_dqf_entity_issue", type_="unique")
        batch_op.create_unique_constraint(
            "uix_dqf_entity_issue",
            ["entity_type", "entity_id", "entity_sf_id", "issue_type"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("data_quality_flag", schema=None) as batch_op:
        batch_op.drop_constraint("uix_dqf_entity_issue", type_="unique")
        batch_op.create_unique_constraint(
            "uix_dqf_entity_issue", ["entity_type", "entity_id", "issue_type"]
        )
        batch_op.drop_index(batch_op.f("ix_data_quality_flag_entity_sf_id"))
        batch_op.drop_column("entity_sf_id")

    with op.batch_alter_table("pending_participation_imports", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_pending_participation_imports_sf_session_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_pending_participation_imports_sf_participation_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_pending_participation_imports_sf_contact_id")
        )
    op.drop_table("pending_participation_imports")
