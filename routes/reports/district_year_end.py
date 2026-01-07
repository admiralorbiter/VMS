import io
from datetime import datetime

import pandas as pd
import pytz
import xlsxwriter
from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from models import db
from models.district_model import District
from models.event import (
    Event,
    EventAttendance,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.google_sheet import GoogleSheet
from models.organization import Organization, VolunteerOrganization
from models.reports import DistrictYearEndReport
from models.school_model import School
from models.student import Student
from models.volunteer import EventParticipation
from routes.decorators import district_scoped_required
from routes.reports.common import (
    DISTRICT_MAPPING,
    cache_district_stats,
    generate_district_stats,
    get_current_school_year,
    get_district_student_count_for_event,
    get_school_year_date_range,
)

# Create blueprint
district_year_end_bp = Blueprint("district_year_end", __name__)


def load_routes(bp):
    @bp.route("/reports/district/year-end")
    @login_required
    def district_year_end():
        # Get school year from query params or default to current
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")  # 'all' or 'prepkc'

        # Get cached reports for the school year and host_filter
        cached_reports = DistrictYearEndReport.query.filter_by(
            school_year=school_year, host_filter=host_filter
        ).all()

        district_stats = {
            report.district.name: report.report_data for report in cached_reports
        }

        if not district_stats:
            district_stats = generate_district_stats(
                school_year, host_filter=host_filter
            )
            cache_district_stats_with_events(
                school_year, district_stats, host_filter=host_filter
            )

        # Filter district stats based on user scope
        if current_user.scope_type == "district" and current_user.allowed_districts:
            import json

            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )
                # Filter to only show allowed districts
                district_stats = {
                    district_name: stats
                    for district_name, stats in district_stats.items()
                    if district_name in allowed_districts
                }
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, show no districts
                district_stats = {}

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        # Convert UTC time to Central time for display
        last_updated = None
        if cached_reports:
            utc_time = min(report.last_updated for report in cached_reports)
            central = pytz.timezone("America/Chicago")
            last_updated = utc_time.replace(tzinfo=pytz.UTC).astimezone(central)

        # Get Google Sheets for this academic year (district reports only)
        academic_year = convert_school_year_format(school_year)
        google_sheets = GoogleSheet.query.filter_by(
            academic_year=academic_year, purpose="district_reports"
        ).all()

        # Get schools for each district, grouped by level
        districts_with_schools = {}
        for district_name, stats in district_stats.items():
            district = District.query.filter_by(name=district_name).first()
            if district:
                schools = School.query.filter_by(district_id=district.id).order_by(School.name).all()
                # Group schools by level
                schools_by_level = {
                    "High": [],
                    "Middle": [],
                    "Elementary": [],
                    "Other": []
                }
                for school in schools:
                    if school.level in ["High", "Middle", "Elementary"]:
                        schools_by_level[school.level].append({"name": school.name, "level": school.level})
                    else:
                        schools_by_level["Other"].append({"name": school.name, "level": school.level})
                
                districts_with_schools[district_name] = {
                    "stats": stats,
                    "schools_by_level": schools_by_level
                }
            else:
                districts_with_schools[district_name] = {
                    "stats": stats,
                    "schools_by_level": {"High": [], "Middle": [], "Elementary": [], "Other": []}
                }

        return render_template(
            "reports/districts/district_year_end.html",
            districts=districts_with_schools,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            last_updated=last_updated,
            host_filter=host_filter,
            google_sheets=google_sheets,
            academic_year=academic_year,
        )

    @bp.route("/reports/district/year-end/refresh", methods=["POST"])
    @login_required
    def refresh_district_year_end():
        """Refresh the cached district year-end report data"""
        import time
        start_time = time.time()
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")
        try:
            # Delete existing cached reports for this school year and host_filter
            deleted_count = DistrictYearEndReport.query.filter_by(
                school_year=school_year, host_filter=host_filter
            ).delete()
            db.session.commit()
            print(f"Deleted {deleted_count} cached reports")

            # Generate new stats (this already does a lot of work)
            print(f"Starting district stats generation for {school_year}...")
            gen_start = time.time()
            district_stats = generate_district_stats(
                school_year, host_filter=host_filter
            )
            gen_time = time.time() - gen_start
            print(f"Generated stats for {len(district_stats)} districts in {gen_time:.2f}s")

            # Cache the stats and events data (this does additional processing)
            print(f"Starting cache with events for {len(district_stats)} districts...")
            cache_start = time.time()
            cache_district_stats_with_events(
                school_year, district_stats, host_filter=host_filter
            )
            cache_time = time.time() - cache_start
            print(f"Cached stats with events in {cache_time:.2f}s")

            total_time = time.time() - start_time
            print(f"Total refresh time: {total_time:.2f}s")

            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully refreshed data for {school_year[:2]}-{school_year[2:]} school year",
                    "stats_generation_time": f"{gen_time:.2f}s",
                    "cache_time": f"{cache_time:.2f}s",
                    "total_time": f"{total_time:.2f}s",
                }
            )
        except Exception as e:
            db.session.rollback()
            print(f"Error refreshing district year-end report: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/reports/district/year-end/detail/<district_name>")
    @login_required
    @district_scoped_required
    def district_year_end_detail(district_name):
        """Show detailed year-end report for a specific district"""
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")

        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()

        # Get the district's mapping info
        district_mapping = next(
            (
                mapping
                for salesforce_id, mapping in DISTRICT_MAPPING.items()
                if mapping["name"] == district_name
            ),
            None,
        )

        # Try to get cached data first (use host_filter)
        cached_report = DistrictYearEndReport.query.filter_by(
            district_id=district.id, school_year=school_year, host_filter=host_filter
        ).first()

        events_by_month = {}
        total_events = 0
        unique_volunteer_count = 0
        unique_student_count = 0  # Initialize unique student count
        stats = {}

        if cached_report:
            stats = cached_report.report_data or {}  # Use cached stats
            # Check if we have cached events data
            if cached_report.events_data:
                events_by_month = cached_report.events_data.get("events_by_month", {})
                total_events = cached_report.events_data.get("total_events", 0)
                unique_volunteer_count = cached_report.events_data.get(
                    "unique_volunteer_count", 0
                )
                unique_student_count = cached_report.events_data.get(
                    "unique_student_count", 0
                )  # Get from cache

                # Calculate unique_organization_count from cached events_by_month
                volunteer_ids = set()
                for month_data in events_by_month.values():
                    for event in month_data.get("events", []):
                        event_id = event["id"]
                        participations = EventParticipation.query.filter_by(
                            event_id=event_id
                        ).all()
                        for p in participations:
                            if p.status in [
                                "Attended",
                                "Completed",
                                "Successfully Completed",
                            ]:
                                volunteer_ids.add(p.volunteer_id)
                org_ids = (
                    db.session.query(VolunteerOrganization.organization_id)
                    .filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids))
                    .distinct()
                    .all()
                )
                unique_organization_count = len(org_ids)

                # Use cached data if we have both stats and events data
                if stats and "enhanced" in stats:
                    # Generate schools_by_level data from cached events
                    cached_events = []
                    for month_data in events_by_month.values():
                        for event_data in month_data.get("events", []):
                            # Create a minimal event object for the function
                            event_obj = type(
                                "Event",
                                (),
                                {
                                    "id": event_data["id"],
                                    "title": event_data["title"],
                                    "start_date": datetime.strptime(
                                        event_data["date"], "%m/%d/%Y"
                                    ),
                                    "type": (
                                        type(
                                            "EventType",
                                            (),
                                            {"value": event_data["type"]},
                                        )()
                                        if event_data["type"]
                                        else None
                                    ),
                                    "location": event_data["location"],
                                    "students": event_data["students"],
                                    "volunteers": event_data["volunteers"],
                                    "volunteer_hours": event_data.get(
                                        "volunteer_hours", 0
                                    ),
                                },
                            )()
                            cached_events.append(event_obj)

                    schools_by_level = generate_schools_by_level_data(
                        district, cached_events
                    )

                    return render_template(
                        "reports/districts/district_year_end_detail.html",
                        district=district,
                        school_year=school_year,
                        stats=stats,
                        events_by_month=events_by_month,
                        schools_by_level=schools_by_level,
                        total_events=total_events,
                        unique_volunteer_count=unique_volunteer_count,
                        unique_student_count=unique_student_count,  # Pass to template
                        unique_organization_count=unique_organization_count,
                        host_filter=host_filter,
                    )

        # If we reach here, either no cache or missing parts (stats or events_data)
        # We'll calculate stats after the events query

        # If we get here, we need to generate the events data (or it was missing from cache)
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ["connector_session"]

        # Build query conditions (Duplicate logic - consider refactoring into a helper)
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

        if district_mapping and "aliases" in district_mapping:
            for alias in district_mapping["aliases"]:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Fetch events (excluding connector_session for main display)
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
        if host_filter == "prepkc":
            events_query = events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        events = events_query.all()

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

        # Calculate enhanced stats from filtered events (always recalculate when filter is applied)
        # Also calculate if cached stats don't include enhanced data
        if host_filter != "all" or not stats or "enhanced" not in stats:
            enhanced_stats = calculate_enhanced_district_stats(
                all_events_for_stats, district.id
            )

            # Keep backward compatibility with existing template variables
            stats = {
                "total_events": enhanced_stats["events"]["total"],
                "total_in_person_students": enhanced_stats["students"]["in_person"],
                "total_virtual_students": enhanced_stats["students"]["virtual"],
                "total_volunteers": enhanced_stats["volunteers"]["total"],
                "total_volunteer_hours": enhanced_stats["volunteers"]["hours_total"],
                "event_types": enhanced_stats["event_types"],
                # Add enhanced breakdown data
                "enhanced": enhanced_stats,
            }

        event_ids = [event.id for event in events]
        total_events = len(events)

        # Fetch student participations
        student_participations = EventStudentParticipation.query.filter(
            EventStudentParticipation.event_id.in_(event_ids)
        ).all()

        # Set to track unique volunteer and student IDs
        unique_volunteers = set()
        unique_students = set()  # Track unique student IDs

        # Organize events by month (Duplicate logic - consider refactoring)
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
                    "unique_students": set(),  # Add monthly set
                }

            # Get attendance and volunteer data
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

            # Update event data and totals in events_by_month
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
                    "session_host": event.session_host or "",
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

        # Calculate overall unique counts from enhanced stats if available
        if "enhanced" in stats:
            unique_volunteer_count = stats["enhanced"]["volunteers"]["unique_total"]
            unique_student_count = stats["enhanced"]["students"]["unique_total"]
            unique_organization_count = stats["enhanced"]["organizations"][
                "unique_total"
            ]
        else:
            # Fallback to original calculation
            unique_volunteer_count = len(unique_volunteers)
            unique_student_count = len(unique_students)

        # Process the events data for storage/display
        for month, data in events_by_month.items():
            data["unique_volunteer_count"] = len(data["unique_volunteers"])
            data["unique_volunteers"] = list(
                data["unique_volunteers"]
            )  # Convert set to list for JSON storage
            data["volunteer_engagements"] = data["volunteer_engagement_count"]
            data["unique_student_count"] = len(
                data["unique_students"]
            )  # Calculate monthly unique students
            data["unique_students"] = list(
                data["unique_students"]
            )  # Convert set to list for JSON

        # Cache the newly generated events data
        if cached_report:
            # Update existing cache
            cached_report.events_data = {
                "events_by_month": events_by_month,
                "total_events": total_events,
                "unique_volunteer_count": unique_volunteer_count,
                "unique_student_count": unique_student_count,
            }
            cached_report.report_data = stats
            db.session.commit()
        else:
            # Create new cache entry
            new_cache = DistrictYearEndReport()
            new_cache.district_id = district.id
            new_cache.school_year = school_year
            new_cache.host_filter = host_filter
            new_cache.report_data = stats
            new_cache.events_data = {
                "events_by_month": events_by_month,
                "total_events": total_events,
                "unique_volunteer_count": unique_volunteer_count,
                "unique_student_count": unique_student_count,
            }
            db.session.add(new_cache)
            db.session.commit()

        # Calculate unique organization count (only if not already calculated in enhanced stats)
        if "enhanced" not in stats:
            volunteer_ids = set()
            for event in events:
                for p in event.volunteer_participations:
                    if p.status in ["Attended", "Completed", "Successfully Completed"]:
                        volunteer_ids.add(p.volunteer_id)

            # Get all unique organization IDs for these volunteers
            org_ids = (
                db.session.query(VolunteerOrganization.organization_id)
                .filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids))
                .distinct()
                .all()
            )
            unique_organization_count = len(org_ids)

        # Generate schools_by_level data
        schools_by_level = generate_schools_by_level_data(district, events)

        return render_template(
            "reports/districts/district_year_end_detail.html",
            district=district,
            school_year=school_year,
            stats=stats,
            events_by_month=events_by_month,
            schools_by_level=schools_by_level,
            total_events=total_events,
            unique_volunteer_count=unique_volunteer_count,
            unique_student_count=unique_student_count,  # Pass to template
            unique_organization_count=unique_organization_count,
            host_filter=host_filter,
        )

    @bp.route("/reports/district/year-end/<district_name>/excel")
    @login_required
    @district_scoped_required
    def district_year_end_excel(district_name):
        """Generate Excel file for district year-end report"""
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")

        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()

        # Get cached report data
        cached_report = DistrictYearEndReport.query.filter_by(
            district_id=district.id, school_year=school_year, host_filter=host_filter
        ).first()

        if not cached_report:
            # Generate new stats if not cached
            district_stats = generate_district_stats(
                school_year, host_filter=host_filter
            )
            stats = district_stats.get(district_name, {})
            events_data = None
        else:
            stats = cached_report.report_data or {}
            events_data = cached_report.events_data

        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        workbook = writer.book

        # Add some formatting
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#467599", "font_color": "white", "border": 1}
        )

        # Summary Sheet
        summary_data = {
            "Metric": [
                "Total Events",
                "Total Students Reached",
                "Unique Students",
                "Total Volunteers",
                "Unique Volunteers",
                "Total Volunteer Hours",
                "Schools Reached",
                "Career Clusters",
            ],
            "Value": [
                stats.get("total_events", 0),
                stats.get("total_students", 0),
                stats.get("unique_student_count", 0),
                stats.get("total_volunteers", 0),
                stats.get("unique_volunteer_count", 0),
                stats.get("total_volunteer_hours", 0),
                stats.get("schools_reached", 0),
                stats.get("career_clusters", 0),
            ],
        }

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Format summary sheet
        worksheet = writer.sheets["Summary"]
        worksheet.set_column("A:A", 25)
        worksheet.set_column("B:B", 15)
        worksheet.conditional_format(
            "A1:B9", {"type": "no_blanks", "format": header_format}
        )

        # Event Types Sheet
        if stats.get("event_types"):
            event_types_data = {
                "Event Type": list(stats["event_types"].keys()),
                "Count": list(stats["event_types"].values()),
            }
            event_types_df = pd.DataFrame(event_types_data)
            event_types_df.to_excel(writer, sheet_name="Event Types", index=False)

            # Format event types sheet
            worksheet = writer.sheets["Event Types"]
            worksheet.set_column("A:A", 30)
            worksheet.set_column("B:B", 15)
            worksheet.conditional_format(
                "A1:B1", {"type": "no_blanks", "format": header_format}
            )

        # Monthly Breakdown Sheet
        if stats.get("monthly_breakdown"):
            monthly_data = []
            for month, data in stats["monthly_breakdown"].items():
                monthly_data.append(
                    {
                        "Month": month,
                        "Events": data.get("events", 0),
                        "Students": data.get("students", 0),
                        "Unique Students": data.get("unique_student_count", 0),
                        "Volunteers": data.get("volunteers", 0),
                        "Unique Volunteers": data.get("unique_volunteer_count", 0),
                        "Volunteer Hours": data.get("volunteer_hours", 0),
                    }
                )

            monthly_df = pd.DataFrame(monthly_data)
            monthly_df.to_excel(writer, sheet_name="Monthly Breakdown", index=False)

            # Format monthly breakdown sheet
            worksheet = writer.sheets["Monthly Breakdown"]
            worksheet.set_column("A:A", 20)
            worksheet.set_column("B:G", 15)
            worksheet.conditional_format(
                "A1:G1", {"type": "no_blanks", "format": header_format}
            )

        # Events Detail Sheet
        if events_data and events_data.get("events_by_month"):
            events_detail = []
            for month, data in events_data["events_by_month"].items():
                for event in data["events"]:
                    events_detail.append(
                        {
                            "Month": month,
                            "Date": event["date"],
                            "Time": event["time"],
                            "Event Title": event["title"],
                            "Type": event["type"],
                            "Location": event["location"],
                            "Students": event["student_count"],
                            "Volunteers": event["volunteer_count"],
                            "Volunteer Hours": event["volunteer_hours"],
                        }
                    )

            events_df = pd.DataFrame(events_detail)
            events_df.to_excel(writer, sheet_name="Events Detail", index=False)

            # Format events detail sheet
            worksheet = writer.sheets["Events Detail"]
            worksheet.set_column("A:A", 20)  # Month
            worksheet.set_column("B:B", 12)  # Date
            worksheet.set_column("C:C", 12)  # Time
            worksheet.set_column("D:D", 40)  # Event Title
            worksheet.set_column("E:E", 20)  # Type
            worksheet.set_column("F:F", 30)  # Location
            worksheet.set_column("G:I", 15)  # Numbers
            worksheet.conditional_format(
                "A1:I1", {"type": "no_blanks", "format": header_format}
            )

        writer.close()
        output.seek(0)

        # Create filename
        filename = (
            f"{district_name.replace(' ', '_')}_{school_year}_Year_End_Report.xlsx"
        )

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name=filename,
            as_attachment=True,
        )

    @bp.route("/reports/district/year-end/detail/<district_name>/filtered-stats")
    @login_required
    def get_filtered_stats(district_name):
        """Get precise filtered stats for selected event types"""
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")
        event_types = request.args.getlist("event_types[]")

        if not event_types:
            return jsonify({"error": "No event types specified"}), 400

        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({"error": "District not found"}), 404

        # Get the district's mapping info
        district_mapping = next(
            (
                mapping
                for salesforce_id, mapping in DISTRICT_MAPPING.items()
                if mapping["name"] == district_name
            ),
            None,
        )

        # Get events of specified types for this district
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ["connector_session"]

        # Build query conditions (same logic as main detail view)
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

        if district_mapping and "aliases" in district_mapping:
            for alias in district_mapping["aliases"]:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        events_query = (
            Event.query.outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                Event.type.in_([EventType(t) for t in event_types]),
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

        # Calculate precise unique counts
        unique_volunteers = set()
        unique_students = set()
        total_events = len(events)
        total_students = 0
        total_in_person_students = 0
        total_virtual_students = 0
        total_volunteers = 0
        total_volunteer_hours = 0

        for event in events:
            # Get volunteer participations
            volunteer_participations = [
                p
                for p in event.volunteer_participations
                if p.status in ["Attended", "Completed", "Successfully Completed"]
            ]

            for p in volunteer_participations:
                unique_volunteers.add(p.volunteer_id)

            total_volunteers += len(volunteer_participations)
            total_volunteer_hours += sum(
                p.delivery_hours or 0 for p in volunteer_participations
            )

            # Get student count for this district
            student_count = get_district_student_count_for_event(event, district.id)
            total_students += student_count

            # Categorize students by event type
            if event.type == EventType.VIRTUAL_SESSION:
                total_virtual_students += student_count
            else:
                total_in_person_students += student_count

            # Get unique students for non-virtual events
            if event.type != EventType.VIRTUAL_SESSION:
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
                unique_students.update(
                    student_id[0] for student_id in district_student_ids
                )

        # Get unique organizations
        if unique_volunteers:
            org_ids = (
                db.session.query(VolunteerOrganization.organization_id)
                .filter(VolunteerOrganization.volunteer_id.in_(unique_volunteers))
                .distinct()
                .all()
            )
            unique_organization_count = len(org_ids)
        else:
            unique_organization_count = 0

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

        # Calculate enhanced stats for filtered events
        enhanced_stats = calculate_enhanced_district_stats(
            all_events_for_stats, district.id
        )

        return jsonify(
            {
                "totalEvents": total_events,
                "totalStudents": total_students,
                "uniqueStudents": len(unique_students),
                "totalInPersonStudents": total_in_person_students,
                "totalVirtualStudents": total_virtual_students,
                "totalVolunteers": total_volunteers,
                "uniqueVolunteers": len(unique_volunteers),
                "totalVolunteerHours": total_volunteer_hours,
                "uniqueOrganizations": unique_organization_count,
                # Add enhanced breakdown data
                "enhanced": enhanced_stats,
            }
        )

    @bp.route("/reports/district/year-end/detail/<district_name>/filtered-participants")
    @login_required
    def get_filtered_participants(district_name):
        """Get filtered volunteers and students for selected event types"""
        school_year = request.args.get("school_year", get_current_school_year())
        event_types = request.args.getlist("event_types[]")

        if not event_types:
            return jsonify({"error": "No event types specified"}), 400

        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({"error": "District not found"}), 404

        # Get the district's mapping info
        district_mapping = next(
            (
                mapping
                for salesforce_id, mapping in DISTRICT_MAPPING.items()
                if mapping["name"] == district_name
            ),
            None,
        )

        # Get events of specified types for this district
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ["connector_session"]

        # Build query conditions (same logic as main detail view)
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

        if district_mapping and "aliases" in district_mapping:
            for alias in district_mapping["aliases"]:
                query_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                query_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        events = (
            Event.query.outerjoin(School, Event.school == School.id)
            .outerjoin(EventAttendance, Event.id == EventAttendance.event_id)
            .filter(
                Event.status == EventStatus.COMPLETED,
                Event.start_date.between(start_date, end_date),
                Event.type.in_([EventType(t) for t in event_types]),
                db.or_(*query_conditions),
            )
            .order_by(Event.start_date)
            .all()
        )

        # Get filtered volunteer IDs
        filtered_volunteer_ids = set()
        for event in events:
            volunteer_participations = [
                p
                for p in event.volunteer_participations
                if p.status in ["Attended", "Completed", "Successfully Completed"]
            ]
            for p in volunteer_participations:
                filtered_volunteer_ids.add(p.volunteer_id)

        # Get filtered student IDs (excluding virtual sessions)
        filtered_student_ids = set()
        non_virtual_events = [e for e in events if e.type != EventType.VIRTUAL_SESSION]

        for event in non_virtual_events:
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
            filtered_student_ids.update(
                student_id[0] for student_id in district_student_ids
            )

        return jsonify(
            {
                "volunteer_ids": list(filtered_volunteer_ids),
                "student_ids": list(filtered_student_ids),
                "event_ids": [event.id for event in events],
            }
        )

    @bp.route("/reports/district/year-end/google-sheets")
    @login_required
    def manage_google_sheets():
        """Manage Google Sheets for district year-end reports"""
        school_year = request.args.get("school_year", get_current_school_year())
        academic_year = convert_school_year_format(school_year)

        # Get all Google Sheets for this academic year (district reports only)
        sheets = GoogleSheet.query.filter_by(
            academic_year=academic_year, purpose="district_reports"
        ).all()

        return render_template(
            "reports/shared/google_sheets_management.html",
            sheets=sheets,
            academic_year=academic_year,
            school_year=school_year,
        )

    @bp.route("/reports/district/year-end/google-sheets/add", methods=["POST"])
    @login_required
    def add_google_sheet():
        """Add a new Google Sheet for the academic year"""
        school_year = request.form.get("school_year", get_current_school_year())
        academic_year = convert_school_year_format(school_year)
        sheet_id = request.form.get("sheet_id", "").strip()
        sheet_name = request.form.get("sheet_name", "").strip()

        if not sheet_id:
            return jsonify({"success": False, "error": "Sheet ID is required"}), 400

        try:
            # Always create a new sheet (multiple sheets per academic year allowed for district reports)
            new_sheet = GoogleSheet(
                academic_year=academic_year,
                sheet_id=sheet_id,
                created_by=current_user.id,
                purpose="district_reports",
                sheet_name=sheet_name if sheet_name else None,
            )
            db.session.add(new_sheet)
            db.session.commit()
            message = f"Added Google Sheet for {academic_year}"

            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "sheet": {
                        "academic_year": academic_year,
                        "sheet_id": sheet_id,
                        "created_by": current_user.username,
                    },
                }
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/reports/district/year-end/google-sheets/remove", methods=["POST"])
    @login_required
    def remove_google_sheet():
        """Remove a Google Sheet"""
        sheet_id = request.form.get("sheet_id")
        academic_year = request.form.get("academic_year")

        if not sheet_id or not academic_year:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sheet ID and academic year are required",
                    }
                ),
                400,
            )

        try:
            # Find the specific sheet by academic year, purpose, and sheet ID
            sheets = GoogleSheet.query.filter_by(
                academic_year=academic_year, purpose="district_reports"
            ).all()
            sheet_to_delete = None

            for sheet in sheets:
                if sheet.decrypted_sheet_id == sheet_id:
                    sheet_to_delete = sheet
                    break

            if sheet_to_delete:
                db.session.delete(sheet_to_delete)
                db.session.commit()
                return jsonify(
                    {
                        "success": True,
                        "message": f"Removed Google Sheet for {academic_year}",
                    }
                )
            else:
                return jsonify({"success": False, "error": "Sheet not found"}), 404
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/reports/district/year-end/google-sheets/api/<academic_year>")
    @login_required
    def get_google_sheets_api(academic_year):
        """API endpoint to get Google Sheets for a specific academic year"""
        sheets = GoogleSheet.query.filter_by(
            academic_year=academic_year, purpose="district_reports"
        ).all()
        return jsonify(
            {
                "sheets": [sheet.to_dict() for sheet in sheets],
                "academic_year": academic_year,
            }
        )

    @bp.route("/reports/district/year-end/breakdown")
    @login_required
    def district_year_end_breakdown():
        """Show detailed stats breakdown for all districts"""
        # Get school year from query params or default to current
        school_year = request.args.get("school_year", get_current_school_year())
        host_filter = request.args.get("host_filter", "all")

        # Get cached reports for the school year and host_filter
        cached_reports = DistrictYearEndReport.query.filter_by(
            school_year=school_year, host_filter=host_filter
        ).all()

        # Build breakdown data structure
        breakdown_data = {}
        overall_totals = {
            "in_person_students": {"total": 0, "unique": 0},
            "in_person_volunteers": {"total": 0, "unique": 0},
            "in_person_events_count": 0,
            "career_jumping_students": {"total": 0, "unique": 0},
            "career_speakers_students": {"total": 0, "unique": 0},
            "career_college_fair_hs_students": {"total": 0, "unique": 0},
            "healthstart_students": {"total": 0, "unique": 0},
            "bfi_students": {"total": 0, "unique": 0},
            "connector_sessions": {
                "teachers_engaged": {"total": 0, "unique": 0},
                "students_participated": {"total": 0, "unique": None},
                "session_count": 0,
            },
        }

        # Track unique IDs across all districts for overall totals
        overall_unique_in_person_students = set()
        overall_unique_in_person_volunteers = set()
        overall_unique_career_jumping_students = set()
        overall_unique_career_speakers_students = set()
        overall_unique_career_fair_hs_students = set()
        overall_unique_connector_teachers = set()

        for report in cached_reports:
            district = report.district
            stats = report.report_data or {}

            # Get program breakdown from cache, or compute on-demand
            if "program_breakdown" in stats:
                breakdown = stats["program_breakdown"]
            else:
                # Fallback: compute on-demand
                from routes.reports.common import calculate_program_breakdown

                breakdown = calculate_program_breakdown(
                    district.id, school_year, host_filter=host_filter
                )

            breakdown_data[district.name] = breakdown

            # Accumulate overall totals
            overall_totals["in_person_students"]["total"] += breakdown.get(
                "in_person_students", {}
            ).get("total", 0)
            overall_totals["in_person_volunteers"]["total"] += breakdown.get(
                "in_person_volunteers", {}
            ).get("total", 0)
            overall_totals["in_person_events_count"] += breakdown.get(
                "in_person_events_count", 0
            )
            overall_totals["career_jumping_students"]["total"] += breakdown.get(
                "career_jumping_students", {}
            ).get("total", 0)
            overall_totals["career_speakers_students"]["total"] += breakdown.get(
                "career_speakers_students", {}
            ).get("total", 0)
            overall_totals["career_college_fair_hs_students"]["total"] += breakdown.get(
                "career_college_fair_hs_students", {}
            ).get("total", 0)
            overall_totals["healthstart_students"]["total"] += breakdown.get(
                "healthstart_students", {}
            ).get("total", 0)
            overall_totals["bfi_students"]["total"] += breakdown.get(
                "bfi_students", {}
            ).get("total", 0)
            overall_totals["connector_sessions"]["teachers_engaged"]["total"] += (
                breakdown.get("connector_sessions", {})
                .get("teachers_engaged", {})
                .get("total", 0)
            )
            overall_totals["connector_sessions"]["students_participated"]["total"] += (
                breakdown.get("connector_sessions", {})
                .get("students_participated", {})
                .get("total", 0)
            )
            overall_totals["connector_sessions"]["session_count"] += breakdown.get(
                "connector_sessions", {}
            ).get("session_count", 0)

            # For unique counts, we need to track across districts
            # Note: This is an approximation - true unique would require cross-district deduplication
            # For now, we'll sum the unique counts (which may overcount if students/volunteers
            # participate across districts, but that's acceptable for this view)
            overall_totals["in_person_students"]["unique"] += breakdown.get(
                "in_person_students", {}
            ).get("unique", 0)
            overall_totals["in_person_volunteers"]["unique"] += breakdown.get(
                "in_person_volunteers", {}
            ).get("unique", 0)
            overall_totals["career_jumping_students"]["unique"] += breakdown.get(
                "career_jumping_students", {}
            ).get("unique", 0)
            overall_totals["career_speakers_students"]["unique"] += breakdown.get(
                "career_speakers_students", {}
            ).get("unique", 0)
            overall_totals["career_college_fair_hs_students"][
                "unique"
            ] += breakdown.get("career_college_fair_hs_students", {}).get("unique", 0)
            overall_totals["healthstart_students"]["unique"] += breakdown.get(
                "healthstart_students", {}
            ).get("unique", 0)
            overall_totals["bfi_students"]["unique"] += breakdown.get(
                "bfi_students", {}
            ).get("unique", 0)
            overall_totals["connector_sessions"]["teachers_engaged"]["unique"] += (
                breakdown.get("connector_sessions", {})
                .get("teachers_engaged", {})
                .get("unique", 0)
            )

        # Filter district breakdown based on user scope
        if current_user.scope_type == "district" and current_user.allowed_districts:
            import json

            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )
                # Filter to only show allowed districts
                breakdown_data = {
                    district_name: breakdown
                    for district_name, breakdown in breakdown_data.items()
                    if district_name in allowed_districts
                }
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, show no districts
                breakdown_data = {}

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            "reports/districts/district_year_end_breakdown.html",
            breakdown_data=breakdown_data,
            overall_totals=overall_totals,
            school_year=school_year,
            school_years=school_years,
            host_filter=host_filter,
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
                print(f"[{processed}/{total_districts}] Cached {district_name} in {district_time:.2f}s (avg: {avg_time:.2f}s, est. remaining: {remaining:.1f}s)")
                break
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    db.session.rollback()
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    db.session.rollback()
                    print(f"Error caching district {district_name}: {str(e)}")
                    raise


def calculate_enhanced_district_stats(events, district_id):
    """
    Calculate comprehensive district statistics with detailed breakdowns.

    Returns a dictionary with total stats and breakdowns by in-person vs virtual sessions.
    Each major category includes detailed metrics for volunteers, organizations, and virtual-specific data.
    """
    from models.event import EventTeacher
    from models.organization import Organization, VolunteerOrganization
    from models.school_model import School
    from models.student import Student
    from models.teacher import Teacher

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
            # Estimate students: confirmed teachers × 25
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
