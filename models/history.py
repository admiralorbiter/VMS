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
- Contact relationship for activity association (volunteers, teachers, etc.)

Data Management:
- Soft deletion for data preservation
- JSON metadata for flexible data storage
- Validation for data integrity
- Indexed fields for performance

Usage Examples:
    # Create a new history record
    history = History(
        contact_id=volunteer.id,
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

    # Use enum for type validation
    history.history_type_enum = HistoryType.ACTIVITY
"""

import warnings
from datetime import datetime, timezone

from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from models import db
from models.contact import FormEnum
from models.utils import get_utc_now, validate_salesforce_id


class HistoryType(FormEnum):
    """
    Enum for categorizing different types of history records.

    Provides standardized categories for organizing and filtering
    history records based on their purpose and content. Inherits from
    FormEnum to provide form integration methods (choices(), choices_required()).

    Categories:
        - NOTE: General notes and comments about contacts
        - ACTIVITY: Contact activities and engagements
        - STATUS_CHANGE: Changes to contact status or information
        - ENGAGEMENT: Specific engagement activities and interactions
        - SYSTEM: System-generated records and automated actions
        - OTHER: Miscellaneous history records that don't fit other categories

    Usage Examples:
        # Use in forms
        history_type_field = SelectField(
            "History Type",
            choices=HistoryType.choices(),
            validators=[Optional()]
        )

        # Validate history type
        history.history_type_enum = HistoryType.ACTIVITY
        assert history.history_type == "activity"

        # Check enum value
        if history.history_type_enum == HistoryType.NOTE:
            print("This is a note")
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
        - Many-to-one with Contact model (volunteers, teachers, etc.)
        - Many-to-one with Event model (optional)
        - Many-to-one with User model (created_by, updated_by)
        - Cascade delete configured for contact relationship

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

    # Automatic timestamps for audit trail (timezone-aware, database-side defaults)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
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
    # Note: Cascade delete configured for proper cleanup of related records
    event = db.relationship(
        "Event",
        backref=db.backref(
            "histories",
            lazy="dynamic",  # Lazy loading for better performance
            cascade="all, delete-orphan",  # Automatically delete histories when event is deleted
        ),
        post_update=True,  # Avoid circular dependency issues
        foreign_keys=[event_id],  # Explicitly specify foreign key
    )

    contact = db.relationship(
        "Contact",
        backref=db.backref(
            "histories",
            lazy="dynamic",
            cascade="all, delete-orphan",  # Automatically delete histories when contact is deleted
        ),
        passive_deletes=True,  # Works with ondelete="CASCADE" for better performance
    )

    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_id],
        backref=db.backref("created_histories", lazy="dynamic"),
    )
    updated_by = db.relationship(
        "User",
        foreign_keys=[updated_by_id],
        backref=db.backref("updated_histories", lazy="dynamic"),
    )

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

    @validates("history_type")
    def validate_history_type(self, key, value):
        """
        Validates history_type to ensure it's a valid HistoryType enum value.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible. Uses value-based
        lookup for better compatibility. Invalid values fall back to HistoryType.OTHER
        per existing test expectations.

        Args:
            key (str): The name of the field being validated
            value: The history_type value to validate

        Returns:
            str: Validated history_type string value (lowercase)

        Example:
            >>> history.validate_history_type("history_type", "activity")
            'activity'

            >>> history.validate_history_type("history_type", HistoryType.ACTIVITY)
            'activity'

            >>> history.validate_history_type("history_type", "NOTE")
            'note'

            >>> history.validate_history_type("history_type", "invalid")
            'other'  # Falls back to OTHER for invalid values
        """
        if value is None:
            return HistoryType.NOTE.value  # Default to NOTE

        # If it's already an enum instance, return its value
        if isinstance(value, HistoryType):
            return value.value.lower()

        # Handle string input - try value-based lookup first (case-insensitive)
        if isinstance(value, str):
            value_lower = value.lower().strip()
            for enum_member in HistoryType:
                if enum_member.value.lower() == value_lower:
                    return enum_member.value.lower()
            # Try name-based lookup for backwards compatibility
            try:
                enum_member = HistoryType[value.upper().replace(" ", "_")]
                return enum_member.value.lower()
            except KeyError:
                # Invalid value - fall back to OTHER per test expectations
                warnings.warn(
                    f"Invalid history_type value: {value}. Using HistoryType.OTHER.",
                    UserWarning,
                )
                return HistoryType.OTHER.value

        # For other types, warn and use default
        warnings.warn(
            f"Invalid history_type type: {type(value).__name__}. Using HistoryType.NOTE.",
            UserWarning,
        )
        return HistoryType.NOTE.value

    @validates("salesforce_id")
    def validate_salesforce_id_field(self, key, value):
        """
        Validates Salesforce ID format using shared validator.

        Args:
            key (str): The name of the field being validated
            value: Salesforce ID to validate

        Returns:
            str: Validated Salesforce ID or None

        Raises:
            ValueError: If Salesforce ID format is invalid

        Example:
            >>> history.validate_salesforce_id_field("salesforce_id", "0011234567890ABCD")
            '0011234567890ABCD'
        """
        return validate_salesforce_id(value)

    @validates("activity_date")
    def validate_activity_date(self, key, value):
        """
        Validates and converts activity_date field to proper datetime object with timezone awareness.

        This validator ensures that activity_date fields are properly formatted and converted
        from various input formats (strings, datetime objects) to consistent timezone-aware
        datetime objects. Invalid dates result in warnings and return None rather than raising
        exceptions, allowing the save operation to continue with null values.

        Note: The database column is currently not timezone-aware (db.DateTime), but this
        validator ensures all datetime objects are timezone-aware in Python. A migration will
        be needed to make the database column timezone-aware (db.DateTime(timezone=True)).

        Args:
            key (str): The name of the field being validated (activity_date)
            value: The datetime value to validate (can be string, datetime, or None)

        Returns:
            datetime: Converted timezone-aware datetime object or None if invalid

        Raises:
            ValueError: If date string cannot be parsed in strict mode

        Example:
            >>> history.validate_activity_date("activity_date", "2024-01-15 10:00:00")
            datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

            >>> history.validate_activity_date("activity_date", "invalid")
            None  # Returns None and logs warning
        """
        if not value:  # Handle empty strings and None
            return None

        # If it's already a datetime, ensure timezone awareness
        if isinstance(value, datetime):
            if value.tzinfo is None:
                # Assume UTC if timezone-naive
                warnings.warn(
                    f"Timezone-naive datetime provided for {key}. Assuming UTC.",
                    UserWarning,
                )
                return value.replace(tzinfo=timezone.utc)
            return value

        # Handle string input - try common formats
        if isinstance(value, str):
            # Try ISO format first (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            date_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y",
            ]

            for fmt in date_formats:
                try:
                    parsed = datetime.strptime(value, fmt)
                    # If parsed datetime is naive, make it timezone-aware (UTC)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
                except ValueError:
                    continue

            # If no format worked, log warning and return None
            warnings.warn(
                f"Invalid date format for {key}: {value}. "
                f"Expected formats: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS",
                UserWarning,
            )
            return None

        # For other types, log warning
        warnings.warn(
            f"Invalid type for {key}: {type(value).__name__}. Expected datetime or string.",
            UserWarning,
        )
        return None

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

        **READ-ONLY PROPERTY** - This property is provided for backward compatibility
        only. Use `contact_id` for new code.

        **IMPORTANT**: This property CANNOT be used in SQLAlchemy queries. It is a
        Python property that accesses the relationship, not a database column. To query
        by volunteer, use:
        ```python
        History.query.join(Contact).filter(Contact.type == 'volunteer', History.contact_id.in_(volunteer_ids))
        ```

        Returns:
            int or None: contact_id if the contact is a volunteer, None otherwise

        Example:
            >>> history.volunteer_id
            123  # If contact is a volunteer
            >>> history.volunteer_id
            None  # If contact is not a volunteer

        Note:
            This property is deprecated in favor of using contact_id directly.
            It will be removed in a future version.
        """
        if hasattr(self.contact, "type") and self.contact.type == "volunteer":
            return self.contact.id
        return None

    @property
    def teacher_id(self):
        """
        Backward compatibility property for teacher_id.

        **READ-ONLY PROPERTY** - This property is provided for backward compatibility
        only. Use `contact_id` for new code.

        **IMPORTANT**: This property CANNOT be used in SQLAlchemy queries. It is a
        Python property that accesses the relationship, not a database column. To query
        by teacher, use:
        ```python
        History.query.join(Contact).filter(Contact.type == 'teacher', History.contact_id.in_(teacher_ids))
        ```

        Returns:
            int or None: contact_id if the contact is a teacher, None otherwise

        Example:
            >>> history.teacher_id
            456  # If contact is a teacher
            >>> history.teacher_id
            None  # If contact is not a teacher

        Note:
            This property is deprecated in favor of using contact_id directly.
            It will be removed in a future version.
        """
        if hasattr(self.contact, "type") and self.contact.type == "teacher":
            return self.contact.id
        return None

    @property
    def contact_type(self):
        """
        Returns the type of contact associated with this history record.

        This property provides access to the contact type (volunteer, teacher, etc.)
        through the Contact relationship. Useful for filtering and displaying history
        records by contact type.

        Returns:
            str or None: The type of contact (e.g., "volunteer", "teacher") or None
                         if contact is not loaded or type is not set

        Example:
            >>> history.contact_type
            'volunteer'
            >>> history.contact_type
            'teacher'
            >>> history.contact_type
            None  # If contact is not loaded or type is not set

        Usage:
            # Filter history by contact type
            if history.contact_type == "volunteer":
                # Handle volunteer-specific logic
                pass
        """
        return getattr(self.contact, "type", None) if self.contact else None

    @property
    def is_recent(self):
        """
        Check if history record is from the last 30 days.

        This property determines if the activity_date is within the last 30 days
        from the current UTC time. Useful for filtering recent activities and
        highlighting current engagement.

        Returns:
            bool: True if activity occurred within last 30 days, False otherwise

        Example:
            >>> # Recent activity (today)
            >>> history.activity_date = datetime.now(timezone.utc)
            >>> history.is_recent
            True

            >>> # Old activity (35 days ago)
            >>> from datetime import timedelta
            >>> history.activity_date = datetime.now(timezone.utc) - timedelta(days=35)
            >>> history.is_recent
            False

        Note:
            Returns False if activity_date is None or not set.
        """
        if not self.activity_date:
            return False
        return (datetime.now(timezone.utc) - self.activity_date).days <= 30

    def to_dict(self):
        """
        Convert history record to dictionary for API responses.

        Returns a comprehensive dictionary representation of the history record
        including all fields. This method is useful for JSON serialization and
        API responses.

        Returns:
            dict: Dictionary representation of the history record with all fields

        Example:
            >>> history = History(
            ...     contact_id=123,
            ...     action="volunteer_created",
            ...     summary="New registration",
            ...     description="Volunteer completed registration",
            ...     activity_type="Registration",
            ...     activity_status="Completed",
            ...     history_type="activity"
            ... )
            >>> history_dict = history.to_dict()
            >>> history_dict["action"]
            'volunteer_created'
            >>> history_dict["contact_type"]
            'volunteer'
        """
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "volunteer_id": self.volunteer_id,  # Backward compatibility
            "teacher_id": self.teacher_id,  # Backward compatibility
            "contact_type": self.contact_type,
            "event_id": self.event_id,
            "action": self.action,
            "summary": self.summary,
            "description": self.description,
            "activity_type": self.activity_type,
            "activity_date": (
                self.activity_date.isoformat() if self.activity_date else None
            ),
            "activity_status": self.activity_status,
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
            "email_message_id": self.email_message_id,
            "salesforce_id": self.salesforce_id,
            "metadata": self.additional_metadata,
        }

    def __repr__(self):
        """
        String representation for debugging.

        Returns:
            str: Debug representation showing id, type, and date
        """
        return f"<History {self.id}: {self.history_type} on {self.activity_date}>"

    @property
    def history_type_enum(self):
        """
        Get the HistoryType enum value from the history_type string field.

        This property provides convenient access to the enum representation of
        the history_type field. Invalid values automatically fall back to
        HistoryType.OTHER per existing test expectations.

        Returns:
            HistoryType: Enum value corresponding to history_type field

        Example:
            >>> history.history_type = "activity"
            >>> history.history_type_enum
            HistoryType.ACTIVITY

            >>> history.history_type = "invalid"
            >>> history.history_type_enum
            HistoryType.OTHER  # Falls back to OTHER for invalid values

            >>> # Use enum for comparisons
            >>> if history.history_type_enum == HistoryType.NOTE:
            ...     print("This is a note")
        """
        try:
            return HistoryType(self.history_type)
        except ValueError:
            return HistoryType.OTHER

    @history_type_enum.setter
    def history_type_enum(self, value):
        """
        Set history_type from enum value or string.

        This setter accepts both HistoryType enum instances and string values,
        converting them appropriately. The validator ensures the value is valid
        and falls back to OTHER for invalid values.

        Args:
            value: HistoryType enum or string value (case-insensitive)

        Example:
            >>> # Set using enum
            >>> history.history_type_enum = HistoryType.ACTIVITY
            >>> history.history_type
            'activity'

            >>> # Set using string
            >>> history.history_type_enum = "note"
            >>> history.history_type
            'note'

            >>> # Case-insensitive string handling
            >>> history.history_type_enum = "ACTIVITY"
            >>> history.history_type
            'activity'
        """
        if isinstance(value, HistoryType):
            self.history_type = value.value.lower()
        elif isinstance(value, str):
            self.history_type = value.lower()
