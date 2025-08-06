"""
Class Model Module
=================

This module defines the Class model for managing school classes and cohorts
in the VMS system. It provides class information storage and relationships
with schools and students.

Key Features:
- School class and cohort management
- Student enrollment tracking
- Academic year organization
- Salesforce integration
- School relationship management
- Student count tracking
- Salesforce URL generation

Database Table:
- class: Stores school class and cohort information

Class Management:
- Class name and identification
- Academic year tracking
- School assignment and relationships
- Student enrollment tracking
- Salesforce record synchronization

Student Relationships:
- One-to-many relationship with Student model
- Student count calculation
- Active student filtering
- Enrollment status tracking

School Relationships:
- Many-to-one relationship with School model
- School assignment tracking
- School-specific class organization
- Academic year alignment

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Class record mapping and tracking
- School relationship synchronization
- Student enrollment data sync

Academic Year Management:
- Class year tracking for organization
- Year-based filtering and reporting
- Academic calendar alignment
- Cohort management

Usage Examples:
    # Create a new class
    class_obj = Class(
        name="10th Grade Science",
        salesforce_id="a1b2c3d4e5f6g7h8i9",
        school_salesforce_id="0015f00000JVZsFAAX",
        class_year=2024
    )

    # Get class student count
    count = class_obj.student_count

    # Get Salesforce URL
    sf_url = class_obj.salesforce_url

    # Get active students
    active_students = class_obj.get_active_students()
"""

from datetime import datetime, timezone

from sqlalchemy import Index
from sqlalchemy.orm import relationship

from models import db


class Class(db.Model):
    """
    Class model representing school classes/cohorts in the system.

    This model maintains relationships between schools and their classes,
    storing both internal and Salesforce-related identifiers. It provides
    comprehensive class management including student enrollment tracking
    and academic year organization.

    Database Table:
        class - Stores school class and cohort information

    Key Features:
        - School class and cohort management
        - Student enrollment tracking
        - Academic year organization
        - Salesforce integration
        - School relationship management
        - Student count tracking
        - Salesforce URL generation

    Class Management:
        - Class name and identification
        - Academic year tracking
        - School assignment and relationships
        - Student enrollment tracking
        - Salesforce record synchronization

    Student Relationships:
        - One-to-many relationship with Student model
        - Student count calculation
        - Active student filtering
        - Enrollment status tracking

    School Relationships:
        - Many-to-one relationship with School model
        - School assignment tracking
        - School-specific class organization
        - Academic year alignment

    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - Class record mapping and tracking
        - School relationship synchronization
        - Student enrollment data sync

    Academic Year Management:
        - Class year tracking for organization
        - Year-based filtering and reporting
        - Academic calendar alignment
        - Cohort management

    Data Validation:
        - Class name is required
        - Salesforce ID is unique and required
        - School relationship is required
        - Class year is required for organization

    Performance Features:
        - Indexed fields for fast queries
        - Composite index on class_year and school_salesforce_id
        - Optimized student count calculation
        - Efficient relationship management

    Important Dependencies:
        - Referenced by Student model via class_salesforce_id
        - Must maintain salesforce_id uniqueness for data sync
        - School relationship relies on school_salesforce_id matching School.id

    Key Relationships:
        - students: One-to-many relationship with Student model (defined in Student model)
        - school: Explicit relationship through school_salesforce_id
    """

    __tablename__ = "class"

    # Primary key and external identifiers
    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False, index=True)

    # Core class information
    name = db.Column(db.String(255), nullable=False, index=True)
    school_salesforce_id = db.Column(db.String(18), db.ForeignKey("school.id"), nullable=False, index=True)
    class_year = db.Column(db.Integer, nullable=False)  # Academic year number

    # Audit timestamps
    # WARNING: These fields are used by data sync processes - do not modify timestamp behavior
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Explicit relationship with School model
    school = relationship("School", backref=db.backref("classes", lazy="dynamic"), foreign_keys=[school_salesforce_id])

    # Keep only the composite index in __table_args__
    __table_args__ = (Index("idx_class_year_school", "class_year", "school_salesforce_id"),)

    def __repr__(self):
        """
        String representation for debugging and logging.

        Returns:
            str: Debug representation showing class name and year
        """
        return f"<Class {self.name} ({self.class_year})>"

    @property
    def student_count(self):
        """
        Returns the count of students in this class.

        Returns:
            int: Number of students enrolled in this class
        """
        from models.student import Student  # Import here to avoid circular imports

        return Student.query.filter_by(class_salesforce_id=self.salesforce_id).count()

    @property
    def salesforce_url(self):
        """
        Generate Salesforce URL for this class.

        Returns:
            str: URL to Salesforce Class record, or None if no salesforce_id
        """
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Class__c/{self.salesforce_id}/view"
        return None

    def to_dict(self):
        """
        Convert class to dictionary for API responses.

        Returns:
            dict: Dictionary representation of the class with metadata
        """
        try:
            student_count = self.student_count
        except Exception:
            student_count = 0

        return {
            "id": self.id,
            "salesforce_id": self.salesforce_id,
            "name": self.name,
            "school_salesforce_id": self.school_salesforce_id,
            "class_year": self.class_year,
            "student_count": student_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    # Add helper method for future use
    def get_active_students(self):
        """
        Returns query of currently enrolled students.

        Returns:
            Query: Query object for active students in this class
        """
        return self.students.filter_by(active=True)

    # TODO: Consider adding relationships:
    # - Back reference to students (currently defined in Student model)
