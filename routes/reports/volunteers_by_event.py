import io
from datetime import datetime, timezone, timedelta

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func

from models import db, eagerload_volunteer_bundle
from models.event import Event, EventStatus, EventType
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, Volunteer
from routes.reports.common import get_current_school_year, get_school_year_date_range

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
        return [EventType.CAREER_FAIR, EventType.DATA_VIZ]

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
    return unique or [EventType.CAREER_FAIR, EventType.DATA_VIZ]


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
    query = db.session.query(
        Volunteer.id,
        Volunteer.first_name,
        Volunteer.last_name,
        func.count(EventParticipation.id).label('event_count'),
        func.max(Event.start_date).label('last_event_date'),
        Organization.name.label('organization_name')
    ).join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)\
    .join(Event, Event.id == EventParticipation.event_id)\
    .outerjoin(VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id)\
    .outerjoin(Organization, VolunteerOrganization.organization_id == Organization.id)\
    .filter(
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
        Event.type.in_(selected_types),
        EventParticipation.status.in_([
            "Attended", "Completed", "Successfully Completed", "Simulcast"
        ]),
        Volunteer.exclude_from_reports == False
    )
    
    if title_contains:
        like = f"%{title_contains.strip()}%"
        query = query.filter(Event.title.ilike(like))
    
    query = query.group_by(
        Volunteer.id, 
        Volunteer.first_name, 
        Volunteer.last_name,
        Organization.name
    ).order_by(func.max(Event.start_date).desc())
    
    results = query.all()
    
    # Get volunteer IDs for additional queries
    volunteer_ids = [row.id for row in results]
    
    # Single query for total volunteer counts (all time)
    total_counts = {}
    if volunteer_ids:
        total_count_query = db.session.query(
            EventParticipation.volunteer_id,
            func.count(EventParticipation.id).label('total_count')
        ).join(Event, Event.id == EventParticipation.event_id)\
        .filter(
            EventParticipation.volunteer_id.in_(volunteer_ids),
            EventParticipation.status.in_([
                "Attended", "Completed", "Successfully Completed", "Simulcast"
            ]),
            Event.status == EventStatus.COMPLETED
        ).group_by(EventParticipation.volunteer_id)
        
        for row in total_count_query.all():
            total_counts[row.volunteer_id] = row.total_count
    
    # Single query for future events
    future_events = {}
    if volunteer_ids:
        future_query = db.session.query(
            EventParticipation.volunteer_id,
            Event.id,
            Event.title,
            Event.start_date,
            Event.type
        ).join(Event, Event.id == EventParticipation.event_id)\
        .filter(
            EventParticipation.volunteer_id.in_(volunteer_ids),
            Event.start_date > datetime.now(timezone.utc),
            Event.status.in_([
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
            ]),
            EventParticipation.status.notin_([
                "Cancelled", "No Show", "Declined", "Withdrawn"
            ])
        ).order_by(EventParticipation.volunteer_id, Event.start_date)
        
        for row in future_query.all():
            if row.volunteer_id not in future_events:
                future_events[row.volunteer_id] = []
            future_events[row.volunteer_id].append({
                'id': row.id,
                'title': row.title,
                'date': row.start_date,
                'type': row.type.value if row.type else None
            })
    
    # Convert to the expected format
    volunteers = []
    for row in results:
        volunteer_id = row.id
        future_events_list = future_events.get(volunteer_id, [])
        
        volunteers.append({
            'id': volunteer_id,
            'name': f"{row.first_name} {row.last_name}",
            'email': None,  # We'll get this separately if needed
            'organization': row.organization_name or 'Independent',
            'organization_id': None,  # We'll get this separately if needed
            'skills': "",  # We'll get this separately if needed
            'event_count': int(row.event_count or 0),
            'last_event_date': row.last_event_date,
            'last_non_internal_email_date': None,  # We'll get this separately if needed
            'total_volunteer_count': total_counts.get(volunteer_id, 0),
            'future_events': future_events_list,
            'future_events_count': len(future_events_list),
            'events': []  # We'll populate this if needed for detailed view
        })
    
    # Sort by name
    volunteers.sort(key=lambda r: (r["name"] or "").lower())
    return volunteers


def load_routes(bp: Blueprint):
    @bp.route("/reports/volunteers/by-event")
    @login_required
    def volunteers_by_event_report():
        # Params: event_types (comma-separated), date_from, date_to, school_year, title
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        school_year = request.args.get("school_year")
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")
        title_contains = request.args.get("title", "").strip() or None

        if school_year:
            start_date, end_date = get_school_year_date_range(school_year)
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)

        volunteers = _query_volunteers(
            start_date, end_date, selected_types, title_contains
        )

        # For display: build concise events string per volunteer
        for v in volunteers:
            # Combine past and future events for display
            all_events = v["events"] + v.get("future_events", [])

            # Sort by date (past events first, then future)
            all_events.sort(key=lambda x: x.get("date") or datetime.min)

            titles = [e["title"] for e in all_events]
            unique_titles = []
            seen = set()
            for t in titles:
                if t and t not in seen:
                    seen.add(t)
                    unique_titles.append(t)

            # Show past events first, then indicate future events
            past_titles = [e["title"] for e in v["events"] if e.get("title")]
            future_titles = [
                e["title"] for e in v.get("future_events", []) if e.get("title")
            ]

            display_parts = []
            if past_titles:
                display_parts.append("; ".join(past_titles[:3]))
            if future_titles:
                future_display = " [Upcoming: " + "; ".join(future_titles[:2]) + "]"
                display_parts.append(future_display)

            v["events_display"] = "".join(display_parts)
            if len(unique_titles) > 5:
                v["events_display"] += " …"

            # Ensure organization and skills strings for UI
            v["organization"] = v.get("organization") or "None"
            v["skills"] = v.get("skills") or ""

        # Build list of selectable event types for the form
        type_choices = _event_type_choices()
        selected_type_values = [t.value for t in selected_types]

        # Build querystring for export link
        export_params = {
            "event_types": ",".join(selected_type_values),
            "date_from": start_date.strftime("%Y-%m-%d") if start_date else "",
            "date_to": end_date.strftime("%Y-%m-%d") if end_date else "",
        }
        if title_contains:
            export_params["title"] = title_contains
        if school_year:
            export_params["school_year"] = school_year

        return render_template(
            "reports/volunteers/volunteers_by_event.html",
            volunteers=volunteers,
            type_choices=type_choices,
            selected_types=selected_type_values,
            school_year=school_year or "",
            date_from=start_date.strftime("%Y-%m-%d") if start_date else "",
            date_to=end_date.strftime("%Y-%m-%d") if end_date else "",
            title_contains=title_contains or "",
            export_params=export_params,
            now=datetime.now(),
        )

    @bp.route("/reports/volunteers/by-event/excel")
    @login_required
    def volunteers_by_event_excel():
        raw_types = request.args.getlist("event_types")
        if not raw_types:
            raw_types = (
                request.args.get("event_types", "").split(",")
                if request.args.get("event_types")
                else None
            )
        selected_types = _normalize_selected_types(raw_types)

        school_year = request.args.get("school_year")
        date_from_param = request.args.get("date_from")
        date_to_param = request.args.get("date_to")
        title_contains = request.args.get("title", "").strip() or None

        if school_year:
            start_date, end_date = get_school_year_date_range(school_year)
        else:
            start_date, end_date = _default_date_range()
            start_date = _parse_date(date_from_param, start_date)
            end_date = _parse_date(date_to_param, end_date)

        volunteers = _query_volunteers(
            start_date, end_date, selected_types, title_contains
        )

        # Build rows for Excel
        rows = []
        for v in volunteers:
            last_date = (
                v["last_event_date"].strftime("%m/%d/%y")
                if v["last_event_date"]
                else ""
            )
            last_email_date = (
                v["last_non_internal_email_date"].strftime("%m/%d/%y")
                if v["last_non_internal_email_date"]
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
                    "Events (Count)": v["event_count"],
                    "Last Volunteered Date": last_volunteered_display,
                    "Last Email": last_email_date,
                    "# Times": v.get("total_volunteer_count", 0),
                    "Event Titles": "; ".join(sorted(set(all_titles))),
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
            ws.set_column("E:E", 14)  # Events (Count)
            ws.set_column("F:F", 20)  # Last Volunteered Date (with upcoming info)
            ws.set_column("G:G", 12)  # Last Email
            ws.set_column("H:H", 10)  # # Times
            ws.set_column("I:I", 60)  # Event Titles

        output.seek(0)

        # Filename
        type_suffix = (
            "_" + ",".join([t.value for t in selected_types]) if selected_types else ""
        )
        if school_year:
            filename = f"Volunteers_By_Event{type_suffix}_{school_year[:2]}-{school_year[2:]}.xlsx"
        else:
            filename = f"Volunteers_By_Event{type_suffix}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name=filename,
            as_attachment=True,
        )
