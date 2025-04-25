from models import db
from models.contact import Contact, ContactTypeEnum, Email, Phone, GenderEnum
from sqlalchemy import String, Integer, Boolean, ForeignKey, Date, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declared_attr, validates
from datetime import datetime, timezone
from functools import cached_property
from enum import Enum
from models.school_model import School

class TeacherStatus(str, Enum):
    """Enum for tracking teacher status"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ON_LEAVE = 'on_leave'
    RETIRED = 'retired'

class Teacher(Contact):
    """
    Teacher model representing educational staff members.
    Inherits from Contact and adds teaching-specific fields.
    
    Key Relationships:
    - school: Many-to-one relationship with School model
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
        """Ensure connector role is properly capitalized"""
        if value:
            return value.capitalize()
        return value

    @validates('salesforce_contact_id')
    def validate_salesforce_id(self, key, value):
        """Validate Salesforce ID format"""
        if value and (len(value) != 18 or not value.isalnum()):
            raise ValueError("Salesforce ID must be 18 alphanumeric characters")
        return value

    @validates('status')
    def validate_status(self, key, value):
        """Ensure proper handling of status changes"""
        if value not in TeacherStatus:
            raise ValueError(f"Invalid status. Must be one of: {list(TeacherStatus)}")
        if hasattr(self, 'status') and self.status != value:
            self.status_change_date = datetime.now(timezone.utc)
        return value

    def __repr__(self):
        return f"<Teacher {self.first_name} {self.last_name}>"

    def update_from_csv(self, data):
        """Update teacher from CSV data"""
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
        """Get teacher's upcoming events"""
        now = datetime.now(timezone.utc)
        return [reg.event for reg in self.event_registrations 
                if reg.event.start_date > now]
    
    @property
    def past_events(self):
        """Get teacher's past events"""
        now = datetime.now(timezone.utc)
        return [reg.event for reg in self.event_registrations 
                if reg.event.start_date <= now]
