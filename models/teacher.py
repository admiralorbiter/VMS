"""
Teacher Model Module
===================

This module defines the Teacher model for managing teacher information in the VMS system.
It inherits from the Contact model and provides teacher-specific academic and professional data.

Key Features:
- Teacher information management and tracking
- School and department relationships
- Connector program participation tracking
- Event registration and participation
- Status tracking and management
- Salesforce integration
- Email and communication tracking
- CSV data import support

Database Table:
- teacher: Inherits from contact table with polymorphic identity

Teacher Management:
- Teacher identification and contact information
- School and department assignment
- Status tracking (active, inactive, on leave, retired)
- Connector program participation
- Event registration tracking

Connector Program:
- Connector role tracking
- Active status management
- Start and end date tracking
- Role validation and capitalization

Event Participation:
- Event registration tracking
- Upcoming and past events
- Event relationship management
- Registration status tracking

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Teacher record mapping and tracking
- School relationship synchronization
- Contact and affiliation data sync

Status Management:
- ACTIVE: Currently active teacher
- INACTIVE: Not currently active
- ON_LEAVE: Temporarily unavailable
- RETIRED: No longer teaching

Usage Examples:
    # Create a new teacher
    teacher = Teacher(
        first_name="Jane",
        last_name="Smith",
        department="Science",
        school_id="0015f00000JVZsFAAX",
        status=TeacherStatus.ACTIVE
    )

    # Update from CSV data
    teacher.update_from_csv(csv_data)

    # Get teacher's upcoming events
    upcoming = teacher.upcoming_events

    # Get teacher's school
    school = teacher.school
"""

from datetime import datetime, timezone
from enum import Enum
from functools import cached_property

from sqlalchemy import Boolean, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import declared_attr, relationship, validates

from models import db
from models.contact import Contact, ContactTypeEnum, Email, GenderEnum, Phone
from models.school_model import School


class TeacherStatus(str, Enum):
    """
    Enum for tracking teacher status.

    Provides standardized status categories for teacher management
    and workflow tracking.

    Statuses:
        - ACTIVE: Currently active and available for teaching
        - INACTIVE: Not currently active but may return
        - ON_LEAVE: Temporarily unavailable (e.g., maternity leave)
        - RETIRED: No longer teaching
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    RETIRED = "retired"


class Teacher(Contact):
    """
    Teacher model representing educational staff members.

    This model inherits from Contact for basic contact information and adds
    teacher-specific academic and professional data. It maintains relationships
    with schools, events, and connector programs for comprehensive teacher tracking.

    Database Table:
        teacher - Inherits from contact table with polymorphic identity

    Key Features:
        - Teacher information management and tracking
        - School and department relationships
        - Connector program participation tracking
        - Event registration and participation
        - Status tracking and management
        - Salesforce integration
        - Email and communication tracking
        - CSV data import support

    Teacher Management:
        - Teacher identification and contact information
        - School and department assignment
        - Status tracking (active, inactive, on leave, retired)
        - Connector program participation
        - Event registration tracking

    Connector Program:
        - connector_role: Teacher's role in connector program
        - connector_active: Whether teacher is active in connector program
        - connector_start_date: When teacher joined connector program
        - connector_end_date: When teacher left connector program

    Event Participation:
        - Event registration tracking through EventTeacher
        - Upcoming and past events filtering
        - Event relationship management
        - Registration status tracking

    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - Teacher record mapping and tracking
        - School relationship synchronization
        - Contact and affiliation data sync

    Status Management:
        - ACTIVE: Currently active teacher
        - INACTIVE: Not currently active
        - ON_LEAVE: Temporarily unavailable
        - RETIRED: No longer teaching

    Data Validation:
        - Connector role capitalization
        - Salesforce ID format validation
        - Status change tracking
        - Date range validation for connector program

    Performance Features:
        - Indexed fields for fast queries
        - Composite indexes for common query patterns
        - Eager loading for common relationships
        - Optimized CSV import processing
    """

    __tablename__ = "teacher"

    id = db.Column(Integer, ForeignKey("contact.id"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "teacher", "confirm_deleted_rows": False}

    # Teacher-specific fields
    department = db.Column(String(50), nullable=True, index=True)
    school_id = db.Column(
        String(255),
        nullable=True,
        index=True,
        comment="Maps to npsp__Primary_Affiliation__c in external systems",
    )

    # Status tracking
    status = db.Column(
        SQLAlchemyEnum(TeacherStatus), default=TeacherStatus.ACTIVE, index=True
    )
    active = db.Column(Boolean, default=True, nullable=False)

    # Connector fields for tracking teacher relationships
    connector_role = db.Column(String(50), nullable=True)
    connector_active = db.Column(Boolean, default=False, nullable=False)
    connector_start_date = db.Column(Date, nullable=True)
    connector_end_date = db.Column(Date, nullable=True)

    # Email tracking fields
    last_email_message = db.Column(Date, nullable=True)
    last_mailchimp_date = db.Column(Date, nullable=True)

    # Salesforce Integration Fields
    salesforce_contact_id = db.Column(
        String(18), unique=True, nullable=True, index=True
    )
    salesforce_school_id = db.Column(
        String(18), nullable=True
    )  # Remove ForeignKey constraint

    # Automatic timestamps for audit trail (timezone-aware, Python-side defaults)
    created_at = db.Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Enhanced event tracking
    event_registrations = db.relationship(
        "EventTeacher", back_populates="teacher", cascade="all, delete-orphan"
    )

    events = db.relationship(
        "Event",
        secondary="event_teacher",
        back_populates="teachers",
        viewonly=True,  # Use event_registrations for modifications
    )

    def _get_local_status_assumption(self):
        """
        Get local status assumption for teachers.

        Teachers are generally assumed to be local since they work in the Kansas City
        area school system. This can be overridden by address data if available.

        Returns:
            LocalStatusEnum: Local status assumption for teachers
        """
        try:
            from models.contact import LocalStatusEnum

            return LocalStatusEnum.local
        except Exception as e:
            print(
                f"Error getting local status assumption for teacher {self.id}: {str(e)}"
            )
            return LocalStatusEnum.local

    school = relationship(
        "School",
        foreign_keys=[school_id],
        primaryjoin="Teacher.school_id == School.id",
        backref=db.backref("teachers", lazy="dynamic"),
    )

    __table_args__ = (
        db.CheckConstraint(
            "connector_end_date >= connector_start_date", name="check_date_range"
        ),
        db.Index("idx_teacher_school_active", "school_id", "active"),
        db.Index("idx_teacher_status_school", "status", "salesforce_school_id"),
    )

    @validates("connector_role")
    def validate_connector_role(self, key, value):
        """
        Ensure connector role is properly capitalized.

        Args:
            key: Field name being validated
            value: Role value to validate

        Returns:
            str: Capitalized role value
        """
        if value:
            return value.capitalize()
        return value

    @validates("salesforce_contact_id")
    def validate_salesforce_id(self, key, value):
        """
        Validate Salesforce ID format.

        Args:
            key: Field name being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID

        Raises:
            ValueError: If Salesforce ID format is invalid
        """
        if value and (len(value) != 18 or not value.isalnum()):
            raise ValueError("Salesforce ID must be 18 alphanumeric characters")
        return value

    @validates("status")
    def validate_status(self, key, value):
        """
        Ensure proper handling of status changes.

        Args:
            key: Field name being validated
            value: Status value to validate

        Returns:
            TeacherStatus: Validated status value

        Raises:
            ValueError: If status is not a valid TeacherStatus
        """
        if value not in TeacherStatus:
            raise ValueError(f"Invalid status. Must be one of: {list(TeacherStatus)}")
        if hasattr(self, "status") and self.status != value:
            self.status_change_date = datetime.now(timezone.utc)
        return value

    def __repr__(self):
        """
        String representation of the Teacher model.

        Returns:
            str: Debug representation showing teacher's full name
        """
        return f"<Teacher {self.first_name} {self.last_name}>"

    def update_from_csv(self, data):
        """
        Update teacher from CSV data.

        Processes CSV data to update teacher information including
        basic contact info, school assignment, connector program data,
        and communication tracking.

        Args:
            data: Dictionary containing CSV data fields
        """
        # Basic info
        self.first_name = data.get("FirstName", "").strip()
        self.last_name = data.get("LastName", "").strip()
        self.middle_name = ""  # Explicitly set to empty string
        self.school_id = data.get("npsp__Primary_Affiliation__c", "")
        self.gender = data.get("Gender__c", None)
        if "Department" in data:
            self.department = data["Department"]

        # Connector fields
        if "Connector_Role__c" in data:
            self.connector_role = data["Connector_Role__c"]
        if "Connector_Active__c" in data:
            self.connector_active = data["Connector_Active__c"]
        if "Connector_Start_Date__c" in data:
            self.connector_start_date = data["Connector_Start_Date__c"]
        if "Connector_End_Date__c" in data:
            self.connector_end_date = data["Connector_End_Date__c"]

        # Phone
        phone_number = data.get("Phone")
        if phone_number:
            existing_phone = Phone.query.filter_by(
                contact_id=self.id, number=phone_number, primary=True
            ).first()

            if not existing_phone:
                phone = Phone()
                phone.contact_id = self.id
                phone.number = phone_number
                phone.type = ContactTypeEnum.personal
                phone.primary = True
                db.session.add(phone)

        # Email
        email_address = data.get("Email")
        if email_address:
            # Check if email already exists
            existing_email = Email.query.filter_by(
                contact_id=self.id, email=email_address, primary=True
            ).first()

            if not existing_email:
                email = Email()
                email.contact_id = self.id
                email.email = email_address
                email.type = ContactTypeEnum.personal
                email.primary = True
                db.session.add(email)

        # Email tracking
        if data.get("Last_Email_Message__c"):
            self.last_email_message = data.get("Last_Email_Message__c")
        if data.get("Last_Mailchimp_Email_Date__c"):
            self.last_mailchimp_date = data.get("Last_Mailchimp_Email_Date__c")

    @property
    def upcoming_events(self):
        """
        Get teacher's upcoming events.

        Returns:
            list: List of upcoming events for this teacher
        """
        now = datetime.now(timezone.utc)
        return [
            reg.event
            for reg in self.event_registrations.all()
            if reg.event.start_date > now
        ]

    @property
    def past_events(self):
        """Get teacher's past events."""
        return [
            reg.event
            for reg in self.event_registrations.all()
            if reg.event and reg.event.start_date < datetime.now()
        ]

    @classmethod
    def import_from_salesforce(cls, sf_data, db_session):
        """
        Import teacher data from Salesforce.

        Args:
            sf_data: Dictionary containing Salesforce teacher data
            db_session: SQLAlchemy database session

        Returns:
            tuple: (teacher_object, is_new_teacher, error_message)
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
                    f"Missing required fields for teacher: {first_name} {last_name}",
                )

            # Check if teacher already exists
            teacher = cls.query.filter_by(salesforce_individual_id=sf_id).first()
            is_new = False

            if not teacher:
                teacher = cls()
                teacher.salesforce_individual_id = sf_id
                db_session.add(teacher)
                is_new = True

            # Update teacher fields
            teacher.salesforce_account_id = sf_data.get("AccountId")
            teacher.first_name = first_name
            teacher.last_name = last_name
            teacher.school_id = sf_data.get("npsp__Primary_Affiliation__c")
            teacher.salesforce_school_id = sf_data.get(
                "npsp__Primary_Affiliation__c"
            )  # Keep both for compatibility
            teacher.department = sf_data.get("Department")

            # Set default status for new teachers
            if is_new and not teacher.status:
                teacher.status = TeacherStatus.ACTIVE

            # Handle gender
            gender_value = sf_data.get("Gender__c")
            if gender_value:
                gender_key = gender_value.lower().replace(" ", "_")
                try:
                    teacher.gender = GenderEnum[gender_key]
                except KeyError:
                    # Log invalid gender but don't fail the import
                    print(
                        f"Invalid gender value for {first_name} {last_name}: {gender_value}"
                    )

            # Handle date fields
            if sf_data.get("Last_Email_Message__c"):
                from routes.utils import parse_date

                teacher.last_email_message = parse_date(
                    sf_data["Last_Email_Message__c"]
                )

            if sf_data.get("Last_Mailchimp_Email_Date__c"):
                from routes.utils import parse_date

                teacher.last_mailchimp_date = parse_date(
                    sf_data["Last_Mailchimp_Email_Date__c"]
                )

            return teacher, is_new, None

        except Exception as e:
            return (
                None,
                False,
                f"Error processing teacher {sf_data.get('FirstName', '')} {sf_data.get('LastName', '')}: {str(e)}",
            )

    def update_contact_info(self, sf_data, db_session):
        """
        Update teacher's contact information from Salesforce data.

        Args:
            sf_data: Dictionary containing Salesforce teacher data
            db_session: SQLAlchemy database session

        Returns:
            tuple: (success, error_message)
        """
        try:
            # Handle email
            email_address = sf_data.get("Email")
            if email_address and isinstance(email_address, str):
                email_address = email_address.strip()
                if email_address:
                    existing_email = Email.query.filter_by(
                        contact_id=self.id, email=email_address, primary=True
                    ).first()

                    if not existing_email:
                        email = Email()
                        email.contact_id = self.id
                        email.email = email_address
                        email.type = ContactTypeEnum.professional
                        email.primary = True
                        db_session.add(email)

            # Handle phone
            phone_number = sf_data.get("Phone")
            if phone_number and isinstance(phone_number, str):
                phone_number = phone_number.strip()
                if phone_number:
                    existing_phone = Phone.query.filter_by(
                        contact_id=self.id, number=phone_number, primary=True
                    ).first()

                    if not existing_phone:
                        phone = Phone()
                        phone.contact_id = self.id
                        phone.number = phone_number
                        phone.type = ContactTypeEnum.professional
                        phone.primary = True
                        db_session.add(phone)

            return True, None

        except Exception as e:
            return (
                False,
                f"Error updating contact info for {self.first_name} {self.last_name}: {str(e)}",
            )
