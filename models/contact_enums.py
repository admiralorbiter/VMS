"""
Contact Enumerations
====================

Extracted from contact.py (TD-012) for better code organization.
Contains all enum types used for contact models.

These enums are re-exported from contact.py for backward compatibility,
so existing ``from models.contact import SalutationEnum`` imports continue to work.
"""

from enum import Enum as PyEnum


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
    other_poc = "Other POC"


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
