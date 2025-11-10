"""
Student Model Module
===================

This module defines the Student model for managing student information in the VMS system.
It inherits from the Contact model and provides student-specific academic and demographic data.

Key Features:
- Student academic information tracking
- School and class relationships
- Teacher assignment tracking
- Demographic data collection
- Program participation tracking
- Grade level management
- Student ID tracking
- Salesforce integration

Database Table:
- student: Inherits from contact table with polymorphic identity

Academic Information:
- Current grade level tracking
- Legacy grade data from Salesforce
- Student ID for school-specific identification
- School and class relationships
- Teacher assignment tracking

Demographic Data:
- Racial/ethnic identification
- English Language Learner status
- Gifted program participation
- Lunch program status
- School code tracking

Program Participation:
- ELL (English Language Learner) program
- Gifted program participation
- Lunch program status
- Special education tracking

Relationships:
- Many-to-one with School model
- Many-to-one with Class model
- Many-to-one with Teacher model
- Inherits from Contact model

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Student record mapping and tracking
- Grade and demographic data sync
- School and class relationship sync

Usage Examples:
    # Create a new student
    student = Student(
        first_name="John",
        last_name="Doe",
        current_grade=10,
        student_id="STU123456",
        school_id="0015f00000JVZsFAAX",
        gifted=True
    )

    # Get student's school
    school = student.school

    # Get student's teacher
    teacher = student.teacher

    # Validate student data
    student.validate_required_fields('first_name', 'John')
"""

import logging

import pandas as pd
from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates

from config.model_constants import GRADE_MAX, GRADE_MIN
from models import db
from models.contact import (
    Contact,
    ContactTypeEnum,
    Email,
    GenderEnum,
    LocalStatusEnum,
    Phone,
    RaceEthnicityEnum,
)
from models.utils import validate_salesforce_id

logger = logging.getLogger(__name__)


class Student(Contact):
    """
    Student Model - Represents a student in the education system.

    This model inherits from Contact for basic contact information and adds
    student-specific academic and demographic data. It maintains relationships
    with schools, classes, and teachers for comprehensive student tracking.

    Database Table:
        student - Inherits from contact table with polymorphic identity

    Key Features:
        - Student academic information tracking
        - School and class relationships
        - Teacher assignment tracking
        - Demographic data collection
        - Program participation tracking
        - Grade level management
        - Student ID tracking
        - Salesforce integration

    Academic Information:
        - current_grade: Current grade level (0-12)
        - legacy_grade: Legacy grade data from Salesforce
        - student_id: School-specific student identifier
        - school_id: Reference to student's school
        - class_salesforce_id: Reference to student's class
        - teacher_id: Reference to student's teacher

    Demographic Data:
        - racial_ethnic: Student's racial/ethnic identification
        - school_code: School-specific code
        - ell_language: English Language Learner primary language
        - gifted: Gifted program participation status
        - lunch_status: Student lunch program status

    Program Participation:
        - ELL (English Language Learner) program tracking
        - Gifted program participation
        - Lunch program status
        - Special education tracking

    Relationships:
        - Many-to-one with School model
        - Many-to-one with Class model
        - Many-to-one with Teacher model
        - Inherits from Contact model

    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - Student record mapping and tracking
        - Grade and demographic data sync
        - School and class relationship sync

    Data Validation:
        - Required fields validation (first_name, last_name)
        - Grade level validation (0-12)
        - Student ID uniqueness
        - School relationship validation

    Performance Features:
        - Indexed foreign keys for fast joins
        - Composite index on school_id and current_grade
        - Eager loading for common relationships
        - Optimized query patterns
    """

    __tablename__ = "student"

    id = db.Column(Integer, ForeignKey("contact.id"), primary_key=True)
    active = db.Column(db.Boolean, default=True)

    __mapper_args__ = {
        "polymorphic_identity": "student",
    }

    # Academic Information
    current_grade = db.Column(
        Integer, nullable=True, comment="Current grade level of the student"
    )
    legacy_grade = db.Column(String(50), comment="Legacy Grade__C from Salesforce")
    student_id = db.Column(
        String(50),
        index=True,  # Add index for faster lookups
        comment="Local_Student_ID__c - School-specific identifier",
    )

    # Institutional Relationships
    school_id = db.Column(
        String(18),
        db.ForeignKey("school.id", ondelete="SET NULL"),
        index=True,  # Add index for foreign key
        comment="References School.id (Salesforce ID)",
    )

    class_salesforce_id = db.Column(
        String(18),
        db.ForeignKey("class.salesforce_id", ondelete="SET NULL"),
        index=True,  # Add index for foreign key
        comment="References Class.salesforce_id",
    )

    teacher_id = db.Column(
        Integer,
        ForeignKey("teacher.id", ondelete="SET NULL"),
        nullable=True,
        index=True,  # Add index for foreign key
        comment="References Teacher.id",
    )

    # Relationship definitions with explicit join conditions
    teacher = db.relationship(
        "Teacher",
        backref=db.backref("students", lazy="dynamic", cascade="all, delete-orphan"),
        foreign_keys=[teacher_id],
        lazy="joined",  # Optimize common queries by eager loading
    )

    school = db.relationship(
        "School", backref=db.backref("students", lazy="dynamic"), lazy="joined"
    )

    class_ref = db.relationship(
        "Class",
        backref=db.backref("students", lazy="dynamic"),
        primaryjoin="Student.class_salesforce_id==Class.salesforce_id",
        lazy="joined",
    )

    # Demographics and Program Participation
    racial_ethnic = db.Column(
        String(100), nullable=True, comment="Student's racial/ethnic identification"
    )

    school_code = db.Column(
        String(50),
        index=True,  # Add index for common lookups
        comment="School-specific code",
    )

    ell_language = db.Column(
        String(50), nullable=True, comment="English Language Learner primary language"
    )

    gifted = db.Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Gifted program participation status",
    )

    lunch_status = db.Column(
        String(50), nullable=True, comment="Student lunch program status"
    )

    __table_args__ = (
        db.Index("idx_student_school_grade", "school_id", "current_grade"),
    )

    # Validation Methods
    @validates("first_name", "last_name")
    def validate_required_fields(self, key, value):
        """
        Validate required fields are not empty.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            Validated value (stripped of whitespace)

        Raises:
            ValueError: If value is empty or whitespace only
        """
        if not value or not value.strip():
            raise ValueError(f"{key} is required and cannot be empty")
        return value.strip()

    @validates("student_id", "school_code", "ell_language")
    def validate_string_fields(self, key, value):
        """
        Validate and clean string fields by stripping whitespace.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            str or None: Cleaned string value or None if empty
        """
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return value

    @validates("current_grade")
    def validate_grade(self, key, grade):
        """
        Validate grade is within acceptable range.

        Args:
            key: Field name being validated
            grade: Grade level to validate

        Returns:
            int or None: Validated grade level

        Raises:
            ValueError: If grade is outside 0-12 range
        """
        if grade is not None and not (GRADE_MIN <= grade <= GRADE_MAX):
            raise ValueError(f"Grade must be between {GRADE_MIN} and {GRADE_MAX}")
        return grade

    @validates("school_id", "class_salesforce_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validates Salesforce ID format using shared validator.

        Args:
            key: Field name being validated
            value: Salesforce ID to validate

        Returns:
            str or None: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid

        Example:
            >>> student.validate_salesforce_id_field("school_id", "0011234567890ABCD")
            '0011234567890ABCD'
        """
        return validate_salesforce_id(value)

    # Properties
    def __repr__(self):
        """
        String representation of the Student model.

        Returns:
            str: Debug representation showing student ID and full name

        Example:
            >>> repr(student)
            '<Student STU123456: John Doe>'
        """
        student_id = self.student_id or "N/A"
        name = self.full_name if self.first_name and self.last_name else "Unknown"
        return f"<Student {student_id}: {name}>"

    def _get_local_status_assumption(self):
        """
        Get local status assumption for students.

        Students are generally assumed to be local since they attend schools in the
        Kansas City area. This can be overridden by address data if available.

        Returns:
            LocalStatusEnum: Local status assumption for students

        Example:
            >>> student._get_local_status_assumption()
            LocalStatusEnum.local
        """
        try:
            return LocalStatusEnum.local
        except Exception as e:
            logger.warning(
                "Error getting local status assumption for student %d: %s",
                self.id,
                str(e),
            )
            return LocalStatusEnum.local

    # Class Methods
    @classmethod
    def import_from_salesforce(cls, sf_data, db_session):
        """
        Import student data from Salesforce.

        Creates a new student or updates an existing one based on Salesforce
        individual ID. Handles contact information, school relationships, and
        demographic data.

        Args:
            sf_data: Dictionary containing Salesforce student data with fields:
                - Id: Salesforce Contact ID (required)
                - FirstName: Student's first name (required)
                - LastName: Student's last name (required)
                - AccountId: Salesforce Account ID
                - MiddleName: Student's middle name
                - Birthdate: Student's birthdate
                - Local_Student_ID__c: School-specific student identifier
                - npsp__Primary_Affiliation__c: School Salesforce ID
                - Class__c: Class Salesforce ID
                - Legacy_Grade__c: Legacy grade data
                - Current_Grade__c: Current grade level
                - Gender__c: Gender value
                - Racial_Ethnic_Background__c: Racial/ethnic identification
            db_session: SQLAlchemy database session

        Returns:
            tuple: (student_object, is_new_student, error_message)
                - student_object: Student instance or None if error
                - is_new_student: Boolean indicating if student was newly created
                - error_message: String error message or None if successful

        Example:
            >>> sf_data = {
            ...     "Id": "0031234567890ABCD",
            ...     "FirstName": "John",
            ...     "LastName": "Doe",
            ...     "npsp__Primary_Affiliation__c": "0015f00000JVZsFAAX",
            ...     "Current_Grade__c": 10
            ... }
            >>> student, is_new, error = Student.import_from_salesforce(sf_data, db.session)
            >>> if error:
            ...     print(f"Error: {error}")
        """
        try:
            # Extract required fields
            sf_id = sf_data.get("Id")
            first_name = sf_data.get("FirstName", "").strip()
            last_name = sf_data.get("LastName", "").strip()

            if not sf_id or not first_name or not last_name:
                return (
                    None,
                    False,
                    f"Missing required fields for student: {first_name} {last_name}",
                )

            # Check if student already exists
            student = cls.query.filter_by(salesforce_individual_id=sf_id).first()
            is_new = False

            if not student:
                student = cls()
                student.salesforce_individual_id = sf_id
                student.salesforce_account_id = sf_data.get("AccountId")
                db_session.add(student)
                is_new = True

            # Update student fields
            student.first_name = first_name
            student.last_name = last_name
            student.middle_name = sf_data.get("MiddleName", "").strip() or None
            student.birthdate = (
                pd.to_datetime(sf_data["Birthdate"]).date()
                if sf_data.get("Birthdate")
                else None
            )
            student.student_id = (
                str(sf_data.get("Local_Student_ID__c", "")).strip() or None
            )
            student.school_id = (
                str(sf_data.get("npsp__Primary_Affiliation__c", "")).strip() or None
            )
            student.class_salesforce_id = (
                str(sf_data.get("Class__c", "")).strip() or None
            )
            student.legacy_grade = (
                str(sf_data.get("Legacy_Grade__c", "")).strip() or None
            )
            student.current_grade = (
                int(sf_data.get("Current_Grade__c", 0))
                if pd.notna(sf_data.get("Current_Grade__c"))
                else None
            )

            # Handle gender
            gender_value = sf_data.get("Gender__c")
            if gender_value:
                gender_key = gender_value.lower().replace(" ", "_")
                try:
                    student.gender = GenderEnum[gender_key]
                except KeyError:
                    # Log invalid gender but don't fail the import
                    logger.warning(
                        "Invalid gender value for %s %s: %s",
                        first_name,
                        last_name,
                        gender_value,
                    )

            # Handle racial/ethnic background
            racial_ethnic = sf_data.get("Racial_Ethnic_Background__c")
            if racial_ethnic:
                try:
                    student.racial_ethnic = cls.map_racial_ethnic_value(racial_ethnic)
                except Exception as e:
                    logger.warning(
                        "Error processing racial/ethnic value for %s %s: %s - %s",
                        first_name,
                        last_name,
                        racial_ethnic,
                        str(e),
                    )

            return student, is_new, None

        except Exception as e:
            return (
                None,
                False,
                f"Error processing student {sf_data.get('FirstName', '')} {sf_data.get('LastName', '')}: {str(e)}",
            )

    # Static Methods
    @staticmethod
    def map_racial_ethnic_value(value):
        """
        Clean and standardize racial/ethnic values from Salesforce.

        Args:
            value: Raw racial/ethnic value from Salesforce

        Returns:
            str or None: Cleaned and standardized value or None if empty

        Example:
            >>> Student.map_racial_ethnic_value("  Asian  ")
            'Asian'

            >>> Student.map_racial_ethnic_value("")
            None
        """
        if not value:
            return None

        # Clean the input by stripping whitespace
        value = value.strip()

        # Return the cleaned value directly
        return value

    # Instance Methods
    def update_contact_info(self, sf_data, db_session):
        """
        Update student's contact information from Salesforce data.

        Adds or updates email and phone records for the student. Creates new
        contact records if they don't exist, marking them as primary and
        personal type.

        Args:
            sf_data: Dictionary containing Salesforce student data with fields:
                - Email: Email address (optional)
                - Phone: Phone number (optional)
            db_session: SQLAlchemy database session

        Returns:
            tuple: (success, error_message)
                - success: Boolean indicating if update was successful
                - error_message: String error message or None if successful

        Example:
            >>> sf_data = {"Email": "student@example.com", "Phone": "555-1234"}
            >>> success, error = student.update_contact_info(sf_data, db.session)
            >>> if success:
            ...     db.session.commit()
        """
        try:
            # Handle email
            email_address = str(sf_data.get("Email", "")).strip()
            if email_address:
                existing_email = Email.query.filter_by(
                    contact_id=self.id, type=ContactTypeEnum.personal
                ).first()

                if existing_email:
                    existing_email.email = email_address
                else:
                    email_record = Email(
                        contact_id=self.id,
                        email=email_address,
                        type=ContactTypeEnum.personal,
                        primary=True,
                    )
                    db_session.add(email_record)

            # Handle phone
            phone_number = str(sf_data.get("Phone", "")).strip()
            if phone_number:
                existing_phone = Phone.query.filter_by(
                    contact_id=self.id, type=ContactTypeEnum.personal
                ).first()

                if existing_phone:
                    existing_phone.number = phone_number
                else:
                    phone_record = Phone(
                        contact_id=self.id,
                        number=phone_number,
                        type=ContactTypeEnum.personal,
                        primary=True,
                    )
                    db_session.add(phone_record)

            return True, None

        except Exception as e:
            return (
                False,
                f"Error updating contact info for {self.first_name} {self.last_name}: {str(e)}",
            )
