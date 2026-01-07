import io
from datetime import datetime

import pandas as pd
import xlsxwriter
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import extract

from models import db
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, Volunteer
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
volunteer_thankyou_bp = Blueprint("volunteer_thankyou", __name__)


def load_routes(bp):
    @bp.route("/reports/volunteer/thankyou")
    @login_required
    def volunteer_thankyou():
        # Get filter parameters - use school year format (e.g., '2425' for 2024-25)
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")  # 'all' or 'prepkc'

        # Sorting
        sort = request.args.get("sort", "total_hours")
        order = request.args.get("order", "desc")

        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)

        # Map sort keys to columns
        sort_columns = {
            "name": db.func.concat(Volunteer.first_name, " ", Volunteer.last_name),
            "total_hours": db.func.sum(EventParticipation.delivery_hours),
            "total_events": db.func.count(EventParticipation.id),
            "organization": Organization.name,
        }
        sort_col = sort_columns.get(
            sort, db.func.sum(EventParticipation.delivery_hours)
        )
        if order == "asc":
            order_by = sort_col.asc()
        else:
            order_by = sort_col.desc()

        # Query volunteer participation through EventParticipation
        volunteer_stats = (
            db.session.query(
                Volunteer,
                db.func.sum(EventParticipation.delivery_hours).label("total_hours"),
                db.func.count(EventParticipation.id).label("total_events"),
            )
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
            )
        )

        # Apply host filter if specified
        if host_filter == "prepkc":
            volunteer_stats = volunteer_stats.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )

        volunteer_stats = (
            volunteer_stats.group_by(Volunteer.id).order_by(order_by).all()
        )

        # Format the data for the template
        volunteer_data = []
        unique_organizations = set()
        total_hours_sum = 0
        total_events_sum = 0

        for v, hours, events in volunteer_stats:
            # Get organization information for this volunteer
            organizations = []
            for vol_org in v.volunteer_organizations:
                if vol_org.organization:
                    organizations.append(vol_org.organization.name)

            # Use the first organization or 'Independent' if none
            organization = organizations[0] if organizations else "Independent"

            # Track unique organizations
            unique_organizations.add(organization)

            # Sum up totals
            volunteer_hours = round(float(hours or 0), 2) if hours is not None else 0
            total_hours_sum += volunteer_hours
            total_events_sum += events

            volunteer_data.append(
                {
                    "id": v.id,
                    "name": f"{v.first_name} {v.last_name}",
                    "total_hours": volunteer_hours,
                    "total_events": events,
                    "organization": organization,
                    "race_ethnicity": (
                        v.race_ethnicity.value if v.race_ethnicity else "Unknown"
                    ),
                }
            )

        # Calculate summary statistics - ensure consistent counting with organization report
        unique_organizations_count = (
            db.session.query(db.func.count(db.distinct(Organization.id)))
            .join(
                VolunteerOrganization,
                Organization.id == VolunteerOrganization.organization_id,
            )
            .join(Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id)
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
            )
        )

        # Apply host filter if specified
        if host_filter == "prepkc":
            unique_organizations_count = unique_organizations_count.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )

        unique_organizations_count = unique_organizations_count.scalar() or 0

        summary_stats = {
            "unique_volunteers": len(volunteer_data),
            "total_hours": round(total_hours_sum, 2),
            "total_events": total_events_sum,
            "unique_organizations": unique_organizations_count,
        }

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            "reports/volunteers/volunteer_thankyou.html",
            volunteers=volunteer_data,
            summary_stats=summary_stats,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort=sort,
            order=order,
            host_filter=host_filter,
        )

    @bp.route("/reports/volunteer/thankyou/excel")
    @login_required
    def volunteer_thankyou_excel():
        """Generate Excel file for volunteer thank you report"""
        # Get filter parameters
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")  # 'all' or 'prepkc'
        sort = request.args.get("sort", "total_hours")
        order = request.args.get("order", "desc")

        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)

        # Map sort keys to columns
        sort_columns = {
            "name": db.func.concat(Volunteer.first_name, " ", Volunteer.last_name),
            "total_hours": db.func.sum(EventParticipation.delivery_hours),
            "total_events": db.func.count(EventParticipation.id),
            "organization": Organization.name,
        }
        sort_col = sort_columns.get(
            sort, db.func.sum(EventParticipation.delivery_hours)
        )
        if order == "asc":
            order_by = sort_col.asc()
        else:
            order_by = sort_col.desc()

        # Query volunteer participation through EventParticipation
        volunteer_stats = (
            db.session.query(
                Volunteer,
                db.func.sum(EventParticipation.delivery_hours).label("total_hours"),
                db.func.count(EventParticipation.id).label("total_events"),
            )
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
            )
        )

        # Apply host filter if specified
        if host_filter == "prepkc":
            volunteer_stats = volunteer_stats.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )

        volunteer_stats = (
            volunteer_stats.group_by(Volunteer.id).order_by(order_by).all()
        )

        # Format the data for Excel
        volunteer_data = []
        for v, hours, events in volunteer_stats:
            # Get organization information for this volunteer
            organizations = []
            for vol_org in v.volunteer_organizations:
                if vol_org.organization:
                    organizations.append(vol_org.organization.name)

            # Use the first organization or 'Independent' if none
            organization = organizations[0] if organizations else "Independent"

            volunteer_data.append(
                {
                    "Presenter": f"{v.first_name} {v.last_name}",
                    "Total Hours": (
                        round(float(hours or 0), 2) if hours is not None else 0
                    ),
                    "Total Events": events,
                    "Organization": organization,
                    "Race/Ethnicity": (
                        v.race_ethnicity.value if v.race_ethnicity else "Unknown"
                    ),
                }
            )

        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        workbook = writer.book

        # Add formatting
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#467599", "font_color": "white", "border": 1}
        )

        # Create DataFrame and write to Excel
        df = pd.DataFrame(volunteer_data)
        df.to_excel(writer, sheet_name="Volunteer Thank You Report", index=False)

        # Format worksheet
        worksheet = writer.sheets["Volunteer Thank You Report"]
        worksheet.set_column("A:A", 30)  # Presenter
        worksheet.set_column("B:B", 15)  # Total Hours
        worksheet.set_column("C:C", 15)  # Total Events
        worksheet.set_column("D:D", 30)  # Organization
        worksheet.set_column("E:E", 30)  # Race/Ethnicity

        # Apply header formatting
        worksheet.conditional_format(
            "A1:E1", {"type": "no_blanks", "format": header_format}
        )

        # Add summary statistics
        total_volunteers = len(volunteer_data)
        total_hours = sum(v["Total Hours"] for v in volunteer_data)
        total_events = sum(v["Total Events"] for v in volunteer_data)

        # Add summary section
        summary_row = total_volunteers + 3
        worksheet.write(summary_row, 0, "Summary Statistics", header_format)
        worksheet.write(summary_row + 1, 0, "Total Volunteers")
        worksheet.write(summary_row + 1, 1, total_volunteers)
        worksheet.write(summary_row + 2, 0, "Total Hours")
        worksheet.write(summary_row + 2, 1, total_hours)
        worksheet.write(summary_row + 3, 0, "Total Events")
        worksheet.write(summary_row + 3, 1, total_events)
        worksheet.write(summary_row + 4, 0, "School Year")
        worksheet.write(
            summary_row + 4, 1, f"{school_year[:2]}-{school_year[2:]} School Year"
        )
        worksheet.write(summary_row + 5, 0, "Filter")
        worksheet.write(
            summary_row + 5,
            1,
            "PREPKC Events Only" if host_filter == "prepkc" else "All Events",
        )

        writer.close()
        output.seek(0)

        # Create filename
        filter_suffix = "_PREPKC" if host_filter == "prepkc" else ""
        filename = f"Volunteer_Thank_You_Report_{school_year[:2]}-{school_year[2:]}{filter_suffix}.xlsx"

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name=filename,
            as_attachment=True,
        )

    @bp.route("/reports/volunteer/thankyou/detail/<int:volunteer_id>")
    @login_required
    def volunteer_thankyou_detail(volunteer_id):
        # Get filter parameters
        school_year = request.args.get("school_year", get_current_school_year())
        sort = request.args.get("sort", "date")
        order = request.args.get("order", "asc")

        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)

        # Get volunteer details
        volunteer = Volunteer.query.get_or_404(volunteer_id)

        # Query all events for this volunteer in the specified year
        events = (
            db.session.query(Event, EventParticipation.delivery_hours)
            .join(EventParticipation, Event.id == EventParticipation.event_id)
            .filter(
                EventParticipation.volunteer_id == volunteer_id,
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
            )
            .order_by(Event.start_date)
            .all()
        )

        # Format the events data
        events_data = []
        for event, hours in events:
            # Ensure date is a datetime object
            start_date = event.start_date
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date, "%B %d, %Y")
                except Exception:
                    start_date = None
            # School lookup
            school_obj = None
            if event.school:
                from models.school_model import School

                school_obj = School.query.get(event.school)
            events_data.append(
                {
                    "id": event.id,
                    "date": start_date,
                    "title": event.title,
                    "type": event.type.value if event.type else "Unknown",
                    "hours": round(hours or 0, 2),
                    "school": (
                        event.school_obj.name
                        if hasattr(event, "school_obj") and event.school_obj
                        else (school_obj.name if school_obj else event.school or "N/A")
                    ),
                    "school_obj": school_obj
                    or (event.school_obj if hasattr(event, "school_obj") else None),
                    "district": event.district_partner or "N/A",
                }
            )

        # Sort events_data in Python
        def get_sort_key(ev):
            if sort == "date":
                return ev["date"]
            elif sort == "title":
                return ev["title"].lower() if ev["title"] else ""
            elif sort == "type":
                return ev["type"].lower() if ev["type"] else ""
            elif sort == "hours":
                return ev["hours"]
            elif sort == "school":
                return ev["school"].lower() if ev["school"] else ""
            elif sort == "district":
                return ev["district"].lower() if ev["district"] else ""
            return ev["date"]

        events_data.sort(key=get_sort_key, reverse=(order == "desc"))

        # Calculate totals
        total_hours = sum(event["hours"] for event in events_data)
        total_events = len(events_data)

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            "reports/volunteers/volunteer_thankyou_detail.html",
            volunteer=volunteer,
            events=events_data,
            total_hours=total_hours,
            total_events=total_events,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort=sort,
            order=order,
        )
