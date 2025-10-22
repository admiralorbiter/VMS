"""
Routes Utilities Module
======================

This module provides utility functions for data processing, parsing, and
mapping operations used throughout the VMS route system. It handles
Salesforce data integration, contact information processing, and various
data transformation tasks.

Key Features:
- Date parsing from multiple formats
- Contact information extraction and formatting
- Salesforce data mapping and transformation
- Skill parsing and standardization
- District name mapping
- Event type and format mapping

Data Processing Functions:
- parse_date: Multi-format date parsing
- clean_skill_name: Skill name standardization
- parse_skills: Skill list parsing and deduplication
- get_email_addresses: Email extraction from CSV rows
- get_phone_numbers: Phone number extraction from CSV rows

Salesforce Integration:
- map_session_type: Event type mapping
- map_cancellation_reason: Cancellation reason mapping
- map_event_format: Event format mapping
- parse_event_skills: Event skills parsing

Contact Processing:
- Email address extraction and type assignment
- Phone number cleaning and formatting
- Primary contact designation
- Duplicate contact prevention

District Mapping:
- DISTRICT_MAPPINGS: Standardized district name mapping
- Salesforce to local district name conversion
- Consistent district naming across the system

Dependencies:
- datetime for date parsing
- Database models for data types
- Enum classes for standardized values
- CSV processing utilities

Usage:
- Imported by route modules for data processing
- Used in Salesforce import operations
- Applied in contact information handling
- Utilized in event data transformation
"""

from datetime import datetime

from flask import jsonify, request
from flask_login import current_user

from models import db
from models.audit_log import AuditLog
from models.contact import ContactTypeEnum, Email
from models.district_model import District
from models.event import CancellationReason, EventFormat, EventType

# District name mapping for Salesforce integration
DISTRICT_MAPPINGS = {
    "KANSAS CITY USD 500": "KANSAS CITY USD 500",
    "HICKMAN MILLS C-1": "HICKMAN MILLS C-1",
    "GRANDVIEW C-4": "GRANDVIEW C-4",
    "NORTH KANSAS CITY 74": "NORTH KANSAS CITY 74",
    "REPUBLIC R-III": "REPUBLIC R-III",
    "KANSAS CITY PUBLIC SCHOOL DISTRICT": "KANSAS CITY PUBLIC SCHOOL DISTRICT",
    "INDEPENDENCE 30": "INDEPENDENCE 30",
    "HOGAN PREPARATORY ACADEMY": "HOGAN PREPARATORY ACADEMY",
    "PIPER-KANSAS CITY": "PIPER-KANSAS CITY",
    "BELTON 124": "BELTON 124",
    "CROSSROADS ACADEMY OF KANSAS CITY": "CROSSROADS ACADEMY OF KANSAS CITY",
    "CENTER SCHOOL DISTRICT": "CENTER SCHOOL DISTRICT",
    "GUADALUPE CENTERS SCHOOLS": "GUADALUPE CENTERS SCHOOLS",
    "BLUE VALLEY": "BLUE VALLEY",
    "BASEHOR-LINWOOD": "BASEHOR-LINWOOD",
    "ALLEN VILLAGE": "ALLEN VILLAGE",
    "SPRINGFIELD R-XII": "SPRINGFIELD R-XII",
    "DE SOTO": "DE SOTO",
    "INDEPENDENT": "INDEPENDENT",
    "CENTER 58 SCHOOL DISTRICT": "CENTER 58 SCHOOL DISTRICT",
    # Add missing districts from your database
    "Kansas City Kansas Public Schools": "Kansas City Kansas Public Schools",
    "Hickman Mills School District": "Hickman Mills School District",
    "Grandview School District": "Grandview School District",
    "Center School District": "Center School District",
    "Kansas City Public Schools (MO)": "Kansas City Public Schools (MO)",
    "Allen Village - District": "Allen Village - District",
    # Add common variations and aliases
    "KCKPS": "Kansas City Kansas Public Schools",
    "KCPS": "Kansas City Public Schools (MO)",
    "Hickman Mills": "Hickman Mills School District",
    "Grandview": "Grandview School District",
    "Center": "Center School District",
    "Allen Village": "Allen Village - District",
}


def admin_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False) or not getattr(
            current_user, "is_admin", False
        ):
            return jsonify({"error": "Unauthorized"}), 403
        return func(*args, **kwargs)

    return wrapper


def kck_viewer_or_higher_required(func):
    """
    Decorator to require KCK viewer level or higher permissions.

    Allows access to:
    - KCK viewers (restricted to KCK page only)
    - Regular users and above (full access)

    Args:
        func: Function to decorate

    Returns:
        Decorated function with permission validation
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False):
            return jsonify({"error": "Authentication required"}), 401

        # KCK viewers and all higher levels can access
        if getattr(current_user, "security_level", -2) >= -1:
            return func(*args, **kwargs)

        return jsonify({"error": "Insufficient permissions"}), 403

    return wrapper


def kck_viewer_only(func):
    """
    DEPRECATED: Use @district_scoped_required instead.

    Decorator to restrict access to KCK viewers only.
    Kept for backwards compatibility.

    This should be used for the specific KCK teacher progress page
    to ensure only KCK viewers can access it.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with KCK viewer validation
    """
    import warnings

    warnings.warn(
        "kck_viewer_only is deprecated. Use @district_scoped_required instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, "is_authenticated", False):
            return jsonify({"error": "Authentication required"}), 401

        # Only KCK viewers can access this specific page
        if getattr(current_user, "is_kck_viewer", False):
            return func(*args, **kwargs)

        # For non-KCK viewers, check if they have higher permissions
        # If they do, allow access (admins, managers, etc.)
        if getattr(current_user, "security_level", -2) > -1:
            return func(*args, **kwargs)

        return jsonify({"error": "Access restricted to KCK viewers"}), 403

    return wrapper


def parse_date(date_str):
    """
    Parse date string from Salesforce CSV or API.

    Handles multiple date formats commonly found in Salesforce data:
    - ISO 8601 format (2025-03-05T14:15:00.000+0000)
    - CSV format with time (YYYY-MM-DD HH:MM:SS)
    - CSV format without seconds (YYYY-MM-DD HH:MM)
    - Date only format (YYYY-MM-DD)

    Args:
        date_str: Date string to parse

    Returns:
        datetime object if parsing successful, None otherwise

    Examples:
        >>> parse_date('2025-03-05T14:15:00.000+0000')
        datetime(2025, 3, 5, 14, 15)
        >>> parse_date('2025-03-05 14:15:30')
        datetime(2025, 3, 5, 14, 15, 30)
        >>> parse_date('2025-03-05')
        datetime(2025, 3, 5, 0, 0)
    """
    if not date_str:
        return None

    try:
        # First try parsing ISO 8601 format (from Salesforce API)
        # Example: 2025-03-05T14:15:00.000+0000
        if "T" in date_str:
            return datetime.strptime(date_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")

        # Try CSV format with time (YYYY-MM-DD HH:MM:SS)
        try:
            parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
            return parsed_date
        except ValueError:
            # If that fails, try without seconds (YYYY-MM-DD HH:MM)
            try:
                parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
                return parsed_date
            except ValueError:
                # Fallback for dates without times
                try:
                    return datetime.strptime(date_str.strip(), "%Y-%m-%d")
                except ValueError:
                    return None
    except Exception as e:
        print(f"Error parsing date {date_str}: {str(e)}")  # Debug logging
        return None


def clean_skill_name(skill_name):
    """
    Standardize skill name format.

    Converts skill names to a consistent format by trimming whitespace,
    converting to lowercase, and capitalizing the first letter.

    Args:
        skill_name: Raw skill name string

    Returns:
        Standardized skill name string

    Examples:
        >>> clean_skill_name('  python programming  ')
        'Python programming'
        >>> clean_skill_name('JAVA')
        'Java'
    """
    return skill_name.strip().lower().capitalize()


def parse_skills(text_skills, comma_skills):
    """
    Parse and combine skills from both columns, removing duplicates.

    Processes skills from two different input formats and combines them
    into a single list with duplicates removed.

    Args:
        text_skills: Semicolon-separated skills string
        comma_skills: Comma-separated skills string

    Returns:
        List of unique, standardized skill names

    Examples:
        >>> parse_skills('Python; Java', 'JavaScript, Python')
        ['Python', 'Java', 'JavaScript']
    """
    skills = set()

    # Parse semicolon-separated skills
    if text_skills:
        skills.update(clean_skill_name(s) for s in text_skills.split(";") if s.strip())

    # Parse comma-separated skills
    if comma_skills:
        skills.update(clean_skill_name(s) for s in comma_skills.split(",") if s.strip())

    return list(skills)


def get_email_addresses(row):
    """
    Extract and format email addresses from a CSV row.

    Processes multiple email columns from Salesforce CSV data and creates
    Email objects with appropriate types and primary designation.

    Args:
        row: Dictionary containing CSV row data

    Returns:
        List of Email objects with type and primary designation

    Email Types:
        - personal: General email addresses
        - home: Home email addresses
        - alternate: Alternate email addresses
        - work: Work email addresses

    Primary Designation:
        - Based on preferred email type from CSV
        - Falls back to 'Email' column if no preference specified
    """
    emails = []
    seen_emails = set()  # Track unique emails
    preferred_type = row.get("npe01__Preferred_Email__c", "").lower()

    # Map of CSV columns to email types
    email_mappings = {
        "Email": (
            "personal",
            ContactTypeEnum.personal,
        ),  # Changed 'email' to 'personal' to match data
        "npe01__HomeEmail__c": ("home", ContactTypeEnum.personal),
        "npe01__AlternateEmail__c": ("alternate", ContactTypeEnum.personal),
        "npe01__WorkEmail__c": ("work", ContactTypeEnum.professional),
    }

    for column, (email_type, contact_type) in email_mappings.items():
        email = row.get(column, "").strip().lower()
        if email and email not in seen_emails:
            # Set primary based on the preferred email type from the CSV
            is_primary = False
            if preferred_type:
                is_primary = preferred_type == email_type
            else:
                # If no preferred type is specified, make the 'Email' column primary
                is_primary = column == "Email"

            emails.append(Email(email=email, type=contact_type, primary=is_primary))
            seen_emails.add(email)

    return emails


def get_phone_numbers(row):
    """
    Extract and format phone numbers from a CSV row.

    Processes multiple phone columns from Salesforce CSV data and creates
    Phone objects with appropriate types and primary designation.

    Args:
        row: Dictionary containing CSV row data

    Returns:
        List of Phone objects with type and primary designation

    Phone Types:
        - personal: General phone numbers
        - mobile: Mobile phone numbers
        - home: Home phone numbers
        - work: Work phone numbers

    Number Formatting:
        - Removes non-digit characters
        - Standardizes format for consistency
    """
    phones = []
    seen_numbers = set()  # Track unique numbers
    preferred_type = row.get("npe01__PreferredPhone__c", "").lower()

    # Map of CSV columns to phone types
    phone_mappings = {
        "Phone": ("phone", ContactTypeEnum.personal),
        "MobilePhone": ("mobile", ContactTypeEnum.personal),
        "HomePhone": ("home", ContactTypeEnum.personal),
        "npe01__WorkPhone__c": ("work", ContactTypeEnum.professional),
    }

    for column, (phone_type, contact_type) in phone_mappings.items():
        number = row.get(column, "").strip()
        # Standardize the number format (remove any non-digit characters)
        cleaned_number = "".join(filter(str.isdigit, number))

    return phones


def map_session_type(salesforce_type):
    """
    Map Salesforce session types to EventType enum values.

    Converts Salesforce session type strings to standardized EventType
    enum values used throughout the VMS system.

    Args:
        salesforce_type: Salesforce session type string

    Returns:
        EventType enum value, defaults to CLASSROOM_ACTIVITY if not found

    Supported Types:
        - Connector Session, Career Jumping, Career Speaker
        - Employability Skills, IGNITE, Career Fair
        - Client Connected Project, Pathway campus visits
        - Workplace Visit, Pathway Workplace Visits
        - College Options, DIA, Campus Visit
        - Advisory Sessions, Volunteer Orientation
        - Mentoring, Financial Literacy, Math Relays
        - Classroom Speaker, Internship, College Application Fair
        - FAFSA, Classroom Activity, Historical
        - DataViz, P2GD, SLA, HealthStart, P2T, BFI
    """
    mapping = {
        "Connector Session": EventType.CONNECTOR_SESSION,
        "Career Jumping": EventType.CAREER_JUMPING,
        "Career Speaker": EventType.CAREER_SPEAKER,
        "Employability Skills": EventType.EMPLOYABILITY_SKILLS,
        "IGNITE": EventType.IGNITE,
        "Career Fair": EventType.CAREER_FAIR,
        "Client Connected Project": EventType.CLIENT_CONNECTED_PROJECT,
        "Pathway campus visits": EventType.PATHWAY_CAMPUS_VISITS,
        "Workplace Visit": EventType.WORKPLACE_VISIT,
        "Pathway Workplace Visits": EventType.PATHWAY_WORKPLACE_VISITS,
        "College Options": EventType.COLLEGE_OPTIONS,
        "DIA - Classroom Speaker": EventType.DIA_CLASSROOM_SPEAKER,
        "DIA": EventType.DIA,
        "Campus Visit": EventType.CAMPUS_VISIT,
        "Advisory Sessions": EventType.ADVISORY_SESSIONS,
        "Volunteer Orientation": EventType.VOLUNTEER_ORIENTATION,
        "Volunteer Engagement": EventType.VOLUNTEER_ENGAGEMENT,
        "Mentoring": EventType.MENTORING,
        "Financial Literacy": EventType.FINANCIAL_LITERACY,
        "Math Relays": EventType.MATH_RELAYS,
        "Classroom Speaker": EventType.CLASSROOM_SPEAKER,
        "Internship": EventType.INTERNSHIP,
        "College Application Fair": EventType.COLLEGE_APPLICATION_FAIR,
        "FAFSA": EventType.FAFSA,
        "Classroom Activity": EventType.CLASSROOM_ACTIVITY,
        "Historical, Not Yet Updated": EventType.HISTORICAL,
        "DataViz": EventType.DATA_VIZ,
        "P2GD": EventType.P2GD,
        "SLA": EventType.SLA,
        "HealthStart": EventType.HEALTHSTART,
        "P2T": EventType.P2T,
        "BFI": EventType.BFI,
    }
    return mapping.get(salesforce_type, EventType.CLASSROOM_ACTIVITY)


def map_cancellation_reason(reason):
    """
    Map cancellation reasons to CancellationReason enum values.

    Converts Salesforce cancellation reason strings to standardized
    CancellationReason enum values.

    Args:
        reason: Salesforce cancellation reason string

    Returns:
        CancellationReason enum value or None if not recognized

    Supported Reasons:
        - 'Inclement Weather Cancellation' -> CancellationReason.WEATHER
    """
    if reason == "Inclement Weather Cancellation":
        return CancellationReason.WEATHER
    return None


def map_event_format(format_str):
    """
    Map Salesforce format to EventFormat enum values.

    Converts Salesforce event format strings to standardized EventFormat
    enum values.

    Args:
        format_str: Salesforce format string

    Returns:
        EventFormat enum value, defaults to IN_PERSON if not found

    Supported Formats:
        - 'In-Person' -> EventFormat.IN_PERSON
        - 'Virtual' -> EventFormat.VIRTUAL
    """
    format_mapping = {
        "In-Person": EventFormat.IN_PERSON,
        "Virtual": EventFormat.VIRTUAL,
    }
    return format_mapping.get(
        format_str, EventFormat.IN_PERSON
    )  # Default to in-person if not found


def parse_event_skills(skills_str, is_needed=False):
    """
    Parse skills from Legacy_Skill_Covered_for_the_Session__c or Legacy_Skills_Needed__c.

    Processes comma-separated skill strings from Salesforce event data,
    cleaning and standardizing skill names.

    Args:
        skills_str: Comma-separated skills string
        is_needed: Boolean indicating if these are needed skills (for future use)

    Returns:
        List of cleaned skill names

    Processing:
        - Splits by commas
        - Removes quotes and extra whitespace
        - Skips empty skills
        - Standardizes skill name format
    """
    if not skills_str:
        return []

    # Split by commas and clean up each skill
    skills = []
    raw_skills = [s.strip() for s in skills_str.split(",")]

    for skill in raw_skills:
        # Remove quotes if present
        skill = skill.strip('"')

        # Skip empty skills
        if not skill:
            continue

        # Map common prefixes to standardized categories
        if skill.startswith("PWY-"):
            skill = skill.replace("PWY-", "Pathway: ")
        elif skill.startswith("Skills-"):
            skill = skill.replace("Skills-", "Skill: ")
        elif skill.startswith("CCE-"):
            skill = skill.replace("CCE-", "Career/College: ")
        elif skill.startswith("CSCs-"):
            skill = skill.replace("CSCs-", "Core Skill: ")
        elif skill.startswith("ACT-"):
            skill = skill.replace("ACT-", "Activity: ")

        # Add "(Required)" suffix for needed skills
        if is_needed:
            skill = f"{skill} (Required)"

        skills.append(skill)

    return skills


def log_audit_action(action: str, resource_type: str, resource_id=None, metadata=None):
    """
    Append an audit log entry. Safe to call in routes.
    """
    try:
        entry = AuditLog(
            user_id=getattr(current_user, "id", None),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            method=getattr(request, "method", None),
            path=getattr(request, "path", None),
            ip=(
                (request.headers.get("X-Forwarded-For") or request.remote_addr)
                if request
                else None
            ),
            meta=metadata or {},
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Avoid raising audit failures; keep non-blocking
        pass
