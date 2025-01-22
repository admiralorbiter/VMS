from models import db
from models.contact import (
    Contact, EducationEnum, RaceEthnicityEnum, 
    LocalStatusEnum, SkillSourceEnum
)
from sqlalchemy import Enum, Date, Integer, String, Text, ForeignKey, Float
from sqlalchemy.orm import relationship, declared_attr
from models.history import History

class Volunteer(Contact):
    __tablename__ = 'volunteer'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'volunteer',
        'confirm_deleted_rows': False
    }
    
    # Organization Information
    organization_name = db.Column(String(100))
    title = db.Column(String(50))
    department = db.Column(String(50))
    industry = db.Column(String(50))

    # Additional Information
    education = db.Column(Enum(EducationEnum), nullable=True)
    local_status = db.Column(Enum(LocalStatusEnum), default=LocalStatusEnum.unknown)
    race_ethnicity = db.Column(Enum(RaceEthnicityEnum))

    # Volunteer Engagement Summary
    first_volunteer_date = db.Column(Date)
    last_volunteer_date = db.Column(Date)
    times_volunteered = db.Column(Integer, default=0)
    additional_volunteer_count = db.Column(Integer, default=0)

    # Communication History
    last_mailchimp_activity_date = db.Column(Date)
    mailchimp_history = db.Column(Text)
    admin_contacts = db.Column(String(200))

    # Relationships need @declared_attr
    @declared_attr
    def engagements(cls):
        return relationship('Engagement', backref='volunteer', lazy='dynamic')

    @declared_attr
    def organizations(cls):
        return relationship(
            'Organization',
            secondary='volunteer_organization',
            back_populates='volunteers',
            overlaps="volunteer_organizations"
        )

    @declared_attr
    def volunteer_organizations(cls):
        return relationship(
            'VolunteerOrganization',
            back_populates='volunteer',
            cascade='all, delete-orphan',
            passive_deletes=True,
            overlaps="organizations"
        )

    @declared_attr
    def skills(cls):
        return relationship('Skill', secondary='volunteer_skills', backref='volunteers')

    @declared_attr
    def event_participations(cls):
        return relationship('EventParticipation', backref='volunteer')

    @property
    def total_times_volunteered(self):
        return self.times_volunteered + self.additional_volunteer_count

    @property
    def active_histories(self):
        return History.query.filter_by(
            volunteer_id=self.id,
            is_deleted=False
        ).order_by(
            History.activity_date.desc()
        ).all()

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
    event = relationship('Event', backref='volunteer_participations')
