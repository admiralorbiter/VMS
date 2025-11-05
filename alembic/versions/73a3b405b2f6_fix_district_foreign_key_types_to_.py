"""fix_district_foreign_key_types_to_integer

Revision ID: 73a3b405b2f6
Revises: e5801d458e9f
Create Date: 2025-11-05 10:20:56.781885

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "73a3b405b2f6"
down_revision: Union[str, Sequence[str], None] = "e5801d458e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix foreign key type mismatch: district_id should be Integer to match District.id
    # Change event_districts.district_id from String(18) to Integer
    with op.batch_alter_table("event_districts", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.String(18),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    # Change district_year_end_reports.district_id from String(18) to Integer
    with op.batch_alter_table("district_year_end_reports", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.String(18),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    # Change district_engagement_reports.district_id from String(18) to Integer
    with op.batch_alter_table("district_engagement_reports", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.String(18),
            type_=sa.Integer(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert foreign key types back to String(18)
    with op.batch_alter_table("district_engagement_reports", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.Integer(),
            type_=sa.String(18),
            existing_nullable=False,
        )

    with op.batch_alter_table("district_year_end_reports", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.Integer(),
            type_=sa.String(18),
            existing_nullable=False,
        )

    with op.batch_alter_table("event_districts", schema=None) as batch_op:
        batch_op.alter_column(
            "district_id",
            existing_type=sa.Integer(),
            type_=sa.String(18),
            existing_nullable=False,
        )
