"""
Sync Log Model
==============

This module defines the SyncLog model for tracking Salesforce sync operations.
It stores historical sync results including timestamps, record counts, and errors.

Model:
    SyncLog: Tracks sync operation results for monitoring and debugging

Fields:
    - sync_type: Type of sync (events, participants, etc.)
    - started_at: When the sync operation started
    - completed_at: When the sync operation completed
    - status: Success, Failed, or Partial
    - records_processed: Number of records successfully processed
    - records_failed: Number of records that failed processing
    - records_skipped: Number of records skipped
    - error_message: Error message if sync failed
    - error_details: Detailed error information (JSON)
"""

from datetime import datetime, timezone
from enum import Enum

from models import db


class SyncStatus(Enum):
    """Enumeration of possible sync statuses."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SyncLog(db.Model):
    """
    Model for tracking Salesforce sync operations.

    Provides historical record of all sync operations including success/failure
    status, record counts, and error details for monitoring and debugging.
    """

    __tablename__ = "sync_logs"

    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(50), nullable=False, index=True)
    started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), nullable=False, default=SyncStatus.SUCCESS.value)
    records_processed = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    records_skipped = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    error_details = db.Column(db.Text)  # JSON string for detailed errors
    # Delta sync watermark - stores the timestamp to use as the baseline for next delta sync
    last_sync_watermark = db.Column(db.DateTime(timezone=True))
    # Recovery buffer for next delta sync (hours). Set to 48 after failed runs. (TD-055)
    recovery_buffer_hours = db.Column(db.Integer, default=1, nullable=False)
    # Track if this was a delta (incremental) or full sync
    is_delta_sync = db.Column(db.Boolean, default=False)

    @property
    def duration_seconds(self):
        """Calculate the duration of the sync in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __repr__(self):
        return f"<SyncLog {self.sync_type} {self.status} at {self.started_at}>"

    def to_dict(self):
        """Convert sync log to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "status": self.status,
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "records_skipped": self.records_skipped,
            "error_message": self.error_message,
            "recovery_buffer_hours": self.recovery_buffer_hours,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else None
            ),
        }

    @staticmethod
    def get_latest_by_type(sync_type):
        """Get the most recent sync log for a given sync type."""
        return (
            SyncLog.query.filter_by(sync_type=sync_type)
            .order_by(SyncLog.started_at.desc())
            .first()
        )

    @staticmethod
    def get_recent_logs(limit=10):
        """Get the most recent sync logs across all types."""
        return SyncLog.query.order_by(SyncLog.started_at.desc()).limit(limit).all()

    @staticmethod
    def get_last_successful_watermark(sync_type):
        """
        Get the LastModifiedDate watermark from the last successful sync.

        .. deprecated::
            Use ``get_watermark_with_buffer()`` instead for delta sync.
            This method does not apply the recovery buffer set by failed runs
            and will not trigger the 48-hour lookback window after a failure. (TD-055)

        Args:
            sync_type: The type of sync (e.g., 'volunteers', 'events_and_participants')

        Returns:
            datetime or None: The watermark timestamp, or None if no successful sync exists
        """
        log = (
            SyncLog.query.filter_by(sync_type=sync_type)
            .filter(
                SyncLog.status.in_([SyncStatus.SUCCESS.value, SyncStatus.PARTIAL.value])
            )
            .filter(SyncLog.last_sync_watermark.isnot(None))
            .order_by(SyncLog.started_at.desc())
            .first()
        )
        return log.last_sync_watermark if log else None

    @staticmethod
    def get_watermark_with_buffer(sync_type):
        """
        Get the watermark + recovery buffer from the last sync that set one.

        Unlike get_last_successful_watermark(), this includes failed runs
        (which now always set a watermark). Returns the buffer hours encoded
        at write time so the caller knows how far back to look. (TD-055)

        Returns:
            (watermark, buffer_hours): watermark is None if no sync has run
        """
        log = (
            SyncLog.query.filter_by(sync_type=sync_type)
            .filter(SyncLog.last_sync_watermark.isnot(None))
            .order_by(SyncLog.started_at.desc())
            .first()
        )
        # Returns 1 as the default buffer; keep in sync with DeltaSyncHelper.DEFAULT_BUFFER_HOURS.
        # Cannot import DeltaSyncHelper here (circular import), so the value is hardcoded.
        if not log:
            return None, 1
        return log.last_sync_watermark, log.recovery_buffer_hours
