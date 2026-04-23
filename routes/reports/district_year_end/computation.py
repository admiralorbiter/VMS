"""
District Year-End computation functions.

Extracted from district_year_end.py as part of TD-020.
Contains:
  - generate_schools_by_level_data: school grouping for reports
  - cache_district_stats_with_events: caching logic
  - calculate_enhanced_district_stats: detailed stat breakdowns
  - convert_school_year_format / convert_academic_year_format: format helpers
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from models import db
from models.district_model import District
from models.event import (
    Event,
    EventAttendance,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.organization import VolunteerOrganization
from models.reports import DistrictYearEndReport
from models.school_model import School
from models.student import Student
from models.volunteer import EventParticipation
from routes.reports.common import (
    DISTRICT_MAPPING,
    generate_district_stats,
    get_district_student_count_for_event,
    get_school_year_date_range,
)


def generate_schools_by_level_data(district, events):
    """Generate schools data organized by level (High, Middle, Elementary, Other)

    This function ensures ALL schools in the district are shown, even if they have no events.
    Schools without events will appear with zero counts.
    """
    from models.school_model import School

    # Initialize the structure
    schools_by_level = {
        "High": [],
        "Middle": [],
        "Elementary": [],
        None: [],  # For schools with no level or 'Other'
    }

    # Get all schools in the district
    district_schools = School.query.filter_by(district_id=district.id).all()

    # Create a mapping of school_id to school for quick lookup
    school_map = {school.id: school for school in district_schools}

    # Also create a mapping by school name for events that reference schools by name
    school_name_map = {school.name.lower(): school for school in district_schools}

    # Initialize school data for ALL schools in the district (ensures all schools are shown)
    school_events = {}
    for school in district_schools:
        school_events[school.id] = {
            "school": school,
            "events": [],
            "total_students": 0,
            "total_volunteers": 0,
            "total_volunteer_hours": 0,
            "unique_volunteers": set(),
        }

    # Process events and associate them with schools
    for event in events:
        school = None

        # Try to find school by event.school (if it's a school ID)
        if hasattr(event, "school") and event.school:
            if isinstance(event.school, str):
                school = school_map.get(event.school)
            else:
                # If it's already a school object
                school = event.school

        # Also try using the school_obj relationship if available
        if not school and hasattr(event, "school_obj") and event.school_obj:
            school = event.school_obj

        # If not found, try to match by event title or location
        if not school:
            event_text = f"{event.title} {getattr(event, 'location', '')}".lower()

            # Try exact school name matches first
            for school_name, school_obj in school_name_map.items():
                if school_name in event_text:
                    school = school_obj
                    break

            # If no exact match, try partial matching with common school name patterns
            if not school:
                for school_obj in district_schools:
                    school_name_parts = school_obj.name.lower().split()
                    # Check if any significant part of the school name appears in the event
                    for part in school_name_parts:
                        if (
                            len(part) > 3 and part in event_text
                        ):  # Only check meaningful parts
                            school = school_obj
                            break
                    if school:
                        break

        # If still not found, try to match by district partner field (if available)
        if not school and hasattr(event, "district_partner") and event.district_partner:
            event_text = event.district_partner.lower()

            # Try exact school name matches first
            for school_name, school_obj in school_name_map.items():
                if school_name in event_text:
                    school = school_obj
                    break

            # If no exact match, try partial matching
            if not school:
                for school_obj in district_schools:
                    school_name_parts = school_obj.name.lower().split()
                    for part in school_name_parts:
                        if len(part) > 3 and part in event_text:
                            school = school_obj
                            break
                    if school:
                        break

        # If we found a school and it's in our district, add the event to that school
        if school and school.id in school_events:
            # Calculate or get event data - handle both cached dictionaries and fresh Event objects
            volunteer_participations = []
            event_id = getattr(event, "id", None)

            if hasattr(event, "students") and hasattr(event, "volunteers"):
                # This is cached data (dictionary-like object)
                students = getattr(event, "students", 0)
                volunteers = getattr(event, "volunteers", 0)
                volunteer_hours = getattr(event, "volunteer_hours", 0)

                # For cached data, we need to query the database to get unique volunteers
                if event_id:
                    volunteer_participations = EventParticipation.query.filter(
                        EventParticipation.event_id == event_id,
                        EventParticipation.status.in_(
                            ["Attended", "Completed", "Successfully Completed"]
                        ),
                    ).all()
            else:
                # This is a fresh Event object - calculate the values
                students = get_district_student_count_for_event(event, district.id)
                volunteer_participations = [
                    p
                    for p in event.volunteer_participations
                    if p.status in ["Attended", "Completed", "Successfully Completed"]
                ]
                volunteers = len(volunteer_participations)
                volunteer_hours = sum(
                    p.delivery_hours or 0 for p in volunteer_participations
                )

            # Add event data
            event_data = {
                "id": event_id,
                "title": getattr(event, "title", ""),
                "date": (
                    event.start_date.strftime("%m/%d/%Y")
                    if hasattr(event, "start_date")
                    else ""
                ),
                "time": (
                    event.start_date.strftime("%I:%M %p")
                    if hasattr(event, "start_date")
                    else ""
                ),
                "type": (
                    event.type.value
                    if hasattr(event, "type") and event.type
                    else "Unknown"
                ),
                "students": students,
                "volunteers": volunteers,
                "volunteer_hours": volunteer_hours,
            }

            school_events[school.id]["events"].append(event_data)
            school_events[school.id]["total_students"] += event_data["students"]
            school_events[school.id]["total_volunteers"] += event_data["volunteers"]
            school_events[school.id]["total_volunteer_hours"] += event_data[
                "volunteer_hours"
            ]

            # Track unique volunteers for this school (works for both cached and fresh data)
            if volunteer_participations:
                for p in volunteer_participations:
                    school_events[school.id]["unique_volunteers"].add(p.volunteer_id)

    # Organize ALL schools by level (including those with no events)
    for school_id, school_data in school_events.items():
        school = school_data["school"]
        school_info = {
            "name": school.name,
            "events": school_data["events"],
            "total_students": school_data["total_students"],
            "total_volunteers": school_data["total_volunteers"],
            "total_volunteer_hours": school_data["total_volunteer_hours"],
            "unique_volunteer_count": len(school_data["unique_volunteers"]),
        }

        # Categorize by level
        level = school.level
        if level in ["High", "Middle", "Elementary"]:
            schools_by_level[level].append(school_info)
        else:
            schools_by_level[None].append(school_info)

    # Sort schools within each level by name
    for level in schools_by_level:
        schools_by_level[level].sort(key=lambda x: x["name"])

    return schools_by_level


def cache_district_stats_with_events(school_year, district_stats, host_filter="all"):
    """Cache district stats and events data for all districts"""
    import time

    max_retries = 3
    retry_delay = 0.5  # seconds

    total_districts = len(district_stats)
    processed = 0
    start_time = time.time()

    for district_name, stats in district_stats.items():
        district_start = time.time()
        processed += 1
        district = District.query.filter_by(name=district_name).first()
        if not district:
            continue

        # Get or create report
        report = DistrictYearEndReport.query.filter_by(
            district_id=district.id, school_year=school_year, host_filter=host_filter
        ).first()

        if not report:
            report = DistrictYearEndReport(
                district_id=district.id,
                school_year=school_year,
                host_filter=host_filter,
                report_data={},  # Initialize with empty dict to satisfy NOT NULL constraint
            )
            db.session.add(report)

        # Generate events data (mostly for monthly breakdown)
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ["connector_session"]

        # Build query conditions (same as generate_district_stats)
        query_conditions = [
            Event.districts.contains(district),
            Event.school.in_([school.id for school in district.schools]),
            *[Event.title.ilike(f"%{school.name}%") for school in district.schools],
            *[
                Event.district_partner.ilike(f"%{school.name}%")
                for school in district.schools
            ],
            Event.district_partner.ilike(f"%{district.name}%"),
            Event.district_partner.ilike(
                f"%{district.name.replace(' School District', '')}%"
            ),
        ]
        district_mapping = next(
            (
                mapping
                for salesforce_id, mapping in DISTRICT_MAPPING.items()
                if mapping["name"] == district_name
            ),
            None,
        )
        if district_mapping and "aliases" in district_mapping:
            for alias in district_mapping["aliases"]:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Fetch events
        events_query = (
            Event.query.outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                ~Event.type.in_([EventType(t) for t in excluded_event_types]),
                db.or_(*query_conditions),
            )
            .order_by(Event.start_date)
        )

        # Apply host filter if specified
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

        # Fetch student participations for these events
        student_participations = EventStudentParticipation.query.filter(
            EventStudentParticipation.event_id.in_(event_ids)
        ).all()

        # Set to track unique volunteer and student IDs for the whole district
        unique_volunteers = set()
        unique_students = set()  # Track unique student IDs

        # Organize events by month
        events_by_month = {}
        for event in events:
            month = event.start_date.strftime("%B %Y")
            if month not in events_by_month:
                events_by_month[month] = {
                    "events": [],
                    "total_students": 0,
                    "total_volunteers": 0,
                    "total_volunteer_hours": 0,
                    "unique_volunteers": set(),
                    "volunteer_engagement_count": 0,
                    "unique_students": set(),  # Add set for monthly unique students
                }

            # Use participant_count for virtual sessions, otherwise use attendance logic
            student_count = get_district_student_count_for_event(event, district.id)

            volunteer_participations = [
                p
                for p in event.volunteer_participations
                if p.status in ["Attended", "Completed", "Successfully Completed"]
            ]
            volunteer_count = len(volunteer_participations)
            volunteer_hours = sum(
                p.delivery_hours or 0 for p in volunteer_participations
            )

            event_date = datetime.fromisoformat(event.start_date.isoformat())
            events_by_month[month]["events"].append(
                {
                    "id": event.id,
                    "title": event.title,
                    "date": event_date.strftime("%m/%d/%Y"),
                    "time": event_date.strftime("%I:%M %p"),
                    "type": event.type.value if event.type else None,
                    "location": event.location or "",
                    "student_count": student_count,
                    "volunteer_count": volunteer_count,
                    "volunteer_hours": volunteer_hours,
                    "students": student_count,
                    "volunteers": volunteer_count,
                }
            )
            events_by_month[month]["total_students"] += student_count
            events_by_month[month]["total_volunteers"] += volunteer_count
            events_by_month[month]["total_volunteer_hours"] += volunteer_hours
            events_by_month[month]["volunteer_engagement_count"] += volunteer_count

            # Track unique volunteers (overall and monthly)
            for p in volunteer_participations:
                unique_volunteers.add(p.volunteer_id)
                events_by_month[month]["unique_volunteers"].add(p.volunteer_id)

            # Track unique students (overall and monthly) - filter by district
            if event.type == EventType.VIRTUAL_SESSION:
                # For virtual events, we can't track individual unique students
                # since the count is calculated from teachers
                pass
            else:
                # Get student IDs for this specific district and event
                district_student_ids = (
                    db.session.query(EventStudentParticipation.student_id)
                    .join(Student, EventStudentParticipation.student_id == Student.id)
                    .join(School, Student.school_id == School.id)
                    .filter(
                        EventStudentParticipation.event_id == event.id,
                        EventStudentParticipation.status == "Attended",
                        School.district_id == district.id,
                    )
                    .all()
                )
                event_student_ids = {
                    student_id[0] for student_id in district_student_ids
                }
                unique_students.update(event_student_ids)
                events_by_month[month]["unique_students"].update(event_student_ids)

        # Process the events data for storage
        for month, data in events_by_month.items():
            data["unique_volunteer_count"] = len(data["unique_volunteers"])
            data["unique_volunteers"] = list(
                data["unique_volunteers"]
            )  # Convert set to list for JSON
            data["volunteer_engagements"] = data["volunteer_engagement_count"]
            data["unique_student_count"] = len(
                data["unique_students"]
            )  # Calculate monthly unique student count
            data["unique_students"] = list(
                data["unique_students"]
            )  # Convert set to list for JSON

        # For enhanced stats, we need to include connector_session events
        # Query connector_session events separately and combine
        connector_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.CONNECTOR_SESSION,
            db.or_(*query_conditions),
        ).order_by(Event.start_date)
        if host_filter == "prepkc":
            connector_events_query = connector_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        connector_events = connector_events_query.all()

        # Combine events for enhanced stats calculation (includes connector_session)
        all_events_for_stats = list(events) + list(connector_events)

        # Calculate enhanced stats for this district
        enhanced_stats = calculate_enhanced_district_stats(
            all_events_for_stats, district.id
        )

        # Calculate program breakdown
        from routes.reports.common import calculate_program_breakdown

        program_breakdown = calculate_program_breakdown(
            district.id, school_year, host_filter=host_filter
        )

        # Update stats to include enhanced data
        enhanced_stats_dict = {
            "total_events": enhanced_stats["events"]["total"],
            "total_in_person_students": enhanced_stats["students"]["in_person"],
            "total_virtual_students": enhanced_stats["students"]["virtual"],
            "total_volunteers": enhanced_stats["volunteers"]["total"],
            "total_volunteer_hours": enhanced_stats["volunteers"]["hours_total"],
            "event_types": enhanced_stats["event_types"],
            # Add enhanced breakdown data
            "enhanced": enhanced_stats,
            # Add program breakdown
            "program_breakdown": program_breakdown,
        }

        # Merge with existing stats (keep any additional fields from generate_district_stats)
        stats.update(enhanced_stats_dict)

        # Cache both the enhanced stats and events data
        report.report_data = stats
        report.events_data = {
            "events_by_month": events_by_month,
            "total_events": len(events),
            "unique_volunteer_count": len(unique_volunteers),
            "unique_student_count": len(
                unique_students
            ),  # Store overall unique student count
        }

        # Commit after each district to avoid long-running transactions
        for attempt in range(max_retries):
            try:
                db.session.commit()
                district_time = time.time() - district_start
                elapsed = time.time() - start_time
                avg_time = elapsed / processed if processed > 0 else 0
                remaining = avg_time * (total_districts - processed)
                logger.debug(
                    "[%d/%d] Cached %s in %.2fs (avg: %.2fs, est. remaining: %.1fs)",
                    processed, total_districts, district_name, district_time, avg_time, remaining
                )
                break
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    db.session.rollback()
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    db.session.rollback()
                    logger.error("Error caching district %s: %s", district_name, str(e))
                    raise


def calculate_enhanced_district_stats(events, district_id):
    """
    Calculate comprehensive district statistics with detailed breakdowns.

    Returns a dictionary with total stats and breakdowns by in-person vs virtual sessions.
    Each major category includes detailed metrics for volunteers, organizations, and virtual-specific data.
    """
    from models.organization import VolunteerOrganization
    from models.school_model import School
    from models.student import Student

    # Initialize comprehensive counters
    stats = {
        "events": {"total": 0, "in_person": 0, "virtual": 0},
        "students": {
            "total": 0,
            "in_person": 0,
            "virtual": 0,
            "unique_total": 0,
            "unique_in_person": 0,
            "unique_virtual": 0,
        },
        "volunteers": {
            "total": 0,
            "in_person": 0,
            "virtual": 0,
            "unique_total": 0,
            "unique_in_person": 0,
            "unique_virtual": 0,
            "hours_total": 0,
            "hours_in_person": 0,
            "hours_virtual": 0,
        },
        "organizations": {
            "total": 0,
            "in_person": 0,
            "virtual": 0,
            "unique_total": 0,
            "unique_in_person": 0,
            "unique_virtual": 0,
            "volunteer_hours_total": 0,
            "volunteer_hours_in_person": 0,
            "volunteer_hours_virtual": 0,
        },
        "virtual_sessions": {
            "classrooms_reached": 0,
            "unique_teachers": 0,
            "confirmed_teachers": 0,
            "registered_teachers": 0,
        },
        "event_types": {},
        "event_types_by_format": {"in_person": {}, "virtual": {}},
    }

    # Track unique IDs and enhanced metrics
    unique_volunteers_total = set()
    unique_volunteers_in_person = set()
    unique_volunteers_virtual = set()
    unique_students_total = set()
    unique_students_in_person = set()
    unique_students_virtual = set()
    unique_orgs_total = set()
    unique_orgs_in_person = set()
    unique_orgs_virtual = set()
    unique_teachers_virtual = set()

    # Track organization volunteer hours
    org_hours_in_person = {}
    org_hours_virtual = {}
    org_hours_total = {}

    # Get district schools for filtering teachers
    from models.school_model import School

    district_schools = School.query.filter_by(district_id=district_id).all()
    district_school_ids = [school.id for school in district_schools]

    for event in events:
        # Include both VIRTUAL_SESSION and CONNECTOR_SESSION as virtual
        is_virtual = event.type in [
            EventType.VIRTUAL_SESSION,
            EventType.CONNECTOR_SESSION,
        ]

        # Count events
        stats["events"]["total"] += 1
        if is_virtual:
            stats["events"]["virtual"] += 1
        else:
            stats["events"]["in_person"] += 1

        # Count event types
        event_type = event.type.value if event.type else "Unknown"
        stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1

        # Count event types by format
        format_key = "virtual" if is_virtual else "in_person"
        stats["event_types_by_format"][format_key][event_type] = (
            stats["event_types_by_format"][format_key].get(event_type, 0) + 1
        )

        # Get student count for this district
        # For virtual/connector sessions, we need to use confirmed teachers from district only
        if is_virtual:
            # Count confirmed teachers from this district
            confirmed_teacher_regs = [
                reg
                for reg in event.teacher_registrations
                if reg.attendance_confirmed_at is not None
            ]
            # Filter by district: only count teachers from this district's schools
            district_confirmed_teachers = [
                reg
                for reg in confirmed_teacher_regs
                if reg.teacher.school_id
                and reg.teacher.school_id in district_school_ids
            ]
            # Estimate students: confirmed teachers Ã— 25
            student_count = len(district_confirmed_teachers) * 25
        else:
            student_count = get_district_student_count_for_event(event, district_id)

        stats["students"]["total"] += student_count
        if is_virtual:
            stats["students"]["virtual"] += student_count
        else:
            stats["students"]["in_person"] += student_count

        # Get volunteer participations
        volunteer_participations = [
            p
            for p in event.volunteer_participations
            if p.status in ["Attended", "Completed", "Successfully Completed"]
        ]

        volunteer_count = len(volunteer_participations)
        stats["volunteers"]["total"] += volunteer_count
        if is_virtual:
            stats["volunteers"]["virtual"] += volunteer_count
        else:
            stats["volunteers"]["in_person"] += volunteer_count

        # Calculate volunteer hours
        volunteer_hours = sum(p.delivery_hours or 0 for p in volunteer_participations)
        stats["volunteers"]["hours_total"] += volunteer_hours
        if is_virtual:
            stats["volunteers"]["hours_virtual"] += volunteer_hours
        else:
            stats["volunteers"]["hours_in_person"] += volunteer_hours

        # Track unique volunteers
        event_volunteer_ids = set()
        for p in volunteer_participations:
            unique_volunteers_total.add(p.volunteer_id)
            event_volunteer_ids.add(p.volunteer_id)
            if is_virtual:
                unique_volunteers_virtual.add(p.volunteer_id)
            else:
                unique_volunteers_in_person.add(p.volunteer_id)

        # Track unique students (for non-virtual events)
        if not is_virtual:
            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_students_total.update(event_student_ids)
            unique_students_in_person.update(event_student_ids)

        # Track unique organizations and their volunteer hours
        if event_volunteer_ids:
            event_org_ids = (
                db.session.query(VolunteerOrganization.organization_id)
                .filter(VolunteerOrganization.volunteer_id.in_(event_volunteer_ids))
                .distinct()
                .all()
            )
            event_org_ids = {org_id[0] for org_id in event_org_ids}
            unique_orgs_total.update(event_org_ids)

            # Track organization volunteer hours
            for org_id in event_org_ids:
                # Calculate hours for this organization in this event
                org_volunteer_ids = (
                    db.session.query(VolunteerOrganization.volunteer_id)
                    .filter(VolunteerOrganization.organization_id == org_id)
                    .filter(VolunteerOrganization.volunteer_id.in_(event_volunteer_ids))
                    .all()
                )
                org_volunteer_ids = {vol_id[0] for vol_id in org_volunteer_ids}

                org_event_hours = sum(
                    p.delivery_hours or 0
                    for p in volunteer_participations
                    if p.volunteer_id in org_volunteer_ids
                )

                # Add to organization hour tracking
                org_hours_total[org_id] = (
                    org_hours_total.get(org_id, 0) + org_event_hours
                )

                if is_virtual:
                    unique_orgs_virtual.update(event_org_ids)
                    org_hours_virtual[org_id] = (
                        org_hours_virtual.get(org_id, 0) + org_event_hours
                    )
                else:
                    unique_orgs_in_person.update(event_org_ids)
                    org_hours_in_person[org_id] = (
                        org_hours_in_person.get(org_id, 0) + org_event_hours
                    )

        # Track virtual session specific metrics
        if is_virtual:
            # Count teachers for virtual sessions (all registered)
            teacher_registrations = event.teacher_registrations
            stats["virtual_sessions"]["registered_teachers"] += len(
                teacher_registrations
            )

            # Count confirmed teachers (those with attendance confirmed) - ALL teachers
            confirmed_teacher_regs = [
                t
                for t in teacher_registrations
                if t.attendance_confirmed_at is not None
            ]

            # Filter by district: only count teachers from this district's schools
            district_confirmed_teachers = [
                reg
                for reg in confirmed_teacher_regs
                if reg.teacher.school_id
                and reg.teacher.school_id in district_school_ids
            ]

            stats["virtual_sessions"]["confirmed_teachers"] += len(
                district_confirmed_teachers
            )

            # Track unique teachers (only from district, only confirmed)
            for teacher_reg in district_confirmed_teachers:
                unique_teachers_virtual.add(teacher_reg.teacher_id)

            # Count classrooms reached (assuming each teacher represents a classroom)
            # Use confirmed teachers from district only
            stats["virtual_sessions"]["classrooms_reached"] += len(
                district_confirmed_teachers
            )

    # Set unique counts
    stats["volunteers"]["unique_total"] = len(unique_volunteers_total)
    stats["volunteers"]["unique_in_person"] = len(unique_volunteers_in_person)
    stats["volunteers"]["unique_virtual"] = len(unique_volunteers_virtual)

    stats["students"]["unique_total"] = len(unique_students_total)
    stats["students"]["unique_in_person"] = len(unique_students_in_person)
    stats["students"]["unique_virtual"] = len(unique_students_virtual)

    stats["organizations"]["unique_total"] = len(unique_orgs_total)
    stats["organizations"]["unique_in_person"] = len(unique_orgs_in_person)
    stats["organizations"]["unique_virtual"] = len(unique_orgs_virtual)

    # Calculate organization volunteer hours totals
    stats["organizations"]["volunteer_hours_total"] = sum(org_hours_total.values())
    stats["organizations"]["volunteer_hours_in_person"] = sum(
        org_hours_in_person.values()
    )
    stats["organizations"]["volunteer_hours_virtual"] = sum(org_hours_virtual.values())

    # Set virtual session unique teacher count
    stats["virtual_sessions"]["unique_teachers"] = len(unique_teachers_virtual)

    # Calculate percentages
    def add_percentages(category_stats):
        total = category_stats["total"]
        if total > 0:
            category_stats["in_person_pct"] = round(
                (category_stats["in_person"] / total) * 100, 1
            )
            category_stats["virtual_pct"] = round(
                (category_stats["virtual"] / total) * 100, 1
            )
        else:
            category_stats["in_person_pct"] = 0
            category_stats["virtual_pct"] = 0

    add_percentages(stats["events"])
    add_percentages(stats["students"])

    # Add percentages for volunteers (both engagements and hours)
    add_percentages(stats["volunteers"])  # This handles total/in_person/virtual
    # Add percentages for volunteer hours
    total_hours = stats["volunteers"]["hours_total"]
    if total_hours > 0:
        stats["volunteers"]["hours_in_person_pct"] = round(
            (stats["volunteers"]["hours_in_person"] / total_hours) * 100, 1
        )
        stats["volunteers"]["hours_virtual_pct"] = round(
            (stats["volunteers"]["hours_virtual"] / total_hours) * 100, 1
        )
    else:
        stats["volunteers"]["hours_in_person_pct"] = 0
        stats["volunteers"]["hours_virtual_pct"] = 0

    # Add percentages for organizations (unique counts)
    total_orgs = stats["organizations"]["unique_total"]
    if total_orgs > 0:
        stats["organizations"]["unique_in_person_pct"] = round(
            (stats["organizations"]["unique_in_person"] / total_orgs) * 100, 1
        )
        stats["organizations"]["unique_virtual_pct"] = round(
            (stats["organizations"]["unique_virtual"] / total_orgs) * 100, 1
        )
    else:
        stats["organizations"]["unique_in_person_pct"] = 0
        stats["organizations"]["unique_virtual_pct"] = 0

    # Add percentages for organization volunteer hours
    total_org_hours = stats["organizations"]["volunteer_hours_total"]
    if total_org_hours > 0:
        stats["organizations"]["volunteer_hours_in_person_pct"] = round(
            (stats["organizations"]["volunteer_hours_in_person"] / total_org_hours)
            * 100,
            1,
        )
        stats["organizations"]["volunteer_hours_virtual_pct"] = round(
            (stats["organizations"]["volunteer_hours_virtual"] / total_org_hours) * 100,
            1,
        )
    else:
        stats["organizations"]["volunteer_hours_in_person_pct"] = 0
        stats["organizations"]["volunteer_hours_virtual_pct"] = 0

    return stats


def convert_school_year_format(school_year_yyzz):
    """
    Convert school year from 'YYZZ' format to 'YYYY-YYYY' format.
    e.g., '2425' -> '2024-2025'
    """
    year = int(school_year_yyzz[:2]) + 2000
    return f"{year}-{year + 1}"


def convert_academic_year_format(academic_year):
    """
    Convert academic year from 'YYYY-YYYY' format to 'YYZZ' format.
    e.g., '2024-2025' -> '2425'
    """
    start_year = int(academic_year.split("-")[0])
    return f"{str(start_year)[-2:]}{str(start_year + 1)[-2:]}"
