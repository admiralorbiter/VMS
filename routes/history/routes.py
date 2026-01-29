"""
History Routes Module
===================

This module provides functionality for managing activity history and audit trails
in the Volunteer Management System (VMS). It handles history tracking, viewing,
filtering, and Salesforce integration for historical data.

Key Features:
- History table display with filtering and pagination
- Individual history item viewing
- History entry creation and management
- Soft delete functionality for history items
- Salesforce history data import
- Advanced filtering and sorting capabilities

Main Endpoints:
- /history_table: Main history listing with filters and pagination
- /history/view/<id>: View individual history item details
- /history/add: Add new history entry (POST)
- /history/delete/<id>: Soft delete history entry (POST)
- /history/import-from-salesforce: Import history from Salesforce (POST)

History Management:
- Activity tracking and audit trails
- Event and volunteer association
- Activity type and status categorization
- Date-based filtering and sorting
- Search functionality across summary and description

Filtering Capabilities:
- Text search in summary and description
- Activity type filtering
- Activity status filtering
- Date range filtering (start/end dates)
- Pagination with configurable page sizes
- Multi-column sorting with direction control

Salesforce Integration:
- History data import from Salesforce
- SOQL query execution for historical records
- Error handling and import statistics
- Batch processing with rollback support

Security Features:
- Login required for all operations
- Soft delete for data preservation
- Input validation and sanitization
- Error handling with user feedback

Dependencies:
- Flask Blueprint for routing
- History and Event models for data
- Salesforce API integration
- Database session management
- Utility functions for date parsing

Models Used:
- History: Activity history and audit data
- Event: Event association data
- Volunteer: Volunteer association data
- Database session for persistence

Template Dependencies:
- history/history.html: Main history table template
- history/view.html: Individual history item template
"""

import csv
import os
from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import login_required
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import or_, text

from config import Config
from models import db
from models.contact import Email
from models.event import Event
from models.history import History
from models.teacher import Teacher
from models.volunteer import Volunteer
from routes.decorators import global_users_only
from routes.utils import parse_date

history_bp = Blueprint("history", __name__)


@history_bp.route("/history_table")
@login_required
@global_users_only
def history_table():
    """
    Display the main history table with filtering and pagination.

    Provides a comprehensive view of all history entries with advanced
    filtering, sorting, and pagination capabilities.

    Query Parameters:
        page: Current page number for pagination
        per_page: Number of items per page
        sort_by: Column to sort by (activity_date, summary, activity_type, etc.)
        sort_direction: Sort direction (asc, desc)
        search_summary: Text search in summary and description
        activity_type: Filter by activity type
        activity_status: Filter by activity status
        start_date: Filter by start date (YYYY-MM-DD)
        end_date: Filter by end date (YYYY-MM-DD)

    Filtering Features:
        - Text search across summary and description fields
        - Activity type and status dropdown filtering
        - Date range filtering with validation
        - Dynamic filter options based on available data

    Sorting Features:
        - Multi-column sorting capability
        - Configurable sort direction
        - Default sort by activity_date descending

    Returns:
        Rendered history table template with filtered and paginated data

    Template Variables:
        history: List of history items for current page
        pagination: Pagination object with navigation
        current_filters: Dictionary of active filters
        activity_types: List of available activity types
        activity_statuses: List of available activity statuses
    """
    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Get sort parameters
    sort_by = request.args.get(
        "sort_by", "activity_date"
    )  # default sort by activity_date
    sort_direction = request.args.get("sort_direction", "desc")  # default direction

    # Create current_filters dictionary
    current_filters = {
        "search_summary": request.args.get("search_summary", "").strip(),
        "activity_type": request.args.get("activity_type", ""),
        "activity_status": request.args.get("activity_status", ""),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
        "per_page": per_page,
        "sort_by": sort_by,
        "sort_direction": sort_direction,
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Build query
    query = History.query.filter_by(is_deleted=False)

    # Apply filters
    if current_filters.get("search_summary"):
        search_term = f"%{current_filters['search_summary']}%"
        query = query.filter(
            or_(
                History.summary.ilike(search_term),
                History.description.ilike(search_term),
            )
        )

    if current_filters.get("activity_type"):
        query = query.filter(History.activity_type == current_filters["activity_type"])

    if current_filters.get("activity_status"):
        query = query.filter(
            History.activity_status == current_filters["activity_status"]
        )

    if current_filters.get("start_date"):
        try:
            start_date = datetime.strptime(current_filters["start_date"], "%Y-%m-%d")
            query = query.filter(History.activity_date >= start_date)
        except ValueError:
            flash("Invalid start date format", "warning")

    if current_filters.get("end_date"):
        try:
            end_date = datetime.strptime(current_filters["end_date"], "%Y-%m-%d")
            # Add 23:59:59 to include the entire end date
            end_date = end_date + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(History.activity_date <= end_date)
        except ValueError:
            flash("Invalid end date format", "warning")

    # Apply sorting
    sort_column = getattr(History, sort_by, History.activity_date)
    if sort_direction == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get unique activity types and statuses for filters (with limits for performance)
    activity_types = (
        db.session.query(History.activity_type)
        .filter(History.is_deleted == False)
        .distinct()
        .order_by(History.activity_type)
        .limit(50)  # Limit to prevent loading massive datasets
        .all()
    )
    activity_types = [t[0] for t in activity_types if t[0]]  # Remove None values

    activity_statuses = (
        db.session.query(History.activity_status)
        .filter(History.is_deleted == False)
        .distinct()
        .order_by(History.activity_status)
        .limit(50)  # Limit to prevent loading massive datasets
        .all()
    )
    activity_statuses = [s[0] for s in activity_statuses if s[0]]  # Remove None values

    return render_template(
        "history/history.html",
        history=pagination.items,
        pagination=pagination,
        current_filters=current_filters,
        activity_types=activity_types,
        activity_statuses=activity_statuses,
    )


@history_bp.route("/history/view/<int:id>")
@login_required
@global_users_only
def view_history(id):
    """
    Display detailed view of a specific history item.

    Shows comprehensive information about a single history entry
    including all associated data and metadata.

    Args:
        id: Database ID of the history item to view

    Returns:
        Rendered template with detailed history item information

    Raises:
        404: History item not found
    """
    history_item = History.query.get_or_404(id)
    return render_template("history/view.html", history=history_item)


@history_bp.route("/history/add", methods=["POST"])
@login_required
@global_users_only
def add_history():
    """
    Add a new history entry.

    Creates a new history record with the provided data and
    associates it with events, volunteers, and other entities.

    Request Body (JSON):
        event_id: Associated event ID (optional)
        volunteer_id: Associated volunteer ID (optional)
        action: Action performed
        summary: Brief summary of the activity
        description: Detailed description of the activity
        activity_type: Type of activity performed
        activity_status: Status of the activity (default: 'Completed')
        email_message_id: Associated email message ID (optional)

    Returns:
        JSON response with success status and history ID

    Raises:
        500: Database or server error
    """
    try:
        data = request.get_json()

        history = History(
            event_id=data.get("event_id"),
            volunteer_id=data.get("volunteer_id"),
            action=data.get("action"),
            summary=data.get("summary"),
            description=data.get("description"),
            activity_type=data.get("activity_type"),
            activity_date=datetime.now(timezone.utc),
            activity_status=data.get("activity_status", "Completed"),
            completed_at=(
                datetime.now(timezone.utc)
                if data.get("activity_status") == "Completed"
                else None
            ),
            email_message_id=data.get("email_message_id"),
        )

        db.session.add(history)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "History entry added successfully",
                "history_id": history.id,
            }
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {"success": False, "message": f"Error adding history entry: {str(e)}"}
            ),
            500,
        )


@history_bp.route("/history/delete/<int:id>", methods=["POST"])
@login_required
@global_users_only
def delete_history(id):
    """
    Soft delete a history entry.

    Marks a history item as deleted without permanently removing
    it from the database, preserving data integrity.

    Args:
        id: Database ID of the history item to delete

    Returns:
        JSON response with success status

    Raises:
        404: History item not found
        500: Database or server error
    """
    try:
        history = History.query.get_or_404(id)
        history.is_deleted = True
        db.session.commit()

        return jsonify(
            {"success": True, "message": "History entry deleted successfully"}
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {"success": False, "message": f"Error deleting history entry: {str(e)}"}
            ),
            500,
        )


@history_bp.route("/history/import-from-salesforce", methods=["POST"])
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
        - Executes SOQL queries for historical data
        - Processes records in batches
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
        print("Starting history import from Salesforce...")
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

        # Query Task records (activities, calls, meetings)
        task_query = """
            SELECT Id, Subject, Description, Type, Status,
                   ActivityDate, WhoId, WhatId
            FROM Task
            WHERE WhoId != null
        """

        # Query EmailMessage records (emails)
        email_query = """
            SELECT Id, Subject, TextBody, HtmlBody, MessageDate, FromAddress,
                   ToAddress, CcAddress, BccAddress, RelatedToId, ParentId,
                   Incoming, Status, CreatedDate, LastModifiedDate,
                   MessageIdentifier, ThreadIdentifier
            FROM EmailMessage
            WHERE RelatedToId != null
        """

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
                        # Process Task record (existing logic)
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

                        # EmailMessage RelatedToId can be Case, Account, or Contact
                        # We need to find the associated contact through different methods
                        contact = None
                        related_to_id = row["RelatedToId"]

                        # Method 1: Try to match by email address (most reliable for EmailMessage)
                        to_address = row.get("ToAddress", "")
                        from_address = row.get("FromAddress", "")

                        # Try to find contact by email in ToAddress
                        if to_address:
                            # Extract email addresses from ToAddress (might be comma-separated)
                            emails = [email.strip() for email in to_address.split(",")]
                            for email in emails:
                                # Clean email address
                                email = email.strip().lower()
                                if email:
                                    # Search volunteers by email through the Email model (EFFICIENT)
                                    contact = (
                                        db.session.query(Volunteer)
                                        .join(Email)
                                        .filter(db.func.lower(Email.email) == email)
                                        .first()
                                    )

                                    # Search teachers by email through the Email model (EFFICIENT)
                                    if not contact:
                                        contact = (
                                            db.session.query(Teacher)
                                            .join(Email)
                                            .filter(db.func.lower(Email.email) == email)
                                            .first()
                                        )

                                    if contact:
                                        break

                        # Try to find contact by email in FromAddress if still no match
                        if not contact and from_address:
                            from_email = from_address.strip().lower()
                            if from_email:
                                # Search volunteers by email through the Email model (EFFICIENT)
                                contact = (
                                    db.session.query(Volunteer)
                                    .join(Email)
                                    .filter(db.func.lower(Email.email) == from_email)
                                    .first()
                                )

                                # Search teachers by email through the Email model (EFFICIENT)
                                if not contact:
                                    contact = (
                                        db.session.query(Teacher)
                                        .join(Email)
                                        .filter(
                                            db.func.lower(Email.email) == from_email
                                        )
                                        .first()
                                    )

                        # Method 2: Try direct contact match (unlikely but worth trying)
                        if not contact:
                            contact = Volunteer.query.filter_by(
                                salesforce_individual_id=related_to_id
                            ).first()

                            if not contact:
                                contact = Teacher.query.filter_by(
                                    salesforce_individual_id=related_to_id
                                ).first()

                        # Method 2: If RelatedToId is a Case, find the contact through the case
                        if not contact:
                            # Query for cases with this RelatedToId and get the contact
                            case_query = f"""
                                SELECT ContactId, AccountId
                                FROM Case
                                WHERE Id = '{related_to_id}'
                            """
                            try:
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
                                print(
                                    f"Error querying case for RelatedToId {related_to_id}: {e}"
                                )

                        # Method 3: If RelatedToId is an Account, find contacts through the account
                        if not contact:
                            # Query for contacts associated with this account
                            account_query = f"""
                                SELECT Id, FirstName, LastName, Email
                                FROM Contact
                                WHERE AccountId = '{related_to_id}'
                                AND (Contact_Type__c = 'Volunteer' OR Contact_Type__c = '' OR Contact_Type__c = 'Teacher')
                            """
                            try:
                                account_result = sf.query_all(account_query)
                                if account_result.get("records"):
                                    # Try to match by email address from the EmailMessage
                                    to_address = row.get("ToAddress", "")
                                    from_address = row.get("FromAddress", "")

                                    for contact_record in account_result["records"]:
                                        contact_email = contact_record.get("Email", "")
                                        if contact_email in [to_address, from_address]:
                                            # Found a match by email
                                            contact = Volunteer.query.filter_by(
                                                salesforce_individual_id=contact_record[
                                                    "Id"
                                                ]
                                            ).first()
                                            if not contact:
                                                contact = Teacher.query.filter_by(
                                                    salesforce_individual_id=contact_record[
                                                        "Id"
                                                    ]
                                                ).first()
                                            if contact:
                                                break
                            except Exception as e:
                                print(
                                    f"Error querying account for RelatedToId {related_to_id}: {e}"
                                )

                        # Method 4: Try to match by email address directly
                        if not contact:
                            to_address = row.get("ToAddress", "")
                            from_address = row.get("FromAddress", "")

                            # Search for volunteers with matching email addresses
                            if to_address:
                                email_match = Email.query.filter_by(
                                    email=to_address
                                ).first()
                                if email_match:
                                    contact = Volunteer.query.get(
                                        email_match.contact_id
                                    )

                            if not contact and from_address:
                                email_match = Email.query.filter_by(
                                    email=from_address
                                ).first()
                                if email_match:
                                    contact = Volunteer.query.get(
                                        email_match.contact_id
                                    )

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
                        # Handle activity date for Task records
                        activity_date = parse_date(
                            row.get("ActivityDate")
                        ) or datetime.now(timezone.utc)

                        history = History(
                            contact_id=contact.id,
                            activity_date=activity_date,
                            history_type="activity",
                            salesforce_id=row["Id"],
                            summary=row.get("Subject", ""),
                            activity_type=row.get("Type", ""),
                            activity_status=row.get("Status", ""),
                        )
                        db.session.add(history)

                        # Process description field for Task records
                        description = row.get("Description", "")
                        if description:
                            import re

                            # Remove HTML tags if present
                            description = re.sub(r"<[^>]+>", "", description)
                            # Clean up extra whitespace
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

                        # Handle event relationship for Task records
                        if row.get("WhatId"):
                            event = Event.query.filter_by(
                                salesforce_id=row["WhatId"]
                            ).first()
                            if event:
                                history.event_id = event.id

                    elif record_type == "EmailMessage":
                        # Handle message date for EmailMessage records
                        message_date = parse_date(
                            row.get("MessageDate")
                        ) or datetime.now(timezone.utc)

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
                        body_content = row.get("TextBody", "") or row.get(
                            "HtmlBody", ""
                        )
                        if body_content:
                            import re

                            # Clean up HTML if present
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
                            activity_status=(
                                "Received" if row.get("Incoming", False) else "Sent"
                            ),
                            description="\n".join(email_content),
                            email_message_id=row["Id"],
                        )
                        db.session.add(history)

                    success_count += 1

                    # Commit every 100 records
                    if success_count % 100 == 0:
                        db.session.commit()
                        print(f"Processed {success_count} records...")

                except Exception as e:
                    error_count += 1
                    other_skip_reasons += 1
                    # Add more detailed error logging
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

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} history records",
                "processed_count": success_count,
                "error_count": error_count,
                "skipped_count": skipped_count,
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
