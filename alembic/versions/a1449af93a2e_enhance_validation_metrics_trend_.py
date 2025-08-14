"""enhance_validation_metrics_trend_aggregation

Revision ID: a1449af93a2e
Revises: e82d1834af0c
Create Date: 2025-08-14 16:15:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1449af93a2e"
down_revision = "e82d1834af0c"
branch_labels = None
depends_on = None


def upgrade():
    # Add new trend analysis fields to validation_metrics table
    op.add_column(
        "validation_metrics",
        sa.Column("trend_period", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "validation_metrics",
        sa.Column("trend_direction", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "validation_metrics", sa.Column("trend_magnitude", sa.Float(), nullable=True)
    )
    op.add_column(
        "validation_metrics", sa.Column("trend_confidence", sa.Float(), nullable=True)
    )
    op.add_column(
        "validation_metrics",
        sa.Column("baseline_value", sa.Numeric(precision=15, scale=6), nullable=True),
    )
    op.add_column(
        "validation_metrics", sa.Column("change_percentage", sa.Float(), nullable=True)
    )

    # Add new aggregation fields to validation_metrics table
    op.add_column(
        "validation_metrics",
        sa.Column("aggregation_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "validation_metrics",
        sa.Column("aggregation_period", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "validation_metrics",
        sa.Column("aggregation_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "validation_metrics",
        sa.Column("aggregation_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "validation_metrics",
        sa.Column("aggregation_count", sa.Integer(), nullable=True),
    )

    # Create new indexes for Phase 3.4 trend analysis
    op.create_index(
        "idx_validation_metrics_trend_period",
        "validation_metrics",
        ["trend_period", "timestamp"],
    )
    op.create_index(
        "idx_validation_metrics_trend_direction",
        "validation_metrics",
        ["trend_direction", "timestamp"],
    )
    op.create_index(
        "idx_validation_metrics_aggregation_period",
        "validation_metrics",
        ["aggregation_period", "timestamp"],
    )
    op.create_index(
        "idx_validation_metrics_aggregation_type",
        "validation_metrics",
        ["aggregation_type", "timestamp"],
    )
    op.create_index(
        "idx_validation_metrics_trend_confidence",
        "validation_metrics",
        ["trend_confidence", "timestamp"],
    )


def downgrade():
    # Drop new indexes
    op.drop_index(
        "idx_validation_metrics_trend_confidence", table_name="validation_metrics"
    )
    op.drop_index(
        "idx_validation_metrics_aggregation_type", table_name="validation_metrics"
    )
    op.drop_index(
        "idx_validation_metrics_aggregation_period", table_name="validation_metrics"
    )
    op.drop_index(
        "idx_validation_metrics_trend_direction", table_name="validation_metrics"
    )
    op.drop_index(
        "idx_validation_metrics_trend_period", table_name="validation_metrics"
    )

    # Drop new aggregation columns
    op.drop_column("validation_metrics", "aggregation_count")
    op.drop_column("validation_metrics", "aggregation_end")
    op.drop_column("validation_metrics", "aggregation_start")
    op.drop_column("validation_metrics", "aggregation_period")
    op.drop_column("validation_metrics", "aggregation_type")

    # Drop new trend columns
    op.drop_column("validation_metrics", "change_percentage")
    op.drop_column("validation_metrics", "baseline_value")
    op.drop_column("validation_metrics", "trend_confidence")
    op.drop_column("validation_metrics", "trend_magnitude")
    op.drop_column("validation_metrics", "trend_direction")
    op.drop_column("validation_metrics", "trend_period")
