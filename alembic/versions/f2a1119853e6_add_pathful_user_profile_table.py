"""add_pathful_user_profile_table

Revision ID: f2a1119853e6
Revises: b7c9d2e4f5a6
Create Date: 2026-01-29 19:17:51.970923

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a1119853e6"
down_revision: Union[str, Sequence[str], None] = "b7c9d2e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pathful_user_profile table for User Report imports."""
    op.create_table(
        "pathful_user_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        # Core identity
        sa.Column("pathful_user_id", sa.String(50), nullable=False),
        sa.Column("signup_role", sa.String(20), nullable=False),
        # Name and contact
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("login_email", sa.String(255), nullable=True),
        sa.Column("notification_email", sa.String(255), nullable=True),
        # Organization
        sa.Column("school", sa.String(255), nullable=True),
        sa.Column("district_or_company", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("grade_cluster", sa.String(100), nullable=True),
        # Skills and affiliations
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("affiliations", sa.Text(), nullable=True),
        # Location
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        # Pathful activity metrics
        sa.Column("join_date", sa.DateTime(), nullable=True),
        sa.Column("last_login_date", sa.DateTime(), nullable=True),
        sa.Column("login_count", sa.Integer(), default=0),
        sa.Column("days_logged_in_last_30", sa.Integer(), default=0),
        sa.Column("last_session_date", sa.DateTime(), nullable=True),
        # Subscription info
        sa.Column("subscription_type", sa.String(100), nullable=True),
        sa.Column("subscription_name", sa.String(255), nullable=True),
        # Import tracking
        sa.Column(
            "import_log_id",
            sa.Integer(),
            sa.ForeignKey("pathful_import_log.id"),
            nullable=True,
        ),
        # Links to resolved Polaris records
        sa.Column(
            "teacher_progress_id",
            sa.Integer(),
            sa.ForeignKey("teacher_progress.id"),
            nullable=True,
        ),
        sa.Column(
            "volunteer_id", sa.Integer(), sa.ForeignKey("volunteer.id"), nullable=True
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for common lookups
    op.create_index(
        "ix_pathful_user_profile_pathful_user_id",
        "pathful_user_profile",
        ["pathful_user_id"],
        unique=True,
    )
    op.create_index(
        "ix_pathful_user_profile_login_email",
        "pathful_user_profile",
        ["login_email"],
        unique=False,
    )
    op.create_index(
        "ix_pathful_user_profile_signup_role",
        "pathful_user_profile",
        ["signup_role"],
        unique=False,
    )


def downgrade() -> None:
    """Drop pathful_user_profile table."""
    op.drop_index("ix_pathful_user_profile_signup_role", "pathful_user_profile")
    op.drop_index("ix_pathful_user_profile_login_email", "pathful_user_profile")
    op.drop_index("ix_pathful_user_profile_pathful_user_id", "pathful_user_profile")
    op.drop_table("pathful_user_profile")
