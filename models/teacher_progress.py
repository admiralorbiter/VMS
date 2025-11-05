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
- Optional relationship to Teacher model for linking records
- Comprehensive field validation and data integrity

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
- Optional link to Teacher model via teacher_id

Relationships:
- teacher: Optional many-to-one relationship with Teacher model
- created_by: Foreign key to users table

Performance Features:
- Indexed fields for fast queries (email, academic_year, virtual_year, building)
- Composite indexes for common query patterns
- Unique constraints to prevent duplicate records

Data Validation:
- Email format validation
- Academic year and virtual year format validation (YYYY-YYYY pattern)
- Target sessions non-negative validation
- Required field trimming and validation

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

    # Access linked teacher if available
    linked_teacher = teacher.linked_teacher
"""

import logging
import re
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from models import db

logger = logging.getLogger(__name__)


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
        - Optional relationship to Teacher model for data linking
        - Comprehensive field validation and data integrity

    Relationships:
        - teacher: Optional many-to-one relationship with Teacher model
                   Links progress records to actual Teacher contact records
        - created_by: Foreign key to users table for audit trail

    Data Management:
        - Building/school organization
        - Teacher identification (name, email)
        - Grade level tracking
        - Target session goals
        - Progress status calculation

    Data Validation:
        - Email format validation using regex
        - Academic year and virtual year format validation (YYYY-YYYY pattern)
        - Target sessions must be non-negative
        - Required fields (name, building, email) are trimmed and validated

    Performance Features:
        - Indexed fields for fast queries (email, academic_year, virtual_year, building)
        - Composite indexes for common query patterns:
          - (virtual_year, building) for filtering by year and school
          - (virtual_year, email) for email-based lookups
        - Unique constraint on (email, virtual_year) to prevent duplicates

    Usage Examples:
        # Create a new teacher progress record
        teacher_progress = TeacherProgress(
            academic_year="2024-2025",
            virtual_year="2024-2025",
            building="Banneker",
            name="Tahra Arnold",
            email="tahra.arnold@kckps.org",
            grade="K",
            target_sessions=1
        )

        # Access linked teacher if relationship exists
        if teacher_progress.teacher:
            print(f"Linked to Teacher ID: {teacher_progress.teacher.id}")

        # Use linked_teacher property to find teacher by email/name
        linked = teacher_progress.linked_teacher
        if linked:
            print(f"Found teacher: {linked.full_name}")
    """

    __tablename__ = "teacher_progress"

    id = db.Column(Integer, primary_key=True)
    academic_year = db.Column(
        String(10),
        nullable=False,
        index=True,
        comment="Academic year (e.g., '2024-2025')",
    )
    virtual_year = db.Column(
        String(10),
        nullable=False,
        index=True,
        comment="Virtual year (e.g., '2024-2025')",
    )
    building = db.Column(
        String(100), nullable=False, index=True, comment="School/building name"
    )
    name = db.Column(String(200), nullable=False, comment="Teacher full name")
    email = db.Column(
        String(255), nullable=False, index=True, comment="Teacher email address"
    )
    grade = db.Column(String(50), nullable=True, comment="Grade level (K, 1, 2, etc.)")
    target_sessions = db.Column(
        Integer, default=1, nullable=False, comment="Target number of sessions"
    )

    # Optional relationship to Teacher model
    teacher_id = db.Column(
        Integer,
        ForeignKey("teacher.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to Teacher model record",
    )

    # Automatic timestamps for audit trail (timezone-aware, database-side defaults)
    created_at = db.Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at = db.Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )
    created_by = db.Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationship definition
    teacher = db.relationship(
        "Teacher",
        foreign_keys=[teacher_id],
        backref=db.backref("teacher_progress_records", lazy="dynamic"),
        lazy="joined",  # Eager load teacher for common queries
    )

    # Table-level constraints and indexes
    __table_args__ = (
        # Composite index for common filtering pattern (year + building)
        Index("idx_teacher_progress_virtual_year_building", "virtual_year", "building"),
        # Composite index for email lookups by year
        Index("idx_teacher_progress_virtual_year_email", "virtual_year", "email"),
        # Unique constraint to prevent duplicate teacher records for same year
        db.UniqueConstraint(
            "email", "virtual_year", name="uix_teacher_progress_email_virtual_year"
        ),
    )

    # Field validations
    @validates("email")
    def validate_email(self, key, value):
        """
        Validate email format using regex pattern.

        This validation is intentionally lenient to handle common edge cases
        like emails with spaces, extra characters, or non-standard formats
        that might come from spreadsheet imports.

        Args:
            key: Field name being validated
            value: Email value to validate

        Returns:
            str: Validated and trimmed email address (lowercased)

        Raises:
            ValueError: If email format is clearly invalid after cleaning
        """
        if not value:
            raise ValueError("Email is required and cannot be empty")

        # Clean the email: strip whitespace, remove common artifacts
        value = str(value).strip()

        # Remove common artifacts that might appear in spreadsheet imports
        value = value.replace(" ", "")  # Remove spaces
        value = value.replace("'", "")  # Remove single quotes
        value = value.replace('"', "")  # Remove double quotes

        # Fix double @ symbols (e.g., "user@name@domain.com" -> "user@domain.com")
        original_value = value
        at_count = value.count("@")
        if at_count > 1:
            # Keep the last @ and everything after it, remove earlier @ symbols
            parts = value.split("@")
            # Take everything before the first @ as username, and last part as domain
            if len(parts) >= 2:
                username = parts[0]
                domain = parts[-1]
                value = f"{username}@{domain}"
                logger.warning(
                    f"Fixed email with multiple @ symbols: '{original_value}' -> '{value}'"
                )

        if not value:
            raise ValueError("Email is required and cannot be empty after cleaning")

        value = value.lower()

        # More lenient email regex pattern - allows for common edge cases
        # Allows: user@domain.com, user.name@domain.co.uk, user+tag@domain.com
        # But still requires basic @ and domain structure
        email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, value):
            # Log warning but don't fail - allow it through if it has @ and .
            # This is more forgiving for spreadsheet imports
            if "@" not in value or "." not in value.split("@")[-1]:
                raise ValueError(f"Invalid email format: {value}")
            else:
                # Has @ and domain structure, allow it but log warning
                logger.warning(
                    f"Email '{value}' doesn't match standard pattern but has basic structure, allowing"
                )

        return value

    @validates("academic_year", "virtual_year")
    def validate_year_format(self, key, value):
        """
        Validate year format matches YYYY-YYYY pattern.

        Args:
            key: Field name being validated (academic_year or virtual_year)
            value: Year value to validate

        Returns:
            str: Validated year string

        Raises:
            ValueError: If year format is invalid
        """
        if not value:
            raise ValueError(f"{key} is required and cannot be empty")

        value = value.strip()

        # Pattern: YYYY-YYYY (e.g., "2024-2025")
        year_pattern = r"^\d{4}-\d{4}$"
        if not re.match(year_pattern, value):
            raise ValueError(
                f"Invalid {key} format: {value}. Expected format: YYYY-YYYY (e.g., '2024-2025')"
            )

        # Validate that second year is one more than first year
        try:
            start_year, end_year = value.split("-")
            if int(end_year) != int(start_year) + 1:
                logger.warning(
                    f"{key} may be invalid: end year ({end_year}) is not one year after start year ({start_year})"
                )
        except ValueError:
            pass  # Already validated by regex

        return value

    @validates("name", "building")
    def validate_required_strings(self, key, value):
        """
        Validate and trim required string fields.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            str: Trimmed value

        Raises:
            ValueError: If value is empty or whitespace only
        """
        if not value or not value.strip():
            raise ValueError(f"{key} is required and cannot be empty")
        return value.strip()

    @validates("target_sessions")
    def validate_target_sessions(self, key, value):
        """
        Validate target_sessions is a non-negative integer.

        Args:
            key: Field name being validated
            value: Target sessions value to validate

        Returns:
            int: Validated non-negative integer

        Raises:
            ValueError: If value is negative
        """
        if value is None:
            return 1  # Default value

        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{key} must be an integer, got: {value}")

        if value < 0:
            raise ValueError(f"{key} must be non-negative, got: {value}")

        return value

    @validates("grade")
    def validate_grade(self, key, value):
        """
        Validate and trim grade field (optional).

        Args:
            key: Field name being validated
            value: Grade value to validate

        Returns:
            str or None: Trimmed grade value or None
        """
        if value is None:
            return None
        return value.strip() if value.strip() else None

    def get_progress_status(self, completed_sessions=0, planned_sessions=0):
        """
        Calculate progress status based on completed and planned sessions.

        Args:
            completed_sessions: Number of completed sessions
            planned_sessions: Number of planned/upcoming sessions

        Returns:
            dict: Progress status information containing:
                - status: Status key ("achieved", "in_progress", "not_started")
                - status_text: Human-readable status text
                - status_class: CSS class for styling
                - progress_percentage: Percentage completion (0-100)
                - completed_sessions: Number of completed sessions
                - planned_sessions: Number of planned sessions
                - needed_sessions: Number of additional sessions needed to meet goal

        Note:
            Handles division by zero and negative values gracefully.
            Logs errors but does not raise exceptions to ensure progress
            calculation always succeeds.
        """
        try:
            # Normalize input values
            completed_sessions = max(
                0, int(completed_sessions) if completed_sessions else 0
            )
            planned_sessions = max(0, int(planned_sessions) if planned_sessions else 0)
            total_sessions = completed_sessions + planned_sessions

            # Determine status based on progress
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

            # Calculate progress percentage
            if self.target_sessions > 0:
                progress_percentage = min(
                    100, (completed_sessions / self.target_sessions) * 100
                )
            else:
                progress_percentage = 0
                logger.warning(
                    f"TeacherProgress {self.id} has target_sessions=0, progress percentage set to 0"
                )

            return {
                "status": status,
                "status_text": status_text,
                "status_class": status_class,
                "progress_percentage": round(progress_percentage, 2),
                "completed_sessions": completed_sessions,
                "planned_sessions": planned_sessions,
                "needed_sessions": max(0, self.target_sessions - total_sessions),
            }

        except Exception as e:
            logger.error(
                f"Error calculating progress status for TeacherProgress {self.id}: {str(e)}"
            )
            # Return safe default values on error
            return {
                "status": "not_started",
                "status_text": "Error Calculating",
                "status_class": "error",
                "progress_percentage": 0,
                "completed_sessions": completed_sessions,
                "planned_sessions": planned_sessions,
                "needed_sessions": self.target_sessions,
            }

    @property
    def linked_teacher(self):
        """
        Attempt to find and link to a Teacher record by email or name.

        This property searches for a matching Teacher record using:
        1. Direct relationship via teacher_id (if already linked)
        2. Email matching with Teacher's primary email
        3. Name matching with Teacher's first_name and last_name

        Returns:
            Teacher or None: Matching Teacher record if found, None otherwise

        Note:
            This is a computed property that performs database queries.
            Consider caching the result if called multiple times in a loop.
        """
        # First check if already linked via teacher_id
        if self.teacher_id and self.teacher:
            return self.teacher

        try:
            # Import here to avoid circular imports
            from models.teacher import Teacher

            # Try to find by email (most reliable)
            if self.email:
                # Import Email model for join
                from models.contact import Email

                # Check Teacher's primary email via Email relationship
                teacher_by_email = (
                    Teacher.query.join(Email, Teacher.id == Email.contact_id)
                    .filter(Email.email == self.email.lower(), Email.primary == True)
                    .first()
                )
                if teacher_by_email:
                    return teacher_by_email

            # Try to find by name (less reliable, may have duplicates)
            if self.name:
                name_parts = self.name.strip().split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = " ".join(name_parts[1:])

                    teacher_by_name = Teacher.query.filter(
                        db.func.lower(Teacher.first_name) == db.func.lower(first_name),
                        db.func.lower(Teacher.last_name) == db.func.lower(last_name),
                    ).first()

                    if teacher_by_name:
                        return teacher_by_name

        except Exception as e:
            logger.warning(
                f"Error finding linked teacher for TeacherProgress {self.id}: {str(e)}"
            )

        return None

    def to_dict(self, include_progress=False, completed_sessions=0, planned_sessions=0):
        """
        Convert to dictionary for API responses.

        Args:
            include_progress: If True, includes progress status information
            completed_sessions: Number of completed sessions (required if include_progress=True)
            planned_sessions: Number of planned sessions (required if include_progress=True)

        Returns:
            dict: Dictionary representation with progress data including:
                - Basic fields (id, academic_year, virtual_year, etc.)
                - Timestamps (created_at, updated_at)
                - Linked teacher information (if available)
                - Progress status (if include_progress=True)
        """
        result = {
            "id": self.id,
            "academic_year": self.academic_year,
            "virtual_year": self.virtual_year,
            "building": self.building,
            "name": self.name,
            "email": self.email,
            "grade": self.grade,
            "target_sessions": self.target_sessions,
            "teacher_id": self.teacher_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at is not None else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
            "created_by": self.created_by,
        }

        # Include linked teacher information if available
        if self.teacher:
            result["teacher"] = {
                "id": self.teacher.id,
                "name": self.teacher.full_name,
                "email": self.teacher.primary_email,
            }
        elif self.linked_teacher:
            # Include linked teacher found via property (not yet saved to database)
            linked = self.linked_teacher
            result["linked_teacher"] = {
                "id": linked.id,
                "name": linked.full_name,
                "email": linked.primary_email,
            }
            result["teacher_id"] = linked.id

        # Include progress status if requested
        if include_progress:
            result["progress"] = self.get_progress_status(
                completed_sessions, planned_sessions
            )

        return result

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing ID, teacher name, and building
        """
        return f"<TeacherProgress(id={self.id}, name='{self.name}', building='{self.building}')>"

    def __str__(self):
        """
        Human-readable string representation.

        Returns:
            str: Human-readable representation showing teacher name and building
        """
        return f"{self.name} - {self.building} ({self.virtual_year})"
