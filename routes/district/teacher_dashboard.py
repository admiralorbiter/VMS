"""
Teacher Dashboard Routes Module
==============================

This module provides the teacher dashboard functionality for the District
Data Tracker. It allows teachers (or admins viewing as teachers) to see their
profile, past sessions, upcoming sessions, and report issues.

Key Features:
- Teacher profile display
- Past sessions listing
- Upcoming sessions listing
- Issue reporting functionality
- Authentication bypass for admin access or direct teacher_id access

Main Endpoints:
- GET /district/<slug>/teacher/select: Teacher selection (admin)
- GET /district/<slug>/teacher/<teacher_id>: Teacher dashboard
- POST /district/<slug>/teacher/<teacher_id>/report-issue: Issue reporting
"""

from datetime import datetime, timezone

from flask import flash, jsonify, render_template, request
from flask_login import current_user

from models import db
from models.event import Event, EventStatus, EventTeacher, EventType
from models.teacher import Teacher
from routes.district import district_bp
from routes.district.portal import RESERVED_SLUGS


def get_teacher_sessions(teacher_id):
    """
    Get past and upcoming sessions for a teacher.

    Args:
        teacher_id: The teacher's database ID

    Returns:
        Tuple of (past_sessions, upcoming_sessions) as lists of dictionaries
    """
    now = datetime.now(timezone.utc)

    # Query all virtual sessions for this teacher
    teacher_registrations = (
        EventTeacher.query.filter_by(teacher_id=teacher_id)
        .join(Event)
        .filter(Event.type == EventType.VIRTUAL_SESSION)
        .options(db.joinedload(EventTeacher.event).joinedload(Event.volunteers))
        .order_by(Event.start_date.desc())
        .all()
    )

    past_sessions = []
    upcoming_sessions = []

    for reg in teacher_registrations:
        event = reg.event
        if not event:
            continue

        # Get presenter information
        presenter_name = ""
        presenter_org = ""
        if event.volunteers:
            # Get first volunteer as presenter
            volunteer = event.volunteers[0]
            presenter_name = f"{volunteer.first_name} {volunteer.last_name}".strip()
            presenter_org = volunteer.organization_name or ""

        # Ensure start_date is timezone-aware for comparison
        start_date = event.start_date
        if start_date:
            # If timezone-naive, assume UTC
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            # Convert to UTC for consistent comparison
            if start_date.tzinfo != timezone.utc:
                start_date = start_date.astimezone(timezone.utc)

        session_data = {
            "id": event.id,
            "title": event.title or "Untitled Session",
            "date": start_date.date() if start_date else None,
            "time": start_date.time() if start_date else None,
            "datetime": start_date,
            "status": event.status.value if event.status else "unknown",
            "topic_theme": event.series or "",
            "session_link": event.registration_link or "",
            "session_id": event.session_id or "",
            "presenter_name": presenter_name,
            "presenter_org": presenter_org,
            "is_simulcast": reg.is_simulcast if reg else False,
            "attendance_status": reg.status if reg else "unknown",
        }

        # Categorize as past or upcoming
        if start_date and start_date < now:
            # Past session
            past_sessions.append(session_data)
        elif start_date and start_date >= now:
            # Upcoming session - only include if status indicates it's happening
            if event.status in [
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
            ]:
                upcoming_sessions.append(session_data)

    # Sort past sessions by date descending (most recent first)
    past_sessions.sort(key=lambda x: x["datetime"] or datetime.min, reverse=True)

    # Sort upcoming sessions by date ascending (soonest first)
    upcoming_sessions.sort(key=lambda x: x["datetime"] or datetime.max)

    return past_sessions, upcoming_sessions


@district_bp.route("/<slug>/teacher/select")
def teacher_select(slug: str):
    """
    Teacher selection page for accessing teacher dashboard.

    For now, allows selecting a teacher to view their dashboard.
    In the future, this will be replaced with proper authentication.

    Args:
        slug: District slug from URL

    Returns:
        Rendered teacher selection template
    """
    if slug.lower() in RESERVED_SLUGS:
        return render_template("errors/404.html"), 404

    # Get list of teachers with virtual sessions
    teachers = (
        Teacher.query.join(EventTeacher)
        .join(Event)
        .filter(Event.type == EventType.VIRTUAL_SESSION)
        .distinct()
        .order_by(Teacher.last_name, Teacher.first_name)
        .limit(100)
        .all()
    )

    return render_template(
        "district/teacher_select.html",
        teachers=teachers,
        district_slug=slug,
    )


@district_bp.route("/<slug>/teacher/<int:teacher_id>")
def teacher_dashboard(slug: str, teacher_id: int):
    """
    Display the teacher dashboard.

    Shows teacher profile, past sessions, and upcoming sessions.
    For now, allows admin access or direct access (bypass auth).

    Args:
        slug: District slug from URL
        teacher_id: The teacher's database ID

    Returns:
        Rendered teacher dashboard template
    """
    if slug.lower() in RESERVED_SLUGS:
        return render_template("errors/404.html"), 404

    # Get teacher
    teacher = Teacher.query.get_or_404(teacher_id)

    # For now: Allow admin access or direct access (bypass auth)
    # In the future, check if current_user is the teacher or has permission
    if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
        # Check if user is admin
        if not hasattr(current_user, "is_admin") or not current_user.is_admin:
            # For now, still allow access (bypass for development)
            pass

    # Get teacher's sessions
    past_sessions, upcoming_sessions = get_teacher_sessions(teacher_id)

    # Get teacher's school name
    school_name = ""
    if teacher.school_id:
        from models.school_model import School

        school = School.query.get(teacher.school_id)
        if school:
            school_name = school.name

    return render_template(
        "district/teacher_dashboard.html",
        teacher=teacher,
        past_sessions=past_sessions,
        upcoming_sessions=upcoming_sessions,
        school_name=school_name,
        district_slug=slug,
    )


@district_bp.route("/<slug>/teacher/<int:teacher_id>/report-issue", methods=["POST"])
def report_issue(slug: str, teacher_id: int):
    """
    Handle issue reporting from teacher dashboard.

    Accepts issue type and category, stores for follow-up.
    For now, uses simple logging or bug_reports model.

    Args:
        slug: District slug from URL
        teacher_id: The teacher's database ID

    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json() or request.form
        issue_type = data.get("issue_type")  # "teacher-related" or "district-related"
        issue_category = data.get("issue_category")  # "missing" or "incorrect"
        description = data.get("description", "")

        # Validate required fields
        if not issue_type or not issue_category:
            return (
                jsonify({"success": False, "message": "Missing required fields"}),
                400,
            )

        # Get teacher
        teacher = Teacher.query.get_or_404(teacher_id)

        # For now: Log the issue (can be enhanced to use bug_reports model)
        from flask import current_app

        current_app.logger.info(
            f"Issue reported by teacher {teacher_id} ({teacher.first_name} {teacher.last_name}): "
            f"Type: {issue_type}, Category: {issue_category}, Description: {description}"
        )

        # Optionally, create a bug report entry
        try:
            from models.bug_report import BugReport, BugReportType
            from models.user import User

            # Get or create a system user for teacher-submitted reports
            # For now, try to find an admin user, or skip bug report creation
            admin_user = User.query.filter_by(security_level=3).first()  # ADMIN level
            submitted_by_id = None
            if hasattr(current_user, "id") and current_user.is_authenticated:
                submitted_by_id = current_user.id
            elif admin_user:
                submitted_by_id = admin_user.id

            if submitted_by_id:
                bug_report = BugReport(
                    type=(
                        BugReportType.DATA_ERROR
                        if issue_category == "incorrect"
                        else BugReportType.OTHER
                    ),
                    description=f"Issue Type: {issue_type}\nCategory: {issue_category}\n"
                    f"District: {slug.upper()}\n"
                    f"Teacher: {teacher.first_name} {teacher.last_name} (ID: {teacher_id})\n"
                    f"Description: {description}",
                    page_url=f"/district/{slug}/teacher/{teacher_id}",
                    page_title="Teacher Dashboard",
                    submitted_by_id=submitted_by_id,
                )
                db.session.add(bug_report)
                db.session.commit()
        except Exception as e:
            # If bug report creation fails, just log it
            current_app.logger.warning(f"Could not create bug report: {e}")

        return jsonify(
            {
                "success": True,
                "message": "Issue reported successfully. Thank you for your feedback!",
            }
        )

    except Exception as e:
        db.session.rollback()
        from flask import current_app

        current_app.logger.error(f"Error reporting issue: {e}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
