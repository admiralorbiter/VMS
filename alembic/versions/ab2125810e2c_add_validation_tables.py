"""add_validation_tables

Revision ID: ab2125810e2c
Revises:
Create Date: 2025-08-14 09:31:21.736954

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ab2125810e2c"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create validation tables."""

    # Create validation_runs table
    op.create_table(
        "validation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_completion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress_percentage", sa.Integer(), nullable=True),
        sa.Column("total_checks", sa.Integer(), nullable=True),
        sa.Column("passed_checks", sa.Integer(), nullable=True),
        sa.Column("failed_checks", sa.Integer(), nullable=True),
        sa.Column("warnings", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Integer(), nullable=True),
        sa.Column("critical_issues", sa.Integer(), nullable=True),
        sa.Column("execution_time_seconds", sa.Integer(), nullable=True),
        sa.Column("memory_usage_mb", sa.Integer(), nullable=True),
        sa.Column("cpu_usage_percent", sa.Integer(), nullable=True),
        sa.Column("config_snapshot", sa.Text(), nullable=True),
        sa.Column("run_metadata", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create validation_results table
    op.create_table(
        "validation_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("entity_name", sa.String(length=255), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("field_path", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("validation_type", sa.String(length=50), nullable=False),
        sa.Column("rule_name", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("difference", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_metadata", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("memory_usage_kb", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create validation_metrics table
    op.create_table(
        "validation_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_category", sa.String(length=50), nullable=True),
        sa.Column("metric_unit", sa.String(length=20), nullable=True),
        sa.Column("metric_value", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("metric_value_raw", sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column("metric_threshold", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metric_metadata", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for validation_runs
    op.create_index("idx_validation_runs_run_type", "validation_runs", ["run_type"])
    op.create_index("idx_validation_runs_started_at", "validation_runs", ["started_at"])
    op.create_index("idx_validation_runs_created_by", "validation_runs", ["created_by"])
    op.create_index(
        "idx_validation_runs_type_status", "validation_runs", ["run_type", "status"]
    )
    op.create_index(
        "idx_validation_runs_created_by_status",
        "validation_runs",
        ["created_by", "status"],
    )
    op.create_index(
        "idx_validation_runs_started_completed",
        "validation_runs",
        ["started_at", "completed_at"],
    )

    # Create indexes for validation_results
    op.create_index("idx_validation_results_run_id", "validation_results", ["run_id"])
    op.create_index(
        "idx_validation_results_entity_type", "validation_results", ["entity_type"]
    )
    op.create_index(
        "idx_validation_results_entity_id", "validation_results", ["entity_id"]
    )
    op.create_index(
        "idx_validation_results_severity", "validation_results", ["severity"]
    )
    op.create_index(
        "idx_validation_results_validation_type",
        "validation_results",
        ["validation_type"],
    )
    op.create_index(
        "idx_validation_results_timestamp", "validation_results", ["timestamp"]
    )
    op.create_index(
        "idx_validation_results_run_entity",
        "validation_results",
        ["run_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "idx_validation_results_severity_timestamp",
        "validation_results",
        ["severity", "timestamp"],
    )

    # Create indexes for validation_metrics
    op.create_index(
        "idx_validation_metrics_metric_name", "validation_metrics", ["metric_name"]
    )
    op.create_index(
        "idx_validation_metrics_metric_category",
        "validation_metrics",
        ["metric_category"],
    )
    op.create_index(
        "idx_validation_metrics_entity_type", "validation_metrics", ["entity_type"]
    )
    op.create_index("idx_validation_metrics_run_id", "validation_metrics", ["run_id"])
    op.create_index(
        "idx_validation_metrics_timestamp", "validation_metrics", ["timestamp"]
    )
    op.create_index(
        "idx_validation_metrics_metric_date", "validation_metrics", ["metric_date"]
    )
    op.create_index(
        "idx_validation_metrics_name_category",
        "validation_metrics",
        ["metric_name", "metric_category"],
    )


def downgrade():
    """Drop validation tables."""

    # Drop indexes first
    op.drop_index("idx_validation_metrics_name_category", "validation_metrics")
    op.drop_index("idx_validation_metrics_metric_date", "validation_metrics")
    op.drop_index("idx_validation_metrics_timestamp", "validation_metrics")
    op.drop_index("idx_validation_metrics_run_id", "validation_metrics")
    op.drop_index("idx_validation_metrics_entity_type", "validation_metrics")
    op.drop_index("idx_validation_metrics_metric_category", "validation_metrics")
    op.drop_index("idx_validation_metrics_metric_name", "validation_metrics")

    op.drop_index("idx_validation_results_severity_timestamp", "validation_results")
    op.drop_index("idx_validation_results_run_entity", "validation_results")
    op.drop_index("idx_validation_results_timestamp", "validation_results")
    op.drop_index("idx_validation_results_validation_type", "validation_results")
    op.drop_index("idx_validation_results_severity", "validation_results")
    op.drop_index("idx_validation_results_entity_id", "validation_results")
    op.drop_index("idx_validation_results_entity_type", "validation_results")
    op.drop_index("idx_validation_results_run_id", "validation_results")

    op.drop_index("idx_validation_runs_started_completed", "validation_runs")
    op.drop_index("idx_validation_runs_created_by_status", "validation_runs")
    op.drop_index("idx_validation_runs_type_status", "validation_runs")
    op.drop_index("idx_validation_runs_created_by", "validation_runs")
    op.drop_index("idx_validation_runs_started_at", "validation_runs")
    op.drop_index("idx_validation_runs_run_type", "validation_runs")

    # Drop tables
    op.drop_table("validation_metrics")
    op.drop_table("validation_results")
    op.drop_table("validation_runs")
