"""
Salesforce History Import Routes
================================

This module handles the Salesforce data import functionality for activity history.
Extracted from routes/history/routes.py to consolidate all Salesforce
import routes in one location.

Routes:
- /history/import-from-salesforce: Import history data from Salesforce
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import text

from config import Config
from models import db
from models.contact import Email
from models.event import Event
from models.history import History
from models.teacher import Teacher
from models.volunteer import Volunteer
from routes.decorators import global_users_only
from routes.utils import parse_date

# Create Blueprint for Salesforce history import routes
history_import_bp = Blueprint("history_import", __name__)


@history_import_bp.route("/history/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
def import_history_from_salesforce():
    """
    Import history data from Salesforce.

    Fetches historical activity data from Salesforce and synchronizes
    it with the local database. Handles batch processing with error
    reporting and import statistics.

    Salesforce Integration:
        - Connects to Salesforce using configured credentials
        - Executes SOQL queries for Task and EmailMessage records
        - Processes records in batches with commit every 100 records
        - Provides detailed import statistics

    Error Handling:
        - Salesforce authentication failures
        - Data validation errors
        - Database transaction rollback
        - Detailed error reporting

    Returns:
        JSON response with import results and statistics

    Raises:
        401: Salesforce authentication failure
        500: Import or database error
    """
    try:
        started_at = datetime.now(timezone.utc)

        # Delta sync support - check if incremental sync requested
        from services.delta_sync_service import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("history")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching history modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Starting history import from Salesforce (FULL SYNC)...")

        success_count = 0
        error_count = 0
        errors = []
        skipped_count = 0

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # Query Task records (activities, calls, meetings) with LastModifiedDate
        task_query = """
            SELECT Id, Subject, Description, Type, Status,
                   ActivityDate, WhoId, WhatId, LastModifiedDate
            FROM Task
            WHERE WhoId != null
        """

        # Add delta filter for Task records
        if is_delta and watermark:
            task_query += delta_helper.build_date_filter(watermark)

        # Query EmailMessage records (emails) - already has LastModifiedDate
        email_query = """
            SELECT Id, Subject, TextBody, HtmlBody, MessageDate, FromAddress,
                   ToAddress, CcAddress, BccAddress, RelatedToId, ParentId,
                   Incoming, Status, CreatedDate, LastModifiedDate,
                   MessageIdentifier, ThreadIdentifier
            FROM EmailMessage
            WHERE RelatedToId != null
        """

        # Add delta filter for EmailMessage records
        if is_delta and watermark:
            email_query += delta_helper.build_date_filter(watermark)

        # Process Task records
        print("Processing Task records...")
        task_result = sf.query_all(task_query)
        task_rows = task_result.get("records", [])
        print(f"Found {len(task_rows)} Task records in Salesforce")

        # Process EmailMessage records
        print("Processing EmailMessage records...")
        email_result = sf.query_all(email_query)
        email_rows = email_result.get("records", [])
        print(f"Found {len(email_rows)} EmailMessage records in Salesforce")

        # Combine both result sets
        all_records = []
        for row in task_rows:
            row["record_type"] = "Task"
            all_records.append(row)

        for row in email_rows:
            row["record_type"] = "EmailMessage"
            all_records.append(row)

        print(f"Total records to process: {len(all_records)}")

        # Sample the first few records to see data structure
        if all_records:
            print("\n=== SAMPLE SALESFORCE DATA ===")
            for i, row in enumerate(all_records[:3]):
                print(f"Record {i+1} ({row.get('record_type', 'Unknown')}):")
                print(f"  ID: {row.get('Id', 'None')}")
                print(f"  Subject: {row.get('Subject', 'None')}")
                if row.get("record_type") == "Task":
                    print(f"  WhoId: {row.get('WhoId', 'None')}")
                    print(f"  Type: {row.get('Type', 'None')}")
                    print(f"  Status: {row.get('Status', 'None')}")
                    print(f"  ActivityDate: {row.get('ActivityDate', 'None')}")
                    print(f"  WhatId: {row.get('WhatId', 'None')}")
                else:  # EmailMessage
                    print(f"  RelatedToId: {row.get('RelatedToId', 'None')}")
                    print(f"  FromAddress: {row.get('FromAddress', 'None')}")
                    print(f"  ToAddress: {row.get('ToAddress', 'None')}")
                    print(f"  MessageDate: {row.get('MessageDate', 'None')}")
                    print(f"  Incoming: {row.get('Incoming', 'None')}")
                print("  ---")

        # Initialize counters for better tracking
        already_exists_count = 0
        no_contact_count = 0
        other_skip_reasons = 0

        # Use no_autoflush to prevent premature flushing
        with db.session.no_autoflush:
            for row in all_records:
                try:
                    record_type = row.get("record_type", "Task")
                    contact = None

                    if record_type == "Task":
                        # Process Task record
                        if not row.get("WhoId"):
                            skipped_count += 1
                            continue

                        # Search across all contact types (volunteers, teachers, etc.)
                        contact = Volunteer.query.filter_by(
                            salesforce_individual_id=row["WhoId"]
                        ).first()

                        if not contact:
                            contact = Teacher.query.filter_by(
                                salesforce_individual_id=row["WhoId"]
                            ).first()

                        if not contact:
                            no_contact_count += 1
                            skipped_count += 1
                            error_msg = f"Skipped Task record {row.get('Subject', 'Unknown')} (ID: {row.get('Id', 'Unknown')}): No matching contact found for WhoId: {row.get('WhoId', 'None')}"
                            print(f"NO_CONTACT: {error_msg}")
                            errors.append(error_msg)
                            continue

                    elif record_type == "EmailMessage":
                        # Process EmailMessage record
                        if not row.get("RelatedToId"):
                            skipped_count += 1
                            continue

                        contact = _find_contact_for_email(sf, row, db)

                        if not contact:
                            no_contact_count += 1
                            skipped_count += 1
                            error_msg = f"Skipped EmailMessage record {row.get('Subject', 'Unknown')} (ID: {row.get('Id', 'Unknown')}): No matching contact found for RelatedToId: {row.get('RelatedToId', 'None')} (To: {row.get('ToAddress', 'None')}, From: {row.get('FromAddress', 'None')})"
                            print(f"NO_CONTACT: {error_msg}")
                            errors.append(error_msg)
                            continue

                    # Check if history exists - use raw SQL to avoid schema issues
                    history_result = db.session.execute(
                        text(
                            "SELECT id FROM history WHERE salesforce_id = :salesforce_id AND is_deleted = 0"
                        ),
                        {"salesforce_id": row["Id"]},
                    ).fetchone()
                    history_exists = history_result is not None

                    if history_exists:
                        # Record already exists in system
                        already_exists_count += 1
                        skipped_count += 1
                        continue

                    # Create new history record based on record type
                    if record_type == "Task":
                        history = _create_task_history(row, contact)

                    elif record_type == "EmailMessage":
                        history = _create_email_history(row, contact)

                    db.session.add(history)
                    success_count += 1

                    # Commit every 100 records
                    if success_count % 100 == 0:
                        db.session.commit()
                        print(f"Processed {success_count} records...")

                except Exception as e:
                    error_count += 1
                    other_skip_reasons += 1
                    error_msg = f"Error processing {record_type} record {row.get('Subject', 'Unknown')} (ID: {row.get('Id', 'Unknown')}): {str(e)}"
                    print(f"ERROR: {error_msg}")
                    errors.append(error_msg)
                    continue

            # Final commit
            try:
                db.session.commit()
                print(f"Import completed successfully!")
                print(f"  - New records created: {success_count}")
                print(f"  - Records already exist: {already_exists_count}")
                print(f"  - No matching contact: {no_contact_count}")
                print(f"  - Other errors: {other_skip_reasons}")
                print(f"  - Total skipped: {skipped_count}")
            except Exception as e:
                db.session.rollback()
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Error during final commit: {str(e)}",
                            "processed": success_count,
                            "errors": errors,
                        }
                    ),
                    500,
                )

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
                sync_type="history",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=success_count,
                records_failed=error_count,
                records_skipped=skipped_count,
                is_delta_sync=is_delta,
                last_sync_watermark=(
                    datetime.now(timezone.utc)
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
                "message": f"Successfully processed {success_count} history records",
                "processed_count": success_count,
                "error_count": error_count,
                "skipped_count": skipped_count,
                "is_delta_sync": is_delta,
                "stats": {
                    "success": success_count,
                    "errors": error_count,
                    "skipped": skipped_count,
                    "skipped_details": {
                        "already_exists": already_exists_count,
                        "no_contact": no_contact_count,
                        "other_reasons": other_skip_reasons,
                    },
                },
                "errors": errors[:100],
            }
        )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _find_contact_for_email(sf, row, db):
    """
    Find a contact for an EmailMessage record.

    Tries multiple methods:
    1. Email address matching from ToAddress/FromAddress
    2. Direct contact match by RelatedToId
    3. Case-based contact lookup
    4. Account-based contact lookup
    """
    contact = None
    related_to_id = row["RelatedToId"]

    # Method 1: Try to match by email address (most reliable for EmailMessage)
    to_address = row.get("ToAddress", "")
    from_address = row.get("FromAddress", "")

    # Try to find contact by email in ToAddress
    if to_address:
        emails = [email.strip() for email in to_address.split(",")]
        for email in emails:
            email = email.strip().lower()
            if email:
                contact = (
                    db.session.query(Volunteer)
                    .join(Email)
                    .filter(db.func.lower(Email.email) == email)
                    .first()
                )
                if not contact:
                    contact = (
                        db.session.query(Teacher)
                        .join(Email)
                        .filter(db.func.lower(Email.email) == email)
                        .first()
                    )
                if contact:
                    break

    # Try FromAddress if still no match
    if not contact and from_address:
        from_email = from_address.strip().lower()
        if from_email:
            contact = (
                db.session.query(Volunteer)
                .join(Email)
                .filter(db.func.lower(Email.email) == from_email)
                .first()
            )
            if not contact:
                contact = (
                    db.session.query(Teacher)
                    .join(Email)
                    .filter(db.func.lower(Email.email) == from_email)
                    .first()
                )

    # Method 2: Direct contact match
    if not contact:
        contact = Volunteer.query.filter_by(
            salesforce_individual_id=related_to_id
        ).first()
        if not contact:
            contact = Teacher.query.filter_by(
                salesforce_individual_id=related_to_id
            ).first()

    # Method 3: Case-based lookup
    if not contact:
        try:
            case_query = f"""
                SELECT ContactId, AccountId
                FROM Case
                WHERE Id = '{related_to_id}'
            """
            case_result = sf.query_all(case_query)
            if case_result.get("records"):
                case_record = case_result["records"][0]
                contact_id = case_record.get("ContactId")
                if contact_id:
                    contact = Volunteer.query.filter_by(
                        salesforce_individual_id=contact_id
                    ).first()
                    if not contact:
                        contact = Teacher.query.filter_by(
                            salesforce_individual_id=contact_id
                        ).first()
        except Exception as e:
            print(f"Error querying case for RelatedToId {related_to_id}: {e}")

    # Method 4: Account-based lookup
    if not contact:
        try:
            account_query = f"""
                SELECT Id, FirstName, LastName, Email
                FROM Contact
                WHERE AccountId = '{related_to_id}'
                AND (Contact_Type__c = 'Volunteer' OR Contact_Type__c = '' OR Contact_Type__c = 'Teacher')
            """
            account_result = sf.query_all(account_query)
            if account_result.get("records"):
                for contact_record in account_result["records"]:
                    contact_email = contact_record.get("Email", "")
                    if contact_email in [to_address, from_address]:
                        contact = Volunteer.query.filter_by(
                            salesforce_individual_id=contact_record["Id"]
                        ).first()
                        if not contact:
                            contact = Teacher.query.filter_by(
                                salesforce_individual_id=contact_record["Id"]
                            ).first()
                        if contact:
                            break
        except Exception as e:
            print(f"Error querying account for RelatedToId {related_to_id}: {e}")

    # Method 5: Direct email table lookup
    if not contact:
        if to_address:
            email_match = Email.query.filter_by(email=to_address).first()
            if email_match:
                contact = Volunteer.query.get(email_match.contact_id)

        if not contact and from_address:
            email_match = Email.query.filter_by(email=from_address).first()
            if email_match:
                contact = Volunteer.query.get(email_match.contact_id)

    return contact


def _create_task_history(row, contact):
    """Create a History record from a Task row."""
    activity_date = parse_date(row.get("ActivityDate")) or datetime.now(timezone.utc)

    history = History(
        contact_id=contact.id,
        activity_date=activity_date,
        history_type="activity",
        salesforce_id=row["Id"],
        summary=row.get("Subject", ""),
        activity_type=row.get("Type", ""),
        activity_status=row.get("Status", ""),
    )

    # Process description field
    description = row.get("Description", "")
    if description:
        description = re.sub(r"<[^>]+>", "", description)
        description = re.sub(r"\s+", " ", description).strip()
        history.description = description

    # Map Salesforce type to history_type
    sf_type = (row.get("Type", "") or "").lower()
    if sf_type == "email":
        history.history_type = "activity"
        history.activity_type = "Email"
        history.email_message_id = row["Id"]
    elif sf_type in ["call"]:
        history.history_type = "activity"
    elif sf_type in ["status_update"]:
        history.history_type = "status_change"
    else:
        history.history_type = "note"

    # Handle event relationship
    if row.get("WhatId"):
        event = Event.query.filter_by(salesforce_id=row["WhatId"]).first()
        if event:
            history.event_id = event.id

    return history


def _create_email_history(row, contact):
    """Create a History record from an EmailMessage row."""
    message_date = parse_date(row.get("MessageDate")) or datetime.now(timezone.utc)

    # Create email content description
    email_content = []
    if row.get("FromAddress"):
        email_content.append(f"From: {row['FromAddress']}")
    if row.get("ToAddress"):
        email_content.append(f"To: {row['ToAddress']}")
    if row.get("CcAddress"):
        email_content.append(f"CC: {row['CcAddress']}")
    if row.get("BccAddress"):
        email_content.append(f"BCC: {row['BccAddress']}")
    email_content.append(f"Subject: {row.get('Subject', '')}")
    email_content.append("Body:")

    # Use TextBody if available, otherwise HtmlBody
    body_content = row.get("TextBody", "") or row.get("HtmlBody", "")
    if body_content:
        if row.get("HtmlBody"):
            body_content = re.sub(r"<[^>]+>", "", body_content)
        body_content = re.sub(r"\s+", " ", body_content).strip()
        email_content.append(body_content)

    history = History(
        contact_id=contact.id,
        activity_date=message_date,
        history_type="activity",
        salesforce_id=row["Id"],
        summary=row.get("Subject", ""),
        activity_type="Email",
        activity_status="Received" if row.get("Incoming", False) else "Sent",
        description="\n".join(email_content),
        email_message_id=row["Id"],
    )

    return history
