"""
Student Routes Module
====================

This module handles all student-related functionality including:
- Student management and viewing
- Salesforce import for students
- Student-specific operations

Key Features:
- Student listing and pagination
- Salesforce data import with chunked processing
- Student detail views
- Contact information management
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from simple_salesforce.api import Salesforce

from config import Config
from models import db
from models.student import Student
from routes.decorators import global_users_only

# Create Blueprint for student routes
students_bp = Blueprint("students", __name__)


@students_bp.route("/students")
@login_required
@global_users_only
def view_students():
    """
    Main student management page showing paginated list of students.

    Returns:
        Rendered template with paginated student data
    """
    # Get pagination parameters from request
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    # Query students with pagination
    students = Student.query.paginate(page=page, per_page=per_page, error_out=False)

    # Calculate total counts for pagination info
    total_students = Student.query.count()

    return render_template(
        "students/students.html",
        students=students,
        current_page=page,
        per_page=per_page,
        total_students=total_students,
        per_page_options=[10, 25, 50, 100],
    )


@students_bp.route("/students/view/<int:id>")
@login_required
@global_users_only
def view_student_details(id):
    """
    View detailed information for a specific student.

    Args:
        id: Database ID of the student

    Returns:
        Rendered template with detailed student information
    """
    try:
        student = Student.query.get_or_404(id)

        # Get related contact information
        primary_email = student.emails.filter_by(primary=True).first()
        primary_phone = student.phones.filter_by(primary=True).first()
        primary_address = student.addresses.filter_by(primary=True).first()

        return render_template(
            "students/view_details.html",
            student=student,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address,
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def load_routes(bp):
    """Load student routes into the main blueprint"""
    bp.register_blueprint(students_bp)
