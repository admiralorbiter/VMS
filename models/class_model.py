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

from sqlalchemy import Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from models import db
from models.utils import validate_salesforce_id


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
        - Salesforce ID is unique and required, validated for format
        - School relationship is required
        - Class year is required and validated for reasonable range (2000-2100)

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
        - district: Access district through school relationship

    Helper Methods:
        - salesforce_url: Generate Salesforce URL for class record
        - student_count: Get count of all students in class
        - active_student_count: Get count of active students in class
        - district: Access district through school relationship
        - to_dict(): Convert class to dictionary for API responses
        - get_active_students(): Get query of active students
    """

    __tablename__ = "class"

    # Primary key and external identifiers
    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False, index=True)

    # Core class information
    name = db.Column(db.String(255), nullable=False, index=True)
    school_salesforce_id = db.Column(
        db.String(18), db.ForeignKey("school.id"), nullable=False, index=True
    )
    class_year = db.Column(db.Integer, nullable=False)  # Academic year number

    # Automatic timestamps for audit trail (timezone-aware, database-side defaults)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Explicit relationship with School model
    school = relationship(
        "School",
        backref=db.backref("classes", lazy="dynamic"),
        foreign_keys=[school_salesforce_id],
    )

    # Keep only the composite index in __table_args__
    __table_args__ = (
        Index("idx_class_year_school", "class_year", "school_salesforce_id"),
    )

    @validates("salesforce_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validates Salesforce ID format using shared validator.

        Args:
            key (str): The name of the field being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid

        Example:
            >>> class_obj.validate_salesforce_id_field("salesforce_id", "0011234567890ABCD")
            '0011234567890ABCD'
        """
        return validate_salesforce_id(value)

    @validates("class_year")
    def validate_class_year(self, key, value):
        """
        Validates class year is within reasonable range.

        Args:
            key (str): The name of the field being validated
            value: Class year to validate

        Returns:
            int: Validated class year

        Raises:
            ValueError: If class year is outside 2000-2100 range

        Example:
            >>> class_obj.validate_class_year("class_year", 2024)
            2024
        """
        if value is None:
            raise ValueError("Class year is required")
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError("Class year must be an integer")
        if not (2000 <= value <= 2100):
            raise ValueError("Class year must be between 2000 and 2100")
        return value

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

    @property
    def district(self):
        """
        Access district through school relationship.

        Returns:
            District or None: District object if school has district relationship,
                            None otherwise
        """
        if self.school and hasattr(self.school, "district"):
            return self.school.district
        return None

    @property
    def active_student_count(self):
        """
        Returns the count of active students in this class.

        Returns:
            int: Number of active students enrolled in this class
        """
        from models.student import Student  # Import here to avoid circular imports

        return Student.query.filter_by(
            class_salesforce_id=self.salesforce_id, active=True
        ).count()

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

    def get_active_students(self):
        """
        Returns query of currently enrolled students.

        Returns:
            Query: Query object for active students in this class
        """
        return self.students.filter_by(active=True)

    @classmethod
    def from_salesforce(cls, data):
        """
        Creates a Class instance from Salesforce data with proper data cleaning.

        This class method handles the conversion of Salesforce data to Class
        instances, ensuring that empty strings are converted to None values
        and data is properly formatted.

        Args:
            data (dict): Dictionary containing Salesforce class data

        Returns:
            Class: New Class instance with cleaned data

        Example:
            >>> sf_data = {
            ...     "Name": "10th Grade Science",
            ...     "Id": "a1b2c3d4e5f6g7h8i9",
            ...     "School__c": "0015f00000JVZsFAAX",
            ...     "Class_Year__c": "2024"
            ... }
            >>> class_obj = Class.from_salesforce(sf_data)
        """
        # Convert empty strings to None
        cleaned = {}
        for k, v in data.items():
            if v == "":
                cleaned[k] = None
            else:
                cleaned[k] = v

        # Map common Salesforce field names to model attributes
        mapped_data = {
            "name": cleaned.get("Name") or cleaned.get("name"),
            "salesforce_id": cleaned.get("Id") or cleaned.get("salesforce_id"),
            "school_salesforce_id": cleaned.get("School__c")
            or cleaned.get("school_salesforce_id"),
            "class_year": cleaned.get("Class_Year__c") or cleaned.get("class_year"),
        }

        # Remove None values to avoid overwriting with None
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None}

        return cls(**mapped_data)
