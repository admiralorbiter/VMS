"""add user district scoping columns

Revision ID: 3c47e3e6ff2b
Revises: 17a6ad434816
Create Date: 2025-10-27 11:25:54.826927

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c47e3e6ff2b"
down_revision: Union[str, Sequence[str], None] = "17a6ad434816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add district scoping columns to users table."""
    # Add allowed_districts column (nullable TEXT field)
    op.add_column("users", sa.Column("allowed_districts", sa.Text(), nullable=True))

    # Add scope_type column with default 'global' and NOT NULL constraint
    op.add_column(
        "users",
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="global"),
    )

    # Migrate existing KCK viewers (security_level = -1) to district-scoped users
    op.execute(
        """
        UPDATE users
        SET scope_type = 'district',
            allowed_districts = '["Kansas City Kansas Public Schools"]'
        WHERE security_level = -1
    """
    )


def downgrade() -> None:
    """Remove district scoping columns from users table."""
    # Remove the new columns
    op.drop_column("users", "scope_type")
    op.drop_column("users", "allowed_districts")
