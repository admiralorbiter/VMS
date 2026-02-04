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

        # Process each teacher record with savepoint recovery
        skipped_count = 0
        for i, row in enumerate(teacher_rows):
            # Use savepoint to isolate each record - failures won't roll back the batch
            try:
                with db.session.begin_nested():
                    # Use the Teacher model's import method
                    teacher, is_new, error = Teacher.import_from_salesforce(
                        row, db.session
                    )

                    if error:
                        # Raise to trigger savepoint rollback
                        raise ValueError(error)

                    # Flush to get ID (needed for contact info) without full commit
                    db.session.flush()

                    # Handle contact info using the teacher's method
                    contact_success, contact_error = teacher.update_contact_info(
                        row, db.session
                    )
                    if not contact_success:
                        raise ValueError(contact_error)

                    success_count += 1

            except Exception as e:
                # Savepoint automatically rolled back - other records in batch preserved
                error_count += 1
                skipped_count += 1
                error_msg = f"SKIPPED: {row.get('FirstName', '')} {row.get('LastName', '')} (SF ID: {row.get('Id', 'unknown')}) - {str(e)}"
                errors.append(error_msg)
                print(f"  ⚠ {error_msg}")
                continue

            # Batch commit every 50 records for performance and resumability
            if (i + 1) % 50 == 0:
                try:
                    db.session.commit()
                    print(
                        f"  → Committed teachers batch {(i+1) // 50} ({success_count} successful, {skipped_count} skipped)"
                    )
                except Exception as batch_e:
                    db.session.rollback()
                    print(f"  → Batch commit failed: {batch_e}")

        # Final commit for remaining records
        db.session.commit()

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
                records_skipped=skipped_count,
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
                "message": f"Successfully processed {success_count} teachers ({skipped_count} skipped, {error_count} errors)",
                "processed_count": success_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "is_delta_sync": is_delta,
                "errors": errors[:100],  # Limit error list size in response
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
