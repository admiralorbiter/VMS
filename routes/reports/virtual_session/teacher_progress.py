"""
Teacher progress tracking computation functions for virtual session reports.

Provides functions to compute teacher school breakdowns and teacher
progress tracking for specific districts.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from models.event import Event, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from services.session_status_service import (
    SessionClassification,
    classify_teacher_session,
)

from .computation import _district_name_matches


def compute_teacher_school_breakdown(district_name, virtual_year, date_from, date_to):
    """
    Compute teacher breakdown grouped by school for a specific district.
    Includes both completed sessions, no-show sessions, and upcoming sessions for each teacher.

    Args:
        district_name: Name of the district
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date

    Returns:
        Dictionary with schools as keys and teacher data as values
    """
    now = datetime.now(timezone.utc)
    # Base query for virtual session events
    base_query = Event.query.options(
        joinedload(Event.districts),
        joinedload(Event.teacher_registrations)
        .joinedload(EventTeacher.teacher)
        .joinedload(Teacher.school),
    ).filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.start_date >= date_from,
        Event.start_date <= date_to,
    )

    events = base_query.all()

    # Dictionary to store school -> teachers -> session counts
    school_teacher_data = {}

    for event in events:
        # Process each teacher registration for both completed and no-show sessions
        for teacher_reg in event.teacher_registrations:
            teacher = teacher_reg.teacher
            if not teacher:
                continue

            # Get teacher info
            teacher_name = f"{teacher.first_name} {teacher.last_name}"
            teacher_id = teacher.id

            # Determine teacher's school and district (use teacher's school for accuracy)
            school_name = "Unknown School"
            teacher_district_name = None
            if hasattr(teacher, "school_obj") and teacher.school_obj:
                school_obj = teacher.school_obj
                school_name = school_obj.name
                if hasattr(school_obj, "district") and school_obj.district:
                    teacher_district_name = school_obj.district.name
            elif teacher.school_id:
                school_obj = School.query.get(teacher.school_id)
                if school_obj:
                    school_name = school_obj.name
                    if hasattr(school_obj, "district") and school_obj.district:
                        teacher_district_name = school_obj.district.name

            # Only include registrations for teachers in the requested district
            # Use helper function to handle aliases (e.g., "KCPS (MO)" vs "Kansas City Public Schools (MO)")
            if not _district_name_matches(district_name, teacher_district_name):
                continue

            # Initialize school if not exists
            if school_name not in school_teacher_data:
                school_teacher_data[school_name] = {}

            # Initialize teacher if not exists
            if teacher_id not in school_teacher_data[school_name]:
                school_teacher_data[school_name][teacher_id] = {
                    "id": teacher_id,
                    "name": teacher_name,
                    "sessions": 0,
                    "no_shows": 0,
                    "upcoming_sessions": 0,
                }

            # Classify using shared service
            classification = classify_teacher_session(event, teacher_reg, now)

            if classification == SessionClassification.COMPLETED:
                school_teacher_data[school_name][teacher_id]["sessions"] += 1
            elif classification == SessionClassification.PLANNED:
                school_teacher_data[school_name][teacher_id]["upcoming_sessions"] += 1
            elif classification == SessionClassification.NO_SHOW:
                school_teacher_data[school_name][teacher_id]["no_shows"] += 1
            # CANCELLED, NEEDS_REVIEW, SKIPPED → don't count in school breakdown

    # Convert to sorted structure for template
    school_breakdown = {}
    for school_name, teachers_dict in school_teacher_data.items():
        # Convert teachers dict to sorted list
        teachers_list = sorted(
            teachers_dict.values(),
            key=lambda x: (
                -(
                    x["sessions"] + x["no_shows"] + x["upcoming_sessions"]
                ),  # Sort by total sessions (completed + no-shows + upcoming) desc
                x["name"],
            ),  # Then by name asc
        )

        # Include teachers with at least 1 session (completed, no-show, or upcoming)
        teachers_with_activity = [
            t
            for t in teachers_list
            if t["sessions"] > 0 or t["no_shows"] > 0 or t["upcoming_sessions"] > 0
        ]

        if (
            teachers_with_activity
        ):  # Only include schools that have teachers with activity
            school_breakdown[school_name] = {
                "teachers": teachers_with_activity,
                "total_teachers": len(teachers_with_activity),
                "total_sessions": sum(t["sessions"] for t in teachers_with_activity),
                "total_no_shows": sum(t["no_shows"] for t in teachers_with_activity),
                "total_upcoming_sessions": sum(
                    t["upcoming_sessions"] for t in teachers_with_activity
                ),
            }

    # Sort schools by total activity (sessions + no-shows + upcoming_sessions) (descending)
    sorted_schools = dict(
        sorted(
            school_breakdown.items(),
            key=lambda x: (
                -(
                    x[1]["total_sessions"]
                    + x[1]["total_no_shows"]
                    + x[1]["total_upcoming_sessions"]
                ),
                x[0],
            ),  # Sort by total activity desc, then school name asc
        )
    )

    return sorted_schools


def compute_teacher_progress_tracking(district_name, virtual_year, date_from, date_to):
    """
    Compute teacher progress tracking for specific teachers in Kansas City Kansas Public Schools.
    This function will track progress for a predefined set of teachers imported from a spreadsheet.

    Args:
        district_name: Name of the district (should be "Kansas City Kansas Public Schools")
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date

    Returns:
        Dictionary with teacher progress data grouped by school
    """

    from models import Event, TeacherProgress
    from models.event import EventStatus, EventType

    # Get all teachers from the progress tracking table for this virtual year
    teachers = TeacherProgress.query.filter_by(virtual_year=virtual_year).all()

    if not teachers:
        return {}

    # Get virtual session events for the date range
    events = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.start_date >= date_from,
        Event.start_date <= date_to,
    ).all()

    # Create mappings for unique teachers and their name variations
    teacher_progress_map = {}
    teacher_alias_map = {}
    for teacher in teachers:
        teacher_progress_map[teacher.id] = {
            "teacher": teacher,
            "completed_sessions": 0,
            "planned_sessions": 0,
            "no_show_count": 0,  # Track no-shows to affect status calculation
        }

        # Store multiple possible name variations for matching
        # Normalize names by replacing hyphens with spaces for better matching
        base_name = teacher.name.lower().strip()
        normalized_name = base_name.replace("-", " ").replace(".", "").replace(",", "")

        name_variations = [
            base_name,  # Original with hyphens
            normalized_name,  # Normalized (hyphens -> spaces)
            base_name.replace(".", "").replace(",", "").strip(),
            # Add first + last name variation if different from stored name
            (
                f"{teacher.name.split()[0]} {teacher.name.split()[-1]}".lower()
                if len(teacher.name.split()) > 1
                else teacher.name.lower()
            ),
            # Also add normalized first + last
            (
                f"{teacher.name.split()[0].lower()} {teacher.name.split()[-1].lower()}".replace(
                    "-", " "
                )
                if len(teacher.name.split()) > 1
                else normalized_name
            ),
        ]

        # Ensure aliases point back to the unique teacher entry
        for name_var in name_variations:
            if name_var:
                teacher_alias_map.setdefault(name_var, teacher.id)

    # Count completed and planned sessions for each teacher
    for event in events:
        for teacher_reg in event.teacher_registrations:
            if teacher_reg.teacher:
                teacher_name = (
                    f"{teacher_reg.teacher.first_name} {teacher_reg.teacher.last_name}"
                )
                teacher_key = teacher_name.lower().strip()
                # Normalize the key by replacing hyphens with spaces for better matching
                teacher_key_normalized = teacher_key.replace("-", " ")

                # Try exact match first against aliases (both original and normalized)
                teacher_id = teacher_alias_map.get(
                    teacher_key
                ) or teacher_alias_map.get(teacher_key_normalized)
                progress_data = (
                    teacher_progress_map.get(teacher_id) if teacher_id else None
                )

                if not progress_data:
                    # Try flexible matching - look for partial matches
                    # Compare both original and normalized versions
                    for name_key, alias_teacher_id in teacher_alias_map.items():
                        name_key_normalized = name_key.replace("-", " ")
                        # Check if either version matches (original or normalized)
                        if (
                            teacher_key in name_key
                            or name_key in teacher_key
                            or teacher_key_normalized in name_key_normalized
                            or name_key_normalized in teacher_key_normalized
                        ) and len(teacher_key) > 3:
                            progress_data = teacher_progress_map.get(alias_teacher_id)
                            if progress_data:
                                break

                if progress_data:
                    # Use shared classifier for consistent status detection
                    now = datetime.now(timezone.utc)
                    classification = classify_teacher_session(event, teacher_reg, now)

                    if classification == SessionClassification.NO_SHOW:
                        progress_data["no_show_count"] += 1
                        continue
                    if classification == SessionClassification.CANCELLED:
                        continue

                    if classification == SessionClassification.COMPLETED:
                        progress_data["completed_sessions"] += 1
                    elif classification == SessionClassification.PLANNED:
                        progress_data["planned_sessions"] += 1
                    elif classification == SessionClassification.NEEDS_REVIEW:
                        # Past events stuck in non-terminal status —
                        # count toward planned so the no-show force-override
                        # doesn't incorrectly trigger "Needs Planning"
                        progress_data["planned_sessions"] += 1

    # Group teachers by building/school
    school_data = {}
    for progress_data in teacher_progress_map.values():
        teacher = progress_data["teacher"]
        building = teacher.building

        if building not in school_data:
            school_data[building] = {
                "teachers": [],
                "total_teachers": 0,
                "goals_achieved": 0,
                "goals_in_progress": 0,
                "goals_not_started": 0,
            }

        # Calculate progress status
        # If teacher has any no-shows and hasn't completed target, they need to replan
        no_show_count = progress_data.get("no_show_count", 0)
        completed = progress_data["completed_sessions"]
        planned = progress_data["planned_sessions"]
        total_sessions = completed + planned

        # If teacher has no-shows and hasn't completed target, check if they need to replan
        # Only force "Needs Planning" if they don't have enough planned sessions to meet target
        if no_show_count > 0 and completed < teacher.target_sessions:
            # If they have enough planned sessions to meet target, they're "In Progress"
            # Otherwise, they need to replan
            if total_sessions >= teacher.target_sessions:
                # They have enough planned sessions, so they're "In Progress"
                progress_status = teacher.get_progress_status(completed, planned)
            else:
                # Not enough planned sessions, force "Needs Planning" - no-shows mean they need to replan
                progress_status = {
                    "status": "not_started",
                    "status_text": "Needs Planning",
                    "status_class": "not_started",
                    "progress_percentage": (
                        min(100, (completed / teacher.target_sessions) * 100)
                        if teacher.target_sessions > 0
                        else 0
                    ),
                    "completed_sessions": completed,
                    "planned_sessions": planned,
                    "needed_sessions": max(
                        0, teacher.target_sessions - completed - planned
                    ),
                }
        else:
            progress_status = teacher.get_progress_status(completed, planned)

        teacher_info = {
            "id": teacher.id,
            "name": teacher.name,
            "email": teacher.email,
            "grade": teacher.grade,
            "target_sessions": teacher.target_sessions,
            "completed_sessions": progress_data["completed_sessions"],
            "planned_sessions": progress_data["planned_sessions"],
            "needed_sessions": progress_status["needed_sessions"],
            "progress_percentage": progress_status["progress_percentage"],
            "goal_status_class": progress_status["status_class"],
            "goal_status_text": progress_status["status_text"],
            "progress_class": (
                "danger"
                if progress_status["progress_percentage"] < 50
                else "warning" if progress_status["progress_percentage"] < 100 else ""
            ),
        }

        school_data[building]["teachers"].append(teacher_info)
        school_data[building]["total_teachers"] += 1

        # Count goal statuses
        if progress_status["status"] == "achieved":
            school_data[building]["goals_achieved"] += 1
        elif progress_status["status"] == "in_progress":
            school_data[building]["goals_in_progress"] += 1
        else:
            school_data[building]["goals_not_started"] += 1

    # Sort teachers within each school by progress (achieved first, then by name)
    for building, data in school_data.items():
        data["teachers"].sort(
            key=lambda x: (
                -x["completed_sessions"],  # Completed sessions first
                -x["planned_sessions"],  # Then planned sessions
                x["name"],  # Then alphabetically
            )
        )

    return school_data
