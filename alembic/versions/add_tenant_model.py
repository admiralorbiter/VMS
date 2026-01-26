"""Add tenant table and user tenant_id

Revision ID: add_tenant_model
Revises:
Create Date: 2026-01-26

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_tenant_model"
down_revision = "80188e1a37e7"  # Previous head migration
branch_labels = None
depends_on = None


def upgrade():
    # Create tenant table
    op.create_table(
        "tenant",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("api_key_hash", sa.String(255), nullable=True),
        sa.Column("api_key_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_origins", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_tenant_slug", "tenant", ["slug"], unique=True)

    # Add tenant_id to users table
    op.add_column("users", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_foreign_key(
        "fk_users_tenant_id", "users", "tenant", ["tenant_id"], ["id"]
    )


def downgrade():
    # Drop foreign key and column from users
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")

    # Drop tenant table
    op.drop_index("ix_tenant_slug", table_name="tenant")
    op.drop_table("tenant")
