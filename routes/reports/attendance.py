import math
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import and_, func

from models import db
from models.attendance import EventAttendanceDetail
from models.district_model import District
from models.event import (
    Event,
    EventAttendance,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.volunteer import EventParticipation

# Create blueprint
attendance_bp = Blueprint("reports_attendance", __name__)


def get_school_year_dates(school_year):
    """Convert school year (e.g., '24-25') to start and end dates"""
    start_year = int(school_year.split("-")[0])
    end_year = int(school_year.split("-")[1])

    # Convert to full years
    start_year = 2000 + start_year
    end_year = 2000 + end_year

    # School year starts June 1st
    start_date = datetime(start_year, 6, 1)
    end_date = datetime(end_year, 5, 31)

    return start_date, end_date


def load_routes(bp):
    @bp.route("/reports/attendance")
    @login_required
    def attendance_report():
        # Get all districts for the dropdown
        districts = District.query.order_by(District.name).all()

        # Get current school year
        current_year = datetime.now().year
        current_month = datetime.now().month

        # If we're past June, use current year as start, otherwise use previous year
        if current_month >= 6:
            school_year = f"{str(current_year)[-2:]}-{str(current_year + 1)[-2:]}"
        else:
            school_year = f"{str(current_year - 1)[-2:]}-{str(current_year)[-2:]}"

        return render_template(
            "reports/attendance_report.html",
            districts=districts,
            current_school_year=school_year,
        )

    @bp.route("/reports/attendance/data")
    @login_required
    def get_attendance_data():
        print("Starting attendance data generation...")  # Debug
        district_id = request.args.get("district_id")
        school_year = request.args.get("school_year", "24-25")
        print(f"Params: district_id={district_id}, school_year={school_year}")

        start_date, end_date = get_school_year_dates(school_year)
        print(f"Date range: {start_date} to {end_date}")

        query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
        )

        if district_id:
            district = District.query.get(district_id)
            print(f"Filtering for district: {district.name if district else 'N/A'}")
            if district:
                query = query.filter(Event.districts.contains(district))

        events = query.all()
        print(f"Found {len(events)} events.")

        # Prepare the response data
        event_data = []
        total_volunteers = 0
        total_students = 0
        total_events = len(events)
        unique_volunteer_set = set()
        unique_student_set = set()
        unique_volunteer_names = set()
        unique_student_names = set()
        total_students_per_volunteer = 0
        events_with_ratio = 0

        for event in events:
            # Get volunteer participation
            volunteer_participations = EventParticipation.query.filter(
                EventParticipation.event_id == event.id,
                EventParticipation.status.in_(
                    ["Attended", "Completed", "Successfully Completed"]
                ),
            ).all()
            volunteers = [
                vp.volunteer for vp in volunteer_participations if vp.volunteer
            ]
            volunteer_names = [f"{v.first_name} {v.last_name}" for v in volunteers]

            # Get student participation
            student_participations = EventStudentParticipation.query.filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status == "Attended",
            ).all()
            students = [sp.student for sp in student_participations if sp.student]
            student_names = [f"{s.first_name} {s.last_name}" for s in students]

            # Get attendance detail information
            attendance_detail = event.attendance_detail
            total_students_count = (
                attendance_detail.total_students if attendance_detail else None
            )
            num_classrooms = (
                attendance_detail.num_classrooms if attendance_detail else None
            )
            rotations = attendance_detail.rotations if attendance_detail else None
            students_per_volunteer = (
                attendance_detail.students_per_volunteer if attendance_detail else None
            )

            # Calculate students per volunteer if we have the required data
            calculated_students_per_volunteer = None
            if total_students_count and num_classrooms and rotations:
                # Ensure values are integers for comparison
                try:
                    total_students_count = int(total_students_count)
                    num_classrooms = int(num_classrooms)
                    rotations = int(rotations)
                    if num_classrooms > 0 and rotations > 0:
                        calculated_students_per_volunteer = math.floor(
                            (total_students_count / num_classrooms) * rotations
                        )
                        total_students_per_volunteer += (
                            calculated_students_per_volunteer
                        )
                        events_with_ratio += 1
                except (ValueError, TypeError):
                    # If conversion fails, skip calculation
                    pass

            # Add to unique sets
            for v in volunteers:
                unique_volunteer_set.add(v.id)
                unique_volunteer_names.add(f"{v.first_name} {v.last_name}")
            for s in students:
                unique_student_set.add(s.id)
                unique_student_names.add(f"{s.first_name} {s.last_name}")

            # Calculate attendance metrics
            volunteer_count = len(volunteer_names)
            student_count = len(student_names)

            # Get district names
            district_names = [d.name for d in event.districts]

            event_data.append(
                {
                    "date": (
                        event.start_date.strftime("%m/%d") if event.start_date else ""
                    ),
                    "name": event.title,
                    "district": ", ".join(district_names),
                    "volunteers": volunteer_count,
                    "students": student_count,
                    "volunteer_names": volunteer_names,
                    "student_names": student_names,
                    "total_students": total_students_count,
                    "num_classrooms": num_classrooms,
                    "rotations": rotations,
                    "students_per_volunteer": calculated_students_per_volunteer,
                }
            )

            total_volunteers += volunteer_count
            total_students += student_count

        # Calculate average students per volunteer across all events
        avg_students_per_volunteer = None
        if events_with_ratio > 0:
            avg_students_per_volunteer = round(
                total_students_per_volunteer / events_with_ratio, 1
            )

        return jsonify(
            {
                "events": event_data,
                "summary": {
                    "total_events": total_events,
                    "total_volunteers": total_volunteers,
                    "total_students": total_students,
                    "unique_volunteers": len(unique_volunteer_set),
                    "unique_students": len(unique_student_set),
                    "avg_students_per_volunteer": avg_students_per_volunteer,
                },
                "unique_volunteer_names": sorted(unique_volunteer_names),
                "unique_student_names": sorted(unique_student_names),
            }
        )
