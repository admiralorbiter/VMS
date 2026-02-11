import io
from datetime import datetime

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError

from models import db
from models.event import Event, EventStatus
from models.organization import Organization, VolunteerOrganization
from models.reports import FirstTimeVolunteerReportCache
from models.volunteer import EventParticipation, Volunteer
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
first_time_volunteer_bp = Blueprint("first_time_volunteer", __name__)


def load_routes(bp):
    @bp.route("/reports/first-time-volunteer")
    @login_required
    def first_time_volunteer():
        # Get filter parameters
        school_year = request.args.get("school_year", get_current_school_year())
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)  # Default 25 per page
        refresh = request.args.get("refresh", "0") == "1"

        # Try to load from cache unless refresh requested
        cache = FirstTimeVolunteerReportCache.query.filter_by(
            school_year=school_year
        ).first()
        if cache and not refresh:
            report = cache.report_data
            last_updated = cache.last_updated
        else:
            # Get date range for the school year
            start_date, end_date = get_school_year_date_range(school_year)
            # Query for first-time volunteers in the school year (same as before)
            first_time_volunteers = (
                db.session.query(
                    Volunteer,
                    db.func.count(EventParticipation.id).label("total_events"),
                    db.func.sum(EventParticipation.delivery_hours).label("total_hours"),
                    Organization.name.label("organization_name"),
                )
                .outerjoin(
                    EventParticipation, Volunteer.id == EventParticipation.volunteer_id
                )
                .outerjoin(
                    Event,
                    and_(
                        EventParticipation.event_id == Event.id,
                        Event.start_date >= start_date,
                        Event.start_date <= end_date,
                        Event.status == EventStatus.COMPLETED,
                    ),
                )
                .outerjoin(
                    VolunteerOrganization,
                    Volunteer.id == VolunteerOrganization.volunteer_id,
                )
                .outerjoin(
                    Organization,
                    VolunteerOrganization.organization_id == Organization.id,
                )
                .filter(
                    and_(
                        Volunteer.first_volunteer_date >= start_date,
                        Volunteer.first_volunteer_date <= end_date,
                    )
                )
                .filter(
                    or_(
                        EventParticipation.status == "Attended",
                        EventParticipation.status == "Completed",
                        EventParticipation.status == "Successfully Completed",
                        EventParticipation.status.is_(None),
                    )
                )
                .group_by(Volunteer.id, Organization.name)
                .order_by(Volunteer.first_volunteer_date.desc())
            )

            all_volunteers_query = first_time_volunteers.all()
            total_first_time_volunteers = len(all_volunteers_query)
            total_events_by_first_timers = sum(
                (events_count or 0) for _, events_count, _, _ in all_volunteers_query
            )
            total_hours_by_first_timers = sum(
                float(hours or 0) for _, _, hours, _ in all_volunteers_query
            )

            # Prepare all volunteer data for cache (not paginated)
            all_volunteer_data = []
            for v, events_count, hours, org in all_volunteers_query:
                # Get events for this volunteer in the school year
                volunteer_events = (
                    db.session.query(
                        Event,
                        EventParticipation.delivery_hours,
                        EventParticipation.status,
                    )
                    .join(EventParticipation, Event.id == EventParticipation.event_id)
                    .filter(
                        EventParticipation.volunteer_id == v.id,
                        Event.start_date >= start_date,
                        Event.start_date <= end_date,
                        Event.status == EventStatus.COMPLETED,
                        or_(
                            EventParticipation.status == "Attended",
                            EventParticipation.status == "Completed",
                            EventParticipation.status == "Successfully Completed",
                        ),
                    )
                    .order_by(Event.start_date)
                    .all()
                )
                events_list = []
                for event, event_hours, status in volunteer_events:
                    events_list.append(
                        {
                            "title": event.title,
                            "date": event.start_date.strftime("%b %d, %Y"),
                            "type": event.type.value if event.type else "Unknown",
                            "hours": round(event_hours or 0, 2),
                            "district": event.district_partner or "N/A",
                        }
                    )
                all_volunteer_data.append(
                    {
                        "id": v.id,
                        "name": f"{v.first_name} {v.last_name}",
                        "first_volunteer_date": (
                            v.first_volunteer_date.strftime("%B %d, %Y")
                            if v.first_volunteer_date
                            else "Unknown"
                        ),
                        "total_events": events_count or 0,
                        "total_hours": round(float(hours or 0), 2),
                        "organization": org or "Independent",
                        "title": v.title or "No title listed",
                        "events": events_list,
                        "salesforce_contact_url": v.salesforce_contact_url,
                        "salesforce_account_url": v.salesforce_account_url,
                    }
                )
            report = {
                "volunteers": all_volunteer_data,
                "total_first_time_volunteers": total_first_time_volunteers,
                "total_events_by_first_timers": total_events_by_first_timers,
                "total_hours_by_first_timers": round(total_hours_by_first_timers, 1),
            }
            # Save to cache
            if not cache:
                cache = FirstTimeVolunteerReportCache(
                    school_year=school_year,
                    report_data=report,
                    last_updated=datetime.now(),
                )
                db.session.add(cache)
            else:
                cache.report_data = report
                cache.last_updated = datetime.now()
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # Update instead of insert if unique constraint fails
                cache = FirstTimeVolunteerReportCache.query.filter_by(
                    school_year=school_year
                ).first()
                if cache:
                    cache.report_data = report
                    cache.last_updated = datetime.now()
                    db.session.commit()
                else:
                    raise
            last_updated = cache.last_updated

        # Pagination (from cached data)
        all_volunteers = report["volunteers"]
        total_volunteers = len(all_volunteers)
        total_pages = (total_volunteers + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        start_idx = (page - 1) * per_page
        end_idx = min(page * per_page, total_volunteers)
        volunteer_data = all_volunteers[start_idx:end_idx]

        return render_template(
            "reports/volunteers/first_time_volunteer.html",
            volunteers=volunteer_data,
            school_year=school_year,
            school_year_display=f"20{school_year[:2]}-{school_year[2:]}",
            total_first_time_volunteers=report["total_first_time_volunteers"],
            total_events_by_first_timers=report["total_events_by_first_timers"],
            total_hours_by_first_timers=report["total_hours_by_first_timers"],
            # Pagination info
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_volunteers=total_volunteers,
            has_prev=has_prev,
            has_next=has_next,
            last_updated=last_updated,
            now=datetime.now(),
        )

    @bp.route("/reports/first-time-volunteer/export")
    @login_required
    def export_first_time_volunteer():
        school_year = request.args.get("school_year", get_current_school_year())
        start_date, end_date = get_school_year_date_range(school_year)

        # Query for first-time volunteers in the school year (same as main report)
        first_time_volunteers = (
            db.session.query(
                Volunteer,
                db.func.count(EventParticipation.id).label("total_events"),
                db.func.sum(EventParticipation.delivery_hours).label("total_hours"),
                Organization.name.label("organization_name"),
            )
            .outerjoin(
                EventParticipation, Volunteer.id == EventParticipation.volunteer_id
            )
            .outerjoin(
                Event,
                and_(
                    EventParticipation.event_id == Event.id,
                    Event.start_date >= start_date,
                    Event.start_date <= end_date,
                    Event.status == EventStatus.COMPLETED,
                ),
            )
            .outerjoin(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .outerjoin(
                Organization, VolunteerOrganization.organization_id == Organization.id
            )
            .filter(
                and_(
                    Volunteer.first_volunteer_date >= start_date,
                    Volunteer.first_volunteer_date <= end_date,
                )
            )
            .filter(
                or_(
                    EventParticipation.status == "Attended",
                    EventParticipation.status == "Completed",
                    EventParticipation.status == "Successfully Completed",
                    EventParticipation.status.is_(None),
                )
            )
            .group_by(Volunteer.id, Organization.name)
            .order_by(Volunteer.first_volunteer_date.desc())
            .all()
        )

        # Prepare data for DataFrame
        data = []
        for v, events_count, hours, org in first_time_volunteers:

            # Get events for this volunteer in the school year
            volunteer_events = (
                db.session.query(Event, EventParticipation.delivery_hours)
                .join(EventParticipation, Event.id == EventParticipation.event_id)
                .filter(
                    EventParticipation.volunteer_id == v.id,
                    Event.start_date >= start_date,
                    Event.start_date <= end_date,
                    Event.status == EventStatus.COMPLETED,
                    or_(
                        EventParticipation.status == "Attended",
                        EventParticipation.status == "Completed",
                        EventParticipation.status == "Successfully Completed",
                    ),
                )
                .order_by(Event.start_date)
                .all()
            )

            # Format events for Excel
            events_str = "; ".join(
                [
                    f"{event.title} ({event.start_date.strftime('%m/%d/%Y')})"
                    for event, _ in volunteer_events
                ]
            )

            data.append(
                {
                    "Name": f"{v.first_name} {v.last_name}",
                    "First Volunteer Date": (
                        v.first_volunteer_date.strftime("%Y-%m-%d")
                        if v.first_volunteer_date
                        else ""
                    ),
                    "Events Count": events_count or 0,
                    "Total Hours": round(float(hours or 0), 2),
                    "Organization": org or "Independent",
                    "Title": v.title or "No title listed",
                    "Events": events_str,
                    "Salesforce Contact URL": v.salesforce_contact_url or "",
                }
            )

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="First Time Volunteers")
        output.seek(0)

        filename = f"first_time_volunteers_{school_year}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
