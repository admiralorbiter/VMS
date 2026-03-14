"""fix_known_schema_drifts

Drop orphaned connector_data table (TD-034) and widen skill.name
from VARCHAR(50) to VARCHAR(200) (TD-034).

Revision ID: fix_known_drifts
Revises: 9418fc9979cf
Create Date: 2026-03-13 22:12:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3_fix_drifts"
down_revision: Union[str, Sequence[str], None] = "9418fc9979cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix two known schema drifts from TD-034.

    1. Drop the orphaned connector_data table (model removed, table remains)
    2. Widen skill.name from VARCHAR(50) to VARCHAR(200) (model updated, column not)

    Both operations are safe and non-destructive to active data:
    - connector_data has no code references (ConnectorData model was deleted)
    - skill.name widening is backwards-compatible (no data loss)
    """
    # 1. Drop connector_data if it exists (safe — no model references it)
    # Use batch mode for SQLite compatibility
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "connector_data" in inspector.get_table_names():
        # Drop indexes first
        with op.batch_alter_table("connector_data", schema=None) as batch_op:
            try:
                batch_op.drop_index("ix_connector_data_active_subscription")
            except Exception:
                pass  # Index may not exist
        op.drop_table("connector_data")

    # 2. Widen skill.name from 50 → 200
    if "skill" in inspector.get_table_names():
        with op.batch_alter_table("skill", schema=None) as batch_op:
            batch_op.alter_column(
                "name",
                existing_type=sa.VARCHAR(length=50),
                type_=sa.String(length=200),
                existing_nullable=False,
            )


def downgrade() -> None:
    """Reverse the drift fixes (not recommended)."""
    # Re-narrow skill.name (may truncate data!)
    with op.batch_alter_table("skill", schema=None) as batch_op:
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=200),
            type_=sa.VARCHAR(length=50),
            existing_nullable=False,
        )

    # Re-create connector_data (empty)
    op.create_table(
        "connector_data",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("volunteer_id", sa.INTEGER(), nullable=False),
        sa.Column("user_auth_id", sa.VARCHAR(length=7), nullable=True),
        sa.Column("joining_date", sa.VARCHAR(length=50), nullable=True),
        sa.Column("last_login_datetime", sa.VARCHAR(length=50), nullable=True),
        sa.Column("last_update_date", sa.DATE(), nullable=True),
        sa.Column("active_subscription", sa.VARCHAR(length=8), nullable=True),
        sa.Column("active_subscription_name", sa.VARCHAR(length=255), nullable=True),
        sa.Column("role", sa.VARCHAR(length=20), nullable=True),
        sa.Column("signup_role", sa.VARCHAR(length=20), nullable=True),
        sa.Column("profile_link", sa.VARCHAR(length=1300), nullable=True),
        sa.Column("affiliations", sa.TEXT(), nullable=True),
        sa.Column("industry", sa.VARCHAR(length=255), nullable=True),
        sa.Column("created_at", sa.DATETIME(), nullable=True),
        sa.Column("updated_at", sa.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(
            ["volunteer_id"],
            ["volunteer.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("connector_data", schema=None) as batch_op:
        batch_op.create_index(
            "ix_connector_data_active_subscription",
            ["active_subscription"],
            unique=False,
        )
