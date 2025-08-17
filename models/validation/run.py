# models/validation/run.py
"""
ValidationRun model for tracking validation execution sessions.
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class ValidationRun(db.Model):
    """
    Tracks individual validation execution sessions.

    This model stores metadata about validation runs including timing,
    status, and summary statistics.
    """

    __tablename__ = "validation_runs"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Run identification and type
    run_type = Column(
        String(50), nullable=False, index=True
    )  # 'fast', 'slow', 'realtime'
    name = Column(String(255))  # Human-readable name for the run
    description = Column(Text)  # Optional description

    # Timing information
    started_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    completed_at = Column(DateTime(timezone=True))
    estimated_completion = Column(DateTime(timezone=True))  # Estimated completion time

    # Status and progress
    status = Column(
        String(20), nullable=False, default="running", index=True
    )  # 'running', 'completed', 'failed', 'cancelled'
    progress_percentage = Column(Integer, default=0)  # 0-100 progress indicator

    # Summary statistics
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    warnings = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)

    # Performance metrics
    execution_time_seconds = Column(Integer)  # Total execution time in seconds
    memory_usage_mb = Column(Integer)  # Peak memory usage in MB
    cpu_usage_percent = Column(Integer)  # Peak CPU usage percentage

    # Configuration and metadata
    config_snapshot = Column(Text)  # JSON string of configuration used
    run_metadata = Column(Text)  # JSON string for additional data

    # User tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Error information
    error_message = Column(Text)  # Error message if status is 'failed'
    error_traceback = Column(Text)  # Full error traceback if available

    # Relationships
    results = relationship(
        "ValidationResult", backref="run", lazy="dynamic", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "ValidationMetric", backref="run", lazy="dynamic", cascade="all, delete-orphan"
    )
    user = relationship("User", foreign_keys=[created_by], backref="validation_runs")

    # Indexes for performance
    __table_args__ = (
        Index("idx_validation_runs_type_status", "run_type", "status"),
        Index("idx_validation_runs_created_by_status", "created_by", "status"),
        Index("idx_validation_runs_started_completed", "started_at", "completed_at"),
    )

    def __repr__(self):
        """String representation of the validation run."""
        return (
            f"<ValidationRun(id={self.id}, type={self.run_type}, status={self.status})>"
        )

    @property
    def is_running(self) -> bool:
        """Check if the validation run is currently running."""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """Check if the validation run has completed successfully."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if the validation run has failed."""
        return self.status == "failed"

    @property
    def is_cancelled(self) -> bool:
        """Check if the validation run was cancelled."""
        return self.status == "cancelled"

    @property
    def duration_seconds(self) -> int:
        """Get the duration of the validation run in seconds."""
        if not self.completed_at or not self.started_at:
            return 0
        return int((self.completed_at - self.started_at).total_seconds())

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.passed_checks / self.total_checks) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate the failure rate as a percentage."""
        if self.total_checks == 0:
            return 0.0
        return (
            (self.failed_checks + self.errors + self.critical_issues)
            / self.total_checks
        ) * 100

    @property
    def warning_rate(self) -> float:
        """Calculate the warning rate as a percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.warnings / self.total_checks) * 100

    def update_progress(self, current_step: int, total_steps: int):
        """Update the progress percentage."""
        if total_steps > 0:
            self.progress_percentage = int((current_step / total_steps) * 100)

    def mark_completed(
        self,
        execution_time: int = None,
        memory_usage: int = None,
        cpu_usage: int = None,
    ):
        """Mark the validation run as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100

        if execution_time is not None:
            self.execution_time_seconds = execution_time
        if memory_usage is not None:
            self.memory_usage_mb = memory_usage
        if cpu_usage is not None:
            self.cpu_usage_percent = cpu_usage

    def mark_failed(self, error_message: str, error_traceback: str = None):
        """Mark the validation run as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_traceback = error_traceback

    def mark_cancelled(self):
        """Mark the validation run as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def update_summary_stats(
        self,
        passed: int = None,
        failed: int = None,
        warnings: int = None,
        errors: int = None,
        critical: int = None,
    ):
        """Update the summary statistics."""
        if passed is not None:
            self.passed_checks = passed
        if failed is not None:
            self.failed_checks = failed
        if warnings is not None:
            self.warnings = warnings
        if errors is not None:
            self.errors = errors
        if critical is not None:
            self.critical_issues = critical

        # Update total checks
        self.total_checks = (
            self.passed_checks
            + self.failed_checks
            + self.warnings
            + self.errors
            + self.critical_issues
        )

    def to_dict(self) -> dict:
        """Convert the validation run to a dictionary."""
        return {
            "id": self.id,
            "run_type": self.run_type,
            "name": self.name,
            "description": self.description,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "estimated_completion": (
                self.estimated_completion.isoformat()
                if self.estimated_completion
                else None
            ),
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "errors": self.errors,
            "critical_issues": self.critical_issues,
            "execution_time_seconds": self.execution_time_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "warning_rate": self.warning_rate,
            "duration_seconds": self.duration_seconds,
            "created_by": self.created_by,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
        }

    @classmethod
    def get_recent_runs(cls, limit: int = 10, run_type: str = None, status: str = None):
        """Get recent validation runs with optional filtering."""
        query = cls.query.order_by(cls.started_at.desc())

        if run_type:
            query = query.filter_by(run_type=run_type)
        if status:
            query = query.filter_by(status=status)

        return query.limit(limit).all()

    @classmethod
    def get_runs_by_user(cls, user_id: int, limit: int = 50):
        """Get validation runs initiated by a specific user."""
        return (
            cls.query.filter_by(created_by=user_id)
            .order_by(cls.started_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_failed_runs(cls, limit: int = 20):
        """Get recent failed validation runs."""
        return (
            cls.query.filter_by(status="failed")
            .order_by(cls.started_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_running_runs(cls):
        """Get all currently running validation runs."""
        return cls.query.filter_by(status="running").all()

    @classmethod
    def cleanup_old_runs(cls, days: int = 90):
        """Clean up old validation runs and their associated data."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_runs = cls.query.filter(cls.completed_at < cutoff_date).all()

        for run in old_runs:
            db.session.delete(run)

        db.session.commit()
        return len(old_runs)
