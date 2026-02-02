"""
Event Flag Model
================

Auto-flagging system for identifying virtual events that need human attention.
Supports Phase D-1 of the Pathful Import refactor.

Key Features:
- Auto-created flags for data quality issues
- Resolution tracking with audit trail
- District-scoped visibility for admin users

Flag Types:
- NEEDS_ATTENTION: Draft event with past date
- MISSING_TEACHER: Event has no teacher assigned
- MISSING_PRESENTER: Completed event has no presenter
- NEEDS_REASON: Cancelled event has no cancellation reason
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


class FlagType:
    """Flag type constants for event issues"""

    NEEDS_ATTENTION = "needs_attention"  # Draft + past date
    MISSING_TEACHER = "missing_teacher"  # No teacher assigned
    MISSING_PRESENTER = "missing_presenter"  # Completed + no presenter
    NEEDS_REASON = "needs_reason"  # Cancelled + no reason

    @classmethod
    def all_types(cls):
        """Return all valid flag types"""
        return [
            cls.NEEDS_ATTENTION,
            cls.MISSING_TEACHER,
            cls.MISSING_PRESENTER,
            cls.NEEDS_REASON,
        ]

    @classmethod
    def display_name(cls, flag_type):
        """Return human-readable display name for flag type"""
        names = {
            cls.NEEDS_ATTENTION: "Needs Attention",
            cls.MISSING_TEACHER: "Missing Teacher",
            cls.MISSING_PRESENTER: "Missing Presenter",
            cls.NEEDS_REASON: "Needs Cancellation Reason",
        }
        return names.get(flag_type, flag_type)


class EventFlag(db.Model):
    """
    Flags for events that need human attention.

    Automatically created during import scanning and manually resolved
    by staff or district admins.

    Database Table:
        event_flag - Stores event quality flags

    Key Features:
        - Links to Event model
        - Tracks creation source (import scan, manual)
        - Resolution with notes and user audit
        - Auto-resolution when underlying issue is fixed
    """

    __tablename__ = "event_flag"

    id = Column(Integer, primary_key=True)
    event_id = Column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type = Column(String(50), nullable=False, index=True)

    # Creation info
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by = Column(Integer, ForeignKey("users.id"))
    created_source = Column(
        String(50), default="import_scan"
    )  # 'import_scan', 'manual', 'nightly_scan'

    # Resolution info
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolution_notes = Column(Text)
    auto_resolved = Column(Boolean, default=False)  # True if fixed by system

    # Relationships
    event = relationship("Event", backref="flags")
    creator = relationship("User", foreign_keys=[created_by])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __init__(
        self,
        event_id,
        flag_type,
        created_by=None,
        created_source="import_scan",
    ):
        """
        Initialize an event flag.

        Args:
            event_id: FK to Event
            flag_type: Type of flag (from FlagType constants)
            created_by: User ID who created (None for system)
            created_source: How the flag was created
        """
        self.event_id = event_id
        self.flag_type = flag_type
        self.created_by = created_by
        self.created_source = created_source

    def resolve(self, notes=None, resolved_by=None, auto=False):
        """
        Mark this flag as resolved.

        Args:
            notes: Optional resolution notes
            resolved_by: User ID who resolved (None for auto)
            auto: True if automatically resolved by the system
        """
        self.is_resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        self.resolution_notes = notes
        self.auto_resolved = auto

    @property
    def flag_type_display(self):
        """Human-readable flag type name"""
        return FlagType.display_name(self.flag_type)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "flag_type": self.flag_type,
            "flag_type_display": self.flag_type_display,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "created_source": self.created_source,
            "is_resolved": self.is_resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "auto_resolved": self.auto_resolved,
        }

    def __repr__(self):
        status = "resolved" if self.is_resolved else "open"
        return f"<EventFlag {self.id}: {self.flag_type} ({status}) for event {self.event_id}>"
