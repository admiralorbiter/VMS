"""
Shared computation helpers for virtual session reporting.

Extracted from duplicated logic in:
  - routes/virtual/usage/computation.py (usage dashboard)
  - routes/reports/virtual_session/computation.py (reports suite)

Contains filtering, summary aggregation, pagination, and shared
utilities used by both UIs.
"""

from datetime import datetime

from models.google_sheet import GoogleSheet
from models.school_model import School

# ── Constants ──────────────────────────────────────────────────────────

COMPLETED_STATUSES = {"completed", "simulcast", "successfully completed"}

MAIN_DISTRICTS = {
    "Hickman Mills School District",
    "Grandview School District",
    "Kansas City Kansas Public Schools",
}

STATUS_FILTER_MAPPING = {
    "completed": [
        "completed",
        "successfully completed",
        "white lable completed",
    ],
    "requested": [
        "requested",
        "teacher requested",
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

# Allowlist of EventTeacher.status strings that indicate attendance.
ATTENDED_STATUSES = {"attended", "count", "completed"}


# ── Attendance Helper ──────────────────────────────────────────────────


def is_teacher_attended(teacher_reg):
    """
    Determine whether a teacher registration counts as 'attended'
    using the hybrid approach:

    1. attendance_confirmed_at is set (explicit first-party signal), OR
    2. status string indicates attendance (fallback for legacy data).

    Then exclude known no-shows and cancellations.

    Returns:
        bool: True if the teacher should be counted as having attended.
    """
    tr_status = (getattr(teacher_reg, "status", "") or "").lower()

    # Primary + fallback attendance signals
    has_attended = (
        teacher_reg.attendance_confirmed_at is not None
        or tr_status in ATTENDED_STATUSES
    )

    # Exclusion: no-shows and cancellations always override
    is_no_show = (
        "no_show" in tr_status
        or "no-show" in tr_status
        or "no show" in tr_status
        or "did not attend" in tr_status
    )
    is_cancel = "cancel" in tr_status or "withdraw" in tr_status

    return has_attended and not is_no_show and not is_cancel


# ── District Resolution ───────────────────────────────────────────────


def resolve_teacher_district(teacher, event):
    """
    Determine a teacher's district using the standard 3-tier cascade:

    1. Teacher's school district (most specific)
    2. Event's district association
    3. Event's district_partner text field
    4. Fallback: "Unknown District"

    Args:
        teacher: Teacher model instance (may be None)
        event: Event model instance

    Returns:
        str: District name
    """
    if teacher and teacher.school_id:
        school = School.query.get(teacher.school_id)
        if school and school.district:
            return school.district.name

    if event.districts:
        return event.districts[0].name

    if event.district_partner:
        return event.district_partner

    return "Unknown District"


def district_name_matches(target_district_name, compare_district_name):
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

    target_normalized = target_district_name.strip().lower()
    compare_normalized = compare_district_name.strip().lower()

    if target_normalized == compare_normalized:
        return True

    from routes.reports.common import DISTRICT_MAPPING

    # Find target in mapping
    target_mapping = None
    for mapping in DISTRICT_MAPPING.values():
        if mapping["name"].strip().lower() == target_normalized:
            target_mapping = mapping
            break

    if target_mapping:
        aliases = target_mapping.get("aliases", [])
        for alias in aliases:
            if alias.strip().lower() == compare_normalized:
                return True
        if (
            compare_district_name.strip().lower()
            == target_mapping["name"].strip().lower()
        ):
            return True

    # Reverse check
    for mapping in DISTRICT_MAPPING.values():
        if mapping["name"].strip().lower() == compare_normalized:
            aliases = mapping.get("aliases", [])
            for alias in aliases:
                if alias.strip().lower() == target_normalized:
                    return True
            break

    return False


# ── Filtering ─────────────────────────────────────────────────────────


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
        # Career cluster filter
        if filters.get("career_cluster"):
            if (
                not session.get("topic_theme")
                or filters["career_cluster"].lower()
                not in session["topic_theme"].lower()
            ):
                continue

        # School filter
        if filters.get("school"):
            if (
                not session.get("school_name")
                or filters["school"].lower() not in session["school_name"].lower()
            ):
                continue

        # District filter
        if filters.get("district"):
            if session.get("district") != filters["district"]:
                continue

        # Status filter (case-insensitive with mapping)
        if filters.get("status"):
            session_status = session.get("status", "").strip().lower()
            filter_status = filters["status"].strip().lower()

            filter_matched = False
            for mapped_status, variations in STATUS_FILTER_MAPPING.items():
                if filter_status == mapped_status and session_status in variations:
                    filter_matched = True
                    break

            if not filter_matched and session_status != filter_status:
                continue

        # Text search filter
        if filters.get("search"):
            search_term = filters["search"].strip().lower()
            if search_term:
                teacher_name = str(session.get("teacher_name") or "").lower()
                session_title = str(session.get("session_title") or "").lower()
                presenter = str(session.get("presenter") or "").lower()

                if (
                    search_term not in teacher_name
                    and search_term not in session_title
                    and search_term not in presenter
                ):
                    continue

        filtered_data.append(session)

    return filtered_data


# ── Summarization ─────────────────────────────────────────────────────


def calculate_summaries_from_sessions(session_data, show_all_districts=False):
    """
    Calculate district summaries and overall summary from session data.
    Only counts sessions with status in COMPLETED_STATUSES.

    Args:
        session_data: List of session records
        show_all_districts: If True, show all districts.

    Returns:
        Tuple of (district_summaries, overall_summary)
    """
    district_summaries = {}
    overall_stats = {
        "teacher_count": set(),
        "student_count": 0,
        "session_count": set(),
        "experience_count": 0,
        "organization_count": set(),
        "professional_count": set(),
        "professional_of_color_count": set(),
        "local_professional_count": set(),
        "local_sessions": set(),
        "poc_sessions": set(),
        "school_count": set(),
    }

    # First pass: initialize districts
    for session in session_data:
        if session["district"]:
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

    # Second pass: process completed sessions
    for session in session_data:
        session_status = session.get("status", "").strip().lower()
        if session_status not in COMPLETED_STATUSES:
            continue

        if not session["district"]:
            continue

        district_summary = district_summaries[session["district"]]

        # Teachers
        if session["teacher_name"]:
            district_summary["teachers"].add(session["teacher_name"])
            overall_stats["teacher_count"].add(session["teacher_name"])

        # Schools
        if session["school_name"]:
            district_summary["schools"].add(session["school_name"])
            overall_stats["school_count"].add(session["school_name"])

        # Sessions (prefer event_id when available)
        if session.get("session_title"):
            district_summary["sessions"].add(session["session_title"])
            overall_stats["session_count"].add(session["session_title"])
        if session.get("event_id"):
            if "session_ids" not in district_summary:
                district_summary["session_ids"] = set()
            district_summary["session_ids"].add(session["event_id"])
            overall_stats.setdefault("session_ids", set()).add(session["event_id"])

        # Experiences
        district_summary["total_experiences"] += 1
        overall_stats["experience_count"] += 1

        # Process presenters
        if session["presenter_data"]:
            for presenter_data in session["presenter_data"]:
                presenter_name = presenter_data.get("name", "")
                presenter_id = presenter_data.get("id")
                if not presenter_name:
                    continue

                # Unique professionals (prefer ID)
                pid = presenter_id or presenter_name
                district_summary["professionals"].add(pid)
                overall_stats["professional_count"].add(pid)

                # Organizations
                organization_name = presenter_data.get("organization_name")
                if organization_name:
                    district_summary["organizations"].add(organization_name)
                    overall_stats["organization_count"].add(organization_name)

                # People of color
                if presenter_data.get("is_people_of_color", False):
                    district_summary["professionals_of_color"].add(pid)
                    overall_stats["professional_of_color_count"].add(pid)

                # Local professionals (single check — no duplicate)
                if presenter_data.get("is_local"):
                    district_summary["local_professionals"].add(pid)
                    overall_stats["local_professional_count"].add(pid)

            # Session-level flags (local / POC sessions)
            sid_flag = session.get("event_id") or session.get("session_title")
            if sid_flag:
                if any(p.get("is_local") for p in session["presenter_data"]):
                    overall_stats["local_sessions"].add(sid_flag)
                    if "local_sessions" not in district_summary:
                        district_summary["local_sessions"] = set()
                    district_summary["local_sessions"].add(sid_flag)
                if any(p.get("is_people_of_color") for p in session["presenter_data"]):
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

    # Convert sets to counts
    for district_name, summary in district_summaries.items():
        summary["teacher_count"] = len(summary["teachers"])
        summary["school_count"] = len(summary["schools"])
        summary["session_count"] = (
            len(summary.get("session_ids", set()))
            if summary.get("session_ids")
            else len(summary["sessions"])
        )
        summary["organization_count"] = len(summary["organizations"])
        summary["professional_count"] = len(summary["professionals"])
        summary["professional_of_color_count"] = len(summary["professionals_of_color"])
        summary["local_professional_count"] = len(summary["local_professionals"])
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

        summary["total_students"] = summary["teacher_count"] * 25

        # Clean up working sets
        for key in (
            "teachers",
            "schools",
            "sessions",
            "session_ids",
            "organizations",
            "professionals",
            "professionals_of_color",
            "local_professionals",
            "local_sessions",
            "poc_sessions",
        ):
            summary.pop(key, None)

    # Filter districts
    if not show_all_districts:
        district_summaries = {
            k: v for k, v in district_summaries.items() if k in MAIN_DISTRICTS
        }

    # Overall summary
    unique_teacher_count = len(overall_stats["teacher_count"])
    overall_session_count = (
        len(overall_stats.get("session_ids", set()))
        if overall_stats.get("session_ids")
        else len(overall_stats["session_count"])
    )

    overall_summary = {
        "teacher_count": unique_teacher_count,
        "student_count": unique_teacher_count * 25,
        "session_count": overall_session_count,
        "experience_count": overall_stats["experience_count"],
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

    # Percentages
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

    return district_summaries, overall_summary


# ── Sorting & Pagination ──────────────────────────────────────────────


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
    sort_column = request_args.get("sort", "date")
    sort_order = request_args.get("order", "desc")

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

    if sort_column in sortable_columns:
        reverse_order = sort_order == "desc"

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

    current_filters["sort"] = sort_column
    current_filters["order"] = sort_order

    # Pagination
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


# ── Utilities ─────────────────────────────────────────────────────────


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


def get_primary_org_name(volunteer):
    """
    Get the primary organization name for a volunteer.
    Prefer explicit primary org from VolunteerOrganization,
    fall back to organization_name field.

    Args:
        volunteer: Volunteer model instance

    Returns:
        str or None: Organization name
    """
    if getattr(volunteer, "volunteer_organizations", None):
        try:
            primary = next(
                (vo for vo in volunteer.volunteer_organizations if vo.is_primary), None
            )
            if primary and primary.organization and primary.organization.name:
                return primary.organization.name
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
