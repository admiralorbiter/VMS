import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from flask_login import current_user

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation, EventType
from models.reports import DistrictYearEndReport
from models.school_model import School
from models.student import Student

# ---------------------------------------------------------------------------
# Virtual session student estimation constant
# ---------------------------------------------------------------------------
# Each attending teacher is assumed to represent one classroom of students.
# This constant is the single source of truth for that assumption.
# Update here to change the estimate globally across all reports.
VIRTUAL_STUDENTS_PER_TEACHER = 25

# from models.upcoming_events import UpcomingEvent  # Moved to microservice

# District mapping configuration
DISTRICT_MAPPING = {
    # Districts to show
    "0015f00000JU4opAAD": {  # Grandview School District
        "name": "Grandview School District",
        "district_code": "48074",
        "merge_with": None,
        "show": True,
        "aliases": [
            "Grandview",
        ],
    },
    "0015f00000JU4pVAAT": {  # Kansas City Kansas Public Schools
        "name": "Kansas City Kansas Public Schools",
        "district_code": "48078",
        "merge_with": None,
        "show": True,
        "aliases": [
            "Kansas City Kansas School District",
            "KANSAS CITY USD 500",
            "KCKPS (KS)",
        ],
    },
    "0015f00000JU9ZEAA1": {  # Allen Village - District
        "name": "Allen Village - District",
        "district_code": "48909",
        "merge_with": None,
        "show": True,
    },
    "0015f00000JU9ZFAA1": {  # Hickman Mills School District
        "name": "Hickman Mills School District",
        "district_code": "48072",
        "merge_with": None,
        "show": True,
        "aliases": ["Hickman Mills"],
    },
    "0015f00000JVaPKAA1": {  # GUADALUPE CENTERS SCHOOLS
        "name": "GUADALUPE CENTERS SCHOOLS",
        "district_code": "48902",
        "merge_with": None,
        "show": True,
    },
    "0015f00000KvuZTAAZ": {  # Center School District
        "name": "Center School District",
        "district_code": "48080",
        "merge_with": None,
        "show": True,
    },
    "0015f00000KxHwVAAV": {  # Kansas City Public Schools (MO)
        "name": "Kansas City Public Schools (MO)",
        "district_code": None,
        "merge_with": None,
        "show": True,
        "aliases": ["KCPS (MO)"],
    },
}


def get_district_student_count_for_event(event, target_district_id):
    """
    Count students for an event that belong to the specified district.

    For virtual sessions: counts all EventTeacher records with status
    'attended' or 'registered' (registered = assumed present for past events)
    and multiplies by VIRTUAL_STUDENTS_PER_TEACHER. The teacher→school→district
    chain is intentionally bypassed — the event is already attributed to the
    correct district via event.districts, and many Pathful-imported teachers
    lack school_id linkage (tracked as DQ-PATHFUL-SCHOOL-LINK).

    For in-person events: uses manual EventAttendanceDetail if available,
    then falls back to EventStudentParticipation aggregate counts.

    Args:
        event: Event object
        target_district_id: The district ID (used only for in-person events)

    Returns:
        int: Estimated or actual student count for the event
    """
    if event.type in (EventType.VIRTUAL_SESSION, EventType.CONNECTOR_SESSION):
        # Count all teachers who attended or are registered (assumed present)
        # No school→district join needed; the event itself is already district-attributed.
        from models.event import EventTeacher

        teacher_count = sum(
            1
            for et in event.teacher_registrations
            if et.status in ("attended", "registered")
        )
        return teacher_count * VIRTUAL_STUDENTS_PER_TEACHER
    else:
        # Check if event is shared across districts (multi-attribution)
        # Proxy: if district_partner contains a comma, or event is in >1 district M2M
        # This is a best-effort heuristic for the live-compute path;
        # the cache refresh path uses the more accurate preloaded_shared_events set.
        is_likely_shared = len(event.districts) > 1 or (
            "," in (event.district_partner or "")
        )

        if (
            not is_likely_shared
            and getattr(event, "attendance_detail", None)
            and getattr(event.attendance_detail, "total_students", None) is not None
        ):
            return event.attendance_detail.total_students

        # For non-virtual events, count actual student participations from the district
        from models.student import Student

        district_student_count = (
            db.session.query(EventStudentParticipation)
            .join(Student, EventStudentParticipation.student_id == Student.id)
            .join(School, Student.school_id == School.id)
            .filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status
                == "Attended",  # Only count attended students
                School.district_id == target_district_id,
            )
            .count()
        )
        return district_student_count


def get_current_school_year():
    """
    Returns the current school year in 'YYZZ' format (e.g., '2324' for 2023-24).
    If before August 1st, returns current academic year.
    If August 1st or later, returns next academic year.
    """
    today = datetime.now()
    if today.month < 8:  # Before August
        return f"{str(today.year-1)[-2:]}{str(today.year)[-2:]}"
    return f"{str(today.year)[-2:]}{str(today.year+1)[-2:]}"


def get_school_year_date_range(school_year):
    """
    Returns start and end dates for a school year.
    school_year format: '2324' for 2023-2024 school year
    Academic year runs from August 1st to July 31st.
    """
    year = int(school_year[:2]) + 2000
    start_date = datetime(year, 8, 1)  # August 1st of start year
    end_date = datetime(year + 1, 7, 31)  # July 31st of end year
    return start_date, end_date


def build_district_event_conditions(district, schools=None, district_mapping=None):
    """
    Build the SQLAlchemy OR condition list for finding events attributed to a district.

    Covers all attribution paths:
    - M2M FK (Event.districts.contains)
    - School FK (Event.school.in_)
    - School name fuzzy match in Event.title / Event.district_partner
    - District name ilike match in Event.district_partner
    - District short-name match (strips ' School District' suffix)
    - DISTRICT_MAPPING alias matches (both district_partner and districts.any)

    Args:
        district: District model instance.
        schools: Optional pre-fetched list of School objects for this district.
                 If None, district.schools (lazy relationship) is used.
        district_mapping: Optional pre-looked-up DISTRICT_MAPPING entry dict.
                          If None, looked up automatically by district.name.

    Returns:
        list: SQLAlchemy column expressions. Pass to db.or_(*result).

    Example::

        conditions = build_district_event_conditions(district, schools=schools,
                                                     district_mapping=mapping)
        events = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start, end),
            db.or_(*conditions),
        ).all()
    """
    if schools is None:
        schools = district.schools

    conditions = [
        Event.districts.contains(district),
        Event.school.in_([s.id for s in schools]),
        *[Event.title.ilike(f"%{s.name}%") for s in schools],
        *[Event.district_partner.ilike(f"%{s.name}%") for s in schools],
        Event.district_partner.ilike(f"%{district.name}%"),
        Event.district_partner.ilike(
            f"%{district.name.replace(' School District', '')}%"
        ),
    ]

    if district_mapping is None:
        district_mapping = next(
            (
                mapping
                for mapping in DISTRICT_MAPPING.values()
                if mapping["name"] == district.name
            ),
            None,
        )

    if district_mapping and "aliases" in district_mapping:
        for alias in district_mapping["aliases"]:
            conditions.append(Event.district_partner.ilike(f"%{alias}%"))
            conditions.append(Event.districts.any(District.name.ilike(f"%{alias}%")))

    return conditions


# --- Virtual Year Helper Functions ---


def get_current_virtual_year() -> str:
    """Determines the current virtual session year string (August 1st to July 31st)."""
    from datetime import date

    today = date.today()
    if today.month > 7 or (today.month == 7 and today.day == 31):  # After July 31st
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{start_year + 1}"


def get_virtual_year_dates(virtual_year: str) -> tuple:
    """Calculates the start and end dates for a given virtual session year string (8/1 to 7/31)."""
    try:
        start_year = int(virtual_year.split("-")[0])
        end_year = start_year + 1
        date_from = datetime(start_year, 8, 1, 0, 0, 0)  # August 1st start
        date_to = datetime(end_year, 7, 31, 23, 59, 59)  # July 31st end
        return date_from, date_to
    except (ValueError, IndexError):
        current_vy = get_current_virtual_year()
        return get_virtual_year_dates(current_vy)


def get_semester_dates(virtual_year: str, semester_type: str) -> tuple:
    """
    Calculates start and end dates for specific semesters.

    Args:
        virtual_year: The virtual year string (e.g. "2024-2025")
        semester_type: "Fall" or "Spring"

    Returns:
        tuple[datetime, datetime]: Start and end dates

    Note:
        Fall Semester: July 1 - Dec 31
        Spring Semester: Jan 1 - Jun 30
    """
    try:
        start_year = int(virtual_year.split("-")[0])
        end_year = start_year + 1

        if semester_type == "Fall":
            return (
                datetime(start_year, 7, 1, 0, 0, 0),
                datetime(start_year, 12, 31, 23, 59, 59),
            )
        elif semester_type == "Spring":
            return (
                datetime(end_year, 1, 1, 0, 0, 0),
                datetime(end_year, 6, 30, 23, 59, 59),
            )
        return get_virtual_year_dates(virtual_year)
    except (ValueError, IndexError):
        return get_virtual_year_dates(virtual_year)


def generate_school_year_options(start_cal_year=2018, end_cal_year=None) -> list:
    """Generates a list of school year strings for dropdowns."""
    from datetime import date

    if end_cal_year is None:
        end_cal_year = date.today().year + 1

    school_years = []
    for year in range(end_cal_year, start_cal_year - 1, -1):
        school_years.append(f"{year}-{year + 1}")
    return school_years


# --- Cache Utility Functions ---


def is_cache_valid(cache_record, max_age_hours=24):
    """
    Check if a cache record is still valid based on age.

    Args:
        cache_record: The cache record to check (must have last_updated attribute)
        max_age_hours: Maximum age in hours before cache is considered stale

    Returns:
        bool: True if cache is valid, False otherwise
    """
    if not cache_record:
        return False

    from datetime import timedelta, timezone

    # Convert to timezone-aware datetime if needed
    if cache_record.last_updated.tzinfo is None:
        last_updated = cache_record.last_updated.replace(tzinfo=timezone.utc)
    else:
        last_updated = cache_record.last_updated

    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)

    return (now - last_updated) < max_age


def generate_district_stats(school_year, host_filter="all"):
    """Generate district statistics for a school year"""
    import time

    fn_start = time.time()
    logger.info(
        "[generate_district_stats] START school_year=%s host_filter=%s",
        school_year,
        host_filter,
    )

    district_stats = {}
    start_date, end_date = get_school_year_date_range(school_year)

    # Only exclude connector sessions
    excluded_event_types = ["connector_session"]

    # Get all districts from the database
    all_districts = District.query.order_by(District.name).all()

    # Pre-load all schools for active districts
    from collections import defaultdict

    from models.event import EventTeacher
    from models.student import Student
    from models.teacher import Teacher
    from models.volunteer import EventParticipation

    active_district_ids = [
        next((d.id for d in all_districts if d.salesforce_id == sf_id), None)
        for sf_id, mapping in DISTRICT_MAPPING.items()
        if mapping["show"]
    ]
    active_district_ids = [d for d in active_district_ids if d]

    all_schools = School.query.filter(School.district_id.in_(active_district_ids)).all()
    schools_by_district = defaultdict(list)
    for school in all_schools:
        schools_by_district[school.district_id].append(school)

    # Process each district in our mapping
    district_count = sum(1 for _, m in DISTRICT_MAPPING.items() if m["show"])
    processed = 0
    for salesforce_id, mapping in DISTRICT_MAPPING.items():
        if not mapping["show"]:
            continue
        processed += 1
        d_start = time.time()

        # Find the primary district record
        primary_district = next(
            (d for d in all_districts if d.salesforce_id == salesforce_id), None
        )
        if not primary_district:
            logger.warning("Primary district %s not found in database", mapping["name"])
            continue

        # Get all schools for this district (from pre-loaded dict)
        schools = schools_by_district[primary_district.id]

        # Build the query conditions for this district
        district_partner_conditions = [
            Event.district_partner.ilike(f"%{school.name}%") for school in schools
        ]
        district_partner_conditions.append(
            Event.district_partner.ilike(f"%{primary_district.name}%")
        )

        # Add conditions for aliases - MODIFIED to handle both directions
        if "aliases" in mapping:
            for alias in mapping["aliases"]:
                district_partner_conditions.append(
                    Event.district_partner.ilike(f"%{alias}%")
                )
                # Also check the districts relationship for aliases
                district_partner_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Combine all conditions with OR instead of AND
        events_query = Event.query.filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            ~Event.type.in_([EventType(t) for t in excluded_event_types]),
            # Use OR between all district-related conditions
            db.or_(
                Event.districts.contains(primary_district),
                Event.school.in_([school.id for school in schools]),
                *district_partner_conditions,
            ),
        ).distinct()
        if host_filter == "prepkc":
            events_query = events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )

        events = events_query.all()
        event_ids = [event.id for event in events]
        logger.info(
            "[generate_district_stats] [%d/%d] %s — events query: %d events in %.2fs",
            processed,
            district_count,
            mapping["name"],
            len(events),
            time.time() - d_start,
        )

        # Debug log event types
        event_types_found = {}
        for event in events:
            event_type = event.type.value if event.type else "unknown"
            event_types_found[event_type] = event_types_found.get(event_type, 0) + 1

        # Bulk pre-load all participations for this district's events
        students_by_event = defaultdict(set)
        if event_ids:
            participation_rows = (
                db.session.query(
                    EventStudentParticipation.event_id,
                    EventStudentParticipation.student_id,
                )
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id.in_(event_ids),
                    EventStudentParticipation.status == "Attended",
                    School.district_id == primary_district.id,
                )
                .all()
            )
            for event_id, student_id in participation_rows:
                students_by_event[event_id].add(student_id)

        # Bulk pre-load all volunteer participations
        volunteers_by_event = defaultdict(list)
        if event_ids:
            volunteer_rows = (
                db.session.query(
                    EventParticipation.event_id,
                    EventParticipation.volunteer_id,
                    EventParticipation.delivery_hours,
                )
                .filter(
                    EventParticipation.event_id.in_(event_ids),
                    EventParticipation.status.in_(
                        ["Attended", "Completed", "Successfully Completed"]
                    ),
                )
                .all()
            )
            for event_id, vol_id, hours in volunteer_rows:
                volunteers_by_event[event_id].append((vol_id, hours or 0))

        # Bulk pre-load all teacher registrations for virtual events
        teachers_by_event = defaultdict(list)
        if event_ids:
            teacher_rows = (
                db.session.query(
                    EventTeacher.event_id,
                    EventTeacher.teacher_id,
                    EventTeacher.attendance_confirmed_at,
                )
                .join(Teacher, EventTeacher.teacher_id == Teacher.id)
                .filter(
                    EventTeacher.event_id.in_(event_ids),
                    Teacher.school_id.in_([s.id for s in schools]),
                )
                .all()
            )
            for event_id, teacher_id, confirmed_at in teacher_rows:
                teachers_by_event[event_id].append((teacher_id, confirmed_at))

        # Initialize stats dictionary
        stats = {
            "name": mapping["name"],
            "district_code": mapping["district_code"],
            "total_events": len(events),
            "total_students": 0,
            "total_in_person_students": 0,
            "total_virtual_students": 0,
            "unique_students": set(),  # Track unique student IDs
            "total_volunteers": 0,
            "unique_volunteers": set(),  # Track unique volunteer IDs
            "total_volunteer_hours": 0,
            "event_types": event_types_found,
            "schools_reached": set(),
            "monthly_breakdown": {},
            "career_clusters": set(),
        }

        # Monthly unique volunteer and student tracking
        monthly_unique_volunteers = {}
        monthly_unique_students = {}  # Track unique students per month

        # Calculate statistics
        for event in events:
            is_virtual = event.type in (
                EventType.VIRTUAL_SESSION,
                EventType.CONNECTOR_SESSION,
            )

            if is_virtual:
                teacher_entries = teachers_by_event.get(event.id, [])
                student_count = len(teacher_entries) * 25
                stats["total_virtual_students"] += student_count
            else:
                student_ids = students_by_event.get(event.id, set())
                student_count = len(student_ids)
                stats["total_in_person_students"] += student_count
                stats["unique_students"].update(student_ids)

            # Keep track of the overall total as well
            stats["total_students"] += student_count

            # Track volunteer participation with pre-loaded data
            vol_entries = volunteers_by_event.get(event.id, [])
            volunteer_count = len(vol_entries)
            volunteer_hours = sum(h for _, h in vol_entries)

            # Track unique volunteers
            for vol_id, _ in vol_entries:
                stats["unique_volunteers"].add(vol_id)

            stats["total_volunteers"] += volunteer_count
            stats["total_volunteer_hours"] += volunteer_hours

            # Track schools and career clusters
            if event.school:
                stats["schools_reached"].add(event.school)
            if event.series:
                stats["career_clusters"].add(event.series)

            # Monthly breakdown
            month = event.start_date.strftime("%B %Y")
            if month not in stats["monthly_breakdown"]:
                stats["monthly_breakdown"][month] = {
                    "events": 0,
                    "students": 0,
                    "volunteers": 0,
                    "volunteer_hours": 0,
                    "unique_volunteers": set(),  # Track unique volunteers by month
                    "unique_students": set(),  # Track unique students by month
                }

            # Update monthly stats
            stats["monthly_breakdown"][month]["events"] += 1
            stats["monthly_breakdown"][month]["students"] += student_count
            stats["monthly_breakdown"][month]["volunteers"] += volunteer_count
            stats["monthly_breakdown"][month]["volunteer_hours"] += volunteer_hours

            # Track unique volunteers by month
            for vol_id, _ in vol_entries:
                stats["monthly_breakdown"][month]["unique_volunteers"].add(vol_id)

            # Track unique students by month for this event - filter by district
            if not is_virtual:
                student_ids = students_by_event.get(event.id, set())
                stats["monthly_breakdown"][month]["unique_students"].update(student_ids)

        # Convert sets to counts and round hours
        stats["unique_student_count"] = len(
            stats["unique_students"]
        )  # Add unique student count
        del stats["unique_students"]  # Remove the set

        stats["unique_volunteer_count"] = len(stats["unique_volunteers"])
        del stats[
            "unique_volunteers"
        ]  # Remove the set to avoid JSON serialization issues

        stats["schools_reached"] = len(stats["schools_reached"])
        stats["career_clusters"] = len(stats["career_clusters"])
        stats["total_volunteer_hours"] = round(stats["total_volunteer_hours"], 1)

        # Process monthly data
        for month in stats["monthly_breakdown"]:
            # Convert unique volunteer sets to counts
            stats["monthly_breakdown"][month]["unique_volunteer_count"] = len(
                stats["monthly_breakdown"][month]["unique_volunteers"]
            )
            del stats["monthly_breakdown"][month]["unique_volunteers"]  # Remove the set

            # Convert unique student sets to counts
            stats["monthly_breakdown"][month]["unique_student_count"] = len(
                stats["monthly_breakdown"][month]["unique_students"]
            )
            del stats["monthly_breakdown"][month]["unique_students"]  # Remove the set

            # Round volunteer hours
            stats["monthly_breakdown"][month]["volunteer_hours"] = round(
                stats["monthly_breakdown"][month]["volunteer_hours"], 1
            )

        district_stats[mapping["name"]] = stats
        logger.info(
            "[generate_district_stats] [%d/%d] %s — DONE in %.2fs",
            processed,
            district_count,
            mapping["name"],
            time.time() - d_start,
        )

    logger.info("[generate_district_stats] COMPLETE in %.2fs", time.time() - fn_start)
    return district_stats


def update_event_districts(event, district_names):
    """Helper function to update event district relationships"""
    # Clear existing relationships
    event.districts = []

    for name in district_names:
        # Try exact match first
        district = District.query.filter(District.name.ilike(name)).first()
        if district and district not in event.districts:
            event.districts.append(district)

        # Update text field for backward compatibility
        if event.district_partner:
            current_districts = set(
                d.strip() for d in event.district_partner.split(",")
            )
            current_districts.add(name)
            event.district_partner = ", ".join(current_districts)


def get_district_filtered_query(base_query, district_field):
    """
    Apply district scoping filter to query.

    Args:
        base_query: SQLAlchemy query object
        district_field: The field to filter on (e.g., District.name)

    Returns:
        Filtered query based on user's scope
    """
    if current_user.scope_type == "global":
        return base_query

    if current_user.scope_type == "district" and current_user.allowed_districts:
        allowed = (
            json.loads(current_user.allowed_districts)
            if isinstance(current_user.allowed_districts, str)
            else current_user.allowed_districts
        )
        return base_query.filter(district_field.in_(allowed))

    return base_query.filter(False)  # No access


from routes.reports.breakdown_helpers import calculate_program_breakdown
