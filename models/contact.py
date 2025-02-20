from models import db
from sqlalchemy import Enum, Date, Boolean, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declared_attr
from enum import Enum as PyEnum

# Base Enum Class
class FormEnum(str, PyEnum):
    """Base enumeration class that provides helper methods for form handling.
    Inherits from both str and PyEnum to allow string comparison and enum functionality.
    """
    @classmethod
    def choices(cls):
        """Returns list of tuples (name, value) for use in form select fields.
        Example: [('mr', 'Mr.'), ('ms', 'Ms.')]
        """
        return [(member.name, member.value) for member in cls]

    @classmethod
    def choices_required(cls):
        """Similar to choices() but used when field is required.
        Returns same format as choices().
        """
        return [(member.name, member.value) for member in cls]

# Common Enums used across the application for standardization
class SalutationEnum(FormEnum):
    """Standard honorific titles/salutations for contacts"""
    none = ''
    mr = 'Mr.'
    ms = 'Ms.'
    mrs = 'Mrs.'
    dr = 'Dr.'
    prof = 'Prof.'
    mx = 'Mx.'
    rev = 'Rev.'
    hon = 'Hon.'
    captain = 'Captain'
    commissioner = 'Commissioner'
    general = 'General'
    judge = 'Judge'
    officer = 'Officer'
    staff_sergeant = 'Staff Sergeant'

class SuffixEnum(FormEnum):
    none = ''
    jr = 'Jr.'
    sr = 'Sr.'
    ii = 'II'
    iii = 'III'
    iv = 'IV'
    phd = 'Ph.D.'
    md = 'M.D.'
    esq = 'Esq.'

class GenderEnum(FormEnum):
    male = 'Male'
    female = 'Female'
    non_binary = 'Non-binary'
    genderfluid = 'Genderfluid'
    agender = 'Agender'
    transgender = 'Transgender'
    prefer_not_to_say = 'Prefer not to say'
    other = 'Other'

class ContactTypeEnum(FormEnum):
    personal = 'personal'
    professional = 'professional'

class RaceEthnicityEnum(FormEnum):
    unknown = 'Unknown'
    american_indian = 'American Indian or Alaska Native'
    asian = 'Asian'
    black = 'Black or African American'
    hispanic = 'Hispanic or Latino'
    native_hawaiian = 'Native Hawaiian or Other Pacific Islander'
    white = 'White'
    multi_racial = 'Multi-racial'
    bi_racial = 'Bi-racial'
    two_or_more = 'Two or More Races'
    prefer_not_to_say = 'Prefer not to say'
    other = 'Other'

class AgeGroupEnum(FormEnum):
    UNKNOWN = ''
    UNDER_18 = 'Under 18'
    AGE_18_24 = '18-24'
    AGE_25_34 = '25-34'
    AGE_35_44 = '35-44'
    AGE_45_54 = '45-54'
    AGE_55_64 = '55-64'
    AGE_65_PLUS = '65+'

class EducationEnum(FormEnum):
    UNKNOWN = ''
    HIGH_SCHOOL = 'High School'
    SOME_COLLEGE = 'Some College'
    ASSOCIATES = 'Associates Degree'
    BACHELORS_DEGREE = "Bachelor's Degree"
    MASTERS = 'Masters Degree'
    DOCTORATE = 'Doctorate'
    PROFESSIONAL = 'Professional Degree'
    OTHER = 'Other'

class LocalStatusEnum(FormEnum):
    local = 'local'          # Within KC metro
    partial = 'partial'      # Within driving distance
    non_local = 'non_local'  # Too far
    unknown = 'unknown'      # No address data

class SkillSourceEnum(FormEnum):
    job = 'job'
    organization = 'organization'
    interest = 'interest'
    previous_engagement = 'previous_engagement'
    user_selected = 'user_selected'
    admin_selected = 'admin_selected'

# Base Contact Models
class Contact(db.Model):
    """Base contact model that all other contact types inherit from (e.g., Volunteer, Teacher).
    Stores common contact information and relationships shared by all contact types.
    
    Key Relationships:
    - phones: One-to-many with Phone model
    - emails: One-to-many with Email model
    - addresses: One-to-many with Address model
    """
    __tablename__ = 'contact'
    
    id = db.Column(Integer, primary_key=True)
    type = db.Column(String(50))  # Stores the type of contact for polymorphic identity
    
    # External System IDs
    salesforce_individual_id = db.Column(String(18), unique=True, nullable=True)
    salesforce_account_id = db.Column(String(18), nullable=True)
    
    # Name Components
    salutation = db.Column(Enum(SalutationEnum), nullable=True)
    first_name = db.Column(String(50), nullable=False)
    middle_name = db.Column(String(50), nullable=True)
    last_name = db.Column(String(50), nullable=False)
    suffix = db.Column(Enum(SuffixEnum), nullable=True)
    
    # Demographic Information
    description = db.Column(Text)                                          # General notes about contact
    age_group = db.Column(Enum(AgeGroupEnum), default=AgeGroupEnum.UNKNOWN)
    education_level = db.Column(Enum(EducationEnum), default=EducationEnum.UNKNOWN)
    birthdate = db.Column(Date)
    gender = db.Column(Enum(GenderEnum))
    race_ethnicity = db.Column(Enum(RaceEthnicityEnum), nullable=True)
    
    # Communication Preferences and Status
    do_not_call = db.Column(Boolean, default=False)      # Indicates phone contact preference
    do_not_contact = db.Column(Boolean, default=False)   # Indicates no contact preference
    email_opt_out = db.Column(Boolean, default=False)    # Email marketing preference
    email_bounced_date = db.Column(DateTime)            # Tracks failed email deliveries
    
    # Activity Tracking
    last_email_date = db.Column(Date)                   # Date of last email communication
    notes = db.Column(Text)                            # General contact notes

    # SQLAlchemy inheritance configuration
    __mapper_args__ = {
        'polymorphic_identity': 'contact',    # Base identity for inheritance
        'polymorphic_on': type,              # Column used to determine contact type
        'confirm_deleted_rows': False        # Prevents deletion confirmation checks
    }

    # Relationship definitions with cascade delete enabled
    phones = relationship('Phone', 
                        backref='contact',
                        lazy='dynamic',
                        cascade='all, delete-orphan')  # Deletes related phones when contact is deleted
    
    emails = relationship('Email',
                        backref='contact',
                        lazy='dynamic',
                        cascade='all, delete-orphan')  # Deletes related emails when contact is deleted
    
    addresses = relationship('Address',
                          backref='contact',
                          lazy='dynamic',
                          cascade='all, delete-orphan')  # Deletes related addresses when contact is deleted

    @property
    def salesforce_contact_url(self):
        """Generates URL to view contact in Salesforce if ID exists"""
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

# Base Contact Info Models
class Phone(db.Model):
    """Stores phone numbers associated with contacts.
    Supports multiple numbers per contact with primary flag.
    """
    __tablename__ = 'phone'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    number = db.Column(String(20))
    type = db.Column(Enum(ContactTypeEnum))     # personal or professional
    primary = db.Column(Boolean, default=False)  # indicates preferred number

class Email(db.Model):
    """Stores email addresses associated with contacts.
    Supports multiple emails per contact with primary flag.
    """
    __tablename__ = 'email'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    email = db.Column(String(100))
    type = db.Column(Enum(ContactTypeEnum))     # personal or professional
    primary = db.Column(Boolean, default=False)  # indicates preferred email

    def to_dict(self):
        """Converts email object to dictionary for API responses"""
        return {
            'id': self.id,
            'email': self.email,
            'type': self.type.name if self.type else 'personal',
            'primary': self.primary
        }

class Address(db.Model):
    """Stores physical addresses associated with contacts.
    Supports multiple addresses per contact with primary flag.
    """
    __tablename__ = 'address'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    address_line1 = db.Column(String(100))
    address_line2 = db.Column(String(100))
    city = db.Column(String(50))
    state = db.Column(String(50))
    zip_code = db.Column(String(20))
    country = db.Column(String(50))
    type = db.Column(Enum(ContactTypeEnum))     # personal or professional
    primary = db.Column(Boolean, default=False)  # indicates preferred address