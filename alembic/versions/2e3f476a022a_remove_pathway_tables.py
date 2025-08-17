"""remove_pathway_tables

Revision ID: 2e3f476a022a
Revises: 995318528785
Create Date: 2025-08-17 12:49:02.545379

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e3f476a022a"
down_revision: Union[str, Sequence[str], None] = "995318528785"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Remove unused pathway tables."""
    # Drop pathway-related tables that are no longer needed
    # These tables were part of the old pathways system that has been removed

    # Drop pathway_contacts table
    op.drop_table("pathway_contacts")

    # Drop pathway_events table
    op.drop_table("pathway_events")


def downgrade() -> None:
    """Downgrade schema - Recreate pathway tables (not recommended)."""
    # Note: This downgrade is not recommended as the pathways system has been removed
    # The tables would be empty and have no associated functionality

    # Recreate pathway_contacts table (basic structure)
    op.create_table(
        "pathway_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pathway_id", sa.Integer(), nullable=True),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate pathway_events table (basic structure)
    op.create_table(
        "pathway_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pathway_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
