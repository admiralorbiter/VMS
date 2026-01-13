# models/validation/metric.py
"""
ValidationMetric model for storing aggregated validation metrics.
"""

from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
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

    # Trend analysis fields (NEW for Phase 3.4)
    trend_period = Column(String(20))  # 'daily', 'weekly', 'monthly', 'quarterly'
    trend_direction = Column(String(20))  # 'improving', 'declining', 'stable'
    trend_magnitude = Column(Float)  # Trend strength (-100 to +100)
    trend_confidence = Column(Float)  # Statistical confidence (0-1)
    baseline_value = Column(Numeric(15, 6))  # Baseline value for trend comparison
    change_percentage = Column(Float)  # Percentage change from baseline

    # Aggregation fields (NEW for Phase 3.4)
    aggregation_type = Column(String(50))  # 'sum', 'average', 'min', 'max', 'count'
    aggregation_period = Column(String(20))  # 'hourly', 'daily', 'weekly', 'monthly'
    aggregation_start = Column(DateTime(timezone=True))  # Start of aggregation period
    aggregation_end = Column(DateTime(timezone=True))  # End of aggregation period
    aggregation_count = Column(Integer)  # Number of values aggregated

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
        # New indexes for Phase 3.4 trend analysis
        Index("idx_validation_metrics_trend_period", "trend_period", "timestamp"),
        Index("idx_validation_metrics_trend_direction", "trend_direction", "timestamp"),
        Index(
            "idx_validation_metrics_aggregation_period",
            "aggregation_period",
            "timestamp",
        ),
        Index(
            "idx_validation_metrics_aggregation_type", "aggregation_type", "timestamp"
        ),
        Index(
            "idx_validation_metrics_trend_confidence", "trend_confidence", "timestamp"
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
            metric_date=metric_date or datetime.now(timezone.utc),
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

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
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

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
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

    @classmethod
    def get_aggregated_metrics(
        cls,
        metric_name: str,
        aggregation_period: str = "daily",
        entity_type: str = None,
        days: int = 30,
    ) -> List["ValidationMetric"]:
        """
        Get aggregated metrics for a specific period.

        Args:
            metric_name: Name of the metric to aggregate
            aggregation_period: Period for aggregation ('hourly', 'daily', 'weekly', 'monthly')
            entity_type: Optional entity type filter
            days: Number of days to look back

        Returns:
            List of aggregated ValidationMetric records
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = cls.query.filter(
            cls.metric_name == metric_name,
            cls.timestamp >= cutoff_date,
            cls.aggregation_period == aggregation_period,
        )

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        return query.order_by(cls.aggregation_start.asc()).all()

    @classmethod
    def calculate_trends_for_metric(
        cls,
        metric_name: str,
        entity_type: str = None,
        days: int = 30,
        min_data_points: int = 3,
    ) -> Dict:
        """
        Calculate trend analysis for a specific metric.

        Args:
            metric_name: Name of the metric to analyze
            entity_type: Optional entity type filter
            days: Number of days to analyze
            min_data_points: Minimum data points required for trend calculation

        Returns:
            Dictionary containing trend analysis results
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = cls.query.filter(
            cls.metric_name == metric_name, cls.timestamp >= cutoff_date
        )

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        metrics = query.order_by(cls.timestamp.asc()).all()

        if len(metrics) < min_data_points:
            return {
                "metric_name": metric_name,
                "entity_type": entity_type,
                "trend": "insufficient_data",
                "confidence": 0.0,
                "data_points": len(metrics),
                "required_points": min_data_points,
            }

        # Extract values for trend calculation
        values = [metric.float_value for metric in metrics]
        timestamps = [metric.timestamp for metric in metrics]

        # Calculate trend using linear regression
        trend_result = cls._calculate_linear_trend(values, timestamps)

        # Determine trend direction
        if trend_result["slope"] > 0.01:
            trend_direction = "improving"
        elif trend_result["slope"] < -0.01:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return {
            "metric_name": metric_name,
            "entity_type": entity_type,
            "trend": trend_direction,
            "slope": trend_result["slope"],
            "confidence": trend_result["confidence"],
            "data_points": len(metrics),
            "period_days": days,
            "baseline_value": values[0],
            "current_value": values[-1],
            "change_percentage": (
                ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            ),
            "trend_magnitude": abs(trend_result["slope"]) * 100,  # Scale to 0-100 range
            "statistical_significance": trend_result["r_squared"],
        }

    @classmethod
    def _calculate_linear_trend(
        cls, values: List[float], timestamps: List[datetime]
    ) -> Dict:
        """
        Calculate linear trend using simple linear regression.

        Args:
            values: List of metric values
            timestamps: List of corresponding timestamps

        Returns:
            Dictionary containing trend analysis results
        """
        if len(values) < 2:
            return {"slope": 0.0, "confidence": 0.0, "r_squared": 0.0}

        # Convert timestamps to numeric values (days since first timestamp)
        first_timestamp = timestamps[0]
        x_values = [(ts - first_timestamp).days for ts in timestamps]
        y_values = values

        # Calculate linear regression
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        # Calculate slope and intercept
        if n * sum_x2 - sum_x * sum_x == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        intercept = (sum_y - slope * sum_x) / n

        # Calculate R-squared (coefficient of determination)
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum(
            (y - (slope * x + intercept)) ** 2 for x, y in zip(x_values, y_values)
        )

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        # Calculate confidence based on R-squared and data points
        confidence = min(1.0, r_squared * (len(values) / 10.0))

        return {
            "slope": slope,
            "intercept": intercept,
            "confidence": confidence,
            "r_squared": r_squared,
        }

    @classmethod
    def get_metric_summary_by_period(
        cls,
        metric_name: str,
        period: str = "daily",
        entity_type: str = None,
        days: int = 30,
    ) -> Dict:
        """
        Get summary statistics for a metric grouped by time period.

        Args:
            metric_name: Name of the metric
            period: Time period for grouping ('hourly', 'daily', 'weekly', 'monthly')
            entity_type: Optional entity type filter
            days: Number of days to analyze

        Returns:
            Dictionary containing period-based summary statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = cls.query.filter(
            cls.metric_name == metric_name, cls.timestamp >= cutoff_date
        )

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        metrics = query.order_by(cls.timestamp.asc()).all()

        if not metrics:
            return {
                "metric_name": metric_name,
                "period": period,
                "entity_type": entity_type,
                "periods": [],
                "values": [],
                "counts": [],
                "averages": [],
            }

        # Group metrics by period
        period_groups = {}
        for metric in metrics:
            if period == "hourly":
                period_key = metric.timestamp.strftime("%Y-%m-%d %H:00")
            elif period == "daily":
                period_key = metric.timestamp.strftime("%Y-%m-%d")
            elif period == "weekly":
                period_key = metric.timestamp.strftime("%Y-W%U")
            elif period == "monthly":
                period_key = metric.timestamp.strftime("%Y-%m")
            else:
                period_key = metric.timestamp.strftime("%Y-%m-%d")

            if period_key not in period_groups:
                period_groups[period_key] = []
            period_groups[period_key].append(metric.float_value)

        # Calculate statistics for each period
        periods = sorted(period_groups.keys())
        values = []
        counts = []
        averages = []

        for period_key in periods:
            period_values = period_groups[period_key]
            values.append(period_values)
            counts.append(len(period_values))
            averages.append(sum(period_values) / len(period_values))

        return {
            "metric_name": metric_name,
            "period": period,
            "entity_type": entity_type,
            "periods": periods,
            "values": values,
            "counts": counts,
            "averages": averages,
            "total_periods": len(periods),
            "total_values": sum(counts),
        }
