"""
Teacher progress computation helpers.

Contains functions for computing teacher school breakdowns, progress
tracking, name matching, and semester archiving. These are standalone
functions (not routes) used by both route handlers and external scripts.
"""

import difflib
from datetime import datetime, timezone

from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import db
from models.contact import LocalStatusEnum
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from models.teacher_progress_archive import TeacherProgressArchive

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
    from datetime import datetime, timezone

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

            # Determine classification for this registration
            def _norm(x):
                return (x or "").strip().lower()

            def _sanitize(text: str) -> str:
                t = (text or "").lower().strip()
                for ch in ["_", "-", "/", "\\", ",", ".", "  "]:
                    t = t.replace(ch, " ")
                while "  " in t:
                    t = t.replace("  ", " ")
                return t

            original_status = _sanitize(getattr(event, "original_status_string", None))
            moved_to_in_person = "moved to in-person" in original_status
            # Consider common variations for teacher no-show at the event level
            event_teacher_no_show = ("teacher no show" in original_status) or (
                "teacher did not attend" in original_status
            )
            tr_status = _sanitize(getattr(teacher_reg, "status", None))

            is_teacher_no_show = (
                "teacher no show" in tr_status
                or "no show" in tr_status
                or "did not attend" in tr_status
            )
            is_teacher_cancel = (
                "cancel" in tr_status
                or "withdraw" in tr_status
                or "inclement weather" in tr_status
                or "technical" in tr_status
            )
            completed_by_status = ("attended" in tr_status) or (
                "completed" in tr_status
            )

            counted_completed = False
            counted_no_show = False

            # Check for upcoming sessions (Teacher requested or Industry chat + Draft status)
            # Only count upcoming sessions that are actually in the future
            session_type = getattr(event, "additional_information", "")
            event_status = getattr(event, "status", "")
            teacher_reg_status = getattr(teacher_reg, "status", "")

            # Handle enum status values
            event_status_str = (
                str(event_status.value)
                if hasattr(event_status, "value")
                else str(event_status)
            )
            teacher_reg_status_str = (
                str(teacher_reg_status) if teacher_reg_status else ""
            )

            # Check if this is an upcoming session AND it's actually in the future
            # Ensure both datetimes are timezone-aware for comparison
            event_start_date = event.start_date
            if event_start_date and event_start_date.tzinfo is None:
                # If event.start_date is timezone-naive, assume it's in UTC
                event_start_date = event_start_date.replace(tzinfo=timezone.utc)

            is_upcoming_session = (
                (
                    "teacher requested" in (session_type or "").lower()
                    or "industry chat" in (session_type or "").lower()
                )
                and (
                    "draft" in event_status_str.lower()
                    or "draft" in teacher_reg_status_str.lower()
                )
                and event_start_date
                and event_start_date > now  # Only future sessions
            )

            if is_upcoming_session:
                school_teacher_data[school_name][teacher_id]["upcoming_sessions"] += 1
            # Prioritize explicit no-show status over attendance_confirmed_at
            elif is_teacher_no_show or (
                event_teacher_no_show and not moved_to_in_person
            ):
                school_teacher_data[school_name][teacher_id]["no_shows"] += 1
                counted_no_show = True
            elif (
                moved_to_in_person
                or completed_by_status
                or teacher_reg.attendance_confirmed_at
            ):
                school_teacher_data[school_name][teacher_id]["sessions"] += 1
                counted_completed = True
            else:
                # Ignore cancellations and indeterminate statuses (do not count as no-show)
                if not is_teacher_cancel:
                    # If truly indeterminate and attendance not confirmed, do nothing
                    pass
                else:
                    pass

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
                    # Normalize status strings for robust matching (similar to compute_teacher_school_breakdown)
                    def _sanitize_status(text):
                        """Normalize status text for comparison"""
                        if not text:
                            return ""
                        t = str(text).lower().strip()
                        # Replace common separators with spaces
                        for ch in ["_", "-", "/", "\\", ",", ".", "  "]:
                            t = t.replace(ch, " ")
                        # Normalize multiple spaces
                        while "  " in t:
                            t = t.replace("  ", " ")
                        return t

                    # Check teacher's individual registration status first
                    teacher_reg_status = _sanitize_status(
                        getattr(teacher_reg, "status", "")
                    )
                    # Also check event-level status for teacher no-shows
                    event_original_status = _sanitize_status(
                        getattr(event, "original_status_string", "")
                    )
                    # Check if event status enum is NO_SHOW
                    event_status_is_no_show = event.status == EventStatus.NO_SHOW

                    # Comprehensive no-show detection
                    # Check teacher registration status first (most specific)
                    is_teacher_no_show = (
                        "teacher no show" in teacher_reg_status
                        or "no show" in teacher_reg_status
                        or "did not attend" in teacher_reg_status
                    )

                    # If teacher registration doesn't have no-show, check event-level status
                    if not is_teacher_no_show:
                        is_teacher_no_show = (
                            "teacher no show" in event_original_status
                            or "teacher did not attend" in event_original_status
                            # Check if event status enum is NO_SHOW and original status mentions teacher
                            or (
                                event_status_is_no_show
                                and "teacher" in event_original_status
                            )
                        )
                    is_teacher_cancel = (
                        "cancel" in teacher_reg_status
                        or "withdraw" in teacher_reg_status
                        or "cancelled" in teacher_reg_status
                    )

                    # Track no-shows - they should not count as completed or planned,
                    # but they affect the status calculation (teacher needs to replan)
                    if is_teacher_no_show:
                        progress_data["no_show_count"] += 1
                        continue
                    if is_teacher_cancel:
                        continue

                    # Check if teacher registration has "count" status - this should count as completed
                    # even if the event status is NO_SHOW (as long as it's not a teacher no-show)
                    is_count_status = (
                        teacher_reg_status == "count" or "count" in teacher_reg_status
                    )

                    # Only count as completed if teacher actually attended (not no-show or cancelled)
                    # Check if this is a completed session
                    if (
                        event.status == EventStatus.COMPLETED
                        or (event.status == EventStatus.SIMULCAST)
                        or (getattr(event, "original_status_string", "") or "").lower()
                        in ["completed", "successfully completed"]
                        # Also count if teacher registration has "count" status
                        or is_count_status
                    ):
                        progress_data["completed_sessions"] += 1
                    # Check if this is a planned/upcoming session
                    elif event.status == EventStatus.DRAFT or (
                        getattr(event, "original_status_string", "") or ""
                    ).lower() in ["draft", "registered"]:
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
            "matched_teacher_id": teacher.teacher_id,  # ID of matched Teacher record
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


def normalize_name(name):
    """
    Normalize a name for matching purposes.

    Args:
        name: Name string to normalize

    Returns:
        Normalized name string (lowercase, no punctuation, single spaces)
    """
    if not name:
        return ""
    # Convert to lowercase
    normalized = name.lower().strip()
    # Remove common punctuation
    for char in [".", ",", "-", "(", ")", "'", '"']:
        normalized = normalized.replace(char, " ")
    # Replace multiple spaces with single space
    while "  " in normalized:
        normalized = normalized.replace("  ", " ")
    return normalized.strip()


def name_similarity(name1, name2):
    """
    Calculate similarity between two names using SequenceMatcher.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()


def match_teacher_progress_to_teachers(virtual_year=None, min_similarity=0.85):
    """
    Automatically match TeacherProgress entries to Teacher records.

    Matching strategy:
    1. Match by email (exact match on primary email) - highest priority
    2. Match by name (fuzzy matching with similarity threshold) - secondary

    Args:
        virtual_year: Virtual year to match teachers for (None = all years)
        min_similarity: Minimum similarity ratio for name matching (default: 0.85)

    Returns:
        dict: Statistics about matching results
    """
    from models.teacher_progress import TeacherProgress

    # Get all TeacherProgress entries (optionally filtered by virtual_year)
    query = TeacherProgress.query
    if virtual_year:
        query = query.filter_by(virtual_year=virtual_year)

    teacher_progress_entries = query.filter_by(teacher_id=None).all()

    # Get all teachers with their primary emails
    teachers = Teacher.query.all()

    # Build email lookup map (email -> teacher)
    email_to_teacher = {}
    for teacher in teachers:
        primary_email = teacher.emails.filter_by(primary=True).first()
        if primary_email and primary_email.email:
            email_lower = primary_email.email.lower().strip()
            email_to_teacher[email_lower] = teacher

    stats = {
        "total_processed": len(teacher_progress_entries),
        "matched_by_email": 0,
        "matched_by_name": 0,
        "unmatched": 0,
        "errors": [],
    }

    for tp_entry in teacher_progress_entries:
        try:
            matched_teacher = None

            # Strategy 1: Match by email (exact match)
            if tp_entry.email:
                email_lower = tp_entry.email.lower().strip()
                matched_teacher = email_to_teacher.get(email_lower)
                if matched_teacher:
                    stats["matched_by_email"] += 1

            # Strategy 2: Match by name (fuzzy matching) if email didn't match
            if not matched_teacher and tp_entry.name:
                best_match = None
                best_similarity = 0.0

                for teacher in teachers:
                    # Build full name from teacher
                    teacher_full_name = (
                        f"{teacher.first_name} {teacher.last_name}".strip()
                    )
                    if not teacher_full_name:
                        continue

                    similarity = name_similarity(tp_entry.name, teacher_full_name)
                    if similarity > best_similarity and similarity >= min_similarity:
                        best_similarity = similarity
                        best_match = teacher

                if best_match:
                    matched_teacher = best_match
                    stats["matched_by_name"] += 1

            # Update TeacherProgress entry with matched teacher_id
            if matched_teacher:
                tp_entry.teacher_id = matched_teacher.id
            else:
                stats["unmatched"] += 1

        except Exception as e:
            stats["errors"].append(f"Error matching {tp_entry.name}: {str(e)}")
            continue

    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        stats["errors"].append(f"Error committing matches: {str(e)}")

    return stats


def snapshot_semester_progress(
    district_name, virtual_year, semester_name, date_from, date_to
):
    """
    Snapshot teacher progress for a specific semester and archive it.
    """
    try:
        from flask_login import current_user

        # 1. Compute stats for the semester
        print(
            f"INFO: Snapshotting {semester_name} for {district_name} ({date_from} - {date_to})"
        )
        progress_data = compute_teacher_progress_tracking(
            district_name, virtual_year, date_from, date_to
        )

        count = 0
        userid = None
        try:
            # handle script execution context where current_user might be missing or anonymous
            if current_user and current_user.is_authenticated:
                userid = current_user.id
        except:
            pass

        # 2. Iterate and save to archive
        for school_name, school_data in progress_data.items():
            for teacher_data in school_data.get("teachers", []):
                # Find original TeacherProgress record
                tp_id = teacher_data.get("id")
                if not tp_id:
                    continue

                # Check if already archived
                existing = TeacherProgressArchive.query.filter_by(
                    teacher_progress_id=tp_id, semester_name=semester_name
                ).first()

                if existing:
                    continue

                # Create archive
                archive = TeacherProgressArchive(
                    teacher_progress_id=tp_id,
                    semester_name=semester_name,
                    academic_year=virtual_year,
                    virtual_year=virtual_year,
                    date_from=date_from,
                    date_to=date_to,
                    completed_sessions=teacher_data.get("completed_sessions", 0),
                    planned_sessions=teacher_data.get("planned_sessions", 0),
                    target_sessions=teacher_data.get("target_sessions", 1),
                    status=teacher_data.get(
                        "goal_status_class"
                    ),  # "achieved", "in_progress", "not_started"
                    status_text=teacher_data.get("goal_status_text"),
                    progress_percentage=teacher_data.get("progress_percentage", 0),
                    created_by=userid,
                )
                db.session.add(archive)
                count += 1

        db.session.commit()
        print(f"INFO: Successfully archived {count} records for {semester_name}")
        return True, count
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to snapshot semester: {str(e)}")
        import traceback

        traceback.print_exc()
        return False, 0
