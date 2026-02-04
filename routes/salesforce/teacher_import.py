"""
Salesforce Teacher Import Routes
================================

This module handles the Salesforce data import functionality for teachers.
Extracted from routes/teachers/routes.py to consolidate all Salesforce
import routes in one location.

Routes:
- /teachers/import-from-salesforce: Import teacher data from Salesforce
"""

from datetime import datetime
from datetime import timezone as tz

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.teacher import Teacher
from routes.decorators import global_users_only
from services.salesforce import get_salesforce_client, safe_query_all

# Create Blueprint for Salesforce teacher import routes
sf_teacher_import_bp = Blueprint("sf_teacher_import", __name__)


@sf_teacher_import_bp.route("/teachers/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
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
        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.salesforce import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("teachers")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching teachers modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Starting teacher import from Salesforce (FULL SYNC)...")

        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce using centralized client with retry logic
        sf = get_salesforce_client()

        # Query for teachers with specific fields and LastModifiedDate
        teacher_query = """
        SELECT Id, AccountId, FirstName, LastName, Email,
               npsp__Primary_Affiliation__c, Department, Gender__c,
               Phone, Last_Email_Message__c, Last_Mailchimp_Email_Date__c,
               LastModifiedDate
        FROM Contact
        WHERE Contact_Type__c = 'Teacher'
        """

        # Add delta filter if using incremental sync
        if is_delta and watermark:
            teacher_query += delta_helper.build_date_filter(watermark)

        # Execute query with automatic retry
        result = safe_query_all(sf, teacher_query)
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
                sync_type="teachers",
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

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} teachers with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "is_delta_sync": is_delta,
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
