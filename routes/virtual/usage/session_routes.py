"""
Virtual session CRUD routes.

Contains routes for viewing, searching, creating, editing, and deleting
virtual sessions. Registered on virtual_bp.
"""

from datetime import datetime, timedelta, timezone

from flask import (
    Response,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import db
from models.contact import LocalStatusEnum
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import EventParticipation, Volunteer
from routes.decorators import district_scoped_required
from routes.reports.common import (
    generate_school_year_options,
    get_current_virtual_year,
    get_school_year_date_range,
    get_virtual_year_dates,
    is_cache_valid,
)
from routes.utils import admin_required
from routes.virtual.routes import virtual_bp

from .cache import (
    get_virtual_session_cache,
    invalidate_virtual_session_caches,
    save_virtual_session_cache,
)
from .computation import (
    _get_primary_org_name_for_volunteer,
    apply_runtime_filters,
    apply_sorting_and_pagination,
    calculate_summaries_from_sessions,
    compute_virtual_session_data,
    compute_virtual_session_district_data,
    get_google_sheet_url,
)


def load_session_routes():
    def _group_sessions_for_table(session_rows):
        """
        Group sessions by logical session identifier (title + date + time).
        Combines multiple teachers/presenters for the same session into one row.
        This is a display-only transform and should not be used for summary calculations.

        Works for both APP-created and spreadsheet-imported sessions.
        """
        grouped_sessions = {}
        ungrouped = []

        for row in session_rows or []:
            # Create grouping key from title, date, and time
            title = (row.get("session_title") or "").strip().lower()
            date = (row.get("date") or "").strip()
            time = (row.get("time") or "").strip()

            # If we don't have the required fields, pass through ungrouped
            if not title or not date or not time:
                ungrouped.append(row)
                continue

            # Create a unique key for this session
            session_key = (title, date, time)

            bucket = grouped_sessions.get(session_key)
            if not bucket:
                # Create new bucket with this row's data
                bucket = dict(row)
                bucket["_teacher_names"] = set()
                bucket["_school_names"] = set()
                bucket["_presenter_names"] = set()
                bucket["_presenter_orgs"] = set()
                # Grouped rows should not link to a single teacher
                bucket["teacher_id"] = None
                grouped_sessions[session_key] = bucket

            # Collect teachers and schools
            if row.get("teacher_name"):
                bucket["_teacher_names"].add(row["teacher_name"])
            if row.get("school_name"):
                bucket["_school_names"].add(row["school_name"])

            # Collect presenters
            if row.get("presenter"):
                # Presenter field may contain comma-separated names
                presenters = [
                    p.strip() for p in row["presenter"].split(",") if p.strip()
                ]
                bucket["_presenter_names"].update(presenters)

            # Collect presenter organizations
            if row.get("presenter_organization"):
                # presenter_organization is already comma-separated
                orgs = [
                    o.strip()
                    for o in row["presenter_organization"].split(",")
                    if o.strip()
                ]
                bucket["_presenter_orgs"].update(orgs)

            # Also collect from presenter_data if available
            if row.get("presenter_data"):
                for presenter in row["presenter_data"]:
                    if presenter.get("organization_name"):
                        bucket["_presenter_orgs"].add(presenter["organization_name"])
                    elif presenter.get("organizations"):
                        # If organizations is a list
                        if isinstance(presenter["organizations"], list):
                            bucket["_presenter_orgs"].update(presenter["organizations"])

        # Convert grouped sessions to list format
        grouped = []
        for session_key, bucket in grouped_sessions.items():
            teachers = sorted(bucket.pop("_teacher_names", set()))
            schools = sorted(bucket.pop("_school_names", set()))
            presenters = sorted(bucket.pop("_presenter_names", set()))
            presenter_orgs = sorted(bucket.pop("_presenter_orgs", set()))

            bucket["teacher_name"] = ", ".join(teachers)
            bucket["school_name"] = "; ".join(schools)

            # Update presenter field
            if presenters:
                bucket["presenter"] = ", ".join(presenters)
            else:
                bucket["presenter"] = ""

            # Update presenter organization
            if presenter_orgs:
                bucket["presenter_organization"] = ", ".join(presenter_orgs)
            elif not bucket.get("presenter_organization"):
                bucket["presenter_organization"] = ""

            grouped.append(bucket)

        # Keep original ordering: newest first by date/time as strings is imperfect but matches existing behavior.
        return grouped + ungrouped

    @virtual_bp.route("/usage")
    @login_required
    def virtual_usage():
        # Get filter parameters - Use virtual year instead of school year
        default_virtual_year = (
            get_current_virtual_year()
        )  # Changed from get_current_school_year()
        selected_virtual_year = request.args.get(
            "year", default_virtual_year
        )  # Changed variable name

        # Check if refresh is requested
        refresh_requested = request.args.get("refresh", "0") == "1"

        # Calculate default date range based on virtual session year
        default_date_from, default_date_to = get_virtual_year_dates(
            selected_virtual_year
        )  # Changed from get_school_year_dates()

        # Handle explicit date range parameters
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")

        date_from = default_date_from
        date_to = default_date_to

        if date_from_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
                if (
                    default_date_from.date()
                    <= parsed_date_from.date()
                    <= default_date_to.date()
                ):
                    date_from = parsed_date_from.replace(hour=0, minute=0, second=0)
            except ValueError:
                pass

        if date_to_str:
            try:
                parsed_date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
                if (
                    default_date_from.date()
                    <= parsed_date_to.date()
                    <= default_date_to.date()
                ):
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass

        if date_from > date_to:
            date_from = default_date_from
            date_to = default_date_to

        # Check if admin wants to see all districts (default: YES for Pathful data)
        show_all_districts = request.args.get("show_all_districts", "1") == "1"

        current_filters = {
            "year": selected_virtual_year,  # Updated variable name
            "date_from": date_from,
            "date_to": date_to,
            "career_cluster": request.args.get("career_cluster"),
            "school": request.args.get("school"),
            "district": request.args.get("district"),
            "status": request.args.get("status"),
            "search": request.args.get(
                "search"
            ),  # Text search across teacher, title, presenter
            "show_all_districts": show_all_districts,
            "group_manual": request.args.get("group_manual", "0") == "1",
        }

        # Check if we're using default full year date range (for caching)
        is_full_year = date_from == default_date_from and date_to == default_date_to

        # If refresh is requested, invalidate cache for this virtual year
        if refresh_requested and is_full_year:
            print(f"DEBUG: Refresh requested for {selected_virtual_year}")
            invalidate_virtual_session_caches(selected_virtual_year)
            print(
                f"Cache invalidated for virtual session report {selected_virtual_year}"
            )

        # Try to get cached data for full year queries (but not if refresh was requested)
        cached_data = None
        is_cached = False
        last_refreshed = None

        if is_full_year and not refresh_requested:
            cached_data = get_virtual_session_cache(
                selected_virtual_year, date_from, date_to
            )
            if cached_data:
                is_cached = True
                last_refreshed = cached_data.last_updated
                print(
                    f"Using cached data for virtual session report {selected_virtual_year}"
                )
                # Use cached data
                session_data = cached_data.session_data
                district_summaries = cached_data.district_summaries
                overall_summary = cached_data.overall_summary
                filter_options = cached_data.filter_options

                # Filter district summaries to main districts if show_all_districts is False
                if not show_all_districts and district_summaries:
                    main_districts = {
                        "Hickman Mills School District",
                        "Grandview School District",
                        "Kansas City Kansas Public Schools",
                    }
                    district_summaries = {
                        k: v
                        for k, v in district_summaries.items()
                        if k in main_districts
                    }

                # Check if cached data has the new fields; if any are missing, recompute summaries
                if session_data and len(session_data) > 0:
                    sample_session = session_data[0]
                    needs_recompute = False
                    if (
                        "teacher_id" not in sample_session
                        or "presenter_data" not in sample_session
                    ):
                        needs_recompute = True
                    if not needs_recompute and "source_host" not in sample_session:
                        needs_recompute = True
                    # Ensure newer Local/POC session coverage fields exist
                    if not needs_recompute and (
                        overall_summary is None
                        or "local_professional_count" not in overall_summary
                        or "local_session_count" not in overall_summary
                        or "poc_session_count" not in overall_summary
                    ):
                        needs_recompute = True
                    # Also ensure district summaries contain the new session coverage fields
                    if (
                        not needs_recompute
                        and isinstance(district_summaries, dict)
                        and district_summaries
                    ):
                        try:
                            any_district = next(iter(district_summaries.values()))
                            if (
                                "local_session_count" not in any_district
                                or "poc_session_count" not in any_district
                            ):
                                needs_recompute = True
                        except Exception:
                            pass
                    if needs_recompute:
                        (
                            session_data,
                            district_summaries,
                            overall_summary,
                            filter_options,
                        ) = compute_virtual_session_data(
                            selected_virtual_year, date_from, date_to, current_filters
                        )
                        is_cached = False

                # Apply runtime filters if any
                if any(
                    [
                        current_filters["career_cluster"],
                        current_filters["school"],
                        current_filters["district"],
                        current_filters["status"],
                        current_filters.get("search"),  # Include search filter
                    ]
                ):
                    # Store original unfiltered data for district summaries
                    unfiltered_session_data = session_data.copy()
                    session_data = apply_runtime_filters(session_data, current_filters)
                    # Recalculate summaries using same method as individual district pages
                    # Get list of all districts that appear in the unfiltered data
                    all_districts_in_data = set()
                    for session in unfiltered_session_data:
                        if session.get("district"):
                            all_districts_in_data.add(session["district"])

                    # Filter to only show main districts by default (unless admin requests all)
                    main_districts = {
                        "Hickman Mills School District",
                        "Grandview School District",
                        "Kansas City Kansas Public Schools",
                    }

                    # Determine which districts to show in the breakdown
                    if show_all_districts:
                        districts_to_show = all_districts_in_data
                    else:
                        # Only show main districts when show_all_districts=False
                        districts_to_show = {
                            d for d in all_districts_in_data if d in main_districts
                        }

                    # Calculate district summaries using the same method as individual district pages
                    district_summaries = {}
                    for district_name in districts_to_show:
                        try:
                            _, _, _, _, summary_stats = (
                                compute_virtual_session_district_data(
                                    district_name,
                                    selected_virtual_year,
                                    date_from,
                                    date_to,
                                )
                            )
                            district_summaries[district_name] = {
                                "teacher_count": summary_stats.get("total_teachers", 0),
                                "total_students": summary_stats.get(
                                    "total_students", 0
                                ),
                                "session_count": summary_stats.get(
                                    "total_unique_sessions", 0
                                ),
                                "total_experiences": summary_stats.get(
                                    "total_experiences", 0
                                ),
                                "organization_count": summary_stats.get(
                                    "total_organizations", 0
                                ),
                                "professional_count": summary_stats.get(
                                    "total_professionals", 0
                                ),
                                "professional_of_color_count": summary_stats.get(
                                    "total_professionals_of_color", 0
                                ),
                                "local_professional_count": summary_stats.get(
                                    "total_local_professionals", 0
                                ),
                                "school_count": summary_stats.get("total_schools", 0),
                                "local_session_count": summary_stats.get(
                                    "local_session_count", 0
                                ),
                                "poc_session_count": summary_stats.get(
                                    "poc_session_count", 0
                                ),
                                "local_session_percent": summary_stats.get(
                                    "local_session_percent", 0
                                ),
                                "poc_session_percent": summary_stats.get(
                                    "poc_session_percent", 0
                                ),
                            }
                        except Exception as e:
                            print(
                                f"DEBUG: Error calculating stats for {district_name}: {str(e)}"
                            )
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

                    # Recalculate overall summary from unfiltered session data
                    _, overall_summary = calculate_summaries_from_sessions(
                        unfiltered_session_data,
                        current_filters.get("show_all_districts", False),
                    )

                    # Filter district summaries based on user scope
                    if (
                        current_user.scope_type == "district"
                        and current_user.allowed_districts
                    ):
                        import json

                        try:
                            allowed_districts = (
                                json.loads(current_user.allowed_districts)
                                if isinstance(current_user.allowed_districts, str)
                                else current_user.allowed_districts
                            )

                            # Create filtered district summaries
                            filtered_district_summaries = {}
                            for district_name, summary in district_summaries.items():
                                if district_name in allowed_districts:
                                    filtered_district_summaries[district_name] = summary

                            # Replace the original district_summaries with the filtered version
                            district_summaries = filtered_district_summaries
                        except (json.JSONDecodeError, TypeError):
                            # If parsing fails, show no districts
                            district_summaries = {}

                # Apply sorting and pagination as before
                # Only group if explicitly requested (group_manual=1)
                # When group_manual=0 or not set, show individual lines (one per teacher registration)
                if current_filters.get("group_manual"):
                    session_data = _group_sessions_for_table(session_data)
                session_data = apply_sorting_and_pagination(
                    session_data, request.args, current_filters
                )

                return render_template(
                    "virtual/usage/index.html",
                    session_data=session_data["paginated_data"],
                    filter_options=filter_options,
                    current_filters=current_filters,
                    pagination=session_data["pagination"],
                    google_sheet_url=get_google_sheet_url(selected_virtual_year),
                    district_summaries=district_summaries,
                    overall_summary=overall_summary,
                    last_refreshed=last_refreshed,
                    is_cached=is_cached,
                )

        # If no cache or not full year, compute data fresh
        print(
            f"Computing fresh data for virtual session report {selected_virtual_year}"
        )

        # Get unfiltered data first to ensure we have all districts for summaries
        print("DEBUG: Getting unfiltered data for district summaries...")
        session_data_unfiltered, _, _, filter_options = compute_virtual_session_data(
            selected_virtual_year, date_from, date_to, {}
        )

        # Get list of all districts that appear in the data
        all_districts_in_data = set()
        for session in session_data_unfiltered:
            if session.get("district"):
                all_districts_in_data.add(session["district"])

        print(
            f"DEBUG: Districts found in session_data: {sorted(list(all_districts_in_data))}"
        )

        # Filter to only show main districts by default (unless admin requests all)
        main_districts = {
            "Hickman Mills School District",
            "Grandview School District",
            "Kansas City Kansas Public Schools",
        }

        # Determine which districts to show in the breakdown
        if show_all_districts:
            districts_to_show = all_districts_in_data
        else:
            # Only show main districts when show_all_districts=False
            districts_to_show = {
                d for d in all_districts_in_data if d in main_districts
            }

        print(
            f"DEBUG: Districts to show in breakdown: {sorted(list(districts_to_show))}"
        )

        # Calculate district summaries using the same method as individual district pages
        # This ensures consistency between breakdown cards and individual district pages
        all_district_summaries = {}
        for district_name in districts_to_show:
            try:
                # Use the same calculation method as individual district page
                _, _, _, _, summary_stats = compute_virtual_session_district_data(
                    district_name, selected_virtual_year, date_from, date_to
                )
                # Convert to the format expected by the breakdown template
                all_district_summaries[district_name] = {
                    "teacher_count": summary_stats.get("total_teachers", 0),
                    "total_students": summary_stats.get("total_students", 0),
                    "session_count": summary_stats.get("total_unique_sessions", 0),
                    "total_experiences": summary_stats.get("total_experiences", 0),
                    "organization_count": summary_stats.get("total_organizations", 0),
                    "professional_count": summary_stats.get("total_professionals", 0),
                    "professional_of_color_count": summary_stats.get(
                        "total_professionals_of_color", 0
                    ),
                    "local_professional_count": summary_stats.get(
                        "total_local_professionals", 0
                    ),
                    "school_count": summary_stats.get("total_schools", 0),
                    "local_session_count": summary_stats.get("local_session_count", 0),
                    "poc_session_count": summary_stats.get("poc_session_count", 0),
                    "local_session_percent": summary_stats.get(
                        "local_session_percent", 0
                    ),
                    "poc_session_percent": summary_stats.get("poc_session_percent", 0),
                }
            except Exception as e:
                print(f"DEBUG: Error calculating stats for {district_name}: {str(e)}")
                # Create empty summary if calculation fails
                all_district_summaries[district_name] = {
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

        print(
            f"DEBUG: Calculated district_summaries keys: {list(all_district_summaries.keys()) if all_district_summaries else 'None'}"
        )

        # Now get filtered data for the session table
        session_data, _, overall_summary, _ = compute_virtual_session_data(
            selected_virtual_year, date_from, date_to, current_filters
        )

        # Apply runtime filters (including search) if any
        if any(
            [
                current_filters["career_cluster"],
                current_filters["school"],
                current_filters["district"],
                current_filters["status"],
                current_filters.get("search"),  # Include search filter
            ]
        ):
            session_data = apply_runtime_filters(session_data, current_filters)

        # Filter session_data by allowed_districts for district-scoped users
        if current_user.scope_type == "district" and current_user.allowed_districts:
            import json

            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )
                # Filter session_data to only include sessions from allowed districts
                session_data = [
                    s for s in session_data if s.get("district") in allowed_districts
                ]
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, show no data for safety
                session_data = []

        # Use the calculated district summaries
        district_summaries = all_district_summaries

        print(
            f"DEBUG: Final district_summaries keys: {list(district_summaries.keys()) if district_summaries else 'None'}"
        )

        # Filter district summaries based on user scope
        if current_user.scope_type == "district" and current_user.allowed_districts:
            import json

            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )

                # Create filtered district summaries
                filtered_district_summaries = {}
                for district_name, summary in district_summaries.items():
                    if district_name in allowed_districts:
                        filtered_district_summaries[district_name] = summary

                # Replace the original district_summaries with the filtered version
                district_summaries = filtered_district_summaries
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, show no districts
                district_summaries = {}

        print(
            f"DEBUG: After filtering, district_summaries keys: {list(district_summaries.keys()) if district_summaries else 'None'}"
        )

        # Cache the data if it's a full year query
        if is_full_year:
            # Cache the unfiltered data
            (
                unfiltered_data,
                unfiltered_district_summaries,
                unfiltered_overall_summary,
                _,
            ) = compute_virtual_session_data(
                selected_virtual_year, date_from, date_to, {}  # No filters for cache
            )
            save_virtual_session_cache(
                selected_virtual_year,
                date_from,
                date_to,
                unfiltered_data,
                unfiltered_district_summaries,
                unfiltered_overall_summary,
                filter_options,
            )
            # Set the last refreshed time for this fresh data
            last_refreshed = datetime.now(timezone.utc)

        # Apply sorting and pagination
        # Only group if explicitly requested (group_manual=1)
        # When group_manual=0 or not set, show individual lines (one per teacher registration)
        if current_filters.get("group_manual"):
            session_data = _group_sessions_for_table(session_data)
        session_result = apply_sorting_and_pagination(
            session_data, request.args, current_filters
        )

        return render_template(
            "virtual/usage/index.html",
            session_data=session_result["paginated_data"],
            filter_options=filter_options,
            current_filters=current_filters,
            pagination=session_result["pagination"],
            google_sheet_url=get_google_sheet_url(selected_virtual_year),
            district_summaries=district_summaries,
            overall_summary=overall_summary,
            last_refreshed=last_refreshed,
            is_cached=is_cached,
        )

    @virtual_bp.route("/usage/api/search-teachers", methods=["GET"])
    @login_required
    def search_teachers():
        """Search for teachers by name, returning id, name, school, and district."""
        from flask import jsonify

        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify([])

        # Search by first name, last name, or full name
        search_term = f"%{query}%"
        # NOTE: SQLite doesn't support CONCAT(). Use SQLAlchemy string concat operator instead.
        full_name_expr = Teacher.first_name + " " + Teacher.last_name
        teachers = (
            Teacher.query.filter(
                or_(
                    func.lower(Teacher.first_name).like(func.lower(search_term)),
                    func.lower(Teacher.last_name).like(func.lower(search_term)),
                    func.lower(full_name_expr).like(func.lower(search_term)),
                )
            )
            .options(joinedload(Teacher.school))
            .limit(20)
            .all()
        )

        results = []
        for teacher in teachers:
            school_name = teacher.school.name if teacher.school else None
            district_name = (
                teacher.school.district.name
                if teacher.school and teacher.school.district
                else None
            )
            results.append(
                {
                    "id": teacher.id,
                    "name": f"{teacher.first_name} {teacher.last_name}".strip(),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "school": school_name,
                    "school_id": teacher.school_id,
                    "district": district_name,
                }
            )

        return jsonify(results)

    @virtual_bp.route("/usage/api/search-presenters", methods=["GET"])
    @login_required
    def search_presenters():
        """Search for volunteers/presenters by name, returning id, name, and organization."""
        from flask import jsonify

        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify([])

        # Search by first name, last name, or full name
        search_term = f"%{query}%"
        # NOTE: SQLite doesn't support CONCAT(). Use SQLAlchemy string concat operator instead.
        full_name_expr = Volunteer.first_name + " " + Volunteer.last_name
        volunteers = (
            Volunteer.query.filter(
                or_(
                    func.lower(Volunteer.first_name).like(func.lower(search_term)),
                    func.lower(Volunteer.last_name).like(func.lower(search_term)),
                    func.lower(full_name_expr).like(func.lower(search_term)),
                )
            )
            .limit(20)
            .all()
        )

        results = []
        for volunteer in volunteers:
            # Get primary organization through VolunteerOrganization
            vol_org = (
                VolunteerOrganization.query.filter_by(
                    volunteer_id=volunteer.id, is_primary=True
                )
                .options(joinedload(VolunteerOrganization.organization))
                .first()
            )

            org_name = None
            org_id = None
            if vol_org and vol_org.organization:
                org_name = vol_org.organization.name
                org_id = vol_org.organization_id
            else:
                # Fallback to any organization
                vol_org_any = (
                    VolunteerOrganization.query.filter_by(volunteer_id=volunteer.id)
                    .options(joinedload(VolunteerOrganization.organization))
                    .first()
                )
                if vol_org_any and vol_org_any.organization:
                    org_name = vol_org_any.organization.name
                    org_id = vol_org_any.organization_id

            results.append(
                {
                    "id": volunteer.id,
                    "name": f"{volunteer.first_name} {volunteer.last_name}".strip(),
                    "first_name": volunteer.first_name,
                    "last_name": volunteer.last_name,
                    "organization": org_name,
                    "organization_id": org_id,
                }
            )

        return jsonify(results)

    @virtual_bp.route("/usage/api/create-teacher", methods=["POST"])
    @login_required
    def create_teacher_api():
        """Create a new teacher immediately via API."""
        from flask import jsonify

        from routes.virtual.utils import get_or_create_district, get_or_create_school

        def _norm(s):
            return s.strip() if s else ""

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        f_name = _norm(data.get("first_name", ""))
        l_name = _norm(data.get("last_name", ""))
        school_name = _norm(data.get("school", ""))

        if not f_name or not l_name:
            return jsonify({"error": "First and Last Name are required"}), 400

        try:
            from services.teacher_service import find_or_create_teacher

            # Resolve school_id if provided
            school_id = None
            if school_name:
                district_obj = get_or_create_district(None)
                school_obj = get_or_create_school(school_name, district_obj)
                if school_obj:
                    school_id = school_obj.id

            teacher, is_new, match_info = find_or_create_teacher(
                first_name=f_name,
                last_name=l_name,
                school_id=school_id,
                import_source="manual",
            )
            db.session.commit()

            # Re-query ensure relationships loaded (if needed)
            school_res = teacher.school.name if teacher.school else ""
            district_res = (
                teacher.school.district.name
                if teacher.school and teacher.school.district
                else ""
            )

            return jsonify(
                {
                    "success": True,
                    "id": teacher.id,
                    "name": f"{teacher.first_name} {teacher.last_name}",
                    "school": school_res,
                    "district": district_res,
                }
            )

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @virtual_bp.route("/usage/api/create-presenter", methods=["POST"])
    @login_required
    def create_presenter_api():
        """Create a new presenter/volunteer immediately via API."""
        from flask import jsonify

        def _norm(s):
            return s.strip() if s else ""

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        f_name = _norm(data.get("first_name", ""))
        l_name = _norm(data.get("last_name", ""))
        org_name = _norm(data.get("organization", ""))

        if not f_name:
            return jsonify({"error": "First Name is required"}), 400

        try:
            # Check for existing
            volunteer = Volunteer.query.filter(
                func.lower(Volunteer.first_name) == func.lower(f_name),
                func.lower(Volunteer.last_name) == func.lower(l_name),
            ).first()

            if not volunteer:
                volunteer = Volunteer(first_name=f_name, last_name=l_name)
                db.session.add(volunteer)
                db.session.commit()

            # Handle Org
            if org_name:
                org = Organization.query.filter(
                    func.lower(Organization.name) == func.lower(org_name)
                ).first()
                if not org:
                    org = Organization(name=org_name)
                    db.session.add(org)
                    db.session.commit()

                vol_org = VolunteerOrganization.query.filter_by(
                    volunteer_id=volunteer.id, organization_id=org.id
                ).first()
                if not vol_org:
                    has_primary = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, is_primary=True
                    ).first()
                    vol_org = VolunteerOrganization(
                        volunteer_id=volunteer.id,
                        organization_id=org.id,
                        role="Professional",
                        is_primary=not has_primary,
                        status="Current",
                    )
                    db.session.add(vol_org)
                    db.session.commit()

            # Get primary org for display
            display_org = ""
            primary_vol_org = VolunteerOrganization.query.filter_by(
                volunteer_id=volunteer.id, is_primary=True
            ).first()
            if primary_vol_org and primary_vol_org.organization:
                display_org = primary_vol_org.organization.name
            elif not display_org and org_name:
                display_org = org_name

            return jsonify(
                {
                    "success": True,
                    "id": volunteer.id,
                    "name": f"{volunteer.first_name} {volunteer.last_name}",
                    "organization": display_org,
                }
            )

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @virtual_bp.route("/usage/update-status/<int:event_id>", methods=["POST"])
    @login_required
    @admin_required
    def update_virtual_session_status(event_id):
        """Quick update of event status only."""
        from flask import jsonify

        event = db.session.get(Event, event_id)
        if not event or event.type != EventType.VIRTUAL_SESSION:
            return jsonify({"error": "Event not found"}), 404

        if event.session_host != "APP":
            return jsonify({"error": "Only app-created sessions can be updated"}), 403

        status_str = (
            request.json.get("status")
            if request.is_json
            else request.form.get("status")
        )
        if not status_str:
            return jsonify({"error": "Status is required"}), 400

        try:
            event.status = EventStatus(status_str)
            db.session.commit()
            return jsonify({"success": True, "status": event.status.value})
        except ValueError:
            return jsonify({"error": "Invalid status"}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @virtual_bp.route("/usage/edit/<int:event_id>", methods=["GET", "POST"])
    @login_required
    @admin_required
    def edit_virtual_usage_session(event_id):
        """
        Edit an existing Virtual Session event created via the app UI.

        GET: Returns event data as JSON for populating the edit form
        POST: Updates the event with new data
        """
        event = db.session.get(Event, event_id)
        if not event or event.type != EventType.VIRTUAL_SESSION:
            flash("Event not found.", "danger")
            return redirect(url_for("virtual.virtual_usage"))

        # Only allow editing APP-created sessions
        if event.session_host != "APP":
            flash("Only sessions created in the app can be edited here.", "warning")
            return redirect(url_for("virtual.virtual_usage"))

        if request.method == "GET":
            # Return event data as JSON for the edit form
            from flask import jsonify

            # Get teachers
            teachers_data = []
            for reg in event.teacher_registrations:
                teacher = reg.teacher
                if teacher:
                    teachers_data.append(
                        {
                            "id": teacher.id,
                            "name": f"{teacher.first_name} {teacher.last_name}".strip(),
                            "school": teacher.school.name if teacher.school else "",
                        }
                    )

            # Get presenters
            presenters_data = []
            for participation in event.volunteers:
                vol_org = VolunteerOrganization.query.filter_by(
                    volunteer_id=participation.id, is_primary=True
                ).first()
                org_name = (
                    vol_org.organization.name
                    if vol_org and vol_org.organization
                    else None
                )
                presenters_data.append(
                    {
                        "id": participation.id,
                        "name": f"{participation.first_name} {participation.last_name}".strip(),
                        "organization": org_name or "",
                    }
                )

            return jsonify(
                {
                    "id": event.id,
                    "title": event.title,
                    "date": (
                        event.start_date.strftime("%Y-%m-%d")
                        if event.start_date
                        else ""
                    ),
                    "time": (
                        event.start_date.strftime("%H:%M") if event.start_date else ""
                    ),
                    "duration": event.duration or 60,
                    "session_type": event.additional_information or "",
                    "topic_theme": event.series or "",
                    "session_link": event.registration_link or "",
                    "status": event.status.value if event.status else "Draft",
                    "teachers": teachers_data,
                    "presenters": presenters_data,
                }
            )

        # POST: Update event
        def _norm(s: str | None) -> str:
            return (s or "").strip()

        def _split_name(full_name: str) -> tuple[str, str]:
            full_name = _norm(full_name)
            parts = [p for p in full_name.split() if p]
            if not parts:
                return "", ""
            if len(parts) == 1:
                return parts[0], ""
            return " ".join(parts[:-1]), parts[-1]

        # Update basic fields
        title = _norm(request.form.get("title"))
        session_type = _norm(request.form.get("session_type"))
        topic_theme = _norm(request.form.get("topic_theme"))
        registration_link = _norm(request.form.get("session_link"))

        date_str = _norm(request.form.get("date"))
        time_str = _norm(request.form.get("time"))
        duration_minutes = 60
        try:
            duration_minutes = int(_norm(request.form.get("duration")) or "60")
        except ValueError:
            duration_minutes = 60

        if not title or not date_str or not time_str:
            flash("Title, date, and time are required.", "danger")
            return redirect(url_for("virtual.virtual_usage"))

        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Invalid date/time.", "danger")
            return redirect(url_for("virtual.virtual_usage"))

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Update event
        status_str = _norm(request.form.get("status", "Requested"))
        try:
            event.status = EventStatus(status_str)
        except ValueError:
            event.status = EventStatus.REQUESTED

        event.title = title
        event.start_date = start_dt
        event.end_date = end_dt
        event.duration = duration_minutes
        event.additional_information = session_type or None
        event.series = topic_theme or None
        event.registration_link = registration_link or None

        # Update teachers (remove old, add new)
        EventTeacher.query.filter_by(event_id=event.id).delete()

        from routes.virtual.routes import get_or_create_district, get_or_create_school

        districts_set = set()

        teacher_ids = request.form.getlist("teacher_id[]")
        teacher_names = request.form.getlist("teacher_name[]")
        teacher_schools = request.form.getlist("teacher_school[]")

        for idx, t_id_raw in enumerate(teacher_ids):
            t_id = _norm(t_id_raw)
            t_name = _norm(teacher_names[idx]) if idx < len(teacher_names) else ""

            teacher = None
            if t_id and t_id.isdigit():
                teacher = Teacher.query.get(int(t_id))

            if not teacher and t_name:
                t_first, t_last = _split_name(t_name)
                if t_first and t_last:
                    from services.teacher_service import find_or_create_teacher

                    school_name = (
                        _norm(teacher_schools[idx])
                        if idx < len(teacher_schools)
                        else ""
                    )
                    school_id = None
                    if school_name:
                        district_obj = get_or_create_district(None)
                        school_obj = get_or_create_school(school_name, district_obj)
                        if school_obj:
                            school_id = school_obj.id
                            if school_obj.district:
                                districts_set.add(school_obj.district.name)

                    teacher, is_new, match_info = find_or_create_teacher(
                        first_name=t_first,
                        last_name=t_last,
                        school_id=school_id,
                        import_source="manual",
                    )
                    db.session.flush()

            if not teacher:
                continue

            if teacher.school and teacher.school.district:
                districts_set.add(teacher.school.district.name)

            reg = EventTeacher(
                event_id=event.id,
                teacher_id=teacher.id,
                status="registered",
                is_simulcast=False,
                attendance_confirmed_at=None,
            )
            db.session.add(reg)

        # ---- Quick Create Teachers (Edit) ----
        from services.teacher_service import find_or_create_teacher as _foct_edit

        new_t_first = request.form.getlist("new_teacher_first_name[]")
        new_t_last = request.form.getlist("new_teacher_last_name[]")
        new_t_school = request.form.getlist("new_teacher_school[]")

        for idx, f_name in enumerate(new_t_first):
            f_name = _norm(f_name)
            l_name = _norm(new_t_last[idx]) if idx < len(new_t_last) else ""
            if not f_name or not l_name:
                continue

            school_name = _norm(new_t_school[idx]) if idx < len(new_t_school) else ""
            school_id = None
            if school_name:
                district_obj = get_or_create_district(None)
                school_obj = get_or_create_school(school_name, district_obj)
                if school_obj:
                    school_id = school_obj.id
                    if school_obj.district:
                        districts_set.add(school_obj.district.name)

            teacher, is_new, match_info = _foct_edit(
                first_name=f_name,
                last_name=l_name,
                school_id=school_id,
                import_source="manual",
            )
            db.session.flush()

            if teacher.school and teacher.school.district:
                districts_set.add(teacher.school.district.name)

            # Link to event if not already linked
            existing_reg = EventTeacher.query.filter_by(
                event_id=event.id, teacher_id=teacher.id
            ).first()
            if not existing_reg:
                reg = EventTeacher(
                    event_id=event.id,
                    teacher_id=teacher.id,
                    status="registered",
                    is_simulcast=False,
                    attendance_confirmed_at=None,
                )
                db.session.add(reg)

        # Update presenters (remove old participations, add new)
        EventParticipation.query.filter_by(event_id=event.id).delete()
        event.volunteers.clear()

        presenter_ids = request.form.getlist("presenter_id[]")
        presenter_names = request.form.getlist("presenter_name[]")
        presenter_orgs = request.form.getlist("presenter_org[]")

        for idx, p_id_raw in enumerate(presenter_ids):
            p_id = _norm(p_id_raw)
            p_name = _norm(presenter_names[idx]) if idx < len(presenter_names) else ""
            org_name = _norm(presenter_orgs[idx]) if idx < len(presenter_orgs) else ""

            volunteer = None
            if p_id and p_id.isdigit():
                volunteer = Volunteer.query.get(int(p_id))

            if not volunteer and p_name:
                p_first, p_last = _split_name(p_name)
                if not p_first:
                    continue
                if not p_last:
                    p_last = ""

                vol_q = Volunteer.query.filter(
                    func.lower(Volunteer.first_name) == func.lower(p_first),
                    func.lower(Volunteer.last_name) == func.lower(p_last),
                )
                volunteer = vol_q.first()

                if not volunteer:
                    volunteer = Volunteer(first_name=p_first, last_name=p_last)
                    db.session.add(volunteer)
                    db.session.flush()

            if not volunteer:
                continue

            if org_name:
                org = Organization.query.filter(
                    func.lower(Organization.name) == func.lower(org_name)
                ).first()
                if not org:
                    org = Organization(name=org_name)
                    db.session.add(org)
                    db.session.flush()

                vol_org = VolunteerOrganization.query.filter_by(
                    volunteer_id=volunteer.id, organization_id=org.id
                ).first()
                if not vol_org:
                    has_primary = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, is_primary=True
                    ).first()
                    vol_org = VolunteerOrganization(
                        volunteer_id=volunteer.id,
                        organization_id=org.id,
                        role="Professional",
                        is_primary=not has_primary,
                        status="Current",
                    )
                    db.session.add(vol_org)

            event.add_volunteer(
                volunteer, participant_type="Presenter", status="Confirmed"
            )

        # ---- Quick Create Presenters (Edit) ----
        new_p_first = request.form.getlist("new_presenter_first_name[]")
        new_p_last = request.form.getlist("new_presenter_last_name[]")
        new_p_org = request.form.getlist("new_presenter_org[]")

        for idx, f_name in enumerate(new_p_first):
            f_name = _norm(f_name)
            l_name = _norm(new_p_last[idx]) if idx < len(new_p_last) else ""
            if not f_name:
                continue

            org_name = _norm(new_p_org[idx]) if idx < len(new_p_org) else ""

            # Check if exists
            volunteer = Volunteer.query.filter(
                func.lower(Volunteer.first_name) == func.lower(f_name),
                func.lower(Volunteer.last_name) == func.lower(l_name),
            ).first()

            if not volunteer:
                volunteer = Volunteer(first_name=f_name, last_name=l_name)
                db.session.add(volunteer)
                db.session.flush()

            # Handle Organization
            if org_name:
                org = Organization.query.filter(
                    func.lower(Organization.name) == func.lower(org_name)
                ).first()
                if not org:
                    org = Organization(name=org_name)
                    db.session.add(org)
                    db.session.flush()

                vol_org = VolunteerOrganization.query.filter_by(
                    volunteer_id=volunteer.id, organization_id=org.id
                ).first()
                if not vol_org:
                    has_primary = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, is_primary=True
                    ).first()
                    vol_org = VolunteerOrganization(
                        volunteer_id=volunteer.id,
                        organization_id=org.id,
                        role="Professional",
                        is_primary=not has_primary,
                        status="Current",
                    )
                    db.session.add(vol_org)

            # Link to event
            event.add_volunteer(
                volunteer, participant_type="Presenter", status="Confirmed"
            )

        # Update districts
        event.districts.clear()
        for district_name in districts_set:
            district_obj = get_or_create_district(district_name)
            if district_obj:
                try:
                    event.districts.append(district_obj)
                except Exception:
                    pass

        if districts_set:
            event.district_partner = ", ".join(sorted(districts_set))

        # Sprint 2: Sync text cache fields from EventTeacher/EventParticipation
        from services.teacher_service import sync_event_participant_fields

        sync_event_participant_fields(event)

        db.session.commit()

        # Invalidate caches so the report reflects updated entries
        try:
            from routes.reports.virtual_session import get_current_virtual_year

            year = get_current_virtual_year()
            invalidate_virtual_session_caches(year)
        except Exception:
            pass

        flash("Session updated successfully!", "success")
        return redirect(url_for("virtual.virtual_usage"))

    @virtual_bp.route("/usage/delete/<int:event_id>", methods=["POST"])
    @login_required
    @admin_required
    def delete_virtual_usage_session(event_id):
        """
        Delete a Virtual Session event created via the app UI.

        Only allows deletion of APP-created sessions to prevent accidental
        deletion of imported sessions.
        """
        event = db.session.get(Event, event_id)
        if not event or event.type != EventType.VIRTUAL_SESSION:
            flash("Event not found.", "danger")
            return redirect(url_for("virtual.virtual_usage"))

        # Only allow deleting APP-created sessions
        if event.session_host != "APP":
            flash("Only sessions created in the app can be deleted here.", "warning")
            return redirect(url_for("virtual.virtual_usage"))

        try:
            # Get virtual year for cache invalidation
            from routes.reports.virtual_session import get_current_virtual_year

            year = get_current_virtual_year()

            # Delete EventParticipation records (no cascade relationship)
            EventParticipation.query.filter_by(event_id=event.id).delete()

            # Delete the event (cascades will handle EventTeacher, EventComment, EventAttendanceDetail)
            db.session.delete(event)
            db.session.commit()

            # Invalidate caches so the report reflects the deletion
            try:
                invalidate_virtual_session_caches(year)
            except Exception:
                pass

            flash("Session deleted successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting session: {str(e)}", "danger")

        return redirect(url_for("virtual.virtual_usage"))

    @virtual_bp.route("/usage/create", methods=["POST"])
    @login_required
    @admin_required
    def create_virtual_usage_session():
        """
        Create a new Virtual Session event via the app UI.

        Defaults (per request):
        - Event status: Requested
        - Teacher registrations: registered, attendance not confirmed
        - Presenter participation: Confirmed (as Presenter)
        """

        def _norm(s: str | None) -> str:
            return (s or "").strip()

        def _split_name(full_name: str) -> tuple[str, str]:
            full_name = _norm(full_name)
            parts = [p for p in full_name.split() if p]
            if not parts:
                return "", ""
            if len(parts) == 1:
                return parts[0], ""
            return " ".join(parts[:-1]), parts[-1]

        # ---- Basic event fields ----
        year = _norm(request.form.get("year")) or get_current_virtual_year()
        title = _norm(request.form.get("title"))
        # District will be determined from teachers, not input directly
        session_type = _norm(request.form.get("session_type"))
        topic_theme = _norm(request.form.get("topic_theme"))
        registration_link = _norm(request.form.get("session_link"))

        date_str = _norm(request.form.get("date"))  # YYYY-MM-DD
        time_str = _norm(request.form.get("time"))  # HH:MM
        duration_minutes = 60
        try:
            duration_minutes = int(_norm(request.form.get("duration")) or "60")
        except ValueError:
            duration_minutes = 60
        if duration_minutes <= 0:
            duration_minutes = 60

        if not title or not date_str or not time_str:
            flash("Title, date, and time are required.", "danger")
            return redirect(url_for("virtual.virtual_usage", year=year))

        try:
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Invalid date/time.", "danger")
            return redirect(url_for("virtual.virtual_usage", year=year))

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # ---- District/School helpers (reuse import logic) ----
        from routes.virtual.routes import get_or_create_district, get_or_create_school

        # Collect districts from teachers
        districts_set = set()

        try:
            event = Event(
                title=title,
                type=EventType.VIRTUAL_SESSION,
                format=EventFormat.VIRTUAL,
                start_date=start_dt,
                end_date=end_dt,
                duration=duration_minutes,
                status=EventStatus.REQUESTED,
                additional_information=session_type or None,
                series=topic_theme or None,
                registration_link=registration_link or None,
                session_host="APP",  # Used to distinguish manual/app-entered sessions
            )
            db.session.add(event)
            db.session.flush()  # get event.id

            # ---- Teachers (multi) ----
            teacher_ids = request.form.getlist("teacher_id[]")
            teacher_names = request.form.getlist("teacher_name[]")
            teacher_schools = request.form.getlist("teacher_school[]")

            for idx, t_id_raw in enumerate(teacher_ids):
                t_id = _norm(t_id_raw)
                t_name = _norm(teacher_names[idx]) if idx < len(teacher_names) else ""

                teacher = None

                # If ID provided, use existing teacher
                if t_id and t_id.isdigit():
                    teacher = Teacher.query.get(int(t_id))

                # If no teacher found by ID, try to find/create by name
                if not teacher and t_name:
                    t_first, t_last = _split_name(t_name)
                    if t_first and t_last:
                        from services.teacher_service import find_or_create_teacher

                        school_name = (
                            _norm(teacher_schools[idx])
                            if idx < len(teacher_schools)
                            else ""
                        )
                        school_id = None
                        if school_name:
                            district_obj = get_or_create_district(None)
                            school_obj = get_or_create_school(school_name, district_obj)
                            if school_obj:
                                school_id = school_obj.id
                                if school_obj.district:
                                    districts_set.add(school_obj.district.name)

                        teacher, is_new, match_info = find_or_create_teacher(
                            first_name=t_first,
                            last_name=t_last,
                            school_id=school_id,
                            import_source="manual",
                        )
                        db.session.flush()

                if not teacher:
                    continue

                # Get district from teacher's school
                if teacher.school and teacher.school.district:
                    districts_set.add(teacher.school.district.name)

                # Create registration if not exists
                reg = EventTeacher.query.filter_by(
                    event_id=event.id, teacher_id=teacher.id
                ).first()
                if not reg:
                    reg = EventTeacher(
                        event_id=event.id,
                        teacher_id=teacher.id,
                        status="registered",
                        is_simulcast=False,
                        attendance_confirmed_at=None,
                    )
                    db.session.add(reg)

            # ---- Quick Create Teachers (Create) ----
            from services.teacher_service import find_or_create_teacher as _foct_create

            new_t_first = request.form.getlist("new_teacher_first_name[]")
            new_t_last = request.form.getlist("new_teacher_last_name[]")
            new_t_school = request.form.getlist("new_teacher_school[]")

            for idx, f_name in enumerate(new_t_first):
                f_name = _norm(f_name)
                l_name = _norm(new_t_last[idx]) if idx < len(new_t_last) else ""
                if not f_name or not l_name:
                    continue

                school_name = (
                    _norm(new_t_school[idx]) if idx < len(new_t_school) else ""
                )
                school_id = None
                if school_name:
                    district_obj = get_or_create_district(None)
                    school_obj = get_or_create_school(school_name, district_obj)
                    if school_obj:
                        school_id = school_obj.id
                        if school_obj.district:
                            districts_set.add(school_obj.district.name)

                teacher, is_new, match_info = _foct_create(
                    first_name=f_name,
                    last_name=l_name,
                    school_id=school_id,
                    import_source="manual",
                )
                db.session.flush()

                if teacher.school and teacher.school.district:
                    districts_set.add(teacher.school.district.name)

                # Create registration if not exists
                reg = EventTeacher.query.filter_by(
                    event_id=event.id, teacher_id=teacher.id
                ).first()
                if not reg:
                    reg = EventTeacher(
                        event_id=event.id,
                        teacher_id=teacher.id,
                        status="registered",
                        is_simulcast=False,
                        attendance_confirmed_at=None,
                    )
                    db.session.add(reg)

            # Attach districts to event
            for district_name in districts_set:
                district_obj = get_or_create_district(district_name)
                if district_obj:
                    try:
                        event.districts.append(district_obj)
                    except Exception:
                        pass

            if districts_set:
                event.district_partner = ", ".join(sorted(districts_set))

            # ---- Presenters (multi) ----
            presenter_ids = request.form.getlist("presenter_id[]")
            presenter_names = request.form.getlist("presenter_name[]")
            presenter_orgs = request.form.getlist("presenter_org[]")

            for idx, p_id_raw in enumerate(presenter_ids):
                p_id = _norm(p_id_raw)
                p_name = (
                    _norm(presenter_names[idx]) if idx < len(presenter_names) else ""
                )
                org_name = (
                    _norm(presenter_orgs[idx]) if idx < len(presenter_orgs) else ""
                )

                volunteer = None

                # If ID provided, use existing volunteer
                if p_id and p_id.isdigit():
                    volunteer = Volunteer.query.get(int(p_id))

                # If no volunteer found by ID, try to find/create by name
                if not volunteer and p_name:
                    p_first, p_last = _split_name(p_name)
                    if not p_first:
                        continue
                    if not p_last:
                        p_last = ""

                    # Find existing volunteer by name (case-insensitive)
                    vol_q = Volunteer.query.filter(
                        func.lower(Volunteer.first_name) == func.lower(p_first),
                        func.lower(Volunteer.last_name) == func.lower(p_last),
                    )
                    volunteer = vol_q.first()

                    # Create new volunteer if not found
                    if not volunteer:
                        volunteer = Volunteer(first_name=p_first, last_name=p_last)
                        db.session.add(volunteer)
                        db.session.flush()

                if not volunteer:
                    continue

                # Ensure org exists + primary association
                if org_name:
                    org = Organization.query.filter(
                        func.lower(Organization.name) == func.lower(org_name)
                    ).first()
                    if not org:
                        org = Organization(name=org_name)
                        db.session.add(org)
                        db.session.flush()

                    vol_org = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, organization_id=org.id
                    ).first()
                    if not vol_org:
                        # Check if volunteer has any primary org, if not make this one primary
                        has_primary = VolunteerOrganization.query.filter_by(
                            volunteer_id=volunteer.id, is_primary=True
                        ).first()
                        vol_org = VolunteerOrganization(
                            volunteer_id=volunteer.id,
                            organization_id=org.id,
                            role="Professional",
                            is_primary=not has_primary,  # Primary if no other primary exists
                            status="Current",
                        )
                        db.session.add(vol_org)

                # Link as presenter participation
                event.add_volunteer(
                    volunteer, participant_type="Presenter", status="Confirmed"
                )

            # ---- Quick Create Presenters (Create) ----
            new_p_first = request.form.getlist("new_presenter_first_name[]")
            new_p_last = request.form.getlist("new_presenter_last_name[]")
            new_p_org = request.form.getlist("new_presenter_org[]")

            for idx, f_name in enumerate(new_p_first):
                f_name = _norm(f_name)
                l_name = _norm(new_p_last[idx]) if idx < len(new_p_last) else ""
                if not f_name:
                    continue

                org_name = _norm(new_p_org[idx]) if idx < len(new_p_org) else ""

                # Check if exists
                volunteer = Volunteer.query.filter(
                    func.lower(Volunteer.first_name) == func.lower(f_name),
                    func.lower(Volunteer.last_name) == func.lower(l_name),
                ).first()

                if not volunteer:
                    volunteer = Volunteer(first_name=f_name, last_name=l_name)
                    db.session.add(volunteer)
                    db.session.flush()

                # Handle Organization
                if org_name:
                    org = Organization.query.filter(
                        func.lower(Organization.name) == func.lower(org_name)
                    ).first()
                    if not org:
                        org = Organization(name=org_name)
                        db.session.add(org)
                        db.session.flush()

                    vol_org = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, organization_id=org.id
                    ).first()
                    if not vol_org:
                        has_primary = VolunteerOrganization.query.filter_by(
                            volunteer_id=volunteer.id, is_primary=True
                        ).first()
                        vol_org = VolunteerOrganization(
                            volunteer_id=volunteer.id,
                            organization_id=org.id,
                            role="Professional",
                            is_primary=not has_primary,
                            status="Current",
                        )
                        db.session.add(vol_org)

                event.add_volunteer(
                    volunteer, participant_type="Presenter", status="Confirmed"
                )

            # Sprint 2: Sync text cache fields from EventTeacher/EventParticipation
            from services.teacher_service import sync_event_participant_fields

            sync_event_participant_fields(event)

            db.session.commit()

            # Invalidate caches so the report reflects new entries
            try:
                invalidate_virtual_session_caches(year)
            except Exception:
                pass

            flash("Virtual session created.", "success")
            return redirect(url_for("virtual.virtual_usage", year=year))

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating virtual session: {e}", "danger")
            return redirect(url_for("virtual.virtual_usage", year=year))
