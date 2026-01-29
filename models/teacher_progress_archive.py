"""
Teacher Progress Archive Model Module
====================================

This module defines the TeacherProgressArchive model for storing historical
snapshots of teacher progress at the end of each semester.

Database Table:
- teacher_progress_archive: Stores archived progress data

Data Structure:
- Link to original TeacherProgress record
- Semester name (e.g., "Fall 2025")
- Snapshot of progress stats (completed, planned, target)
- Snapshot of status (achieved, in_progress, etc.)
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models import db


class TeacherProgressArchive(db.Model):
    """
    Model for archiving teacher progress at semester boundaries.

    This allows historical reporting of teacher progress for previous semesters
    (e.g. Fall 2025, Spring 2026) even after the main dashboard resets for
    the new semester.
    """

    __tablename__ = "teacher_progress_archive"

    id = Column(Integer, primary_key=True)
    teacher_progress_id = Column(
        Integer, ForeignKey("teacher_progress.id"), nullable=False
    )

    # Semester identification
    semester_name = Column(String(50), nullable=False)  # e.g., "Fall 2025"
    academic_year = Column(String(10), nullable=False)  # e.g., "2025-2026"
    virtual_year = Column(String(10), nullable=False)  # e.g., "2025-2026"

    # Semester date range for refernece
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)

    # Snapshot of stats at time of archive
    completed_sessions = Column(Integer, default=0)
    planned_sessions = Column(Integer, default=0)
    target_sessions = Column(Integer, default=1)

    # Snapshot of status
    status = Column(String(50))  # "achieved", "in_progress", "not_started"
    status_text = Column(String(100))
    progress_percentage = Column(Integer, default=0)

    # Metadata
    archived_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    teacher_progress = relationship("TeacherProgress", backref="archives")
    archiver = relationship("User")

    def __repr__(self):
        return f"<TeacherProgressArchive {self.semester_name} - {self.teacher_progress_id}>"
