"""
History Models Module
====================

This module defines the History model for tracking volunteer activities, notes,
and system changes in the VMS system. It provides comprehensive audit trail
functionality with soft deletion support.

Key Features:
- Comprehensive audit trail for volunteer activities
- Soft deletion support for data preservation
- Automatic timestamping and user tracking
- Activity categorization and status tracking
- Salesforce integration for data synchronization
- Email integration for communication tracking
- JSON metadata storage for flexible data
- Recent activity detection

Database Table:
- history: Stores all volunteer activity and note records

History Types:
- NOTE: General notes and comments
- ACTIVITY: Volunteer activities and engagements
- STATUS_CHANGE: Changes to volunteer status
- ENGAGEMENT: Specific engagement activities
- SYSTEM: System-generated records
- OTHER: Miscellaneous history records

Activity Tracking:
- Action and summary tracking
- Detailed description storage
- Activity type categorization
- Status tracking for workflow management
- Date and time tracking for all activities

User Tracking:
- Created by user identification
- Updated by user tracking
- User relationship management
- Audit trail for accountability

Integration Features:
- Salesforce ID mapping for synchronization
- Email message ID tracking
- Event relationship for activity context
- Volunteer relationship for activity association

Data Management:
- Soft deletion for data preservation
- JSON metadata for flexible data storage
- Validation for data integrity
- Indexed fields for performance

Usage Examples:
    # Create a new history record
    history = History(
        volunteer_id=volunteer.id,
        action="volunteer_created",
        summary="New volunteer registration",
        description="Volunteer completed registration process",
        history_type="activity",
        created_by_id=user.id
    )

    # Soft delete a record
    history.soft_delete(user_id=admin_user.id)

    # Check if record is recent
    if history.is_recent:
        print("This is a recent activity")

    # Convert to dictionary for API
    history_dict = history.to_dict()
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import validates

from models import db


class HistoryType(Enum):
    """
    Enum for categorizing different types of history records.

    Provides standardized categories for organizing and filtering
    history records based on their purpose and content.

    Categories:
        - NOTE: General notes and comments about volunteers
        - ACTIVITY: Volunteer activities and engagements
        - STATUS_CHANGE: Changes to volunteer status or information
        - ENGAGEMENT: Specific engagement activities and interactions
        - SYSTEM: System-generated records and automated actions
        - OTHER: Miscellaneous history records that don't fit other categories
    """

    NOTE = "note"
    ACTIVITY = "activity"
    STATUS_CHANGE = "status_change"
    ENGAGEMENT = "engagement"
    SYSTEM = "system"
    OTHER = "other"


class History(db.Model):
    """
    History model for tracking volunteer activities and notes.

    This model maintains an audit trail of volunteer interactions, status changes,
    and administrative notes. Each record is timestamped and can be soft-deleted.

    Database Table:
        history - Stores all volunteer activity and note records

    Key Features:
        - Comprehensive audit trail for volunteer activities
        - Soft deletion support for data preservation
        - Automatic timestamping and user tracking
        - Activity categorization and status tracking
        - Salesforce integration for data synchronization
        - Email integration for communication tracking
        - JSON metadata storage for flexible data
        - Recent activity detection

    Relationships:
        - Many-to-one with Volunteer model
        - Many-to-one with Event model (optional)
        - Many-to-one with User model (created_by, updated_by)

    Activity Tracking:
        - action: Type of action performed (e.g., "created", "updated")
        - summary: Brief overview of the activity
        - description: Detailed description of the activity
        - activity_type: Categorization of activity
        - activity_date: When the activity occurred
        - activity_status: Current status of the activity

    User Tracking:
        - created_by_id: User who created the record
        - updated_by_id: User who last updated the record
        - Automatic timestamp tracking for all changes

    Integration Features:
        - salesforce_id: Salesforce record synchronization
        - email_message_id: Email communication tracking
        - additional_metadata: JSON field for flexible data storage

    Data Management:
        - Soft deletion with is_deleted flag
        - Validation for data integrity
        - Indexed fields for performance optimization
        - Composite indexes for common queries

    Performance Optimizations:
        - Lazy loading for related records
        - Cascade delete for proper cleanup
        - Indexed foreign keys for fast joins
        - Composite indexes for common query patterns
    """

    __tablename__ = "history"

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys - Define relationships with other models
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"))
    # Contact ID - can be volunteer, teacher, or other contact types
    contact_id = db.Column(
        db.Integer, db.ForeignKey("contact.id"), nullable=False, index=True
    )

    # Core Activity Fields
    action = db.Column(
        db.String(255)
    )  # Type of action performed (e.g., "created", "updated")
    summary = db.Column(
        db.Text
    )  # Brief overview of the activity (mapped from "Subject")
    description = db.Column(db.Text)  # Detailed description of the activity

    # Activity Metadata
    activity_type = db.Column(db.String(100), index=True)  # Categorization of activity
    activity_date = db.Column(db.DateTime, nullable=False, index=True)
    activity_status = db.Column(
        db.String(50), index=True
    )  # Current status of the activity

    # Automatic timestamps for audit trail (timezone-aware, Python-side defaults)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    # Note: updated_at column removed to match current database schema

    # Status and Integration Fields
    is_deleted = db.Column(db.Boolean, default=False, index=True)  # Soft delete flag
    email_message_id = db.Column(db.String(255), nullable=True)  # For email integration
    salesforce_id = db.Column(
        db.String(18), unique=True, nullable=True
    )  # For Salesforce integration

    # New columns for enhanced tracking
    history_type = db.Column(db.String(50), nullable=False, default="note", index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    additional_metadata = db.Column(
        db.JSON, nullable=True
    )  # For storing additional structured data

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Relationship Definitions
    # cascade='all, delete-orphan' ensures proper cleanup of related records
    event = db.relationship(
        "Event",
        backref=db.backref(
            "histories",
            lazy="dynamic",  # Lazy loading for better performance
            cascade="all, delete-orphan",  # Automatically handle related records
        ),
        post_update=True,  # Avoid circular dependency issues
        foreign_keys=[event_id],  # Explicitly specify foreign key
    )

    contact = db.relationship(
        "Contact",
        backref=db.backref("histories", lazy="dynamic", cascade="all, delete-orphan"),
        passive_deletes=True,  # Works with ondelete="CASCADE" for better performance
    )

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])

    __table_args__ = (
        # Composite index for common queries
        db.Index(
            "idx_contact_activity_date", "contact_id", "activity_date", "is_deleted"
        ),
    )

    def __init__(self, **kwargs):
        """
        Initialize history record with validation.

        Automatically sets activity_date to current time if not provided.

        Args:
            **kwargs: History record attributes
        """
        if "activity_date" not in kwargs:
            kwargs["activity_date"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)

    @validates("notes")
    def validate_notes(self, key, value):
        """
        Ensure notes field is not empty when provided.

        Args:
            key: Field name being validated
            value: Value to validate

        Returns:
            Validated value

        Raises:
            ValueError: If notes is provided but empty
        """
        if value is not None and not value.strip():
            raise ValueError("Notes cannot be empty if provided")
        return value

    def soft_delete(self, user_id=None):
        """
        Soft delete the history record.

        Marks the record as deleted without actually removing it from the database.
        Updates the updated_by_id.

        Args:
            user_id: ID of user performing the deletion

        Returns:
            self: For method chaining
        """
        self.is_deleted = True
        self.updated_by_id = user_id
        return self

    def restore(self, user_id=None):
        """
        Restore a soft-deleted history record.

        Unmarks the record as deleted and updates the updated_by_id.

        Args:
            user_id: ID of user performing the restoration

        Returns:
            self: For method chaining
        """
        self.is_deleted = False
        self.updated_by_id = user_id
        return self

    @property
    def volunteer_id(self):
        """
        Backward compatibility property for volunteer_id.
        Returns contact_id if the contact is a volunteer, None otherwise.
        """
        if hasattr(self.contact, "type") and self.contact.type == "volunteer":
            return self.contact.id
        return None

    @property
    def teacher_id(self):
        """
        Returns contact_id if the contact is a teacher, None otherwise.
        """
        if hasattr(self.contact, "type") and self.contact.type == "teacher":
            return self.contact.id
        return None

    @property
    def contact_type(self):
        """
        Returns the type of contact (volunteer, teacher, etc.)
        """
        return getattr(self.contact, "type", None) if self.contact else None

    @property
    def is_recent(self):
        """
        Check if history record is from the last 30 days.

        Returns:
            bool: True if activity occurred within last 30 days
        """
        if not self.activity_date:
            return False
        return (datetime.now(timezone.utc) - self.activity_date).days <= 30

    def to_dict(self):
        """
        Convert history record to dictionary for API responses.

        Returns:
            dict: Dictionary representation of the history record
        """
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "volunteer_id": self.volunteer_id,  # Backward compatibility
            "teacher_id": self.teacher_id,  # New field
            "contact_type": self.contact_type,  # New field
            "activity_date": (
                self.activity_date.isoformat() if self.activity_date else None
            ),
            "notes": self.notes,
            "history_type": self.history_type,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": None,  # Column removed from database schema
            "created_by": (
                self.created_by.username
                if self.created_by and self.created_by.username
                else None
            ),
            "metadata": self.additional_metadata,
        }

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing id, type, and date
        """
        return f"<History {self.id}: {self.history_type} on {self.activity_date}>"

    # Add a property to handle Enum conversion
    @property
    def history_type_enum(self):
        """
        Get the HistoryType enum value.

        Returns:
            HistoryType: Enum value corresponding to history_type field
        """
        try:
            return HistoryType(self.history_type)
        except ValueError:
            return HistoryType.OTHER

    @history_type_enum.setter
    def history_type_enum(self, value):
        """
        Set history_type from enum value.

        Args:
            value: HistoryType enum or string value
        """
        if isinstance(value, HistoryType):
            self.history_type = value.value.lower()
        elif isinstance(value, str):
            self.history_type = value.lower()
