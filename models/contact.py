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
    
    # Basic Info
    birthdate = db.Column(Date)
    gender = db.Column(Enum(GenderEnum))
    
    # Tracking
    last_email_date = db.Column(Date)
    notes = db.Column(Text)

    __mapper_args__ = {
        'polymorphic_identity': 'contact',
        'polymorphic_on': type
    }

    # Relationships
    phones = relationship('Phone', backref='contact', lazy='dynamic')
    emails = relationship('Email', backref='contact', lazy='dynamic')
    addresses = relationship('Address', backref='contact', lazy='dynamic')

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

# Volunteer-specific enums
class EducationEnum(FormEnum):
    none = ''
    high_school = 'High School Diploma'
    associate_degree = 'Associate Degree'
    bachelors_degree = "Bachelor's Degree"
    masters_degree = "Master's Degree"
    doctorate_degree = 'Doctorate Degree'
    professional_degree = 'Professional Degree'
    some_college = 'Some College'
    technical_certification = 'Technical Certification'
    other = 'Other'

class RaceEthnicityEnum(FormEnum):
    unknown = 'Unknown'
    american_indian = 'American Indian or Alaska Native'
    asian = 'Asian'
    black = 'Black or African American'
    hispanic = 'Hispanic or Latino'
    native_hawaiian = 'Native Hawaiian or Other Pacific Islander'
    white = 'White'
    two_or_more = 'Two or More Races'
    prefer_not_to_say = 'Prefer not to say'
    other = 'Other'

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