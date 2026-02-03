"""
Salesforce Student Import Routes
================================

This module handles the Salesforce data import functionality for students.
Extracted from routes/students/routes.py to consolidate all Salesforce
import routes in one location.

Routes:
- /students/import-from-salesforce: Import student data from Salesforce (chunked)
"""

from datetime import datetime
from datetime import timezone as tz

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce.api import Salesforce

from config import Config
from models import db
from models.student import Student
from routes.decorators import global_users_only

# Create Blueprint for Salesforce student import routes
sf_student_import_bp = Blueprint("sf_student_import", __name__)


@sf_student_import_bp.route("/students/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
def import_students_from_salesforce():
    """
    Import student data from Salesforce with chunked processing.

    This function handles large datasets by processing them in chunks
    to avoid memory issues and stay within Salesforce API limits.

    Args:
        chunk_size: Number of records to process per chunk (default: 2000)
        last_id: ID of last processed record for pagination

    Returns:
        JSON response with chunk processing results
    """
    try:
        started_at = datetime.now(tz.utc)

        # Delta sync support - check if incremental sync requested
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("students")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        chunk_size = request.json.get(
            "chunk_size", 2000
        )  # Reduced to 2000 to stay within limits
        last_id = request.json.get(
            "last_id", None
        )  # Use ID-based pagination instead of offset

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching students modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print(
                f"Starting student import from Salesforce (chunk_size: {chunk_size}, last_id: {last_id})..."
            )

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # First, get total count for progress tracking
        count_query = """
        SELECT COUNT(Id) total
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        """
        # Apply delta filter to count query as well
        if is_delta and watermark:
            count_query += delta_helper.build_date_filter(watermark)

        result = sf.query(count_query)
        if not result or "records" not in result or not result["records"]:
            return {
                "status": "error",
                "message": "Failed to get total record count from Salesforce",
                "errors": ["No records returned from Salesforce count query"],
            }
        total_records = result["records"][0]["total"]

        # Query for students using ID-based pagination with LastModifiedDate
        base_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email, Phone,
               Local_Student_ID__c, Birthdate, Gender__c, Racial_Ethnic_Background__c,
               npsp__Primary_Affiliation__c, Class__c, Legacy_Grade__c, Current_Grade__c,
               LastModifiedDate
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        {where_clause}
        {delta_clause}
        ORDER BY Id
        LIMIT {limit}
        """

        # Add WHERE clause for ID-based pagination
        where_clause = f"AND Id > '{last_id}'" if last_id else ""
        # Add delta filter
        delta_clause = (
            delta_helper.build_date_filter(watermark) if is_delta and watermark else ""
        )
        query = base_query.format(
            where_clause=where_clause, delta_clause=delta_clause, limit=chunk_size
        )

        print(
            f"Fetching students from Salesforce (chunk_size: {chunk_size}, last_id: {last_id}, delta: {is_delta})..."
        )
        result = sf.query(query)
        student_rows = result.get("records", [])

        success_count = 0
        error_count = 0
        errors = []
        processed_ids = []

        # Process each student in the chunk
        for row in student_rows:
            try:
                # Use the Student model's import method
                student, is_new, error = Student.import_from_salesforce(row, db.session)

                if error:
                    error_count += 1
                    errors.append(error)
                    continue

                if not student.id:
                    db.session.add(student)

                # Commit each student individually to prevent large transaction blocks
                db.session.commit()

                # Handle contact info using the student's method
                try:
                    success, error = student.update_contact_info(row, db.session)
                    if not success:
                        errors.append(error)
                    else:
                        db.session.commit()
                        success_count += 1
                        processed_ids.append(row["Id"])

                except Exception as e:
                    db.session.rollback()
                    errors.append(
                        f"Error processing contact info for {student.first_name} {student.last_name}: {str(e)}"
                    )
                    error_count += 1

            except Exception as e:
                db.session.rollback()
                errors.append(
                    f"Error processing student {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}"
                )
                error_count += 1
                continue

        # Get the last processed ID for the next chunk
        next_id = processed_ids[-1] if processed_ids else None
        is_complete = (
            len(student_rows) < chunk_size
        )  # If we got fewer records than chunk_size, we're done

        print(
            f"\nChunk complete - Created/Updated: {success_count}, Errors: {error_count}"
        )
        if errors:
            print("\nErrors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"- {error}")

        # Record sync log for delta sync tracking (only on final chunk)
        if is_complete:
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
                    sync_type="students",
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

        return {
            "status": "success",
            "message": f"Processed chunk of {len(student_rows)} students ({success_count} successful, {error_count} errors)",
            "total_records": total_records,
            "processed_count": len(processed_ids),
            "error_count": error_count,
            "skipped_count": 0,
            "next_id": next_id if not is_complete else None,
            "is_complete": is_complete,
            "is_delta_sync": is_delta,
            "errors": errors[:100],  # Limit error list size in response
            "processed_ids": processed_ids,
        }

    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        print(f"Error: {error_msg}")
        return {"status": "error", "message": error_msg, "errors": [str(e)]}
