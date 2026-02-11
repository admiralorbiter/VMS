"""
Pathway Events Import
====================

This module provides functionality for syncing unaffiliated events from Salesforce
and associating them with districts based on student participation data.

This was refactored from routes/events/pathway_events.py to consolidate all
Salesforce import operations under routes/salesforce.

Key Features:
- Syncs events missing School, District, and Parent Account associations
- Associates events with districts based on participating students' school districts
- Syncs volunteer and student participation data for processed events
- Uses lightweight ID-only caches for memory efficiency
- Provides detailed error reporting and success statistics
"""

import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_login import login_required
from simple_salesforce import SalesforceAuthenticationFailed
from sqlalchemy.orm import selectinload

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation
from models.school_model import School
from models.student import Student
from models.sync_log import SyncLog, SyncStatus
from models.volunteer import EventParticipation, Skill, Volunteer
from routes.decorators import global_users_only
from routes.salesforce.event_import import safe_parse_delivery_hours
from routes.utils import (
    map_cancellation_reason,
    map_event_format,
    map_session_type,
    parse_date,
    parse_event_skills,
)
from services.salesforce import get_salesforce_client, safe_query_all
from services.salesforce.errors import ImportErrorCode, create_import_error

# Blueprint for pathway events import functionality
sf_pathway_import_bp = Blueprint(
    "sf_pathway_import", __name__, url_prefix="/pathway-events"
)


def _create_event_from_salesforce(sf_event_data, event_districts):
    """
    Creates and returns a new Event object from Salesforce data.
    Does not commit to database.

    Args:
        sf_event_data (dict): Raw Salesforce event data from API
        event_districts (set): Set of District objects to associate with the event

    Returns:
        Event: Newly created Event object (not yet committed)

    Raises:
        ValueError: If required Salesforce ID is missing
    """
    event_sf_id = sf_event_data.get("Id")
    if not event_sf_id:
        raise ValueError("Salesforce event data missing 'Id'")

    # Create new event with basic information
    new_event = Event(
        salesforce_id=event_sf_id,
        title=sf_event_data.get("Name", "").strip() or f"Untitled Event {event_sf_id}",
    )

    # Map Salesforce fields to Event model fields
    new_event.type = map_session_type(sf_event_data.get("Session_Type__c", ""))
    new_event.format = map_event_format(sf_event_data.get("Format__c", ""))
    new_event.start_date = parse_date(
        sf_event_data.get("Start_Date_and_Time__c")
    ) or datetime(2000, 1, 1)
    new_event.end_date = parse_date(
        sf_event_data.get("End_Date_and_Time__c")
    ) or datetime(2000, 1, 1)

    # Handle status mapping with fallback to DRAFT
    raw_status = sf_event_data.get("Session_Status__c")
    try:
        new_event.status = EventStatus(raw_status) if raw_status else EventStatus.DRAFT
    except ValueError:
        print(
            f"Warning: Unknown status '{raw_status}' for event {event_sf_id}. Defaulting to DRAFT."
        )
        new_event.status = EventStatus.DRAFT

    # Map additional fields
    new_event.location = sf_event_data.get("Location_Information__c", "")
    new_event.description = sf_event_data.get("Description__c", "")
    new_event.cancellation_reason = map_cancellation_reason(
        sf_event_data.get("Cancellation_Reason__c")
    )
    new_event.participant_count = int(
        float(sf_event_data.get("Non_Scheduled_Students_Count__c", 0))
        if sf_event_data.get("Non_Scheduled_Students_Count__c") is not None
        else 0
    )
    new_event.additional_information = sf_event_data.get(
        "Additional_Information__c", ""
    )
    new_event.session_host = sf_event_data.get("Session_Host__c", "")

    # Helper function for safe integer conversion
    def safe_convert_to_int(value, default=0):
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    new_event.total_requested_volunteer_jobs = safe_convert_to_int(
        sf_event_data.get("Total_Requested_Volunteer_Jobs__c")
    )
    new_event.available_slots = safe_convert_to_int(
        sf_event_data.get("Available_Slots__c")
    )

    # Assign districts
    new_event.districts = list(event_districts)

    # Handle Skills
    skills_covered = parse_event_skills(
        sf_event_data.get("Legacy_Skill_Covered_for_the_Session__c", "")
    )
    skills_needed = parse_event_skills(sf_event_data.get("Legacy_Skills_Needed__c", ""))
    requested_skills = parse_event_skills(sf_event_data.get("Requested_Skills__c", ""))
    all_skill_names = set(skills_covered + skills_needed + requested_skills)

    for skill_name in all_skill_names:
        skill = db.session.query(Skill).filter(Skill.name == skill_name).first()
        if not skill:
            skill = Skill(name=skill_name)
            db.session.add(skill)
        if skill not in new_event.skills:
            new_event.skills.append(skill)

    return new_event


def _process_volunteer_participation_row(
    row,
    success_count,
    error_count,
    errors,
    events_cache,
    volunteers_cache,
    participations_cache,
):
    """
    Process a single volunteer participation row with lightweight caches.

    Args:
        row: Salesforce participation record
        success_count: Running success count
        error_count: Running error count
        errors: List to append errors to
        events_cache: dict[salesforce_id -> event_id]
        volunteers_cache: dict[salesforce_individual_id -> volunteer_id]
        participations_cache: set of salesforce_ids already processed

    Returns:
        tuple: (success_count, error_count)
    """
    try:
        participation_sf_id = row.get("Id")
        event_sf_id = row.get("Session__c")
        volunteer_sf_id = row.get("Contact__c")

        if not all([participation_sf_id, event_sf_id, volunteer_sf_id]):
            return success_count, error_count + 1

        # Skip if already processed
        if participation_sf_id in participations_cache:
            return success_count, error_count

        # Lookup event and volunteer IDs
        event_id = events_cache.get(event_sf_id)
        volunteer_id = volunteers_cache.get(volunteer_sf_id)

        if not event_id or not volunteer_id:
            return success_count, error_count + 1

        # Check if participation already exists
        existing = EventParticipation.query.filter_by(
            salesforce_id=participation_sf_id
        ).first()
        if existing:
            participations_cache.add(participation_sf_id)
            return success_count, error_count

        # Create new participation
        participation = EventParticipation(
            volunteer_id=volunteer_id,
            event_id=event_id,
            status=row.get("Status__c"),
            delivery_hours=safe_parse_delivery_hours(row.get("Delivery_Hours__c")),
            salesforce_id=participation_sf_id,
        )
        db.session.add(participation)
        participations_cache.add(participation_sf_id)

        return success_count + 1, error_count
    except Exception as e:
        import_error = create_import_error(
            code=ImportErrorCode.UNKNOWN,
            row=row,
            message=f"Error processing volunteer participation: {e}",
        )
        errors.append(import_error.to_dict())
        return success_count, error_count + 1


def _process_student_participation_row(
    row,
    success_count,
    error_count,
    errors,
    events_cache,
    students_cache,
    participations_by_sf_id,
    participations_by_pair,
):
    """
    Process a single student participation row with lightweight caches.

    Args:
        row: Salesforce participation record
        success_count: Running success count
        error_count: Running error count
        errors: List to append errors to
        events_cache: dict[salesforce_id -> event_id]
        students_cache: dict[salesforce_individual_id -> student_id]
        participations_by_sf_id: set of salesforce_ids already processed
        participations_by_pair: set of (event_id, student_id) pairs

    Returns:
        tuple: (success_count, error_count)
    """
    try:
        participation_sf_id = row.get("Id")
        event_sf_id = row.get("Session__c")
        student_sf_id = row.get("Contact__c")

        if not all([participation_sf_id, event_sf_id, student_sf_id]):
            return success_count, error_count + 1

        # Skip if already processed
        if participation_sf_id in participations_by_sf_id:
            return success_count, error_count

        # Lookup event and student IDs
        event_id = events_cache.get(event_sf_id)
        student_id = students_cache.get(student_sf_id)

        if not event_id or not student_id:
            return success_count, error_count + 1

        pair_key = (event_id, student_id)
        if pair_key in participations_by_pair:
            return success_count, error_count

        # Create new participation
        participation = EventStudentParticipation(
            event_id=event_id,
            student_id=student_id,
            status=row.get("Status__c"),
            delivery_hours=safe_parse_delivery_hours(row.get("Delivery_Hours__c")),
            age_group=row.get("Age_Group__c"),
            salesforce_id=participation_sf_id,
        )
        db.session.add(participation)

        # Update caches
        participations_by_sf_id.add(participation_sf_id)
        participations_by_pair.add(pair_key)

        return success_count + 1, error_count
    except Exception as e:
        import_error = create_import_error(
            code=ImportErrorCode.UNKNOWN,
            row=row,
            message=f"Error processing student participation: {e}",
        )
        errors.append(import_error.to_dict())
        return success_count, error_count + 1


@sf_pathway_import_bp.route("/sync-unaffiliated-events", methods=["POST"])
@login_required
@global_users_only
def sync_unaffiliated_events():
    """
    Fetches events from Salesforce that are missing School, District, and Parent Account.
    Attempts to associate these events with districts based on the districts of
    participating students found in the local database.

    This endpoint:
    1. Queries Salesforce for all student participants to build event-to-student mapping
    2. Queries Salesforce for unaffiliated events (missing school/district/parent account)
    3. Creates/updates events and assigns districts based on student participation
    4. Syncs volunteer and student participation data with lightweight caches

    Returns:
        JSON response with success status, counts, and error details
    """
    processed_count = 0
    updated_count = 0
    created_count = 0
    errors = []
    district_map_details = {}
    started_at = datetime.now(timezone.utc)

    try:
        print("Connecting to Salesforce...")
        sf = get_salesforce_client()
        print("Connected to Salesforce.")

        # Step 1: Query for ALL student participants
        all_participants_query = """
        SELECT Session__c, Contact__c
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Student' AND Contact__c != NULL
        """
        print("Querying ALL student participants from Salesforce...")
        all_participants_result = safe_query_all(sf, all_participants_query)
        all_participant_rows = all_participants_result.get("records", [])
        print(f"Found {len(all_participant_rows)} total student participation records.")

        # Build event -> student SF IDs map
        event_to_student_sf_ids = {}
        for row in all_participant_rows:
            event_id = row["Session__c"]
            student_contact_id = row["Contact__c"]
            if event_id and student_contact_id:
                if event_id not in event_to_student_sf_ids:
                    event_to_student_sf_ids[event_id] = set()
                event_to_student_sf_ids[event_id].add(student_contact_id)
        print(f"Built participation map for {len(event_to_student_sf_ids)} events.")

        # Step 2: Query for unaffiliated events in Salesforce
        unaffiliated_events_query = """
        SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c,
               End_Date_and_Time__c, Session_Status__c, Location_Information__c,
               Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c,
               District__c, School__c, Legacy_Skill_Covered_for_the_Session__c,
               Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
               Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c,
               Session_Host__c
        FROM Session__c
        WHERE School__c = NULL AND District__c = NULL AND Parent_Account__c = NULL
        ORDER BY CreatedDate DESC
        """
        print("Querying unaffiliated events from Salesforce...")
        events_result = safe_query_all(sf, unaffiliated_events_query)
        unaffiliated_events_data = events_result.get("records", [])
        print(f"Found {len(unaffiliated_events_data)} potentially unaffiliated events.")

        if not unaffiliated_events_data:
            return jsonify(
                {
                    "success": True,
                    "message": "No unaffiliated events found in Salesforce.",
                    "processed_count": 0,
                    "updated_count": 0,
                    "errors": [],
                }
            )

        # Step 3: Process each unaffiliated event
        total_events = len(unaffiliated_events_data)
        for i, sf_event_data in enumerate(unaffiliated_events_data):
            event_sf_id = sf_event_data["Id"]
            processed_count += 1

            try:
                local_event = Event.query.filter_by(salesforce_id=event_sf_id).first()

                if local_event:
                    # Update existing event
                    updated_fields = []

                    if (
                        sf_event_data.get("Name")
                        and sf_event_data.get("Name").strip() != local_event.title
                    ):
                        local_event.title = sf_event_data.get("Name").strip()
                        updated_fields.append("title")

                    if not local_event.districts:
                        student_sf_ids = event_to_student_sf_ids.get(event_sf_id)
                        if student_sf_ids:
                            local_students = (
                                db.session.query(Student)
                                .options(
                                    selectinload(Student.school).selectinload(
                                        School.district
                                    )
                                )
                                .filter(
                                    Student.salesforce_individual_id.in_(student_sf_ids)
                                )
                                .all()
                            )
                            event_districts = set()
                            for student in local_students:
                                if student.school and student.school.district:
                                    event_districts.add(student.school.district)
                            if event_districts:
                                local_event.districts = list(event_districts)
                                updated_fields.append("districts")
                                district_map_details[event_sf_id] = [
                                    d.name for d in event_districts
                                ]

                    if updated_fields:
                        db.session.add(local_event)
                        updated_count += 1
                else:
                    # Create new event
                    student_sf_ids = event_to_student_sf_ids.get(event_sf_id)
                    event_districts = set()

                    if student_sf_ids:
                        local_students = (
                            db.session.query(Student)
                            .options(
                                selectinload(Student.school).selectinload(
                                    School.district
                                )
                            )
                            .filter(
                                Student.salesforce_individual_id.in_(student_sf_ids)
                            )
                            .all()
                        )
                        for student in local_students:
                            if student.school and student.school.district:
                                event_districts.add(student.school.district)

                    new_event = _create_event_from_salesforce(
                        sf_event_data, event_districts
                    )
                    db.session.add(new_event)
                    db.session.flush()
                    created_count += 1

                    if event_districts:
                        district_map_details[event_sf_id] = [
                            d.name for d in event_districts
                        ]

                # Progress logging
                if (i + 1) % 50 == 0 and total_events >= 100:
                    pct = (i + 1) * 100 // total_events
                    print(f"  → Events: {i+1}/{total_events} ({pct}%)")

            except Exception as e:
                db.session.rollback()
                errors.append(
                    {
                        "code": "UNKNOWN",
                        "record_id": event_sf_id,
                        "record_name": "Event",
                        "message": str(e),
                    }
                )

        db.session.commit()
        print(f"Events processed: {created_count} created, {updated_count} updated")

        # Step 4: Pre-load lightweight caches for participation sync
        print("Pre-loading lightweight caches for participation sync...")

        events_cache = {
            sf_id: event_id
            for event_id, sf_id in db.session.query(Event.id, Event.salesforce_id)
            .filter(Event.salesforce_id.isnot(None))
            .all()
        }

        volunteers_cache = {
            sf_id: vol_id
            for vol_id, sf_id in db.session.query(
                Volunteer.id, Volunteer.salesforce_individual_id
            )
            .filter(Volunteer.salesforce_individual_id.isnot(None))
            .all()
        }

        students_cache = {
            sf_id: student_id
            for student_id, sf_id in db.session.query(
                Student.id, Student.salesforce_individual_id
            )
            .filter(Student.salesforce_individual_id.isnot(None))
            .all()
        }

        vol_participations_cache = set(
            sf_id
            for (sf_id,) in db.session.query(EventParticipation.salesforce_id)
            .filter(EventParticipation.salesforce_id.isnot(None))
            .all()
        )

        student_participations_by_sf_id = set(
            sf_id
            for (sf_id,) in db.session.query(EventStudentParticipation.salesforce_id)
            .filter(EventStudentParticipation.salesforce_id.isnot(None))
            .all()
        )

        student_participations_by_pair = set(
            db.session.query(
                EventStudentParticipation.event_id, EventStudentParticipation.student_id
            ).all()
        )

        print(
            f"  → Cached: {len(events_cache)} events, {len(volunteers_cache)} volunteers, {len(students_cache)} students"
        )

        # Step 5: Sync volunteer participants
        processed_event_sf_ids = [event["Id"] for event in unaffiliated_events_data]
        participant_success = 0
        participant_error = 0

        if processed_event_sf_ids:
            batch_size = 50
            for i in range(0, len(processed_event_sf_ids), batch_size):
                batch_sf_ids = processed_event_sf_ids[i : i + batch_size]
                safe_ids = ",".join(
                    [
                        f"'{sf_id}'"
                        for sf_id in batch_sf_ids
                        if re.fullmatch(r"[A-Za-z0-9]{15,18}", sf_id)
                    ]
                )

                if not safe_ids:
                    continue

                participants_query = f"""
                SELECT Id, Name, Contact__c, Session__c, Status__c, Delivery_Hours__c
                FROM Session_Participant__c
                WHERE Participant_Type__c = 'Volunteer' AND Session__c IN ({safe_ids})
                """

                try:
                    participants_result = sf.query_all(participants_query)
                    participant_rows = participants_result.get("records", [])

                    for row in participant_rows:
                        participant_success, participant_error = (
                            _process_volunteer_participation_row(
                                row,
                                participant_success,
                                participant_error,
                                errors,
                                events_cache,
                                volunteers_cache,
                                vol_participations_cache,
                            )
                        )
                except Exception as batch_error:
                    errors.append(
                        {
                            "code": "UNKNOWN",
                            "record_id": None,
                            "record_name": "Volunteer Batch",
                            "message": str(batch_error),
                        }
                    )

        # Step 6: Sync student participants
        student_success = 0
        student_error = 0

        if processed_event_sf_ids:
            batch_size = 50
            for i in range(0, len(processed_event_sf_ids), batch_size):
                batch_sf_ids = processed_event_sf_ids[i : i + batch_size]
                safe_ids = ",".join(
                    [
                        f"'{sf_id}'"
                        for sf_id in batch_sf_ids
                        if re.fullmatch(r"[A-Za-z0-9]{15,18}", sf_id)
                    ]
                )

                if not safe_ids:
                    continue

                student_query = f"""
                SELECT Id, Name, Contact__c, Session__c, Status__c, Delivery_Hours__c, Age_Group__c
                FROM Session_Participant__c
                WHERE Participant_Type__c = 'Student' AND Session__c IN ({safe_ids})
                """

                try:
                    student_result = sf.query_all(student_query)
                    student_rows = student_result.get("records", [])

                    for row in student_rows:
                        student_success, student_error = (
                            _process_student_participation_row(
                                row,
                                student_success,
                                student_error,
                                errors,
                                events_cache,
                                students_cache,
                                student_participations_by_sf_id,
                                student_participations_by_pair,
                            )
                        )
                except Exception as batch_error:
                    errors.append(
                        {
                            "code": "UNKNOWN",
                            "record_id": None,
                            "record_name": "Student Batch",
                            "message": str(batch_error),
                        }
                    )

        db.session.commit()
        print(
            f"Participations: {participant_success} volunteer, {student_success} student"
        )

        response = jsonify(
            {
                "success": True,
                "message": f"Processed {processed_count} events. Created: {created_count}, Updated: {updated_count}.",
                "processed_count": processed_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "volunteer_participations": participant_success,
                "student_participations": student_success,
                "error_count": len(errors),
                "district_map_details": district_map_details,
                "errors": errors[:50],
            }
        )

        # Record sync log for dashboard tracking
        try:
            total_success = (
                created_count + updated_count + participant_success + student_success
            )
            total_errors = len(errors)
            sync_status = SyncStatus.SUCCESS.value
            if total_errors > 0:
                sync_status = (
                    SyncStatus.PARTIAL.value
                    if total_success > 0
                    else SyncStatus.FAILED.value
                )

            sync_log = SyncLog(
                sync_type="unaffiliated_events",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=sync_status,
                records_processed=total_success,
                records_failed=total_errors,
                is_delta_sync=False,
            )
            db.session.add(sync_log)
            db.session.commit()
            print(f"Sync log recorded: {sync_status}")
        except Exception as log_e:
            print(f"Warning: Failed to record sync log: {log_e}")

        return response

    except SalesforceAuthenticationFailed:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Failed to authenticate with Salesforce.",
                    "error": "Salesforce Authentication Failed",
                }
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal Server Error",
                    "message": str(e),
                }
            ),
            500,
        )
