"""
Salesforce Event Import Routes
==============================

This module handles the Salesforce data import functionality for events
and event participation (both volunteer and student).

Routes:
- /events/import-from-salesforce: Import events and volunteer participants
- /events/sync-student-participants: Sync student participation data

Processing logic has been extracted to services.salesforce.processors.event
to keep routes as thin HTTP handlers.
"""

import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation, EventType
from models.school_model import School
from models.student import Student
from models.sync_log import SyncLog, SyncStatus
from models.volunteer import EventParticipation, Skill, Volunteer
from routes.decorators import global_users_only
from routes.utils import (
    DISTRICT_MAPPINGS,
    map_cancellation_reason,
    map_event_format,
    map_session_type,
    parse_date,
    parse_event_skills,
)
from services.salesforce import get_salesforce_client, safe_query_all
from services.salesforce.processors.event import (
    fix_missing_participation_records,
    process_event_row,
    process_participation_row,
    process_student_participation_row,
)
from services.salesforce.utils import safe_parse_delivery_hours
from utils.cache_refresh_scheduler import refresh_all_caches

# Create Blueprint for Salesforce event import routes
sf_event_import_bp = Blueprint("sf_event_import", __name__)


# =============================================================================
# ROUTE HANDLERS
# =============================================================================
# Processing functions (process_event_row, process_participation_row, etc.)
# are now imported from services.salesforce.processors.event above.


@sf_event_import_bp.route("/events/import-from-salesforce", methods=["POST"])
@login_required
@global_users_only
def import_events_from_salesforce():
    """
    Import events and participants from Salesforce

    This endpoint performs a comprehensive import of both events and
    participant data from Salesforce. It handles authentication, data
    processing, and error reporting.

    Returns:
        JSON response with import results and statistics
    """
    try:
        started_at = datetime.now(timezone.utc)

        # Delta sync support
        from services.salesforce import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("events")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching records modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Fetching data from Salesforce (FULL SYNC)...")

        success_count = 0
        error_count = 0
        errors = []
        skipped_count = 0

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

        # First query: Get events
        events_query = """
        SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c,
            End_Date_and_Time__c, Session_Status__c, Location_Information__c,
            Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c,
            District__c, School__c, Legacy_Skill_Covered_for_the_Session__c,
            Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
            Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c,
            Session_Host__c, LastModifiedDate
        FROM Session__c
        WHERE Session_Status__c != 'Draft' AND Session_Type__c != 'Connector Session'
        """

        if is_delta and watermark:
            events_query += delta_helper.build_date_filter(watermark)

        events_query += " ORDER BY Start_Date_and_Time__c DESC"

        events_result = safe_query_all(sf, events_query)
        events_rows = events_result.get("records", [])
        total_events = len(events_rows)

        print(f"Found {total_events} events in Salesforce")

        status_counts = {}
        type_counts = {}

        for i, row in enumerate(events_rows):
            if i > 0 and i % 500 == 0:
                print(f"Progress: {i}/{total_events} events processed")

            status = row.get("Session_Status__c", "Unknown")
            session_type = row.get("Session_Type__c", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[session_type] = type_counts.get(session_type, 0) + 1

            success_count, error_count, skipped_count = process_event_row(
                row, success_count, error_count, errors, skipped_count
            )

            # Batch commit every 100 events for resumability
            if (i + 1) % 100 == 0:
                try:
                    db.session.commit()
                    print(f"  → Committed events batch {(i+1) // 100}")
                except Exception as batch_e:
                    db.session.rollback()
                    print(f"  → Events batch commit failed: {batch_e}")

        # Print status summary
        print(f"\n{'='*60}")
        print(f"EVENTS IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Total from Salesforce: {total_events}")
        print(f"Successfully processed: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Skipped (invalid): {skipped_count}")

        # Second query: Get participants
        participants_query = """
        SELECT
            Id,
            Name,
            Contact__c,
            Session__c,
            Status__c,
            Delivery_Hours__c,
            Age_Group__c,
            Email__c,
            Title__c,
            LastModifiedDate
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Volunteer'
        """

        if is_delta and watermark:
            participants_query += delta_helper.build_date_filter(watermark)

        participants_result = safe_query_all(sf, participants_query)
        participant_rows = participants_result.get("records", [])

        participant_success = 0
        participant_error = 0
        for row in participant_rows:
            participant_success, participant_error = process_participation_row(
                row, participant_success, participant_error, errors
            )

        db.session.commit()

        # Final summary
        print(f"\n{'='*60}")
        print(f"FINAL IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Events: {success_count}/{total_events} processed successfully")
        print(
            f"Participants: {participant_success}/{len(participant_rows)} processed successfully"
        )
        print(f"Total errors: {error_count + participant_error}")
        print(f"{'='*60}")

        actual_errors = [e for e in errors if "Error processing" in e]
        skipped_events = [e for e in errors if "Skipping event" in e]

        # Trigger cache refresh if any data was processed
        if success_count > 0 or participant_success > 0:
            print(f"\nData updated. Triggering full cache refresh...")
            try:
                refresh_all_caches()
                print("Cache refresh triggered successfully.")
            except Exception as e:
                print(f"Warning: Cache refresh failed: {e}")

        # Record sync log
        try:
            sync_status = SyncStatus.SUCCESS.value
            if error_count + participant_error > 0:
                if success_count + participant_success > 0:
                    sync_status = SyncStatus.PARTIAL.value
                else:
                    sync_status = SyncStatus.FAILED.value

            sync_log = SyncLog(
                sync_type="events",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=success_count + participant_success,
                records_failed=error_count + participant_error,
                records_skipped=skipped_count,
                error_details=(
                    json.dumps(actual_errors[:100]) if actual_errors else None
                ),
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
        except Exception as e:
            print(f"Warning: Failed to record sync log: {e}")

        return jsonify(
            {
                "success": True,
                "message": f"Import completed successfully",
                "processed_count": success_count + participant_success,
                "error_count": error_count + participant_error,
                "skipped_count": skipped_count,
                "events_processed": success_count,
                "events_skipped": skipped_count,
                "participants_processed": participant_success,
                "total_events_from_salesforce": total_events,
                "total_participants_from_salesforce": len(participant_rows),
                "errors": actual_errors[:50],
                "skipped_events": skipped_events[:50],
            }
        )

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        _record_failure_sync_log(
            "events",
            started_at if "started_at" in locals() else datetime.now(timezone.utc),
            "Failed to authenticate with Salesforce",
        )
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        _record_failure_sync_log(
            "events",
            started_at if "started_at" in locals() else datetime.now(timezone.utc),
            str(e),
        )
        return jsonify({"success": False, "error": str(e)}), 500


@sf_event_import_bp.route("/events/sync-student-participants", methods=["POST"])
@login_required
@global_users_only
def sync_student_participants():
    """
    Sync student participation data from Salesforce

    This endpoint fetches student participation data from Salesforce and
    creates EventStudentParticipation records in the local database.

    Returns:
        JSON response with sync results and statistics
    """
    try:
        started_at = datetime.now(timezone.utc)

        # Delta sync support
        from services.salesforce import DeltaSyncHelper

        delta_helper = DeltaSyncHelper("student_participants")
        delta_info = delta_helper.get_delta_info(request.args)
        is_delta = delta_info["actual_delta"]
        watermark = delta_info["watermark"]

        if delta_info["requested_delta"]:
            if is_delta:
                print(
                    f"DELTA SYNC: Only fetching student participations modified after {delta_info['watermark_formatted']}"
                )
            else:
                print(
                    "DELTA SYNC requested but no previous watermark found - performing FULL SYNC"
                )
        else:
            print("Fetching student participation data from Salesforce (FULL SYNC)...")

        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce using centralized client with retry
        sf = get_salesforce_client()

        participants_query = """
        SELECT
            Id,
            Name,
            Contact__c,
            Session__c,
            Status__c,
            Delivery_Hours__c,
            Age_Group__c,
            Email__c,
            Title__c,
            LastModifiedDate
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Student'
        """

        if is_delta and watermark:
            participants_query += delta_helper.build_date_filter(watermark)

        participants_query += " ORDER BY Session__c, Name"

        participants_result = safe_query_all(sf, participants_query)
        participant_rows = participants_result.get("records", [])

        print(
            f"Found {len(participant_rows)} student participation records in Salesforce."
        )

        total_count = len(participant_rows)

        # OPTIMIZED: Pre-load lightweight ID-only caches (reduces memory usage)
        # Instead of loading full ORM objects, we only load the IDs we need for lookups
        print("Pre-loading lightweight lookup caches...")

        # Map: salesforce_id -> event_id (int)
        events_cache = {
            sf_id: event_id
            for event_id, sf_id in db.session.query(Event.id, Event.salesforce_id)
            .filter(Event.salesforce_id.isnot(None))
            .all()
        }

        # Map: salesforce_individual_id -> student_id (int)
        students_cache = {
            sf_id: student_id
            for student_id, sf_id in db.session.query(
                Student.id, Student.salesforce_individual_id
            )
            .filter(Student.salesforce_individual_id.isnot(None))
            .all()
        }

        # Set of existing salesforce_ids for O(1) duplicate check
        participations_by_sf_id = set(
            sf_id
            for (sf_id,) in db.session.query(EventStudentParticipation.salesforce_id)
            .filter(EventStudentParticipation.salesforce_id.isnot(None))
            .all()
        )

        # Set of existing (event_id, student_id) pairs for O(1) duplicate check
        participations_by_pair = set(
            db.session.query(
                EventStudentParticipation.event_id, EventStudentParticipation.student_id
            ).all()
        )

        print(
            f"  → Cached {len(events_cache)} events, {len(students_cache)} students, "
            f"{len(participations_by_sf_id)} participation SF IDs, {len(participations_by_pair)} pairs"
        )

        for i, row in enumerate(participant_rows):
            success_count, error_count = process_student_participation_row(
                row,
                success_count,
                error_count,
                errors,
                events_cache=events_cache,
                students_cache=students_cache,
                participations_by_sf_id=participations_by_sf_id,
                participations_by_pair=participations_by_pair,
            )

            # Batch commit every 100 records for resumability
            if (i + 1) % 100 == 0:
                try:
                    db.session.commit()
                    # Progress logging with percentage for large imports
                    if total_count >= 500:
                        pct = (i + 1) * 100 // total_count
                        print(f"  → Batch {(i+1) // 100}: {i+1}/{total_count} ({pct}%)")
                    else:
                        print(
                            f"  → Committed student participations batch {(i+1) // 100}"
                        )
                except Exception as batch_e:
                    db.session.rollback()
                    print(f"  → Batch commit failed: {batch_e}")

        # Final commit for remaining records
        db.session.commit()

        print(
            f"\nSuccessfully processed {success_count} student participations with {error_count} total errors"
        )
        if errors:
            print("\nErrors encountered:")
            for error in errors[:10]:
                print(f"- {error}")
            if len(errors) > 10:
                print(f"... and {len(errors) - 10} more errors")

        # Record sync log
        try:
            sync_status = SyncStatus.SUCCESS.value
            if error_count > 0:
                if success_count > 0:
                    sync_status = SyncStatus.PARTIAL.value
                else:
                    sync_status = SyncStatus.FAILED.value

            sync_log = SyncLog(
                sync_type="student_participations",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=success_count,
                records_failed=error_count,
                error_details=json.dumps(errors[:100]) if errors else None,
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
        except Exception as e:
            print(f"Warning: Failed to record sync log: {e}")

        return jsonify(
            {
                "success": True,
                "message": f"Processed {success_count} student participations with {error_count} errors.",
                "processed_count": success_count,
                "error_count": error_count,
                "successCount": success_count,
                "errorCount": error_count,
                "errors": errors,
            }
        )

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        _record_failure_sync_log(
            "student_participants",
            started_at if "started_at" in locals() else datetime.now(timezone.utc),
            "Failed to authenticate with Salesforce",
        )
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        print(f"Error in sync_student_participants: {str(e)}")
        _record_failure_sync_log(
            "student_participants",
            started_at if "started_at" in locals() else datetime.now(timezone.utc),
            str(e),
        )
        return jsonify({"success": False, "error": str(e)}), 500


def _record_failure_sync_log(sync_type, started_at, error_message):
    """Helper to record a failed sync log entry."""
    try:
        sync_log = SyncLog(
            sync_type=sync_type,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            status=SyncStatus.FAILED.value,
            error_message=error_message,
        )
        db.session.add(sync_log)
        db.session.commit()
    except Exception as log_e:
        print(f"Warning: Failed to record error sync log: {log_e}")
