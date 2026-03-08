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


# Alias for backward compatibility
def get_school_year_dates(school_year: str) -> tuple:
    """Alias for get_school_year_date_range for backward compatibility."""
    return get_school_year_date_range(
        school_year[:2] + school_year[-2:] if "-" in school_year else school_year
    )


def apply_runtime_filters(session_data, filters):
    """
    Apply runtime filters to session data.

    Args:
        session_data: List of session records
        filters: Dictionary of filter criteria

    Returns:
        Filtered session data
    """
    filtered_data = []

    for session in session_data:
        # Apply career cluster filter
        if filters.get("career_cluster"):
            if (
                not session.get("topic_theme")
                or filters["career_cluster"].lower()
                not in session["topic_theme"].lower()
            ):
                continue

        # Apply school filter
        if filters.get("school"):
            if (
                not session.get("school_name")
                or filters["school"].lower() not in session["school_name"].lower()
            ):
                continue

        # Apply district filter
        if filters.get("district"):
            if session.get("district") != filters["district"]:
                continue

        # Apply status filter (case-insensitive with mapping)
        if filters.get("status"):
            session_status = session.get("status", "").strip().lower()
            filter_status = filters["status"].strip().lower()

            # Map common status variations
            status_mapping = {
                "completed": [
                    "completed",
                    "successfully completed",
                    "white lable completed",
                ],
                "simulcast": ["simulcast"],
                "no show": [
                    "no show",
                    "teacher no-show",
                    "local professional no-show",
                    "pathful professional no-show",
                    "local professional no show",
                ],
                "cancelled": [
                    "cancelled",
                    "teacher cancelation",
                    "local professional cancellation",
                    "pathful professional cancellation",
                    "inclement weather cancellation",
                    "technical difficulties",
                ],
                "draft": [
                    "draft",
                    "moved to in-person session",
                    "unfilled",
                    "registered",
                    "count",
                    "white lable unfilled",
                ],
            }

            # Check if the filter status matches any of the mapped statuses
            filter_matched = False
            for mapped_status, variations in status_mapping.items():
                if filter_status == mapped_status and session_status in variations:
                    filter_matched = True
                    break

            if not filter_matched and session_status != filter_status:
                continue

        # Apply text search filter (searches teacher name, session title, and presenter)
        if filters.get("search"):
            search_term = filters["search"].strip().lower()
            if search_term:
                # Get field values, handling None and empty strings
                teacher_name = str(session.get("teacher_name") or "").lower()
                session_title = str(session.get("session_title") or "").lower()
                presenter = str(session.get("presenter") or "").lower()

                # Check if search term matches any of the fields (case-insensitive substring match)
                if (
                    search_term not in teacher_name
                    and search_term not in session_title
                    and search_term not in presenter
                ):
                    continue

        filtered_data.append(session)

    return filtered_data


def calculate_summaries_from_sessions(session_data, show_all_districts=False):
    """
    Calculate district summaries and overall summary from session data.
    Only counts sessions with status "Completed" or "Simulcast".

    Args:
        session_data: List of session records
        show_all_districts: If True, show all districts. If False, only show main districts.

    Returns:
        Tuple of (district_summaries, overall_summary)
    """
    # Include all districts that have data
    # Note: We don't filter districts here anymore - show all districts with data

    print(
        f"DEBUG: calculate_summaries_from_sessions called with {len(session_data)} sessions"
    )
    print(f"DEBUG: show_all_districts = {show_all_districts}")

    district_summaries = {}
    overall_stats = {
        "teacher_count": set(),  # Changed to set for unique counting
        "student_count": 0,
        "session_count": set(),
        "experience_count": 0,  # Changed back to integer for counting every row
        "organization_count": set(),
        "professional_count": set(),
        "professional_of_color_count": set(),
        "local_professional_count": set(),
        "local_sessions": set(),
        "poc_sessions": set(),
        "school_count": set(),
    }

    # First pass: initialize all districts that have any sessions
    districts_found = set()
    for session in session_data:
        if session["district"]:
            districts_found.add(session["district"])
            if session["district"] not in district_summaries:
                district_summaries[session["district"]] = {
                    "teachers": set(),
                    "schools": set(),
                    "sessions": set(),
                    "total_students": 0,
                    "total_experiences": 0,
                    "organizations": set(),
                    "professionals": set(),
                    "professionals_of_color": set(),
                    "local_professionals": set(),
                }

    print(f"DEBUG: Districts found in session_data: {sorted(list(districts_found))}")
    print(
        f"DEBUG: district_summaries initialized with keys: {sorted(list(district_summaries.keys()))}"
    )

    # Second pass: process only completed sessions for counting
    completed_sessions = 0
    for session in session_data:
        # Only count sessions with completed status (case-insensitive)
        session_status = session.get("status", "").strip().lower()
        if session_status not in ["completed", "simulcast", "successfully completed"]:
            continue

        completed_sessions += 1
        if session["district"]:
            district_summary = district_summaries[session["district"]]

            # Count unique teachers (only from completed sessions)
            if session["teacher_name"]:
                district_summary["teachers"].add(session["teacher_name"])
                overall_stats["teacher_count"].add(session["teacher_name"])

            # Count unique schools
            if session["school_name"]:
                district_summary["schools"].add(session["school_name"])
                overall_stats["school_count"].add(session["school_name"])

            # Count unique sessions (prefer id when available)
            if session.get("session_title"):
                district_summary["sessions"].add(session["session_title"])
                overall_stats["session_count"].add(session["session_title"])
            if session.get("event_id"):
                # Attach id sets lazily to avoid key errors if older cache present
                if "session_ids" not in district_summary:
                    district_summary["session_ids"] = set()
                district_summary["session_ids"].add(session["event_id"])
                overall_stats.setdefault("session_ids", set()).add(session["event_id"])

            # Count experiences (every row counts as an experience)
            district_summary["total_experiences"] += 1
            overall_stats["experience_count"] += 1

            # Student count will be calculated after we have unique teacher count

            # Process presenters and check for People of Color; also mark session as Local/POC
            if session["presenter_data"]:
                for presenter_data in session["presenter_data"]:
                    presenter_name = presenter_data.get("name", "")
                    presenter_id = presenter_data.get("id")
                    if presenter_name:
                        # Count unique professionals by ID if available, otherwise by name
                        if presenter_id:
                            district_summary["professionals"].add(presenter_id)
                            overall_stats["professional_count"].add(presenter_id)
                        else:
                            district_summary["professionals"].add(presenter_name)
                            overall_stats["professional_count"].add(presenter_name)

                        # Count only primary organization from this presenter
                        organization_name = presenter_data.get("organization_name")
                        if organization_name:
                            district_summary["organizations"].add(organization_name)
                            overall_stats["organization_count"].add(organization_name)

                        # Check if this presenter is marked as People of Color
                        if presenter_data.get("is_people_of_color", False):
                            if presenter_id:
                                district_summary["professionals_of_color"].add(
                                    presenter_id
                                )
                                overall_stats["professional_of_color_count"].add(
                                    presenter_id
                                )
                            else:
                                district_summary["professionals_of_color"].add(
                                    presenter_name
                                )
                                overall_stats["professional_of_color_count"].add(
                                    presenter_name
                                )
                        # Count local professionals (based on derived is_local flag)
                        if presenter_data.get("is_local"):
                            if presenter_id:
                                district_summary["local_professionals"].add(
                                    presenter_id
                                )
                                overall_stats["local_professional_count"].add(
                                    presenter_id
                                )
                            else:
                                district_summary["local_professionals"].add(
                                    presenter_name
                                )
                                overall_stats["local_professional_count"].add(
                                    presenter_name
                                )
                        # Count local professionals (based on volunteer.local_status)
                        try:
                            # We don't have local flag in presenter_data today; derive from volunteer.id later if needed
                            # For now, assume presenter_data includes a boolean 'is_local' when set by import
                            is_local = presenter_data.get("is_local")
                            if is_local:
                                if presenter_id:
                                    overall_stats["local_professional_count"].add(
                                        presenter_id
                                    )
                                else:
                                    overall_stats["local_professional_count"].add(
                                        presenter_name
                                    )
                        except Exception:
                            pass

                # Session-level flags (local / POC sessions)
                # Prefer event_id for consistency with session counting logic
                sid_flag = session.get("event_id") or session.get("session_title")
                if sid_flag:
                    if any(p.get("is_local") for p in session["presenter_data"]):
                        overall_stats["local_sessions"].add(sid_flag)
                        # mirror per-district; initialize lazily
                        if "local_sessions" not in district_summary:
                            district_summary["local_sessions"] = set()
                        district_summary["local_sessions"].add(sid_flag)
                    if any(
                        p.get("is_people_of_color") for p in session["presenter_data"]
                    ):
                        overall_stats["poc_sessions"].add(sid_flag)
                        if "poc_sessions" not in district_summary:
                            district_summary["poc_sessions"] = set()
                        district_summary["poc_sessions"].add(sid_flag)
            elif session["presenter"]:
                # Fallback to old presenter format
                presenters = [p.strip() for p in session["presenter"].split(",")]
                for presenter in presenters:
                    if presenter:
                        district_summary["professionals"].add(presenter)
                        overall_stats["professional_count"].add(presenter)
                        # For old format, we can't determine POC status, so don't count them

    # Convert sets to counts and filter allowed districts
    for district_name, summary in district_summaries.items():
        summary["teacher_count"] = len(summary["teachers"])
        summary["school_count"] = len(summary["schools"])
        # Prefer event-id based counting if present
        summary["session_count"] = (
            len(summary.get("session_ids", set()))
            if summary.get("session_ids")
            else len(summary["sessions"])
        )
        summary["organization_count"] = len(summary["organizations"])
        summary["professional_count"] = len(summary["professionals"])
        summary["professional_of_color_count"] = len(summary["professionals_of_color"])
        summary["local_professional_count"] = len(summary["local_professionals"])
        # Session-level flags
        summary["local_session_count"] = len(summary.get("local_sessions", set()))
        summary["poc_session_count"] = len(summary.get("poc_sessions", set()))
        if summary["session_count"]:
            summary["local_session_percent"] = round(
                100 * summary["local_session_count"] / summary["session_count"]
            )
            summary["poc_session_percent"] = round(
                100 * summary["poc_session_count"] / summary["session_count"]
            )
        else:
            summary["local_session_percent"] = 0
            summary["poc_session_percent"] = 0

        # Calculate student count as unique teachers × 25
        summary["total_students"] = summary["teacher_count"] * 25

        del summary["teachers"]
        del summary["schools"]
        del summary["sessions"]
        if "session_ids" in summary:
            del summary["session_ids"]
        del summary["organizations"]
        del summary["professionals"]
        del summary["professionals_of_color"]
        del summary["local_professionals"]
        if "local_sessions" in summary:
            del summary["local_sessions"]
        if "poc_sessions" in summary:
            del summary["poc_sessions"]

    # Filter to only show main districts by default (unless admin requests all)
    if not show_all_districts:
        main_districts = {
            "Hickman Mills School District",
            "Grandview School District",
            "Kansas City Kansas Public Schools",
        }
        # Only show main districts when show_all_districts=False
        district_summaries = {
            k: v for k, v in district_summaries.items() if k in main_districts
        }

    # Calculate overall student count as unique teachers × 25
    unique_teacher_count = len(overall_stats["teacher_count"])
    overall_student_count = unique_teacher_count * 25

    # Prepare overall summary stats
    # Use session_ids (event_id) if available for session counting, otherwise fall back to session_count
    overall_session_count = (
        len(overall_stats.get("session_ids", set()))
        if overall_stats.get("session_ids")
        else len(overall_stats["session_count"])
    )

    overall_summary = {
        "teacher_count": unique_teacher_count,
        "student_count": overall_student_count,
        "session_count": overall_session_count,
        "experience_count": overall_stats["experience_count"],  # Use integer value
        "organization_count": len(overall_stats["organization_count"]),
        "professional_count": len(overall_stats["professional_count"]),
        "professional_of_color_count": len(
            overall_stats["professional_of_color_count"]
        ),
        "local_professional_count": len(overall_stats["local_professional_count"]),
        "school_count": len(overall_stats["school_count"]),
        "local_session_count": len(overall_stats["local_sessions"]),
        "poc_session_count": len(overall_stats["poc_sessions"]),
    }

    # Percentages overall - use session_ids for denominator if available
    denom = (
        len(overall_stats.get("session_ids", set()))
        if overall_stats.get("session_ids")
        else (overall_summary["session_count"] or 1)
    )
    if denom == 0:
        denom = 1
    overall_summary["local_session_percent"] = (
        round(100 * overall_summary["local_session_count"] / denom)
        if overall_summary["local_session_count"]
        else 0
    )
    overall_summary["poc_session_percent"] = (
        round(100 * overall_summary["poc_session_count"] / denom)
        if overall_summary["poc_session_count"]
        else 0
    )

    print(
        f"DEBUG: calculate_summaries_from_sessions returning {len(district_summaries)} districts: {sorted(list(district_summaries.keys()))}"
    )
    return district_summaries, overall_summary


def apply_sorting_and_pagination(session_data, request_args, current_filters):
    """
    Apply sorting and pagination to session data.

    Args:
        session_data: List of session records
        request_args: Request arguments for sorting/pagination
        current_filters: Current filter settings

    Returns:
        Dictionary with paginated_data and pagination info
    """
    # Apply sorting
    sort_column = request_args.get("sort", "date")
    sort_order = request_args.get("order", "desc")

    # Define sortable columns mapping
    sortable_columns = {
        "status": "status",
        "date": "date",
        "time": "time",
        "session_type": "session_type",
        "teacher_name": "teacher_name",
        "school_name": "school_name",
        "school_level": "school_level",
        "district": "district",
        "session_title": "session_title",
        "presenter": "presenter",
        "presenter_organization": "presenter_organization",
        "topic_theme": "topic_theme",
    }

    # Apply sorting if valid column
    if sort_column in sortable_columns:
        reverse_order = sort_order == "desc"

        # Handle special sorting for date/time columns
        if sort_column == "date":

            def date_sort_key(session):
                try:
                    if session["date"]:
                        date_parts = session["date"].split("/")
                        if len(date_parts) == 3:
                            month = int(date_parts[0])
                            day = int(date_parts[1])
                            year = int(date_parts[2])
                            if year < 50:
                                year += 2000
                            else:
                                year += 1900
                            return datetime(year, month, day)
                        elif len(date_parts) == 2:
                            month = int(date_parts[0])
                            day = int(date_parts[1])
                            virtual_year_start = int(
                                current_filters["year"].split("-")[0]
                            )
                            if month >= 7:
                                year = virtual_year_start
                            else:
                                year = virtual_year_start + 1
                            return datetime(year, month, day)
                    return datetime.min
                except (ValueError, IndexError):
                    return datetime.min

            session_data.sort(key=date_sort_key, reverse=reverse_order)

        elif sort_column == "time":

            def time_sort_key(session):
                try:
                    if session["time"]:
                        return datetime.strptime(session["time"], "%I:%M %p").time()
                    return datetime.min.time()
                except ValueError:
                    return datetime.min.time()

            session_data.sort(key=time_sort_key, reverse=reverse_order)

        else:

            def string_sort_key(session):
                value = session.get(sortable_columns[sort_column], "") or ""
                return str(value).lower()

            session_data.sort(key=string_sort_key, reverse=reverse_order)

    # Add sorting info to current_filters for template
    current_filters["sort"] = sort_column
    current_filters["order"] = sort_order

    # Apply pagination
    try:
        page = int(request_args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    try:
        per_page = int(request_args.get("per_page", 25))
        if per_page < 1:
            per_page = 25
    except ValueError:
        per_page = 25

    total_records = len(session_data)
    total_pages = (total_records + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = session_data[start_idx:end_idx]

    pagination = {
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "total_records": total_records,
    }

    return {"paginated_data": paginated_data, "pagination": pagination}


def get_google_sheet_url(virtual_year):
    """
    Get Google Sheet URL for a virtual year.

    Args:
        virtual_year: The virtual year to get sheet for

    Returns:
        Google Sheet URL or None
    """
    google_sheet = GoogleSheet.query.filter_by(
        academic_year=virtual_year, purpose="virtual_sessions"
    ).first()
    if google_sheet and google_sheet.decrypted_sheet_id:
        return (
            f"https://docs.google.com/spreadsheets/d/{google_sheet.decrypted_sheet_id}"
        )
    return None


def _get_primary_org_name_for_volunteer(volunteer):
    """
    Get the primary organization name for a volunteer.
    Prefer explicit primary org from VolunteerOrganization, fall back to organization_name field.
    Uses the same pattern as routes/reports/volunteers_by_event.py:_get_primary_org_name
    """
    # Prefer explicit primary org from association table
    if getattr(volunteer, "volunteer_organizations", None):
        try:
            primary = next(
                (vo for vo in volunteer.volunteer_organizations if vo.is_primary), None
            )
            if primary and primary.organization and primary.organization.name:
                return primary.organization.name
            # Fall back to first org if no primary
            first = (
                volunteer.volunteer_organizations[0].organization
                if volunteer.volunteer_organizations
                else None
            )
            if first and first.name:
                return first.name
        except (StopIteration, AttributeError, IndexError):
            pass
    # Avoid showing raw Salesforce IDs stored in organization_name
    org_name = getattr(volunteer, "organization_name", None)
    if org_name and not (len(str(org_name)) == 18 and str(org_name).isalnum()):
        return org_name
    return None


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


def _district_name_matches(target_district_name, compare_district_name):
    """
    Check if a district name matches the target district, including aliases.

    Args:
        target_district_name: The target district name (from URL/filter)
        compare_district_name: The district name to compare against

    Returns:
        bool: True if the districts match (including aliases)
    """
    if not target_district_name or not compare_district_name:
        return False

    # Normalize for comparison (case-insensitive, strip whitespace)
    target_normalized = target_district_name.strip().lower()
    compare_normalized = compare_district_name.strip().lower()

    # Exact match (case-insensitive)
    if target_normalized == compare_normalized:
        return True

    # Check against DISTRICT_MAPPING aliases
    from routes.reports.common import DISTRICT_MAPPING

    # Find the target district in the mapping
    target_mapping = None
    for mapping in DISTRICT_MAPPING.values():
        if mapping["name"].strip().lower() == target_normalized:
            target_mapping = mapping
            break

    if target_mapping:
        # Check if compare_district_name matches any alias
        aliases = target_mapping.get("aliases", [])
        for alias in aliases:
            if alias.strip().lower() == compare_normalized:
                return True

        # Also check reverse: if compare_district_name is the primary name and target is an alias
        if (
            compare_district_name.strip().lower()
            == target_mapping["name"].strip().lower()
        ):
            return True

    # Reverse check: maybe compare_district_name is in the mapping and target is an alias
    for mapping in DISTRICT_MAPPING.values():
        if mapping["name"].strip().lower() == compare_normalized:
            aliases = mapping.get("aliases", [])
            for alias in aliases:
                if alias.strip().lower() == target_normalized:
                    return True
            break

    return False


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
            # Only count teachers who actually attended OR were part of events
            # moved to in-person (counted as successful)
            tr_status_norm = (getattr(teacher_reg, "status", "") or "").lower()
            is_no_show = (
                "no-show" in tr_status_norm
                or "no show" in tr_status_norm
                or "did not attend" in tr_status_norm
            )
            is_cancel = "cancel" in tr_status_norm or "withdraw" in tr_status_norm
            if not moved_to_in_person:
                # For regular virtual events, require confirmed attendance and not a no-show/cancel
                if teacher_reg.attendance_confirmed_at is None:
                    continue
                if is_no_show or is_cancel:
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
