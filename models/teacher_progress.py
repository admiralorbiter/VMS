"""
Teacher Progress Models Module
=============================

This module defines the TeacherProgress model for tracking specific teachers'
progress in virtual sessions for Kansas City Kansas Public Schools.

Key Features:
- Tracks predefined teachers from imported Google Sheets
- Monitors completion status against district goals
- Organizes teachers by building/school
- Tracks target vs actual session completion
- Academic year and virtual year organization

Database Table:
- teacher_progress: Stores teacher progress tracking data

Data Structure:
- Building (school name)
- Teacher name and email
- Grade level
- Target sessions (default: 1)
- Completed sessions (calculated from virtual sessions)
- Planned sessions (upcoming virtual sessions)
- Progress status tracking

Usage Examples:
    # Create a new teacher progress record
    teacher = TeacherProgress(
        academic_year="2024-2025",
        virtual_year="2024-2025",
        building="Banneker",
        name="Tahra Arnold",
        email="tahra.arnold@kckps.org",
        grade="K",
        target_sessions=1
    )

    # Get all teachers for a specific building
    teachers = TeacherProgress.query.filter_by(
        academic_year="2024-2025",
        building="Banneker"
    ).all()
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from models import db


class TeacherProgress(db.Model):
    """
    Model for tracking teacher progress in virtual sessions.

    This model stores predefined teachers from Google Sheets imports
    and tracks their progress against district goals for Kansas City
    Kansas Public Schools.

    Database Table:
        teacher_progress - Stores teacher progress tracking data

    Key Features:
        - Tracks predefined teachers from imported data
        - Monitors completion status against goals
        - Organizes by building/school and grade level
        - Academic year and virtual year organization
        - Target vs actual session tracking

    Data Management:
        - Building/school organization
        - Teacher identification (name, email)
        - Grade level tracking
        - Target session goals
        - Progress status calculation
    """

    __tablename__ = "teacher_progress"

    id = Column(Integer, primary_key=True)
    academic_year = Column(String(10), nullable=False)  # e.g., "2024-2025"
    virtual_year = Column(String(10), nullable=False)  # e.g., "2024-2025"
    building = Column(String(100), nullable=False)  # School/building name
    name = Column(String(200), nullable=False)  # Teacher full name
    email = Column(String(255), nullable=False)  # Teacher email
    grade = Column(String(50), nullable=True)  # Grade level (K, 1, 2, etc.)
    target_sessions = Column(Integer, default=1)  # Target number of sessions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(Integer, db.ForeignKey("users.id"))

    def __init__(
        self,
        academic_year,
        virtual_year,
        building,
        name,
        email,
        grade=None,
        target_sessions=1,
        created_by=None,
    ):
        """
        Initialize a new teacher progress record.

        Args:
            academic_year: Academic year (e.g., "2024-2025")
            virtual_year: Virtual year (e.g., "2024-2025")
            building: School/building name
            name: Teacher full name
            email: Teacher email address
            grade: Grade level (optional)
            target_sessions: Target number of sessions (default: 1)
            created_by: User ID who created this record
        """
        self.academic_year = academic_year
        self.virtual_year = virtual_year
        self.building = building
        self.name = name
        self.email = email
        self.grade = grade
        self.target_sessions = target_sessions
        self.created_by = created_by

    def get_progress_status(self, completed_sessions=0, planned_sessions=0):
        """
        Calculate progress status based on completed and planned sessions.

        Args:
            completed_sessions: Number of completed sessions
            planned_sessions: Number of planned/upcoming sessions

        Returns:
            dict: Progress status information
        """
        total_sessions = completed_sessions + planned_sessions

        if completed_sessions >= self.target_sessions:
            status = "achieved"
            status_text = "Goal Achieved"
            status_class = "achieved"
        elif total_sessions >= self.target_sessions:
            status = "in_progress"
            status_text = "In Progress"
            status_class = "in_progress"
        else:
            status = "not_started"
            status_text = "Needs Planning"
            status_class = "not_started"

        progress_percentage = (
            min(100, (completed_sessions / self.target_sessions) * 100)
            if self.target_sessions > 0
            else 0
        )

        return {
            "status": status,
            "status_text": status_text,
            "status_class": status_class,
            "progress_percentage": progress_percentage,
            "completed_sessions": completed_sessions,
            "planned_sessions": planned_sessions,
            "needed_sessions": max(0, self.target_sessions - total_sessions),
        }

    def to_dict(self):
        """
        Convert to dictionary for API responses.

        Returns:
            dict: Dictionary representation with progress data
        """
        return {
            "id": self.id,
            "academic_year": self.academic_year,
            "virtual_year": self.virtual_year,
            "building": self.building,
            "name": self.name,
            "email": self.email,
            "grade": self.grade,
            "target_sessions": self.target_sessions,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
            "created_by": self.created_by,
        }

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing teacher and building
        """
        return f"<TeacherProgress {self.name} - {self.building}>"
