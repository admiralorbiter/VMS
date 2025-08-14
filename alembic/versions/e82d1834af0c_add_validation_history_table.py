"""add_validation_history_table

Revision ID: e82d1834af0c
Revises: ab2125810e2c
Create Date: 2025-08-14 15:57:06.581727

"""

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from alembic import op

# revision identifiers, used by Alembic.
revision = "e82d1834af0c"
down_revision = "ab2125810e2c"
branch_labels = None
depends_on = None


def upgrade():
    # Create validation_history table
    op.create_table(
        "validation_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("validation_type", sa.String(length=50), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("quality_score_raw", sa.Float(), nullable=True),
        sa.Column("quality_threshold", sa.Float(), nullable=True),
        sa.Column("violation_counts", sa.JSON(), nullable=False),
        sa.Column("total_violations", sa.Integer(), nullable=False),
        sa.Column("critical_violations", sa.Integer(), nullable=False),
        sa.Column("error_violations", sa.Integer(), nullable=False),
        sa.Column("warning_violations", sa.Integer(), nullable=False),
        sa.Column("info_violations", sa.Integer(), nullable=False),
        sa.Column("total_checks", sa.Integer(), nullable=False),
        sa.Column("passed_checks", sa.Integer(), nullable=False),
        sa.Column("failed_checks", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
        sa.Column("memory_usage_mb", sa.Float(), nullable=True),
        sa.Column("cpu_usage_percent", sa.Float(), nullable=True),
        sa.Column("metrics_summary", sa.JSON(), nullable=True),
        sa.Column("field_completeness", sa.Float(), nullable=True),
        sa.Column("data_type_accuracy", sa.Float(), nullable=True),
        sa.Column("relationship_integrity", sa.Float(), nullable=True),
        sa.Column("business_rule_compliance", sa.Float(), nullable=True),
        sa.Column("trend_data", sa.JSON(), nullable=True),
        sa.Column("trend_direction", sa.String(length=20), nullable=True),
        sa.Column("trend_magnitude", sa.Float(), nullable=True),
        sa.Column("trend_confidence", sa.Float(), nullable=True),
        sa.Column("is_anomaly", sa.Integer(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("anomaly_type", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_metadata", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "idx_validation_history_entity_timestamp",
        "validation_history",
        ["entity_type", "timestamp"],
    )
    op.create_index(
        "idx_validation_history_type_timestamp",
        "validation_history",
        ["validation_type", "timestamp"],
    )
    op.create_index(
        "idx_validation_history_quality_timestamp",
        "validation_history",
        ["quality_score", "timestamp"],
    )
    op.create_index(
        "idx_validation_history_run_entity",
        "validation_history",
        ["run_id", "entity_type"],
    )
    op.create_index(
        "idx_validation_history_anomaly",
        "validation_history",
        ["is_anomaly", "timestamp"],
    )
    op.create_index(
        "idx_validation_history_trend",
        "validation_history",
        ["trend_direction", "timestamp"],
    )
    op.create_index(
        "idx_validation_history_entity_quality",
        "validation_history",
        ["entity_type", "quality_score"],
    )
    op.create_index(
        "idx_validation_history_date_range",
        "validation_history",
        ["validation_date", "timestamp"],
    )


def downgrade():
    # Drop indexes first
    op.drop_index("idx_validation_history_date_range", table_name="validation_history")
    op.drop_index(
        "idx_validation_history_entity_quality", table_name="validation_history"
    )
    op.drop_index("idx_validation_history_trend", table_name="validation_history")
    op.drop_index("idx_validation_history_anomaly", table_name="validation_history")
    op.drop_index("idx_validation_history_run_entity", table_name="validation_history")
    op.drop_index(
        "idx_validation_history_quality_timestamp", table_name="validation_history"
    )
    op.drop_index(
        "idx_validation_history_type_timestamp", table_name="validation_history"
    )
    op.drop_index(
        "idx_validation_history_entity_timestamp", table_name="validation_history"
    )

    # Drop table
    op.drop_table("validation_history")
