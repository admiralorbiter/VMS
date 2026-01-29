"""add email tables

Revision ID: a1b2c3d4e5f6
Revises: 3c47e3e6ff2b
Create Date: 2026-01-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "cde2c27b7e84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_templates, email_messages, and email_delivery_attempts tables."""

    # Create email_templates table
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purpose_key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_template", sa.Text(), nullable=False),
        sa.Column("html_template", sa.Text(), nullable=False),
        sa.Column("text_template", sa.Text(), nullable=False),
        sa.Column("required_placeholders", sa.JSON(), nullable=True),
        sa.Column("optional_placeholders", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_templates_purpose_key"),
        "email_templates",
        ["purpose_key"],
        unique=False,
    )

    # Create email_messages table
    op.create_table(
        "email_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("recipients", sa.JSON(), nullable=False),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("excluded_recipients", sa.JSON(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_checks", sa.JSON(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("context_metadata", sa.JSON(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["email_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_messages_status"), "email_messages", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_email_messages_created_at"),
        "email_messages",
        ["created_at"],
        unique=False,
    )

    # Create email_delivery_attempts table
    op.create_table(
        "email_delivery_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mailjet_message_id", sa.String(length=100), nullable=True),
        sa.Column("mailjet_response", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("provider_payload_summary", sa.JSON(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_dry_run", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["email_messages.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_delivery_attempts_status"),
        "email_delivery_attempts",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_delivery_attempts_mailjet_message_id"),
        "email_delivery_attempts",
        ["mailjet_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_delivery_attempts_attempted_at"),
        "email_delivery_attempts",
        ["attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop email tables."""
    op.drop_index(
        op.f("ix_email_delivery_attempts_attempted_at"),
        table_name="email_delivery_attempts",
    )
    op.drop_index(
        op.f("ix_email_delivery_attempts_mailjet_message_id"),
        table_name="email_delivery_attempts",
    )
    op.drop_index(
        op.f("ix_email_delivery_attempts_status"), table_name="email_delivery_attempts"
    )
    op.drop_table("email_delivery_attempts")
    op.drop_index(op.f("ix_email_messages_created_at"), table_name="email_messages")
    op.drop_index(op.f("ix_email_messages_status"), table_name="email_messages")
    op.drop_table("email_messages")
    op.drop_index(op.f("ix_email_templates_purpose_key"), table_name="email_templates")
    op.drop_table("email_templates")
