"""
Salesforce Organization Import Routes
=====================================

This module handles the Salesforce data import functionality for organizations
and volunteer-organization affiliations. Extracted from routes/organizations/routes.py
to consolidate all Salesforce import routes in one location.

Routes:
- /organizations/import-from-salesforce: Import organization data from Salesforce
- /organizations/import-affiliations-from-salesforce: Import volunteer-org affiliations
"""

from datetime import datetime
from datetime import timezone as tz

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce import SalesforceAuthenticationFailed

from models import db
from models.contact import Contact
from models.district_model import District
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from routes.decorators import global_users_only
from routes.utils import parse_date
from services.salesforce_client import get_salesforce_client, safe_query_all

# Create Blueprint for Salesforce organization import routes
organization_import_bp = Blueprint("organization_import", __name__)


@organization_import_bp.route("/organizations/import-from-salesforce", methods=["POST"])
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
        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("organizations")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching organizations modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Fetching organizations from Salesforce (FULL SYNC)...")

        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

        # Query organizations from Salesforce with LastModifiedDate
        # Excludes household, school district, and school accounts
        org_query = """
        SELECT Id, Name, Type, Description, ParentId,
               BillingStreet, BillingCity, BillingState,
               BillingPostalCode, BillingCountry, LastActivityDate, LastModifiedDate
        FROM Account
        WHERE Type NOT IN ('Household', 'School District', 'School')
        """

        # Add delta filter if using incremental sync
        if is_delta and watermark:
            org_query += delta_helper.build_date_filter(watermark)

        org_query += " ORDER BY Name ASC"

        # Execute the query and get results
        result = safe_query_all(sf, org_query)
        sf_rows = result.get("records", [])

        # Process each organization from Salesforce
        for i, row in enumerate(sf_rows):
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
                org.billing_street = row.get("BillingStreet")
                org.billing_city = row.get("BillingCity")
                org.billing_state = row.get("BillingState")
                org.billing_postal_code = row.get("BillingPostalCode")
                org.billing_country = row.get("BillingCountry")

                # Parse and set last activity date if available
                if row.get("LastActivityDate"):
                    org.last_activity_date = parse_date(row["LastActivityDate"])

                success_count += 1

                # Batch commit every 50 records for resumability
                if (i + 1) % 50 == 0:
                    try:
                        db.session.commit()
                        print(f"  → Committed orgs batch {(i+1) // 50}")
                    except Exception as batch_e:
                        db.session.rollback()
                        print(f"  → Orgs batch commit failed: {batch_e}")

            except Exception as e:
                # Track errors for reporting
                error_count += 1
                errors.append(
                    f"Error processing organization {row.get('Name', 'Unknown')}: {str(e)}"
                )
                continue

        # Final commit for any remaining changes
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

        # Record sync log for delta sync tracking
        try:
            from models.sync_log import SyncLog, SyncStatus

            sync_status = SyncStatus.SUCCESS.value
            if error_count > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if success_count > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = SyncLog(
                sync_type="organizations",
                started_at=started_at,
                completed_at=datetime.now(tz.utc),
                status=sync_status,
                records_processed=success_count,
                records_failed=error_count,
                is_delta_sync=is_delta,
                last_sync_watermark=(
                    datetime.now(tz.utc)
                    if sync_status
                    in (SyncStatus.SUCCESS.value, SyncStatus.PARTIAL.value)
                    else None
                ),
            )
            db.session.add(sync_log)
            db.session.commit()
        except Exception as log_e:
            print(f"Warning: Failed to record sync log: {log_e}")

        # Return JSON response with import results
        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} organizations with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "is_delta_sync": is_delta,
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


@organization_import_bp.route(
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
        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("affiliations")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching affiliations modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Fetching affiliations from Salesforce (FULL SYNC)...")

        affiliation_success = 0
        affiliation_error = 0
        errors = []

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

        # Query affiliations from Salesforce with LastModifiedDate for delta sync
        # Note: WHERE Id != null is required so delta filter can append AND clause
        affiliation_query = """
        SELECT Id, Name, npe5__Organization__c, npe5__Contact__c,
               npe5__Role__c, npe5__Primary__c, npe5__Status__c,
               npe5__StartDate__c, npe5__EndDate__c, LastModifiedDate
        FROM npe5__Affiliation__c
        WHERE Id != null
        """

        # Add delta filter if using incremental sync
        if is_delta and watermark:
            affiliation_query += delta_helper.build_date_filter(watermark)

        # Execute the query and get results
        affiliation_result = safe_query_all(sf, affiliation_query)
        affiliation_rows = affiliation_result.get("records", [])

        # Process each affiliation from Salesforce
        for i, row in enumerate(affiliation_rows):
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

                # Batch commit every 50 records for resumability
                if (i + 1) % 50 == 0:
                    try:
                        db.session.commit()
                        print(f"  → Committed affiliations batch {(i+1) // 50}")
                    except Exception as batch_e:
                        db.session.rollback()
                        print(f"  → Affiliations batch commit failed: {batch_e}")

            except Exception as e:
                # Track processing errors
                affiliation_error += 1
                errors.append(f"Error processing affiliation: {str(e)}")
                continue

        # Final commit for remaining changes
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

        # Record sync log for dashboard tracking
        try:
            from models.sync_log import SyncLog, SyncStatus

            sync_status = SyncStatus.SUCCESS.value
            if affiliation_error > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if affiliation_success > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = SyncLog(
                sync_type="affiliations",
                started_at=started_at,
                completed_at=datetime.now(tz.utc),
                status=sync_status,
                records_processed=affiliation_success,
                records_failed=affiliation_error,
                is_delta_sync=is_delta,
                last_sync_watermark=(
                    datetime.now(tz.utc)
                    if sync_status
                    in (SyncStatus.SUCCESS.value, SyncStatus.PARTIAL.value)
                    else None
                ),
            )
            db.session.add(sync_log)
            db.session.commit()
        except Exception as log_e:
            print(f"Warning: Failed to record sync log: {log_e}")

        # Return JSON response with import results
        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {affiliation_success} affiliations with {affiliation_error} errors",
                "processed_count": affiliation_success,
                "error_count": affiliation_error,
                "is_delta_sync": is_delta,
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
