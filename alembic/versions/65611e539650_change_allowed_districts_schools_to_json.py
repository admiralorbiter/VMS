"""change_allowed_districts_schools_to_json

Revision ID: 65611e539650
Revises: 3c47e3e6ff2b
Create Date: 2025-10-31 22:58:11.367252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65611e539650'
down_revision: Union[str, Sequence[str], None] = '3c47e3e6ff2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add allowed_schools column as JSON
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allowed_schools', sa.JSON(), nullable=True))
        # Convert allowed_districts from Text to JSON
        batch_op.alter_column('allowed_districts',
                              existing_type=sa.Text(),
                              type_=sa.JSON(),
                              existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Convert back to Text and remove allowed_schools
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Convert allowed_districts back to Text
        batch_op.alter_column('allowed_districts',
                              existing_type=sa.JSON(),
                              type_=sa.Text(),
                              existing_nullable=True)
        # Drop allowed_schools column
        batch_op.drop_column('allowed_schools')
