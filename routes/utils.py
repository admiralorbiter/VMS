from datetime import datetime

from models.volunteer import ContactTypeEnum, Email

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