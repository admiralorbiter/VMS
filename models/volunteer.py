from models import db
from models.contact import (
    Contact, EducationEnum, LocalStatusEnum, RaceEthnicityEnum, SkillSourceEnum,
    FormEnum, Enum, ContactTypeEnum
)
from sqlalchemy import Integer, String, Date, ForeignKey, Text, Float, DateTime
from sqlalchemy.orm import relationship, declared_attr, validates
from models.history import History
from datetime import date, datetime

class ConnectorSubscriptionEnum(FormEnum):
    """Enum representing the subscription status of a connector.
    Used to track whether a volunteer is actively participating in the connector program.
    """
    NONE = ''
    ACTIVE = 'Active'
    INACTIVE = 'Inactive'
    PENDING = 'Pending'

class ConnectorData(db.Model):
    """Model representing additional data for volunteers who are connectors.
    Stores subscription status, role information, and activity tracking details.
    Has a one-to-one relationship with the Volunteer model.
    """
    __tablename__ = 'connector_data'
    
    # Database columns for identifying and linking to volunteer
    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    
    # Tracks whether the connector is currently participating in the program
    active_subscription = db.Column(Enum(ConnectorSubscriptionEnum), default=ConnectorSubscriptionEnum.NONE, index=True)
    active_subscription_name = db.Column(String(255))
    
    # Role information - both current and initial signup role
    role = db.Column(String(20))
    signup_role = db.Column(String(20))
    
    # External profile and professional information
    profile_link = db.Column(String(1300))  # URL to connector's external profile
    affiliations = db.Column(Text)          # Organizations/groups they're affiliated with
    industry = db.Column(String(255))       # Their professional industry
    user_auth_id = db.Column(String(7), unique=True)  # Unique identifier for authentication
    
    # Tracking important dates
    joining_date = db.Column(String(50))           # When they joined as a connector
    last_login_datetime = db.Column(String(50))    # Last time they logged in
    last_update_date = db.Column(Date)            # Last time their record was updated
    
    # Automatic timestamp tracking
    created_at = db.Column(DateTime, nullable=True)
    updated_at = db.Column(DateTime, nullable=True)
    
    # Bidirectional relationship with Volunteer model
    # This allows easy access between volunteer and their connector data
    volunteer = relationship('Volunteer', back_populates='connector')

    # Ensure each connector has unique user_auth_id and volunteer_id
    __table_args__ = (
        db.UniqueConstraint('user_auth_id', name='uix_connector_user_auth_id'),
        db.UniqueConstraint('volunteer_id', name='uix_connector_volunteer_id'),
    )

class VolunteerStatus(FormEnum):
    """Enum defining the possible states of a volunteer's engagement.
    Used to track whether a volunteer is currently active, inactive, or on hold.
    """
    NONE = ''
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ON_HOLD = 'on_hold'

class Volunteer(Contact):
    """Main volunteer model that inherits from Contact base class.
    Stores all volunteer-specific information and manages relationships with other models.
    
    Key Relationships:
    - skills: Many-to-many with Skill model (through VolunteerSkill)
    - organizations: Many-to-many with Organization model
    - engagements: One-to-many with Engagement model
    - connector: One-to-one with ConnectorData model
    - event_participations: One-to-many with EventParticipation model
    """
    __tablename__ = 'volunteer'
    
    # Links this table to the parent Contact table
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    # SQLAlchemy inheritance settings
    __mapper_args__ = {
        'polymorphic_identity': 'volunteer',  # Identifies this as a volunteer type contact
        'confirm_deleted_rows': False,        # Prevents deletion confirmation checks
        'inherit_condition': id == Contact.id # Links to parent table
    }
    
    # Professional Information
    organization_name = db.Column(String(100))  # Current workplace
    title = db.Column(String(50))              # Job title
    department = db.Column(String(50))         # Department within organization
    industry = db.Column(String(50))           # Industry sector

    # Demographic and Status Information
    education = db.Column(Enum(EducationEnum), nullable=True)
    local_status = db.Column(Enum(LocalStatusEnum), default=LocalStatusEnum.unknown, index=True)
    local_status_last_updated = db.Column(DateTime)

    # Volunteer Activity Tracking
    first_volunteer_date = db.Column(Date)                    # First time they volunteered
    last_volunteer_date = db.Column(Date, index=True)         # Most recent volunteer activity
    last_non_internal_email_date = db.Column(Date)            # Last external communication
    last_activity_date = db.Column(Date, index=True)          # Any type of activity
    times_volunteered = db.Column(Integer, default=0)         # Number of recorded volunteer sessions
    additional_volunteer_count = db.Column(Integer, default=0) # Manual adjustment to volunteer count

    # Communication and Engagement Tracking
    last_mailchimp_activity_date = db.Column(Date)
    mailchimp_history = db.Column(Text)           # Historical email engagement data
    admin_contacts = db.Column(String(200))       # Staff members who've worked with this volunteer
    interests = db.Column(Text)                   # Semicolon-separated volunteer interests

    # Current volunteer status (active, inactive, on hold)
    status = db.Column(Enum(VolunteerStatus), default=VolunteerStatus.ACTIVE, index=True)

    # Relationship definitions
    # Note: @declared_attr is used to define these relationships dynamically during class creation
    
    # Tracks all volunteer sessions/activities
    engagements = relationship(
        'Engagement',
        backref='volunteer',
        lazy='dynamic',  # Loads related items only when accessed
        cascade="all, delete-orphan"  # Deletes related items when volunteer is deleted
    )

    # Many-to-many relationship with organizations
    organizations = db.relationship(
        'Organization',
        secondary='volunteer_organization',  # Junction table name
        back_populates='volunteers',
        overlaps="volunteer_organizations"   # Handles overlap with the association proxy
    )

    @property
    def total_times_volunteered(self):
        """Calculates total volunteer sessions including manual adjustments"""
        return self.times_volunteered + self.additional_volunteer_count

    @property
    def active_histories(self):
        """Returns all non-deleted history records for this volunteer, ordered by date"""
        return History.query.filter_by(
            volunteer_id=self.id,
            is_deleted=False
        ).order_by(
            History.activity_date.desc()
        ).all()

    def calculate_local_status(self):
        """Determines if a volunteer is local, partially local, or non-local based on zip code.
        
        Returns:
            LocalStatusEnum: The calculated status based on the volunteer's address(es)
        
        Logic:
        1. Checks primary address first
        2. Falls back to personal address if no primary exists
        3. Uses predefined KC metro and regional zip code prefixes
        4. Returns 'unknown' if no valid address is found or on error
        """
        try:
            # Define KC metro and regional zip code prefixes
            kc_metro_prefixes = ('640', '641', '660', '661', '664', '665', '666')
            region_prefixes = ('644', '645', '646', '670', '671', '672', '673', '674')
            
            def check_address_status(address):
                """Helper function to check status based on zip code prefix"""
                if not address or not address.zip_code:
                    return None
                    
                zip_prefix = address.zip_code[:3]
                if zip_prefix in kc_metro_prefixes:
                    return LocalStatusEnum.local
                if zip_prefix in region_prefixes:
                    return LocalStatusEnum.partial
                return LocalStatusEnum.non_local

            # First check if there's a primary address
            primary_addr = next((addr for addr in self.addresses if addr.primary), None)
            if primary_addr:
                # If primary exists but has no zip, return partial
                if not primary_addr.zip_code:
                    return LocalStatusEnum.partial
                # If primary has zip, use it
                return check_address_status(primary_addr)

            # If no primary address, try personal address
            personal_addr = next((addr for addr in self.addresses 
                                if addr.type == ContactTypeEnum.personal), None)
            if personal_addr and personal_addr.zip_code:
                return check_address_status(personal_addr)

            return LocalStatusEnum.unknown  
        except Exception as e:
            print(f"Error calculating local status: {str(e)}")
            return LocalStatusEnum.unknown

    @validates('first_volunteer_date', 'last_volunteer_date', 'last_activity_date')
    def validate_dates(self, key, value):
        """Validates and converts date fields to proper date objects.
        
        Args:
            key (str): The name of the field being validated
            value: The date value to validate (can be string or date object)
        
        Returns:
            date: Converted date object or None if invalid
        """
        if not value:  # Handle empty strings and None
            return None
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                print(f"Warning: Invalid date format for {key}: {value}")
                return None
        return value

    @validates('times_volunteered', 'additional_volunteer_count')
    def validate_counts(self, key, value):
        if not value:  # Handle empty strings and None
            return 0
        try:
            value = int(float(value))  # Handle string numbers and floats
            return max(0, value)
        except (ValueError, TypeError):
            print(f"Warning: Invalid {key} value: {value}")
            return 0

    @validates('education')
    def validate_education(self, key, value):
        if value is not None:
            # If it's already an enum instance, return it
            if isinstance(value, EducationEnum):
                return value
            if isinstance(value, str):
                try:
                    return EducationEnum[value.upper()]
                except KeyError:
                    raise ValueError(f"Invalid education value: {value}")
            raise ValueError(f"Education must be an EducationEnum value")
        return value

    # Add data cleaning for Salesforce imports
    @classmethod
    def from_salesforce(cls, data):
        # Convert empty strings to None
        cleaned = {k: (None if v == "" else v) for k, v in data.items()}
        return cls(**cleaned)

    # Relationship definitions that were accidentally removed
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
        return relationship(
            "ConnectorData",
            uselist=False,
            back_populates="volunteer",
            cascade="all, delete-orphan",
            single_parent=True
        )

# Skill Model
class Skill(db.Model):
    """Model representing a skill that volunteers can possess.
    Used to track various capabilities and expertise areas of volunteers.
    """
    __tablename__ = 'skill'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), unique=True, nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<Skill {self.name}>'

# Association Table for Volunteer and Skill
class VolunteerSkill(db.Model):
    """Association model connecting volunteers to their skills.
    Includes additional metadata about the skill relationship.
    """
    __tablename__ = 'volunteer_skills'

    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), primary_key=True)
    skill_id = db.Column(Integer, ForeignKey('skill.id'), primary_key=True)
    source = db.Column(Enum(SkillSourceEnum))
    interest_level = db.Column(String(20))  # Optional field

# Engagement Model
class Engagement(db.Model):
    """Model tracking individual volunteer engagement activities.
    Records specific interactions and activities of volunteers.
    """
    __tablename__ = 'engagement'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    engagement_date = db.Column(Date)
    engagement_type = db.Column(String(50))
    notes = db.Column(Text)

# Event Participation Model
class EventParticipation(db.Model):
    """Model tracking volunteer participation in specific events.
    Includes details about their role and contribution to each event.
    """
    __tablename__ = 'event_participation'

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey('volunteer.id'), nullable=False)
    event_id = db.Column(Integer, ForeignKey('event.id'), nullable=False)
    
    # Fields from Salesforce Session_Participant__c
    status = db.Column(String(20), nullable=False)
    delivery_hours = db.Column(Float, nullable=True)
    salesforce_id = db.Column(String(18), unique=True)
    age_group = db.Column(String(50), nullable=True)
    email = db.Column(String(255), nullable=True)
    title = db.Column(String(100), nullable=True)
    participant_type = db.Column(String(50), default='Volunteer')
    contact = db.Column(String(255), nullable=True)
    
    # Relationships
    event = relationship('Event', backref='volunteer_participations')
