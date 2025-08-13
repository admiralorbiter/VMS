import io
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required

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
    end = datetime.utcnow()
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


def _query_volunteers(
    start_date: datetime,
    end_date: datetime,
    selected_types: list[EventType],
    title_contains: str | None,
):
    # Base query joining volunteers to their participations and events
    query = (
        db.session.query(Volunteer, Event, EventParticipation)
        .join(EventParticipation, EventParticipation.volunteer_id == Volunteer.id)
        .join(Event, Event.id == EventParticipation.event_id)
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

    # Fetch and aggregate by volunteer
    rows = eagerload_volunteer_bundle(query).all()

    aggregated: dict[int, dict] = {}
    for volunteer, event, participation in rows:
        rec = aggregated.get(volunteer.id)
        if not rec:
            rec = {
                "id": volunteer.id,
                "name": f"{volunteer.first_name} {volunteer.last_name}",
                "email": volunteer.primary_email,
                "organization": _get_primary_org_name(volunteer),
                "skills": ", ".join(
                    sorted(
                        {
                            s.name
                            for s in getattr(volunteer, "skills", [])
                            if getattr(s, "name", None)
                        }
                    )
                ),
                "events": [],
                "event_count": 0,
                "last_event_date": None,
            }
            aggregated[volunteer.id] = rec

        rec["events"].append(
            {
                "id": event.id,
                "title": event.title,
                "date": event.start_date,
                "type": event.type.value if event.type else None,
            }
        )
        rec["event_count"] += 1
        if not rec["last_event_date"] or (
            event.start_date and event.start_date > rec["last_event_date"]
        ):
            rec["last_event_date"] = event.start_date

    # Convert to sorted list
    result = list(aggregated.values())
    result.sort(key=lambda r: (r["name"] or "").lower())
    return result


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
            titles = [e["title"] for e in v["events"]]
            unique_titles = []
            seen = set()
            for t in titles:
                if t and t not in seen:
                    seen.add(t)
                    unique_titles.append(t)
            v["events_display"] = "; ".join(unique_titles[:5]) + (
                " …" if len(unique_titles) > 5 else ""
            )
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
            "reports/volunteers_by_event.html",
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
            titles = [e["title"] for e in v["events"] if e.get("title")]
            rows.append(
                {
                    "Name": v["name"],
                    "Email": v["email"],
                    "Organization": v.get("organization") or "",
                    "Skills": v.get("skills") or "",
                    "Events (Count)": v["event_count"],
                    "Last Event": last_date,
                    "Event Titles": "; ".join(sorted(set(titles))),
                }
            )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df = pd.DataFrame(rows)
            df.to_excel(writer, index=False, sheet_name="Volunteers")
            ws = writer.sheets["Volunteers"]
            ws.set_column("A:A", 28)
            ws.set_column("B:B", 36)
            ws.set_column("C:C", 26)  # Organization
            ws.set_column("D:D", 40)  # Skills
            ws.set_column("E:E", 14)  # Events (Count)
            ws.set_column("F:F", 14)  # Last Event
            ws.set_column("G:G", 60)  # Event Titles

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
