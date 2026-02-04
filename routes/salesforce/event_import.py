"""
Salesforce Event Import Routes
==============================

This module handles the Salesforce data import functionality for events
and event participation (both volunteer and student). Extracted from
routes/events/routes.py to consolidate all Salesforce import routes in
one location.

Routes:
- /events/import-from-salesforce: Import events and volunteer participants
- /events/sync-student-participants: Sync student participation data

Helper Functions:
- safe_parse_delivery_hours: Parse delivery hours from Salesforce
- process_event_row: Process individual event records
- process_participation_row: Process volunteer participation records
- process_student_participation_row: Process student participation records
- fix_missing_participation_records: Fix missing EventParticipation records
"""

import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

from config import Config
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
from utils.cache_refresh_scheduler import refresh_all_caches

# Create Blueprint for Salesforce event import routes
event_import_bp = Blueprint("event_import", __name__)


def safe_parse_delivery_hours(value):
    """
    Safely parse delivery hours from Salesforce data

    Args:
        value: Raw value from Salesforce Delivery_Hours__c field

    Returns:
        float or None: Parsed hours value or None if invalid
    """
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    try:
        hours = float(value)
        return hours if hours > 0 else None
    except (ValueError, TypeError):
        return None


def process_event_row(row, success_count, error_count, errors, skipped_count):
    """
    Process a single event row from Salesforce data

    This function handles the processing of individual event records from
    Salesforce API responses. It validates required fields, creates or updates
    Event objects, and handles relationships with districts, schools, and skills.

    Args:
        row (dict): Event data from Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages
        skipped_count (int): Running count of skipped events (already exist)

    Returns:
        tuple: Updated (success_count, error_count, skipped_count)
    """
    try:
        parent_account = row.get("Parent_Account__c")
        district_name = row.get("District__c")
        school_id = row.get("School__c")
        event_name = row.get("Name", "").strip()
        session_type = row.get("Session_Type__c", "")

        if not event_name:
            event_id = row.get("Id", "unknown")
            errors.append(
                f"Skipping event {event_id}: Missing event name/title (required field)"
            )
            return success_count, error_count + 1, skipped_count

        event_id = row.get("Id")
        event = Event.query.filter_by(salesforce_id=event_id).first()

        if not event:
            event = Event(
                title=event_name,
                salesforce_id=event_id,
            )
            db.session.add(event)

        # Update event fields
        event.title = event_name
        event.type = map_session_type(session_type)
        event.format = map_event_format(row.get("Format__c", ""))
        event.start_date = parse_date(row.get("Start_Date_and_Time__c")) or datetime(
            2000, 1, 1
        )
        event.end_date = parse_date(row.get("End_Date_and_Time__c")) or datetime(
            2000, 1, 1
        )
        event.status = row.get("Session_Status__c", "Draft")
        event.location = row.get("Location_Information__c", "")
        event.description = row.get("Description__c", "")
        event.cancellation_reason = map_cancellation_reason(
            row.get("Cancellation_Reason__c")
        )
        event.participant_count = int(
            float(row.get("Non_Scheduled_Students_Count__c", 0))
            if row.get("Non_Scheduled_Students_Count__c") is not None
            else 0
        )
        event.additional_information = row.get("Additional_Information__c", "")
        event.session_host = row.get("Session_Host__c", "")

        # Handle numeric fields with constraint protection
        def safe_convert_to_int(value, default=0):
            if value is None:
                return default
            try:
                converted = int(float(value))
                return max(0, converted)
            except (ValueError, TypeError):
                return default

        event.total_requested_volunteer_jobs = safe_convert_to_int(
            row.get("Total_Requested_Volunteer_Jobs__c")
        )
        event.available_slots = safe_convert_to_int(row.get("Available_Slots__c"))

        # Handle School relationship
        school_district = None
        if school_id:
            school = School.query.get(school_id)
            if school:
                event.school = school_id
                school_district = school.district

        # Handle District relationship
        if not district_name and parent_account:
            district_name = parent_account

        district = None
        if district_name and district_name in DISTRICT_MAPPINGS:
            mapped_name = DISTRICT_MAPPINGS[district_name]
            district = District.query.filter_by(name=mapped_name).first()

        if district or school_district:
            event.districts = []
            if school_district:
                event.districts.append(school_district)
            if district and district not in event.districts:
                event.districts.append(district)

        event.district_partner = district_name if district_name else None

        # Handle skills
        skills_covered = parse_event_skills(
            row.get("Legacy_Skill_Covered_for_the_Session__c", "")
        )
        skills_needed = parse_event_skills(row.get("Legacy_Skills_Needed__c", ""))
        requested_skills = parse_event_skills(row.get("Requested_Skills__c", ""))
        all_skills = set(skills_covered + skills_needed + requested_skills)

        existing_skill_names = {skill.name for skill in event.skills}
        new_skill_names = all_skills - existing_skill_names

        for skill_name in new_skill_names:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.session.add(skill)
            if skill not in event.skills:
                event.skills.append(skill)

        db.session.flush()
        return success_count + 1, error_count, skipped_count

    except Exception as e:
        db.session.rollback()
        errors.append(f"Error processing event {row.get('Id', 'unknown')}: {str(e)}")
        return success_count, error_count + 1, skipped_count


def process_participation_row(row, success_count, error_count, errors):
    """
    Process a single participation row from Salesforce data

    This function handles volunteer participation records from Salesforce
    sync operations. It creates EventParticipation records linking
    volunteers to events with status and delivery hours.

    Args:
        row (dict): Participation data from Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages

    Returns:
        tuple: Updated (success_count, error_count)
    """
    try:
        existing = EventParticipation.query.filter_by(salesforce_id=row["Id"]).first()
        if existing:
            existing.status = row["Status__c"]
            existing.delivery_hours = safe_parse_delivery_hours(
                row.get("Delivery_Hours__c")
            )
            if row.get("Email__c"):
                existing.email = row["Email__c"]
            if row.get("Title__c"):
                existing.title = row["Title__c"]
            if row.get("Age_Group__c"):
                existing.age_group = row["Age_Group__c"]
            return success_count + 1, error_count

        volunteer = Volunteer.query.filter_by(
            salesforce_individual_id=row["Contact__c"]
        ).first()
        event = Event.query.filter_by(salesforce_id=row["Session__c"]).first()

        if not volunteer or not event:
            error_msg = (
                f"Could not find volunteer or event for participation {row['Id']}"
            )
            errors.append(error_msg)
            return success_count, error_count + 1

        participation = EventParticipation(
            volunteer_id=volunteer.id,
            event_id=event.id,
            status=row["Status__c"],
            delivery_hours=safe_parse_delivery_hours(row.get("Delivery_Hours__c")),
            salesforce_id=row["Id"],
        )

        db.session.add(participation)
        return success_count + 1, error_count

    except Exception as e:
        error_msg = f"Error processing participation row: {str(e)}"
        print(error_msg)
        db.session.rollback()
        errors.append(error_msg)
        return success_count, error_count + 1


def process_student_participation_row(row, success_count, error_count, errors):
    """
    Process a single student participation row from Salesforce data

    This function handles student participation records from Salesforce sync
    operations. It creates EventStudentParticipation records linking students
    to events with status, delivery hours, and age group information.

    Args:
        row (dict): Student participation data from Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages

    Returns:
        tuple: Updated (success_count, error_count)
    """
    try:
        event_sf_id = row.get("Session__c")
        student_contact_sf_id = row.get("Contact__c")
        participation_sf_id = row.get("Id")
        status = row.get("Status__c")
        delivery_hours_str = row.get("Delivery_Hours__c")
        age_group = row.get("Age_Group__c")

        if not all([event_sf_id, student_contact_sf_id, participation_sf_id]):
            errors.append(
                f"Skipping student participation {participation_sf_id or 'unknown'}: Missing required Salesforce IDs"
            )
            return success_count, error_count + 1

        event = Event.query.filter_by(salesforce_id=event_sf_id).first()
        if not event:
            errors.append(
                f"Event with Salesforce ID {event_sf_id} not found for participation {participation_sf_id}"
            )
            return success_count, error_count + 1

        student = Student.query.filter(
            Student.salesforce_individual_id == student_contact_sf_id
        ).first()
        if not student:
            errors.append(
                f"Student with Salesforce Contact ID {student_contact_sf_id} not found for participation {participation_sf_id}"
            )
            return success_count, error_count + 1

        existing_participation = EventStudentParticipation.query.filter_by(
            salesforce_id=participation_sf_id
        ).first()

        if existing_participation:
            return success_count, error_count

        pair_participation = EventStudentParticipation.query.filter_by(
            event_id=event.id, student_id=student.id
        ).first()

        delivery_hours = safe_parse_delivery_hours(delivery_hours_str)

        if pair_participation:
            if not pair_participation.salesforce_id:
                pair_participation.salesforce_id = participation_sf_id
            if status:
                pair_participation.status = status
            if delivery_hours is not None:
                pair_participation.delivery_hours = delivery_hours
            if age_group:
                pair_participation.age_group = age_group
            return success_count + 1, error_count

        new_participation = EventStudentParticipation(
            event_id=event.id,
            student_id=student.id,
            status=status,
            delivery_hours=delivery_hours,
            age_group=age_group,
            salesforce_id=participation_sf_id,
        )
        db.session.add(new_participation)
        db.session.commit()
        return success_count + 1, error_count

    except Exception as e:
        db.session.rollback()
        errors.append(
            f"Error processing student participation {row.get('Id', 'unknown')}: {str(e)}"
        )
        return success_count, error_count + 1


def fix_missing_participation_records(event):
    """
    Fix missing EventParticipation records for volunteers linked to an event.

    This function ensures that all volunteers linked to an event through the
    many-to-many relationship have proper EventParticipation records with
    appropriate delivery hours.

    Args:
        event: Event object to fix participation records for
    """
    event_volunteers = event.volunteers

    for volunteer in event_volunteers:
        participation = EventParticipation.query.filter_by(
            event_id=event.id, volunteer_id=volunteer.id
        ).first()

        if not participation:
            delivery_hours = None
            if event.duration:
                delivery_hours = event.duration / 60
            elif event.start_date and event.end_date:
                duration_minutes = (
                    event.end_date - event.start_date
                ).total_seconds() / 60
                delivery_hours = max(1.0, duration_minutes / 60)
            else:
                delivery_hours = 0.0

            status = "Attended"
            if event.status == EventStatus.COMPLETED:
                status = "Completed"
            elif event.status == EventStatus.CANCELLED:
                status = "Cancelled"
            elif event.status == EventStatus.NO_SHOW:
                status = "No Show"

            participation = EventParticipation(
                volunteer_id=volunteer.id,
                event_id=event.id,
                status=status,
                delivery_hours=delivery_hours,
                participant_type="Volunteer",
            )
            db.session.add(participation)
            print(
                f"Created missing participation record for volunteer {volunteer.first_name} {volunteer.last_name} in event {event.title}"
            )

        elif participation.delivery_hours is None:
            if event.duration:
                participation.delivery_hours = event.duration / 60
            elif event.start_date and event.end_date:
                duration_minutes = (
                    event.end_date - event.start_date
                ).total_seconds() / 60
                participation.delivery_hours = max(1.0, duration_minutes / 60)
            else:
                participation.delivery_hours = 0.0
            print(
                f"Fixed delivery hours for volunteer {volunteer.first_name} {volunteer.last_name} in event {event.title}"
            )

    try:
        db.session.commit()
        print(f"Successfully fixed participation records for event: {event.title}")
    except Exception as e:
        db.session.rollback()
        print(f"Error fixing participation records: {str(e)}")


@event_import_bp.route("/events/import-from-salesforce", methods=["POST"])
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
        from services.delta_sync_service import DeltaSyncHelper

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

        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

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

        events_result = sf.query_all(events_query)
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

        participants_result = sf.query_all(participants_query)
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


@event_import_bp.route("/events/sync-student-participants", methods=["POST"])
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
        from services.delta_sync_service import DeltaSyncHelper

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

        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

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

        participants_result = sf.query_all(participants_query)
        participant_rows = participants_result.get("records", [])

        print(
            f"Found {len(participant_rows)} student participation records in Salesforce."
        )

        for row in participant_rows:
            success_count, error_count = process_student_participation_row(
                row, success_count, error_count, errors
            )

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
