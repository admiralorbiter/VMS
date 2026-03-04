"""
Email Reminder Utilities
========================

Utility functions for building and sending teacher session reminder emails.
Queries upcoming virtual sessions and builds per-teacher personalized contexts
for the teacher_session_reminder email template.

Key Functions:
    - get_upcoming_virtual_sessions: Query future virtual sessions
    - build_session_list_html: Format sessions as styled HTML table
    - build_session_list_text: Format sessions as plain text
    - build_teacher_reminder_context: Build full placeholder context per teacher
    - send_session_reminders: Orchestrate sending reminders to all teachers
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from models import db
from models.email import EmailTemplate
from models.event import Event, EventStatus, EventType
from models.teacher_progress import TeacherProgress
from utils.email import create_delivery_attempt, create_email_message

logger = logging.getLogger(__name__)

# Default district name for KCKPS
DEFAULT_DISTRICT_NAME = "Kansas City Kansas Public Schools"

# Statuses that indicate an active (not cancelled/completed) session
ACTIVE_SESSION_STATUSES = [
    EventStatus.CONFIRMED,
    EventStatus.PUBLISHED,
    EventStatus.REQUESTED,
]

# Status badge styling for HTML emails
STATUS_STYLES = {
    EventStatus.CONFIRMED: ("background: #d4edda; color: #155724;", "Confirmed"),
    EventStatus.PUBLISHED: ("background: #cce5ff; color: #004085;", "Published"),
    EventStatus.REQUESTED: ("background: #fff3cd; color: #856404;", "Requested"),
}


def get_upcoming_virtual_sessions(
    tenant_id: Optional[int] = None,
) -> List[Event]:
    """
    Query upcoming virtual sessions.

    Returns future virtual sessions with active statuses, ordered by start date.

    Args:
        tenant_id: Optional tenant ID to filter sessions by district

    Returns:
        List of Event objects
    """
    now = datetime.now(timezone.utc)

    query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status.in_(ACTIVE_SESSION_STATUSES),
        Event.start_date > now,
    )

    if tenant_id is not None:
        query = query.filter(Event.tenant_id == tenant_id)

    return query.order_by(Event.start_date.asc()).all()


def build_session_list_html(sessions: List[Event]) -> str:
    """
    Build a styled HTML table of upcoming sessions for email embedding.

    Args:
        sessions: List of Event objects

    Returns:
        HTML string containing a formatted table
    """
    if not sessions:
        return (
            '<p style="color: #888; font-style: italic; text-align: center; '
            'padding: 20px;">No upcoming sessions currently scheduled.</p>'
        )

    rows = ""
    for session in sessions:
        # Format date and time in Central timezone
        start = session.start_date
        if start.tzinfo is not None:
            import pytz

            tz = pytz.timezone("America/Chicago")
            start = start.astimezone(tz)

        date_str = start.strftime("%b %d, %Y")
        time_str = start.strftime("%I:%M %p").lstrip("0")

        # Status badge
        style_info = STATUS_STYLES.get(
            session.status, ("background: #e2e3e5; color: #383d41;", "Unknown")
        )
        status_style, status_text = style_info

        # Career cluster (fallback to empty string)
        cluster = session.career_cluster or "—"

        rows += f"""
            <tr>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">{date_str}</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">{time_str}</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">{session.title}</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee;">{cluster}</td>
                <td style="padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center;">
                    <span style="{status_style} padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">{status_text}</span>
                </td>
            </tr>"""

    return f"""
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
        <thead>
            <tr style="background-color: #003366;">
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Date</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Time</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Title</th>
                <th style="padding: 10px 8px; text-align: left; color: white; border-bottom: 2px solid #c8a415;">Career Cluster</th>
                <th style="padding: 10px 8px; text-align: center; color: white; border-bottom: 2px solid #c8a415;">Status</th>
            </tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>"""


def build_session_list_text(sessions: List[Event]) -> str:
    """
    Build a plain text list of upcoming sessions.

    Args:
        sessions: List of Event objects

    Returns:
        Plain text string listing sessions
    """
    if not sessions:
        return "No upcoming sessions currently scheduled."

    lines = []
    for session in sessions:
        start = session.start_date
        if start.tzinfo is not None:
            import pytz

            tz = pytz.timezone("America/Chicago")
            start = start.astimezone(tz)

        date_str = start.strftime("%b %d, %Y")
        time_str = start.strftime("%I:%M %p").lstrip("0")
        cluster = session.career_cluster or "N/A"

        status_text = (
            session.status.value
            if hasattr(session.status, "value")
            else str(session.status)
        )

        lines.append(
            f"- {date_str} {time_str} | {session.title} | {cluster} | {status_text}"
        )

    return "\n".join(lines)


def get_completed_session_count(teacher: TeacherProgress) -> int:
    """
    Count completed virtual sessions for a teacher.

    Counts events where the teacher's email appears in the educators field
    and the event status is Completed.

    Args:
        teacher: TeacherProgress record

    Returns:
        Number of completed sessions
    """
    if not teacher.email:
        return 0

    query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status == EventStatus.COMPLETED,
    )

    if teacher.tenant_id is not None:
        query = query.filter(Event.tenant_id == teacher.tenant_id)

    # Check if teacher email or name appears in the educators field
    completed_events = query.all()
    count = 0
    for event in completed_events:
        if event.educators:
            educator_list = [e.strip().lower() for e in event.educators.split(";")]
            if (
                teacher.name.lower() in educator_list
                or teacher.email.lower() in educator_list
            ):
                count += 1

    return count


def build_teacher_reminder_context(
    teacher: TeacherProgress,
    sessions: List[Event],
    completed_count: int = 0,
    district_name: str = DEFAULT_DISTRICT_NAME,
) -> Dict:
    """
    Build the full placeholder context dict for one teacher.

    Args:
        teacher: TeacherProgress record
        sessions: List of upcoming Event objects
        completed_count: Number of completed sessions for this teacher
        district_name: District name for branding

    Returns:
        Dictionary of placeholder values for template rendering
    """
    return {
        "teacher_name": teacher.name,
        "building_name": teacher.building,
        "district_name": district_name,
        "session_list": build_session_list_html(sessions),
        "session_list_text": build_session_list_text(sessions),
        "completed_count": completed_count,
        "target_sessions": teacher.target_sessions,
    }


def send_session_reminders(
    tenant_id: Optional[int] = None,
    created_by_id: Optional[int] = None,
    dry_run: bool = False,
    district_name: str = DEFAULT_DISTRICT_NAME,
) -> Dict:
    """
    Send session reminder emails to all active teachers.

    Orchestrates the full reminder workflow:
    1. Loads the teacher_session_reminder template
    2. Queries upcoming virtual sessions
    3. Iterates over active TeacherProgress records
    4. Builds personalized context and creates EmailMessage for each
    5. Optionally creates delivery attempts

    Args:
        tenant_id: Optional tenant ID to scope to a district
        created_by_id: User ID of the admin triggering the send
        dry_run: If True, creates messages but doesn't actually deliver
        district_name: District name for email branding

    Returns:
        Summary dict with sent_count, skipped_count, error_count, errors list
    """
    result = {
        "sent_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "errors": [],
        "dry_run": dry_run,
    }

    # Load template
    template = EmailTemplate.query.filter_by(
        purpose_key="teacher_session_reminder",
        is_active=True,
    ).first()

    if not template:
        result["errors"].append(
            "Template 'teacher_session_reminder' not found or not active. "
            "Run the seed script first."
        )
        result["error_count"] = 1
        return result

    # Get upcoming sessions
    sessions = get_upcoming_virtual_sessions(tenant_id=tenant_id)

    if not sessions:
        logger.info("No upcoming virtual sessions found. No reminders to send.")
        result["errors"].append("No upcoming virtual sessions found.")
        return result

    # Get active teachers
    teacher_query = TeacherProgress.query.filter_by(is_active=True)
    if tenant_id is not None:
        teacher_query = teacher_query.filter_by(tenant_id=tenant_id)

    teachers = teacher_query.all()

    if not teachers:
        logger.info("No active teachers found in TeacherProgress.")
        result["errors"].append("No active teachers found.")
        return result

    logger.info(
        "Sending session reminders to %s teachers with %s upcoming sessions",
        len(teachers),
        len(sessions),
    )

    sender_id = created_by_id or 1

    for teacher in teachers:
        try:
            # Skip teachers without email
            if not teacher.email:
                result["skipped_count"] += 1
                logger.warning("Skipping teacher %s — no email address", teacher.name)
                continue

            # Get completed count for this teacher
            completed = get_completed_session_count(teacher)

            # Build context
            context = build_teacher_reminder_context(
                teacher=teacher,
                sessions=sessions,
                completed_count=completed,
                district_name=district_name,
            )

            # Create email message
            message = create_email_message(
                template=template,
                recipients=[teacher.email],
                context=context,
                created_by_id=sender_id,
            )

            db.session.commit()

            # Create delivery attempt
            create_delivery_attempt(message, is_dry_run=dry_run)
            result["sent_count"] += 1

            logger.info(
                "Reminder %s for teacher %s (%s)",
                "queued (dry-run)" if dry_run else "sent",
                teacher.name,
                teacher.email,
            )

        except Exception as e:
            result["error_count"] += 1
            error_msg = f"Failed for {teacher.name} ({teacher.email}): {e}"
            result["errors"].append(error_msg)
            logger.error("Session reminder error: %s", error_msg)
            db.session.rollback()

    logger.info(
        "Session reminder send complete: sent=%s, skipped=%s, errors=%s",
        result["sent_count"],
        result["skipped_count"],
        result["error_count"],
    )

    return result
