"""
Teacher Routes Module
====================

This module handles all teacher-related functionality including:
- Teacher management and viewing
- Salesforce import for teachers
- Teacher exclusion from reports
- Teacher-specific operations

Key Features:
- Teacher listing and pagination
- Salesforce data import
- Teacher exclusion management
- Teacher detail views
- Contact information management
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from sqlalchemy.orm import aliased

from config import Config
from models import db
from models.contact import ContactTypeEnum, Email, GenderEnum, Phone
from models.event import EventTeacher
from models.school_model import School
from models.teacher import Teacher, TeacherStatus
from routes.utils import parse_date

# Create Blueprint for teacher routes
teachers_bp = Blueprint("teachers", __name__)


@teachers_bp.route("/teachers")
@login_required
def list_teachers():
    """
    Main teacher management page showing paginated list of teachers.

    Returns:
        Rendered template with paginated teacher data
    """
    # Get pagination parameters from request
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    # Query teachers with pagination - simplified for better performance
    teachers_query = Teacher.query.order_by(Teacher.last_name, Teacher.first_name)
    
    # Apply pagination directly
    teachers = teachers_query.paginate(page=page, per_page=per_page, error_out=False)

    # Create a pagination-like object
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < self.pages else None

        def iter_pages(
            self, left_edge=2, left_current=2, right_current=2, right_edge=2
        ):
            last = 0
            for num in range(1, self.pages + 1):
                if (
                    num <= left_edge
                    or (
                        num > self.page - left_current - 1
                        and num < self.page + right_current
                    )
                    or num > self.pages - right_edge
                ):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    # Get schools for the filter dropdown (with limit for performance)
    schools = School.query.order_by(School.name).limit(100).all()

    return render_template(
        "teachers/teachers.html",
        teachers=teachers,
        schools=schools,
        current_page=page,
        per_page=per_page,
        total_teachers=teachers.total,
        per_page_options=[10, 25, 50, 100],
    )


@teachers_bp.route("/teachers/import-from-salesforce", methods=["POST"])
@login_required
def import_teachers_from_salesforce():
    """
    Import teacher data from Salesforce.

    This function:
    1. Connects to Salesforce using configured credentials
    2. Queries for teachers with specific criteria
    3. Creates or updates teacher records in the local database
    4. Handles associated contact information (emails, phones)

    Returns:
        JSON response with import results and any errors
    """
    try:
        print("Starting teacher import from Salesforce...")
        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce using configured credentials
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # Query for teachers with specific fields
        teacher_query = """
        SELECT Id, AccountId, FirstName, LastName, Email,
               npsp__Primary_Affiliation__c, Department, Gender__c,
               Phone, Last_Email_Message__c, Last_Mailchimp_Email_Date__c
        FROM Contact
        WHERE Contact_Type__c = 'Teacher'
        """

        # Execute query and get results
        result = sf.query_all(teacher_query)
        teacher_rows = result.get("records", [])

        # Process each teacher record
        for row in teacher_rows:
            try:
                # Use the Teacher model's import method
                teacher, is_new, error = Teacher.import_from_salesforce(row, db.session)

                if error:
                    error_count += 1
                    errors.append(error)
                    continue

                success_count += 1

                # Save the teacher first to get the ID
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    errors.append(
                        f"Error saving teacher {teacher.first_name} {teacher.last_name}: {str(e)}"
                    )
                    continue

                # Handle contact info using the teacher's method
                try:
                    success, error = teacher.update_contact_info(row, db.session)
                    if not success:
                        errors.append(error)
                    else:
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    errors.append(
                        f"Error saving contact info for teacher {teacher.first_name} {teacher.last_name}: {str(e)}"
                    )

            except Exception as e:
                error_count += 1
                errors.append(
                    f"Error processing teacher {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}"
                )
                continue

        print(
            f"Teacher import complete: {success_count} successes, {error_count} errors"
        )
        if errors:
            print("Teacher import errors:")
            for error in errors:
                print(f"  - {error}")

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} teachers with {error_count} errors",
                "errors": errors,
            }
        )

    except SalesforceAuthenticationFailed:
        print("Salesforce authentication failed")
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        print(f"Teacher import failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@teachers_bp.route("/teachers/toggle-exclude-reports/<int:id>", methods=["POST"])
@login_required
def toggle_teacher_exclude_reports(id):
    """Toggle the exclude_from_reports field for a teacher - Admin only"""
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403

    try:
        teacher = db.session.get(Teacher, id)
        if not teacher:
            return jsonify({"success": False, "message": "Teacher not found"}), 404

        # Get the new value from the request
        data = request.get_json()
        exclude_from_reports = data.get("exclude_from_reports", False)

        # Update the field
        teacher.exclude_from_reports = exclude_from_reports
        db.session.commit()

        status = "excluded" if exclude_from_reports else "included"
        return jsonify(
            {"success": True, "message": f"Teacher {status} from reports successfully"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@teachers_bp.route("/teachers/view/<int:teacher_id>")
@login_required
def view_teacher(teacher_id):
    """
    View detailed information for a specific teacher.

    Args:
        id: Database ID of the teacher

    Returns:
        Rendered template with detailed teacher information
    """
    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        # Get related contact information
        primary_email = teacher.emails.filter_by(primary=True).first()
        primary_phone = teacher.phones.filter_by(primary=True).first()
        primary_address = teacher.addresses.filter_by(primary=True).first()

        # Debug: Print school relationship info
        print(f"Teacher: {teacher.first_name} {teacher.last_name}")
        print(f"School ID: {teacher.school_id}")
        print(f"Salesforce School ID: {teacher.salesforce_school_id}")
        print(f"School relationship: {teacher.school}")

        return render_template(
            "teachers/view.html",
            teacher=teacher,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address,
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@teachers_bp.route("/teachers/edit/<int:teacher_id>", methods=["GET", "POST"])
@login_required
def edit_teacher(teacher_id):
    """
    Edit teacher information - Admin only

    Args:
        teacher_id: Database ID of the teacher

    Returns:
        Rendered template with edit form or redirect on success
    """
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Admin access required"}), 403

    try:
        teacher = Teacher.query.get_or_404(teacher_id)

        if request.method == "POST":
            # Update teacher information
            teacher.first_name = request.form.get("first_name", teacher.first_name)
            teacher.last_name = request.form.get("last_name", teacher.last_name)
            teacher.salesforce_id = request.form.get(
                "salesforce_id", teacher.salesforce_id
            )
            teacher.status = TeacherStatus(
                request.form.get("status", teacher.status.value)
            )
            teacher.school_id = request.form.get("school_id", teacher.school_id)
            teacher.exclude_from_reports = "exclude_from_reports" in request.form

            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": f"Teacher {teacher.first_name} {teacher.last_name} updated successfully",
                }
            )

        # GET request - show edit form
        schools = School.query.order_by(School.name).all()

        return render_template("teachers/edit.html", teacher=teacher, schools=schools)

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


def load_routes(bp):
    """Load teacher routes into the main blueprint"""
    bp.register_blueprint(teachers_bp)
