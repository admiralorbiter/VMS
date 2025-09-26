# models/validation/history.py
"""
ValidationHistory model for storing historical validation data.

This model provides comprehensive historical tracking of validation runs,
quality scores, and trends over time for advanced analytics and reporting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class ValidationHistory(db.Model):
    """
    Historical validation run data for trend analysis and quality monitoring.

    This model stores comprehensive historical data from validation runs,
    enabling trend analysis, quality scoring, and predictive modeling.
    It maintains a rolling window of validation history for analysis.

    Database Table:
        validation_history - Stores historical validation data and trends

    Key Features:
        - Historical quality score tracking
        - Violation count aggregation
        - Trend data calculation and storage
        - Performance metrics history
        - Entity-specific quality tracking
        - Automatic data retention management
        - Statistical analysis support

    Data Retention:
        - Configurable retention period (default: 1 year)
        - Automatic cleanup of old records
        - Efficient storage with JSON compression
        - Indexed queries for fast retrieval

    Trend Analysis:
        - Quality score trends over time
        - Violation pattern identification
        - Performance trend tracking
        - Anomaly detection support
        - Correlation analysis data
    """

    __tablename__ = "validation_history"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Run relationship
    run_id = Column(
        Integer,
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entity context
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # 'volunteer', 'organization', 'event', etc.
    validation_type = Column(
        String(50), nullable=False, index=True
    )  # 'count', 'field_completeness', 'data_types', etc.

    # Quality metrics
    quality_score = Column(Float, nullable=False)  # Overall quality score (0-100)
    quality_score_raw = Column(Float)  # Raw quality score before normalization
    quality_threshold = Column(Float)  # Quality threshold for this entity/type

    # Violation counts and severity breakdown
    violation_counts = Column(
        JSON, nullable=False
    )  # {critical: 5, error: 10, warning: 15, info: 2}
    total_violations = Column(Integer, nullable=False)  # Total violation count
    critical_violations = Column(Integer, nullable=False, default=0)
    error_violations = Column(Integer, nullable=False, default=0)
    warning_violations = Column(Integer, nullable=False, default=0)
    info_violations = Column(Integer, nullable=False, default=0)

    # Success metrics
    total_checks = Column(Integer, nullable=False, default=0)
    passed_checks = Column(Integer, nullable=False, default=0)
    failed_checks = Column(Integer, nullable=False, default=0)
    success_rate = Column(
        Float, nullable=False, default=0.0
    )  # Percentage of passed checks

    # Performance metrics
    execution_time_seconds = Column(Float)  # Validation execution time
    memory_usage_mb = Column(Float)  # Peak memory usage
    cpu_usage_percent = Column(Float)  # Peak CPU usage

    # Aggregated metrics summary
    metrics_summary = Column(JSON)  # Aggregated metrics from ValidationMetric
    field_completeness = Column(Float)  # Field completeness percentage
    data_type_accuracy = Column(Float)  # Data type accuracy percentage
    relationship_integrity = Column(Float)  # Relationship integrity percentage
    business_rule_compliance = Column(Float)  # Business rule compliance percentage

    # Trend analysis data
    trend_data = Column(JSON)  # Calculated trend information
    trend_direction = Column(String(20))  # 'improving', 'declining', 'stable'
    trend_magnitude = Column(Float)  # Trend strength (-100 to +100)
    trend_confidence = Column(Float)  # Statistical confidence (0-1)

    # Anomaly detection
    is_anomaly = Column(Integer, default=0)  # 0=normal, 1=anomaly
    anomaly_score = Column(Float)  # Statistical anomaly score
    anomaly_type = Column(String(50))  # Type of anomaly detected

    # Timestamps
    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    validation_date = Column(
        DateTime(timezone=True), index=True
    )  # Date the validation represents
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    # Additional context
    validation_metadata = Column(JSON)  # Additional context and configuration data
    notes = Column(Text)  # Human-readable notes about this validation

    # Relationships
    run = relationship("ValidationRun", backref="history_records")

    # Indexes for performance
    __table_args__ = (
        Index("idx_validation_history_entity_timestamp", "entity_type", "timestamp"),
        Index("idx_validation_history_type_timestamp", "validation_type", "timestamp"),
        Index("idx_validation_history_quality_timestamp", "quality_score", "timestamp"),
        Index("idx_validation_history_run_entity", "run_id", "entity_type"),
        Index("idx_validation_history_anomaly", "is_anomaly", "timestamp"),
        Index("idx_validation_history_trend", "trend_direction", "timestamp"),
        Index("idx_validation_history_entity_quality", "entity_type", "quality_score"),
        Index("idx_validation_history_date_range", "validation_date", "timestamp"),
    )

    def __repr__(self):
        """String representation of the validation history record."""
        return (
            f"<ValidationHistory(id={self.id}, entity={self.entity_type}, "
            f"type={self.validation_type}, score={self.quality_score:.2f})>"
        )

    @property
    def quality_status(self) -> str:
        """Get the quality status based on score and threshold."""
        if self.quality_threshold is None:
            return "unknown"

        if self.quality_score >= self.quality_threshold:
            return "excellent"
        elif self.quality_score >= self.quality_threshold * 0.8:
            return "good"
        elif self.quality_score >= self.quality_threshold * 0.6:
            return "fair"
        else:
            return "poor"

    @property
    def violation_rate(self) -> float:
        """Calculate the violation rate as a percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.total_violations / self.total_checks) * 100

    @property
    def critical_violation_rate(self) -> float:
        """Calculate the critical violation rate as a percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.critical_violations / self.total_checks) * 100

    @property
    def days_since_validation(self) -> int:
        """Get the number of days since this validation was run."""
        if not self.validation_date:
            return 0
        return (datetime.now(datetime.UTC) - self.validation_date).days

    @property
    def trend_description(self) -> str:
        """Get a human-readable description of the trend."""
        if not self.trend_direction:
            return "No trend data available"

        magnitude_desc = "slightly"
        if abs(self.trend_magnitude) > 50:
            magnitude_desc = "significantly"
        elif abs(self.trend_magnitude) > 20:
            magnitude_desc = "moderately"

        if self.trend_direction == "improving":
            return f"Quality is {magnitude_desc} improving"
        elif self.trend_direction == "declining":
            return f"Quality is {magnitude_desc} declining"
        else:
            return "Quality is stable"

    def to_dict(self) -> dict:
        """Convert the validation history record to a dictionary."""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "entity_type": self.entity_type,
            "validation_type": self.validation_type,
            "quality_score": self.quality_score,
            "quality_score_raw": self.quality_score_raw,
            "quality_threshold": self.quality_threshold,
            "quality_status": self.quality_status,
            "violation_counts": self.violation_counts,
            "total_violations": self.total_violations,
            "critical_violations": self.critical_violations,
            "error_violations": self.error_violations,
            "warning_violations": self.warning_violations,
            "info_violations": self.info_violations,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "success_rate": self.success_rate,
            "violation_rate": self.violation_rate,
            "critical_violation_rate": self.critical_violation_rate,
            "execution_time_seconds": self.execution_time_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "metrics_summary": self.metrics_summary,
            "field_completeness": self.field_completeness,
            "data_type_accuracy": self.data_type_accuracy,
            "relationship_integrity": self.relationship_integrity,
            "business_rule_compliance": self.business_rule_compliance,
            "trend_data": self.trend_data,
            "trend_direction": self.trend_direction,
            "trend_magnitude": self.trend_magnitude,
            "trend_confidence": self.trend_confidence,
            "trend_description": self.trend_description,
            "is_anomaly": bool(self.is_anomaly),
            "anomaly_score": self.anomaly_score,
            "anomaly_type": self.anomaly_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "validation_date": (
                self.validation_date.isoformat() if self.validation_date else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "days_since_validation": self.days_since_validation,
            "metadata": self.validation_metadata,
            "notes": self.notes,
        }

    @classmethod
    def create_from_validation_run(
        cls,
        run_id: int,
        entity_type: str,
        validation_type: str,
        quality_score: float,
        violation_counts: Dict[str, int],
        total_checks: int,
        passed_checks: int,
        failed_checks: int,
        execution_time: float = None,
        memory_usage: float = None,
        cpu_usage: float = None,
        metrics_summary: Dict = None,
        quality_threshold: float = None,
        validation_metadata: Dict = None,
        notes: str = None,
    ) -> "ValidationHistory":
        """
        Create a new validation history record from validation run data.

        Args:
            run_id: ID of the validation run
            entity_type: Type of entity validated
            validation_type: Type of validation performed
            quality_score: Overall quality score
            violation_counts: Dictionary of violation counts by severity
            total_checks: Total number of validation checks
            passed_checks: Number of passed checks
            failed_checks: Number of failed checks
            execution_time: Validation execution time in seconds
            memory_usage: Peak memory usage in MB
            cpu_usage: Peak CPU usage percentage
            metrics_summary: Summary of validation metrics
            quality_threshold: Quality threshold for this entity/type
            validation_metadata: Additional context and configuration data
            notes: Human-readable notes

        Returns:
            New ValidationHistory instance
        """
        # Calculate derived fields
        total_violations = sum(violation_counts.values())
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0

        # Extract individual violation counts
        critical_violations = violation_counts.get("critical", 0)
        error_violations = violation_counts.get("error", 0)
        warning_violations = violation_counts.get("warning", 0)
        info_violations = violation_counts.get("info", 0)

        return cls(
            run_id=run_id,
            entity_type=entity_type,
            validation_type=validation_type,
            quality_score=quality_score,
            quality_score_raw=quality_score,
            quality_threshold=quality_threshold,
            violation_counts=violation_counts,
            total_violations=total_violations,
            critical_violations=critical_violations,
            error_violations=error_violations,
            warning_violations=warning_violations,
            info_violations=info_violations,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            success_rate=success_rate,
            execution_time_seconds=execution_time,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            metrics_summary=metrics_summary,
            validation_metadata=validation_metadata,
            notes=notes,
            validation_date=datetime.now(datetime.UTC),
        )

    @classmethod
    def get_entity_history(
        cls,
        entity_type: str,
        validation_type: str = None,
        days: int = 30,
        limit: int = 100,
    ) -> List["ValidationHistory"]:
        """
        Get historical validation data for a specific entity type.

        Args:
            entity_type: Type of entity to get history for
            validation_type: Optional validation type filter
            days: Number of days to look back
            limit: Maximum number of records to return

        Returns:
            List of ValidationHistory records
        """
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days)
        query = cls.query.filter(
            cls.entity_type == entity_type, cls.timestamp >= cutoff_date
        )

        if validation_type:
            query = query.filter(cls.validation_type == validation_type)

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_quality_trends(
        cls,
        entity_type: str,
        validation_type: str = None,
        days: int = 90,
    ) -> Dict:
        """
        Get quality score trends for an entity type over time.

        Args:
            entity_type: Type of entity to analyze
            validation_type: Optional validation type filter
            days: Number of days to analyze

        Returns:
            Dictionary containing trend analysis data
        """
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days)
        query = cls.query.filter(
            cls.entity_type == entity_type, cls.timestamp >= cutoff_date
        )

        if validation_type:
            query = query.filter(cls.validation_type == validation_type)

        records = query.order_by(cls.timestamp.asc()).all()

        if not records:
            return {
                "entity_type": entity_type,
                "validation_type": validation_type,
                "period_days": days,
                "data_points": 0,
                "trend": "insufficient_data",
                "quality_scores": [],
                "timestamps": [],
                "average_score": 0.0,
                "score_variance": 0.0,
            }

        # Extract data for analysis
        quality_scores = [record.quality_score for record in records]
        timestamps = [record.timestamp.isoformat() for record in records]

        # Calculate basic statistics
        average_score = sum(quality_scores) / len(quality_scores)
        score_variance = sum(
            (score - average_score) ** 2 for score in quality_scores
        ) / len(quality_scores)

        # Simple trend calculation (linear regression slope)
        if len(quality_scores) > 1:
            x_values = list(range(len(quality_scores)))
            y_values = quality_scores

            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(y_values)
            sum_xy = sum(x * y for x, y in zip(x_values, y_values))
            sum_x2 = sum(x * x for x in x_values)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            if slope > 0.5:
                trend = "improving"
            elif slope < -0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "entity_type": entity_type,
            "validation_type": validation_type,
            "period_days": days,
            "data_points": len(records),
            "trend": trend,
            "quality_scores": quality_scores,
            "timestamps": timestamps,
            "average_score": round(average_score, 2),
            "score_variance": round(score_variance, 2),
            "min_score": min(quality_scores),
            "max_score": max(quality_scores),
            "trend_slope": slope if len(quality_scores) > 1 else 0.0,
        }

    @classmethod
    def get_anomalies(
        cls,
        entity_type: str = None,
        validation_type: str = None,
        days: int = 30,
        anomaly_threshold: float = 2.0,
    ) -> List["ValidationHistory"]:
        """
        Get validation records that are statistical anomalies.

        Args:
            entity_type: Optional entity type filter
            validation_type: Optional validation type filter
            days: Number of days to look back
            anomaly_threshold: Standard deviations for anomaly detection

        Returns:
            List of ValidationHistory records marked as anomalies
        """
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days)
        query = cls.query.filter(cls.timestamp >= cutoff_date, cls.is_anomaly == 1)

        if entity_type:
            query = query.filter(cls.entity_type == entity_type)
        if validation_type:
            query = query.filter(cls.validation_type == validation_type)

        return query.order_by(cls.timestamp.desc()).all()

    @classmethod
    def cleanup_old_records(cls, retention_days: int = 365) -> int:
        """
        Clean up old validation history records.

        Args:
            retention_days: Number of days to retain records

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=retention_days)
        old_records = cls.query.filter(cls.timestamp < cutoff_date).all()

        count = len(old_records)
        for record in old_records:
            db.session.delete(record)

        db.session.commit()
        return count

    @classmethod
    def get_summary_statistics(
        cls,
        entity_type: str = None,
        validation_type: str = None,
        days: int = 30,
    ) -> Dict:
        """
        Get summary statistics for validation history.

        Args:
            entity_type: Optional entity type filter
            validation_type: Optional validation type filter
            days: Number of days to analyze

        Returns:
            Dictionary containing summary statistics
        """
        cutoff_date = datetime.now(datetime.UTC) - timedelta(days=days)
        query = cls.query.filter(cls.timestamp >= cutoff_date)

        if entity_type:
            query = query.filter(cls.entity_type == entity_type)
        if validation_type:
            query = query.filter(cls.validation_type == validation_type)

        records = query.all()

        if not records:
            return {
                "total_records": 0,
                "period_days": days,
                "entity_type": entity_type,
                "validation_type": validation_type,
                "average_quality_score": 0.0,
                "total_violations": 0,
                "anomaly_count": 0,
            }

        # Calculate statistics
        quality_scores = [record.quality_score for record in records]
        total_violations = sum(record.total_violations for record in records)
        anomaly_count = sum(1 for record in records if record.is_anomaly)

        return {
            "total_records": len(records),
            "period_days": days,
            "entity_type": entity_type,
            "validation_type": validation_type,
            "average_quality_score": round(
                sum(quality_scores) / len(quality_scores), 2
            ),
            "min_quality_score": min(quality_scores),
            "max_quality_score": max(quality_scores),
            "total_violations": total_violations,
            "average_violations_per_run": round(total_violations / len(records), 2),
            "anomaly_count": anomaly_count,
            "anomaly_rate": round((anomaly_count / len(records)) * 100, 2),
        }
