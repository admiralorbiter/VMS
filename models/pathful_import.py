"""
Pathful Import Models Module
============================

This module defines models for tracking Pathful data imports into Polaris.
Supports US-304 (Import Pathful export into Polaris) and US-306 (Historical virtual data).

Key Features:
- Import batch audit logging
- Unmatched record tracking for review workflow
- Resolution status management

Database Tables:
- pathful_import_log: Audit trail for import batches
- pathful_unmatched_record: Unmatched records requiring manual review

Related Documentation:
- documentation/content/dev/pathful_import_deployment.md
- documentation/content/dev/pathful_import_recommendations.md
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class PathfulImportType:
    """Import type constants"""

    SESSION_REPORT = "session_report"
    USER_REPORT = "user_report"


class PathfulImportLog(db.Model):
    """
    Audit log for Pathful import batches.

    Tracks each import operation including statistics on processed rows,
    created/updated records, and any errors encountered.

    Database Table:
        pathful_import_log - Stores import batch audit data

    Key Features:
        - Filename and import type tracking
        - Start/complete timestamps for duration calculation
        - Comprehensive statistics (rows, events, teachers, volunteers)
        - Error and unmatched record counts

    Usage Example:
        log = PathfulImportLog(
            filename="Session Report_reports_abc123.xlsx",
            import_type="session_report",
            imported_by=current_user.id
        )
        db.session.add(log)
    """

    __tablename__ = "pathful_import_log"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    import_type = Column(String(50), nullable=False)  # 'session_report', 'user_report'

    # Timestamps
    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True))

    # User who initiated the import
    imported_by = Column(Integer, ForeignKey("users.id"))
    importer = relationship("User", backref="pathful_imports")

    # Processing statistics
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    skipped_rows = Column(
        Integer, default=0
    )  # Rows skipped (e.g., non-PREPKC, students)

    # Event statistics
    created_events = Column(Integer, default=0)
    updated_events = Column(Integer, default=0)

    # Participant statistics
    matched_teachers = Column(Integer, default=0)
    created_teachers = Column(Integer, default=0)
    matched_volunteers = Column(Integer, default=0)
    created_volunteers = Column(Integer, default=0)

    # Error tracking
    unmatched_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_details = Column(Text)  # JSON array of error messages

    # Relationships
    unmatched_records = relationship(
        "PathfulUnmatchedRecord",
        back_populates="import_log",
        cascade="all, delete-orphan",
    )

    def __init__(self, filename, import_type, imported_by=None):
        """
        Initialize a new import log entry.

        Args:
            filename: Name of the uploaded file
            import_type: Type of import ('session_report' or 'user_report')
            imported_by: User ID of the person running the import
        """
        self.filename = filename
        self.import_type = import_type
        self.imported_by = imported_by
        self.started_at = datetime.now(timezone.utc)

    def mark_complete(self):
        """Mark the import as complete with current timestamp."""
        self.completed_at = datetime.now(timezone.utc)

    @property
    def duration_seconds(self):
        """Calculate import duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self):
        """Calculate percentage of successfully processed rows."""
        if self.total_rows > 0:
            return ((self.processed_rows - self.error_count) / self.total_rows) * 100
        return 0

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "filename": self.filename,
            "import_type": self.import_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_seconds": self.duration_seconds,
            "imported_by": self.imported_by,
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "skipped_rows": self.skipped_rows,
            "created_events": self.created_events,
            "updated_events": self.updated_events,
            "matched_teachers": self.matched_teachers,
            "created_teachers": self.created_teachers,
            "matched_volunteers": self.matched_volunteers,
            "created_volunteers": self.created_volunteers,
            "unmatched_count": self.unmatched_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
        }

    def __repr__(self):
        return f"<PathfulImportLog {self.id}: {self.filename}>"


class UnmatchedType:
    """Constants for unmatched record types"""

    TEACHER = "teacher"
    VOLUNTEER = "volunteer"
    EVENT = "event"
    TEACHER_AND_EVENT = "teacher_and_event"
    VOLUNTEER_AND_EVENT = "volunteer_and_event"


class ResolutionStatus:
    """Constants for resolution status"""

    PENDING = "pending"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    CREATED = "created"  # New record was created


class PathfulUnmatchedRecord(db.Model):
    """
    Stores unmatched records from Pathful imports for manual review.

    When the import process cannot match a teacher, volunteer, or event
    to existing records, it creates an entry here for staff review.

    Database Table:
        pathful_unmatched_record - Stores unmatched import rows

    Key Features:
        - Links to parent import log
        - Stores full original row data as JSON
        - Tracks match attempts and resolution status
        - Supports audit trail for resolutions

    Usage Example:
        unmatched = PathfulUnmatchedRecord(
            import_log_id=log.id,
            row_number=42,
            raw_data=row_dict,
            unmatched_type="teacher",
            attempted_match_name="Jane Smith"
        )
    """

    __tablename__ = "pathful_unmatched_record"

    id = Column(Integer, primary_key=True)
    import_log_id = Column(
        Integer,
        ForeignKey("pathful_import_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Original data
    row_number = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)  # Full row data for review

    # Match attempt details
    unmatched_type = Column(
        String(50), nullable=False
    )  # 'teacher', 'volunteer', 'event', etc.
    attempted_match_name = Column(String(255))
    attempted_match_email = Column(String(255))
    attempted_match_session_id = Column(String(100))
    attempted_match_school = Column(String(255))
    attempted_match_organization = Column(String(255))

    # Resolution tracking
    resolution_status = Column(String(50), default="pending", nullable=False)
    resolution_notes = Column(Text)
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))

    # If resolved by creating/matching a record, store the reference
    resolved_teacher_id = Column(Integer, ForeignKey("teacher.id"))
    resolved_volunteer_id = Column(Integer, ForeignKey("volunteer.id"))
    resolved_event_id = Column(Integer, ForeignKey("event.id"))

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    import_log = relationship("PathfulImportLog", back_populates="unmatched_records")
    resolver = relationship("User", foreign_keys=[resolved_by])
    resolved_teacher = relationship("Teacher", foreign_keys=[resolved_teacher_id])
    resolved_volunteer = relationship("Volunteer", foreign_keys=[resolved_volunteer_id])
    resolved_event = relationship("Event", foreign_keys=[resolved_event_id])

    def __init__(
        self,
        import_log_id,
        row_number,
        raw_data,
        unmatched_type,
        attempted_match_name=None,
        attempted_match_email=None,
        attempted_match_session_id=None,
        attempted_match_school=None,
        attempted_match_organization=None,
    ):
        """
        Initialize an unmatched record.

        Args:
            import_log_id: FK to parent PathfulImportLog
            row_number: Row number in the original import file
            raw_data: Full row data as dictionary
            unmatched_type: Type of unmatched record
            attempted_match_name: Name that was searched for
            attempted_match_email: Email that was searched for
            attempted_match_session_id: Session ID searched for
            attempted_match_school: School name searched for
            attempted_match_organization: Organization name searched for
        """
        self.import_log_id = import_log_id
        self.row_number = row_number
        self.raw_data = raw_data
        self.unmatched_type = unmatched_type
        self.attempted_match_name = attempted_match_name
        self.attempted_match_email = attempted_match_email
        self.attempted_match_session_id = attempted_match_session_id
        self.attempted_match_school = attempted_match_school
        self.attempted_match_organization = attempted_match_organization
        self.resolution_status = ResolutionStatus.PENDING

    def resolve(
        self,
        status,
        notes=None,
        resolved_by=None,
        teacher_id=None,
        volunteer_id=None,
        event_id=None,
    ):
        """
        Mark this record as resolved.

        Args:
            status: Resolution status (RESOLVED, IGNORED, CREATED)
            notes: Optional notes about the resolution
            resolved_by: User ID who resolved this
            teacher_id: If matched/created a teacher
            volunteer_id: If matched/created a volunteer
            event_id: If matched/created an event
        """
        self.resolution_status = status
        self.resolution_notes = notes
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_teacher_id = teacher_id
        self.resolved_volunteer_id = volunteer_id
        self.resolved_event_id = event_id

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "import_log_id": self.import_log_id,
            "row_number": self.row_number,
            "raw_data": self.raw_data,
            "unmatched_type": self.unmatched_type,
            "attempted_match_name": self.attempted_match_name,
            "attempted_match_email": self.attempted_match_email,
            "attempted_match_session_id": self.attempted_match_session_id,
            "attempted_match_school": self.attempted_match_school,
            "attempted_match_organization": self.attempted_match_organization,
            "resolution_status": self.resolution_status,
            "resolution_notes": self.resolution_notes,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_teacher_id": self.resolved_teacher_id,
            "resolved_volunteer_id": self.resolved_volunteer_id,
            "resolved_event_id": self.resolved_event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PathfulUnmatchedRecord {self.id}: {self.unmatched_type} row {self.row_number}>"
