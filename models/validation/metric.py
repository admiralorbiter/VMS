# models/validation/metric.py
"""
ValidationMetric model for storing aggregated validation metrics.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class ValidationMetric(db.Model):
    """
    Stores aggregated validation metrics.

    This model captures performance and quality metrics for validation runs,
    enabling trend analysis and performance monitoring.
    """

    __tablename__ = "validation_metrics"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Metric identification
    metric_name = Column(
        String(100), nullable=False, index=True
    )  # 'completeness_rate', 'accuracy_rate', etc.
    metric_category = Column(
        String(50), index=True
    )  # 'performance', 'quality', 'business', 'technical'
    metric_unit = Column(String(20))  # 'percentage', 'count', 'seconds', 'bytes', etc.

    # Metric value and context
    metric_value = Column(Numeric(10, 4), nullable=False)  # The actual metric value
    metric_value_raw = Column(Numeric(15, 6))  # Raw value before any processing
    metric_threshold = Column(Numeric(10, 4))  # Threshold value for this metric

    # Entity context
    entity_type = Column(
        String(50), index=True
    )  # 'volunteer', 'organization', 'event', etc.
    entity_id = Column(Integer, index=True)  # Specific entity instance
    field_name = Column(String(100))  # Specific field if applicable

    # Run context
    run_id = Column(
        Integer, ForeignKey("validation_runs.id", ondelete="CASCADE"), index=True
    )

    # Timing
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    metric_date = Column(
        DateTime(timezone=True), index=True
    )  # Date the metric represents

    # Additional context
    metric_metadata = Column(String(500))  # Additional context information

    # Relationships
    # Note: back_populates removed to avoid circular import issues

    # Indexes for performance
    __table_args__ = (
        Index("idx_validation_metrics_name_timestamp", "metric_name", "timestamp"),
        Index("idx_validation_metrics_entity_timestamp", "entity_type", "timestamp"),
        Index(
            "idx_validation_metrics_category_timestamp", "metric_category", "timestamp"
        ),
        Index("idx_validation_metrics_run_entity", "run_id", "entity_type"),
        Index(
            "idx_validation_metrics_name_entity_timestamp",
            "metric_name",
            "entity_type",
            "timestamp",
        ),
    )

    # Metric category constants
    CATEGORY_PERFORMANCE = "performance"
    CATEGORY_QUALITY = "quality"
    CATEGORY_BUSINESS = "business"
    CATEGORY_TECHNICAL = "technical"
    CATEGORY_SYSTEM = "system"

    # Common metric names
    METRIC_COMPLETENESS_RATE = "completeness_rate"
    METRIC_ACCURACY_RATE = "accuracy_rate"
    METRIC_ERROR_RATE = "error_rate"
    METRIC_WARNING_RATE = "warning_rate"
    METRIC_CRITICAL_RATE = "critical_rate"
    METRIC_SUCCESS_RATE = "success_rate"
    METRIC_EXECUTION_TIME = "execution_time"
    METRIC_MEMORY_USAGE = "memory_usage"
    METRIC_CPU_USAGE = "cpu_usage"
    METRIC_RECORD_COUNT = "record_count"
    METRIC_DIFFERENCE_PERCENTAGE = "difference_percentage"
    METRIC_ORPHANED_RECORDS = "orphaned_records"
    METRIC_DUPLICATE_RECORDS = "duplicate_records"
    METRIC_INVALID_RELATIONSHIPS = "invalid_relationships"

    def __repr__(self):
        """String representation of the validation metric."""
        return f"<ValidationMetric(id={self.id}, name={self.metric_name}, value={self.metric_value})>"

    @property
    def is_performance_metric(self) -> bool:
        """Check if this is a performance metric."""
        return self.metric_category == self.CATEGORY_PERFORMANCE

    @property
    def is_quality_metric(self) -> bool:
        """Check if this is a quality metric."""
        return self.metric_category == self.CATEGORY_QUALITY

    @property
    def is_business_metric(self) -> bool:
        """Check if this is a business metric."""
        return self.metric_category == self.CATEGORY_BUSINESS

    @property
    def is_technical_metric(self) -> bool:
        """Check if this is a technical metric."""
        return self.metric_category == self.CATEGORY_TECHNICAL

    @property
    def is_system_metric(self) -> bool:
        """Check if this is a system metric."""
        return self.metric_category == self.CATEGORY_SYSTEM

    @property
    def is_percentage_metric(self) -> bool:
        """Check if this metric is a percentage."""
        return self.metric_unit == "percentage"

    @property
    def is_count_metric(self) -> bool:
        """Check if this metric is a count."""
        return self.metric_unit == "count"

    @property
    def is_time_metric(self) -> bool:
        """Check if this metric is time-based."""
        return self.metric_unit == "seconds"

    @property
    def is_size_metric(self) -> bool:
        """Check if this metric is size-based."""
        return self.metric_unit in ["bytes", "kb", "mb", "gb"]

    @property
    def float_value(self) -> float:
        """Get the metric value as a float."""
        return float(self.metric_value) if self.metric_value else 0.0

    @property
    def int_value(self) -> int:
        """Get the metric value as an integer."""
        return int(self.metric_value) if self.metric_value else 0

    @property
    def meets_threshold(self) -> bool:
        """Check if the metric meets its threshold."""
        if self.metric_threshold is None:
            return True

        # For percentage metrics, higher is better
        if self.is_percentage_metric:
            return self.float_value >= float(self.metric_threshold)

        # For error/count metrics, lower is better
        if self.metric_name in [
            self.METRIC_ERROR_RATE,
            self.METRIC_CRITICAL_RATE,
            self.METRIC_ORPHANED_RECORDS,
            self.METRIC_DUPLICATE_RECORDS,
        ]:
            return self.float_value <= float(self.metric_threshold)

        # For time/size metrics, lower is better
        if self.is_time_metric or self.is_size_metric:
            return self.float_value <= float(self.metric_threshold)

        # Default: higher is better
        return self.float_value >= float(self.metric_threshold)

    def to_dict(self) -> dict:
        """Convert the validation metric to a dictionary."""
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "metric_category": self.metric_category,
            "metric_unit": self.metric_unit,
            "metric_value": self.float_value,
            "metric_value_raw": (
                float(self.metric_value_raw) if self.metric_value_raw else None
            ),
            "metric_threshold": (
                float(self.metric_threshold) if self.metric_threshold else None
            ),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metric_date": self.metric_date.isoformat() if self.metric_date else None,
            "metadata": self.metric_metadata,
            "meets_threshold": self.meets_threshold,
            "is_percentage": self.is_percentage_metric,
            "is_count": self.is_count_metric,
            "is_time": self.is_time_metric,
            "is_size": self.is_size_metric,
        }

    @classmethod
    def create_metric(
        cls,
        metric_name: str,
        metric_value: float,
        metric_category: str = None,
        metric_unit: str = None,
        entity_type: str = None,
        entity_id: int = None,
        field_name: str = None,
        run_id: int = None,
        metric_threshold: float = None,
        metric_value_raw: float = None,
        metric_date: datetime = None,
        metadata: str = None,
    ) -> "ValidationMetric":
        """
        Create a new validation metric with the given parameters.

        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            metric_category: Category of the metric
            metric_unit: Unit of the metric
            entity_type: Type of entity
            entity_id: ID of the entity
            field_name: Name of the field
            run_id: ID of the validation run
            metric_threshold: Threshold value for the metric
            metric_value_raw: Raw value before processing
            metric_date: Date the metric represents
            metadata: Additional metadata

        Returns:
            New ValidationMetric instance
        """
        return cls(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_category=metric_category,
            metric_unit=metric_unit,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            run_id=run_id,
            metric_threshold=metric_threshold,
            metric_value_raw=metric_value_raw,
            metric_date=metric_date or datetime.utcnow(),
            metadata=metadata,
        )

    @classmethod
    def get_metrics_by_run(
        cls, run_id: int, metric_category: str = None, entity_type: str = None
    ):
        """Get metrics for a specific validation run."""
        query = cls.query.filter_by(run_id=run_id)

        if metric_category:
            query = query.filter_by(metric_category=metric_category)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        return query.order_by(cls.timestamp.desc()).all()

    @classmethod
    def get_metrics_by_name(
        cls, metric_name: str, entity_type: str = None, limit: int = 100, days: int = 30
    ):
        """Get historical metrics for a specific metric name."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = cls.query.filter(
            cls.metric_name == metric_name, cls.timestamp >= cutoff_date
        )

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_latest_metric(cls, metric_name: str, entity_type: str = None):
        """Get the latest value for a specific metric."""
        query = cls.query.filter_by(metric_name=metric_name)

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        return query.order_by(cls.timestamp.desc()).first()

    @classmethod
    def get_metric_summary(cls, run_id: int) -> dict:
        """Get a summary of metrics for a validation run."""
        metrics = cls.query.filter_by(run_id=run_id).all()

        summary = {
            "total_metrics": len(metrics),
            "categories": {},
            "entity_types": {},
            "threshold_compliance": {
                "meets_threshold": 0,
                "below_threshold": 0,
                "no_threshold": 0,
            },
        }

        for metric in metrics:
            # Category breakdown
            if metric.metric_category not in summary["categories"]:
                summary["categories"][metric.metric_category] = {
                    "count": 0,
                    "total_value": 0.0,
                    "min_value": float("inf"),
                    "max_value": float("-inf"),
                }

            cat_summary = summary["categories"][metric.metric_category]
            cat_summary["count"] += 1
            cat_summary["total_value"] += metric.float_value
            cat_summary["min_value"] = min(cat_summary["min_value"], metric.float_value)
            cat_summary["max_value"] = max(cat_summary["max_value"], metric.float_value)

            # Entity type breakdown
            if metric.entity_type not in summary["entity_types"]:
                summary["entity_types"][metric.entity_type] = {
                    "count": 0,
                    "total_value": 0.0,
                }

            ent_summary = summary["entity_types"][metric.entity_type]
            ent_summary["count"] += 1
            ent_summary["total_value"] += metric.float_value

            # Threshold compliance
            if metric.metric_threshold is None:
                summary["threshold_compliance"]["no_threshold"] += 1
            elif metric.meets_threshold:
                summary["threshold_compliance"]["meets_threshold"] += 1
            else:
                summary["threshold_compliance"]["below_threshold"] += 1

        # Calculate averages
        for cat_summary in summary["categories"].values():
            if cat_summary["count"] > 0:
                cat_summary["average_value"] = (
                    cat_summary["total_value"] / cat_summary["count"]
                )
            else:
                cat_summary["average_value"] = 0.0

        for ent_summary in summary["entity_types"].values():
            if ent_summary["count"] > 0:
                ent_summary["average_value"] = (
                    ent_summary["total_value"] / ent_summary["count"]
                )
            else:
                ent_summary["average_value"] = 0.0

        return summary

    @classmethod
    def get_trend_data(
        cls, metric_name: str, entity_type: str = None, days: int = 30
    ) -> dict:
        """Get trend data for a specific metric over time."""
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = cls.query.filter(
            cls.metric_name == metric_name, cls.timestamp >= cutoff_date
        )

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        metrics = query.order_by(cls.timestamp.asc()).all()

        trend_data = {
            "metric_name": metric_name,
            "entity_type": entity_type,
            "period_days": days,
            "data_points": len(metrics),
            "timestamps": [],
            "values": [],
            "thresholds": [],
            "compliance": [],
        }

        for metric in metrics:
            trend_data["timestamps"].append(metric.timestamp.isoformat())
            trend_data["values"].append(metric.float_value)
            trend_data["thresholds"].append(
                float(metric.metric_threshold) if metric.metric_threshold else None
            )
            trend_data["compliance"].append(metric.meets_threshold)

        return trend_data
