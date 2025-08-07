"""
Organization Routes Module
=========================

This module contains all the Flask routes for managing organizations in the VMS system.
It provides CRUD operations, Salesforce integration, and data management functionality.

Key Features:
- Organization listing with search, filtering, and pagination
- Create, read, update, and delete operations
- Salesforce data import and synchronization
- Volunteer-organization relationship management
- Data purging and cleanup operations
- Affiliation tracking and management

Main Endpoints:
- GET /organizations - List organizations with filtering
- GET /organizations/view/<id> - View organization details
- GET/POST /organizations/add - Create new organization
- GET/POST /organizations/edit/<id> - Edit existing organization
- DELETE /organizations/delete/<id> - Delete organization
- POST /organizations/purge - Purge all organizations
- POST /organizations/import-from-salesforce - Import from Salesforce
- POST /organizations/import-affiliations-from-salesforce - Import affiliations

Organization Management:
- Comprehensive organization profiles
- Type categorization and filtering
- Address and contact information
- Volunteer relationship tracking
- Activity history and engagement metrics

Salesforce Integration:
- Organization data import from Salesforce
- Affiliation relationship synchronization
- Batch processing with error handling
- Data validation and cleanup
- Import statistics and reporting

Filtering and Search:
- Text search across organization names
- Type-based filtering
- Sortable columns (name, type, activity date)
- Configurable pagination
- Filter state preservation

Security Features:
- Login required for all operations
- Input validation and sanitization
- Error handling with user feedback
- Data integrity protection
- Soft delete capabilities

Dependencies:
- Flask-Login for authentication
- SQLAlchemy for database operations
- simple-salesforce for Salesforce integration
- CSV processing for data import
- Utility functions for date parsing

Models Used:
- Organization: Main organization data
- VolunteerOrganization: Volunteer-organization relationships
- Volunteer: Volunteer data for relationships
- Event: Event data for activity tracking
- EventParticipation: Volunteer participation data
- Contact: Contact information
- Teacher: Teacher data
- District: District associations
- School: School relationships

Template Dependencies:
- organizations/organizations.html: Main listing page
- organizations/view.html: Organization detail view
- organizations/add_organization.html: Organization creation form
- organizations/edit_organization.html: Organization editing form
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

# TODO: Fix import statements for simple_salesforce
from simple_salesforce import SalesforceAuthenticationFailed

from models import db
from models.contact import Contact
from models.district_model import District
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.volunteer import EventParticipation
from routes.utils import parse_date
from utils.salesforce_importer import ImportConfig, ImportHelpers, SalesforceImporter

# Create the organizations blueprint
organizations_bp = Blueprint("organizations", __name__)


def validate_organization_record(record: dict) -> tuple[bool, list[str]]:
    """
    Validate an organization record from Salesforce.

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
        errors.append("Missing organization name")

    # Validate Salesforce ID format (18 characters)
    if record.get("Id") and len(record["Id"]) != 18:
        errors.append("Invalid Salesforce ID format")

    # Validate name length
    if record.get("Name") and len(record["Name"]) > 255:
        errors.append("Organization name too long (max 255 characters)")

    return len(errors) == 0, errors


def process_organization_record(record: dict, session) -> tuple[bool, str]:
    """
    Process a single organization record from Salesforce.

    Args:
        record: Salesforce record dictionary
        session: Database session

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Use ImportHelpers to create or update the organization
        org, created = ImportHelpers.create_or_update_record(
            Organization,
            record["Id"],
            {
                "name": ImportHelpers.clean_string(record.get("Name", "")),
                "type": ImportHelpers.clean_string(record.get("Type")),
                "description": ImportHelpers.clean_string(record.get("Description")),
                "billing_street": ImportHelpers.clean_string(record.get("BillingStreet")),
                "billing_city": ImportHelpers.clean_string(record.get("BillingCity")),
                "billing_state": ImportHelpers.clean_string(record.get("BillingState")),
                "billing_postal_code": ImportHelpers.clean_string(record.get("BillingPostalCode")),
                "billing_country": ImportHelpers.clean_string(record.get("BillingCountry")),
            },
            session,
        )

        # Parse and set last activity date if available
        if record.get("LastActivityDate"):
            org.last_activity_date = parse_date(record["LastActivityDate"])

        return True, ""

    except Exception as e:
        return False, f"Error processing organization {record.get('Name', 'Unknown')}: {str(e)}"


def validate_affiliation_record(record: dict) -> tuple[bool, list[str]]:
    """
    Validate an affiliation record from Salesforce.

    Args:
        record: Salesforce record dictionary

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check required fields
    if not record.get("Id"):
        errors.append("Missing Salesforce ID")
    if not record.get("npe5__Organization__c"):
        errors.append("Missing organization Salesforce ID")
    if not record.get("npe5__Contact__c"):
        errors.append("Missing contact Salesforce ID")

    # Validate Salesforce ID format (18 characters)
    if record.get("Id") and len(record["Id"]) != 18:
        errors.append("Invalid Salesforce ID format")

    return len(errors) == 0, errors


def process_affiliation_record(record: dict, session) -> tuple[bool, str]:
    """
    Process a single affiliation record from Salesforce.

    Args:
        record: Salesforce record dictionary
        session: Database session

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get the organization by its Salesforce ID
        org = Organization.query.filter_by(salesforce_id=record.get("npe5__Organization__c")).first()

        # If organization not found, check if it's a school or district
        if not org:
            # First check if it's a school
            school = School.query.filter_by(id=record.get("npe5__Organization__c")).first()
            if school:
                # Create an organization record for the school
                org = Organization(name=school.name, type="School", salesforce_id=school.id)
                session.add(org)
                session.flush()  # Get the new org ID
            else:
                # If not a school, check if it's a district
                district = District.query.filter_by(salesforce_id=record.get("npe5__Organization__c")).first()
                if district:
                    # Create an organization record for the district
                    org = Organization(name=district.name, type="District", salesforce_id=district.salesforce_id)
                    session.add(org)
                    session.flush()  # Get the new org ID

        # Look up contact by Salesforce ID across all contact types
        contact = Contact.query.filter_by(salesforce_individual_id=record.get("npe5__Contact__c")).first()

        # Create or update the volunteer-organization relationship
        if org and contact:
            # Check for existing relationship
            vol_org = VolunteerOrganization.query.filter_by(volunteer_id=contact.id, organization_id=org.id).first()

            if not vol_org:
                # Create new relationship
                vol_org = VolunteerOrganization(volunteer_id=contact.id, organization_id=org.id)
                session.add(vol_org)

            # Update relationship details from Salesforce
            vol_org.salesforce_volunteer_id = record.get("npe5__Contact__c")
            vol_org.salesforce_org_id = record.get("npe5__Organization__c")
            vol_org.role = ImportHelpers.clean_string(record.get("npe5__Role__c"))
            vol_org.is_primary = record.get("npe5__Primary__c") == "true"
            vol_org.status = ImportHelpers.clean_string(record.get("npe5__Status__c"))

            # Parse and set date fields if available
            if record.get("npe5__StartDate__c"):
                vol_org.start_date = parse_date(record["npe5__StartDate__c"])
            if record.get("npe5__EndDate__c"):
                vol_org.end_date = parse_date(record["npe5__EndDate__c"])

            return True, ""
        else:
            # Track missing organization or contact
            error_msgs = []
            if not org:
                error_msgs.append(f"Organization/School/District with Salesforce ID {record.get('npe5__Organization__c')} not found")
            if not contact:
                error_msgs.append(f"Contact (Volunteer/Teacher) with Salesforce ID {record.get('npe5__Contact__c')} not found")
            return False, "; ".join(error_msgs)

    except Exception as e:
        return False, f"Error processing affiliation: {str(e)}"


@organizations_bp.route("/organizations")
@login_required
def organizations():
    """
    Display the main organizations listing page with filtering and pagination.

    Provides a comprehensive view of all organizations with advanced
    filtering, sorting, and pagination capabilities.

    Features:
        - Search organizations by name
        - Filter by organization type
        - Sortable columns (name, type, last activity date)
        - Pagination with configurable page size
        - Admin actions (edit/delete) - currently disabled in template

    Query Parameters:
        page: Page number for pagination
        per_page: Number of items per page (10, 25, 50, 100)
        search_name: Search term for organization name
        type: Filter by organization type
        sort: Column to sort by (name, type, last_activity_date)
        direction: Sort direction (asc, desc)

    Filtering Features:
        - Text search across organization names
        - Type-based dropdown filtering
        - Dynamic filter options based on available data
        - Filter state preservation across requests

    Sorting Features:
        - Multi-column sorting capability
        - Configurable sort direction
        - Default sort by name ascending

    Returns:
        Rendered template with organizations list and pagination info

    Template Variables:
        organizations: List of organization objects for current page
        pagination: Pagination object with navigation
        current_filters: Dictionary of active filters
        organization_types: List of available organization types
    """
    # Get pagination and sorting parameters from request
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    sort_by = request.args.get("sort", "name")  # Default sort by name
    sort_dir = request.args.get("direction", "asc")  # Default ascending

    # Create current_filters dictionary to maintain filter state
    current_filters = {
        "search_name": request.args.get("search_name", "").strip(),
        "type": request.args.get("type", ""),
        "per_page": per_page,
        "sort": sort_by,
        "direction": sort_dir,
    }

    # Build base query for organizations
    query = Organization.query

    # Apply search filter for organization name
    if current_filters.get("search_name"):
        search_term = f"%{current_filters['search_name']}%"
        query = query.filter(Organization.name.ilike(search_term))

    # Apply organization type filter
    if current_filters.get("type"):
        query = query.filter(Organization.type == current_filters["type"])

    # Apply sorting to the query
    if sort_by == "volunteer_count":
        from sqlalchemy import func

        from models.contact import Contact

        volunteer_count_subq = (
            db.session.query(VolunteerOrganization.organization_id, func.count(VolunteerOrganization.volunteer_id).label("volunteer_count"))
            .join(Contact, VolunteerOrganization.volunteer_id == Contact.id)
            .filter(Contact.type == "volunteer")
            .group_by(VolunteerOrganization.organization_id)
            .subquery()
        )

        # Join the subquery for sorting but don't add columns to preserve Organization objects
        query = query.outerjoin(volunteer_count_subq, Organization.id == volunteer_count_subq.c.organization_id)

        sort_column = func.coalesce(volunteer_count_subq.c.volunteer_count, 0)
    else:
        sort_column = getattr(Organization, sort_by, Organization.name)

    if sort_dir == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Get unique organization types for the filter dropdown
    # This provides the available options in the type filter
    organization_types = db.session.query(Organization.type).filter(Organization.type.isnot(None)).distinct().order_by(Organization.type).all()
    organization_types = [t[0] for t in organization_types if t[0]]

    # Apply pagination to the filtered query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Render the template with all necessary data
    return render_template(
        "organizations/organizations.html",
        organizations=pagination.items,
        pagination=pagination,
        current_filters=current_filters,
        organization_types=organization_types,
    )


@organizations_bp.route("/organizations/view/<int:id>")
@login_required
def view_organization(id):
    """
    Display detailed information about a specific organization.

    Shows comprehensive organization information including basic details,
    associated volunteers, recent activities, and relationship data.

    Features:
        - Organization basic information (name, type, description, address)
        - Timestamps (created, updated, last activity)
        - Associated volunteers list with roles and dates
        - Salesforce integration links
        - Recent activity tracking

    Args:
        id (int): Organization ID to view

    Returns:
        Rendered template with organization details and associated data

    Raises:
        404: Organization not found

    Template Variables:
        organization: Organization object with all details
        volunteer_organizations: List of volunteer-organization relationships
        recent_activities: List of recent volunteer activities
    """
    # Get the organization or return 404 if not found
    organization = Organization.query.get_or_404(id)

    # Get volunteer-organization relationships with volunteer data loaded
    # This ensures we have access to both the relationship metadata and volunteer details
    volunteer_organizations = VolunteerOrganization.query.filter_by(organization_id=id).join(VolunteerOrganization.volunteer).all()

    # Get recent events/activities for associated volunteers
    # This provides context about the organization's recent involvement
    recent_activities = []
    for vo in volunteer_organizations:
        if vo.volunteer:  # Only process if volunteer exists
            participations = EventParticipation.query.filter_by(volunteer_id=vo.volunteer.id).join(Event).order_by(Event.start_date.desc()).limit(5).all()
            recent_activities.extend(participations)

    # Sort activities by event date (most recent first)
    recent_activities.sort(key=lambda x: x.event.start_date, reverse=True)

    # Render the view template with organization and related data
    return render_template(
        "organizations/view.html",
        organization=organization,
        volunteer_organizations=volunteer_organizations,
        recent_activities=recent_activities[:10],  # Limit to 10 most recent
    )


@organizations_bp.route("/organizations/add", methods=["GET", "POST"])
@login_required
def add_organization():
    """
    Create a new organization in the system.

    Handles both GET (form display) and POST (form processing)
    for creating new organizations with validation and error handling.

    Features:
        - GET: Display the organization creation form
        - POST: Process form submission and create organization
        - Form validation and error handling
        - Flash messages for user feedback

    Form Fields:
        name (required): Organization name
        type: Organization type (dropdown)
        description: Organization description
        billing_street: Street address
        billing_city: City
        billing_state: State/Province
        billing_postal_code: Postal/ZIP code
        billing_country: Country

    Returns:
        GET: Rendered form template
        POST: Redirect to organizations list on success
    """
    if request.method == "POST":
        try:
            # Create new organization instance with form data
            organization = Organization(
                name=request.form["name"],
                type=request.form["type"],
                description=request.form["description"],
                billing_street=request.form["billing_street"],
                billing_city=request.form["billing_city"],
                billing_state=request.form["billing_state"],
                billing_postal_code=request.form["billing_postal_code"],
                billing_country=request.form["billing_country"],
            )

            # Add to database and commit
            db.session.add(organization)
            db.session.commit()

            # Show success message and redirect
            flash("Organization created successfully!", "success")
            return redirect(url_for("organizations.organizations"))

        except Exception as e:
            # Rollback on error and show error message
            db.session.rollback()
            flash(f"Error creating organization: {str(e)}", "error")
            return redirect(url_for("organizations.add_organization"))

    # GET request: Get unique organization types for the dropdown
    organization_types = db.session.query(Organization.type).filter(Organization.type.isnot(None)).distinct().order_by(Organization.type).all()
    organization_types = [t[0] for t in organization_types if t[0]]

    # Render the add organization form
    return render_template("organizations/add_organization.html", organization_types=organization_types)


@organizations_bp.route("/organizations/delete/<int:id>", methods=["DELETE"])
@login_required
def delete_organization(id):
    """
    Delete an organization and its associated volunteer relationships.

    Features:
    - Soft delete with cascade to volunteer relationships
    - JSON response for AJAX requests
    - Error handling with rollback

    Args:
        id (int): Organization ID to delete

    Returns:
        JSON response with success/error status
    """
    try:
        # Get the organization or return 404
        organization = Organization.query.get_or_404(id)

        # Delete associated volunteer organizations first
        # This prevents foreign key constraint violations
        VolunteerOrganization.query.filter_by(organization_id=id).delete()

        # Delete the organization itself
        db.session.delete(organization)
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        # Rollback on error and return error response
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@organizations_bp.route("/organizations/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_organization(id):
    """
    Edit an existing organization.

    Features:
    - GET: Display pre-populated edit form
    - POST: Process form submission and update organization
    - Form validation and error handling
    - Flash messages for user feedback

    Args:
        id (int): Organization ID to edit

    Returns:
        GET: Rendered edit form template
        POST: Redirect to organizations list on success
    """
    # Get the organization or return 404
    organization = Organization.query.get_or_404(id)

    if request.method == "POST":
        try:
            # Update organization fields with form data
            organization.name = request.form["name"]
            organization.type = request.form["type"]
            organization.description = request.form["description"]
            organization.billing_street = request.form["billing_street"]
            organization.billing_city = request.form["billing_city"]
            organization.billing_state = request.form["billing_state"]
            organization.billing_postal_code = request.form["billing_postal_code"]
            organization.billing_country = request.form["billing_country"]

            # Commit changes to database
            db.session.commit()
            flash("Organization updated successfully!", "success")
            return redirect(url_for("organizations.organizations"))

        except Exception as e:
            # Rollback on error and show error message
            db.session.rollback()
            flash(f"Error updating organization: {str(e)}", "error")
            return redirect(url_for("organizations.edit_organization", id=id))

    # GET request: Get unique organization types for the dropdown
    organization_types = db.session.query(Organization.type).filter(Organization.type.isnot(None)).distinct().order_by(Organization.type).all()
    organization_types = [t[0] for t in organization_types if t[0]]

    # Render the edit form with current organization data
    return render_template("organizations/edit_organization.html", organization=organization, organization_types=organization_types)


@organizations_bp.route("/organizations/purge", methods=["POST"])
@login_required
def purge_organizations():
    """
    Purge all organizations and their volunteer affiliations from the database.

    WARNING: This is a destructive operation that removes all organization data.
    Should only be used for data cleanup or system reset.

    Features:
    - Deletes all volunteer-organization relationships first
    - Deletes all organizations
    - JSON response with success/error status
    - Comprehensive error handling

    Returns:
        JSON response with operation status and message
    """
    try:
        # First delete all volunteer organization affiliations
        # This prevents foreign key constraint violations
        VolunteerOrganization.query.delete()

        # Then delete all organizations
        Organization.query.delete()

        # Commit the changes
        db.session.commit()

        return jsonify({"success": True, "message": "All organizations and their affiliations have been purged"})
    except Exception as e:
        # Rollback on error and return error response
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@organizations_bp.route("/organizations/import-from-salesforce", methods=["POST"])
@login_required
def import_organizations_from_salesforce():
    """
    Import organizations from Salesforce into the local database using the optimized framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures

    Salesforce Query:
    - Filters out household, school district, and school accounts
    - Orders by organization name
    - Includes address fields and activity dates

    Returns:
        JSON response with import statistics and error details
    """
    try:
        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=500,  # Process 500 records at a time
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=100,  # Commit every 100 records
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query
        org_query = """
        SELECT Id, Name, Type, Description, ParentId,
               BillingStreet, BillingCity, BillingState,
               BillingPostalCode, BillingCountry, LastActivityDate
        FROM Account
        WHERE Type NOT IN ('Household', 'School District', 'School')
        ORDER BY Name ASC
        """

        # Execute the import using the optimized framework
        result = importer.import_data(query=org_query, process_func=process_organization_record, validation_func=validate_organization_record)

        # Prepare response based on import result
        if result.success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {result.success_count} organizations with {result.error_count} errors",
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
        # Handle Salesforce authentication errors
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        # Handle other errors
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@organizations_bp.route("/organizations/import-affiliations-from-salesforce", methods=["POST"])
@login_required
def import_affiliations_from_salesforce():
    """
    Import volunteer-organization affiliations from Salesforce using the optimized framework.

    Features:
    - Uses the standardized SalesforceImporter framework
    - Batch processing for memory efficiency
    - Comprehensive error handling and validation
    - Progress tracking and detailed reporting
    - Retry logic for transient failures
    - Handles schools and districts as organizations

    Salesforce Query:
    - Queries npe5__Affiliation__c object
    - Includes role, status, and date fields
    - Links contacts to organizations

    Returns:
        JSON response with import statistics and error details
    """
    try:
        # Configure the import with optimized settings
        config = ImportConfig(
            batch_size=300,  # Process 300 records at a time (smaller due to complexity)
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=50,  # Commit every 50 records
        )

        # Initialize the Salesforce importer
        importer = SalesforceImporter(config)

        # Define the Salesforce query
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c,
               npe5__Role__c, npe5__Primary__c, npe5__Status__c,
               npe5__StartDate__c, npe5__EndDate__c
        FROM npe5__Affiliation__c
        """

        # Execute the import using the optimized framework
        result = importer.import_data(query=affiliation_query, process_func=process_affiliation_record, validation_func=validate_affiliation_record)

        # Prepare response based on import result
        if result.success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully processed {result.success_count} affiliations with {result.error_count} errors",
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
        # Handle Salesforce authentication errors
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        # Handle other errors
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
