"""
Volunteer Management System - Models
===================================

This module contains the core data models for the volunteer management system.
It includes the main Volunteer model and related supporting models for tracking
volunteer information, skills, engagements, and participation in events.

Key Components:
- Volunteer: Main model inheriting from Contact
- ConnectorData: Specialized data for connector program volunteers
- Skill: Skills that volunteers can possess
- VolunteerSkill: Association table linking volunteers to skills
- Engagement: Individual volunteer engagement activities
- EventParticipation: Volunteer participation in specific events

Core Features:
- Comprehensive volunteer data management
- Skill tracking and matching capabilities
- Engagement and activity tracking
- Event participation recording
- Connector program support
- Local status calculation
- Historical data tracking
- Organization affiliations

Database Relationships:
- Volunteer inherits from Contact (polymorphic inheritance)
- Many-to-many relationships with skills and organizations
- One-to-many relationships with engagements and event participations
- One-to-one relationship with connector data
- History tracking for audit trails

Data Sources:
- Manual entry through web interface
- Salesforce synchronization
- External system integrations
- Automated data imports

Security and Privacy:
- Personal information protection
- Access control based on user permissions
- Audit trails for data changes
- GDPR compliance considerations

Author: VMS Development Team
Last Updated: 2024
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    or_,
)
from sqlalchemy.orm import declared_attr, relationship, validates

from models import db
from models.contact import (
    Contact,
    ContactTypeEnum,
    EducationEnum,
    Enum,
    FormEnum,
    LocalStatusEnum,
    RaceEthnicityEnum,
    SkillSourceEnum,
)
from models.history import History


class ConnectorSubscriptionEnum(FormEnum):
    """
    Enum representing the subscription status of a connector.

    Used to track whether a volunteer is actively participating in the connector program.
    This is a specialized program within the volunteer system that has additional
    requirements and tracking mechanisms.

    Values:
    - NONE: No subscription status (default)
    - ACTIVE: Currently active in connector program
    - INACTIVE: Previously active but currently inactive
    - PENDING: Awaiting activation or approval
    """

    NONE = ""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"


class ConnectorData(db.Model):
    """
    Model representing additional data for volunteers who are connectors.

    Stores subscription status, role information, and activity tracking details.
    Has a one-to-one relationship with the Volunteer model.

    Connectors are a specialized subset of volunteers who participate in a specific
    program with additional requirements and tracking mechanisms.

    Database Table:
        connector_data - Stores connector-specific information

    Key Features:
        - Subscription status tracking
        - Role management (current and signup roles)
        - Professional information storage
        - Activity tracking with timestamps
        - External profile integration
        - Authentication ID management

    Relationships:
        - One-to-one with Volunteer model
        - Unique constraints on user_auth_id and volunteer_id

    Attributes:
        volunteer_id: Foreign key to the volunteer
        active_subscription: Current subscription status in connector program
        active_subscription_name: Human-readable subscription name
        role: Current role in connector program
        signup_role: Original role when they signed up
        profile_link: URL to external profile
        affiliations: Organizations/groups they're affiliated with
        industry: Professional industry
        user_auth_id: Unique identifier for authentication
        joining_date: When they joined as a connector
        last_login_datetime: Last time they logged in
        last_update_date: Last time their record was updated
        created_at: Record creation timestamp
        updated_at: Record update timestamp
    """

    __tablename__ = "connector_data"

    # Database columns for identifying and linking to volunteer
    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id"), nullable=False)

    # Tracks whether the connector is currently participating in the program
    active_subscription = db.Column(
        Enum(ConnectorSubscriptionEnum),
        default=ConnectorSubscriptionEnum.NONE,
        index=True,
    )
    active_subscription_name = db.Column(String(255))

    # Role information - both current and initial signup role
    role = db.Column(String(20))
    signup_role = db.Column(String(20))

    # External profile and professional information
    profile_link = db.Column(String(1300))  # URL to connector's external profile
    affiliations = db.Column(Text)  # Organizations/groups they're affiliated with
    industry = db.Column(String(255))  # Their professional industry
    user_auth_id = db.Column(
        String(7), unique=True
    )  # Unique identifier for authentication

    # Tracking important dates
    joining_date = db.Column(String(50))  # When they joined as a connector
    last_login_datetime = db.Column(String(50))  # Last time they logged in
    last_update_date = db.Column(Date)  # Last time their record was updated

    # Automatic timestamp tracking (timezone-aware, Python-side defaults)
    created_at = db.Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=True
    )
    updated_at = db.Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
    )

    # Bidirectional relationship with Volunteer model
    # This allows easy access between volunteer and their connector data
    volunteer = relationship("Volunteer", back_populates="connector")

    # Ensure each connector has unique user_auth_id and volunteer_id
    __table_args__ = (
        db.UniqueConstraint("user_auth_id", name="uix_connector_user_auth_id"),
        db.UniqueConstraint("volunteer_id", name="uix_connector_volunteer_id"),
    )


class VolunteerStatus(FormEnum):
    """
    Enum defining the possible states of a volunteer's engagement.

    Used to track whether a volunteer is currently active, inactive, or on hold.
    This helps with volunteer management and communication strategies.

    Values:
    - NONE: No status set (default)
    - ACTIVE: Currently active and available for volunteering
    - INACTIVE: Not currently active but may return
    - ON_HOLD: Temporarily on hold (e.g., due to scheduling conflicts)
    """

    NONE = ""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_HOLD = "on_hold"


class Volunteer(Contact):
    """
    Main volunteer model that inherits from Contact base class.

    Stores all volunteer-specific information and manages relationships with other models.
    This is the core model for the volunteer management system.

    Database Table:
        volunteer - Inherits from contact table with polymorphic identity

    Key Relationships:
    - skills: Many-to-many with Skill model (through VolunteerSkill)
    - organizations: Many-to-many with Organization model
    - engagements: One-to-many with Engagement model
    - connector: One-to-one with ConnectorData model
    - event_participations: One-to-many with EventParticipation model
    - histories: One-to-many with History model for audit trails

    Inheritance:
    - Inherits from Contact model for basic contact information
    - Uses polymorphic inheritance to distinguish volunteer contacts from other types

    Key Features:
    - Tracks volunteer activity and engagement
    - Manages skills and organizational affiliations
    - Supports connector program participation
    - Handles local status calculation based on address
    - Provides comprehensive volunteer history tracking
    - Automatic date validation and status updates
    - Salesforce data synchronization support

    Data Management:
    - Professional information tracking
    - Demographic data collection
    - Activity and engagement metrics
    - Communication history
    - Status and availability tracking

    Validation Features:
    - Date validation for volunteer activities
    - Count validation for volunteer sessions
    - Education level validation
    - Local status calculation and updates
    """

    __tablename__ = "volunteer"

    # Links this table to the parent Contact table
    id = db.Column(Integer, ForeignKey("contact.id"), primary_key=True)

    # SQLAlchemy inheritance settings
    __mapper_args__ = {
        "polymorphic_identity": "volunteer",  # Identifies this as a volunteer type contact
        "confirm_deleted_rows": False,  # Prevents deletion confirmation checks
        "inherit_condition": id == Contact.id,  # Links to parent table
    }

    # Professional Information
    organization_name = db.Column(String(100))  # Current workplace
    title = db.Column(String(50))  # Job title
    department = db.Column(String(50))  # Department within organization
    industry = db.Column(String(50))  # Industry sector

    # Demographic and Status Information
    education = db.Column(Enum(EducationEnum), nullable=True)
    local_status = db.Column(
        Enum(LocalStatusEnum), default=LocalStatusEnum.unknown, index=True
    )
    local_status_last_updated = db.Column(DateTime)

    # People of Color tracking for virtual sessions
    is_people_of_color = db.Column(Boolean, default=False, index=True)

    # Volunteer Activity Tracking
    first_volunteer_date = db.Column(Date)  # First time they volunteered
    last_volunteer_date = db.Column(Date, index=True)  # Most recent volunteer activity
    last_non_internal_email_date = db.Column(Date)  # Last external communication
    last_activity_date = db.Column(Date, index=True)  # Any type of activity
    times_volunteered = db.Column(
        Integer, default=0
    )  # Number of recorded volunteer sessions
    additional_volunteer_count = db.Column(
        Integer, default=0
    )  # Manual adjustment to volunteer count

    # Communication and Engagement Tracking
    last_mailchimp_activity_date = db.Column(Date)
    mailchimp_history = db.Column(Text)  # Historical email engagement data
    admin_contacts = db.Column(
        String(200)
    )  # Staff members who've worked with this volunteer
    interests = db.Column(Text)  # Semicolon-separated volunteer interests

    # Current volunteer status (active, inactive, on hold)
    status = db.Column(
        Enum(VolunteerStatus), default=VolunteerStatus.ACTIVE, index=True
    )

    # Relationship definitions
    # Note: @declared_attr is used to define these relationships dynamically during class creation

    # Tracks all volunteer sessions/activities
    engagements = relationship(
        "Engagement",
        backref="volunteer",
        lazy="dynamic",  # Loads related items only when accessed
        cascade="all, delete-orphan",  # Deletes related items when volunteer is deleted
    )

    # Many-to-many relationship with organizations
    organizations = db.relationship(
        "Organization",
        secondary="volunteer_organization",  # Junction table name
        back_populates="volunteers",
        overlaps="volunteer_organizations",  # Handles overlap with the association proxy
    )

    @property
    def total_times_volunteered(self):
        """
        Calculates the total number of times this volunteer has volunteered.

        This property combines actual event participations with manual adjustments
        to provide an accurate count of volunteer activity.

        Returns:
            int: Total count of volunteer sessions including manual adjustments

        Note:
            This avoids double counting by not adding times_volunteered field
            which may contain outdated data from Salesforce imports.
        """
        from sqlalchemy import or_

        # Get count of participations with all relevant statuses
        participation_count = EventParticipation.query.filter(
            EventParticipation.volunteer_id == self.id,
            or_(
                EventParticipation.status == "Attended",
                EventParticipation.status == "Completed",
                EventParticipation.status == "Successfully Completed",
            ),
        ).count()

        # Add only the manual adjustment (don't add times_volunteered to avoid double counting)
        return participation_count + self.additional_volunteer_count

    @property
    def active_histories(self):
        """
        Returns all non-deleted history records for this volunteer, ordered by date.

        This provides a chronological view of all volunteer activities and interactions
        that have been recorded in the system.

        Returns:
            list: List of History objects ordered by activity_date descending
        """
        return (
            History.query.filter_by(contact_id=self.id, is_deleted=False)
            .order_by(History.activity_date.desc())
            .all()
        )

    def calculate_local_status(self):
        """
        Determines if a volunteer is local, partially local, or non-local based on zip code.

        This method analyzes the volunteer's address(es) to determine their geographic
        relationship to the organization's service area. This is important for:
        - Event planning and logistics
        - Communication strategies
        - Resource allocation

        Returns:
            LocalStatusEnum: The calculated status based on the volunteer's address(es)

        Logic:
        1. Checks primary address first
        2. Falls back to personal address if no primary exists
        3. Uses predefined KC metro and regional zip code prefixes
        4. Returns 'unknown' if no valid address is found or on error

        Zip Code Mapping:
        - Local: 640, 641, 660, 661, 664, 665, 666 (KC Metro)
        - Partial: 644, 645, 646, 670, 671, 672, 673, 674 (Regional)
        - Non-local: All other zip codes
        """
        try:
            # Define KC metro and regional zip code prefixes
            kc_metro_prefixes = ("640", "641", "660", "661", "664", "665", "666")
            region_prefixes = ("644", "645", "646", "670", "671", "672", "673", "674")

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
            personal_addr = next(
                (
                    addr
                    for addr in self.addresses
                    if addr.type == ContactTypeEnum.personal
                ),
                None,
            )
            if personal_addr and personal_addr.zip_code:
                return check_address_status(personal_addr)

            return LocalStatusEnum.unknown
        except Exception as e:
            print(f"Error calculating local status: {str(e)}")
            return LocalStatusEnum.unknown

    @validates("first_volunteer_date", "last_volunteer_date", "last_activity_date")
    def validate_dates(self, key, value):
        """
        Validates and converts date fields to proper date objects.

        This validator ensures that date fields are properly formatted and converted
        from various input formats (strings, date objects) to consistent date objects.

        Args:
            key (str): The name of the field being validated
            value: The date value to validate (can be string or date object)

        Returns:
            date: Converted date object or None if invalid

        Raises:
            ValueError: If date string cannot be parsed
        """
        if not value:  # Handle empty strings and None
            return None
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                print(f"Warning: Invalid date format for {key}: {value}")
                return None
        return value

    @validates("times_volunteered", "additional_volunteer_count")
    def validate_counts(self, key, value):
        """
        Validates and normalizes count fields to ensure they are non-negative integers.

        This validator handles various input formats and ensures count fields
        are properly formatted as integers with a minimum value of 0.

        Args:
            key (str): The name of the field being validated
            value: The count value to validate

        Returns:
            int: Normalized count value (minimum 0)
        """
        if not value:  # Handle empty strings and None
            return 0
        try:
            value = int(float(value))  # Handle string numbers and floats
            return max(0, value)
        except (ValueError, TypeError):
            print(f"Warning: Invalid {key} value: {value}")
            return 0

    @validates("education")
    def validate_education(self, key, value):
        """
        Validates education enum values to ensure they are valid EducationEnum instances.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible.

        Args:
            key (str): The name of the field being validated
            value: The education value to validate

        Returns:
            EducationEnum: Valid education enum value or None

        Raises:
            ValueError: If education value is invalid
        """
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
        """
        Creates a Volunteer instance from Salesforce data with proper data cleaning.

        This class method handles the conversion of Salesforce data to Volunteer
        instances, ensuring that empty strings are converted to None values
        and data is properly formatted.

        Args:
            data (dict): Dictionary containing Salesforce volunteer data

        Returns:
            Volunteer: New Volunteer instance with cleaned data
        """
        # Convert empty strings to None
        cleaned = {k: (None if v == "" else v) for k, v in data.items()}
        return cls(**cleaned)

    # Relationship definitions that were accidentally removed
    @declared_attr
    def volunteer_organizations(cls):
        """
        Many-to-many relationship with organizations through VolunteerOrganization.

        This relationship allows volunteers to be associated with multiple organizations
        with additional metadata about their role and status within each organization.

        Returns:
            relationship: SQLAlchemy relationship to VolunteerOrganization
        """
        return relationship(
            "VolunteerOrganization",
            back_populates="volunteer",
            cascade="all, delete-orphan",
            passive_deletes=True,
            overlaps="organizations",
        )

    @declared_attr
    def skills(cls):
        """
        Many-to-many relationship with skills through VolunteerSkill.

        This relationship allows volunteers to have multiple skills with additional
        metadata about the source of the skill and interest level.

        Returns:
            relationship: SQLAlchemy relationship to Skill model
        """
        return relationship("Skill", secondary="volunteer_skills", backref="volunteers")

    @declared_attr
    def event_participations(cls):
        """
        One-to-many relationship with event participations.

        This relationship tracks all events that a volunteer has participated in,
        including their role, status, and contribution details.

        Returns:
            relationship: SQLAlchemy relationship to EventParticipation model
        """
        return relationship("EventParticipation", backref="volunteer")

    @declared_attr
    def connector(cls):
        """
        One-to-one relationship with connector data.

        This relationship provides access to specialized connector program data
        for volunteers who participate in the connector program.

        Returns:
            relationship: SQLAlchemy relationship to ConnectorData model
        """
        return relationship(
            "ConnectorData",
            uselist=False,
            back_populates="volunteer",
            cascade="all, delete-orphan",
            single_parent=True,
        )


# Skill Model
class Skill(db.Model):
    """
    Model representing a skill that volunteers can possess.

    Used to track various capabilities and expertise areas of volunteers.
    This allows for skill-based volunteer matching and reporting.

    Attributes:
        id: Primary key
        name: Unique skill name (e.g., "Python Programming", "Event Planning")
    """

    __tablename__ = "skill"

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), unique=True, nullable=False)

    def __str__(self):
        """String representation of the skill."""
        return self.name

    def __repr__(self):
        """Developer-friendly representation of the skill."""
        return f"<Skill {self.name}>"


# Association Table for Volunteer and Skill
class VolunteerSkill(db.Model):
    """
    Association model connecting volunteers to their skills.

    Includes additional metadata about the skill relationship such as
    the source of the skill information and the volunteer's interest level.

    Attributes:
        volunteer_id: Foreign key to volunteer
        skill_id: Foreign key to skill
        source: How the skill information was obtained (e.g., self-reported, assessed)
        interest_level: Optional field for tracking interest level in the skill
    """

    __tablename__ = "volunteer_skills"

    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id"), primary_key=True)
    skill_id = db.Column(Integer, ForeignKey("skill.id"), primary_key=True)
    source = db.Column(Enum(SkillSourceEnum))
    interest_level = db.Column(String(20))  # Optional field


# Engagement Model
class Engagement(db.Model):
    """
    Model tracking individual volunteer engagement activities.

    Records specific interactions and activities of volunteers that may not
    be tied to specific events. This includes things like:
    - Phone calls
    - Email communications
    - Training sessions
    - Orientation meetings

    Attributes:
        id: Primary key
        volunteer_id: Foreign key to volunteer
        engagement_date: Date of the engagement
        engagement_type: Type of engagement (e.g., "Phone Call", "Training")
        notes: Additional notes about the engagement
    """

    __tablename__ = "engagement"

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id"), nullable=False)
    engagement_date = db.Column(Date)
    engagement_type = db.Column(String(50))
    notes = db.Column(Text)


# Event Participation Model
class EventParticipation(db.Model):
    """
    Model tracking volunteer participation in specific events.

    Includes details about their role and contribution to each event.
    This is the primary way to track volunteer activity and impact.

    Fields from Salesforce Session_Participant__c are mapped to this model
    to maintain compatibility with existing Salesforce data.

    Attributes:
        id: Primary key
        volunteer_id: Foreign key to volunteer
        event_id: Foreign key to event
        status: Participation status (e.g., "Attended", "No-Show", "Cancelled")
        delivery_hours: Hours contributed to the event
        salesforce_id: Salesforce record ID for synchronization
        age_group: Age group of participant at time of event
        email: Email used for event registration
        title: Professional title at time of event
        participant_type: Type of participant (default: "Volunteer")
        contact: Additional contact information
    """

    __tablename__ = "event_participation"

    id = db.Column(Integer, primary_key=True)
    volunteer_id = db.Column(Integer, ForeignKey("volunteer.id"), nullable=False)
    event_id = db.Column(Integer, ForeignKey("event.id"), nullable=False)

    # Fields from Salesforce Session_Participant__c
    status = db.Column(String(20), nullable=False)
    delivery_hours = db.Column(Float, nullable=True)
    salesforce_id = db.Column(String(18), unique=True)
    age_group = db.Column(String(50), nullable=True)
    email = db.Column(String(255), nullable=True)
    title = db.Column(String(100), nullable=True)
    participant_type = db.Column(String(50), default="Volunteer")
    contact = db.Column(String(255), nullable=True)

    # Relationships
    event = relationship("Event", backref="volunteer_participations")
