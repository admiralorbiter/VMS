"""
Teacher Model Module
===================

This module defines the Teacher model for managing teacher information in the VMS system.
It inherits from the Contact model and provides teacher-specific academic and professional data.

Key Features:
- Teacher information management and tracking
- School and department relationships
- Connector program participation tracking
- Event registration and participation
- Status tracking and management
- Salesforce integration
- Email and communication tracking
- CSV data import support

Database Table:
- teacher: Inherits from contact table with polymorphic identity

Teacher Management:
- Teacher identification and contact information
- School and department assignment
- Status tracking (active, inactive, on leave, retired)
- Connector program participation
- Event registration tracking

Connector Program:
- Connector role tracking
- Active status management
- Start and end date tracking
- Role validation and capitalization

Event Participation:
- Event registration tracking
- Upcoming and past events
- Event relationship management
- Registration status tracking

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Teacher record mapping and tracking
- School relationship synchronization
- Contact and affiliation data sync

Status Management:
- ACTIVE: Currently active teacher
- INACTIVE: Not currently active
- ON_LEAVE: Temporarily unavailable
- RETIRED: No longer teaching

Usage Examples:
    # Create a new teacher
    teacher = Teacher(
        first_name="Jane",
        last_name="Smith",
        department="Science",
        school_id="0015f00000JVZsFAAX",
        status=TeacherStatus.ACTIVE
    )
    
    # Update from CSV data
    teacher.update_from_csv(csv_data)
    
    # Get teacher's upcoming events
    upcoming = teacher.upcoming_events
    
    # Get teacher's school
    school = teacher.school
"""

from models import db
from models.contact import Contact, ContactTypeEnum, Email, Phone, GenderEnum
from sqlalchemy import String, Integer, Boolean, ForeignKey, Date, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declared_attr, validates
from datetime import datetime, timezone
from functools import cached_property
from enum import Enum
from models.school_model import School

class TeacherStatus(str, Enum):
    """
    Enum for tracking teacher status.
    
    Provides standardized status categories for teacher management
    and workflow tracking.
    
    Statuses:
        - ACTIVE: Currently active and available for teaching
        - INACTIVE: Not currently active but may return
        - ON_LEAVE: Temporarily unavailable (e.g., maternity leave)
        - RETIRED: No longer teaching
    """
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ON_LEAVE = 'on_leave'
    RETIRED = 'retired'

class Teacher(Contact):
    """
    Teacher model representing educational staff members.
    
    This model inherits from Contact for basic contact information and adds
    teacher-specific academic and professional data. It maintains relationships
    with schools, events, and connector programs for comprehensive teacher tracking.
    
    Database Table:
        teacher - Inherits from contact table with polymorphic identity
        
    Key Features:
        - Teacher information management and tracking
        - School and department relationships
        - Connector program participation tracking
        - Event registration and participation
        - Status tracking and management
        - Salesforce integration
        - Email and communication tracking
        - CSV data import support
        
    Teacher Management:
        - Teacher identification and contact information
        - School and department assignment
        - Status tracking (active, inactive, on leave, retired)
        - Connector program participation
        - Event registration tracking
        
    Connector Program:
        - connector_role: Teacher's role in connector program
        - connector_active: Whether teacher is active in connector program
        - connector_start_date: When teacher joined connector program
        - connector_end_date: When teacher left connector program
        
    Event Participation:
        - Event registration tracking through EventTeacher
        - Upcoming and past events filtering
        - Event relationship management
        - Registration status tracking
        
    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - Teacher record mapping and tracking
        - School relationship synchronization
        - Contact and affiliation data sync
        
    Status Management:
        - ACTIVE: Currently active teacher
        - INACTIVE: Not currently active
        - ON_LEAVE: Temporarily unavailable
        - RETIRED: No longer teaching
        
    Data Validation:
        - Connector role capitalization
        - Salesforce ID format validation
        - Status change tracking
        - Date range validation for connector program
        
    Performance Features:
        - Indexed fields for fast queries
        - Composite indexes for common query patterns
        - Eager loading for common relationships
        - Optimized CSV import processing
    """
    __tablename__ = 'teacher'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'teacher',
        'confirm_deleted_rows': False
    }
    
    # Teacher-specific fields
    department = db.Column(String(50), nullable=True, index=True)
    school_id = db.Column(String(255), nullable=True, index=True, 
                         comment="Maps to npsp__Primary_Affiliation__c in external systems")
    
    # Status tracking
    status = db.Column(SQLAlchemyEnum(TeacherStatus), default=TeacherStatus.ACTIVE, index=True)
    active = db.Column(Boolean, default=True, nullable=False)
    
    # Connector fields for tracking teacher relationships
    connector_role = db.Column(String(50), nullable=True)
    connector_active = db.Column(Boolean, default=False, nullable=False)
    connector_start_date = db.Column(Date, nullable=True)
    connector_end_date = db.Column(Date, nullable=True)
    
    # Email tracking fields
    last_email_message = db.Column(Date, nullable=True)
    last_mailchimp_date = db.Column(Date, nullable=True)

    # Salesforce Integration Fields
    salesforce_contact_id = db.Column(String(18), unique=True, nullable=True, index=True)
    salesforce_school_id = db.Column(String(18), ForeignKey('school.id'), nullable=True)
    
    # Metadata
    created_at = db.Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Enhanced event tracking
    event_registrations = db.relationship(
        'EventTeacher',
        back_populates='teacher',
        cascade='all, delete-orphan'
    )
    
    events = db.relationship(
        'Event',
        secondary='event_teacher',
        back_populates='teachers',
        viewonly=True  # Use event_registrations for modifications
    )
    
    school = relationship(
        'School',
        foreign_keys=[salesforce_school_id],
        backref=db.backref('teachers', lazy='dynamic')
    )
    
    __table_args__ = (
        db.CheckConstraint('connector_end_date >= connector_start_date',
                          name='check_date_range'),
        db.Index('idx_teacher_school_active', 'school_id', 'active'),
        db.Index('idx_teacher_status_school', 'status', 'salesforce_school_id'),
    )

    @validates('connector_role')
    def validate_connector_role(self, key, value):
        """
        Ensure connector role is properly capitalized.
        
        Args:
            key: Field name being validated
            value: Role value to validate
            
        Returns:
            str: Capitalized role value
        """
        if value:
            return value.capitalize()
        return value

    @validates('salesforce_contact_id')
    def validate_salesforce_id(self, key, value):
        """
        Validate Salesforce ID format.
        
        Args:
            key: Field name being validated
            value: Salesforce ID to validate
            
        Returns:
            str: Validated Salesforce ID
            
        Raises:
            ValueError: If Salesforce ID format is invalid
        """
        if value and (len(value) != 18 or not value.isalnum()):
            raise ValueError("Salesforce ID must be 18 alphanumeric characters")
        return value

    @validates('status')
    def validate_status(self, key, value):
        """
        Ensure proper handling of status changes.
        
        Args:
            key: Field name being validated
            value: Status value to validate
            
        Returns:
            TeacherStatus: Validated status value
            
        Raises:
            ValueError: If status is not a valid TeacherStatus
        """
        if value not in TeacherStatus:
            raise ValueError(f"Invalid status. Must be one of: {list(TeacherStatus)}")
        if hasattr(self, 'status') and self.status != value:
            self.status_change_date = datetime.now(timezone.utc)
        return value

    def __repr__(self):
        """
        String representation of the Teacher model.
        
        Returns:
            str: Debug representation showing teacher's full name
        """
        return f"<Teacher {self.first_name} {self.last_name}>"

    def update_from_csv(self, data):
        """
        Update teacher from CSV data.
        
        Processes CSV data to update teacher information including
        basic contact info, school assignment, connector program data,
        and communication tracking.
        
        Args:
            data: Dictionary containing CSV data fields
        """
        # Basic info
        self.first_name = data.get('FirstName', '').strip()
        self.last_name = data.get('LastName', '').strip()
        self.middle_name = ''  # Explicitly set to empty string
        self.school_id = data.get('npsp__Primary_Affiliation__c', '')
        self.gender = data.get('Gender__c', None)
        if 'Department' in data:
            self.department = data['Department']
        
        # Connector fields
        if 'Connector_Role__c' in data:
            self.connector_role = data['Connector_Role__c']
        if 'Connector_Active__c' in data:
            self.connector_active = data['Connector_Active__c']
        if 'Connector_Start_Date__c' in data:
            self.connector_start_date = data['Connector_Start_Date__c']
        if 'Connector_End_Date__c' in data:
            self.connector_end_date = data['Connector_End_Date__c']
        
        # Phone
        phone_number = data.get('Phone')
        if phone_number:
            existing_phone = Phone.query.filter_by(
                contact_id=self.id,
                number=phone_number,
                primary=True
            ).first()
            
            if not existing_phone:
                phone = Phone(
                    contact_id=self.id,
                    number=phone_number,
                    primary=True
                )
                db.session.add(phone)
        
        # Email
        email_address = data.get('Email')
        if email_address:
            # Check if email already exists
            existing_email = Email.query.filter_by(
                contact_id=self.id,
                email=email_address,
                primary=True
            ).first()
            
            if not existing_email:
                email = Email(
                    contact_id=self.id,
                    email=email_address,
                    type=ContactTypeEnum.personal,
                    primary=True
                )
                db.session.add(email)
        
        # Email tracking
        if data.get('Last_Email_Message__c'):
            self.last_email_message = data.get('Last_Email_Message__c')
        if data.get('Last_Mailchimp_Email_Date__c'):
            self.last_mailchimp_date = data.get('Last_Mailchimp_Email_Date__c')

    @property
    def upcoming_events(self):
        """
        Get teacher's upcoming events.
        
        Returns:
            list: List of upcoming events for this teacher
        """
        now = datetime.now(timezone.utc)
        return [reg.event for reg in self.event_registrations 
                if reg.event.start_date > now]
    
    @property
    def past_events(self):
        """
        Get teacher's past events.
        
        Returns:
            list: List of past events for this teacher
        """
        now = datetime.now(timezone.utc)
        return [reg.event for reg in self.event_registrations 
                if reg.event.start_date <= now]
