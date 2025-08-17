"""fix_volunteer_organization_timestamps_for_sqlite

Revision ID: 14962ffc3069
Revises: d9dd0eb34119
Create Date: 2025-08-17 09:56:43.682947

"""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "14962ffc3069"
down_revision = "d9dd0eb34119"
branch_labels = None
depends_on = None


def upgrade():
    # For SQLite, we need to recreate the table to change column defaults
    # First, create a new table with the correct schema
    op.create_table(
        "volunteer_organization_new",
        sa.Column("volunteer_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("salesforce_volunteer_id", sa.String(length=18), nullable=True),
        sa.Column("salesforce_org_id", sa.String(length=18), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), default=False),
        sa.Column("status", sa.String(length=50), default="Current"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            default=datetime.utcnow,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["volunteer_id"], ["volunteer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("volunteer_id", "organization_id"),
    )

    # Copy data from old table to new table
    op.execute(
        """
        INSERT INTO volunteer_organization_new
        (volunteer_id, organization_id, salesforce_volunteer_id, salesforce_org_id,
         role, start_date, end_date, is_primary, status, created_at, updated_at)
        SELECT
            volunteer_id, organization_id, salesforce_volunteer_id, salesforce_org_id,
            role, start_date, end_date, is_primary, status,
            COALESCE(created_at, datetime('now')) as created_at,
            COALESCE(updated_at, datetime('now')) as updated_at
        FROM volunteer_organization
    """
    )

    # Drop old table and rename new table
    op.drop_table("volunteer_organization")
    op.rename_table("volunteer_organization_new", "volunteer_organization")

    # Recreate indexes
    op.create_index(
        op.f("ix_volunteer_organization_organization_id"),
        "volunteer_organization",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_volunteer_organization_salesforce_org_id"),
        "volunteer_organization",
        ["salesforce_org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_volunteer_organization_salesforce_volunteer_id"),
        "volunteer_organization",
        ["salesforce_volunteer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_volunteer_organization_volunteer_id"),
        "volunteer_organization",
        ["volunteer_id"],
        unique=False,
    )


def downgrade():
    # Revert to the old schema if needed
    # Note: This is a destructive operation that will lose data
    pass
