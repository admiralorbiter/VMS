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
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.event import EventTeacher
from models.school_model import School
from models.teacher import Teacher, TeacherStatus
from utils.salesforce_importer import ImportConfig, ImportHelpers, SalesforceImporter

# Create Blueprint for teacher routes
teachers_bp = Blueprint("teachers", __name__)


def validate_teacher_record(record):
    """
    Validate a teacher record from Salesforce.

    Args:
        record: Dictionary containing Salesforce teacher data

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []
    required_fields = ["Id", "FirstName", "LastName"]

    for field in required_fields:
        if not record.get(field):
            errors.append(f"Missing required field: {field}")

    # Validate Salesforce ID format
    sf_id = record.get("Id", "")
    if sf_id and not ImportHelpers.is_valid_salesforce_id(sf_id):
        errors.append(f"Invalid Salesforce ID format: {sf_id}")

    # Validate name fields
    first_name = record.get("FirstName", "").strip()
    last_name = record.get("LastName", "").strip()

    if not first_name or not last_name:
        errors.append(f"Invalid name data: first_name='{first_name}', last_name='{last_name}'")

    return errors


def process_teacher_record(record, db_session):
    """
    Process a teacher record from Salesforce.

    Args:
        record: Dictionary containing Salesforce teacher data
        db_session: SQLAlchemy database session

    Returns:
        bool: True if successfully processed, False otherwise
    """
    try:
        # Use the Teacher model's import method
        teacher, is_new, error = Teacher.import_from_salesforce(record, db_session)

        if error:
            return False

        # Handle contact info using the teacher's method
        try:
            success, error = teacher.update_contact_info(record, db_session)
            if not success:
                return False
        except Exception:
            return False

        return True

    except Exception:
        return False


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

    # Query teachers with pagination - include teachers who participate in events
    teachers_query = db.session.query(Teacher).distinct()

    # Add teachers who participate in events (including virtual sessions)
    teachers_with_events = db.session.query(Teacher).join(EventTeacher).distinct()

    # Combine both queries and remove duplicates
    all_teachers = teachers_query.union(teachers_with_events).order_by(Teacher.last_name, Teacher.first_name)

    # Apply pagination manually since union doesn't work well with paginate
    total_teachers = all_teachers.count()
    offset = (page - 1) * per_page
    teachers_list = all_teachers.offset(offset).limit(per_page).all()

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

        def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or (num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    teachers = Pagination(teachers_list, page, per_page, total_teachers)

    # Calculate total counts for pagination info
    total_teachers_count = Teacher.query.count()

    # Get schools for the filter dropdown
    schools = School.query.order_by(School.name).all()

    return render_template(
        "teachers/teachers.html",
        teachers=teachers,
        schools=schools,
        current_page=page,
        per_page=per_page,
        total_teachers=total_teachers_count,
        per_page_options=[10, 25, 50, 100],
    )


@teachers_bp.route("/teachers/import-from-salesforce", methods=["POST"])
@login_required
def import_teachers_from_salesforce():
    """
    Import teacher data from Salesforce using the optimized framework.

    This function:
    1. Uses SalesforceImporter for batch processing
    2. Validates teacher records before processing
    3. Creates or updates teacher records in the local database
    4. Handles associated contact information (emails, phones)
    5. Provides detailed progress tracking and error reporting

    Returns:
        JSON response with import results and detailed statistics
    """
    try:
        print("Starting optimized teacher import from Salesforce...")

        # Configure the import
        config = ImportConfig(batch_size=350, max_retries=3, retry_delay_seconds=1, validate_data=True, log_progress=True)  # Optimal batch size for teachers

        # Create the importer
        importer = SalesforceImporter(config=config)

        # Define the query for teachers
        teacher_query = """
        SELECT Id, AccountId, FirstName, LastName, Email,
               npsp__Primary_Affiliation__c, Department, Gender__c,
               Phone, Last_Email_Message__c, Last_Mailchimp_Email_Date__c
        FROM Contact
        WHERE Contact_Type__c = 'Teacher'
        """

        # Execute the import
        result = importer.import_data(query=teacher_query, process_func=process_teacher_record, validation_func=validate_teacher_record)

        # Prepare response
        response_data = {
            "success": result.success,
            "message": f"Successfully processed {result.processed_count} teachers",
            "statistics": {
                "total_records": result.total_records,
                "processed_count": result.processed_count,
                "success_count": result.success_count,
                "error_count": result.error_count,
                "skipped_count": result.skipped_count,
                "duration_seconds": result.duration_seconds,
            },
            "errors": result.errors,
            "warnings": result.warnings,
        }

        print(f"Teacher import complete: {result.success_count} successes, {result.error_count} errors")
        if result.errors:
            print("Teacher import errors:")
            for error in result.errors:
                print(f"  - {error}")

        return jsonify(response_data)

    except SalesforceAuthenticationFailed:
        print("Salesforce authentication failed")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
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
        return jsonify({"success": True, "message": f"Teacher {status} from reports successfully"})

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

        return render_template("teachers/view.html", teacher=teacher, primary_email=primary_email, primary_phone=primary_phone, primary_address=primary_address)

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
            teacher.salesforce_id = request.form.get("salesforce_id", teacher.salesforce_id)
            teacher.status = TeacherStatus(request.form.get("status", teacher.status.value))
            teacher.school_id = request.form.get("school_id", teacher.school_id)
            teacher.exclude_from_reports = "exclude_from_reports" in request.form

            db.session.commit()

            return jsonify({"success": True, "message": f"Teacher {teacher.first_name} {teacher.last_name} updated successfully"})

        # GET request - show edit form
        schools = School.query.order_by(School.name).all()

        return render_template("teachers/edit.html", teacher=teacher, schools=schools)

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


def load_routes(bp):
    """Load teacher routes into the main blueprint"""
    bp.register_blueprint(teachers_bp)
