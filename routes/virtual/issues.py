"""
District Issue Reporting Routes Module
======================================

This module provides issue reporting functionality for district-scoped users
on virtual district views. Allows district staff to report data issues
related to teachers, schools, and sessions.

Key Features:
- Floating action button (FAB) for easy issue reporting
- Teacher and session selection
- Integration with BugReport system
- District-scoped access control

Main Endpoints:
- POST /virtual/issues/report: Submit district issue report
- GET /virtual/issues/api/teacher-sessions: Get teacher's sessions for selection
"""

from datetime import datetime, timezone

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import db
from models.bug_report import BugReport, BugReportType
from models.event import Event, EventTeacher, EventType
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from routes.decorators import district_scoped_required
from routes.virtual.routes import virtual_bp


@virtual_bp.route("/issues/api/search-teachers", methods=["GET"])
@login_required
@district_scoped_required
def search_teachers_for_issues():
    """
    Search for teachers by name, filtered to only those in TeacherProgress for the virtual year.

    This endpoint restricts results to teachers that are part of the special imported list
    used in the virtual usage dashboard (TeacherProgress table).

    Query Parameters:
        q: Search query (minimum 2 characters)
        virtual_year: Virtual year to filter by (required)
        district_name: District name for validation (required)

    Returns:
        JSON array of teacher objects with id, name, school, and district
    """
    query = request.args.get("q", "").strip()
    virtual_year = request.args.get("virtual_year", "").strip()
    district_name = request.args.get("district_name", "").strip()

    if len(query) < 2:
        return jsonify([])

    if not virtual_year:
        return jsonify({"error": "virtual_year is required"}), 400

    # Validate district access
    if current_user.scope_type == "district":
        if not current_user.can_view_district(district_name):
            return jsonify({"error": "Access denied to this district"}), 403

    # Get all TeacherProgress entries for this virtual year
    teacher_progress_entries = TeacherProgress.query.filter_by(
        virtual_year=virtual_year
    ).all()

    if not teacher_progress_entries:
        return jsonify([])

    # Collect teacher IDs from TeacherProgress entries
    teacher_ids_from_progress = set()

    for tp_entry in teacher_progress_entries:
        if tp_entry.teacher_id:
            teacher_ids_from_progress.add(tp_entry.teacher_id)

    # If we have teacher_ids, search the Teacher table filtered by those IDs
    if teacher_ids_from_progress:
        search_term = f"%{query}%"
        full_name_expr = Teacher.first_name + " " + Teacher.last_name
        teachers = (
            Teacher.query.filter(
                Teacher.id.in_(teacher_ids_from_progress),
                or_(
                    func.lower(Teacher.first_name).like(func.lower(search_term)),
                    func.lower(Teacher.last_name).like(func.lower(search_term)),
                    func.lower(full_name_expr).like(func.lower(search_term)),
                ),
            )
            .options(joinedload(Teacher.school))
            .limit(20)
            .all()
        )

        results = []
        for teacher in teachers:
            school_name = teacher.school.name if teacher.school else None
            district_name_result = (
                teacher.school.district.name
                if teacher.school and teacher.school.district
                else district_name
            )
            results.append(
                {
                    "id": teacher.id,
                    "name": f"{teacher.first_name} {teacher.last_name}".strip(),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "school": school_name,
                    "school_id": teacher.school_id,
                    "district": district_name_result,
                }
            )

        return jsonify(results)

    # If no teacher_ids are set, search TeacherProgress entries by name
    # This handles cases where TeacherProgress entries haven't been matched to Teacher records yet
    query_lower = query.lower()
    matching_progress_entries = [
        tp for tp in teacher_progress_entries if query_lower in tp.name.lower()
    ][
        :20
    ]  # Limit to 20

    results = []
    for tp_entry in matching_progress_entries:
        # Try to find matching Teacher record by name
        teacher = None
        name_parts = tp_entry.name.split(" ", 1)

        if len(name_parts) >= 2:
            first_name, last_name = name_parts[0], name_parts[1]
            teacher = Teacher.query.filter(
                func.lower(Teacher.first_name) == func.lower(first_name),
                func.lower(Teacher.last_name) == func.lower(last_name),
            ).first()

        # Build result - prefer Teacher data if found, otherwise use TeacherProgress data
        if teacher:
            school_name = teacher.school.name if teacher.school else tp_entry.building
            results.append(
                {
                    "id": teacher.id,
                    "name": f"{teacher.first_name} {teacher.last_name}".strip(),
                    "first_name": teacher.first_name,
                    "last_name": teacher.last_name,
                    "school": school_name,
                    "school_id": teacher.school_id,
                    "district": (
                        teacher.school.district.name
                        if teacher.school and teacher.school.district
                        else district_name
                    ),
                }
            )
        else:
            # No Teacher record found, use TeacherProgress data
            results.append(
                {
                    "id": None,
                    "name": tp_entry.name,
                    "first_name": name_parts[0] if len(name_parts) >= 1 else "",
                    "last_name": name_parts[1] if len(name_parts) >= 2 else "",
                    "school": tp_entry.building,
                    "school_id": None,
                    "district": district_name,
                }
            )

    return jsonify(results)


@virtual_bp.route("/issues/api/teacher-sessions", methods=["GET"])
@login_required
@district_scoped_required
def get_teacher_sessions():
    """
    Get virtual sessions for a specific teacher within a date range.

    Used for populating session dropdown in issue reporting modal.
    Requires district-scoped access.

    Query Parameters:
        teacher_id: Teacher's database ID (required)
        district_name: District name for validation (required)
        date_from: Start date (YYYY-MM-DD format)
        date_to: End date (YYYY-MM-DD format)

    Returns:
        JSON array of session objects with id, title, date, and status
    """
    teacher_id = request.args.get("teacher_id", type=int)
    district_name = request.args.get("district_name", "")
    date_from_str = request.args.get("date_from", "")
    date_to_str = request.args.get("date_to", "")

    if not teacher_id:
        return jsonify({"error": "teacher_id is required"}), 400

    # Validate district access
    if current_user.scope_type == "district":
        if not current_user.can_view_district(district_name):
            return jsonify({"error": "Access denied to this district"}), 403

    # Get teacher
    teacher = Teacher.query.get_or_404(teacher_id)

    # Build query for teacher's virtual sessions
    query = (
        Event.query.join(EventTeacher)
        .filter(
            EventTeacher.teacher_id == teacher_id,
            Event.type == EventType.VIRTUAL_SESSION,
        )
        .order_by(Event.start_date.desc())
    )

    # Apply date filters if provided
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
            query = query.filter(Event.start_date >= date_from)
        except ValueError:
            pass

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
            # Include the full day
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(Event.start_date <= date_to)
        except ValueError:
            pass

    # Limit to recent sessions
    sessions = query.limit(50).all()

    results = []
    for event in sessions:
        results.append(
            {
                "id": event.id,
                "title": event.title or "Untitled Session",
                "date": (
                    event.start_date.strftime("%Y-%m-%d") if event.start_date else None
                ),
                "time": (
                    event.start_date.strftime("%I:%M %p") if event.start_date else None
                ),
                "status": event.status.value if event.status else "unknown",
            }
        )

    return jsonify(results)


@virtual_bp.route("/issues/report", methods=["POST"])
@login_required
def report_district_issue():
    """
    Submit a district issue report.

    Creates a BugReport entry for data issues reported by district staff.
    Requires district-scoped user access.

    Request Body (JSON):
        district_name: District name (required)
        teacher_id: Teacher ID (required)
        school_name: School name (optional, auto-filled from teacher)
        session_id: Event/session ID (optional)
        category: "missing" or "incorrect" (required)
        description: Optional free-text description
        page_url: Current page URL (required)
        page_title: Current page title (optional)

    Returns:
        JSON response with success status
    """
    # Check if user is district-scoped
    if current_user.scope_type != "district":
        return jsonify({"error": "This endpoint is for district users only"}), 403

    data = request.get_json() or request.form

    # Validate required fields
    district_name = data.get("district_name", "").strip()
    teacher_id_raw = data.get("teacher_id")
    category = data.get("category", "").strip()
    page_url = data.get("page_url", "").strip()

    if not district_name:
        return jsonify({"error": "district_name is required"}), 400

    # Convert teacher_id to int
    try:
        teacher_id = int(teacher_id_raw) if teacher_id_raw else None
    except (ValueError, TypeError):
        teacher_id = None

    if not teacher_id:
        return (
            jsonify({"error": "teacher_id is required and must be a valid number"}),
            400,
        )
    if category not in ["missing", "incorrect"]:
        return jsonify({"error": "category must be 'missing' or 'incorrect'"}), 400
    if not page_url:
        return jsonify({"error": "page_url is required"}), 400

    # Validate district access
    if not current_user.can_view_district(district_name):
        return jsonify({"error": "Access denied to this district"}), 403

    try:
        # Get teacher
        teacher = Teacher.query.get_or_404(teacher_id)

        # Get school name
        school_name = data.get("school_name", "").strip()
        if not school_name and teacher.school_id:
            from models.school_model import School

            school = School.query.get(teacher.school_id)
            if school:
                school_name = school.name

        # Get session info if provided
        session_id_raw = data.get("session_id")
        session_id = None
        if session_id_raw:
            try:
                session_id = int(session_id_raw)
            except (ValueError, TypeError):
                session_id = None

        session_info = ""
        if session_id:
            event = Event.query.get(session_id)
            if event:
                date_str = (
                    event.start_date.strftime("%Y-%m-%d")
                    if event.start_date
                    else "Unknown"
                )
                session_info = f"Session: {event.title or 'Untitled'} (ID: {event.id}, Date: {date_str})"

        # Build structured description
        description_parts = [
            f"Source: District",
            f"District: {district_name}",
            f"Teacher: {teacher.first_name} {teacher.last_name} (ID: {teacher_id})",
        ]

        if school_name:
            description_parts.append(f"School: {school_name}")

        if session_info:
            description_parts.append(session_info)

        description_parts.append(f"Category: {category}")

        notes = data.get("description", "").strip()
        if notes:
            description_parts.append(f"Notes: {notes}")

        description = "\n".join(description_parts)

        # Create bug report
        bug_report = BugReport(
            type=BugReportType.DATA_ERROR,
            description=description,
            page_url=page_url,
            page_title=data.get("page_title", "District Issue Report"),
            submitted_by_id=current_user.id,
        )

        db.session.add(bug_report)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Issue reported successfully. Thank you for your feedback!",
            }
        )

    except Exception as e:
        db.session.rollback()
        from flask import current_app

        current_app.logger.error(f"Error reporting district issue: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
