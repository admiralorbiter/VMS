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
from simple_salesforce import SalesforceAuthenticationFailed
from sqlalchemy import text

from models import db
from models.contact import Email
from models.event import Event
from models.history import History
from models.teacher import Teacher
from models.volunteer import Volunteer
from routes.decorators import global_users_only, handle_route_errors
from routes.utils import parse_date
from services.salesforce import get_salesforce_client, safe_query_all
from services.salesforce.errors import ImportErrorCode, create_import_error

# Create Blueprint for Salesforce history import routes
sf_history_import_bp = Blueprint("sf_history_import", __name__)


@sf_history_import_bp.route("/history/import-from-salesforce", methods=["POST"])
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
        from services.salesforce import DeltaSyncHelper

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

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

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
        task_result = safe_query_all(sf, task_query)
        task_rows = task_result.get("records", [])
        print(f"Found {len(task_rows)} Task records in Salesforce")

        # Process EmailMessage records
        print("Processing EmailMessage records...")
        email_result = safe_query_all(sf, email_query)
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

        # C-1 Hardening: Build memory-resident caches
        from services.salesforce.utils import build_history_caches

        contacts_cache, events_cache, emails_cache = build_history_caches(db.session)

        # Pre-fetch Case and Account data to eliminate SOQL API N+1 queries
        # 1. Cases
        case_ids = {
            r["RelatedToId"]
            for r in email_rows
            if (r.get("RelatedToId") or "").startswith("500")
        }
        case_to_contact_cache = {}
        if case_ids:
            case_ids_list = list(case_ids)
            for chunk_start in range(0, len(case_ids_list), 200):
                chunk = case_ids_list[chunk_start : chunk_start + 200]
                ids_str = ",".join([f"'{i}'" for i in chunk])
                case_query = f"SELECT Id, ContactId FROM Case WHERE Id IN ({ids_str})"
                try:
                    case_res = sf.query_all(case_query)
                    for c_rec in case_res.get("records", []):
                        if c_rec.get("ContactId"):
                            case_to_contact_cache[c_rec["Id"]] = c_rec["ContactId"]
                except Exception as e:
                    print(f"Error bulk querying Cases: {e}")

        # 2. Accounts
        account_ids = {
            r["RelatedToId"]
            for r in email_rows
            if (r.get("RelatedToId") or "").startswith("001")
        }
        account_to_contacts_cache = {}
        if account_ids:
            acc_ids_list = list(account_ids)
            for chunk_start in range(0, len(acc_ids_list), 200):
                chunk = acc_ids_list[chunk_start : chunk_start + 200]
                ids_str = ",".join([f"'{i}'" for i in chunk])
                acc_query = f"SELECT AccountId, Id, Email FROM Contact WHERE AccountId IN ({ids_str}) AND (Contact_Type__c = 'Volunteer' OR Contact_Type__c = '' OR Contact_Type__c = 'Teacher')"
                try:
                    acc_res = sf.query_all(acc_query)
                    for acc_rec in acc_res.get("records", []):
                        acc_id = acc_rec.get("AccountId")
                        if acc_id not in account_to_contacts_cache:
                            account_to_contacts_cache[acc_id] = []
                        account_to_contacts_cache[acc_id].append(
                            {"Email": acc_rec.get("Email"), "Id": acc_rec.get("Id")}
                        )
                except Exception as e:
                    print(f"Error bulk querying Accounts: {e}")

        # Use no_autoflush to prevent premature flushing
        with db.session.no_autoflush:
            for i, row in enumerate(all_records):
                try:
                    record_type = row.get("record_type", "Task")
                    contact_id = None

                    if record_type == "Task":
                        # Process Task record
                        if not row.get("WhoId"):
                            skipped_count += 1
                            continue

                        contact_id = contacts_cache.get(row["WhoId"])

                        if not contact_id:
                            no_contact_count += 1
                            skipped_count += 1
                            import_error = create_import_error(
                                code=ImportErrorCode.FK_NOT_FOUND,
                                row=row,
                                message=f"No matching contact found for WhoId: {row.get('WhoId', 'None')}",
                                field="WhoId",
                                name_fields=("Subject",),
                            )
                            # Supressed excessive prints, N+1 fix
                            errors.append(import_error.to_dict())
                            continue

                    elif record_type == "EmailMessage":
                        # Process EmailMessage record
                        if not row.get("RelatedToId"):
                            skipped_count += 1
                            continue

                        contact_id = _find_contact_for_email(
                            row,
                            contacts_cache,
                            emails_cache,
                            case_to_contact_cache,
                            account_to_contacts_cache,
                        )

                        if not contact_id:
                            no_contact_count += 1
                            skipped_count += 1
                            import_error = create_import_error(
                                code=ImportErrorCode.FK_NOT_FOUND,
                                row=row,
                                message=f"No matching contact found for RelatedToId: {row.get('RelatedToId', 'None')} (To: {row.get('ToAddress', 'None')}, From: {row.get('FromAddress', 'None')})",
                                field="RelatedToId",
                                name_fields=("Subject",),
                            )
                            # Supressed excessive prints, N+1 fix
                            errors.append(import_error.to_dict())
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
                        history = _create_task_history(row, contact_id, events_cache)

                    elif record_type == "EmailMessage":
                        history = _create_email_history(row, contact_id)

                    db.session.add(history)
                    success_count += 1

                    # Batch commit every 100 records for resumability
                    if (i + 1) % 100 == 0:
                        db.session.commit()
                        print(
                            f"  -> Committed history batch {(i+1) // 100} ({success_count} successful)"
                        )

                except Exception as e:
                    error_count += 1
                    other_skip_reasons += 1
                    import_error = create_import_error(
                        code=ImportErrorCode.UNKNOWN,
                        row=row,
                        message=str(e),
                        name_fields=("Subject",),
                    )
                    print(f"ERROR: {import_error}")
                    errors.append(import_error.to_dict())
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
            from models.sync_log import SyncStatus
            from services.salesforce.delta_sync import create_sync_log_with_watermark

            sync_status = SyncStatus.SUCCESS.value
            if error_count > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if success_count > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = create_sync_log_with_watermark(
                sync_type="history",
                started_at=started_at,
                status=sync_status,
                records_processed=success_count,
                records_failed=error_count,
                records_skipped=skipped_count,
                is_delta=is_delta,
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


def _find_contact_for_email(
    row, contacts_cache, emails_cache, case_cache, account_cache
):
    """
    Find a contact for an EmailMessage record using in-memory caches.
    Returns contact_id instead of full contact object to eliminate N+1 queries.
    """
    contact_id = None
    related_to_id = row.get("RelatedToId", "")

    # Method 1: Try to match by email address
    to_address = row.get("ToAddress", "")
    from_address = row.get("FromAddress", "")

    if to_address:
        emails = [email.strip().lower() for email in to_address.split(",")]
        for email in emails:
            if email in emails_cache:
                contact_id = emails_cache[email]
                break

    if not contact_id and from_address:
        from_email = from_address.strip().lower()
        if from_email in emails_cache:
            contact_id = emails_cache[from_email]

    # Method 2: Direct contact match
    if not contact_id:
        contact_id = contacts_cache.get(related_to_id)

    # Method 3: Case-based lookup
    if not contact_id and related_to_id.startswith("500"):
        case_contact_sf_id = case_cache.get(related_to_id)
        if case_contact_sf_id:
            contact_id = contacts_cache.get(case_contact_sf_id)

    # Method 4: Account-based lookup
    if not contact_id and related_to_id.startswith("001"):
        acc_contacts = account_cache.get(related_to_id, [])
        for acc_contact in acc_contacts:
            contact_email = acc_contact.get("Email", "")
            if contact_email in [to_address, from_address]:
                contact_id = contacts_cache.get(acc_contact["Id"])
                if contact_id:
                    break

    return contact_id


def _create_task_history(row, contact_id, events_cache):
    """Create a History record from a Task row."""
    activity_date = parse_date(row.get("ActivityDate")) or datetime.now(timezone.utc)

    history = History(
        contact_id=contact_id,
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
        event_id = events_cache.get(row["WhatId"])
        if event_id:
            history.event_id = event_id

    return history


def _create_email_history(row, contact_id):
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
        contact_id=contact_id,
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
