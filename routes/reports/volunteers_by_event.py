import io
from datetime import datetime, timedelta, timezone

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func

from models import db, eagerload_volunteer_bundle
from models.contact import Email
from models.event import Event, EventStatus, EventType
from models.organization import Organization, VolunteerOrganization
from models.volunteer import (
    ConnectorData,
    EventParticipation,
    Skill,
    Volunteer,
    VolunteerSkill,
)
from routes.reports.common import get_current_school_year

# Blueprint is provided by parent reports package via load_routes
volunteers_by_event_bp = Blueprint("volunteers_by_event", __name__)


def _parse_date(value: str, default: datetime | None = None) -> datetime | None:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        return default


def _default_date_range():
    # Past 365 days by default
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)
    return start, end


def _event_type_choices():
    """Return all event types with friendly labels, sorted alphabetically."""

    def friendly_label(value: str) -> str:
        label = value.replace("_", " ").title()
        # Fix common acronym casing
        fixes = {
            "Fafsa": "FAFSA",
            "Dia": "DIA",
            "P2gd": "P2GD",
            "Sla": "SLA",
            "Bfi": "BFI",
        }
        return fixes.get(label, label)

    choices = [(et.value, friendly_label(et.value)) for et in EventType]
    # Sort by label
    choices.sort(key=lambda x: x[1].lower())
    return choices


def _normalize_selected_types(raw_types: list[str] | None) -> list[EventType]:
    if not raw_types:
        # Return all event types as default (select all)
        return list(EventType)

    normalized: list[EventType] = []
    values = {et.value: et for et in EventType}
    names = {et.name.lower(): et for et in EventType}
    for t in raw_types:
        if not t:
            continue
        t_norm = t.strip().lower()
        if t_norm in values:
            normalized.append(values[t_norm])
        elif t_norm in names:
            normalized.append(names[t_norm])
    # De-duplicate while preserving order
    seen = set()
    unique = []
    for et in normalized:
        if et not in seen:
            seen.add(et)
            unique.append(et)
    return unique or list(EventType)  # Fallback to all event types


def _get_primary_org_name(volunteer: Volunteer) -> str | None:
    # Prefer explicit primary org from association table
    if getattr(volunteer, "volunteer_organizations", None):
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
    # Avoid showing raw Salesforce IDs stored in organization_name
    org_name = getattr(volunteer, "organization_name", None)
    if org_name and not (len(org_name) == 18 and org_name.isalnum()):
        return org_name
    return None


def _get_primary_org_id(volunteer: Volunteer) -> int | None:
    # Prefer explicit primary org from association table
    if getattr(volunteer, "volunteer_organizations", None):
        primary = next(
            (vo for vo in volunteer.volunteer_organizations if vo.is_primary), None
        )
        if primary and primary.organization and primary.organization.id:
            return primary.organization.id
        # Fall back to first org if no primary
        first = (
            volunteer.volunteer_organizations[0].organization
            if volunteer.volunteer_organizations
            else None
        )
        if first and first.id:
            return first.id
    return None


def _query_volunteers(
    start_date: datetime,
    end_date: datetime,
    selected_types: list[EventType],
    title_contains: str | None,
):
    """
    Optimized query for volunteers by event using single queries with proper aggregation.
    Eliminates N+1 query problems and reduces database load significantly.
    """
    # Single query with proper joins and aggregation
    query = (
        db.session.query(
            Volunteer.id,
            Volunteer.first_name,
            Volunteer.last_name,
            func.count(EventParticipation.id).label("event_count"),
            func.max(Event.start_date).label("last_event_date"),
            Organization.name.label("organization_name"),
        )
        .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
        .join(Event, Event.id == EventParticipation.event_id)
        .outerjoin(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        )
        .outerjoin(
            Organization, VolunteerOrganization.organization_id == Organization.id
        )
        .filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            Event.type.in_(selected_types),
            EventParticipation.status.in_(
                ["Attended", "Completed", "Successfully Completed", "Simulcast"]
            ),
            Volunteer.exclude_from_reports == False,
        )
    )

    if title_contains:
        like = f"%{title_contains.strip()}%"
        query = query.filter(Event.title.ilike(like))

    query = query.group_by(
        Volunteer.id, Volunteer.first_name, Volunteer.last_name, Organization.name
    ).order_by(func.max(Event.start_date).desc())

    results = query.all()

    # Get volunteer IDs for additional queries
    volunteer_ids = [row.id for row in results]

    # Single query for total volunteer counts (all time)
    total_counts = {}
    if volunteer_ids:
        total_count_query = (
            db.session.query(
                EventParticipation.volunteer_id,
                func.count(EventParticipation.id).label("total_count"),
            )
            .join(Event, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id.in_(volunteer_ids),
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed", "Simulcast"]
                ),
                Event.status == EventStatus.COMPLETED,
            )
            .group_by(EventParticipation.volunteer_id)
        )

        for row in total_count_query.all():
            total_counts[row.volunteer_id] = row.total_count

    # Single query for future events
    future_events = {}
    if volunteer_ids:
        future_query = (
            db.session.query(
                EventParticipation.volunteer_id,
                Event.id,
                Event.title,
                Event.start_date,
                Event.type,
            )
            .join(Event, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id.in_(volunteer_ids),
                Event.start_date > datetime.now(timezone.utc),
                Event.status.in_(
                    [
                        EventStatus.CONFIRMED,
                        EventStatus.PUBLISHED,
                        EventStatus.REQUESTED,
                    ]
                ),
                EventParticipation.status.notin_(
                    ["Cancelled", "No Show", "Declined", "Withdrawn"]
                ),
            )
            .order_by(EventParticipation.volunteer_id, Event.start_date)
        )

        for row in future_query.all():
            if row.volunteer_id not in future_events:
                future_events[row.volunteer_id] = []
            future_events[row.volunteer_id].append(
                {
                    "id": row.id,
                    "title": row.title,
                    "date": row.start_date,
                    "type": row.type.value if row.type else None,
                }
            )

    # Convert to the expected format
    volunteers = []
    for row in results:
        volunteer_id = row.id
        future_events_list = future_events.get(volunteer_id, [])

        volunteers.append(
            {
                "id": volunteer_id,
                "name": f"{row.first_name} {row.last_name}",
                "email": None,  # We'll get this separately if needed
                "organization": row.organization_name or "Independent",
                "organization_id": None,  # We'll get this separately if needed
                "skills": "",  # We'll get this separately if needed
                "event_count": int(row.event_count or 0),
                "last_event_date": row.last_event_date,
                "last_non_internal_email_date": None,  # We'll get this separately if needed
                "total_volunteer_count": total_counts.get(volunteer_id, 0),
                "future_events": future_events_list,
                "future_events_count": len(future_events_list),
                "events": [],  # We'll populate this if needed for detailed view
            }
        )

    # Sort by name
    volunteers.sort(key=lambda r: (r["name"] or "").lower())
    return volunteers


def _query_volunteers_with_search(
    start_date: datetime,
    end_date: datetime,
    search_query: str | None,
    selected_types: list[EventType],
    page: int = 1,
    per_page: int = 25,
    connector_only: bool = False,
):
    """
    Query volunteers with wide search functionality (OR mode).
    Searches across volunteer names, organizations, event titles, and event types.
    """
    # First get unique volunteers who participated in events (like main volunteers page)
    volunteer_subquery = (
        db.session.query(
            EventParticipation.volunteer_id,
            func.count(EventParticipation.id).label("event_count"),
            func.max(Event.start_date).label("last_event_date"),
        )
        .join(Event, Event.id == EventParticipation.event_id)
        .filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            Event.type.in_(selected_types),
            EventParticipation.status.in_(
                ["Attended", "Completed", "Successfully Completed", "Simulcast"]
            ),
        )
        .group_by(EventParticipation.volunteer_id)
        .subquery()
    )

    # Main query - get unique volunteers only (no organization joins to prevent duplicates)
    query = (
        db.session.query(
            Volunteer.id,
            Volunteer.first_name,
            Volunteer.last_name,
            volunteer_subquery.c.event_count,
            volunteer_subquery.c.last_event_date,
        )
        .join(volunteer_subquery, Volunteer.id == volunteer_subquery.c.volunteer_id)
        .outerjoin(VolunteerSkill, Volunteer.id == VolunteerSkill.volunteer_id)
        .outerjoin(Skill, VolunteerSkill.skill_id == Skill.id)
        .filter(Volunteer.exclude_from_reports == False)
    )

    # Apply search if provided (always uses wide/OR search)
    if search_query:
        # Split search query into terms and remove empty strings
        search_terms = [term.strip() for term in search_query.split() if term.strip()]

        # Create subquery for event-based search
        event_search_subquery = (
            db.session.query(EventParticipation.volunteer_id)
            .join(Event, Event.id == EventParticipation.event_id)
            .filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                Event.status == EventStatus.COMPLETED,
                Event.type.in_(selected_types),
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed", "Simulcast"]
                ),
            )
            .subquery()
        )

        # OR mode: Match any term across all fields
        search_conditions = []
        for term in search_terms:
            # Check if any volunteer matches this term in events
            event_matches = (
                db.session.query(event_search_subquery.c.volunteer_id)
                .filter(
                    db.or_(
                        Event.title.ilike(f"%{term}%"), Event.type.ilike(f"%{term}%")
                    )
                )
                .exists()
            )

            # Check if any volunteer matches this term in organizations
            org_matches = (
                db.session.query(VolunteerOrganization.volunteer_id)
                .join(
                    Organization,
                    VolunteerOrganization.organization_id == Organization.id,
                )
                .filter(
                    Organization.name.ilike(f"%{term}%"),
                    VolunteerOrganization.volunteer_id.in_(
                        db.session.query(volunteer_subquery.c.volunteer_id)
                    ),
                )
                .exists()
            )

            search_conditions.append(
                db.or_(
                    Volunteer.first_name.ilike(f"%{term}%"),
                    Volunteer.last_name.ilike(f"%{term}%"),
                    Volunteer.organization_name.ilike(f"%{term}%"),
                    Skill.name.ilike(f"%{term}%"),
                    event_matches,
                    org_matches,
                )
            )
        query = query.filter(db.or_(*search_conditions))

    # Apply connector filter if requested
    if connector_only:
        # Use INNER JOIN to only get volunteers with VALID connector data (with user_auth_id)
        query = query.join(ConnectorData, Volunteer.id == ConnectorData.volunteer_id)
        query = query.filter(
            ConnectorData.user_auth_id.isnot(None), ConnectorData.user_auth_id != ""
        )

    query = query.group_by(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        volunteer_subquery.c.event_count,
        volunteer_subquery.c.last_event_date,
    ).order_by(Volunteer.first_name, Volunteer.last_name)

    # Apply pagination
    total_count = query.count()
    paginated_query = query.offset((page - 1) * per_page).limit(per_page)
    results = paginated_query.all()

    # Get volunteer IDs for additional queries
    volunteer_ids = [row.id for row in results]

    # Single query for total volunteer counts (all time)
    total_counts = {}
    if volunteer_ids:
        total_count_query = (
            db.session.query(
                EventParticipation.volunteer_id,
                func.count(EventParticipation.id).label("total_count"),
            )
            .join(Event, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id.in_(volunteer_ids),
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed", "Simulcast"]
                ),
                Event.status == EventStatus.COMPLETED,
            )
            .group_by(EventParticipation.volunteer_id)
        )

        for row in total_count_query.all():
            total_counts[row.volunteer_id] = row.total_count

    # Single query for future events
    future_events = {}
    if volunteer_ids:
        future_query = (
            db.session.query(
                EventParticipation.volunteer_id,
                Event.id,
                Event.title,
                Event.start_date,
                Event.type,
            )
            .join(Event, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id.in_(volunteer_ids),
                Event.start_date > datetime.now(timezone.utc),
                Event.status.in_(
                    [
                        EventStatus.CONFIRMED,
                        EventStatus.PUBLISHED,
                        EventStatus.REQUESTED,
                    ]
                ),
                EventParticipation.status.notin_(
                    ["Cancelled", "No Show", "Declined", "Withdrawn"]
                ),
            )
            .order_by(EventParticipation.volunteer_id, Event.start_date)
        )

        for row in future_query.all():
            if row.volunteer_id not in future_events:
                future_events[row.volunteer_id] = []
            future_events[row.volunteer_id].append(
                {
                    "id": row.id,
                    "title": row.title,
                    "date": row.start_date,
                    "type": row.type.value if row.type else None,
                }
            )

    # Get volunteer details (emails, skills, etc.) for display
    volunteer_details = {}
    if volunteer_ids:
        # Get volunteers and their last email dates
        volunteers_query = db.session.query(
            Volunteer.id,
            Volunteer.last_email_date,
            Volunteer.last_non_internal_email_date,
        ).filter(Volunteer.id.in_(volunteer_ids))

        # Get primary emails for volunteers
        emails_query = db.session.query(Email.contact_id, Email.email).filter(
            Email.contact_id.in_(volunteer_ids), Email.primary == True
        )

        # Get skills for volunteers
        skills_query = (
            db.session.query(VolunteerSkill.volunteer_id, Skill.name)
            .join(Skill, VolunteerSkill.skill_id == Skill.id)
            .filter(VolunteerSkill.volunteer_id.in_(volunteer_ids))
            .order_by(VolunteerSkill.volunteer_id, Skill.name)
        )

        # Get connector data for volunteers
        connector_query = db.session.query(
            ConnectorData.volunteer_id, ConnectorData.user_auth_id
        ).filter(ConnectorData.volunteer_id.in_(volunteer_ids))

        # Create mappings
        email_map = {row.contact_id: row.email for row in emails_query.all()}

        # Group skills by volunteer_id
        skills_map = {}
        for row in skills_query.all():
            if row.volunteer_id not in skills_map:
                skills_map[row.volunteer_id] = []
            skills_map[row.volunteer_id].append(row.name)

        # Convert to comma-separated strings
        skills_map = {k: ", ".join(v) for k, v in skills_map.items()}

        # Create connector mapping
        connector_map = {
            row.volunteer_id: row.user_auth_id for row in connector_query.all()
        }

        for row in volunteers_query.all():
            user_auth_id = connector_map.get(row.id)
            # Use the more recent of the two email dates
            last_email_date = row.last_email_date
            if row.last_non_internal_email_date and row.last_email_date:
                last_email_date = max(
                    row.last_email_date, row.last_non_internal_email_date
                )
            elif row.last_non_internal_email_date:
                last_email_date = row.last_non_internal_email_date

            volunteer_details[row.id] = {
                "email": email_map.get(row.id),
                "skills": skills_map.get(row.id, ""),
                "last_email_date": last_email_date,
                "connector_profile_url": (
                    f"https://prepkc.nepris.com/app/user/{user_auth_id}"
                    if user_auth_id
                    else None
                ),
            }

    # Get organization information for volunteers (like main volunteers page)
    volunteer_orgs = {}
    if volunteer_ids:
        # Get volunteer organizations with proper organization names
        org_query = (
            db.session.query(
                VolunteerOrganization.volunteer_id,
                Organization.name,
                Organization.id,
                VolunteerOrganization.is_primary,
                VolunteerOrganization.role,
            )
            .join(
                Organization, VolunteerOrganization.organization_id == Organization.id
            )
            .filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids))
            .order_by(VolunteerOrganization.is_primary.desc(), Organization.name)
        )

        for row in org_query.all():
            if row.volunteer_id not in volunteer_orgs:
                volunteer_orgs[row.volunteer_id] = []
            volunteer_orgs[row.volunteer_id].append(
                {
                    "name": row.name,
                    "id": row.id,
                    "is_primary": row.is_primary,
                    "role": row.role,
                }
            )

    # Convert to the expected format
    volunteers = []
    for row in results:
        volunteer_id = row.id
        future_events_list = future_events.get(volunteer_id, [])
        details = volunteer_details.get(volunteer_id, {})

        # Get primary organization or first organization
        orgs = volunteer_orgs.get(volunteer_id, [])
        primary_org = next((org for org in orgs if org["is_primary"]), None)
        if not primary_org and orgs:
            primary_org = orgs[0]  # Use first org if no primary

        # Fallback to volunteer's direct organization_name if no relationship
        if not primary_org:
            # Get the volunteer object to access organization_name
            volunteer_obj = db.session.get(Volunteer, volunteer_id)
            org_name = volunteer_obj.organization_name if volunteer_obj else None
            if org_name and not (len(org_name) == 18 and org_name.isalnum()):
                primary_org = {
                    "name": org_name,
                    "id": None,
                    "is_primary": True,
                    "role": None,
                }
            else:
                primary_org = {
                    "name": "Independent",
                    "id": None,
                    "is_primary": True,
                    "role": None,
                }

        volunteers.append(
            {
                "id": volunteer_id,
                "name": f"{row.first_name} {row.last_name}",
                "email": details.get("email"),
                "organization": primary_org["name"],
                "organization_id": primary_org["id"],
                "skills": details.get("skills", ""),
                "event_count": int(row.event_count or 0),
                "last_event_date": row.last_event_date,
                "last_email_date": details.get("last_email_date"),
                "connector_profile_url": details.get("connector_profile_url"),
                "total_volunteer_count": total_counts.get(volunteer_id, 0),
                "future_events": future_events_list,
                "future_events_count": len(future_events_list),
                "events": [],  # We'll populate this if needed for detailed view
            }
        )

    # Volunteers are already sorted by name from the database query

    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages

    return {
        "volunteers": volunteers,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_num": page - 1 if has_prev else None,
            "next_num": page + 1 if has_next else None,
        },
    }


def load_routes(bp: Blueprint):
    @bp.route("/reports/volunteers/by-event")
    @login_required
    def volunteers_by_event_report():
        # Params: search, event_types, date_from, date_to, all_past_data, last_2_years, page, per_page
        search_query = request.args.get("search", "").strip()

        # Pagination parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))  # Default 25 per page

        # Handle event types
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        all_past_data = request.args.get("all_past_data") == "1"
        last_2_years = request.args.get("last_2_years") == "1"
        connector_only = request.args.get("connector_only") == "1"

        # Ensure mutual exclusivity - if all_past_data is selected, uncheck last_2_years
        if all_past_data:
            last_2_years = False
        # If neither is selected, default to last_2_years
        elif not all_past_data and not last_2_years:
            last_2_years = True
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")

        if all_past_data:
            # Search all historical data - set a very early start date
            start_date = datetime(2000, 1, 1)  # Very early date to capture all data
            end_date = datetime.now(timezone.utc)  # Current time
        elif last_2_years:
            # Search last 2 years
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=730)  # 2 years = 730 days
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)

        result = _query_volunteers_with_search(
            start_date,
            end_date,
            search_query,
            selected_types,
            page,
            per_page,
            connector_only,
        )
        volunteers = result["volunteers"]
        pagination = result["pagination"]

        # Ensure organization and skills strings for UI
        for v in volunteers:
            v["organization"] = v.get("organization") or "None"
            v["skills"] = v.get("skills") or ""

        # Build querystring for export link
        export_params = {
            "date_from": (
                start_date.strftime("%Y-%m-%d")
                if start_date and not all_past_data and not last_2_years
                else ""
            ),
            "date_to": (
                end_date.strftime("%Y-%m-%d")
                if end_date and not all_past_data and not last_2_years
                else ""
            ),
        }
        if search_query:
            export_params["search"] = search_query
        if selected_types:
            export_params["event_types"] = [t.value for t in selected_types]
        if all_past_data:
            export_params["all_past_data"] = "1"
        if last_2_years:
            export_params["last_2_years"] = "1"

        return render_template(
            "reports/volunteers/volunteers_by_event.html",
            volunteers=volunteers,
            pagination=pagination,
            search_query=search_query,
            all_past_data=all_past_data,
            last_2_years=last_2_years,
            connector_only=connector_only,
            date_from=(
                start_date.strftime("%Y-%m-%d")
                if start_date and not all_past_data and not last_2_years
                else ""
            ),
            date_to=(
                end_date.strftime("%Y-%m-%d")
                if end_date and not all_past_data and not last_2_years
                else ""
            ),
            export_params=export_params,
            now=datetime.now(),
            type_choices=_event_type_choices(),
            selected_types=[t.value for t in selected_types],
        )

    @bp.route("/reports/volunteers/by-event/excel")
    @login_required
    def volunteers_by_event_excel():
        search_query = request.args.get("search", "").strip()

        # Handle event types
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        all_past_data = request.args.get("all_past_data") == "1"
        last_2_years = request.args.get("last_2_years") == "1"
        connector_only = request.args.get("connector_only") == "1"

        # Ensure mutual exclusivity - if all_past_data is selected, uncheck last_2_years
        if all_past_data:
            last_2_years = False
        # If neither is selected, default to last_2_years
        elif not all_past_data and not last_2_years:
            last_2_years = True
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")

        if all_past_data:
            # Search all historical data - set a very early start date
            start_date = datetime(2000, 1, 1)  # Very early date to capture all data
            end_date = datetime.now(timezone.utc)  # Current time
        elif last_2_years:
            # Search last 2 years
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=730)  # 2 years = 730 days
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)

        # For Excel export, get all results (no pagination)
        result = _query_volunteers_with_search(
            start_date,
            end_date,
            search_query,
            selected_types,
            page=1,
            per_page=10000,
            connector_only=connector_only,
        )
        volunteers = result["volunteers"]

        # Build rows for Excel
        rows = []
        for v in volunteers:
            last_date = (
                v["last_event_date"].strftime("%m/%d/%y")
                if v["last_event_date"]
                else ""
            )
            last_email_date = (
                v["last_email_date"].strftime("%m/%d/%y")
                if v["last_email_date"]
                else ""
            )
            # Combine past and future events for Excel
            past_titles = [e["title"] for e in v["events"] if e.get("title")]
            future_titles = [
                e["title"] for e in v.get("future_events", []) if e.get("title")
            ]

            all_titles = past_titles + future_titles
            future_count = v.get("future_events_count", 0)

            # Combine last volunteered date with future events info
            last_volunteered_display = last_date
            if future_count > 0:
                last_volunteered_display += f" ({future_count} upcoming)"

            rows.append(
                {
                    "Name": v["name"],
                    "Email": v["email"],
                    "Organization": v.get("organization") or "",
                    "Skills": v.get("skills") or "",
                    "Last Volunteered Date": last_volunteered_display,
                    "Last Email": last_email_date,
                    "Past Events": v.get("total_volunteer_count", 0),
                }
            )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df = pd.DataFrame(rows)
            df.to_excel(writer, index=False, sheet_name="Volunteers")
            ws = writer.sheets["Volunteers"]
            ws.set_column("A:A", 28)  # Name
            ws.set_column("B:B", 36)  # Email
            ws.set_column("C:C", 26)  # Organization
            ws.set_column("D:D", 40)  # Skills
            ws.set_column("E:E", 20)  # Last Volunteered Date (with upcoming info)
            ws.set_column("F:F", 12)  # Last Email
            ws.set_column("G:G", 12)  # Past Events

        output.seek(0)

        # Filename
        type_suffix = (
            "_" + ",".join([t.value for t in selected_types]) if selected_types else ""
        )
        if all_past_data:
            filename = f"Volunteers_By_Event{type_suffix}_All_Past_Data.xlsx"
        elif last_2_years:
            filename = f"Volunteers_By_Event{type_suffix}_Last_2_Years.xlsx"
        else:
            filename = f"Volunteers_By_Event{type_suffix}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name=filename,
            as_attachment=True,
        )
