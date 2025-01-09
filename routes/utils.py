from datetime import datetime

from models import db
from models.event import CancellationReason, District, EventFormat, EventType
from models.contact import ContactTypeEnum, Email

DISTRICT_MAPPINGS = {
    'KANSAS CITY USD 500': 'KANSAS CITY USD 500',
    'HICKMAN MILLS C-1': 'HICKMAN MILLS C-1',
    'GRANDVIEW C-4': 'GRANDVIEW C-4',
    'NORTH KANSAS CITY 74': 'NORTH KANSAS CITY 74',
    'REPUBLIC R-III': 'REPUBLIC R-III',
    'KANSAS CITY PUBLIC SCHOOL DISTRICT': 'KANSAS CITY PUBLIC SCHOOL DISTRICT',
    'INDEPENDENCE 30': 'INDEPENDENCE 30',
    'HOGAN PREPARATORY ACADEMY': 'HOGAN PREPARATORY ACADEMY',
    'PIPER-KANSAS CITY': 'PIPER-KANSAS CITY',
    'BELTON 124': 'BELTON 124',
    'CROSSROADS ACADEMY OF KANSAS CITY': 'CROSSROADS ACADEMY OF KANSAS CITY',
    'CENTER SCHOOL DISTRICT': 'CENTER SCHOOL DISTRICT',
    'GUADALUPE CENTERS SCHOOLS': 'GUADALUPE CENTERS SCHOOLS',
    'BLUE VALLEY': 'BLUE VALLEY',
    'BASEHOR-LINWOOD': 'BASEHOR-LINWOOD',
    'ALLEN VILLAGE': 'ALLEN VILLAGE',
    'SPRINGFIELD R-XII': 'SPRINGFIELD R-XII',
    'DE SOTO': 'DE SOTO',
    'INDEPENDENT': 'INDEPENDENT',
    'CENTER 58 SCHOOL DISTRICT': 'CENTER 58 SCHOOL DISTRICT'
}

def get_or_create_district(district_name):
    """Get existing district or create new one"""
    district = District.query.filter_by(name=district_name).first()
    if not district:
        district = District(name=district_name)
        db.session.add(district)
    return district

def parse_date(date_str):
    """Parse date string from Salesforce CSV or API"""
    if not date_str:
        return None
    
    try:
        # First try parsing ISO 8601 format (from Salesforce API)
        # Example: 2025-03-05T14:15:00.000+0000
        if 'T' in date_str:
            return datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            
        # Try CSV format with time (YYYY-MM-DD HH:MM:SS)
        try:
            parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M:%S')
            return parsed_date
        except ValueError:
            # If that fails, try without seconds (YYYY-MM-DD HH:MM)
            try:
                parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M')
                return parsed_date
            except ValueError:
                # Fallback for dates without times
                try:
                    return datetime.strptime(date_str.strip(), '%Y-%m-%d')
                except ValueError:
                    return None
    except Exception as e:
        print(f"Error parsing date {date_str}: {str(e)}")  # Debug logging
        return None

def clean_skill_name(skill_name):
    """Standardize skill name format"""
    return skill_name.strip().lower().capitalize()

def parse_skills(text_skills, comma_skills):
    """Parse and combine skills from both columns, removing duplicates"""
    skills = set()
    
    # Parse semicolon-separated skills
    if text_skills:
        skills.update(clean_skill_name(s) for s in text_skills.split(';') if s.strip())
    
    # Parse comma-separated skills
    if comma_skills:
        skills.update(clean_skill_name(s) for s in comma_skills.split(',') if s.strip())
    
    return list(skills)

def get_email_addresses(row):
    """Extract and format email addresses from a CSV row."""
    emails = []
    seen_emails = set()  # Track unique emails
    preferred_type = row.get('npe01__Preferred_Email__c', '').lower()
    
    # Map of CSV columns to email types
    email_mappings = {
        'Email': ('personal', ContactTypeEnum.personal),  # Changed 'email' to 'personal' to match data
        'npe01__HomeEmail__c': ('home', ContactTypeEnum.personal),
        'npe01__AlternateEmail__c': ('alternate', ContactTypeEnum.personal),
        'npe01__WorkEmail__c': ('work', ContactTypeEnum.professional)
    }

    for column, (email_type, contact_type) in email_mappings.items():
        email = row.get(column, '').strip().lower()
        if email and email not in seen_emails:
            # Set primary based on the preferred email type from the CSV
            is_primary = False
            if preferred_type:
                is_primary = (preferred_type == email_type)
            else:
                # If no preferred type is specified, make the 'Email' column primary
                is_primary = (column == 'Email')
            
            emails.append(Email(
                email=email,
                type=contact_type,
                primary=is_primary
            ))
            seen_emails.add(email)
    
    return emails


def get_phone_numbers(row):
    """Extract and format phone numbers from a CSV row."""
    phones = []
    seen_numbers = set()  # Track unique numbers
    preferred_type = row.get('npe01__PreferredPhone__c', '').lower()
    
    # Map of CSV columns to phone types
    phone_mappings = {
        'Phone': ('phone', ContactTypeEnum.personal),
        'MobilePhone': ('mobile', ContactTypeEnum.personal),
        'HomePhone': ('home', ContactTypeEnum.personal),
        'npe01__WorkPhone__c': ('work', ContactTypeEnum.professional)
    }
    
    for column, (phone_type, contact_type) in phone_mappings.items():
        number = row.get(column, '').strip()
        # Standardize the number format (remove any non-digit characters)
        cleaned_number = ''.join(filter(str.isdigit, number))
    
    return phones

def map_session_type(salesforce_type):
    """Map Salesforce session types to EventType enum values"""
    mapping = {
        'Connector Session': EventType.CONNECTOR_SESSION,
        'Career Jumping': EventType.CAREER_JUMPING,
        'Career Speaker': EventType.CAREER_SPEAKER,
        'Employability Skills': EventType.EMPLOYABILITY_SKILLS,
        'IGNITE': EventType.IGNITE,
        'Career Fair': EventType.CAREER_FAIR,
        'Client Connected Project': EventType.CLIENT_CONNECTED_PROJECT,
        'Pathway Campus Visits': EventType.PATHWAY_CAMPUS_VISITS,
        'Workplace Visit': EventType.WORKPLACE_VISIT,
        'Pathway Workplace Visits': EventType.PATHWAY_WORKPLACE_VISITS,
        'College Options': EventType.COLLEGE_OPTIONS,
        'DIA - Classroom Speaker': EventType.DIA_CLASSROOM_SPEAKER,
        'DIA': EventType.DIA,
        'Campus Visit': EventType.CAMPUS_VISIT,
        'Advisory Sessions': EventType.ADVISORY_SESSIONS,
        'Volunteer Orientation': EventType.VOLUNTEER_ORIENTATION,
        'Volunteer Engagement': EventType.VOLUNTEER_ENGAGEMENT,
        'Mentoring': EventType.MENTORING,
        'Financial Literacy': EventType.FINANCIAL_LITERACY,
        'Math Relays': EventType.MATH_RELAYS,
        'Classroom Speaker': EventType.CLASSROOM_SPEAKER,
        'Internship': EventType.INTERNSHIP,
        'College Application Fair': EventType.COLLEGE_APPLICATION_FAIR,
        'FAFSA': EventType.FAFSA,
        'Classroom Activity': EventType.CLASSROOM_ACTIVITY,
        'Historical, Not Yet Updated': EventType.HISTORICAL,
        'DataViz': EventType.DATA_VIZ
    }
    return mapping.get(salesforce_type, EventType.CLASSROOM_ACTIVITY)  # default to CLASSROOM_ACTIVITY if not found

def map_cancellation_reason(reason):
    """Map cancellation reasons to CancellationReason enum values"""
    if reason == 'Inclement Weather Cancellation':
        return CancellationReason.WEATHER
    return None

def map_event_format(format_str):
    """Map Salesforce format to EventFormat enum values"""
    format_mapping = {
        'In-Person': EventFormat.IN_PERSON,
        'Virtual': EventFormat.VIRTUAL
    }
    return format_mapping.get(format_str, EventFormat.IN_PERSON)  # Default to in-person if not found

def parse_event_skills(skills_str, is_needed=False):
    """Parse skills from Legacy_Skill_Covered_for_the_Session__c or Legacy_Skills_Needed__c"""
    if not skills_str:
        return []
    
    # Split by commas and clean up each skill
    skills = []
    raw_skills = [s.strip() for s in skills_str.split(',')]
    
    for skill in raw_skills:
        # Remove quotes if present
        skill = skill.strip('"')
        
        # Skip empty skills
        if not skill:
            continue
            
        # Map common prefixes to standardized categories
        if skill.startswith('PWY-'):
            skill = skill.replace('PWY-', 'Pathway: ')
        elif skill.startswith('Skills-'):
            skill = skill.replace('Skills-', 'Skill: ')
        elif skill.startswith('CCE-'):
            skill = skill.replace('CCE-', 'Career/College: ')
        elif skill.startswith('CSCs-'):
            skill = skill.replace('CSCs-', 'Core Skill: ')
        elif skill.startswith('ACT-'):
            skill = skill.replace('ACT-', 'Activity: ')
        
        # Add "(Required)" suffix for needed skills
        if is_needed:
            skill = f"{skill} (Required)"
            
        skills.append(skill)
    
    return skills