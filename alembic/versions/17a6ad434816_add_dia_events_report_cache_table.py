"""add_dia_events_report_cache_table

Revision ID: 17a6ad434816
Revises: 2e3f476a022a
Create Date: 2025-10-14 12:36:28.904193

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "17a6ad434816"
down_revision: Union[str, Sequence[str], None] = "2e3f476a022a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create DIA Events Report Cache table
    op.create_table(
        "dia_events_report_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop DIA Events Report Cache table
    op.drop_table("dia_events_report_cache")
