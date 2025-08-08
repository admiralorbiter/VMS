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

from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import login_required
from simple_salesforce import SalesforceAuthenticationFailed
from sqlalchemy import or_

from models import db
from models.event import Event
from models.history import History
from models.volunteer import Volunteer
from routes.utils import parse_date
from utils.salesforce_importer import ImportConfig, SalesforceImporter

history_bp = Blueprint("history", __name__)


@history_bp.route("/history_table")
@login_required
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
    sort_by = request.args.get("sort_by", "activity_date")  # default sort by activity_date
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
        query = query.filter(or_(History.summary.ilike(search_term), History.description.ilike(search_term)))

    if current_filters.get("activity_type"):
        query = query.filter(History.activity_type == current_filters["activity_type"])

    if current_filters.get("activity_status"):
        query = query.filter(History.activity_status == current_filters["activity_status"])

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

    # Get unique activity types and statuses for filters
    activity_types = db.session.query(History.activity_type).filter(History.is_deleted is False).distinct().order_by(History.activity_type).all()
    activity_types = [t[0] for t in activity_types if t[0]]  # Remove None values

    activity_statuses = db.session.query(History.activity_status).filter(History.is_deleted is False).distinct().order_by(History.activity_status).all()
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
            completed_at=datetime.now(timezone.utc) if data.get("activity_status") == "Completed" else None,
            email_message_id=data.get("email_message_id"),
        )

        db.session.add(history)
        db.session.commit()

        return jsonify({"success": True, "message": "History entry added successfully", "history_id": history.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error adding history entry: {str(e)}"}), 500


@history_bp.route("/history/delete/<int:id>", methods=["POST"])
@login_required
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

        return jsonify({"success": True, "message": "History entry deleted successfully"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error deleting history entry: {str(e)}"}), 500


@history_bp.route("/history/import-from-salesforce", methods=["POST"])
@login_required
def import_history_from_salesforce():
    """
    Import history data from Salesforce (Optimized).

    Uses the standardized SalesforceImporter with batching, retries,
    validation, and progress reporting.
    """
    try:
        print("Starting optimized history import from Salesforce...")

        # Configure importer
        config = ImportConfig(
            batch_size=500,
            max_retries=3,
            retry_delay_seconds=5,
            validate_data=True,
            log_progress=True,
            commit_frequency=10,
        )
        importer = SalesforceImporter(config)

        # Minimal fields needed from Task
        task_query = """
            SELECT Id, Subject, Description, Type, Status,
                   ActivityDate, WhoId, WhatId
            FROM Task
            WHERE WhoId != null
            ORDER BY ActivityDate DESC
        """

        # Caches
        volunteer_cache: dict[str, Volunteer | None] = {}
        event_cache: dict[str, Event | None] = {}

        created_count = 0
        updated_count = 0
        skipped_no_volunteer = 0
        linked_events = 0

        def get_volunteer_cached(who_id: str, session):
            if who_id in volunteer_cache:
                return volunteer_cache[who_id]
            with session.no_autoflush:
                vol = session.query(Volunteer).filter_by(salesforce_individual_id=who_id).first()
            volunteer_cache[who_id] = vol
            return vol

        def get_event_cached(what_id: str, session):
            if not what_id:
                return None
            if what_id in event_cache:
                return event_cache[what_id]
            with session.no_autoflush:
                ev = session.query(Event).filter_by(salesforce_id=what_id).first()
            event_cache[what_id] = ev
            return ev

        def validate_history_record(record: dict) -> list:
            errors = []
            if not record.get("Id"):
                errors.append("Missing Task Id")
            return errors

        def process_history_record_optimized(record: dict, session) -> bool:
            nonlocal created_count, updated_count, skipped_no_volunteer, linked_events
            try:
                who_id = record.get("WhoId")
                if not who_id:
                    skipped_no_volunteer += 1
                    return False

                volunteer = get_volunteer_cached(who_id, session)
                if not volunteer:
                    skipped_no_volunteer += 1
                    return False

                sf_id = record.get("Id")
                with session.no_autoflush:
                    history = session.query(History).filter_by(salesforce_id=sf_id).first()

                activity_date = parse_date(record.get("ActivityDate")) or datetime.now(timezone.utc)

                if not history:
                    history = History(volunteer_id=volunteer.id, activity_date=activity_date, history_type="note")
                    session.add(history)
                    created_count += 1
                else:
                    updated_count += 1

                # Update fields
                history.salesforce_id = sf_id
                history.summary = record.get("Subject", "")
                history.activity_status = record.get("Status", "")
                history.activity_date = activity_date

                # Clean description
                description = record.get("Description", "")
                if description:
                    import re

                    description = re.sub(r"<[^>]+>", "", description)
                    description = re.sub(r"\s+", " ", description).strip()
                    history.description = description

                # Map type
                sf_type = (record.get("Type", "") or "").lower()
                if sf_type == "email":
                    history.history_type = "activity"
                    history.activity_type = "Email"
                    history.email_message_id = sf_id
                elif sf_type in ["call"]:
                    history.history_type = "activity"
                    history.activity_type = "Call"
                elif sf_type in ["status_update"]:
                    history.history_type = "status_change"
                    history.activity_type = "Status Update"
                else:
                    history.history_type = "note"
                    history.activity_type = record.get("Type", "") or "Note"

                # Link event if present
                event = get_event_cached(record.get("WhatId"), session)
                if event:
                    history.event_id = event.id
                    linked_events += 1

                return True
            except Exception as e:
                print(f"Error processing Task {record.get('Id', 'unknown')}: {str(e)}")
                return False

        def progress_callback(processed, total, message):
            if processed % 1000 == 0 and processed > 0:
                pct = (processed / max(total, 1)) * 100
                print(f"Progress: {processed:,}/{total:,} history ({pct:.1f}%) - {message}")

        result = importer.import_data(
            query=task_query,
            process_func=process_history_record_optimized,
            validation_func=validate_history_record,
            progress_callback=progress_callback,
        )

        return jsonify(
            {
                "success": result.success,
                "message": (
                    f"Created {created_count:,}, Updated {updated_count:,}, "
                    f"Linked Events {linked_events:,}, Skipped (no volunteer) {skipped_no_volunteer:,}, "
                    f"Errors {result.error_count:,}"
                ),
                "statistics": {
                    "total_records": result.total_records,
                    "processed_count": result.processed_count,
                    "success_count": result.success_count,
                    "error_count": result.error_count,
                    "skipped_count": result.skipped_count,
                    "duration_seconds": result.duration_seconds,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "skipped_no_volunteer": skipped_no_volunteer,
                    "linked_events": linked_events,
                },
                "errors": result.errors[:10],
                "warnings": result.warnings[:10],
            }
        )

    except SalesforceAuthenticationFailed:
        return jsonify({"success": False, "message": "Failed to authenticate with Salesforce"}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
