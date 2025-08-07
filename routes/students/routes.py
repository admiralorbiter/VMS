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
from models.contact import Contact  # Added missing import for Contact
from models.school_model import School
from models.student import Student
from utils.salesforce_importer import SalesforceAuthenticationFailed  # Added missing import for SalesforceAuthenticationFailed
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


def process_student_record_without_school(record, db_session):
    """
    Process a student record from Salesforce WITHOUT school assignment.
    This allows us to import students first and fix school associations later.

    Args:
        record: Dictionary containing Salesforce student data
        db_session: SQLAlchemy database session

    Returns:
        bool: True if successfully processed, False otherwise
    """
    try:
        # Use the Student model's import method but skip school assignment
        student, is_new, error = Student.import_from_salesforce_without_school(record, db_session)

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


@students_bp.route("/students/fix-school-assignments", methods=["POST"])
@login_required
def fix_school_assignments():
    """
    Fix school assignments for students that don't have them.
    This can be run after the main student import is complete.
    """
    try:
        print("Starting school assignment fix...")

        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=500,  # Smaller batches for school assignment
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=100,
        )

        # Create the importer
        importer = SalesforceImporter(config=config)

        # Query only students that need school assignments
        student_query = """
        SELECT Id, npsp__Primary_Affiliation__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        AND npsp__Primary_Affiliation__c IS NOT NULL
        """

        def fix_school_assignment(record, db_session):
            """Fix school assignment for a single student."""
            try:
                sf_id = record.get("Id")
                school_sf_id = record.get("npsp__Primary_Affiliation__c")

                if not sf_id or not school_sf_id:
                    return False

                # Find the student
                student = Student.query.filter_by(salesforce_individual_id=sf_id).first()
                if not student:
                    return False

                # Check if school exists
                school = School.query.filter_by(id=school_sf_id).first()
                if not school:
                    print(f"School {school_sf_id} not found for student {sf_id}")
                    return False

                # Update school assignment
                student.school_id = school_sf_id
                db_session.commit()

                return True

            except Exception as e:
                print(f"Error fixing school assignment for {sf_id}: {str(e)}")
                return False

        result = importer.import_data(query=student_query, process_func=fix_school_assignment, validation_func=None)

        response_data = {
            "success": result.success,
            "message": f"Fixed school assignments for {result.success_count} students",
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

        print(f"School assignment fix complete: {result.success_count} successes, {result.error_count} errors")
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print(f"School assignment fix failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


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
    Phase 1: Import student data from Salesforce WITHOUT school assignments.

    This is the first phase of a two-phase import pipeline:
    1. Import all student data (names, grades, contact info) without school assignments
    2. Run school assignment phase separately

    This approach is more robust because:
    - No dependency on school import completion
    - Faster processing (no school lookups during import)
    - Better error isolation
    - Can be re-run safely
    - Handles missing schools gracefully

    Returns:
        JSON response with import results and detailed statistics
    """
    try:
        print("Starting Phase 1: Student import (without school assignments)...")

        # Configure the import with optimized settings for large datasets
        config = ImportConfig(
            batch_size=300,  # Optimal batch size for students
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=50,
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

        print(f"Executing student import with query: {student_query}")
        result = importer.import_data(query=student_query, process_func=process_student_record_without_school, validation_func=validate_student_record)
        print(f"Import result: total_records={result.total_records}, processed_count={result.processed_count}, success_count={result.success_count}")

        response_data = {
            "success": result.success,
            "message": f"Phase 1 complete: Successfully processed {result.success_count} students",
            "phase": "student_import",
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
            "next_phase": "school_assignment",
        }

        print(f"Student import complete: {result.success_count} successes, {result.error_count} errors")
        if result.errors:
            print("Student import errors:")
            for error in result.errors:
                print(f"  - {error}")

        return jsonify(response_data)

    except SalesforceAuthenticationFailed:
        print("Salesforce authentication failed")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        print(f"Student import failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/assign-schools", methods=["POST"])
@login_required
def assign_schools_to_students():
    """
    Phase 2: Assign schools to students that were imported in Phase 1.

    This phase:
    - Only processes students that don't have school assignments
    - Only assigns schools that exist in the database
    - Can be run multiple times safely
    - Provides detailed reporting on assignments vs missing schools

    This is part of the robust two-phase import pipeline.

    Returns:
        JSON response with assignment results and detailed statistics
    """
    try:
        print("Starting Phase 2: School assignment...")

        # Configure the import with optimized settings for school assignment
        config = ImportConfig(
            batch_size=500,  # Smaller batches for school assignment
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=100,
        )

        # Create the importer
        importer = SalesforceImporter(config=config)

        # Query only students that need school assignments
        student_query = """
        SELECT Id, npsp__Primary_Affiliation__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        AND npsp__Primary_Affiliation__c IS NOT NULL
        """

        def assign_school_to_student(record, db_session):
            """Assign school to a single student."""
            try:
                sf_id = record.get("Id")
                school_sf_id = record.get("npsp__Primary_Affiliation__c")

                if not sf_id or not school_sf_id:
                    return False

                # Find the student
                student = Student.query.filter_by(salesforce_individual_id=sf_id).first()
                if not student:
                    print(f"Student {sf_id} not found for school assignment")
                    return False

                # Check if school exists
                school = School.query.filter_by(id=school_sf_id).first()
                if not school:
                    print(f"School {school_sf_id} not found for student {sf_id}")
                    return False

                # Update school assignment
                student.school_id = school_sf_id
                db_session.commit()

                return True

            except Exception as e:
                print(f"Error assigning school for {sf_id}: {str(e)}")
                return False

        result = importer.import_data(query=student_query, process_func=assign_school_to_student, validation_func=None)

        # Get additional statistics about school assignments
        total_students = Student.query.count()
        students_with_schools = Student.query.filter(Student.school_id.isnot(None)).count()
        students_without_schools = Student.query.filter(Student.school_id.is_(None)).count()

        response_data = {
            "success": result.success,
            "message": f"Phase 2 complete: Assigned schools to {result.success_count} students",
            "phase": "school_assignment",
            "statistics": {
                "total_records": result.total_records,
                "processed_count": result.processed_count,
                "success_count": result.success_count,
                "error_count": result.error_count,
                "skipped_count": result.skipped_count,
                "duration_seconds": result.duration_seconds,
                "total_students": total_students,
                "students_with_schools": students_with_schools,
                "students_without_schools": students_without_schools,
            },
            "errors": result.errors,
            "warnings": result.warnings,
            "pipeline_complete": students_without_schools == 0,
        }

        print(f"School assignment complete: {result.success_count} successes, {result.error_count} errors")
        print(f"Total students: {total_students}, With schools: {students_with_schools}, Without schools: {students_without_schools}")

        if result.errors:
            print("School assignment errors:")
            for error in result.errors:
                print(f"  - {error}")

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print(f"School assignment failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/import-pipeline-status", methods=["GET"])
@login_required
def get_import_pipeline_status():
    """
    Get the current status of the two-phase import pipeline.

    This provides a comprehensive view of:
    - How many students are imported
    - How many have school assignments
    - Pipeline completion status
    - Missing schools analysis

    Returns:
        JSON response with pipeline status
    """
    try:
        # Get basic counts
        total_students = Student.query.count()
        students_with_schools = Student.query.filter(Student.school_id.isnot(None)).count()
        students_without_schools = Student.query.filter(Student.school_id.is_(None)).count()

        # Get school statistics
        total_schools = School.query.count()

        # Get students that should have schools but don't
        students_needing_schools = (
            db.session.query(Student)
            .join(Contact, Student.id == Contact.id)
            .filter(Student.school_id.is_(None), Contact.salesforce_individual_id.isnot(None))
            .count()
        )

        # Calculate completion percentages
        phase1_complete = total_students > 0
        phase2_complete = students_without_schools == 0
        pipeline_complete = phase1_complete and phase2_complete

        # Analyze missing schools
        missing_school_analysis = {}
        if students_needing_schools > 0:
            # Get sample of students without schools to analyze
            sample_students = (
                db.session.query(Student)
                .join(Contact, Student.id == Contact.id)
                .filter(Student.school_id.is_(None), Contact.salesforce_individual_id.isnot(None))
                .limit(10)
                .all()
            )

            missing_school_analysis = {
                "students_needing_schools": students_needing_schools,
                "sample_students": [{"name": f"{s.first_name} {s.last_name}", "salesforce_id": s.salesforce_individual_id} for s in sample_students],
            }

        status_data = {
            "pipeline_status": {"phase1_complete": phase1_complete, "phase2_complete": phase2_complete, "pipeline_complete": pipeline_complete},
            "statistics": {
                "total_students": total_students,
                "students_with_schools": students_with_schools,
                "students_without_schools": students_without_schools,
                "total_schools": total_schools,
                "students_needing_schools": students_needing_schools,
            },
            "completion_percentages": {
                "phase1": 100 if phase1_complete else 0,
                "phase2": (students_with_schools / total_students * 100) if total_students > 0 else 0,
                "overall": (students_with_schools / total_students * 100) if total_students > 0 else 0,
            },
            "missing_school_analysis": missing_school_analysis,
            "recommendations": [],
        }

        # Add recommendations based on status
        if not phase1_complete:
            status_data["recommendations"].append("Run Phase 1: Student import")
        elif not phase2_complete:
            status_data["recommendations"].append("Run Phase 2: School assignment")
            if students_needing_schools > 0:
                status_data["recommendations"].append(f"Investigate {students_needing_schools} students without school assignments")
        else:
            status_data["recommendations"].append("Pipeline complete!")

        return jsonify(status_data)

    except Exception as e:
        print(f"Error getting pipeline status: {str(e)}")
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
