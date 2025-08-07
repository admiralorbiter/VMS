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

from models import db
from models.student import Student
from utils.salesforce_importer import ImportConfig, ImportHelpers, SalesforceImporter

# Create Blueprint for student routes
students_bp = Blueprint("students", __name__)


def validate_student_record(record):
    """
    Validate a student record from Salesforce.

    Args:
        record: Dictionary containing Salesforce student data

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


def process_student_record(record, db_session):
    """
    Process a student record from Salesforce.

    Args:
        record: Dictionary containing Salesforce student data
        db_session: SQLAlchemy database session

    Returns:
        bool: True if successfully processed, False otherwise
    """
    try:
        # Use the Student model's import method
        student, is_new, error = Student.import_from_salesforce(record, db_session)

        if error:
            return False

        # Handle contact info using the student's method
        try:
            success, error = student.update_contact_info(record, db_session)
            if not success:
                return False
        except Exception:
            return False

        return True

    except Exception:
        return False


@students_bp.route("/students")
@login_required
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
        "students/students.html", students=students, current_page=page, per_page=per_page, total_students=total_students, per_page_options=[10, 25, 50, 100]
    )


@students_bp.route("/students/import-from-salesforce", methods=["POST"])
@login_required
def import_students_from_salesforce():
    """
    Import student data from Salesforce using the optimized framework.

    This function:
    1. Uses SalesforceImporter for batch processing
    2. Validates student records before processing
    3. Creates or updates student records in the local database
    4. Handles associated contact information (emails, phones)
    5. Provides detailed progress tracking and error reporting
    6. Uses optimized batch processing for 145,138+ students

    Returns:
        JSON response with import results and detailed statistics
    """
    try:
        print("Starting optimized student import from Salesforce...")

        # Configure the import with optimized settings for large datasets
        config = ImportConfig(
            batch_size=300,  # Optimal batch size for students (memory efficient)
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=50,  # Commit every 50 records (not every single one!)
        )

        # Create the importer
        importer = SalesforceImporter(config=config)

        # Define the query for students
        student_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email, Phone,
               Local_Student_ID__c, Birthdate, Gender__c, Racial_Ethnic_Background__c,
               npsp__Primary_Affiliation__c, Class__c, Legacy_Grade__c, Current_Grade__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        """

        # Execute the import
        print(f"Executing student import with query: {student_query}")
        result = importer.import_data(query=student_query, process_func=process_student_record, validation_func=validate_student_record)
        print(f"Import result: total_records={result.total_records}, processed_count={result.processed_count}, success_count={result.success_count}")

        # Prepare response
        response_data = {
            "success": result.success,
            "message": f"Successfully processed {result.processed_count} students",
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

        print(f"Student import complete: {result.success_count} successes, {result.error_count} errors")
        if result.errors:
            print("Student import errors:")
            for error in result.errors:
                print(f"  - {error}")

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print(f"Student import failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/view/<int:id>")
@login_required
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
            "students/view_details.html", student=student, primary_email=primary_email, primary_phone=primary_phone, primary_address=primary_address
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def load_routes(bp):
    """Load student routes into the main blueprint"""
    bp.register_blueprint(students_bp)
