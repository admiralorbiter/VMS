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
from services.salesforce import get_salesforce_client, safe_query_all
from services.salesforce.errors import classify_exception, create_import_error

# SQLite has a limit on the number of variables in a query (typically 999)
# We chunk large IN queries to avoid this limit
QUERY_CHUNK_SIZE = 500


def chunked_in_query(model, field, id_set, key_func=None):
    """
    Execute IN queries in chunks to avoid SQLite's variable limit.

    Args:
        model: SQLAlchemy model class to query
        field: Model field to filter on (e.g., Model.salesforce_id)
        id_set: Set of IDs to query for
        key_func: Optional function to extract key from result (defaults to field value)

    Returns:
        Dictionary mapping key to model instance
    """
    if not id_set:
        return {}

    result = {}
    id_list = list(id_set)

    for i in range(0, len(id_list), QUERY_CHUNK_SIZE):
        chunk = id_list[i : i + QUERY_CHUNK_SIZE]
        rows = model.query.filter(field.in_(chunk)).all()
        for row in rows:
            if key_func:
                key = key_func(row)
            else:
                # Default: use the field value we filtered on
                key = getattr(row, field.key)
            result[key] = row

    return result


# Create Blueprint for Salesforce organization import routes
sf_organization_import_bp = Blueprint("sf_organization_import", __name__)


@sf_organization_import_bp.route(
    "/organizations/import-from-salesforce", methods=["POST"]
)
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
        from services.salesforce import DeltaSyncHelper

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

        # Process each organization from Salesforce with savepoint recovery
        skipped_count = 0
        for i, row in enumerate(sf_rows):
            # Use savepoint to isolate each record - failures won't roll back the batch
            try:
                with db.session.begin_nested():
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

            except Exception as e:
                # Savepoint automatically rolled back - other records in batch preserved
                error_count += 1
                skipped_count += 1
                import_error = create_import_error(
                    code=classify_exception(e),
                    row=row,
                    message=str(e),
                    name_fields=("Name",),
                )
                errors.append(import_error.to_dict())
                print(f"  ⚠ {import_error}")
                continue

            # Batch commit every 50 records for resumability
            if (i + 1) % 50 == 0:
                try:
                    db.session.commit()
                    print(
                        f"  → Committed orgs batch {(i+1) // 50} ({success_count} successful, {skipped_count} skipped)"
                    )
                except Exception as batch_e:
                    db.session.rollback()
                    print(f"  → Orgs batch commit failed: {batch_e}")

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


@sf_organization_import_bp.route(
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
    - Uses pre-loaded lookups for O(1) entity resolution
    - Bulk commits for improved throughput

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
        from services.salesforce import DeltaSyncHelper

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
        MAX_ERRORS = 100  # Cap error list to prevent memory bloat

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
        total_count = len(affiliation_rows)
        print(f"  Fetched {total_count} affiliation records from Salesforce")

        # === PRE-LOAD PHASE: Build lookup dictionaries for O(1) access ===
        # Extract unique Salesforce IDs from the incoming data
        org_sf_ids = {
            row.get("npe5__Organization__c")
            for row in affiliation_rows
            if row.get("npe5__Organization__c")
        }
        contact_sf_ids = {
            row.get("npe5__Contact__c")
            for row in affiliation_rows
            if row.get("npe5__Contact__c")
        }

        print(
            f"  Pre-loading {len(org_sf_ids)} orgs, {len(contact_sf_ids)} contacts..."
        )

        # Pre-load organizations by salesforce_id (chunked to avoid SQLite variable limit)
        org_lookup = chunked_in_query(
            Organization, Organization.salesforce_id, org_sf_ids
        )

        # Pre-load schools by id (matching current query pattern)
        school_lookup = chunked_in_query(School, School.id, org_sf_ids)

        # Pre-load districts by salesforce_id
        district_lookup = chunked_in_query(District, District.salesforce_id, org_sf_ids)

        # Pre-load contacts by salesforce_individual_id
        contact_lookup = chunked_in_query(
            Contact, Contact.salesforce_individual_id, contact_sf_ids
        )

        # Pre-load existing volunteer-organization relationships (chunked)
        # Query by Salesforce IDs to find existing relationships
        vol_org_lookup = {}
        org_id_list = list(org_sf_ids)
        for i in range(0, len(org_id_list), QUERY_CHUNK_SIZE):
            chunk = org_id_list[i : i + QUERY_CHUNK_SIZE]
            chunk_results = VolunteerOrganization.query.filter(
                VolunteerOrganization.salesforce_org_id.in_(chunk)
            ).all()
            for vo in chunk_results:
                vol_org_lookup[(vo.volunteer_id, vo.organization_id)] = vo

        print(
            f"  Pre-loaded: {len(org_lookup)} orgs, {len(school_lookup)} schools, "
            f"{len(district_lookup)} districts, {len(contact_lookup)} contacts, "
            f"{len(vol_org_lookup)} existing relationships"
        )

        # Track newly created organizations to add to lookup
        new_orgs_pending = []

        # === PROCESSING PHASE: Use lookups instead of queries ===
        for i, row in enumerate(affiliation_rows):
            try:
                sf_org_id = row.get("npe5__Organization__c")
                sf_contact_id = row.get("npe5__Contact__c")

                # Get the organization using pre-loaded lookup (O(1))
                org = org_lookup.get(sf_org_id)

                # If organization not found, check if it's a school or district
                if not org:
                    # First check if it's a school
                    school = school_lookup.get(sf_org_id)
                    if school:
                        # Create an organization record for the school
                        org = Organization(
                            name=school.name, type="School", salesforce_id=school.id
                        )
                        db.session.add(org)
                        db.session.flush()  # Get the new org ID
                        # Add to lookup for future iterations
                        org_lookup[sf_org_id] = org
                    else:
                        # If not a school, check if it's a district
                        district = district_lookup.get(sf_org_id)
                        if district:
                            # Create an organization record for the district
                            org = Organization(
                                name=district.name,
                                type="District",
                                salesforce_id=district.salesforce_id,
                            )
                            db.session.add(org)
                            db.session.flush()  # Get the new org ID
                            # Add to lookup for future iterations
                            org_lookup[sf_org_id] = org

                # Look up contact using pre-loaded lookup (O(1))
                contact = contact_lookup.get(sf_contact_id)

                # Create or update the volunteer-organization relationship
                if org and contact:
                    # Check for existing relationship using pre-loaded lookup (O(1))
                    vol_org = vol_org_lookup.get((contact.id, org.id))

                    if not vol_org:
                        # Create new relationship
                        vol_org = VolunteerOrganization(
                            volunteer_id=contact.id, organization_id=org.id
                        )
                        db.session.add(vol_org)
                        # Add to lookup for future iterations
                        vol_org_lookup[(contact.id, org.id)] = vol_org

                    # Update relationship details from Salesforce
                    vol_org.salesforce_volunteer_id = sf_contact_id
                    vol_org.salesforce_org_id = sf_org_id
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
                    # Track missing organization or contact (with error cap)
                    affiliation_error += 1
                    if len(errors) < MAX_ERRORS:
                        error_msgs = []
                        if not org:
                            error_msgs.append(
                                f"Organization/School/District with Salesforce ID {sf_org_id} not found"
                            )
                        if not contact:
                            error_msgs.append(
                                f"Contact (Volunteer/Teacher) with Salesforce ID {sf_contact_id} not found"
                            )
                        errors.extend(error_msgs[: MAX_ERRORS - len(errors)])

                # Batch commit every 50 records for resumability
                if (i + 1) % 50 == 0:
                    try:
                        db.session.commit()
                        # Progress logging for large imports
                        if total_count >= 500:
                            print(
                                f"  → Batch {(i+1) // 50}: {i+1}/{total_count} ({(i+1)*100//total_count}%)"
                            )
                    except Exception as batch_e:
                        db.session.rollback()
                        print(f"  → Affiliations batch commit failed: {batch_e}")

            except Exception as e:
                # Track processing errors
                affiliation_error += 1
                if len(errors) < MAX_ERRORS:
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
