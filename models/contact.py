from models import db
from sqlalchemy import Enum, Date, Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from enum import Enum as PyEnum

# Base Enum Class (moved from volunteer.py)
class FormEnum(str, PyEnum):
    @classmethod
    def choices(cls):
        return [(member.name, member.value) for member in cls]

    @classmethod
    def choices_required(cls):
        return [(member.name, member.value) for member in cls]

# Common Enums
class SalutationEnum(FormEnum):
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
    BACHELORS = 'Bachelors Degree'
    MASTERS = 'Masters Degree'
    DOCTORATE = 'Doctorate'
    PROFESSIONAL = 'Professional Degree'
    OTHER = 'Other'

class LocalStatusEnum(FormEnum):
    true = 'true'
    partial = 'partial'
    false = 'false'
    unknown = 'unknown'

class SkillSourceEnum(FormEnum):
    job = 'job'
    organization = 'organization'
    interest = 'interest'
    previous_engagement = 'previous_engagement'
    user_selected = 'user_selected'
    admin_selected = 'admin_selected'

# Base Contact Models
class Contact(db.Model):
    """Base contact model that creates a real table"""
    __tablename__ = 'contact'
    
    id = db.Column(Integer, primary_key=True)
    type = db.Column(String(50))  # To store the type of contact (volunteer, teacher, student)
    
    # Basic identification
    salesforce_individual_id = db.Column(String(18), unique=True, nullable=True)
    salesforce_account_id = db.Column(String(18), nullable=True)
    salutation = db.Column(Enum(SalutationEnum), nullable=True)
    first_name = db.Column(String(50), nullable=False)
    middle_name = db.Column(String(50), nullable=True)
    last_name = db.Column(String(50), nullable=False)
    suffix = db.Column(Enum(SuffixEnum), nullable=True)
    
    # Personal Information
    description = db.Column(Text)
    age_group = db.Column(Enum(AgeGroupEnum), default=AgeGroupEnum.UNKNOWN)
    education_level = db.Column(Enum(EducationEnum), default=EducationEnum.UNKNOWN)
    
    # Basic Info
    birthdate = db.Column(Date)
    gender = db.Column(Enum(GenderEnum))
    race_ethnicity = db.Column(Enum(RaceEthnicityEnum), nullable=True)
    
    # Tracking
    last_email_date = db.Column(Date)
    notes = db.Column(Text)

    __mapper_args__ = {
        'polymorphic_identity': 'contact',
        'polymorphic_on': type,
        'confirm_deleted_rows': False
    }

    # Update relationships to include cascade delete
    phones = relationship('Phone', backref='contact', lazy='dynamic',
                         cascade='all, delete-orphan')
    emails = relationship('Email', backref='contact', lazy='dynamic',
                         cascade='all, delete-orphan')
    addresses = relationship('Address', backref='contact', lazy='dynamic',
                           cascade='all, delete-orphan')

    @property
    def salesforce_contact_url(self):
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
        """Returns the primary email address for this contact, or None if not found."""
        primary = self.emails.filter_by(primary=True).first()
        return primary.email if primary else None

    @property
    def primary_email_object(self):
        """Returns the primary email object for this contact, or None if not found."""
        return self.emails.filter_by(primary=True).first()

# Base Contact Info Models
class Phone(db.Model):
    __tablename__ = 'phone'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    number = db.Column(String(20))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)

class Email(db.Model):
    __tablename__ = 'email'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    email = db.Column(String(100))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'type': self.type.name if self.type else 'personal',
            'primary': self.primary
        }

class Address(db.Model):
    __tablename__ = 'address'

    id = db.Column(Integer, primary_key=True)
    contact_id = db.Column(Integer, ForeignKey('contact.id'), nullable=False)
    address_line1 = db.Column(String(100))
    address_line2 = db.Column(String(100))
    city = db.Column(String(50))
    state = db.Column(String(50))
    zip_code = db.Column(String(20))
    country = db.Column(String(50))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)