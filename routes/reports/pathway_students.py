"""
Pathway Student Attendance Report
=================================

Shows students who attended pathway-related events (BFI, Pathway Campus Visits,
etc.) with their student number, name, school, grade, graduating class,
DOB, gender, ethnicity, lunch status, and event details.

Routes:
    GET /reports/pathway-students       — Report page with filters
    GET /reports/pathway-students/data  — JSON API for AJAX table population
"""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from models.event import Event, EventStatus, EventStudentParticipation, EventType
from models.student import Student

# Create blueprint
pathway_students_bp = Blueprint("reports_pathway_students", __name__)

# Event types available for filtering in this report
PATHWAY_EVENT_TYPES = [
    {"value": EventType.BFI.value, "label": "BFI"},
    {"value": EventType.PATHWAY_CAMPUS_VISITS.value, "label": "Pathway Campus Visits"},
    {
        "value": EventType.PATHWAY_WORKPLACE_VISITS.value,
        "label": "Pathway Workplace Visits",
    },
    {"value": EventType.CAREER_FAIR.value, "label": "Career Fair"},
    {"value": EventType.CAMPUS_VISIT.value, "label": "Campus Visit"},
    {"value": EventType.WORKPLACE_VISIT.value, "label": "Workplace Visit"},
]


def _school_year_dates(school_year):
    """Convert a school year string like '25-26' to (start, end) datetimes."""
    start_yr = 2000 + int(school_year.split("-")[0])
    end_yr = 2000 + int(school_year.split("-")[1])
    return datetime(start_yr, 6, 1), datetime(end_yr, 5, 31)


def load_routes(bp):
    @bp.route("/reports/pathway-students")
    @login_required
    def pathway_students_report():
        now = datetime.now()
        if now.month >= 6:
            school_year = f"{str(now.year)[-2:]}-{str(now.year + 1)[-2:]}"
        else:
            school_year = f"{str(now.year - 1)[-2:]}-{str(now.year)[-2:]}"

        return render_template(
            "reports/pathway_students/pathway_students.html",
            event_types=PATHWAY_EVENT_TYPES,
            current_school_year=school_year,
        )

    @bp.route("/reports/pathway-students/data")
    @login_required
    def pathway_students_data():
        school_year = request.args.get("school_year", "25-26")
        event_types_param = request.args.get("event_types", "")

        # Parse requested event types (comma-separated enum values)
        if event_types_param:
            requested_types = []
            for val in event_types_param.split(","):
                val = val.strip()
                try:
                    requested_types.append(EventType(val))
                except ValueError:
                    continue
        else:
            # Default: all pathway event types
            requested_types = [et["value"] for et in PATHWAY_EVENT_TYPES]
            requested_types = [EventType(v) for v in requested_types]

        if not requested_types:
            return jsonify({"students": [], "summary": {}})

        start_date, end_date = _school_year_dates(school_year)

        # Query completed events of the selected types within the school year
        events = (
            Event.query.filter(
                Event.type.in_(requested_types),
                Event.status == EventStatus.COMPLETED,
                Event.start_date >= start_date,
                Event.start_date <= end_date,
            )
            .order_by(Event.start_date)
            .all()
        )

        # Build a student-centric view: student -> list of events attended
        student_map = {}  # student_id (db pk) -> dict
        type_counts = {}  # event type label -> count of events

        for event in events:
            # Track event type counts
            type_label = event.type.value if event.type else "unknown"
            type_counts[type_label] = type_counts.get(type_label, 0) + 1

            # Get students who attended
            participations = EventStudentParticipation.query.filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status == "Attended",
            ).all()

            for sp in participations:
                student = sp.student
                if not student:
                    continue

                if student.id not in student_map:
                    # Get school and district names
                    school_name = ""
                    district_name = ""
                    if student.school:
                        school_name = getattr(student.school, "name", "")
                        if student.school.district:
                            district_name = getattr(student.school.district, "name", "")

                    # Compute graduating class year from current grade
                    graduating_class = None
                    if student.current_grade is not None:
                        # Current school year end year
                        grad_year = end_date.year + (12 - student.current_grade)
                        graduating_class = grad_year

                    # Gender value
                    gender_val = ""
                    if student.gender:
                        gender_val = (
                            student.gender.value
                            if hasattr(student.gender, "value")
                            else str(student.gender)
                        )

                    student_map[student.id] = {
                        "id": student.id,
                        "student_number": student.student_id or "",
                        "first_name": student.first_name or "",
                        "last_name": student.last_name or "",
                        "district": district_name,
                        "school": school_name,
                        "grade": student.current_grade,
                        "graduating_class": graduating_class,
                        "dob": (
                            student.birthdate.strftime("%m/%d/%Y")
                            if student.birthdate
                            else ""
                        ),
                        "gender": gender_val,
                        "ethnicity": student.racial_ethnic or "",
                        "lunch_status": student.lunch_status or "",
                        "events": [],
                    }

                student_map[student.id]["events"].append(
                    {
                        "id": event.id,
                        "title": event.title,
                        "date": (
                            event.start_date.strftime("%m/%d/%Y")
                            if event.start_date
                            else ""
                        ),
                        "type": type_label,
                    }
                )

        # Convert to sorted list
        students_list = sorted(
            student_map.values(), key=lambda s: (s["last_name"], s["first_name"])
        )

        # Add event count to each student
        for s in students_list:
            s["event_count"] = len(s["events"])

        summary = {
            "total_unique_students": len(students_list),
            "total_events": len(events),
            "type_counts": type_counts,
        }

        return jsonify({"students": students_list, "summary": summary})
