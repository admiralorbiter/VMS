"""Add Pathful import models and fields (US-304, US-306)

Revision ID: b7c9d2e4f5a6
Revises: add_tenant_model
Create Date: 2026-01-29 14:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c9d2e4f5a6"
down_revision: Union[str, Sequence[str], None] = "add_tenant_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name, index_name):
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [i["name"] for i in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    """
    Add Pathful import infrastructure:
    - New pathful_import_log table for batch audit
    - New pathful_unmatched_record table for unmatched record review
    - New fields on event table for Pathful integration
    - New fields on teacher_progress and volunteer for Pathful user tracking
    """
    # Create pathful_import_log table if it doesn't exist
    if not table_exists("pathful_import_log"):
        op.create_table(
            "pathful_import_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("import_type", sa.String(length=50), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "imported_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("total_rows", sa.Integer(), default=0),
            sa.Column("processed_rows", sa.Integer(), default=0),
            sa.Column("skipped_rows", sa.Integer(), default=0),
            sa.Column("created_events", sa.Integer(), default=0),
            sa.Column("updated_events", sa.Integer(), default=0),
            sa.Column("matched_teachers", sa.Integer(), default=0),
            sa.Column("created_teachers", sa.Integer(), default=0),
            sa.Column("matched_volunteers", sa.Integer(), default=0),
            sa.Column("created_volunteers", sa.Integer(), default=0),
            sa.Column("unmatched_count", sa.Integer(), default=0),
            sa.Column("error_count", sa.Integer(), default=0),
            sa.Column("error_details", sa.Text(), nullable=True),
        )

    # Create pathful_unmatched_record table if it doesn't exist
    if not table_exists("pathful_unmatched_record"):
        op.create_table(
            "pathful_unmatched_record",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "import_log_id",
                sa.Integer(),
                sa.ForeignKey("pathful_import_log.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("raw_data", sa.JSON(), nullable=False),
            sa.Column("unmatched_type", sa.String(length=50), nullable=False),
            sa.Column("attempted_match_name", sa.String(length=255), nullable=True),
            sa.Column("attempted_match_email", sa.String(length=255), nullable=True),
            sa.Column(
                "attempted_match_session_id", sa.String(length=100), nullable=True
            ),
            sa.Column("attempted_match_school", sa.String(length=255), nullable=True),
            sa.Column(
                "attempted_match_organization", sa.String(length=255), nullable=True
            ),
            sa.Column(
                "resolution_status",
                sa.String(length=50),
                default="pending",
                nullable=False,
            ),
            sa.Column("resolution_notes", sa.Text(), nullable=True),
            sa.Column(
                "resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "resolved_teacher_id",
                sa.Integer(),
                sa.ForeignKey("teacher.id"),
                nullable=True,
            ),
            sa.Column(
                "resolved_volunteer_id",
                sa.Integer(),
                sa.ForeignKey("volunteer.id"),
                nullable=True,
            ),
            sa.Column(
                "resolved_event_id",
                sa.Integer(),
                sa.ForeignKey("event.id"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    # Add Pathful fields to event table (if they don't exist)
    if not column_exists("event", "pathful_session_id"):
        op.add_column(
            "event",
            sa.Column("pathful_session_id", sa.String(length=100), nullable=True),
        )
    if not column_exists("event", "career_cluster"):
        op.add_column(
            "event",
            sa.Column("career_cluster", sa.String(length=255), nullable=True),
        )
    if not column_exists("event", "import_source"):
        op.add_column(
            "event",
            sa.Column("import_source", sa.String(length=50), nullable=True),
        )
    if not column_exists("event", "registered_student_count"):
        op.add_column(
            "event",
            sa.Column("registered_student_count", sa.Integer(), default=0),
        )
    if not column_exists("event", "attended_student_count"):
        op.add_column(
            "event",
            sa.Column("attended_student_count", sa.Integer(), default=0),
        )

    # Create unique index on pathful_session_id if it doesn't exist
    if not index_exists("event", "ix_event_pathful_session_id"):
        op.create_index(
            "ix_event_pathful_session_id",
            "event",
            ["pathful_session_id"],
            unique=True,
        )

    # Add pathful_user_id to teacher_progress
    if not column_exists("teacher_progress", "pathful_user_id"):
        op.add_column(
            "teacher_progress",
            sa.Column("pathful_user_id", sa.String(length=100), nullable=True),
        )
    if not index_exists("teacher_progress", "ix_teacher_progress_pathful_user_id"):
        op.create_index(
            "ix_teacher_progress_pathful_user_id",
            "teacher_progress",
            ["pathful_user_id"],
            unique=False,
        )

    # Add pathful_user_id to volunteer
    if not column_exists("volunteer", "pathful_user_id"):
        op.add_column(
            "volunteer",
            sa.Column("pathful_user_id", sa.String(length=100), nullable=True),
        )
    if not index_exists("volunteer", "ix_volunteer_pathful_user_id"):
        op.create_index(
            "ix_volunteer_pathful_user_id",
            "volunteer",
            ["pathful_user_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove Pathful import infrastructure."""
    # Drop volunteer index and column
    if index_exists("volunteer", "ix_volunteer_pathful_user_id"):
        op.drop_index("ix_volunteer_pathful_user_id", table_name="volunteer")
    if column_exists("volunteer", "pathful_user_id"):
        op.drop_column("volunteer", "pathful_user_id")

    # Drop teacher_progress index and column
    if index_exists("teacher_progress", "ix_teacher_progress_pathful_user_id"):
        op.drop_index(
            "ix_teacher_progress_pathful_user_id", table_name="teacher_progress"
        )
    if column_exists("teacher_progress", "pathful_user_id"):
        op.drop_column("teacher_progress", "pathful_user_id")

    # Drop event index and columns
    if index_exists("event", "ix_event_pathful_session_id"):
        op.drop_index("ix_event_pathful_session_id", table_name="event")
    if column_exists("event", "attended_student_count"):
        op.drop_column("event", "attended_student_count")
    if column_exists("event", "registered_student_count"):
        op.drop_column("event", "registered_student_count")
    if column_exists("event", "import_source"):
        op.drop_column("event", "import_source")
    if column_exists("event", "career_cluster"):
        op.drop_column("event", "career_cluster")
    if column_exists("event", "pathful_session_id"):
        op.drop_column("event", "pathful_session_id")

    # Drop unmatched records table
    if table_exists("pathful_unmatched_record"):
        op.drop_table("pathful_unmatched_record")

    # Drop import log table
    if table_exists("pathful_import_log"):
        op.drop_table("pathful_import_log")
