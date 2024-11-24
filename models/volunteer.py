from models import db
from sqlalchemy import Enum, Date, Boolean, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from models.history import History

# Base Enum Class
class FormEnum(str, PyEnum):
    @classmethod
    def choices(cls):
        return [
            (member.name, member.value)
            for member in cls
        ]

    @classmethod
    def choices_required(cls):
        return [
            (member.name, member.value)
            for member in cls
        ]

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
    prefer_not_to_say = 'Prefer not to say'
    other = 'Other'

class EducationEnum(FormEnum):
    high_school = 'High School Diploma'
    associate_degree = 'Associate Degree'
    bachelors_degree = 'Bachelor’s Degree'
    masters_degree = 'Master’s Degree'
    doctorate_degree = 'Doctorate Degree'
    professional_degree = 'Professional Degree'
    some_college = 'Some College'
    technical_certification = 'Technical Certification'
    other = 'Other'

class RaceEthnicityEnum(FormEnum):
    american_indian = 'American Indian or Alaska Native'
    asian = 'Asian'
    black = 'Black or African American'
    hispanic = 'Hispanic or Latino'
    native_hawaiian = 'Native Hawaiian or Other Pacific Islander'
    white = 'White'
    two_or_more = 'Two or More Races'
    prefer_not_to_say = 'Prefer not to say'
    other = 'Other'

# Enums for field choices
class LocalStatusEnum(FormEnum):
    true = 'true'
    partial = 'partial'
    false = 'false'
    unknown = 'unknown'

class ContactTypeEnum(FormEnum):
    personal = 'personal'
    professional = 'professional'

class SkillSourceEnum(FormEnum):
    job = 'job'
    organization = 'organization'
    interest = 'interest'
    previous_engagement = 'previous_engagement'
    user_selected = 'user_selected'
    admin_selected = 'admin_selected'

# Volunteer Model
class Volunteer(db.Model):
    __tablename__ = 'volunteer'
    
    id = db.Column(Integer, primary_key=True)
    salesforce_individual_id = db.Column(String(18), unique=True, nullable=True)
    salesforce_account_id = db.Column(String(18), nullable=True)
    salutation = db.Column(Enum(SalutationEnum), nullable=True)
    first_name = db.Column(String(50), nullable=False)
    middle_name = db.Column(String(50), nullable=True)
    last_name = db.Column(String(50), nullable=False)
    suffix = db.Column(Enum(SuffixEnum), nullable=True) 

    # Organization Information
    organization_name = db.Column(String(100))
    title = db.Column(String(50))
    department = db.Column(String(50))
    industry = db.Column(String(50))

    # Additional Information
    birthdate = db.Column(Date)
    gender = db.Column(Enum(GenderEnum))
    education = db.Column(Enum(EducationEnum))
    local_status = db.Column(Enum(LocalStatusEnum), default=LocalStatusEnum.unknown)
    race_ethnicity = db.Column(Enum(RaceEthnicityEnum))

    # Volunteer Engagement Summary
    first_volunteer_date = db.Column(Date)
    last_volunteer_date = db.Column(Date)
    times_volunteered = db.Column(Integer, default=0)
    additional_volunteer_count = db.Column(Integer, default=0)  # For adding constants

    last_mailchimp_activity_date = db.Column(Date)
    mailchimp_history = db.Column(Text)
    last_email_date = db.Column(Date)
    notes = db.Column(Text)
    admin_contacts = db.Column(String(200))

    # Relationships
    phones = relationship('Phone', backref='volunteer', lazy='dynamic')
    emails = relationship('Email', backref='volunteer', lazy='dynamic')
    addresses = relationship('Address', backref='volunteer', lazy='dynamic')
    engagements = relationship('Engagement', backref='volunteer', lazy='dynamic')
    
    # Add this new relationship
    organizations = relationship('Organization', 
                               secondary='volunteer_organization',
                               back_populates='volunteers')
    # Add this relationship
    volunteer_organizations = relationship('VolunteerOrganization', back_populates='volunteer')

    # Skills relationship through association table
    skills = relationship('Skill', secondary='volunteer_skills', backref='volunteers')

    @property
    def total_times_volunteered(self):
        return self.times_volunteered + self.additional_volunteer_count

    @property
    def active_histories(self):
        """Get non-deleted history records ordered by date"""
        return History.query.filter_by(
            volunteer_id=self.id,
            is_deleted=False
        ).order_by(
            History.activity_date.desc()
        ).all()

    @property
    def salesforce_contact_url(self):
        """Generate Salesforce contact URL if ID exists"""
        if self.salesforce_individual_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Contact/{self.salesforce_individual_id}/view"
        return None

    @property
    def salesforce_account_url(self):
        """Generate Salesforce account URL if ID exists"""
        if self.salesforce_account_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_account_id}/view"
        return None

# Phone Model
class Phone(db.Model):
    __tablename__ = 'phone'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    number = db.Column(String(20))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)

# Email Model
class Email(db.Model):
    __tablename__ = 'email'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    email = db.Column(String(100))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)

# Address Model
class Address(db.Model):
    __tablename__ = 'address'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    address_line1 = db.Column(String(100))
    address_line2 = db.Column(String(100))
    city = db.Column(String(50))
    state = db.Column(String(50))
    zip_code = db.Column(String(20))
    country = db.Column(String(50))
    type = db.Column(Enum(ContactTypeEnum))
    primary = db.Column(Boolean, default=False)

# Skill Model
class Skill(db.Model):
    __tablename__ = 'skill'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), unique=True, nullable=False)

# Association Table for Volunteer and Skill
class VolunteerSkill(db.Model):
    __tablename__ = 'volunteer_skills'

    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), primary_key=True)
    skill_id = db.Column(Integer, ForeignKey('skill.id'), primary_key=True)
    source = db.Column(Enum(SkillSourceEnum))
    interest_level = db.Column(String(20))  # Optional field

# Engagement Model
class Engagement(db.Model):
    __tablename__ = 'engagement'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    engagement_date = db.Column(Date)
    engagement_type = db.Column(String(50))
    notes = db.Column(Text)

# Event Participation Model
class EventParticipation(db.Model):
    __tablename__ = 'event_participation'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    event_id = db.Column(Integer, ForeignKey('event.id'), nullable=False)
    status = db.Column(String(20), nullable=False)  # For storing Status__c values like 'Attended', 'No-Show', etc.
    delivery_hours = db.Column(Float, nullable=True)  # For storing Delivery_Hours__c
    salesforce_id = db.Column(String(18), unique=True)  # For storing the original Id from Salesforce

    # Relationships
    volunteer = relationship('Volunteer', backref='event_participations')
    event = relationship('Event', backref='volunteer_participations')
