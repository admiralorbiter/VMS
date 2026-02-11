"""
Attendance Override Model
=========================

Stores virtual admin corrections to session attendance tracking.
Admin overrides are stored separately from original import data
(Event.educators) so that original data is preserved and overrides
can be rolled back.

Override Actions:
- add: Credit a teacher for a session they attended but weren't recorded for
- remove: Revoke credit for a session where a teacher was incorrectly recorded

Related Requirements:
    FR-VIRTUAL-234 through FR-VIRTUAL-243
    FR-DISTRICT-550 through FR-DISTRICT-553
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


class OverrideAction:
    """Constants for attendance override action types."""

    ADD = "add"
    REMOVE = "remove"

    @classmethod
    def all_actions(cls):
        return [cls.ADD, cls.REMOVE]

    @classmethod
    def display_name(cls, action):
        names = {
            cls.ADD: "Added to Session",
            cls.REMOVE: "Removed from Session",
        }
        return names.get(action, action)


class AttendanceOverride(db.Model):
    """
    Virtual admin attendance override for teacher session tracking.

    Each record represents an admin's decision to add or remove a teacher
    from a session's attendance. Overrides are stored separately from
    the Event.educators field to preserve original import data.

    Database Table:
        attendance_override
    """

    __tablename__ = "attendance_override"

    id = Column(Integer, primary_key=True)

    # Which teacher and which session
    teacher_progress_id = Column(
        Integer,
        ForeignKey("teacher_progress.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Override details
    action = Column(String(10), nullable=False)  # "add" or "remove"
    reason = Column(Text, nullable=False)  # Required reason/note

    # Status — is_active=False means this override has been reversed
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Creation info
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Reversal info (populated when staff reverses an override)
    reversed_at = Column(DateTime(timezone=True))
    reversed_by = Column(Integer, ForeignKey("users.id"))
    reversal_reason = Column(Text)

    # Relationships
    teacher_progress = relationship("TeacherProgress", backref="attendance_overrides")
    event = relationship("Event", backref="attendance_overrides")
    creator = relationship("User", foreign_keys=[created_by])
    reverser = relationship("User", foreign_keys=[reversed_by])

    def reverse(self, reason=None, reversed_by=None):
        """Reverse this override, restoring original attendance state."""
        self.is_active = False
        self.reversed_at = datetime.now(timezone.utc)
        self.reversed_by = reversed_by
        self.reversal_reason = reason

    @property
    def action_display(self):
        return OverrideAction.display_name(self.action)

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_progress_id": self.teacher_progress_id,
            "event_id": self.event_id,
            "action": self.action,
            "action_display": self.action_display,
            "reason": self.reason,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "reversed_at": (self.reversed_at.isoformat() if self.reversed_at else None),
            "reversed_by": self.reversed_by,
            "reversal_reason": self.reversal_reason,
        }

    def __repr__(self):
        status = "active" if self.is_active else "reversed"
        return (
            f"<AttendanceOverride {self.id}: {self.action} ({status}) "
            f"tp={self.teacher_progress_id} event={self.event_id}>"
        )
