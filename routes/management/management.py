"""
Management Routes Module
========================

This module contains all the Flask routes for system management and administration
in the VMS system. It provides administrative functions, data import operations,
and system configuration management.

Key Features:
- Administrative dashboard and user management
- Salesforce data import and synchronization
- Google Sheets integration and management
- Bug report management and resolution
- School and district data management
- System configuration and maintenance

Main Endpoints:
- GET /admin - Administrative dashboard
- POST /admin/import - General data import
- POST /management/import-classes - Import classes from Salesforce
- POST /management/import-schools - Import schools from Salesforce
- POST /management/import-districts - Import districts from Salesforce
- GET/POST /google-sheets - Google Sheets management
- GET/POST /bug-reports - Bug report management

Administrative Functions:
- User management and permissions
- System configuration
- Data import and synchronization
- Error tracking and resolution
- Performance monitoring

Salesforce Integration:
- Class data import and synchronization
- School and district data import
- Batch processing with error handling
- Data validation and cleanup
- Import statistics and reporting

Google Sheets Integration:
- Sheet creation and management
- Data export and synchronization
- Template management
- Access control and permissions

Bug Report Management:
- Report creation and tracking
- Resolution workflow
- Status updates and notifications
- Historical tracking and analytics

Security Features:
- Admin-only access for sensitive operations
- Input validation and sanitization
- Error handling with user feedback
- Data integrity protection
- Audit trail maintenance

Dependencies:
- Flask-Login for authentication
- SQLAlchemy for database operations
- simple-salesforce for Salesforce integration
- Google Sheets API for spreadsheet operations
- Utility functions for data processing

Models Used:
- User: User management and authentication
- Class: Class data for import operations
- School: School data for import operations
- District: District data for import operations
- GoogleSheet: Google Sheets management
- BugReport: Bug report tracking

Template Dependencies:
- management/admin.html: Administrative dashboard
- management/google_sheets.html: Google Sheets management
- management/bug_reports.html: Bug report management
- management/resolve_form.html: Bug resolution form
"""

import os
from datetime import datetime, timezone

import pandas as pd
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

# TODO: Fix import statements for simple_salesforce
from simple_salesforce import SalesforceAuthenticationFailed
from werkzeug.security import generate_password_hash

from models import db
from models.bug_report import BugReport, BugReportType
from models.class_model import Class
from models.district_model import District
from models.google_sheet import GoogleSheet
from models.school_model import School
from models.user import SecurityLevel, User
from utils.academic_year import get_academic_year_range
from utils.salesforce_importer import ImportConfig, ImportHelpers, SalesforceImporter

# Create the management blueprint
management_bp = Blueprint("management", __name__)


def validate_district_record(record: dict) -> tuple[bool, list[str]]:
    """
    Validate a district record from Salesforce.

    Args:
        record: Salesforce record dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if not record.get("Id"):
        errors.append("Missing Salesforce ID")
    if not record.get("Name"):
        errors.append("Missing district name")

    # Validate Salesforce ID format (18 characters)
    if record.get("Id") and len(record["Id"]) != 18:
        errors.append("Invalid Salesforce ID format")

    # Validate name length
    if record.get("Name") and len(record["Name"]) > 255:
        errors.append("District name too long (max 255 characters)")

    return len(errors) == 0, errors


def process_district_record(record: dict, session) -> tuple[bool, str]:
    """
    Process a single district record from Salesforce.

    Args:
        record: Salesforce record dictionary
        session: Database session

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Use ImportHelpers to create or update the district
        district, created = ImportHelpers.create_or_update_record(
            District,
            record["Id"],
            {
                "salesforce_id": record["Id"],  # Include salesforce_id in update_data
                "name": ImportHelpers.clean_string(record.get("Name", "")),
                "district_code": ImportHelpers.clean_string(record.get("School_Code_External_ID__c")),
            },
            session,
        )

        return True, ""

    except Exception as e:
        return False, f"Error processing district {record.get('Name', 'Unknown')}: {str(e)}"


def validate_school_record(record: dict) -> tuple[bool, list[str]]:
    """
    Validate a school record from Salesforce.

    Args:
        record: Salesforce record dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if not record.get("Id"):
        errors.append("Missing Salesforce ID")
    if not record.get("Name"):
        errors.append("Missing school name")

    # Validate Salesforce ID format (accept both 15 and 18 character IDs)
    if record.get("Id"):
        id_length = len(record["Id"])
        if id_length not in [15, 18]:
            errors.append(f"Invalid Salesforce ID format: {record['Id']} (length: {id_length})")

    # Validate name length
    if record.get("Name") and len(record["Name"]) > 255:
        errors.append("School name too long (max 255 characters)")

    return len(errors) == 0, errors


def process_school_record(record: dict, session) -> tuple[bool, str]:
    """
    Process a single school record from Salesforce.

    Args:
        record: Salesforce record dictionary
        session: Database session

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Find the district using salesforce_id
        district = District.query.filter_by(salesforce_id=record.get("ParentId")).first()

        # Try to find existing school by ID (Salesforce ID)
        school = session.query(School).filter_by(id=record["Id"]).first()

        if school:
            # Update existing school
            school.name = ImportHelpers.clean_string(record.get("Name", ""))
            school.district_id = district.id if district else None
            school.salesforce_district_id = ImportHelpers.clean_string(record.get("ParentId"))
            school.normalized_name = ImportHelpers.clean_string(record.get("Connector_Account_Name__c"))
            school.school_code = ImportHelpers.clean_string(record.get("School_Code_External_ID__c"))
        else:
            # Create new school
            school = School(
                id=record["Id"],
                name=ImportHelpers.clean_string(record.get("Name", "")),
                district_id=district.id if district else None,
                salesforce_district_id=ImportHelpers.clean_string(record.get("ParentId")),
                normalized_name=ImportHelpers.clean_string(record.get("Connector_Account_Name__c")),
                school_code=ImportHelpers.clean_string(record.get("School_Code_External_ID__c")),
            )
            session.add(school)

        return True, ""

    except Exception as e:
        return False, f"Error processing school {record.get('Name', 'Unknown')}: {str(e)}"


def validate_class_record(record: dict) -> tuple[bool, list[str]]:
    """
    Validate a class record from Salesforce.

    Args:
        record: Salesforce record dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if not record.get("Id"):
        errors.append("Missing Salesforce ID")
    if not record.get("Name"):
        errors.append("Missing class name")
    if not record.get("School__c"):
        errors.append("Missing school Salesforce ID")
    if not record.get("Class_Year_Number__c"):
        errors.append("Missing class year")

    # Validate Salesforce ID format (18 characters)
    if record.get("Id") and len(record["Id"]) != 18:
        errors.append("Invalid Salesforce ID format")

    # Validate school ID format (18 characters)
    if record.get("School__c") and len(record["School__c"]) != 18:
        errors.append("Invalid school Salesforce ID format")

    # Validate name length
    if record.get("Name") and len(record["Name"]) > 255:
        errors.append("Class name too long (max 255 characters)")

    # Validate class year is numeric
    if record.get("Class_Year_Number__c"):
        try:
            int(record["Class_Year_Number__c"])
        except (ValueError, TypeError):
            errors.append("Class year must be a valid number")

    return len(errors) == 0, errors


def process_class_record(record: dict, session) -> tuple[bool, str]:
    """
    Process a single class record from Salesforce.

    Args:
        record: Salesforce record dictionary
        session: Database session

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Use ImportHelpers to create or update the class
        class_obj, created = ImportHelpers.create_or_update_record(
            Class,
            record["Id"],
            {
                "salesforce_id": record["Id"],  # Include salesforce_id in update_data
                "name": ImportHelpers.clean_string(record.get("Name", "")),
                "school_salesforce_id": ImportHelpers.clean_string(record.get("School__c")),
                "class_year": ImportHelpers.safe_parse_int(record.get("Class_Year_Number__c"), 0),
            },
            session,
        )

        return True, ""

    except Exception as e:
        return False, f"Error processing class {record.get('Name', 'Unknown')}: {str(e)}"


@management_bp.route("/admin")
@login_required
def admin():
    """
    Display the main admin panel.

    Provides administrative interface for user management, system
    configuration, and administrative functions. Requires supervisor
    or higher security level access.

    Permission Requirements:
        - Security level >= SUPERVISOR

    Returns:
        Rendered admin template with user list and configuration options

    Raises:
        Redirect to main index if unauthorized
    """
    if not current_user.security_level >= SecurityLevel.SUPERVISOR:
        flash("Access denied. Supervisor or higher privileges required.", "error")
        return redirect(url_for("main.index"))

    users = User.query.all()
    # Provide academic years with Google Sheets for the dropdown (virtual sessions only)
    from models.google_sheet import GoogleSheet

    sheet_years = [sheet.academic_year for sheet in GoogleSheet.query.filter_by(purpose="virtual_sessions").order_by(GoogleSheet.academic_year.desc()).all()]
    return render_template("management/admin.html", users=users, sheet_years=sheet_years)


@management_bp.route("/admin/import", methods=["POST"])
@login_required
def import_data():
    """
    Handle data import functionality.

    Processes file uploads for data import operations. Currently
    a placeholder for future import functionality.

    Permission Requirements:
        - Admin access required

    Form Parameters:
        import_file: File to import

    Returns:
        Redirect to admin panel with success/error message

    Raises:
        403: Unauthorized access attempt
    """
    if not current_user.is_admin:
        return {"error": "Unauthorized"}, 403

    if "import_file" not in request.files:
        flash("No file provided", "error")
        return redirect(url_for("management.admin"))

    file = request.files["import_file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("management.admin"))

    # TODO: Process the file and import data
    # This will be implemented after creating the model

    flash("Import started successfully", "success")
    return redirect(url_for("management.admin"))


@management_bp.route("/management/import-classes", methods=["POST"])
@login_required
def import_classes():
    """
    Import class data from Salesforce using the optimized framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures

    Salesforce Objects:
        - Class__c: Class data with school associations

    Process Flow:
        1. Authenticate with Salesforce using optimized framework
        2. Query Class__c objects with batch processing
        3. Validate and create/update class records
        4. Associate with schools
        5. Commit all changes with error handling

    Permission Requirements:
        - Admin access required

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        403: Unauthorized access attempt
        500: Import or database error
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=400,  # Process 400 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=80,  # Commit every 80 records
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query
        salesforce_query = """
        SELECT Id, Name, School__c, Class_Year_Number__c
        FROM Class__c
        """

        # Execute the import using the optimized framework
        result = importer.import_data(query=salesforce_query, process_func=process_class_record, validation_func=validate_class_record)

        # Prepare response based on import result
        if result.success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {result.success_count} classes with {result.error_count} errors",
                    "statistics": {
                        "total_records": result.total_records,
                        "processed_count": result.processed_count,
                        "success_count": result.success_count,
                        "error_count": result.error_count,
                        "skipped_count": result.skipped_count,
                        "duration_seconds": result.duration_seconds,
                    },
                    "errors": result.errors[:10] if result.errors else [],  # Limit to first 10 errors
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "message": "Import failed", "error": "Import operation failed", "errors": result.errors[:10] if result.errors else []}
                ),
                500,
            )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Google Sheet Management Routes
@management_bp.route("/google-sheets")
@login_required
def google_sheets():
    """
    Display Google Sheets management interface.

    Shows all configured Google Sheets with their academic years
    and provides options for creating new sheet configurations.

    Permission Requirements:
        - Admin access required

    Returns:
        Rendered Google Sheets management template

    Template Variables:
        sheets: List of all Google Sheet configurations
        available_years: Academic years available for new sheets
        sheet_years: Years that already have sheet configurations
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("main.index"))
    sheets = GoogleSheet.query.filter_by(purpose="virtual_sessions").order_by(GoogleSheet.academic_year.desc()).all()
    all_years = get_academic_year_range(2018, 2032)
    used_years = {sheet.academic_year for sheet in sheets}
    available_years = [y for y in all_years if y not in used_years]
    sheet_years = [sheet.academic_year for sheet in sheets]
    return render_template("management/google_sheets.html", sheets=sheets, available_years=available_years, sheet_years=sheet_years)


@management_bp.route("/google-sheets", methods=["POST"])
@login_required
def create_google_sheet():
    """
    Create a new Google Sheet configuration.

    Creates a new Google Sheet record with encrypted sheet ID
    and associates it with an academic year.

    Permission Requirements:
        - Admin access required

    Request Body (JSON):
        academic_year: Academic year for the sheet
        sheet_id: Google Sheet ID to associate

    Validation:
        - Academic year and sheet ID are required
        - No duplicate academic years allowed
        - Encryption key must be configured

    Returns:
        JSON response with success status and sheet data

    Raises:
        400: Missing required fields or duplicate academic year
        403: Unauthorized access attempt
        500: Database or encryption error
    """
    print("GOOGLE SHEETS ROUTE HIT")
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        # Debug environment variable
        encryption_key = os.getenv("ENCRYPTION_KEY")
        print(f"DEBUG: ENCRYPTION_KEY exists: {encryption_key is not None}")
        if encryption_key:
            print(f"DEBUG: ENCRYPTION_KEY length: {len(encryption_key)}")
        else:
            print("DEBUG: ENCRYPTION_KEY is None or empty")

        data = request.get_json()
        print("GOT DATA:", data)
        academic_year = data.get("academic_year")
        sheet_id = data.get("sheet_id")
        print("ACADEMIC YEAR:", academic_year, "SHEET ID:", sheet_id)

        if not all([academic_year, sheet_id]):
            return jsonify({"error": "Academic year and sheet ID are required"}), 400

        existing = GoogleSheet.query.filter_by(academic_year=academic_year, purpose="virtual_sessions").first()
        if existing:
            return jsonify({"error": f"Virtual sessions sheet for academic year {academic_year} already exists"}), 400

        print(f"DEBUG: About to create GoogleSheet with sheet_id: {sheet_id}")
        new_sheet = GoogleSheet(academic_year=academic_year, sheet_id=sheet_id, created_by=current_user.id, purpose="virtual_sessions")
        print("DEBUG: GoogleSheet created successfully")

        db.session.add(new_sheet)
        db.session.commit()

        return jsonify({"success": True, "message": f"Google Sheet for {academic_year} created successfully", "sheet": new_sheet.to_dict()})
    except Exception as e:
        print("EXCEPTION:", e)
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["PUT"])
@login_required
def update_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        data = request.get_json()
        if "sheet_id" in data:
            sheet.update_sheet_id(data["sheet_id"])
        db.session.commit()
        return jsonify({"success": True, "message": "Google Sheet updated successfully", "sheet": sheet.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["DELETE"])
@login_required
def delete_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        academic_year = sheet.academic_year
        db.session.delete(sheet)
        db.session.commit()
        return jsonify({"success": True, "message": f"Google Sheet for {academic_year} deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["GET"])
@login_required
def get_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        return jsonify({"success": True, "sheet": sheet.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@management_bp.route("/management/import-schools", methods=["POST"])
@login_required
def import_schools():
    """
    Import schools and districts from Salesforce using the optimized framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures
    - Two-phase import: districts first, then schools

    Salesforce Objects:
        - Account (Type = 'School District'): District data
        - Account (Type = 'School'): School data with district relationships

    Process Flow:
        1. Import districts using optimized framework
        2. Import schools using optimized framework
        3. Update school levels automatically
        4. Provide comprehensive statistics

    Permission Requirements:
        - Admin access required

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        403: Unauthorized access attempt
        500: Import or database error
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Phase 1: Import Districts
        print("Starting district import process...")

        # Configure the district import with optimized settings
        district_config = ImportConfig(
            batch_size=300,  # Process 300 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=60,  # Commit every 60 records
        )

        # Initialize the Salesforce importer for districts
        district_importer = SalesforceImporter(district_config)

        # Define the district query
        district_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account
        WHERE Type = 'School District'
        """

        # Execute the district import using the optimized framework
        district_result = district_importer.import_data(query=district_query, process_func=process_district_record, validation_func=validate_district_record)

        print(f"District import complete: {district_result.success_count} successes, {district_result.error_count} errors")

        # Phase 2: Import Schools
        print("Starting school import process...")

        # Configure the school import with optimized settings
        school_config = ImportConfig(
            batch_size=400,  # Process 400 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=80,  # Commit every 80 records
        )

        # Initialize the Salesforce importer for schools
        school_importer = SalesforceImporter(school_config)

        # Define the school query - include all school types, not just 'School'
        school_query = """
        SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c
        FROM Account
        WHERE Type = 'School' OR Type LIKE '%School%' OR Type LIKE '%Academy%' OR Type LIKE '%Elementary%' OR Type LIKE '%High%' OR Type LIKE '%Middle%'
        """

        # Execute the school import using the optimized framework
        school_result = school_importer.import_data(query=school_query, process_func=process_school_record, validation_func=validate_school_record)

        print(f"School import complete: {school_result.success_count} successes, {school_result.error_count} errors")

        # After successful school import, update school levels
        level_update_response = update_school_levels()

        # Prepare comprehensive response
        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {district_result.success_count} districts and {school_result.success_count} schools",
                "district_statistics": {
                    "total_records": district_result.total_records,
                    "processed_count": district_result.processed_count,
                    "success_count": district_result.success_count,
                    "error_count": district_result.error_count,
                    "skipped_count": district_result.skipped_count,
                    "duration_seconds": district_result.duration_seconds,
                },
                "school_statistics": {
                    "total_records": school_result.total_records,
                    "processed_count": school_result.processed_count,
                    "success_count": school_result.success_count,
                    "error_count": school_result.error_count,
                    "skipped_count": school_result.skipped_count,
                    "duration_seconds": school_result.duration_seconds,
                },
                "district_errors": district_result.errors[:10] if district_result.errors else [],
                "school_errors": school_result.errors[:10] if school_result.errors else [],
                "level_update": level_update_response.json if hasattr(level_update_response, "json") else None,
            }
        )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@management_bp.route("/management/import-districts", methods=["POST"])
@login_required
def import_districts():
    """
    Import districts from Salesforce using the optimized framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures

    Salesforce Objects:
        - Account (Type = 'School District'): District data

    Process Flow:
        1. Authenticate with Salesforce using optimized framework
        2. Query Account objects with batch processing
        3. Validate and create/update district records
        4. Commit all changes with error handling

    Permission Requirements:
        - Admin access required

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        403: Unauthorized access attempt
        500: Import or database error
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=300,  # Process 300 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=60,  # Commit every 60 records
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query
        salesforce_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account
        WHERE Type = 'School District'
        """

        # Execute the import using the optimized framework
        result = importer.import_data(query=salesforce_query, process_func=process_district_record, validation_func=validate_district_record)

        # Prepare response based on import result
        if result.success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {result.success_count} districts with {result.error_count} errors",
                    "statistics": {
                        "total_records": result.total_records,
                        "processed_count": result.processed_count,
                        "success_count": result.success_count,
                        "error_count": result.error_count,
                        "skipped_count": result.skipped_count,
                        "duration_seconds": result.duration_seconds,
                    },
                    "errors": result.errors[:10] if result.errors else [],  # Limit to first 10 errors
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "message": "Import failed", "error": "Import operation failed", "errors": result.errors[:10] if result.errors else []}
                ),
                500,
            )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@management_bp.route("/schools")
@login_required
def schools():
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("main.index"))

    districts = District.query.order_by(District.name).all()
    schools = School.query.order_by(School.name).all()
    sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else None

    return render_template("management/schools.html", districts=districts, schools=schools, sheet_url=sheet_url)


@management_bp.route("/management/schools/<school_id>", methods=["DELETE"])
@login_required
def delete_school(school_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        school = School.query.get_or_404(school_id)
        db.session.delete(school)
        db.session.commit()
        return jsonify({"success": True, "message": "School deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@management_bp.route("/management/districts/<district_id>", methods=["DELETE"])
@login_required
def delete_district(district_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        district = District.query.get_or_404(district_id)
        db.session.delete(district)  # This will cascade delete associated schools
        db.session.commit()
        return jsonify({"success": True, "message": "District and associated schools deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@management_bp.route("/bug-reports")
@login_required
def bug_reports():
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("main.index"))

    # Get all bug reports, newest first
    reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    return render_template("management/bug_reports.html", reports=reports, BugReportType=BugReportType)


@management_bp.route("/bug-reports/<int:report_id>/resolve", methods=["POST"])
@login_required
def resolve_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        report = BugReport.query.get_or_404(report_id)
        report.resolved = True
        report.resolved_by_id = current_user.id
        report.resolved_at = datetime.now(timezone.utc)
        report.resolution_notes = request.form.get("notes", "")

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/bug-reports/<int:report_id>", methods=["DELETE"])
@login_required
def delete_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        report = BugReport.query.get_or_404(report_id)
        db.session.delete(report)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/bug-reports/<int:report_id>/resolve-form")
@login_required
def get_resolve_form(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    return render_template("management/resolve_form.html", report_id=report_id)


@management_bp.route("/management/update-school-levels", methods=["POST"])
@login_required
def update_school_levels():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
        print(f"DEBUG: SCHOOL_MAPPING_GOOGLE_SHEET = {sheet_id}")

        if not sheet_id:
            raise ValueError("School mapping Google Sheet ID not configured")

        # Try primary URL format
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        print(f"DEBUG: Trying CSV URL: {csv_url}")

        try:
            df = pd.read_csv(csv_url)
            print(f"DEBUG: Successfully read CSV with {len(df)} rows")
            print(f"DEBUG: CSV columns: {list(df.columns)}")
        except Exception as e:
            current_app.logger.error(f"Failed to read CSV: {str(e)}")
            print(f"DEBUG: Failed to read CSV with primary URL: {str(e)}")

            # Try alternative URL format
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            print(f"DEBUG: Trying alternative CSV URL: {csv_url}")
            df = pd.read_csv(csv_url)
            print(f"DEBUG: Successfully read CSV with alternative URL, {len(df)} rows")

        success_count = 0
        error_count = 0
        errors = []

        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip rows without an ID or Level
                if pd.isna(row["Id"]) or pd.isna(row["Level"]):
                    print(f"DEBUG: Skipping row {index} - missing Id or Level")
                    continue

                print(f"DEBUG: Processing row {index} - Id: {row['Id']}, Level: {row['Level']}")

                # Find the school by Salesforce ID
                school = School.query.get(row["Id"])
                if school:
                    school.level = row["Level"].strip()
                    success_count += 1
                    print(f"DEBUG: Updated school {school.name} to level {school.level}")
                else:
                    error_count += 1
                    error_msg = f"School not found with ID: {row['Id']}"
                    errors.append(error_msg)
                    print(f"DEBUG: {error_msg}")

            except Exception as e:
                error_count += 1
                error_msg = f"Error processing school {row.get('Id')}: {str(e)}"
                errors.append(error_msg)
                print(f"DEBUG: {error_msg}")

        db.session.commit()
        print(f"DEBUG: Final result - {success_count} successes, {error_count} errors")

        return jsonify({"success": True, "message": f"Successfully updated {success_count} schools with {error_count} errors", "errors": errors})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("School level update failed", exc_info=True)
        print(f"DEBUG: School level update failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400


@management_bp.route("/management/users/<int:user_id>/edit", methods=["GET"])
@login_required
def edit_user_form(user_id):
    """Route to render the user edit modal"""
    if not current_user.is_admin and not current_user.security_level >= SecurityLevel.SUPERVISOR:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    # Check if current user has permission to edit this user
    if not current_user.can_manage_user(user) and current_user.id != user_id:
        return jsonify({"error": "Unauthorized to edit this user"}), 403

    return render_template("management/user_edit_modal.html", user=user)


@management_bp.route("/management/users/<int:user_id>", methods=["PUT"])
@login_required
def update_user(user_id):
    """Route to handle the user update form submission"""
    if not current_user.is_admin and not current_user.security_level >= SecurityLevel.SUPERVISOR:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    # Check if current user has permission to edit this user
    if not current_user.can_manage_user(user) and current_user.id != user_id:
        return jsonify({"error": "Unauthorized to edit this user"}), 403

    # Get form data
    email = request.form.get("email")
    security_level = int(request.form.get("security_level", 0))
    new_password = request.form.get("new_password")

    # If not admin, restrict ability to escalate privileges
    if not current_user.is_admin and security_level > current_user.security_level:
        return jsonify({"error": "Cannot assign security level higher than your own"}), 403

    # Update user
    user.email = email

    # Regular users should only be able to update their own security level if they're an admin
    if current_user.is_admin or current_user.security_level > user.security_level:
        user.security_level = security_level

    # Update password if provided
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
