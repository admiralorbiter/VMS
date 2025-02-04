from models import db
from models.contact import (
    Contact, EducationEnum, LocalStatusEnum, RaceEthnicityEnum, SkillSourceEnum,
    FormEnum, Enum, ContactTypeEnum
)
from sqlalchemy import Integer, String, Date, ForeignKey, Text, Float
from sqlalchemy.orm import relationship, declared_attr
from models.history import History

class ConnectorSubscriptionEnum(FormEnum):
    NONE = ''
    ACTIVE = 'Active'
    INACTIVE = 'Inactive'
    PENDING = 'Pending'

class ConnectorData(db.Model):
    __tablename__ = 'connector_data'
    
    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    
    # Subscription and Role Info
    active_subscription = db.Column(Enum(ConnectorSubscriptionEnum), default=ConnectorSubscriptionEnum.NONE)
    active_subscription_name = db.Column(String(255))
    role = db.Column(String(20))
    signup_role = db.Column(String(20))
    
    # Profile and Activity
    profile_link = db.Column(String(1300))
    affiliations = db.Column(Text)
    industry = db.Column(String(255))
    user_auth_id = db.Column(String(7), unique=True)
    
    # Dates
    joining_date = db.Column(String(50))
    last_login_datetime = db.Column(String(50))
    last_update_date = db.Column(Date)
    
    # Define relationship back to volunteer
    volunteer = relationship('Volunteer', back_populates='connector')

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

    # Volunteer Engagement Summary
    first_volunteer_date = db.Column(Date)
    last_volunteer_date = db.Column(Date)
    last_non_internal_email_date = db.Column(Date)
    last_activity_date = db.Column(Date)
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

    @declared_attr
    def connector(cls):
        return relationship('ConnectorData', uselist=False, back_populates='volunteer',
                           cascade='all, delete-orphan')

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<Skill {self.name}>'

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
