from sqlalchemy.orm import validates
from models import db
from models.utils import get_utc_now
from datetime import datetime, UTC
from enum import Enum
from sqlalchemy import event

class HistoryType(Enum):
    """Enum for categorizing different types of history records"""
    NOTE = 'note'
    ACTIVITY = 'activity'
    STATUS_CHANGE = 'status_change'
    ENGAGEMENT = 'engagement'
    SYSTEM = 'system'
    OTHER = 'other'

class History(db.Model):
    """History model for tracking volunteer activities and notes.
    
    This model maintains an audit trail of volunteer interactions, status changes,
    and administrative notes. Each record is timestamped and can be soft-deleted.
    
    Key Features:
    - Soft deletion support
    - Automatic timestamping
    - Type categorization
    - Activity tracking
    """
    __tablename__ = 'history'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys - Define relationships with other models
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    # CASCADE ensures that when a volunteer is deleted, all related history records are also deleted
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id'), nullable=False, index=True)
    
    # Core Activity Fields
    action = db.Column(db.String(255))  # Type of action performed (e.g., "created", "updated")
    summary = db.Column(db.Text)        # Brief overview of the activity (mapped from "Subject")
    description = db.Column(db.Text)    # Detailed description of the activity
    
    # Activity Metadata
    activity_type = db.Column(db.String(100), index=True)    # Categorization of activity
    activity_date = db.Column(db.DateTime, nullable=False, index=True)
    activity_status = db.Column(db.String(50), index=True)   # Current status of the activity
    
    # Timestamp Fields - Track record lifecycle
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    completed_at = db.Column(db.DateTime)                    # When the activity was completed
    last_modified_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)  # Change from get_utc_now to lambda
    )
    
    # Status and Integration Fields
    is_deleted = db.Column(db.Boolean, default=False, index=True)        # Soft delete flag
    email_message_id = db.Column(db.String(255), nullable=True)  # For email integration
    salesforce_id = db.Column(db.String(18), 
                            unique=True, 
                            nullable=True)    # For Salesforce integration
    
    # New columns for enhanced tracking
    history_type = db.Column(db.String(50), nullable=False, default='note', index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    additional_metadata = db.Column(db.JSON, nullable=True)  # For storing additional structured data
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    
    # Relationship Definitions
    # cascade='all, delete-orphan' ensures proper cleanup of related records
    event = db.relationship(
        'Event', 
        backref=db.backref(
            'histories',
            lazy='dynamic',           # Lazy loading for better performance
            cascade='all, delete-orphan'  # Automatically handle related records
        )
    )
    
    volunteer = db.relationship(
        'Volunteer',
        backref=db.backref(
            'histories',
            lazy='dynamic',
            cascade='all, delete-orphan'
        ),
        passive_deletes=True  # Works with ondelete="CASCADE" for better performance
    )

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    __table_args__ = (
        # Composite index for common queries
        db.Index('idx_volunteer_activity_date', 'volunteer_id', 'activity_date', 'is_deleted'),
    )

    def __init__(self, **kwargs):
        """Initialize history record with validation"""
        if 'activity_date' not in kwargs:
            kwargs['activity_date'] = datetime.now(UTC)
        super().__init__(**kwargs)

    @validates('notes')
    def validate_notes(self, key, value):
        """Ensure notes field is not empty when provided"""
        if value is not None and not value.strip():
            raise ValueError("Notes cannot be empty if provided")
        return value

    def soft_delete(self, user_id=None):
        """Soft delete the history record"""
        self.is_deleted = True
        self.updated_at = datetime.now(UTC)
        self.updated_by_id = user_id
        return self

    def restore(self, user_id=None):
        """Restore a soft-deleted history record"""
        self.is_deleted = False
        self.updated_at = datetime.now(UTC)
        self.updated_by_id = user_id
        return self

    @property
    def is_recent(self):
        """Check if history record is from the last 30 days"""
        if not self.activity_date:
            return False
        return (datetime.now(UTC) - self.activity_date).days <= 30

    def to_dict(self):
        """Convert history record to dictionary for API responses"""
        return {
            'id': self.id,
            'volunteer_id': self.volunteer_id,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'notes': self.notes,
            'history_type': self.history_type,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'created_by': self.created_by.username if self.created_by and self.created_by.username else None,
            'metadata': self.additional_metadata
        }

    def __repr__(self):
        """String representation for debugging"""
        return f'<History {self.id}: {self.history_type} on {self.activity_date}>'

    # Add a property to handle Enum conversion
    @property
    def history_type_enum(self):
        """Get the HistoryType enum value"""
        try:
            return HistoryType(self.history_type)
        except ValueError:
            return HistoryType.OTHER

    @history_type_enum.setter
    def history_type_enum(self, value):
        """Set history_type from enum value"""
        if isinstance(value, HistoryType):
            self.history_type = value.value.lower()
        elif isinstance(value, str):
            self.history_type = value.lower()
