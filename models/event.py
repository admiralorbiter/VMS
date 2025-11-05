"""
Event Model and Related Classes
==============================

This module defines the Event model and related classes for managing events in the VMS system.
Events represent various types of activities, sessions, and programs that can involve
volunteers, students, teachers, and other participants.

Key Features:
- Comprehensive event management with multiple types and formats
- Salesforce integration for data synchronization
- Attendance tracking and participation management
- Skills and requirements association
- District and school relationships
- Teacher and student participation tracking
- Validation and business logic methods
- Capacity management and registration tracking
- Status workflow management
- Comment and note system

Database Tables:
- event: Main events table with comprehensive event data
- event_volunteers: Association table for event-volunteer relationships
- event_districts: Association table for event-district relationships
- event_skills: Association table for event-skill relationships
- event_teacher: Association table for event-teacher relationships with attendance
- event_student_participation: Student participation tracking
- event_comment: Event comments and notes
- event_attendance: Event attendance tracking

Event Types:
- IN_PERSON: Traditional face-to-face events
- VIRTUAL_SESSION: Online events and webinars
- CONNECTOR_SESSION: Specialized connector program events
- CAREER_FAIR: Career exploration events
- CLASSROOM_SPEAKER: Classroom presentations
- MENTORING: One-on-one mentoring sessions
- INTERNSHIP: Internship programs
- And many more specialized event types

Event Formats:
- IN_PERSON: Physical location events
- VIRTUAL: Online or remote events

Event Statuses:
- DRAFT: Initial planning stage
- REQUESTED: Event has been requested
- CONFIRMED: Event is confirmed and ready
- PUBLISHED: Event is publicly available
- COMPLETED: Event has finished
- CANCELLED: Event was cancelled
- NO_SHOW: Event had no participants
- SIMULCAST: Multi-location event
- COUNT: Administrative counting event

Key Relationships:
- Many-to-many with volunteers, districts, and skills
- One-to-many with teachers, students, and comments
- One-to-one with attendance tracking
- Foreign key relationships with schools

Data Validation:
- Date consistency validation
- Capacity and attendance validation
- Status transition validation
- Title and description validation
- Count validation for participants

Salesforce Integration:
- Salesforce ID mapping for synchronization
- Status mapping from Salesforce values
- Participant data synchronization
- Session tracking and management

Usage Examples:
    # Create a new event
    event = Event(
        title="Career Fair 2024",
        type=EventType.CAREER_FAIR,
        format=EventFormat.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    db.session.add(event)
    db.session.commit()

    # Add volunteers to event
    event.volunteers.append(volunteer)

    # Add skills to event
    event.skills.append(skill)

    # Check event capacity
    if event.is_at_capacity:
        print("Event is full")

    # Validate event data
    event.validate_dates()
    event.validate_counts()

    # Update from external data
    event.update_from_csv(csv_data)
"""

import warnings
from datetime import datetime, timezone
from enum import Enum

import pytz
from flask import current_app
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import String
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from models import db
from models.attendance import EventAttendanceDetail
from models.utils import validate_salesforce_id
from models.volunteer import EventParticipation

# Define the association table first
event_volunteers = db.Table(
    "event_volunteers",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column(
        "volunteer_id", db.Integer, db.ForeignKey("volunteer.id"), primary_key=True
    ),
)

# Add this association table for event-district relationship
event_districts = db.Table(
    "event_districts",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column(
        "district_id", db.Integer, db.ForeignKey("district.id"), primary_key=True
    ),
)

# Add this near the top with other association tables
event_skills = db.Table(
    "event_skills",
    db.Column("event_id", db.Integer, db.ForeignKey("event.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)


class EventType(str, Enum):
    """
    Event Type Enumeration

    Defines all possible types of events in the system. Each type represents
    a different category of educational or career development activity.

    The enum values are used for filtering, reporting, and organizing events
    by their primary purpose or format.

    Event Categories:
        - Career Development: CAREER_FAIR, CAREER_SPEAKER, CAREER_JUMPING
        - Educational: CLASSROOM_SPEAKER, CLASSROOM_ACTIVITY, MATH_RELAYS
        - Virtual Programs: VIRTUAL_SESSION, CONNECTOR_SESSION
        - College Preparation: COLLEGE_OPTIONS, COLLEGE_APPLICATION_FAIR, FAFSA
        - Workplace Exposure: WORKPLACE_VISIT, INTERNSHIP
        - Campus Visits: CAMPUS_VISIT, PATHWAY_CAMPUS_VISITS
        - Mentoring: MENTORING, ADVISORY_SESSIONS
        - Financial Education: FINANCIAL_LITERACY
        - Special Programs: IGNITE, DIA, P2GD, SLA, HEALTHSTART, P2T, BFI
        - Volunteer Management: VOLUNTEER_ORIENTATION, VOLUNTEER_ENGAGEMENT
        - Historical: HISTORICAL, DATA_VIZ
    """

    IN_PERSON = "in_person"
    VIRTUAL_SESSION = "virtual_session"
    CONNECTOR_SESSION = "connector_session"
    CAREER_JUMPING = "career_jumping"
    CAREER_SPEAKER = "career_speaker"
    EMPLOYABILITY_SKILLS = "employability_skills"
    IGNITE = "ignite"
    CAREER_FAIR = "career_fair"
    CLIENT_CONNECTED_PROJECT = "client_connected_project"
    PATHWAY_CAMPUS_VISITS = "pathway_campus_visits"
    WORKPLACE_VISIT = "workplace_visit"
    PATHWAY_WORKPLACE_VISITS = "pathway_workplace_visits"
    COLLEGE_OPTIONS = "college_options"
    DIA_CLASSROOM_SPEAKER = "dia_classroom_speaker"
    DIA = "dia"
    CAMPUS_VISIT = "campus_visit"
    ADVISORY_SESSIONS = "advisory_sessions"
    VOLUNTEER_ORIENTATION = "volunteer_orientation"
    VOLUNTEER_ENGAGEMENT = "volunteer_engagement"
    MENTORING = "mentoring"
    FINANCIAL_LITERACY = "financial_literacy"
    MATH_RELAYS = "math_relays"
    CLASSROOM_SPEAKER = "classroom_speaker"
    INTERNSHIP = "internship"
    COLLEGE_APPLICATION_FAIR = "college_application_fair"
    FAFSA = "fafsa"
    CLASSROOM_ACTIVITY = "classroom_activity"
    HISTORICAL = "historical"
    DATA_VIZ = "data_viz"
    P2GD = "p2gd"
    SLA = "sla"
    HEALTHSTART = "healthstart"
    P2T = "p2t"
    BFI = "bfi"


class CancellationReason(str, Enum):
    """
    Cancellation Reason Enumeration

    Defines the possible reasons why an event might be cancelled.
    Used for tracking and reporting on event cancellations.

    Reasons:
        - WEATHER: Weather-related cancellations
        - LOW_ENROLLMENT: Insufficient participant registration
        - INSTRUCTOR_UNAVAILABLE: Instructor unable to attend
        - FACILITY_ISSUE: Problems with the event location
        - OTHER: Miscellaneous cancellation reasons
    """

    WEATHER = "weather"
    LOW_ENROLLMENT = "low_enrollment"
    INSTRUCTOR_UNAVAILABLE = "instructor_unavailable"
    FACILITY_ISSUE = "facility_issue"
    OTHER = "other"


class EventComment(db.Model):
    """
    Event Comment Model

    Allows users to add comments and notes to events for internal
    communication and tracking purposes.

    Database Table:
        event_comment - Stores event comments and notes

    Features:
        - Rich text content support
        - Automatic timestamp tracking
        - Cascade deletion with events
        - User-friendly comment management
    """

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


class AttendanceStatus(str, Enum):
    """
    Attendance Status Enumeration

    Tracks the status of attendance taking for events.

    Statuses:
        - NOT_TAKEN: Attendance has not been recorded yet
        - IN_PROGRESS: Attendance is currently being taken
        - COMPLETED: Attendance has been fully recorded
    """

    NOT_TAKEN = "not_taken"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class EventAttendance(db.Model):
    """
    Event Attendance Model

    Tracks attendance information for events, including status,
    counts, and timestamps.

    Database Table:
        event_attendance - Stores attendance tracking data

    Features:
        - Status tracking for attendance process
        - Total attendance counting
        - Timestamp tracking for audit trails
        - One-to-one relationship with events
    """

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)

    # Attendance details
    status = db.Column(
        SQLAlchemyEnum(AttendanceStatus),
        default=AttendanceStatus.NOT_TAKEN,
        nullable=False,
    )
    last_taken = db.Column(db.DateTime(timezone=True), nullable=True)
    total_attendance = db.Column(db.Integer, default=0)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # Change the relationship definition to prevent circular updates
    event = db.relationship(
        "Event",
        backref=db.backref("attendance", uselist=False, cascade="all, delete-orphan"),
        single_parent=True,
    )


class EventFormat(str, Enum):
    """
    Event Format Enumeration

    Defines the format or delivery method of events.

    Formats:
        - IN_PERSON: Traditional face-to-face events
        - VIRTUAL: Online or remote events
    """

    IN_PERSON = "in_person"
    VIRTUAL = "virtual"


class EventStatus(str, Enum):
    """
    Event Status Enumeration

    Defines the current status of events. Used for filtering,
    reporting, and workflow management.

    The map_status class method provides mapping from various
    Salesforce status values to standardized enum values.

    Status Workflow:
        DRAFT -> REQUESTED -> CONFIRMED -> PUBLISHED -> COMPLETED
        Any status can transition to CANCELLED
        NO_SHOW and SIMULCAST are special administrative statuses
    """

    COMPLETED = "Completed"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    REQUESTED = "Requested"
    DRAFT = "Draft"
    PUBLISHED = "Published"
    NO_SHOW = "No Show"
    SIMULCAST = "Simulcast"
    COUNT = "Count"

    @classmethod
    def map_status(cls, status_str):
        """
        Maps various status strings to standardized enum values.

        This method handles the conversion from Salesforce status values
        and other external status formats to our internal enum values.

        Args:
            status_str (str): Raw status string from external source

        Returns:
            EventStatus: Mapped enum value, defaults to DRAFT if unknown
        """
        if not status_str:
            return cls.DRAFT

        status_str = status_str.lower().strip()
        status_mapping = {
            "teacher no-show": cls.NO_SHOW,
            "teacher cancelation": cls.CANCELLED,
            "simulcast": cls.SIMULCAST,
            "successfully completed": cls.COMPLETED,
            "completed": cls.COMPLETED,
            "confirmed": cls.CONFIRMED,
            "cancelled": cls.CANCELLED,
            "canceled": cls.CANCELLED,
            "published": cls.PUBLISHED,
            "requested": cls.REQUESTED,
            "draft": cls.DRAFT,
            "count": cls.COUNT,
            "technical difficulties": cls.NO_SHOW,
            "local professional no-show": cls.NO_SHOW,
            "pathful professional no-show": cls.NO_SHOW,
            # Additional mappings for virtual sessions
            "teacher requested": cls.REQUESTED,
            "industry chat": cls.CONFIRMED,
        }

        return status_mapping.get(status_str, cls.DRAFT)


class Event(db.Model):
    """
    Event Model

    Represents an event in the system. Events can be various types (in-person, virtual, etc.)
    and can have multiple participants (volunteers, educators) associated with them.

    Important Implementation Notes:
    - Use validate_dates() before saving to ensure date consistency
    - Check validate_counts() when updating attendance numbers
    - Consider using the merge_duplicate() method when handling duplicate events

    Database Optimization:
    - Indexes are created on frequently queried fields (start_date, school, status)
    - Composite index on (status, start_date) for common event listing queries
    """

    # Primary identifiers
    id = db.Column(db.Integer, primary_key=True)
    # Index salesforce_id since it's used for lookups and is unique
    salesforce_id = db.Column(String(18), unique=True, nullable=True, index=True)

    # Basic event information - frequently searched fields should be indexed
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    # Add index for type since it's commonly used in filters
    type = db.Column(SQLAlchemyEnum(EventType), default=EventType.IN_PERSON, index=True)
    format = db.Column(
        SQLAlchemyEnum(EventFormat), nullable=False, default=EventFormat.IN_PERSON
    )

    # Create a composite index for common queries that filter by both status and date
    __table_args__ = (
        db.Index("idx_event_status_date", "status", "start_date"),
        # Add index for district partner lookups
        db.Index("idx_district_partner", "district_partner"),
        # Add new composite index for district year-end report queries
        db.Index("idx_event_status_date_type", "status", "start_date", "type"),
        # Improve calendar queries filtered by school and start date
        db.Index("idx_event_school_start", "school", "start_date"),
        # Non-negative checks for counters and duration
        db.CheckConstraint(
            "duration IS NULL OR duration >= 0", name="ck_event_duration_nonneg"
        ),
        db.CheckConstraint(
            "participant_count >= 0", name="ck_event_participant_nonneg"
        ),
        db.CheckConstraint("registered_count >= 0", name="ck_event_registered_nonneg"),
        db.CheckConstraint("attended_count >= 0", name="ck_event_attended_nonneg"),
        db.CheckConstraint("available_slots >= 0", name="ck_event_available_nonneg"),
        db.CheckConstraint(
            "scheduled_participants_count >= 0", name="ck_event_scheduled_nonneg"
        ),
        db.CheckConstraint(
            "total_requested_volunteer_jobs >= 0", name="ck_event_total_jobs_nonneg"
        ),
    )

    # Event timing - Consider adding validation to ensure end_date > start_date
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date = db.Column(db.DateTime(timezone=True), nullable=True)
    duration = db.Column(
        db.Integer
    )  # Consider adding a check constraint for positive values

    # Status tracking
    status = db.Column(
        SQLAlchemyEnum(EventStatus),
        nullable=False,
        default=EventStatus.DRAFT,
        index=True,
    )
    cancellation_reason = db.Column(SQLAlchemyEnum(CancellationReason), nullable=True)

    # Location and organizational details
    location = db.Column(db.String(255))
    school = db.Column(db.String(18), db.ForeignKey("school.id"), index=True)
    district_partner = db.Column(db.String(255), index=True)

    # Participant tracking
    volunteers_needed = db.Column(
        db.Integer
    )  # Consider adding check constraint for non-negative
    participant_count = db.Column(db.Integer, default=0)
    registered_count = db.Column(db.Integer, default=0, index=True)
    attended_count = db.Column(db.Integer, default=0)
    available_slots = db.Column(db.Integer, default=0)
    scheduled_participants_count = db.Column(db.Integer, default=0)
    total_requested_volunteer_jobs = db.Column(db.Integer, default=0)

    # Additional metadata
    additional_information = db.Column(db.Text)
    session_id = db.Column(db.String(255))
    session_host = db.Column(
        db.String(255), default="PREPKC"
    )  # Store Session_Host__c from Salesforce
    series = db.Column(db.String(255))
    registration_link = db.Column(db.String(1300))
    original_status_string = db.Column(
        db.String(255)
    )  # Store original status string for detailed analysis

    # Participant details - Consider moving to separate tables for better normalization
    educators = db.Column(
        db.Text
    )  # Semicolon-separated list - candidate for normalization
    educator_ids = db.Column(
        db.Text
    )  # Semicolon-separated list - candidate for normalization
    professionals = db.Column(db.Text)  # Consider normalizing this data
    professional_ids = db.Column(db.Text)  # Consider normalizing this data

    # Timestamps for auditing (timezone-aware, database-side defaults)
    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    volunteers = db.relationship(
        "Volunteer",
        secondary=event_volunteers,
        backref=db.backref("events", lazy="dynamic"),
    )

    comments = db.relationship(
        "EventComment",
        backref="event",
        lazy="dynamic",
        cascade="all, delete-orphan",  # Comments are deleted when event is deleted
    )

    districts = db.relationship(
        "District",
        secondary=event_districts,
        backref=db.backref("events", lazy="dynamic"),
    )

    skills = db.relationship(
        "Skill", secondary=event_skills, backref=db.backref("events", lazy="dynamic")
    )

    # Enhanced teacher tracking
    teacher_registrations = db.relationship(
        "EventTeacher", back_populates="event", cascade="all, delete-orphan"
    )

    teachers = db.relationship(
        "Teacher",
        secondary="event_teacher",
        back_populates="events",
        viewonly=True,  # Use teacher_registrations for modifications
    )

    # Add this to your Event class relationships section
    school_obj = db.relationship(
        "School", foreign_keys=[school], backref=db.backref("events", lazy="dynamic")
    )

    # Add one-to-one relationship to EventAttendanceDetail
    attendance_detail = db.relationship(
        "EventAttendanceDetail",
        back_populates="event",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Note: Validation is handled automatically via @validates decorators:
    # - Date validation: @validates("start_date", "end_date") with timezone handling
    # - Count validation: @validates for all count fields with normalization
    # - Status transitions: validate_status_transition() called automatically

    __mapper_args__ = {"confirm_deleted_rows": False}

    def __repr__(self):
        """Add a string representation for debugging"""
        return f"<Event {self.id}: {self.title}>"

    @property
    def volunteer_count(self):
        """Get current volunteer count"""
        # Count via association table to avoid loading entire collection
        return (
            db.session.query(event_volunteers)
            .filter(event_volunteers.c.event_id == self.id)
            .count()
        )

    @property
    def attendance_status(self):
        """Helper property to easily check attendance status"""
        if not self.attendance:
            return AttendanceStatus.NOT_TAKEN
        return self.attendance.status

    @property
    def attendance_count(self):
        """Helper property to easily get attendance count"""
        if not self.attendance:
            return 0
        return self.attendance.total_attendance

    @property
    def display_status(self):
        """Returns a clean version of the status for display"""
        return self.status.value if hasattr(self.status, "value") else str(self.status)

    @property
    def salesforce_url(self):
        """Generate Salesforce session URL if ID exists"""
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Session__c/{self.salesforce_id}/view"
        return None

    @property
    def is_virtual(self):
        """Check if event is virtual format"""
        return self.type == EventType.VIRTUAL_SESSION

    @property
    def local_start_date(self):
        """Returns the start date in the application's configured timezone"""
        if not self.start_date:
            return None
        if not self.start_date.tzinfo:
            # If date is naive, assume UTC
            self.start_date = self.start_date.replace(tzinfo=timezone.utc)
        tz = pytz.timezone(current_app.config.get("TIMEZONE", "America/Chicago"))
        return self.start_date.astimezone(tz)

    @property
    def is_past_event(self):
        """
        Check if event is in the past.

        Returns:
            bool: True if event has ended (or started if no end_date), False otherwise

        Example:
            >>> event.start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            >>> event.is_past_event
            True  # If current date is after start_date
        """
        if not self.end_date:
            return self.start_date < datetime.now(timezone.utc)
        return self.end_date < datetime.now(timezone.utc)

    @property
    def is_upcoming(self):
        """
        Check if event is upcoming (hasn't started yet).

        Returns:
            bool: True if event start_date is in the future, False otherwise

        Example:
            >>> event.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
            >>> event.is_upcoming
            True  # If current date is before start_date
        """
        now = datetime.now(timezone.utc)
        return self.start_date > now

    @property
    def is_in_progress(self):
        """
        Determine if an event is currently in progress.

        Returns:
            bool: True if current time is between start_date and end_date (or after start_date if no end_date)

        Example:
            >>> event.start_date = datetime.now(timezone.utc) - timedelta(hours=1)
            >>> event.end_date = datetime.now(timezone.utc) + timedelta(hours=1)
            >>> event.is_in_progress
            True
        """
        now = datetime.now(timezone.utc)
        if self.end_date:
            return self.start_date <= now <= self.end_date
        return self.start_date <= now

    def can_register(self):
        """
        Determines if registration is still possible for this event.

        Registration is allowed when:
        - Event status is not CANCELLED or COMPLETED
        - Event has not passed (not in the past)
        - Available slots exist (if slot tracking is enabled)

        Returns:
            bool: True if registration is allowed, False otherwise

        Example:
            >>> event.status = EventStatus.PUBLISHED
            >>> event.available_slots = 10
            >>> event.can_register()
            True

        Usage:
            if event.can_register():
                # Show registration button
        """
        return (
            self.status not in [EventStatus.CANCELLED, EventStatus.COMPLETED]
            and not self.is_past_event
            and (self.available_slots is None or self.available_slots > 0)
        )

    def merge_duplicate(self, data):
        """
        Merge data from a duplicate event's CSV row.

        This method combines data from duplicate events, typically used
        when importing data from external sources that may contain duplicates.
        Includes error handling for invalid data with warnings for non-critical issues.

        Args:
            data (dict): CSV row data to merge

        Raises:
            ValueError: If critical data is missing or invalid

        Example:
            >>> event.merge_duplicate({
            ...     "Registered Student Count": "10",
            ...     "Attended Student Count": "8",
            ...     "Name": "John Doe",
            ...     "SignUp Role": "professional"
            ... })
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        # Combine counts with error handling
        try:
            registered_str = str(data.get("Registered Student Count", "0")).replace(
                "n/a", "0"
            )
            new_registered = int(float(registered_str)) if registered_str else 0
            if new_registered < 0:
                warnings.warn(
                    f"Event {self.id}: Negative registered count value: {new_registered}. "
                    f"Using 0 instead.",
                    UserWarning,
                )
                new_registered = 0
        except (ValueError, TypeError) as e:
            warnings.warn(
                f"Event {self.id}: Invalid registered count value: {data.get('Registered Student Count')}. "
                f"Error: {str(e)}. Skipping count update.",
                UserWarning,
            )
            new_registered = 0

        try:
            attended_str = str(data.get("Attended Student Count", "0")).replace(
                "n/a", "0"
            )
            new_attended = int(float(attended_str)) if attended_str else 0
            if new_attended < 0:
                warnings.warn(
                    f"Event {self.id}: Negative attended count value: {new_attended}. "
                    f"Using 0 instead.",
                    UserWarning,
                )
                new_attended = 0
        except (ValueError, TypeError) as e:
            warnings.warn(
                f"Event {self.id}: Invalid attended count value: {data.get('Attended Student Count')}. "
                f"Error: {str(e)}. Skipping count update.",
                UserWarning,
            )
            new_attended = 0

        self.registered_count += new_registered
        self.attended_count += new_attended

        # Handle role-specific data
        role = data.get("SignUp Role", "").strip().lower()
        name = data.get("Name", "").strip()
        user_id = data.get("User Auth Id", "").strip()
        company = data.get("District or Company", "").strip()

        if name and role:
            if role == "educator":
                current_educators = set(
                    filter(None, (self.educators or "").split("; "))
                )
                current_educator_ids = set(
                    filter(None, (self.educator_ids or "").split("; "))
                )

                if name:
                    current_educators.add(name)
                    self.educators = "; ".join(sorted(current_educators))
                if user_id:
                    current_educator_ids.add(user_id)
                    self.educator_ids = "; ".join(sorted(current_educator_ids))

            elif role == "professional":
                # Split name into first and last
                name_parts = name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                # Try to find existing volunteer
                from models.volunteer import Volunteer, db

                volunteer = Volunteer.query.filter(
                    Volunteer.first_name == first_name, Volunteer.last_name == last_name
                ).first()

                if not volunteer:
                    # Create new volunteer with empty middle name
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name="",  # Explicitly set empty string
                    )
                    db.session.add(volunteer)

                    # Create or get organization if company provided
                    if company:
                        from models.organization import (
                            Organization,
                            VolunteerOrganization,
                        )

                        org = Organization.query.filter_by(name=company).first()
                        if not org:
                            org = Organization(name=company)
                            db.session.add(org)
                            db.session.flush()

                        # Link volunteer to organization
                        vol_org = VolunteerOrganization(
                            volunteer=volunteer,
                            organization=org,
                            role="Professional",
                            is_primary=True,
                        )
                        db.session.add(vol_org)

                # Link volunteer to event if not already linked
                if volunteer not in self.volunteers:
                    self.volunteers.append(volunteer)

    def update_from_csv(self, data):
        """
        Update event from CSV data.

        This method updates an event with data from a CSV import,
        typically used for bulk data updates from external sources.
        Includes comprehensive error handling with warnings for non-critical issues.

        Args:
            data (dict): CSV row data containing event information

        Raises:
            ValueError: If required fields (Date, Title) are missing or invalid

        Example:
            >>> event.update_from_csv({
            ...     "Date": "01/15/2024",
            ...     "Title": "Career Fair",
            ...     "Status": "Completed",
            ...     "Registered Student Count": "50"
            ... })
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        # Validate required fields
        date_str = data.get("Date")
        if not date_str:
            raise ValueError("Date is required for event update")

        title = data.get("Title")
        if not title or not str(title).strip():
            raise ValueError("Title is required for event update")

        # Set basic fields
        self.session_id = data.get("Session ID")
        self.title = str(title).strip()
        self.series = data.get("Series or Event Title")

        # Parse date with multiple format support and error handling
        try:
            # Try common CSV date formats
            date_formats = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%d/%m/%Y"]
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(str(date_str).strip(), fmt)
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                raise ValueError(f"Unable to parse date: {date_str}")

            # Ensure timezone awareness
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)

            self.start_date = parsed_date
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date format: {date_str}. Error: {str(e)}")

        # Set status with validation
        status_str = data.get("Status")
        if status_str:
            try:
                self.status = status_str  # Will use the status validator
            except ValueError as e:
                warnings.warn(
                    f"Event {self.id}: Invalid status value '{status_str}'. "
                    f"Error: {str(e)}. Using default status.",
                    UserWarning,
                )
                self.status = EventStatus.DRAFT

        # Set duration with error handling
        duration_str = data.get("Duration", "0")
        try:
            self.duration = int(float(str(duration_str).replace("n/a", "0")))
            if self.duration < 0:
                warnings.warn(
                    f"Event {self.id}: Negative duration value: {self.duration}. "
                    f"Setting to 0.",
                    UserWarning,
                )
                self.duration = 0
        except (ValueError, TypeError) as e:
            warnings.warn(
                f"Event {self.id}: Invalid duration value: {duration_str}. "
                f"Error: {str(e)}. Setting to None.",
                UserWarning,
            )
            self.duration = None

        self.school = data.get("School")
        self.district_partner = data.get("District or Company")

        # Set counts with error handling
        try:
            registered_str = str(data.get("Registered Student Count", "0")).replace(
                "n/a", "0"
            )
            self.registered_count = int(float(registered_str)) if registered_str else 0
            if self.registered_count < 0:
                warnings.warn(
                    f"Event {self.id}: Negative registered count. Setting to 0.",
                    UserWarning,
                )
                self.registered_count = 0
        except (ValueError, TypeError) as e:
            warnings.warn(
                f"Event {self.id}: Invalid registered count: {data.get('Registered Student Count')}. "
                f"Error: {str(e)}. Setting to 0.",
                UserWarning,
            )
            self.registered_count = 0

        try:
            attended_str = str(data.get("Attended Student Count", "0")).replace(
                "n/a", "0"
            )
            self.attended_count = int(float(attended_str)) if attended_str else 0
            if self.attended_count < 0:
                warnings.warn(
                    f"Event {self.id}: Negative attended count. Setting to 0.",
                    UserWarning,
                )
                self.attended_count = 0
        except (ValueError, TypeError) as e:
            warnings.warn(
                f"Event {self.id}: Invalid attended count: {data.get('Attended Student Count')}. "
                f"Error: {str(e)}. Setting to 0.",
                UserWarning,
            )
            self.attended_count = 0

        # Add handling for volunteers_needed with error handling
        volunteers_needed_str = data.get("Volunteers Needed")
        if volunteers_needed_str:
            try:
                self.volunteers_needed = int(float(str(volunteers_needed_str)))
                if self.volunteers_needed < 0:
                    warnings.warn(
                        f"Event {self.id}: Negative volunteers needed. Setting to 0.",
                        UserWarning,
                    )
                    self.volunteers_needed = 0
            except (ValueError, TypeError) as e:
                warnings.warn(
                    f"Event {self.id}: Invalid volunteers needed value: {volunteers_needed_str}. "
                    f"Error: {str(e)}. Skipping.",
                    UserWarning,
                )

        # Set event type
        self.type = EventType.VIRTUAL_SESSION

        # Handle role-specific data with error handling
        role = data.get("SignUp Role", "").strip().lower()
        name = data.get("Name", "").strip()
        user_id = data.get("User Auth Id", "").strip()
        company = data.get("District or Company", "").strip()

        if name and role:
            if role == "educator":
                self.educators = name
                self.educator_ids = user_id if user_id else ""
            elif role == "professional":
                # Split name into first and last
                name_parts = name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                # Try to find existing volunteer
                from models.volunteer import Volunteer, db

                volunteer = Volunteer.query.filter(
                    Volunteer.first_name == first_name, Volunteer.last_name == last_name
                ).first()

                if not volunteer:
                    # Create new volunteer with empty middle name
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name="",  # Explicitly set empty string
                    )
                    db.session.add(volunteer)

                    # Create or get organization if company provided
                    if company:
                        from models.organization import (
                            Organization,
                            VolunteerOrganization,
                        )

                        org = Organization.query.filter_by(name=company).first()
                        if not org:
                            org = Organization(name=company)
                            db.session.add(org)
                            db.session.flush()

                        # Link volunteer to organization
                        vol_org = VolunteerOrganization(
                            volunteer=volunteer,
                            organization=org,
                            role="Professional",
                            is_primary=True,
                        )
                        db.session.add(vol_org)

                # Update to specify participant type
                self.add_volunteer(
                    volunteer, participant_type="Professional", status="Confirmed"
                )

    def validate_status_transition(self, new_status=None):
        """
        Validate status transitions to ensure logical workflow.

        This method checks if a status transition from the previous status to the
        new status is valid according to business rules. Invalid transitions
        raise exceptions to prevent data inconsistencies.

        Status Workflow Rules:
        - COMPLETED cannot transition to DRAFT
        - CANCELLED cannot transition to COMPLETED
        - DRAFT cannot transition to COMPLETED (but can transition to CANCELLED - cancellation allowed from any status)

        Args:
            new_status: The new status value to validate. If None, uses self.status.

        Raises:
            ValueError: If status transition is invalid

        Note:
            This method is called automatically by the status validator when
            status changes are detected.

        Example:
            >>> event.status = EventStatus.DRAFT
            >>> event.status = EventStatus.COMPLETED  # Raises ValueError
        """
        if not self._previous_status:
            return

        invalid_transitions = {
            EventStatus.COMPLETED: [EventStatus.DRAFT],
            EventStatus.CANCELLED: [EventStatus.COMPLETED],
            EventStatus.DRAFT: [
                EventStatus.COMPLETED
            ],  # DRAFT can transition to CANCELLED (cancellation allowed from any status)
        }

        # Use provided new_status or fall back to self.status
        status_to_check = new_status if new_status is not None else self.status

        # Check if the transition from previous_status to new_status is invalid
        if (
            self._previous_status
            and self._previous_status in invalid_transitions
            and status_to_check in invalid_transitions[self._previous_status]
        ):
            raise ValueError(
                f"Invalid status transition from {self._previous_status} to {status_to_check}"
            )

    @property
    def is_at_capacity(self):
        """Check if event is at volunteer capacity"""
        return (
            self.volunteer_count >= self.volunteers_needed
            if self.volunteers_needed
            else False
        )

    @property
    def location_short(self):
        """
        Returns the first part of the address (street) for display in the UI.
        Used to provide a concise location in event tables and lists.
        Returns None if location is missing or set to 'None'.
        """
        if not self.location or self.location.lower() == "none":
            return None
        return self.location.split(",")[0].strip()

    @property
    def has_location(self):
        """
        Returns True if the event has a valid, non-empty location that is not 'None'.
        Used for conditional display logic in templates.
        """
        return bool(
            self.location and self.location.strip() and self.location.lower() != "none"
        )

    def __init__(self, *args, **kwargs):
        """
        Initialize event with automatic validation.

        Validation is handled automatically via @validates decorators when fields are assigned.
        The status field is tracked for transition validation.
        """
        super().__init__(*args, **kwargs)
        self._previous_status = getattr(self, "status", None)

    @validates("status")
    def validate_status(self, key, value):
        """
        Validates event status to ensure it's a valid EventStatus enum value.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible. Uses value-based
        lookup instead of name-based lookup for better compatibility. Also tracks
        status transitions and validates them.

        Args:
            key (str): The name of the field being validated
            value: The status value to validate

        Returns:
            EventStatus: Valid status enum value

        Raises:
            ValueError: If status value is invalid or transition is invalid

        Example:
            >>> event.validate_status("status", "Completed")
            EventStatus.COMPLETED

            >>> event.validate_status("status", EventStatus.CONFIRMED)
            EventStatus.CONFIRMED
        """
        # Track previous status for transition validation
        # Always get current status first (handles cases after commit/refresh)
        current_status = getattr(self, "status", None)
        # Initialize _previous_status if it doesn't exist or is None
        if not hasattr(self, "_previous_status"):
            self._previous_status = current_status
        else:
            # Update _previous_status with current status before validation
            # This ensures we track the status before the new assignment
            self._previous_status = (
                current_status if current_status is not None else None
            )

        # Handle None - default to DRAFT
        if value is None:
            value = EventStatus.DRAFT

        # If it's already an enum instance, validate it exists
        if isinstance(value, EventStatus):
            # Check transition from _previous_status to new value (before assignment)
            if self._previous_status:
                self.validate_status_transition(new_status=value)
            return value

        # Handle string input - try value-based lookup first
        if isinstance(value, str):
            for enum_member in EventStatus:
                if enum_member.value.lower() == value.lower():
                    # Check transition from _previous_status to new value (before assignment)
                    if self._previous_status:
                        self.validate_status_transition(new_status=enum_member)
                    return enum_member
            # Try name-based lookup for backwards compatibility
            try:
                enum_value = EventStatus[value.upper().replace(" ", "_")]
                if self._previous_status:
                    self.validate_status_transition(new_status=enum_value)
                return enum_value
            except KeyError:
                raise ValueError(
                    f"Invalid status: {value}. "
                    f"Valid values: {[s.value for s in EventStatus]}"
                )

        raise ValueError(f"Status must be an EventStatus enum value or valid string")

    @validates("type")
    def validate_type(self, key, value):
        """
        Validates event type to ensure it's a valid EventType enum value.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible. Uses value-based
        lookup instead of name-based lookup for better compatibility.

        Args:
            key (str): The name of the field being validated
            value: The type value to validate

        Returns:
            EventType: Valid type enum value

        Raises:
            ValueError: If type value is invalid

        Example:
            >>> event.validate_type("type", "virtual_session")
            EventType.VIRTUAL_SESSION

            >>> event.validate_type("type", EventType.CAREER_FAIR)
            EventType.CAREER_FAIR
        """
        if value is None:
            return EventType.IN_PERSON  # Default type

        if isinstance(value, EventType):
            return value

        if isinstance(value, str):
            # Try value-based lookup first (matches enum.value)
            for enum_member in EventType:
                if enum_member.value.lower() == value.lower():
                    return enum_member
            # Try name-based lookup for backwards compatibility
            try:
                return EventType[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid event type: {value}. "
                    f"Valid values: {[t.value for t in EventType]}"
                )

        raise ValueError(f"Type must be an EventType enum value or valid string")

    @validates("format")
    def validate_format(self, key, value):
        """
        Validates event format to ensure it's a valid EventFormat enum value.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible. Uses value-based
        lookup instead of name-based lookup for better compatibility.

        Args:
            key (str): The name of the field being validated
            value: The format value to validate

        Returns:
            EventFormat: Valid format enum value

        Raises:
            ValueError: If format value is invalid

        Example:
            >>> event.validate_format("format", "virtual")
            EventFormat.VIRTUAL

            >>> event.validate_format("format", EventFormat.IN_PERSON)
            EventFormat.IN_PERSON
        """
        if value is None:
            return EventFormat.IN_PERSON  # Default format

        if isinstance(value, EventFormat):
            return value

        if isinstance(value, str):
            # Try value-based lookup first (matches enum.value)
            for enum_member in EventFormat:
                if enum_member.value.lower() == value.lower():
                    return enum_member
            # Try name-based lookup for backwards compatibility
            try:
                return EventFormat[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid event format: {value}. "
                    f"Valid values: {[f.value for f in EventFormat]}"
                )

        raise ValueError(f"Format must be an EventFormat enum value or valid string")

    @validates("cancellation_reason")
    def validate_cancellation_reason(self, key, value):
        """
        Validates cancellation reason to ensure it's a valid CancellationReason enum value.

        This validator handles both enum instances and string representations,
        converting strings to proper enum values when possible. Uses value-based
        lookup instead of name-based lookup for better compatibility.

        Args:
            key (str): The name of the field being validated
            value: The cancellation reason value to validate

        Returns:
            CancellationReason or None: Valid cancellation reason enum value or None

        Raises:
            ValueError: If cancellation reason value is invalid

        Example:
            >>> event.validate_cancellation_reason("cancellation_reason", "weather")
            CancellationReason.WEATHER

            >>> event.validate_cancellation_reason("cancellation_reason", CancellationReason.LOW_ENROLLMENT)
            CancellationReason.LOW_ENROLLMENT
        """
        if value is None:
            return None  # Cancellation reason is optional

        if isinstance(value, CancellationReason):
            return value

        if isinstance(value, str):
            # Try value-based lookup first (matches enum.value)
            for enum_member in CancellationReason:
                if enum_member.value.lower() == value.lower():
                    return enum_member
            # Try name-based lookup for backwards compatibility
            try:
                return CancellationReason[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid cancellation reason: {value}. "
                    f"Valid values: {[r.value for r in CancellationReason]}"
                )

        raise ValueError(
            f"Cancellation reason must be a CancellationReason enum value or valid string"
        )

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
            >>> event.validate_salesforce_id_field("salesforce_id", "0011234567890ABCD")
            '0011234567890ABCD'
        """
        return validate_salesforce_id(value)

    @validates("title")
    def validate_title_field(self, key, value):
        """
        Validates event title to ensure it's not empty.

        Args:
            key (str): The name of the field being validated
            value: The title value to validate

        Returns:
            str: Validated title string

        Raises:
            ValueError: If title is empty or None

        Example:
            >>> event.validate_title_field("title", "Career Fair 2024")
            'Career Fair 2024'
        """
        if not value or not value.strip():
            raise ValueError("Event title cannot be empty")
        return value.strip()

    @validates("start_date", "end_date")
    def validate_dates(self, key, value):
        """
        Validates and converts datetime fields to proper datetime objects with timezone awareness.

        This validator ensures that date/datetime fields are properly formatted and converted
        from various input formats (strings, datetime objects) to consistent timezone-aware
        datetime objects. Invalid dates result in warnings and return None rather than raising
        exceptions, allowing the save operation to continue with null values.

        Args:
            key (str): The name of the field being validated (start_date or end_date)
            value: The datetime value to validate (can be string, datetime, or None)

        Returns:
            datetime: Converted timezone-aware datetime object or None if invalid

        Raises:
            ValueError: If date string cannot be parsed in strict mode

        Example:
            >>> event.validate_dates("start_date", "2024-01-15 10:00:00")
            datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

            >>> event.validate_dates("start_date", "invalid")
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

    def _validate_date_relationship(self):
        """
        Internal method to validate that end_date is after start_date.

        This is called after date assignments to ensure date consistency.
        Uses warnings for non-critical issues instead of exceptions.

        Note:
            This method should be called manually after both dates are set,
            or can be triggered via event listeners.
        """
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                warnings.warn(
                    f"Event {self.id}: End date ({self.end_date}) is before start date ({self.start_date}). "
                    f"This may indicate a data issue.",
                    UserWarning,
                )

    @validates(
        "participant_count",
        "registered_count",
        "attended_count",
        "available_slots",
        "scheduled_participants_count",
        "volunteers_needed",
        "total_requested_volunteer_jobs",
    )
    def validate_counts(self, key, value):
        """
        Validates and normalizes count fields to ensure they are non-negative integers.

        This validator handles various input formats and ensures count fields
        are properly formatted as integers with a minimum value of 0.
        Invalid values result in warnings and return 0 rather than raising exceptions,
        allowing the save operation to continue with default values.

        Args:
            key (str): The name of the field being validated
            value: The count value to validate (can be int, float, or string)

        Returns:
            int: Normalized count value (minimum 0)

        Example:
            >>> event.validate_counts("participant_count", "5")
            5

            >>> event.validate_counts("participant_count", -10)
            0  # Negative values are normalized to 0

            >>> event.validate_counts("participant_count", "invalid")
            0  # Returns 0 and logs warning
        """
        if not value and value != 0:  # Handle empty strings, None, but allow 0
            return 0
        try:
            original_value = value
            value = int(float(value))  # Handle string numbers and floats
            # Issue warning if value is negative (will be normalized to 0)
            if value < 0:
                warnings.warn(
                    f"Invalid {key} value: {original_value}. Negative values normalized to 0.",
                    UserWarning,
                )
                return 0
            return value  # Already non-negative, no need for max()
        except (ValueError, TypeError):
            warnings.warn(
                f"Invalid {key} value: {value}. Using default value of 0.",
                UserWarning,
            )
            return 0

    @validates("duration")
    def validate_duration(self, key, value):
        """
        Validates and normalizes duration field to ensure it's a non-negative integer.

        Duration represents the length of the event in minutes (or appropriate time unit).
        This validator handles various input formats and ensures duration is properly
        formatted as an integer with a minimum value of 0.

        Args:
            key (str): The name of the field being validated
            value: The duration value to validate (can be int, float, or string)

        Returns:
            int or None: Normalized duration value (minimum 0) or None if not provided

        Example:
            >>> event.validate_duration("duration", "60")
            60

            >>> event.validate_duration("duration", -30)
            0  # Negative values are normalized to 0

            >>> event.validate_duration("duration", None)
            None  # Duration is optional
        """
        if not value and value != 0:  # Handle empty strings, None, but allow 0
            return None  # Duration is optional
        try:
            original_value = value
            value = int(float(value))  # Handle string numbers and floats
            # Issue warning if value is negative (will be normalized to 0)
            if value < 0:
                warnings.warn(
                    f"Invalid {key} value: {original_value}. Negative values normalized to 0.",
                    UserWarning,
                )
                return 0
            return value  # Already non-negative, no need for max()
        except (ValueError, TypeError):
            warnings.warn(
                f"Invalid {key} value: {value}. Setting to None.",
                UserWarning,
            )
            return None

    def _validate_count_relationships(self):
        """
        Internal method to validate relationships between count fields.

        This is called after count assignments to ensure count consistency.
        Uses warnings for non-critical issues instead of exceptions.

        Note:
            This method should be called manually after counts are updated,
            or can be triggered via event listeners.
        """
        if self.attended_count and self.registered_count:
            if self.attended_count > self.registered_count:
                warnings.warn(
                    f"Event {self.id}: Attended count ({self.attended_count}) exceeds "
                    f"registered count ({self.registered_count}). This may indicate a data issue.",
                    UserWarning,
                )

        if self.attended_count and self.participant_count:
            if self.attended_count > self.participant_count:
                warnings.warn(
                    f"Event {self.id}: Attended count ({self.attended_count}) exceeds "
                    f"participant count ({self.participant_count}). This may indicate a data issue.",
                    UserWarning,
                )

    def add_volunteer(
        self, volunteer, participant_type="Volunteer", status="Confirmed"
    ):
        """
        Add volunteer to event and create participation record.

        This method adds a volunteer to an event and creates the necessary
        participation record to track their involvement. If the volunteer is
        already associated with the event, updates the existing participation record.

        Args:
            volunteer (Volunteer): Volunteer object to add to the event
            participant_type (str): Type of participation, e.g., 'Volunteer', 'Professional'
                (default: 'Volunteer')
            status (str): Participation status, e.g., 'Confirmed', 'Attended', 'No-Show'
                (default: 'Confirmed')

        Returns:
            EventParticipation: The created or updated participation record

        Example:
            >>> volunteer = Volunteer.query.first()
            >>> participation = event.add_volunteer(volunteer, participant_type="Professional")
            >>> participation.status
            'Confirmed'

        Note:
            This method automatically handles the many-to-many relationship
            and creates the EventParticipation record for tracking.
        """
        # Add to many-to-many relationship if not present
        if volunteer not in self.volunteers:
            self.volunteers.append(volunteer)

        # Create or update EventParticipation
        participation = EventParticipation.query.filter_by(
            volunteer_id=volunteer.id, event_id=self.id
        ).first()

        if not participation:
            participation = EventParticipation(
                volunteer_id=volunteer.id,
                event_id=self.id,
                participant_type=participant_type,
                status=status,
            )
            db.session.add(participation)

        return participation

    @property
    def confirmed_teacher_count(self):
        """Get count of teachers who have confirmed attendance"""
        return EventTeacher.query.filter(
            EventTeacher.event_id == self.id,
            EventTeacher.attendance_confirmed_at.isnot(None),
        ).count()

    @property
    def registered_teacher_count(self):
        """Get count of registered teachers"""
        return EventTeacher.query.filter(EventTeacher.event_id == self.id).count()


class EventTeacher(db.Model):
    """
    Association table for Event-Teacher many-to-many relationship with attendance tracking

    This model tracks the relationship between events and teachers, including
    attendance status, simulcast participation, and confirmation timestamps.
    """

    __tablename__ = "event_teacher"

    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), primary_key=True)

    # Enhanced tracking fields
    status = db.Column(
        db.String(50), default="registered"
    )  # registered, attended, no_show, cancelled
    is_simulcast = db.Column(db.Boolean, default=False)
    attendance_confirmed_at = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = db.relationship("Event", back_populates="teacher_registrations")
    teacher = db.relationship("Teacher", back_populates="event_registrations")


class EventStudentParticipation(db.Model):
    """
    Event Student Participation Model

    Tracks student participation in events, including status, delivery hours,
    and age group information. Links to Salesforce Session_Participant__c records.
    """

    __tablename__ = "event_student_participation"

    id = db.Column(db.Integer, primary_key=True)  # Optional: internal primary key
    salesforce_id = db.Column(
        db.String(18), unique=True, nullable=True, index=True
    )  # Salesforce Session_Participant__c ID

    event_id = db.Column(
        db.Integer, db.ForeignKey("event.id"), nullable=False, index=True
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("student.id"), nullable=False, index=True
    )  # Assumes Student primary key is 'id' inherited from Contact

    # Participation details from Salesforce
    status = db.Column(
        db.String(50), nullable=True
    )  # e.g., 'Registered', 'Attended', 'No Show' from SF Status__c
    delivery_hours = db.Column(db.Float, nullable=True)  # From Delivery_Hours__c
    age_group = db.Column(db.String(100), nullable=True)  # From Age_Group__c

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships (optional but helpful)
    event = db.relationship(
        "Event", backref=db.backref("student_participations", lazy="dynamic")
    )
    student = db.relationship(
        "Student", backref=db.backref("event_participations", lazy="dynamic")
    )

    # Enforce uniqueness for a given event/student pair
    __table_args__ = (
        db.UniqueConstraint("event_id", "student_id", name="uq_event_student"),
    )

    def __repr__(self):
        return f"<EventStudentParticipation SF_ID:{self.salesforce_id} Event:{self.event_id} Student:{self.student_id}>"
