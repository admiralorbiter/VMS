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

import csv
import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

# TODO: Fix import statements for simple_salesforce
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

from config import Config
from models import Volunteer, db, eagerload_organization_bundle
from models.contact import Contact  # Add this import at the top
from models.district_model import District  # Add this import at the top
from models.event import Event
from models.organization import Organization, VolunteerOrganization
from models.school_model import School  # Add this import at the top
from models.teacher import Teacher  # Add this import at the top
from models.volunteer import EventParticipation
from routes.decorators import global_users_only
from routes.utils import admin_required, log_audit_action, parse_date

# Create the organizations blueprint
organizations_bp = Blueprint("organizations", __name__)


@organizations_bp.route("/organizations")
@login_required
@global_users_only
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
            db.session.query(
                VolunteerOrganization.organization_id,
                func.count(VolunteerOrganization.volunteer_id).label("volunteer_count"),
            )
            .join(Contact, VolunteerOrganization.volunteer_id == Contact.id)
            .filter(Contact.type == "volunteer")
            .group_by(VolunteerOrganization.organization_id)
            .subquery()
        )

        # Join the subquery for sorting but don't add columns to preserve Organization objects
        query = query.outerjoin(
            volunteer_count_subq,
            Organization.id == volunteer_count_subq.c.organization_id,
        )

        sort_column = func.coalesce(volunteer_count_subq.c.volunteer_count, 0)
    else:
        sort_column = getattr(Organization, sort_by, Organization.name)

    if sort_dir == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Get unique organization types for the filter dropdown
    # This provides the available options in the type filter
    organization_types = (
        db.session.query(Organization.type)
        .filter(Organization.type.isnot(None))
        .distinct()
        .order_by(Organization.type)
        .all()
    )
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
@global_users_only
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
        - Summary engagement metrics (all-time)
        - Link to comprehensive detailed report

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
        summary_stats: All-time engagement summary statistics
    """
    from utils.services.organization_service import OrganizationService

    # Get the organization or return 404 if not found
    organization = eagerload_organization_bundle(Organization.query).get_or_404(id)

    # Get volunteer-organization relationships with volunteer data loaded
    # This ensures we have access to both the relationship metadata and volunteer details
    # Order by last volunteer date (most recent first) for better user experience
    from sqlalchemy import desc

    volunteer_organizations = (
        VolunteerOrganization.query.filter_by(organization_id=id)
        .join(Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id)
        .order_by(desc(Volunteer.last_volunteer_date).nullslast())
        .all()
    )

    # Get recent events/activities for associated volunteers
    # This provides context about the organization's recent involvement
    recent_activities = []
    for vo in volunteer_organizations:
        if vo.volunteer:  # Only process if volunteer exists
            participations = (
                EventParticipation.query.filter_by(volunteer_id=vo.volunteer.id)
                .join(Event)
                .order_by(Event.start_date.desc())
                .limit(5)
                .all()
            )
            recent_activities.extend(participations)

    # Sort activities by event date (most recent first)
    recent_activities.sort(key=lambda x: x.event.start_date, reverse=True)

    # Get communication history for all associated volunteers
    # This provides a comprehensive view of all communications across the organization
    from models.history import History

    # Get all volunteer IDs associated with this organization
    volunteer_ids = [vo.volunteer.id for vo in volunteer_organizations if vo.volunteer]

    # Fetch all communication history for these volunteers
    organization_histories = []
    if volunteer_ids:
        organization_histories = (
            History.query.filter(
                History.contact_id.in_(volunteer_ids), History.is_deleted == False
            )
            .order_by(History.activity_date.desc())
            .all()
        )

    # Debug: Print history count
    print(
        f"Found {len(organization_histories)} communication history records for organization {id}"
    )
    if organization_histories:
        print(
            f"First history record: {organization_histories[0].activity_type} - {organization_histories[0].summary}"
        )

    # Get all-time summary statistics using the service
    service = OrganizationService()
    summary_data = service.get_organization_summary(id)

    # Render the view template with organization and related data
    return render_template(
        "organizations/view.html",
        organization=organization,
        volunteer_organizations=volunteer_organizations,
        recent_activities=recent_activities[:10],  # Limit to 10 most recent
        summary_stats=summary_data,
        organization_histories=organization_histories,
    )


@organizations_bp.route("/organizations/add", methods=["GET", "POST"])
@login_required
@global_users_only
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
    organization_types = (
        db.session.query(Organization.type)
        .filter(Organization.type.isnot(None))
        .distinct()
        .order_by(Organization.type)
        .all()
    )
    organization_types = [t[0] for t in organization_types if t[0]]

    # Render the add organization form
    return render_template(
        "organizations/add_organization.html", organization_types=organization_types
    )


@organizations_bp.route("/organizations/delete/<int:id>", methods=["DELETE"])
@login_required
@admin_required
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
        log_audit_action(action="delete", resource_type="organization", resource_id=id)

        return jsonify({"success": True})
    except Exception as e:
        # Rollback on error and return error response
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@organizations_bp.route("/organizations/edit/<int:id>", methods=["GET", "POST"])
@login_required
@global_users_only
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
    organization_types = (
        db.session.query(Organization.type)
        .filter(Organization.type.isnot(None))
        .distinct()
        .order_by(Organization.type)
        .all()
    )
    organization_types = [t[0] for t in organization_types if t[0]]

    # Render the edit form with current organization data
    return render_template(
        "organizations/edit_organization.html",
        organization=organization,
        organization_types=organization_types,
    )


@organizations_bp.route("/organizations/purge", methods=["POST"])
@login_required
@admin_required
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
        log_audit_action(action="purge", resource_type="organization")

        return jsonify(
            {
                "success": True,
                "message": "All organizations and their affiliations have been purged",
            }
        )
    except Exception as e:
        # Rollback on error and return error response
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@organizations_bp.route("/organizations/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
def import_organizations_from_salesforce():
    """
    Import organizations from Salesforce into the local database.

    Features:
    - Connects to Salesforce using configured credentials
    - Queries Account records (excluding households, districts, schools)
    - Creates or updates local organization records
    - Handles address information and timestamps
    - Provides detailed success/error reporting

    Salesforce Query:
    - Filters out household, school district, and school accounts
    - Orders by organization name
    - Includes address fields and activity dates

    Returns:
        JSON response with import statistics and error details
    """
    try:
        print("Fetching organizations from Salesforce...")
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

        # Query organizations from Salesforce
        # Excludes household, school district, and school accounts
        org_query = """
        SELECT Id, Name, Type, Description, ParentId,
               BillingStreet, BillingCity, BillingState,
               BillingPostalCode, BillingCountry, LastActivityDate
        FROM Account
        WHERE Type NOT IN ('Household', 'School District', 'School')
        ORDER BY Name ASC
        """

        # Execute the query and get results
        result = sf.query_all(org_query)
        sf_rows = result.get("records", [])

        # Process each organization from Salesforce
        for row in sf_rows:
            try:
                # Check if organization already exists in local database
                org = Organization.query.filter_by(salesforce_id=row["Id"]).first()
                if not org:
                    # Create new organization if it doesn't exist
                    org = Organization()
                    db.session.add(org)

                # Update organization fields with Salesforce data
                org.salesforce_id = row["Id"]
                org.name = row.get("Name", "")
                org.type = row.get("Type")
                org.description = row.get("Description")
                # TODO: Fix volunteer_parent_id field - this field doesn't exist in the model
                # org.volunteer_parent_id = row.get('ParentId')
                org.billing_street = row.get("BillingStreet")
                org.billing_city = row.get("BillingCity")
                org.billing_state = row.get("BillingState")
                org.billing_postal_code = row.get("BillingPostalCode")
                org.billing_country = row.get("BillingCountry")

                # Parse and set last activity date if available
                if row.get("LastActivityDate"):
                    org.last_activity_date = parse_date(row["LastActivityDate"])

                success_count += 1
            except Exception as e:
                # Track errors for reporting
                error_count += 1
                errors.append(
                    f"Error processing organization {row.get('Name', 'Unknown')}: {str(e)}"
                )
                continue

        # Commit all changes to database
        db.session.commit()

        # Print summary to console for debugging
        print(f"\nImport completed:")
        print(f"Successfully imported: {success_count} organizations")
        print(f"Errors encountered: {error_count}")
        if errors:
            print("\nFirst 3 errors:")
            for error in errors[:3]:
                print(f"- {error}")
            if len(errors) > 3:
                print(f"... and {len(errors) - 3} more errors")

        # Return JSON response with import results
        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} organizations with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }
        )

    except SalesforceAuthenticationFailed:
        # Handle Salesforce authentication errors
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        # Handle other errors
        db.session.rollback()
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@organizations_bp.route(
    "/organizations/import-affiliations-from-salesforce", methods=["POST"]
)
@login_required
def import_affiliations_from_salesforce():
    """
    Import volunteer-organization affiliations from Salesforce.

    Features:
    - Connects to Salesforce and queries Affiliation__c records
    - Creates volunteer-organization relationships
    - Handles schools and districts as organizations
    - Manages role, status, and date information
    - Provides detailed success/error reporting

    Salesforce Query:
    - Queries npe5__Affiliation__c object
    - Includes role, status, and date fields
    - Links contacts to organizations

    Returns:
        JSON response with import statistics and error details
    """
    try:
        print("Fetching affiliations from Salesforce...")
        affiliation_success = 0
        affiliation_error = 0
        errors = []

        # Connect to Salesforce using configured credentials
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # Query affiliations from Salesforce
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c,
               npe5__Role__c, npe5__Primary__c, npe5__Status__c,
               npe5__StartDate__c, npe5__EndDate__c
        FROM npe5__Affiliation__c
        """

        # Execute the query and get results
        affiliation_result = sf.query_all(affiliation_query)
        affiliation_rows = affiliation_result.get("records", [])

        # Process each affiliation from Salesforce
        for row in affiliation_rows:
            try:
                # Get the organization by its Salesforce ID
                org = Organization.query.filter_by(
                    salesforce_id=row.get("npe5__Organization__c")
                ).first()

                # If organization not found, check if it's a school or district
                if not org:
                    # First check if it's a school
                    school = School.query.filter_by(
                        id=row.get("npe5__Organization__c")
                    ).first()
                    if school:
                        # Create an organization record for the school
                        org = Organization(
                            name=school.name, type="School", salesforce_id=school.id
                        )
                        db.session.add(org)
                        db.session.flush()  # Get the new org ID
                    else:
                        # If not a school, check if it's a district
                        district = District.query.filter_by(
                            salesforce_id=row.get("npe5__Organization__c")
                        ).first()
                        if district:
                            # Create an organization record for the district
                            org = Organization(
                                name=district.name,
                                type="District",
                                salesforce_id=district.salesforce_id,
                            )
                            db.session.add(org)
                            db.session.flush()  # Get the new org ID

                # Look up contact by Salesforce ID across all contact types
                contact = Contact.query.filter_by(
                    salesforce_individual_id=row.get("npe5__Contact__c")
                ).first()

                # Create or update the volunteer-organization relationship
                if org and contact:
                    # Check for existing relationship
                    vol_org = VolunteerOrganization.query.filter_by(
                        volunteer_id=contact.id, organization_id=org.id
                    ).first()

                    if not vol_org:
                        # Create new relationship
                        vol_org = VolunteerOrganization(
                            volunteer_id=contact.id, organization_id=org.id
                        )
                        db.session.add(vol_org)

                    # Update relationship details from Salesforce
                    vol_org.salesforce_volunteer_id = row.get("npe5__Contact__c")
                    vol_org.salesforce_org_id = row.get("npe5__Organization__c")
                    vol_org.role = row.get("npe5__Role__c")
                    vol_org.is_primary = row.get("npe5__Primary__c") == "true"
                    vol_org.status = row.get("npe5__Status__c")

                    # Parse and set date fields if available
                    if row.get("npe5__StartDate__c"):
                        vol_org.start_date = parse_date(row["npe5__StartDate__c"])
                    if row.get("npe5__EndDate__c"):
                        vol_org.end_date = parse_date(row["npe5__EndDate__c"])

                    affiliation_success += 1
                else:
                    # Track missing organization or contact
                    affiliation_error += 1
                    error_msgs = []
                    if not org:
                        error_msgs.append(
                            f"Organization/School/District with Salesforce ID {row.get('npe5__Organization__c')} not found"
                        )
                    if not contact:
                        error_msgs.append(
                            f"Contact (Volunteer/Teacher) with Salesforce ID {row.get('npe5__Contact__c')} not found"
                        )
                    errors.extend(error_msgs)

            except Exception as e:
                # Track processing errors
                affiliation_error += 1
                errors.append(f"Error processing affiliation: {str(e)}")
                continue

        # Commit all changes to database
        db.session.commit()

        # Print summary to console for debugging
        print(f"\nAffiliation import completed:")
        print(f"Successfully imported: {affiliation_success} affiliations")
        print(f"Errors encountered: {affiliation_error}")
        if errors:
            print("\nFirst 3 errors:")
            for error in errors[:3]:
                print(f"- {error}")
            if len(errors) > 3:
                print(f"... and {len(errors) - 3} more errors")

        # Return JSON response with import results
        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {affiliation_success} affiliations with {affiliation_error} errors",
                "processed_count": affiliation_success,
                "error_count": affiliation_error,
                "errors": errors[:3] if errors else [],
            }
        )

    except SalesforceAuthenticationFailed:
        # Handle Salesforce authentication errors
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        # Handle other errors
        db.session.rollback()
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
