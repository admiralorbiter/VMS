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

import logging
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.event import listens_for
from sqlalchemy.orm import declared_attr, relationship, validates

from config.model_constants import KC_METRO_ZIP_PREFIXES, KC_REGION_ZIP_PREFIXES
from models import db

logger = logging.getLogger(__name__)


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
    do_not_call = db.Column(
        Boolean, default=False
    )  # Indicates phone contact preference
    do_not_contact = db.Column(
        Boolean, default=False
    )  # Indicates no contact preference
    email_opt_out = db.Column(Boolean, default=False)  # Email marketing preference
    email_bounced_date = db.Column(DateTime)  # Tracks failed email deliveries
    exclude_from_reports = db.Column(
        Boolean, default=False
    )  # Excludes from all reports and statistics

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

    emails = relationship(
        "Email", backref="contact", lazy="dynamic", cascade="all, delete-orphan"
    )

    addresses = relationship(
        "Address", backref="contact", lazy="dynamic", cascade="all, delete-orphan"
    )

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
        """
        Generates URL to view account in Salesforce if ID exists.

        Returns:
            str: URL to Salesforce Account record, or None if no salesforce_account_id exists

        Usage:
            sf_url = contact.salesforce_account_url
            if sf_url:
                # Open Salesforce account record in browser
        """
        if self.salesforce_account_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_account_id}/view"
        return None

    @property
    def primary_email(self):
        """
        Returns the primary email address string for this contact.

        Returns:
            str or None: The primary email address if one exists, None otherwise

        Note:
            This returns only the email string. Use primary_email_object if you
            need access to the full Email model instance with metadata.
        """
        primary = self.emails.filter_by(primary=True).first()
        return primary.email if primary else None

    @property
    def primary_email_object(self):
        """
        Returns the primary Email model object for this contact.

        Returns:
            Email or None: The primary Email model instance if one exists, None otherwise

        Note:
            This returns the full Email object with all metadata (type, id, etc.).
            Use primary_email if you only need the email address string.
        """
        return self.emails.filter_by(primary=True).first()

    @property
    def primary_phone(self):
        """
        Returns the primary phone number string for this contact.

        Returns:
            str or None: The primary phone number if one exists, None otherwise

        Note:
            This returns only the phone number string. Use primary_phone_object if you
            need access to the full Phone model instance with metadata.
        """
        primary = self.phones.filter_by(primary=True).first()
        return primary.number if primary else None

    @property
    def primary_phone_object(self):
        """
        Returns the primary Phone model object for this contact.

        Returns:
            Phone or None: The primary Phone model instance if one exists, None otherwise

        Note:
            This returns the full Phone object with all metadata (type, id, etc.).
            Use primary_phone if you only need the phone number string.
        """
        return self.phones.filter_by(primary=True).first()

    def validate_email_primary_status(self):
        """
        Ensures only one email is marked as primary for this contact.

        Raises:
            ValueError: If more than one email is marked as primary

        Note:
            This method should be called manually or via event listeners.
            It does not automatically run during database operations.
        """
        primary_count = self.emails.filter_by(primary=True).count()
        if primary_count > 1:
            raise ValueError("Contact cannot have multiple primary emails")

    def validate_phone_primary_status(self):
        """
        Ensures only one phone is marked as primary for this contact.

        Raises:
            ValueError: If more than one phone is marked as primary

        Note:
            This method should be called manually or via event listeners.
            It does not automatically run during database operations.
        """
        primary_count = self.phones.filter_by(primary=True).count()
        if primary_count > 1:
            raise ValueError("Contact cannot have multiple primary phones")

    @property
    def full_name(self):
        """
        Returns formatted full name with optional middle name.

        Returns:
            str: Full name in format "First Middle Last" or "First Last"

        Example:
            >>> contact.first_name = "John"
            >>> contact.middle_name = "Michael"
            >>> contact.last_name = "Doe"
            >>> contact.full_name
            'John Michael Doe'
        """
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def formal_name(self):
        """
        Returns formal name with salutation and suffix if present.

        Returns:
            str: Formal name in format "Salutation Full Name Suffix"

        Example:
            >>> contact.salutation = SalutationEnum.dr
            >>> contact.full_name = "John Doe"
            >>> contact.suffix = SuffixEnum.phd
            >>> contact.formal_name
            'Dr. John Doe Ph.D.'
        """
        name_parts = []
        if self.salutation and self.salutation != SalutationEnum.none:
            name_parts.append(self.salutation.value)
        name_parts.append(self.full_name)
        if self.suffix and self.suffix != SuffixEnum.none:
            name_parts.append(self.suffix.value)
        return " ".join(name_parts)

    @property
    def age(self):
        """
        Calculate age based on birthdate.

        Returns:
            int or None: Age in years if birthdate exists, None otherwise

        Note:
            Age is calculated as of today's date. The calculation accounts for
            whether the birthday has occurred this year.
        """
        if not self.birthdate:
            return None
        today = date.today()
        return (
            today.year
            - self.birthdate.year
            - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
        )

    @property
    def has_valid_email(self):
        """
        Check if contact has at least one valid email address.

        Returns:
            bool: True if contact has at least one email, has not opted out,
                  and email has not bounced, False otherwise
        """
        return (
            self.emails.count() > 0
            and not self.email_opt_out
            and not self.email_bounced_date
        )

    @property
    def has_valid_phone(self):
        """
        Check if contact has at least one valid phone number.

        Returns:
            bool: True if contact has at least one phone number and has not
                  set do_not_call flag, False otherwise
        """
        return self.phones.count() > 0 and not self.do_not_call

    @property
    def is_contactable(self):
        """
        Check if contact can be contacted through any available means.

        Returns:
            bool: True if contact has not set do_not_contact flag and has at
                  least one valid email or phone number, False otherwise
        """
        return not self.do_not_contact and (
            self.has_valid_email or self.has_valid_phone
        )

    @property
    def primary_address(self):
        """
        Returns the primary Address model object for this contact.

        Returns:
            Address or None: The primary Address model instance if one exists,
                             None otherwise
        """
        return self.addresses.filter_by(primary=True).first()

    @property
    def formatted_primary_address(self):
        """
        Returns formatted string representation of primary address.

        Returns:
            str or None: Multi-line formatted address string if primary address
                         exists, None otherwise

        Format:
            Address Line 1
            Address Line 2 (if present)
            City, State ZIP
            Country (if not USA)
        """
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

    def calculate_local_status(self):
        """
        Base local status calculation using multiple data sources.

        This method determines if a contact is local, partially local, or non-local
        based on multiple indicators. Child classes can override specific parts.

        Returns:
            LocalStatusEnum: The calculated status based on available data

        Logic Priority:
        1. Check for in-person event participation (strongest indicator)
        2. Use address zip code analysis if available
        3. Check virtual event presenter location hints
        4. Use contact type specific assumptions
        5. Return unknown if no indicators available
        """
        try:
            # First, check if contact has participated in any in-person events
            local_from_events = self._check_local_status_from_events()
            if local_from_events is not None:
                return local_from_events

            # Second, use traditional zip code analysis
            local_from_address = self._check_local_status_from_address()
            if local_from_address is not None:
                return local_from_address

            # Third, check virtual event presenter location hints
            local_from_virtual_hints = self._check_local_status_from_virtual_hints()
            if local_from_virtual_hints is not None:
                return local_from_virtual_hints

            # Fourth, use contact type specific assumptions
            local_from_assumptions = self._get_local_status_assumption()
            if local_from_assumptions is not None:
                return local_from_assumptions

            # If we have a previously calculated local status that's not unknown, keep it
            # Note: local_status attribute only exists on Volunteer model, not base Contact
            # Use getattr to safely access without hasattr check
            local_status = getattr(self, "local_status", None)
            if local_status is not None and local_status != LocalStatusEnum.unknown:
                return local_status

            return LocalStatusEnum.unknown

        except Exception as e:
            logger.error(
                "Error calculating local status for contact %d: %s", self.id, str(e)
            )
            return LocalStatusEnum.unknown

    def _check_local_status_from_events(self):
        """
        Check local status based on event participation.

        If a contact has participated in any in-person events (non-virtual),
        they are very likely local since they physically attended.

        Returns:
            LocalStatusEnum or None: Local status if determinable from events
        """
        try:
            # This is a base implementation - child classes can override
            # to provide more specific event checking logic
            return None

        except Exception as e:
            logger.warning(
                "Error checking local status from events for contact %d: %s",
                self.id,
                str(e),
            )
            return None

    def _check_local_status_from_address(self):
        """
        Traditional zip code-based local status calculation.

        Returns:
            LocalStatusEnum or None: Local status if determinable from address
        """
        try:
            # Use constants from model_constants for zip code prefixes
            def check_address_status(address):
                """Helper function to check status based on zip code prefix"""
                if not address or not address.zip_code:
                    return None

                zip_prefix = address.zip_code[:3]
                if zip_prefix in KC_METRO_ZIP_PREFIXES:
                    return LocalStatusEnum.local
                if zip_prefix in KC_REGION_ZIP_PREFIXES:
                    return LocalStatusEnum.partial
                return LocalStatusEnum.non_local

            # First check if there's a primary address
            primary_addr = next((addr for addr in self.addresses if addr.primary), None)
            if primary_addr:
                # If primary exists but has no zip, return partial
                if not primary_addr.zip_code:
                    return LocalStatusEnum.partial
                # If primary has zip, use it
                return check_address_status(primary_addr)

            # If no primary address, try personal address
            personal_addr = next(
                (
                    addr
                    for addr in self.addresses
                    if addr.type == ContactTypeEnum.personal
                ),
                None,
            )
            if personal_addr and personal_addr.zip_code:
                return check_address_status(personal_addr)

            return None

        except Exception as e:
            logger.warning(
                "Error checking local status from address for contact %d: %s",
                self.id,
                str(e),
            )
            return None

    def _check_local_status_from_virtual_hints(self):
        """
        Check local status from virtual event presenter location hints.

        This uses the logic from the virtual import process where presenter
        location is tagged as "local" or "non-local".

        Note:
            This method checks for a temporary `_is_local_hint` attribute that
            is set during virtual event imports. This is a transient attribute
            that exists only during the import process and is not persisted
            to the database. For a more permanent solution, consider storing
            this information in the database.

        Returns:
            LocalStatusEnum or None: Local status if determinable from virtual hints
        """
        try:
            # Check if this contact has the _is_local_hint attribute
            # This is set during virtual event imports as a temporary attribute
            # Warning: This is fragile and depends on the import process setting this attribute
            local_hint = getattr(self, "_is_local_hint", None)
            if local_hint is not None:
                if local_hint:
                    return LocalStatusEnum.local
                else:
                    return LocalStatusEnum.non_local

            return None

        except Exception as e:
            logger.warning(
                "Error checking local status from virtual hints for contact %d: %s",
                self.id,
                str(e),
            )
            return None

    def _get_local_status_assumption(self):
        """
        Get local status assumption based on contact type.

        This method should be overridden by child classes to provide
        type-specific assumptions (e.g., teachers assumed local).

        Returns:
            LocalStatusEnum or None: Local status assumption if applicable
        """
        # Base implementation returns None - child classes override this
        return None

    def __repr__(self):
        """String representation for debugging."""
        return f"<Contact(id={self.id}, type={self.type}, name='{self.full_name}')>"

    def __str__(self):
        """Human-readable string representation."""
        return self.full_name


# Base Contact Info Models
class Phone(db.Model):
    """
    Phone number model for storing contact phone numbers.

    Each Phone record belongs to exactly one Contact (many-to-one relationship).
    A contact can have multiple phone numbers, but only one should be marked as primary.

    Database Table:
        phone - Stores phone numbers associated with contacts

    Relationships:
        - contact: Many-to-one relationship with Contact model (via backref)
                  Each phone number belongs to exactly one contact

    Key Features:
        - Multiple phone numbers per contact supported
        - Primary phone designation for preferred contact method
        - Contact type classification (personal/professional)
        - Automatic validation of primary status uniqueness

    Usage Examples:
        # Create a new phone number
        phone = Phone(
            contact_id=contact.id,
            number="555-123-4567",
            type=ContactTypeEnum.personal,
            primary=True
        )

        # Access contact from phone
        contact = phone.contact
    """

    __tablename__ = "phone"

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(
        Integer,
        ForeignKey("contact.id"),
        nullable=False,
        index=True,
    )  # Indexed for performance on lookups
    number = db.Column(String(20), nullable=False)  # Phone number is required
    type = db.Column(
        Enum(ContactTypeEnum), nullable=True
    )  # personal or professional, optional
    primary = db.Column(
        Boolean, default=False, index=True
    )  # Indexed for primary phone lookups

    __table_args__ = (
        Index("idx_phone_contact_primary", "contact_id", "primary"),
    )  # Composite index for primary phone queries

    def __repr__(self):
        """String representation for debugging."""
        return f"<Phone(id={self.id}, contact_id={self.contact_id}, number='{self.number}', primary={self.primary})>"

    def __str__(self):
        """Human-readable string representation."""
        type_str = f" ({self.type.value})" if self.type else ""
        primary_str = " [Primary]" if self.primary else ""
        return f"{self.number}{type_str}{primary_str}"

    def to_dict(self):
        """
        Converts phone object to dictionary for API responses.

        Returns:
            dict: Dictionary containing phone id, number, type, and primary status
        """
        return {
            "id": self.id,
            "number": self.number,
            "type": self.type.name if self.type else None,
            "primary": self.primary,
        }


class Email(db.Model):
    """
    Email address model for storing contact email addresses.

    Supports multiple emails per contact with primary flag designation.
    Each Email record belongs to exactly one Contact (many-to-one relationship).

    Database Table:
        email - Stores email addresses associated with contacts

    Relationships:
        - contact: Many-to-one relationship with Contact model (via backref)
                  Each email belongs to exactly one contact

    Key Features:
        - Multiple email addresses per contact supported
        - Primary email designation for preferred contact method
        - Contact type classification (personal/professional)
        - Automatic validation of primary status uniqueness

    Usage Examples:
        # Create a new email address
        email = Email(
            contact_id=contact.id,
            email="john.doe@example.com",
            type=ContactTypeEnum.personal,
            primary=True
        )

        # Access contact from email
        contact = email.contact
    """

    __tablename__ = "email"

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(
        Integer,
        ForeignKey("contact.id"),
        nullable=False,
        index=True,
    )  # Indexed for performance on lookups
    email = db.Column(String(100), nullable=False)  # Email address is required
    type = db.Column(
        Enum(ContactTypeEnum), nullable=True
    )  # personal or professional, optional
    primary = db.Column(
        Boolean, default=False, index=True
    )  # Indexed for primary email lookups

    __table_args__ = (
        Index("idx_email_contact_primary", "contact_id", "primary"),
    )  # Composite index for primary email queries

    def __repr__(self):
        """String representation for debugging."""
        return f"<Email(id={self.id}, contact_id={self.contact_id}, email='{self.email}', primary={self.primary})>"

    def __str__(self):
        """Human-readable string representation."""
        type_str = f" ({self.type.value})" if self.type else ""
        primary_str = " [Primary]" if self.primary else ""
        return f"{self.email}{type_str}{primary_str}"

    def to_dict(self):
        """
        Converts email object to dictionary for API responses.

        Returns:
            dict: Dictionary containing email id, address, type, and primary status
        """
        return {
            "id": self.id,
            "email": self.email,
            "type": self.type.name if self.type else "personal",
            "primary": self.primary,
        }


class Address(db.Model):
    """
    Physical address model for storing contact addresses.

    Supports multiple addresses per contact with primary flag designation.
    Each Address record belongs to exactly one Contact (many-to-one relationship).

    Database Table:
        address - Stores physical addresses associated with contacts

    Relationships:
        - contact: Many-to-one relationship with Contact model (via backref)
                  Each address belongs to exactly one contact

    Key Features:
        - Multiple addresses per contact supported
        - Primary address designation for preferred location
        - Contact type classification (personal/professional)
        - Full address components (street, city, state, zip, country)
        - Used for local status calculation based on zip code

    Usage Examples:
        # Create a new address
        address = Address(
            contact_id=contact.id,
            address_line1="123 Main St",
            address_line2="Apt 4B",
            city="Kansas City",
            state="MO",
            zip_code="64111",
            country="USA",
            type=ContactTypeEnum.personal,
            primary=True
        )

        # Access contact from address
        contact = address.contact
    """

    __tablename__ = "address"

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(
        Integer,
        ForeignKey("contact.id"),
        nullable=False,
        index=True,
    )  # Indexed for performance on lookups
    address_line1 = db.Column(String(100), nullable=True)  # Street address line 1
    address_line2 = db.Column(
        String(100), nullable=True
    )  # Street address line 2 (apt, suite, etc.)
    city = db.Column(String(50), nullable=True)  # City name
    state = db.Column(String(50), nullable=True)  # State or province
    zip_code = db.Column(
        String(20), nullable=True, index=True
    )  # ZIP/postal code, indexed for local status lookups
    country = db.Column(String(50), nullable=True)  # Country name
    type = db.Column(
        Enum(ContactTypeEnum), nullable=True
    )  # personal or professional, optional
    primary = db.Column(
        Boolean, default=False, index=True
    )  # Indexed for primary address lookups

    __table_args__ = (
        Index("idx_address_contact_primary", "contact_id", "primary"),
    )  # Composite index for primary address queries

    def __repr__(self):
        """String representation for debugging."""
        city_state = f"{self.city}, {self.state}" if self.city and self.state else "N/A"
        return f"<Address(id={self.id}, contact_id={self.contact_id}, city_state='{city_state}', primary={self.primary})>"

    def __str__(self):
        """Human-readable string representation."""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        if self.zip_code:
            parts.append(self.zip_code)
        address_str = " ".join(parts) if parts else "No address"
        primary_str = " [Primary]" if self.primary else ""
        return f"{address_str}{primary_str}"

    def to_dict(self):
        """
        Converts address object to dictionary for API responses.

        Returns:
            dict: Dictionary containing all address fields
        """
        return {
            "id": self.id,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "type": self.type.name if self.type else None,
            "primary": self.primary,
        }


# SQLAlchemy Event Listeners for Automatic Validation
# These listeners automatically validate primary status when Phone or Email records are created/updated


@listens_for(Phone, "before_insert")
@listens_for(Phone, "before_update")
def validate_phone_primary_before_change(mapper, connection, target):
    """
    Event listener to ensure only one phone is marked as primary per contact.

    Automatically called by SQLAlchemy before Phone insert/update operations.
    If multiple phones are marked as primary, unmarks all except the most recent one.
    """
    if target.primary:
        # Unmark all other primary phones for this contact
        # Use connection to query within the same transaction
        from sqlalchemy import select, update

        # Build where clause - for inserts, target.id is None, so check for it
        where_clauses = [
            Phone.contact_id == target.contact_id,
            Phone.primary == True,  # noqa: E712
        ]
        if target.id is not None:
            where_clauses.append(Phone.id != target.id)

        # Find other primary phones for this contact
        stmt = select(Phone.id).where(*where_clauses)
        other_primary_ids = connection.execute(stmt).scalars().all()

        # Unmark other primary phones
        if other_primary_ids:
            update_stmt = (
                update(Phone)
                .where(Phone.id.in_(other_primary_ids))
                .values(primary=False)
            )
            connection.execute(update_stmt)


@listens_for(Email, "before_insert")
@listens_for(Email, "before_update")
def validate_email_primary_before_change(mapper, connection, target):
    """
    Event listener to ensure only one email is marked as primary per contact.

    Automatically called by SQLAlchemy before Email insert/update operations.
    If multiple emails are marked as primary, unmarks all except the most recent one.
    """
    if target.primary:
        # Unmark all other primary emails for this contact
        # Use connection to query within the same transaction
        from sqlalchemy import select, update

        # Build where clause - for inserts, target.id is None, so check for it
        where_clauses = [
            Email.contact_id == target.contact_id,
            Email.primary == True,  # noqa: E712
        ]
        if target.id is not None:
            where_clauses.append(Email.id != target.id)

        # Find other primary emails for this contact
        stmt = select(Email.id).where(*where_clauses)
        other_primary_ids = connection.execute(stmt).scalars().all()

        # Unmark other primary emails
        if other_primary_ids:
            update_stmt = (
                update(Email)
                .where(Email.id.in_(other_primary_ids))
                .values(primary=False)
            )
            connection.execute(update_stmt)
