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

from datetime import datetime

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


def _ensure_sf_affiliation_column():
    """Ensure the student table has sf_primary_affiliation_id column and index."""
    from sqlalchemy import inspect, text

    insp = inspect(db.engine)
    columns = {col["name"] for col in insp.get_columns("student")}
    if "sf_primary_affiliation_id" not in columns:
        db.session.execute(text("ALTER TABLE student ADD COLUMN sf_primary_affiliation_id VARCHAR(18)"))
        db.session.commit()
    # Create index if missing (SQLite IF NOT EXISTS supported for index creation)
    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_student_sf_affiliation ON student (sf_primary_affiliation_id)"))
    db.session.commit()


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


@students_bp.route("/students/backfill-affiliations", methods=["POST"])
@login_required
def backfill_student_affiliations():
    """
    One-time backfill to populate Student.sf_primary_affiliation_id from Salesforce
    for students missing this value. This enables a fully local Phase 2 assignment.
    """
    try:
        print("Starting backfill of student affiliations...")
        _ensure_sf_affiliation_column()

        # Build set of local students needing backfill
        rows = db.session.query(Student.id, Student.salesforce_individual_id).filter(Student.sf_primary_affiliation_id.is_(None)).all()
        missing_ids = {sid for (_, sid) in rows if sid}

        if not missing_ids:
            return jsonify(
                {
                    "success": True,
                    "message": "No backfill needed. All students already have affiliations stored.",
                    "statistics": {"target_students": 0, "updated": 0, "skipped": 0},
                }
            )

        # Fast lookup of local students by SF Contact Id (only those missing)
        id_to_student = {sid: sid for sid in missing_ids}

        # Configure importer for a single Salesforce scan
        config = ImportConfig(
            batch_size=2000, max_retries=3, retry_delay_seconds=2, validate_data=False, log_progress=False, commit_frequency=500, timeout_seconds=300
        )
        importer = SalesforceImporter(config=config)

        updated_count = 0

        def process_affiliation(record, session):
            nonlocal updated_count
            sf_id = record.get("Id")
            aff = record.get("npsp__Primary_Affiliation__c")
            if not sf_id or not aff:
                return False
            if sf_id not in id_to_student:
                return False
            # Update only if currently null
            student = Student.query.filter_by(salesforce_individual_id=sf_id).first()
            if not student or student.sf_primary_affiliation_id:
                return False
            student.sf_primary_affiliation_id = aff
            updated_count += 1
            return True

        query = """
        SELECT Id, npsp__Primary_Affiliation__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        AND npsp__Primary_Affiliation__c != NULL
        """

        result = importer.import_data(query=query, process_func=process_affiliation, validation_func=None)

        # Summarize
        return jsonify(
            {
                "success": True,
                "message": f"Backfill complete. Updated {updated_count} students.",
                "statistics": {
                    "target_students": len(missing_ids),
                    "processed_from_sf": result.total_records,
                    "updated": updated_count,
                    "errors": result.error_count,
                },
                "errors": result.errors,
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"Backfill failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


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
        AND npsp__Primary_Affiliation__c != NULL
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
                # Don't commit here - let the framework handle it
                # db_session.commit()

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
        print("Expected: ~150,000 students to process")
        print("Progress updates: Every 10,000 students")
        print("Batch size: 2,000 students per batch")
        print("Commit frequency: Every 50 batches (~100,000 students)")

        # Ensure schema has sf_primary_affiliation_id to persist affiliation locally
        _ensure_sf_affiliation_column()

        # Configure the import with optimized settings for large datasets
        config = ImportConfig(
            batch_size=2000,  # Larger batches for faster processing of 150k students
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=50,  # Commit every 50 batches = ~100k students for progress updates
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

        # Custom progress callback for detailed updates every 10k students
        def progress_callback(processed_count, total_count, message):
            if processed_count % 10000 == 0 and processed_count > 0:
                percentage = (processed_count / total_count) * 100
                print(f"Progress: {processed_count:,}/{total_count:,} students ({percentage:.1f}%) - {message}")
                print(f"  Success rate: {stats.get('success_count', 0):,} successes, {stats.get('error_count', 0):,} errors")

        # Track statistics for progress reporting
        stats = {"success_count": 0, "error_count": 0}

        print(f"Executing student import with query: {student_query}")
        result = importer.import_data(
            query=student_query,
            process_func=process_student_record_without_school,
            validation_func=validate_student_record,
            progress_callback=progress_callback,
        )
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
        # Ensure schema has the required column for local assignment
        _ensure_sf_affiliation_column()

        # Phase 2 is now fully local: assign school_id from sf_primary_affiliation_id where the school exists
        # Build local datasets once
        students_without_schools = (
            db.session.query(Student.id, Student.salesforce_individual_id, Student.sf_primary_affiliation_id).filter(Student.school_id.is_(None)).all()
        )
        missing_student_ids = {sid for (_, sid, aff) in students_without_schools if sid}
        # If none of the missing students have an affiliation captured, advise backfill
        missing_with_affiliation = [1 for (_, sid, aff) in students_without_schools if aff]
        if not missing_with_affiliation:
            return jsonify(
                {
                    "success": False,
                    "message": "No local affiliations found. Run Backfill Student Affiliations, then re-run Phase 2.",
                    "phase": "school_assignment",
                    "errors": ["sf_primary_affiliation_id is empty for students needing assignment"],
                    "statistics": {
                        "total_records": len(missing_student_ids),
                        "processed_count": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "skipped_count": 0,
                    },
                }
            )

        if not missing_student_ids:
            return jsonify(
                {
                    "success": True,
                    "message": "No students need school assignments",
                    "phase": "school_assignment",
                    "statistics": {
                        "total_records": 0,
                        "processed_count": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "skipped_count": 0,
                        "duration_seconds": 0,
                        "total_students": Student.query.count(),
                        "students_with_schools": Student.query.filter(Student.school_id.isnot(None)).count(),
                        "students_without_schools": 0,
                    },
                    "errors": [],
                    "warnings": ["All students already have school assignments"],
                    "pipeline_complete": True,
                }
            )

        # Perform a more careful school assignment
        # Only assign schools when the affiliation is valid and the school exists
        from sqlalchemy import text

        # First, let's see what affiliations we have
        cursor = db.session.execute(
            text(
                """
            SELECT DISTINCT sf_primary_affiliation_id, COUNT(*) as student_count
            FROM student
            WHERE school_id IS NULL AND sf_primary_affiliation_id IS NOT NULL
            GROUP BY sf_primary_affiliation_id
            ORDER BY student_count DESC
            LIMIT 10
        """
            )
        )

        affiliation_counts = cursor.fetchall()
        print("Top affiliations needing assignment:")
        for affiliation, count in affiliation_counts:
            print(f"  {affiliation}: {count} students")

        # Only assign schools that actually exist and are valid
        update_sql = text(
            """
            UPDATE student
            SET school_id = sf_primary_affiliation_id
            WHERE school_id IS NULL
              AND sf_primary_affiliation_id IS NOT NULL
              AND sf_primary_affiliation_id IN (SELECT id FROM school)
              AND sf_primary_affiliation_id != '0015f00000JUL8CAAX'  -- Exclude problematic school
            """
        )
        result_proxy = db.session.execute(update_sql)
        db.session.commit()
        updated_rows = result_proxy.rowcount if hasattr(result_proxy, "rowcount") else 0

        # Get additional statistics about school assignments
        total_students = Student.query.count()
        students_with_schools = Student.query.filter(Student.school_id.isnot(None)).count()
        students_without_schools = Student.query.filter(Student.school_id.is_(None)).count()

        response_data = {
            "success": True,
            "message": f"Phase 2 complete: Assigned schools to {updated_rows} students",
            "phase": "school_assignment",
            "statistics": {
                "total_records": len(missing_student_ids),
                "processed_count": len(missing_student_ids),
                "success_count": updated_rows,
                "error_count": 0,
                "skipped_count": 0,
                "duration_seconds": 0,
                "total_students": total_students,
                "students_with_schools": students_with_schools,
                "students_without_schools": students_without_schools,
            },
            "errors": [],
            "warnings": [],
            "pipeline_complete": students_without_schools == 0,
        }

        print(f"School assignment complete: {updated_rows} assignments")
        print(f"Total students: {total_students}, With schools: {students_with_schools}, Without schools: {students_without_schools}")

        # No errors expected for local update; keep placeholder if needed

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


@students_bp.route("/students/import-status-report", methods=["GET"])
@login_required
def get_import_status_report():
    """
    Get a comprehensive import status report showing what didn't get linked.

    This provides detailed analysis of:
    - Students with/without school assignments
    - Missing school affiliations
    - Students with affiliations but no corresponding schools
    - Recommendations for fixing issues

    Returns:
        JSON response with detailed import status
    """
    try:

        # Get basic statistics
        total_students = Student.query.count()
        students_with_schools = Student.query.filter(Student.school_id.isnot(None)).count()
        students_without_schools = Student.query.filter(Student.school_id.is_(None)).count()
        total_schools = School.query.count()

        # Get students with affiliations but no school assignments
        students_with_affiliations_no_school = (
            db.session.query(Student).filter(Student.sf_primary_affiliation_id.isnot(None), Student.school_id.is_(None)).count()
        )

        # Get students without any affiliation data
        students_no_affiliation = db.session.query(Student).filter(Student.sf_primary_affiliation_id.is_(None), Student.school_id.is_(None)).count()

        # Get missing school affiliations (affiliations that don't correspond to existing schools)
        missing_school_affiliations = (
            db.session.query(Student.sf_primary_affiliation_id, db.func.count(Student.id).label("student_count"))
            .filter(
                Student.sf_primary_affiliation_id.isnot(None), Student.school_id.is_(None), ~Student.sf_primary_affiliation_id.in_(db.session.query(School.id))
            )
            .group_by(Student.sf_primary_affiliation_id)
            .order_by(db.desc("student_count"))
            .limit(20)
            .all()
        )

        # Get sample students without school assignments
        sample_unassigned = db.session.query(Student, Contact).join(Contact, Student.id == Contact.id).filter(Student.school_id.is_(None)).limit(10).all()

        # Get sample students with missing schools
        sample_missing_schools = (
            db.session.query(Student, Contact)
            .join(Contact, Student.id == Contact.id)
            .filter(
                Student.sf_primary_affiliation_id.isnot(None), Student.school_id.is_(None), ~Student.sf_primary_affiliation_id.in_(db.session.query(School.id))
            )
            .limit(10)
            .all()
        )

        # Calculate completion percentages
        completion_percentage = (students_with_schools / total_students * 100) if total_students > 0 else 0

        # Generate recommendations
        recommendations = []
        if students_with_affiliations_no_school > 0:
            recommendations.append(f"{students_with_affiliations_no_school:,} students have affiliations but no school assignments")
            recommendations.append("Check if these affiliations correspond to schools that need to be imported")

        if students_no_affiliation > 0:
            recommendations.append(f"{students_no_affiliation:,} students have no affiliation data")
            recommendations.append("These students may need affiliation data updated in Salesforce")

        if missing_school_affiliations:
            recommendations.append("Import missing schools or update affiliations in Salesforce")

        # Build response data
        report_data = {
            "summary": {
                "total_students": total_students,
                "students_with_schools": students_with_schools,
                "students_without_schools": students_without_schools,
                "total_schools": total_schools,
                "completion_percentage": round(completion_percentage, 1),
            },
            "detailed_breakdown": {
                "students_with_affiliations_no_school": students_with_affiliations_no_school,
                "students_no_affiliation": students_no_affiliation,
            },
            "missing_school_affiliations": [
                {"affiliation_id": affiliation_id, "student_count": count} for affiliation_id, count in missing_school_affiliations
            ],
            "sample_unassigned_students": [
                {
                    "name": f"{contact.first_name} {contact.last_name}",
                    "salesforce_id": contact.salesforce_individual_id,
                    "affiliation": student.sf_primary_affiliation_id,
                }
                for student, contact in sample_unassigned
            ],
            "sample_missing_schools": [
                {
                    "name": f"{contact.first_name} {contact.last_name}",
                    "salesforce_id": contact.salesforce_individual_id,
                    "missing_school": student.sf_primary_affiliation_id,
                }
                for student, contact in sample_missing_schools
            ],
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

        return jsonify({"success": True, "message": "Import status report generated successfully", "data": report_data})

    except Exception as e:
        print(f"Error generating import status report: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/export-unassigned-students", methods=["GET"])
@login_required
def export_unassigned_students():
    """
    Export a list of students without school assignments for analysis.

    This creates a CSV file with students who don't have school assignments,
    including their Salesforce IDs and affiliations for manual review.

    Returns:
        CSV file download with unassigned students
    """
    try:
        import csv
        import tempfile

        from flask import send_file

        # Get students without school assignments
        unassigned_students = db.session.query(Student, Contact).join(Contact, Student.id == Contact.id).filter(Student.school_id.is_(None)).all()

        # Create temporary CSV file
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv", newline="")

        with temp_file:
            writer = csv.writer(temp_file)
            writer.writerow(["First Name", "Last Name", "Salesforce ID", "Affiliation ID", "Email", "Phone"])

            for student, contact in unassigned_students:
                writer.writerow(
                    [
                        contact.first_name,
                        contact.last_name,
                        contact.salesforce_individual_id,
                        student.sf_primary_affiliation_id,
                        contact.email or "",
                        contact.phone or "",
                    ]
                )

        # Return file for download
        return send_file(
            temp_file.name, as_attachment=True, download_name=f'unassigned_students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', mimetype="text/csv"
        )

    except Exception as e:
        print(f"Error exporting unassigned students: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/import-dashboard", methods=["GET"])
@login_required
def view_import_dashboard():
    """
    View the import dashboard page.

    Returns:
        Rendered import dashboard template
    """
    return render_template("students/import_dashboard.html")


@students_bp.route("/students/import-dashboard-data", methods=["GET"])
@login_required
def get_import_dashboard_data():
    """
    Get data for a real-time import dashboard.

    This provides aggregated statistics and visualizations for:
    - Import completion status
    - Top schools by student count
    - Missing schools analysis
    - Real-time progress tracking

    Returns:
        JSON response with dashboard data
    """
    try:
        # Get basic statistics
        total_students = Student.query.count()
        students_with_schools = Student.query.filter(Student.school_id.isnot(None)).count()
        students_without_schools = Student.query.filter(Student.school_id.is_(None)).count()

        # Get top schools by student count
        top_schools = (
            db.session.query(School, db.func.count(Student.id).label("student_count"))
            .join(Student, School.id == Student.school_id)
            .group_by(School.id)
            .order_by(db.desc("student_count"))
            .limit(10)
            .all()
        )

        # Get missing schools analysis
        missing_schools = (
            db.session.query(Student.sf_primary_affiliation_id, db.func.count(Student.id).label("student_count"))
            .filter(
                Student.sf_primary_affiliation_id.isnot(None), Student.school_id.is_(None), ~Student.sf_primary_affiliation_id.in_(db.session.query(School.id))
            )
            .group_by(Student.sf_primary_affiliation_id)
            .order_by(db.desc("student_count"))
            .limit(10)
            .all()
        )

        # Calculate completion percentages
        completion_percentage = (students_with_schools / total_students * 100) if total_students > 0 else 0

        dashboard_data = {
            "summary": {
                "total_students": total_students,
                "students_with_schools": students_with_schools,
                "students_without_schools": students_without_schools,
                "completion_percentage": round(completion_percentage, 1),
            },
            "top_schools": [{"school_id": school.id, "name": school.name, "student_count": count} for school, count in top_schools],
            "missing_schools": [{"affiliation_id": affiliation_id, "student_count": count} for affiliation_id, count in missing_schools],
            "last_updated": datetime.now().isoformat(),
        }

        return jsonify({"success": True, "message": "Dashboard data retrieved successfully", "data": dashboard_data})

    except Exception as e:
        print(f"Error getting dashboard data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/test-import-limited", methods=["POST"])
@login_required
def test_student_import_limited():
    """
    Test Phase 1: Import limited student data (1000 students) to debug affiliation issues.

    This is a test version of the import to check if the affiliation data is being captured properly.
    """
    try:
        print("Starting Test Phase 1: Limited student import (1000 students)...")
        # Ensure schema has sf_primary_affiliation_id to persist affiliation locally
        _ensure_sf_affiliation_column()

        # Configure the import with optimized settings for testing
        config = ImportConfig(
            batch_size=100,  # Smaller batches for testing
            max_retries=3,
            retry_delay_seconds=2,
            validate_data=True,
            log_progress=True,
            commit_frequency=20,
        )

        # Create the importer
        importer = SalesforceImporter(config=config)

        # Define the query for students with LIMIT for testing
        student_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email, Phone,
               Local_Student_ID__c, Birthdate, Gender__c, Racial_Ethnic_Background__c,
               npsp__Primary_Affiliation__c, Class__c, Legacy_Grade__c, Current_Grade__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        LIMIT 1000
        """

        print(f"Executing limited student import with query: {student_query}")

        # Track affiliation data capture
        affiliation_stats = {"with_affiliation": 0, "without_affiliation": 0}
        students_without_affiliation_examples = []  # Track examples for debugging

        def test_process_student_record(record, db_session):
            """Test version of process function with affiliation tracking"""
            try:
                # Track affiliation data from Salesforce
                sf_affiliation = record.get("npsp__Primary_Affiliation__c")
                student_name = f"{record.get('FirstName', '')} {record.get('LastName', '')}"

                if sf_affiliation:
                    affiliation_stats["with_affiliation"] += 1
                else:
                    affiliation_stats["without_affiliation"] += 1
                    # Store example for debugging (limit to 3)
                    if len(students_without_affiliation_examples) < 3:
                        students_without_affiliation_examples.append(
                            {"name": student_name, "sf_id": record.get("Id"), "affiliation_value": sf_affiliation, "account_id": record.get("AccountId")}
                        )

                # Use the Student model's import method but skip school assignment
                student, is_new, error = Student.import_from_salesforce_without_school(record, db_session)

                if error:
                    print(f"Student import error: {error}")
                    return False

                # Handle contact info using the student's method
                try:
                    success, error = student.update_contact_info(record, db_session)
                    if not success:
                        print(f"Contact info update error: {error}")
                        return False
                except Exception as e:
                    print(f"Contact info update exception: {str(e)}")
                    return False

                return True

            except Exception as e:
                print(f"Process record exception: {str(e)}")
                return False

        result = importer.import_data(query=student_query, process_func=test_process_student_record, validation_func=validate_student_record)

        print(f"Import result: total_records={result.total_records}, processed_count={result.processed_count}, success_count={result.success_count}")
        print(f"Affiliation stats: {affiliation_stats}")
        print(f"Students without affiliation examples: {students_without_affiliation_examples}")

        # Check what was actually imported
        total_students = Student.query.count()
        students_with_affiliations = Student.query.filter(Student.sf_primary_affiliation_id.isnot(None)).count()
        students_without_affiliations = Student.query.filter(Student.sf_primary_affiliation_id.is_(None)).count()

        response_data = {
            "success": result.success,
            "message": f"Test Phase 1 complete: Successfully processed {result.success_count} students",
            "phase": "test_student_import",
            "statistics": {
                "total_records": result.total_records,
                "processed_count": result.processed_count,
                "success_count": result.success_count,
                "error_count": result.error_count,
                "skipped_count": result.skipped_count,
                "duration_seconds": result.duration_seconds,
                "affiliation_stats": affiliation_stats,
                "imported_students": total_students,
                "students_with_affiliations": students_with_affiliations,
                "students_without_affiliations": students_without_affiliations,
            },
            "debug_info": {"students_without_affiliation_examples": students_without_affiliation_examples},
            "errors": result.errors,
            "warnings": result.warnings,
        }

        print(f"Test student import complete: {result.success_count} successes, {result.error_count} errors")
        print(f"Affiliation capture: {students_with_affiliations} with affiliations, {students_without_affiliations} without")

        if result.errors:
            print("Test import errors:")
            for error in result.errors:
                print(f"  - {error}")

        return jsonify(response_data)

    except SalesforceAuthenticationFailed:
        print("Salesforce authentication failed")
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        print(f"Test student import failed with error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/check-affiliation-status", methods=["GET"])
@login_required
def check_affiliation_status():
    """
    Quick check of current affiliation data status.
    """
    try:
        total_students = Student.query.count()
        students_with_affiliations = Student.query.filter(Student.sf_primary_affiliation_id.isnot(None)).count()
        students_without_affiliations = Student.query.filter(Student.sf_primary_affiliation_id.is_(None)).count()

        # Get a sample of students with affiliations
        sample_with_affiliations = Student.query.filter(Student.sf_primary_affiliation_id.isnot(None)).limit(5).all()

        sample_data = []
        for student in sample_with_affiliations:
            sample_data.append(
                {"name": f"{student.first_name} {student.last_name}", "sf_affiliation_id": student.sf_primary_affiliation_id, "school_id": student.school_id}
            )

        response_data = {
            "success": True,
            "statistics": {
                "total_students": total_students,
                "students_with_affiliations": students_with_affiliations,
                "students_without_affiliations": students_without_affiliations,
                "affiliation_percentage": round((students_with_affiliations / total_students * 100), 2) if total_students > 0 else 0,
            },
            "sample_data": sample_data,
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route("/students/show-no-affiliation-examples", methods=["GET"])
@login_required
def show_no_affiliation_examples():
    """
    Show examples of students without affiliations from the current database.
    """
    try:
        # Get 3 examples of students without affiliations
        students_without_affiliations = (
            db.session.query(Student, Contact).join(Contact, Student.id == Contact.id).filter(Student.sf_primary_affiliation_id.is_(None)).limit(3).all()
        )

        examples = []
        for student, contact in students_without_affiliations:
            examples.append(
                {
                    "name": f"{contact.first_name} {contact.last_name}",
                    "sf_id": contact.salesforce_individual_id,
                    "affiliation_value": student.sf_primary_affiliation_id,
                    "account_id": student.salesforce_account_id,
                }
            )

        response_data = {
            "success": True,
            "examples": examples,
            "total_without_affiliations": Student.query.filter(Student.sf_primary_affiliation_id.is_(None)).count(),
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def load_routes(bp):
    """Load student routes into the main blueprint"""
    bp.register_blueprint(students_bp)
