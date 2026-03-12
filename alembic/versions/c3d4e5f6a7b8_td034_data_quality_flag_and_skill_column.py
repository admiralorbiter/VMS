"""td034_data_quality_flag_and_skill_column

Revision ID: c3d4e5f6a7b8
Revises: aea77c3ec7e8
Create Date: 2026-03-12 07:30:00.000000

TD-034: Create data_quality_flag table and widen skill.name column.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "aea77c3ec7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create data_quality_flag table and widen skill.name."""
    # --- 1. Create data_quality_flag table ---
    op.create_table(
        "data_quality_flag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("salesforce_id", sa.String(18), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "issue_type", name="uix_dqf_entity_issue"
        ),
    )

    # Indexes for common lookups
    op.create_index(
        "ix_dqf_entity_type", "data_quality_flag", ["entity_type"], unique=False
    )
    op.create_index(
        "ix_dqf_entity_id", "data_quality_flag", ["entity_id"], unique=False
    )
    op.create_index(
        "ix_dqf_issue_type", "data_quality_flag", ["issue_type"], unique=False
    )
    op.create_index("ix_dqf_status", "data_quality_flag", ["status"], unique=False)
    op.create_index(
        "ix_dqf_salesforce_id",
        "data_quality_flag",
        ["salesforce_id"],
        unique=False,
    )

    # --- 2. Widen skill.name from VARCHAR(50) to VARCHAR(200) ---
    with op.batch_alter_table("skill") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(50),
            type_=sa.String(200),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Drop data_quality_flag table and shrink skill.name back."""
    # Shrink skill.name back
    with op.batch_alter_table("skill") as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(200),
            type_=sa.String(50),
            existing_nullable=False,
        )

    # Drop data_quality_flag
    op.drop_index("ix_dqf_salesforce_id", "data_quality_flag")
    op.drop_index("ix_dqf_status", "data_quality_flag")
    op.drop_index("ix_dqf_issue_type", "data_quality_flag")
    op.drop_index("ix_dqf_entity_id", "data_quality_flag")
    op.drop_index("ix_dqf_entity_type", "data_quality_flag")
    op.drop_table("data_quality_flag")
