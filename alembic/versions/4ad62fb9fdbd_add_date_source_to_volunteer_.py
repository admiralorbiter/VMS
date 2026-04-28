"""add date_source to volunteer_organization and add index

Revision ID: 4ad62fb9fdbd
Revises: 19c9840f1b3c
Create Date: 2026-04-28 10:41:57.819781

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ad62fb9fdbd"
down_revision: Union[str, Sequence[str], None] = "19c9840f1b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "volunteer_organization",
        sa.Column("date_source", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "idx_vo_status_dates",
        "volunteer_organization",
        ["status", "start_date", "end_date"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_vo_status_dates", table_name="volunteer_organization")
    op.drop_column("volunteer_organization", "date_source")
