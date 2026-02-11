"""
Teacher Data Flag Model
=======================

Flagging system for Virtual Admins to report data issues on teacher
progress records (missing sessions, shouldn't-be-tracked, etc.).

Flag Types:
- missing_session: Teacher completed a session but it wasn't recorded
- not_tracked: Teacher/person shouldn't be on the tracking list
- other: Freeform issue
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


class TeacherDataFlagType:
    """Constants for teacher data flag types."""

    MISSING_SESSION = "missing_session"
    NOT_TRACKED = "not_tracked"
    OTHER = "other"

    @classmethod
    def all_types(cls):
        return [cls.MISSING_SESSION, cls.NOT_TRACKED, cls.OTHER]

    @classmethod
    def display_name(cls, flag_type):
        names = {
            cls.MISSING_SESSION: "Missing Session",
            cls.NOT_TRACKED: "Shouldn't Be On List",
            cls.OTHER: "Other",
        }
        return names.get(flag_type, flag_type)


class TeacherDataFlag(db.Model):
    """
    Flags for teacher data issues reported by Virtual Admins.

    Database Table:
        teacher_data_flag
    """

    __tablename__ = "teacher_data_flag"

    id = Column(Integer, primary_key=True)
    teacher_progress_id = Column(
        Integer,
        ForeignKey("teacher_progress.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type = Column(String(50), nullable=False)
    details = Column(Text)  # e.g. session name for "missing_session"

    # Status
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)

    # Creation info
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by = Column(Integer, ForeignKey("users.id"))

    # Resolution info
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolution_notes = Column(Text)

    # Relationships
    teacher_progress = relationship("TeacherProgress", backref="data_flags")
    creator = relationship("User", foreign_keys=[created_by])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def resolve(self, notes=None, resolved_by=None):
        self.is_resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = resolved_by
        self.resolution_notes = notes

    @property
    def flag_type_display(self):
        return TeacherDataFlagType.display_name(self.flag_type)

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_progress_id": self.teacher_progress_id,
            "flag_type": self.flag_type,
            "flag_type_display": self.flag_type_display,
            "details": self.details,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
        }

    def __repr__(self):
        status = "resolved" if self.is_resolved else "open"
        return f"<TeacherDataFlag {self.id}: {self.flag_type} ({status}) for tp {self.teacher_progress_id}>"
