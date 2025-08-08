"""
Contact Models Module
====================

This module defines the base Contact model and related classes for managing
contact information in the VMS system. It provides a foundation for all
contact types including volunteers, teachers, students, and other participants.

Key Features:
- Polymorphic inheritance for different contact types
- Comprehensive contact information management
- Multiple phone numbers, emails, and addresses per contact
- Demographic data collection and tracking
- Salesforce integration for data synchronization
- Communication preference management
- Activity tracking and audit trails

Database Tables:
- contact: Base contact information and demographics
- phone: Phone numbers associated with contacts
- email: Email addresses associated with contacts
- address: Physical addresses associated with contacts

Contact Types:
- personal: Personal contact information
- professional: Professional/business contact information

Demographic Data:
- Age groups and birthdate tracking
- Gender and race/ethnicity information
- Education level tracking
- Local status calculation

Communication Management:
- Primary contact method designation
- Communication preference tracking
- Email bounce tracking
- Do-not-contact flags

Salesforce Integration:
- Individual and account ID mapping
- Direct URL generation for Salesforce records
- Bi-directional data synchronization

Inheritance Structure:
- Contact: Base class with common fields
- Volunteer: Inherits from Contact with volunteer-specific data
- Teacher: Inherits from Contact with teacher-specific data
- Student: Inherits from Contact with student-specific data

Usage Examples:
    # Create a new contact
    contact = Contact(
        first_name="John",
        last_name="Doe",
        salutation=SalutationEnum.mr,
        gender=GenderEnum.male
    )

    # Add phone number
    phone = Phone(
        contact_id=contact.id,
        number="555-123-4567",
        type=ContactTypeEnum.personal,
        primary=True
    )

    # Get primary contact methods
    primary_email = contact.primary_email
    primary_phone = contact.primary_phone
"""

from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models import db


# Base Enum Class
class FormEnum(str, PyEnum):
    """
    Base enumeration class that provides helper methods for form handling.

    Inherits from both str and PyEnum to allow string comparison and enum functionality.
    This base class provides common methods for form integration and data validation.

    Key Features:
        - String comparison support for database queries
        - Form choice generation for web interfaces
        - Required field handling for validation
        - Consistent enum behavior across the application
    """

    @classmethod
    def choices(cls):
        """
        Returns list of tuples (name, value) for use in form select fields.

        Returns:
            List of tuples containing (enum_name, enum_value) pairs

        Example:
            [('mr', 'Mr.'), ('ms', 'Ms.'), ('dr', 'Dr.')]
        """
        return [(member.name, member.value) for member in cls]

    @classmethod
    def choices_required(cls):
        """
        Similar to choices() but used when field is required.

        Returns:
            List of tuples containing (enum_name, enum_value) pairs

        Note: Currently returns same format as choices(), but can be extended
        for required field specific behavior.
        """
        return [(member.name, member.value) for member in cls]


# Common Enums used across the application for standardization
class SalutationEnum(FormEnum):
    """
    Standard honorific titles/salutations for contacts.

    Provides a comprehensive list of professional and personal titles
    used for formal address and communication.

    Values include common titles like Mr., Ms., Dr. as well as
    professional titles like Captain, Judge, and military ranks.
    """

    none = ""
    mr = "Mr."
    ms = "Ms."
    mrs = "Mrs."
    dr = "Dr."
    prof = "Prof."
    mx = "Mx."
    rev = "Rev."
    hon = "Hon."
    captain = "Captain"
    commissioner = "Commissioner"
    general = "General"
    judge = "Judge"
    officer = "Officer"
    staff_sergeant = "Staff Sergeant"


class SuffixEnum(FormEnum):
    """
    Name suffixes for contacts.

    Includes common suffixes like Jr., Sr., II, III, IV as well as
    professional suffixes like Ph.D., M.D., and Esq.
    """

    none = ""
    jr = "Jr."
    sr = "Sr."
    ii = "II"
    iii = "III"
    iv = "IV"
    phd = "Ph.D."
    md = "M.D."
    esq = "Esq."


class GenderEnum(FormEnum):
    """
    Gender identity options for contacts.

    Provides inclusive options for gender identification including
    traditional categories, non-binary options, and respectful alternatives.
    """

    male = "Male"
    female = "Female"
    non_binary = "Non-binary"
    genderfluid = "Genderfluid"
    agender = "Agender"
    transgender = "Transgender"
    prefer_not_to_say = "Prefer not to say"
    other = "Other"
    na = "NA"  # Not Applicable - for Salesforce data


class ContactTypeEnum(FormEnum):
    """
    Types of contact information.

    Distinguishes between personal and professional contact information
    for proper communication channel management.
    """

    personal = "personal"
    professional = "professional"


class RaceEthnicityEnum(FormEnum):
    """
    Race and ethnicity categories for demographic tracking.

    Based on standard demographic categories used in educational
    and professional settings for diversity and inclusion tracking.
    """

    unknown = "Unknown"
    american_indian = "American Indian or Alaska Native"
    asian = "Asian"
    black = "Black or African American"
    hispanic = "Hispanic or Latino"
    native_hawaiian = "Native Hawaiian or Other Pacific Islander"
    white = "White"
    multi_racial = "Multi-racial"
    bi_racial = "Bi-racial"
    two_or_more = "Two or More Races"
    prefer_not_to_say = "Prefer not to say"
    other = "Other"


class AgeGroupEnum(FormEnum):
    """
    Age group categories for demographic analysis.

    Used for age-appropriate programming, reporting, and
    demographic analysis across the organization.
    """

    UNKNOWN = ""
    UNDER_18 = "Under 18"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_64 = "55-64"
    AGE_65_PLUS = "65+"


class EducationEnum(FormEnum):
    """
    Education level categories for demographic tracking.

    Used for volunteer matching, program eligibility, and
    demographic reporting across educational programs.
    """

    UNKNOWN = ""
    HIGH_SCHOOL = "High School"
    SOME_COLLEGE = "Some College"
    ASSOCIATES = "Associates Degree"
    BACHELORS_DEGREE = "Bachelor's Degree"
    MASTERS = "Masters Degree"
    DOCTORATE = "Doctorate"
    PROFESSIONAL = "Professional Degree"
    OTHER = "Other"


class LocalStatusEnum(FormEnum):
    """
    Local status categories for geographic analysis.

    Used to determine volunteer availability and program
    participation based on geographic proximity to events.
    """

    local = "local"  # Within KC metro
    partial = "partial"  # Within driving distance
    non_local = "non_local"  # Too far
    unknown = "unknown"  # No address data


class SkillSourceEnum(FormEnum):
    """
    Sources of skill information for volunteers.

    Tracks how skill information was obtained for data quality
    and volunteer matching purposes.
    """

    job = "job"
    organization = "organization"
    interest = "interest"
    previous_engagement = "previous_engagement"
    user_selected = "user_selected"
    admin_selected = "admin_selected"


# Base Contact Models
class Contact(db.Model):
    """
    Base contact model that all other contact types inherit from.

    This is a SQLAlchemy model that uses polymorphic inheritance - other contact
    types (like Volunteer, Teacher, Student) will inherit all these fields and
    relationships automatically.

    Database Table:
        contact - Stores base contact information and demographics

    Key Features:
        - Polymorphic inheritance for different contact types
        - Comprehensive contact information management
        - Multiple contact methods (phone, email, address)
        - Demographic data collection and tracking
        - Salesforce integration for data synchronization
        - Communication preference management
        - Activity tracking and audit trails

    Relationships:
        - phones: One-to-many with Phone model (one contact can have many phone numbers)
        - emails: One-to-many with Email model (one contact can have many email addresses)
        - addresses: One-to-many with Address model (one contact can have many physical addresses)

    Inheritance:
        - Uses polymorphic inheritance with 'type' column
        - Child classes set their own polymorphic_identity
        - Common fields and relationships inherited by all contact types

    Salesforce Integration:
        - salesforce_individual_id: Links to Salesforce Contact record
        - salesforce_account_id: Links to Salesforce Account record
        - salesforce_contact_url: Generates direct link to Salesforce record
        - salesforce_account_url: Generates direct link to Account record

    Data Validation:
        - First and last name are required fields
        - Email and phone validation through related models
        - Address validation and formatting
        - Demographic data completeness tracking
    """

    __tablename__ = "contact"

    # Primary key - every contact gets a unique ID number
    id = db.Column(Integer, primary_key=True)
    # This field helps SQLAlchemy know what type of contact this is (e.g., 'volunteer', 'teacher')
    type = db.Column(String(50))

    # External IDs for Salesforce integration
    # The unique=True ensures no two contacts can have the same Salesforce Individual ID
    salesforce_individual_id = db.Column(String(18), unique=True, nullable=True)
    salesforce_account_id = db.Column(String(18), nullable=True)

    # Basic contact information - notice how some fields are nullable=False (required)
    # while others are nullable=True (optional)
    salutation = db.Column(Enum(SalutationEnum), nullable=True)
    first_name = db.Column(String(50), nullable=False)  # Required field
    middle_name = db.Column(String(50), nullable=True)  # Optional field
    last_name = db.Column(String(50), nullable=False)  # Required field
    suffix = db.Column(Enum(SuffixEnum), nullable=True)

    # Demographic Information
    description = db.Column(Text)  # General notes about contact
    age_group = db.Column(Enum(AgeGroupEnum), default=AgeGroupEnum.UNKNOWN)
    education_level = db.Column(Enum(EducationEnum), default=EducationEnum.UNKNOWN)
    birthdate = db.Column(Date)
    gender = db.Column(Enum(GenderEnum))
    race_ethnicity = db.Column(Enum(RaceEthnicityEnum), nullable=True)

    # Communication Preferences and Status
    do_not_call = db.Column(Boolean, default=False)  # Indicates phone contact preference
    do_not_contact = db.Column(Boolean, default=False)  # Indicates no contact preference
    email_opt_out = db.Column(Boolean, default=False)  # Email marketing preference
    email_bounced_date = db.Column(DateTime)  # Tracks failed email deliveries
    exclude_from_reports = db.Column(Boolean, default=False)  # Excludes from all reports and statistics

    # Activity Tracking
    last_email_date = db.Column(Date)  # Date of last email communication
    notes = db.Column(Text)  # General contact notes

    # SQLAlchemy inheritance configuration
    __mapper_args__ = {
        "polymorphic_identity": "contact",  # Base identity for inheritance
        "polymorphic_on": type,  # Column used to determine contact type
        "confirm_deleted_rows": False,  # Prevents deletion confirmation checks
    }

    # These relationship definitions tell SQLAlchemy how contacts are connected to their
    # phone numbers, emails, and addresses. The 'cascade' parameter ensures that when
    # a contact is deleted, all their related information is also deleted.
    phones = relationship(
        "Phone",
        backref="contact",  # This creates a .contact property on Phone objects
        lazy="dynamic",  # Lazy loading - only fetches data when accessed
        cascade="all, delete-orphan",
    )  # Automatically deletes related phones when contact is deleted

    emails = relationship("Email", backref="contact", lazy="dynamic", cascade="all, delete-orphan")

    addresses = relationship("Address", backref="contact", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def salesforce_contact_url(self):
        """
        Generates URL to view contact in Salesforce if ID exists.

        Returns:
            str: URL to Salesforce Contact record, or None if no salesforce_individual_id exists

        Usage:
            sf_url = contact.salesforce_contact_url
            if sf_url:
                # Open Salesforce contact record in browser
        """
        if self.salesforce_individual_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Contact/{self.salesforce_individual_id}/view"
        return None

    @property
    def salesforce_account_url(self):
        if self.salesforce_account_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_account_id}/view"
        return None

    @property
    def primary_email(self):
        """Returns the primary email address string for this contact, or None if not found."""
        primary = self.emails.filter_by(primary=True).first()
        return primary.email if primary else None

    @property
    def primary_email_object(self):
        """Returns the primary Email model object for this contact, or None if not found.
        Useful when you need access to email metadata beyond just the address.
        """
        return self.emails.filter_by(primary=True).first()

    @property
    def primary_phone(self):
        """Returns the primary phone number for this contact, or None if not found."""
        primary = self.phones.filter_by(primary=True).first()
        return primary.number if primary else None

    @property
    def primary_phone_object(self):
        """Returns the primary phone object for this contact, or None if not found."""
        return self.phones.filter_by(primary=True).first()

    def validate_email_primary_status(self):
        """Ensures only one email is marked as primary"""
        primary_count = self.emails.filter_by(primary=True).count()
        if primary_count > 1:
            raise ValueError("Contact cannot have multiple primary emails")

    def validate_phone_primary_status(self):
        """Ensures only one phone is marked as primary"""
        primary_count = self.phones.filter_by(primary=True).count()
        if primary_count > 1:
            raise ValueError("Contact cannot have multiple primary phones")

    @property
    def full_name(self):
        """Returns formatted full name with optional middle name"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def formal_name(self):
        """Returns formal name with salutation and suffix if present"""
        name_parts = []
        if self.salutation and self.salutation != SalutationEnum.none:
            name_parts.append(self.salutation.value)
        name_parts.append(self.full_name)
        if self.suffix and self.suffix != SuffixEnum.none:
            name_parts.append(self.suffix.value)
        return " ".join(name_parts)

    @property
    def age(self):
        """Calculate age based on birthdate"""
        if not self.birthdate:
            return None
        today = date.today()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))

    @property
    def has_valid_email(self):
        """Check if contact has at least one valid email"""
        return self.emails.count() > 0 and not self.email_opt_out and not self.email_bounced_date

    @property
    def has_valid_phone(self):
        """Check if contact has at least one valid phone"""
        return self.phones.count() > 0 and not self.do_not_call

    @property
    def is_contactable(self):
        """Check if contact can be contacted through any means"""
        return not self.do_not_contact and (self.has_valid_email or self.has_valid_phone)

    @property
    def primary_address(self):
        """Returns the primary address object for this contact"""
        return self.addresses.filter_by(primary=True).first()

    @property
    def formatted_primary_address(self):
        """Returns formatted string of primary address"""
        addr = self.primary_address
        if not addr:
            return None

        parts = [addr.address_line1]
        if addr.address_line2:
            parts.append(addr.address_line2)
        parts.append(f"{addr.city}, {addr.state} {addr.zip_code}")
        if addr.country and addr.country.upper() != "USA":
            parts.append(addr.country)
        return "\n".join(parts)


# Base Contact Info Models
class Phone(db.Model):
    """Stores phone numbers associated with contacts.
    Each Phone record belongs to exactly one Contact (many-to-one relationship).
    A contact can have multiple phone numbers, but only one can be marked as primary.
    """

    __tablename__ = "phone"

    id = db.Column(Integer, primary_key=True)
    # This foreign key connects each phone number to its contact
    # The nullable=False means every phone number must belong to a contact
    contact_id = db.Column(Integer, ForeignKey("contact.id"), nullable=False)
    number = db.Column(String(20))
    type = db.Column(Enum(ContactTypeEnum))  # Uses the enum defined above
    primary = db.Column(Boolean, default=False)  # Only one phone per contact should be primary


class Email(db.Model):
    """Stores email addresses associated with contacts.
    Supports multiple emails per contact with primary flag.
    """

    __tablename__ = "email"

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey("contact.id"), nullable=False)
    email = db.Column(String(100))
    type = db.Column(Enum(ContactTypeEnum))  # personal or professional
    primary = db.Column(Boolean, default=False)  # indicates preferred email

    def to_dict(self):
        """Converts email object to dictionary for API responses"""
        return {"id": self.id, "email": self.email, "type": self.type.name if self.type else "personal", "primary": self.primary}


class Address(db.Model):
    """Stores physical addresses associated with contacts.
    Supports multiple addresses per contact with primary flag.
    """

    __tablename__ = "address"

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey("contact.id"), nullable=False)
    address_line1 = db.Column(String(100))
    address_line2 = db.Column(String(100))
    city = db.Column(String(50))
    state = db.Column(String(50))
    zip_code = db.Column(String(20))
    country = db.Column(String(50))
    type = db.Column(Enum(ContactTypeEnum))  # personal or professional
    primary = db.Column(Boolean, default=False)  # indicates preferred address
