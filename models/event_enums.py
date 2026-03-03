"""
Event Enumerations
==================

Extracted from event.py (TD-012) for better code organization.
Contains all enum types used for event models.

These enums are re-exported from event.py for backward compatibility,
so existing ``from models.event import EventType`` imports continue to work.
"""

from enum import Enum


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
    Cancellation Reason Enumeration (DEC-008)

    Defines the possible reasons why an event might be cancelled.
    Used for tracking and reporting on event cancellations, particularly
    for virtual sessions imported from Pathful.

    Reasons:
        - WEATHER: Weather / Snow Day - School closed due to weather
        - PRESENTER_CANCELLED: Presenter Cancelled - Volunteer/presenter unable to attend
        - TEACHER_CANCELLED: Teacher Cancelled - Teacher unable to host session
        - SCHOOL_CONFLICT: School Conflict - Assembly, testing, or other school event
        - TECHNICAL_ISSUES: Technical Issues - Platform or connectivity problems
        - LOW_ENROLLMENT: Low Enrollment - Not enough student signups
        - SCHEDULING_ERROR: Scheduling Error - Double-booked or incorrectly scheduled
        - OTHER: Other - See notes for details
    """

    WEATHER = "Weather / Snow Day"
    PRESENTER_CANCELLED = "Presenter Cancelled"
    TEACHER_CANCELLED = "Teacher Cancelled"
    SCHOOL_CONFLICT = "School Conflict"
    TECHNICAL_ISSUES = "Technical Issues"
    LOW_ENROLLMENT = "Low Enrollment"
    SCHEDULING_ERROR = "Scheduling Error"
    OTHER = "Other"


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
            EventStatus: Mapped enum value, defaults to REQUESTED if unknown
        """
        if not status_str:
            return cls.REQUESTED

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
            "pathful professional cancellation": cls.CANCELLED,
            "local professional cancellation": cls.CANCELLED,
            # Additional mappings for virtual sessions
            "teacher requested": cls.REQUESTED,
            "industry chat": cls.CONFIRMED,
        }

        return status_mapping.get(status_str, cls.REQUESTED)
