"""
Data processing and computation functions for virtual session reports.

Contains filtering, summarization, sorting/pagination, and the main
compute functions that produce session data from the database.
"""

from datetime import datetime

from models.contact import LocalStatusEnum
from models.event import Event, EventType
from models.google_sheet import GoogleSheet
from models.school_model import School
from models.volunteer import Volunteer
from routes.reports.common import (
    generate_school_year_options,
    get_school_year_date_range,
    get_virtual_year_dates,
)
from services.academic_year_service import get_school_year_dates  # noqa: F401
from services.virtual_computation_service import (
    apply_runtime_filters,
    apply_sorting_and_pagination,
    calculate_summaries_from_sessions,
)
from services.virtual_computation_service import (
    district_name_matches as _district_name_matches,
)
from services.virtual_computation_service import get_google_sheet_url
from services.virtual_computation_service import (
    get_primary_org_name as _get_primary_org_name_for_volunteer,
)
from services.virtual_computation_service import (
    is_teacher_attended,
    resolve_teacher_district,
)


def compute_virtual_session_data(virtual_year, date_from, date_to, filters):
    """
    Compute virtual session data from database.

    Args:
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date
        filters: Filter criteria

    Returns:
        Tuple of (session_data, district_summaries, overall_summary, filter_options)
    """
    # Base query for virtual session events
    from sqlalchemy.orm import selectinload

    from models import eagerload_event_bundle
    from models.organization import VolunteerOrganization

    base_query = (
        eagerload_event_bundle(Event.query)
        .options(
            selectinload(Event.volunteers)
            .selectinload(Volunteer.volunteer_organizations)
            .selectinload(VolunteerOrganization.organization)
        )
        .filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        )
    )

    # Apply database-level filters
    if filters.get("career_cluster"):
        base_query = base_query.filter(
            Event.series.ilike(f'%{filters["career_cluster"]}%')
        )

    if filters.get("status"):
        base_query = base_query.filter(Event.status == filters["status"])

    # Get all events
    events = base_query.order_by(Event.start_date.desc()).all()

    # First pass: collect all districts, schools, career clusters, and statuses from raw events
    all_districts = set()
    all_schools = set()
    all_career_clusters = set()
    all_statuses = set()

    for event in events:
        # Collect districts from events
        if event.districts:
            all_districts.add(event.districts[0].name)
        elif event.district_partner:
            all_districts.add(event.district_partner)

        # Collect career clusters and statuses
        if event.series:
            all_career_clusters.add(event.series)
        if event.status:
            all_statuses.add(event.status.value)

        # Collect schools and their districts from teacher registrations
        for teacher_reg in event.teacher_registrations:
            teacher = teacher_reg.teacher
            if teacher and teacher.school_id:
                school = School.query.get(teacher.school_id)
                if school:
                    all_schools.add(school.name)
                    # Also add the school's district if available
                    if hasattr(school, "district") and school.district:
                        all_districts.add(school.district.name)

    # Build session data
    session_data = []

    for event in events:
        # Get all teacher registrations for this event
        teacher_registrations = event.teacher_registrations

        if teacher_registrations:
            # Create a row for each teacher registration
            for teacher_reg in teacher_registrations:
                teacher = teacher_reg.teacher

                # Get school information
                school = None
                school_name = ""
                school_level = ""

                if teacher:
                    if hasattr(teacher, "school_obj") and teacher.school_obj:
                        school = teacher.school_obj
                        school_name = school.name
                        school_level = getattr(school, "level", "")
                    elif teacher.school_id:
                        school = School.query.get(teacher.school_id)
                        if school:
                            school_name = school.name
                            school_level = getattr(school, "level", "")

                # Determine district from multiple sources
                # Prioritize teacher's school district over event's district
                district_name = None
                if school and hasattr(school, "district") and school.district:
                    # Teacher's school district takes priority
                    district_name = school.district.name
                elif event.districts:
                    district_name = event.districts[0].name
                elif event.district_partner:
                    district_name = event.district_partner
                else:
                    district_name = "Unknown District"

                # Apply district filter if specified
                if filters.get("district") and district_name != filters["district"]:
                    continue

                # Apply school filter if specified
                if (
                    filters.get("school")
                    and school_name
                    and filters["school"].lower() not in school_name.lower()
                ):
                    continue

                session_data.append(
                    {
                        "event_id": event.id,
                        # Use the event's status for session-level filtering (completed/simulcast),
                        # not the individual teacher registration status
                        "status": (
                            event.status.value if getattr(event, "status", None) else ""
                        )
                        or "registered",
                        "date": (
                            event.start_date.strftime("%m/%d/%y")
                            if event.start_date
                            else ""
                        ),
                        "time": (
                            event.start_date.strftime("%I:%M %p")
                            if event.start_date
                            else ""
                        ),
                        "session_type": event.additional_information or "",
                        "teacher_name": (
                            f"{teacher.first_name} {teacher.last_name}"
                            if teacher
                            else ""
                        ),
                        "teacher_id": teacher.id if teacher else None,
                        "school_name": school_name,
                        "school_level": school_level,
                        "district": district_name,
                        "session_title": event.title,
                        "presenter": (
                            ", ".join([v.full_name for v in event.volunteers])
                            if event.volunteers
                            else ""
                        ),
                        "presenter_organization": (
                            ", ".join(
                                [
                                    _get_primary_org_name_for_volunteer(v)
                                    or "Independent"
                                    for v in event.volunteers
                                ]
                            )
                            if event.volunteers
                            else ""
                        ),
                        "presenter_data": (
                            [
                                {
                                    "id": v.id,
                                    "name": v.full_name,
                                    "is_people_of_color": v.is_people_of_color,
                                    "organization_name": v.organization_name,
                                    "organizations": (
                                        [org.name for org in v.organizations]
                                        if v.organizations
                                        else []
                                    ),
                                    "is_local": getattr(v, "local_status", None)
                                    == LocalStatusEnum.local,
                                }
                                for v in event.volunteers
                            ]
                            if event.volunteers
                            else []
                        ),
                        "topic_theme": event.series or "",
                        "session_link": event.registration_link or "",
                        "session_id": event.session_id or "",
                        "participant_count": event.participant_count or 0,
                        "duration": event.duration or 0,
                        "is_simulcast": teacher_reg.is_simulcast,
                    }
                )

        else:
            # Event with no teacher registrations - show the event itself
            district_name = None
            if event.districts:
                district_name = event.districts[0].name
            elif event.district_partner:
                district_name = event.district_partner
            else:
                district_name = "Unknown District"

            # Apply district filter if specified
            if filters.get("district") and district_name != filters["district"]:
                continue

            session_data.append(
                {
                    "event_id": event.id,
                    "status": event.status.value if event.status else "",
                    "date": (
                        event.start_date.strftime("%m/%d/%y")
                        if event.start_date
                        else ""
                    ),
                    "time": (
                        event.start_date.strftime("%I:%M %p")
                        if event.start_date
                        else ""
                    ),
                    "session_type": event.additional_information or "",
                    "teacher_name": "",
                    "teacher_id": None,
                    "school_name": "",
                    "school_level": "",
                    "district": district_name,
                    "session_title": event.title,
                    "presenter": (
                        ", ".join([v.full_name for v in event.volunteers])
                        if event.volunteers
                        else ""
                    ),
                    "presenter_organization": (
                        ", ".join(
                            [
                                _get_primary_org_name_for_volunteer(v) or "Independent"
                                for v in event.volunteers
                            ]
                        )
                        if event.volunteers
                        else ""
                    ),
                    "presenter_data": (
                        [
                            {
                                "id": v.id,
                                "name": v.full_name,
                                "is_people_of_color": v.is_people_of_color,
                                "organization_name": v.organization_name,
                                "organizations": (
                                    [org.name for org in v.organizations]
                                    if v.organizations
                                    else []
                                ),
                                "is_local": getattr(v, "local_status", None)
                                == LocalStatusEnum.local,
                            }
                            for v in event.volunteers
                        ]
                        if event.volunteers
                        else []
                    ),
                    "topic_theme": event.series or "",
                    "session_link": event.registration_link or "",
                    "session_id": event.session_id or "",
                    "participant_count": event.participant_count or 0,
                    "duration": event.duration or 0,
                    "is_simulcast": False,
                }
            )

    # Calculate summaries
    show_all_districts = filters.get("show_all_districts", False)
    district_summaries, overall_summary = calculate_summaries_from_sessions(
        session_data, show_all_districts
    )

    # Ensure all districts with data are included in summaries
    # Only create empty summaries for districts that appear in all_districts but have no completed sessions
    # This allows showing all districts that exist, even if they have zero completed sessions
    for district_name in all_districts:
        if district_name not in district_summaries:
            # Only create empty summary if we want to show all districts
            # Otherwise, skip districts with no completed sessions
            district_summaries[district_name] = {
                "teacher_count": 0,
                "total_students": 0,
                "session_count": 0,
                "total_experiences": 0,
                "organization_count": 0,
                "professional_count": 0,
                "professional_of_color_count": 0,
                "local_professional_count": 0,
                "school_count": 0,
                "local_session_count": 0,
                "poc_session_count": 0,
                "local_session_percent": 0,
                "poc_session_percent": 0,
            }

    # Show all districts that have data, but prioritize the main districts
    main_districts = {
        "Hickman Mills School District",
        "Grandview School District",
        "Kansas City Kansas Public Schools",
    }
    # Include all districts that have data, but put main districts first
    all_districts_list = sorted(list(all_districts))
    main_districts_list = [d for d in all_districts_list if d in main_districts]
    other_districts_list = [d for d in all_districts_list if d not in main_districts]
    filtered_districts = main_districts_list + other_districts_list

    # Prepare filter options
    virtual_year_options = generate_school_year_options()
    filter_options = {
        "school_years": virtual_year_options,
        "career_clusters": sorted(list(all_career_clusters)),
        "schools": sorted(list(all_schools)),
        "districts": sorted(filtered_districts),
        "statuses": sorted(list(all_statuses)),
    }

    return session_data, district_summaries, overall_summary, filter_options


def compute_virtual_session_district_data(
    district_name, virtual_year, date_from, date_to
):
    """
    Compute district-specific virtual session data from database.

    Args:
        district_name: Name of the district
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date

    Returns:
        Tuple of (session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats)
    """
    # Base query for virtual session events
    from sqlalchemy.orm import selectinload

    from models import eagerload_event_bundle
    from models.organization import VolunteerOrganization

    base_query = (
        eagerload_event_bundle(Event.query)
        .options(
            selectinload(Event.volunteers)
            .selectinload(Volunteer.volunteer_organizations)
            .selectinload(VolunteerOrganization.organization)
        )
        .filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        )
    )

    events = base_query.order_by(Event.start_date.desc()).all()
    session_dict = {}

    for event in events:
        # Check if any teacher in this event belongs to the target district
        event_has_target_district_teacher = False
        target_district_teachers = set()
        target_district_schools = set()

        for teacher_reg in event.teacher_registrations:
            teacher = teacher_reg.teacher
            if teacher:
                # Determine district using the same logic as main function
                teacher_district = None

                # Check teacher's school district first
                if teacher.school_id:
                    school = School.query.get(teacher.school_id)
                    if school and school.district:
                        teacher_district = school.district.name

                # If no school district, check event's districts
                if not teacher_district and event.districts:
                    teacher_district = event.districts[0].name

                # If still no district, check event's district_partner
                if not teacher_district and event.district_partner:
                    teacher_district = event.district_partner

                # If teacher belongs to target district, include this event
                # Use helper function to handle aliases (e.g., "KCPS (MO)" vs "Kansas City Public Schools (MO)")
                if _district_name_matches(district_name, teacher_district):
                    event_has_target_district_teacher = True
                    target_district_teachers.add(
                        f"{teacher.first_name} {teacher.last_name}"
                    )
                    if teacher.school_id:
                        school = School.query.get(teacher.school_id)
                        if school:
                            target_district_schools.add(school.name)

        # If no teachers from target district, skip this event
        if not event_has_target_district_teacher:
            continue

        # Calculate participant count for this district only
        # Count only teachers from the target district and multiply by 25
        district_teacher_count = len(target_district_teachers)
        district_participant_count = district_teacher_count * 25

        # Create aggregated session record using only target district teachers and schools
        session_dict[event.id] = {
            "event_id": event.id,  # This should always be the correct event ID
            "status": event.status.value if event.status else "",
            "date": event.start_date.strftime("%m/%d/%y") if event.start_date else "",
            "time": event.start_date.strftime("%I:%M %p") if event.start_date else "",
            "session_type": event.additional_information or "",
            "teachers": (
                sorted(target_district_teachers) if target_district_teachers else []
            ),
            "schools": (
                sorted(target_district_schools) if target_district_schools else []
            ),
            "district": district_name,
            "session_title": event.title,
            "presenter": (
                ", ".join([v.full_name for v in event.volunteers])
                if event.volunteers
                else ""
            ),
            "presenter_data": (
                [
                    {
                        "id": v.id,
                        "name": v.full_name,
                        "is_people_of_color": v.is_people_of_color,
                        "organization_name": v.organization_name,
                        "organizations": (
                            [org.name for org in v.organizations]
                            if v.organizations
                            else []
                        ),
                        # Derive locality from volunteer.local_status
                        "is_local": getattr(v, "local_status", None)
                        == LocalStatusEnum.local,
                    }
                    for v in event.volunteers
                ]
                if event.volunteers
                else []
            ),
            "topic_theme": event.series or "",
            "session_link": event.registration_link or "",
            "participant_count": district_participant_count,
            "duration": event.duration or 0,
            "is_simulcast": (
                any([tr.is_simulcast for tr in event.teacher_registrations])
                if event.teacher_registrations
                else False
            ),
        }

    # Convert to list and sort by date descending
    session_data = list(session_dict.values())
    session_data.sort(key=lambda s: s["date"], reverse=True)

    # Calculate summary statistics
    total_teachers = set()
    total_students = 0
    total_unique_sessions = set()
    total_experiences = 0
    total_organizations = set()
    total_professionals = set()
    total_professionals_of_color = set()
    total_local_professionals = set()
    total_schools = set()
    school_breakdown = {}
    teacher_breakdown = {}

    # We need to track teachers by their actual database objects to get IDs
    # Re-query events with teacher data to get proper teacher IDs
    teacher_sessions = {}  # teacher_id -> session_count
    teacher_details = {}  # teacher_id -> {name, school, id}

    for event in events:
        # Check if any teacher in this event belongs to the target district
        event_has_target_district_teacher = False

        for teacher_reg in event.teacher_registrations:
            teacher = teacher_reg.teacher
            if teacher:
                # Determine district using the same logic as main function
                teacher_district = None

                # Check teacher's school district first
                if teacher.school_id:
                    school = School.query.get(teacher.school_id)
                    if school and school.district:
                        teacher_district = school.district.name

                # If no school district, check event's districts
                if not teacher_district and event.districts:
                    teacher_district = event.districts[0].name

                # If still no district, check event's district_partner
                if not teacher_district and event.district_partner:
                    teacher_district = event.district_partner

                # If teacher belongs to target district, include this event
                # Use helper function to handle aliases (e.g., "KCPS (MO)" vs "Kansas City Public Schools (MO)")
                if _district_name_matches(district_name, teacher_district):
                    event_has_target_district_teacher = True
                    break

        # If no teachers from target district, skip this event
        if not event_has_target_district_teacher:
            continue

        # Only count completed sessions for teacher breakdown and totals
        # Treat "moved to in-person session" as successful/completed
        should_skip = False
        _orig_status = (getattr(event, "original_status_string", "") or "").lower()
        moved_to_in_person = "moved to in-person" in _orig_status
        # Don't skip events with no-show status - we need to count those for teacher breakdown
        if (
            event.status
            and event.status.value not in ["Completed", "Simulcast"]
            and not moved_to_in_person
        ):
            should_skip = True

        if should_skip:
            continue

        # Process teacher registrations to get proper IDs
        for teacher_reg in event.teacher_registrations:
            # Use hybrid attendance check: attendance_confirmed_at OR status allowlist
            if not moved_to_in_person:
                if not is_teacher_attended(teacher_reg):
                    continue

            teacher = teacher_reg.teacher
            if teacher:
                # Determine district using the same logic as main function
                teacher_district = None

                # Check teacher's school district first
                if teacher.school_id:
                    school = School.query.get(teacher.school_id)
                    if school and school.district:
                        teacher_district = school.district.name

                # If no school district, check event's districts
                if not teacher_district and event.districts:
                    teacher_district = event.districts[0].name

                # If still no district, check event's district_partner
                if not teacher_district and event.district_partner:
                    teacher_district = event.district_partner

                # Skip teachers not from the target district
                # Use helper function to handle aliases (e.g., "KCPS (MO)" vs "Kansas City Public Schools (MO)")
                if not _district_name_matches(district_name, teacher_district):
                    continue

                teacher_id = teacher.id
                teacher_name = f"{teacher.first_name} {teacher.last_name}"

                # Get school info
                school_name = "N/A"
                if hasattr(teacher, "school_obj") and teacher.school_obj:
                    school_name = teacher.school_obj.name
                elif teacher.school_id:
                    school_obj = School.query.get(teacher.school_id)
                    if school_obj:
                        school_name = school_obj.name

                # Track teacher sessions
                if teacher_id not in teacher_sessions:
                    teacher_sessions[teacher_id] = 0
                    teacher_details[teacher_id] = {
                        "id": teacher_id,
                        "name": teacher_name,
                        "school": school_name,
                    }
                teacher_sessions[teacher_id] += 1
                total_teachers.add(teacher_name)

        # Count local professionals for this included, completed event
        for v in event.volunteers or []:
            try:
                from models.contact import LocalStatusEnum as _LSE

                if getattr(v, "local_status", None) == _LSE.local:
                    total_local_professionals.add(
                        v.id or f"{v.first_name} {v.last_name}"
                    )
            except Exception:
                # Fallback string check if enum import not available at runtime
                try:
                    if str(getattr(v, "local_status", "")).lower().endswith("local"):
                        total_local_professionals.add(
                            v.id or f"{v.first_name} {v.last_name}"
                        )
                except Exception:
                    pass

    # Build teacher breakdown from the collected data
    for teacher_id, session_count in teacher_sessions.items():
        teacher_info = teacher_details[teacher_id]
        teacher_breakdown[teacher_id] = {
            "id": teacher_info["id"],
            "name": teacher_info["name"],
            "school": teacher_info["school"],
            "sessions": session_count,
        }

    # Calculate breakdowns - only for completed sessions
    for session in session_data:
        # Only count completed sessions for breakdowns
        session_status = session.get("status", "").strip()
        if session_status not in ["Completed", "Simulcast"]:
            continue

        # Schools - only count schools from the target district
        for school_name in session["schools"]:
            # Check if this school belongs to the target district
            school = School.query.filter_by(name=school_name).first()
            if (
                school
                and school.district
                and _district_name_matches(district_name, school.district.name)
            ):
                total_schools.add(school_name)
                # School breakdown
                if school_name not in school_breakdown:
                    school_breakdown[school_name] = {"name": school_name, "sessions": 0}
                school_breakdown[school_name]["sessions"] += 1

        # Sessions
        if session["session_title"]:
            total_unique_sessions.add(session["session_title"])

        # Students
        if session.get("participant_count", 0) > 0:
            total_students += session["participant_count"]
        else:
            total_students += 25
        total_experiences += 1

        # Presenters/Organizations
        if session["presenter_data"]:
            for presenter_data in session["presenter_data"]:
                presenter_name = presenter_data.get("name", "")
                if presenter_name:
                    total_professionals.add(presenter_name)

                    # Check if this presenter is marked as People of Color
                    if presenter_data.get("is_people_of_color", False):
                        total_professionals_of_color.add(presenter_name)
        elif session["presenter"]:
            # Fallback to old presenter format
            presenters = [p.strip() for p in session["presenter"].split(",")]
            for presenter in presenters:
                if presenter:
                    total_professionals.add(presenter)
                    # For old format, we can't determine POC status, so don't count them

    # Convert breakdowns to sorted lists
    school_breakdown_list = sorted(
        school_breakdown.values(), key=lambda x: x["sessions"], reverse=True
    )
    teacher_breakdown_list = sorted(
        teacher_breakdown.values(), key=lambda x: x["sessions"], reverse=True
    )

    # Calculate summary statistics - only for completed sessions with confirmed attendance
    # Use the same teacher counting logic as the teacher breakdown
    total_teachers_completed = set()
    total_unique_sessions_completed = set()
    total_experiences_completed = 0
    total_organizations_completed = set()
    total_professionals_completed = set()
    total_professionals_of_color_completed = set()

    # Use the same teacher counting logic as the teacher breakdown
    for teacher_id, teacher_info in teacher_details.items():
        if (
            teacher_sessions[teacher_id] > 0
        ):  # Only count teachers who actually attended
            total_teachers_completed.add(teacher_info["name"])

    # Count sessions and other stats for completed sessions
    completed_sessions = [
        s
        for s in session_data
        if s.get("status", "").strip().lower()
        in ["completed", "simulcast", "successfully completed"]
    ]

    for session in completed_sessions:

        # Count unique sessions for completed sessions
        if session["session_title"]:
            total_unique_sessions_completed.add(session["session_title"])

        # Count presenters/organizations for completed sessions
        if session["presenter_data"]:
            for presenter_data in session["presenter_data"]:
                presenter_name = presenter_data.get("name", "")
                if presenter_name:
                    total_professionals_completed.add(presenter_name)

                    # Check if this presenter is marked as People of Color
                    if presenter_data.get("is_people_of_color", False):
                        total_professionals_of_color_completed.add(presenter_name)

                    # Count organizations - only count the main/current organization
                    if presenter_data.get("organization_name"):
                        org_name = presenter_data["organization_name"]
                        if org_name:
                            total_organizations_completed.add(org_name)
                    elif (
                        presenter_data.get("organizations")
                        and presenter_data["organizations"]
                    ):
                        # Fallback to first organization if no main organization is set
                        org_name = presenter_data["organizations"][0]
                        if org_name:
                            total_organizations_completed.add(org_name)
        elif session["presenter"]:
            # Fallback to old presenter format
            presenters = [p.strip() for p in session["presenter"].split(",")]
            for presenter in presenters:
                if presenter:
                    total_professionals_completed.add(presenter)

    # Count experiences as total teacher sessions (each teacher attending counts as an experience)
    total_experiences_completed = sum(teacher_sessions.values())

    # Calculate monthly statistics - only for completed sessions
    monthly_stats = {}
    for session in session_data:
        # Only count completed sessions for monthly stats
        session_status = session.get("status", "").strip().lower()
        if session_status not in ["completed", "simulcast", "successfully completed"]:
            continue

        # Parse month from date
        try:
            date_obj = datetime.strptime(session["date"], "%m/%d/%y")
            month_key = date_obj.strftime("%Y-%m")
            month_name = date_obj.strftime("%B %Y")
        except Exception:
            continue

        if month_key not in monthly_stats:
            monthly_stats[month_key] = {
                "month_name": month_name,
                "total_sessions": 0,
                "total_registered": 0,
                "total_attended": 0,
                "total_duration": 0,
                "avg_attendance_rate": 0.0,
                "avg_duration": 0.0,
                "schools": set(),
                "educators": set(),
                "career_clusters": set(),
                "events": [],
            }

        stats = monthly_stats[month_key]
        stats["total_sessions"] += 1
        stats["total_registered"] += session.get("participant_count", 0)
        stats["total_attended"] += session.get("participant_count", 0)
        stats["total_duration"] += session.get("duration", 0)

        for school_name in session["schools"]:
            stats["schools"].add(school_name)
        for teacher_name in session["teachers"]:
            stats["educators"].add(teacher_name)
        if session["topic_theme"]:
            stats["career_clusters"].add(session["topic_theme"])

        stats["events"].append(
            {
                "title": session["session_title"],
                "date": session["date"],
                "time": session["time"],
                "duration": session["duration"],
                "registered": session.get("participant_count", 0),
                "attended": session.get("participant_count", 0),
                "schools": (
                    ", ".join(session["schools"]) if session["schools"] else "N/A"
                ),
                "educators": (
                    ", ".join(session["teachers"]) if session["teachers"] else "N/A"
                ),
                "career_cluster": session["topic_theme"],
                "event_id": session["event_id"],
                "session_link": session.get("session_link", ""),
                "presenter": session["presenter"],
                "presenter_data": session.get("presenter_data", []),
            }
        )

    # Finalize monthly stats
    for stats in monthly_stats.values():
        if stats["total_registered"] > 0:
            stats["avg_attendance_rate"] = (
                stats["total_attended"] / stats["total_registered"]
            ) * 100
        if stats["total_sessions"] > 0:
            stats["avg_duration"] = stats["total_duration"] / stats["total_sessions"]
        stats["school_count"] = len(stats["schools"])
        stats["educator_count"] = len(stats["educators"])
        stats["career_cluster_count"] = len(stats["career_clusters"])
        del stats["schools"]
        del stats["educators"]
        del stats["career_clusters"]

    sorted_monthly_stats = dict(sorted(monthly_stats.items()))

    # Prepare summary statistics - use completed sessions only for summary stats
    # Calculate estimated students as unique teachers * 25
    estimated_students = len(total_teachers_completed) * 25

    # Compute local professional count across completed sessions
    local_professionals = set()
    for stats in monthly_stats.values():
        for evt in stats["events"]:
            for p in evt.get("presenter_data", []) or []:
                try:
                    # Prefer id when available
                    pid = p.get("id") or p.get("name")
                    if p.get("is_local"):
                        local_professionals.add(pid)
                except Exception:
                    pass

    # Add district-level session coverage fields based on session_data
    # Build sets of unique session ids and flags
    _session_ids = set()
    _local_sessions = set()
    _poc_sessions = set()
    for s in session_data:
        sid = s.get("event_id") or s.get("session_title")
        if not sid:
            continue
        # Only count completed/simulcast at district detail level
        st = (s.get("status") or "").strip().lower()
        if st not in ("completed", "simulcast", "successfully completed"):
            continue
        _session_ids.add(sid)
        try:
            if any(p.get("is_local") for p in s.get("presenter_data", []) or []):
                _local_sessions.add(sid)
            if any(
                p.get("is_people_of_color") for p in s.get("presenter_data", []) or []
            ):
                _poc_sessions.add(sid)
        except Exception:
            pass

    summary_stats = {
        "total_teachers": len(total_teachers_completed),
        "total_students": estimated_students,
        "total_unique_sessions": len(total_unique_sessions_completed),
        "total_experiences": total_experiences_completed,
        "total_organizations": len(total_organizations_completed),
        "total_professionals": len(total_professionals_completed),
        "total_professionals_of_color": len(total_professionals_of_color_completed),
        "total_local_professionals": len(total_local_professionals),
        "total_schools": len(total_schools),
        # District-level coverage
        "local_session_count": len(_local_sessions),
        "poc_session_count": len(_poc_sessions),
    }

    # Add percents derived from unique session ids
    denom = len(_session_ids) or 1
    summary_stats["local_session_percent"] = (
        round(100 * summary_stats["local_session_count"] / denom)
        if summary_stats["local_session_count"]
        else 0
    )
    summary_stats["poc_session_percent"] = (
        round(100 * summary_stats["poc_session_count"] / denom)
        if summary_stats["poc_session_count"]
        else 0
    )

    return (
        session_data,
        sorted_monthly_stats,
        school_breakdown_list,
        teacher_breakdown_list,
        summary_stats,
    )
