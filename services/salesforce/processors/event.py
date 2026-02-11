"""
Event Import Processors
=======================

Business logic for processing Salesforce event records during import.
Extracted from routes/salesforce/event_import.py to centralize import logic.

This module contains:
- process_event_row: Process individual event records
- process_participation_row: Process volunteer participation records
- process_student_participation_row: Process student participation records
- fix_missing_participation_records: Fix missing EventParticipation records

Usage:
    from services.salesforce.processors.event import (
        process_event_row,
        process_participation_row,
    )

    for row in salesforce_records:
        success, error, skipped = process_event_row(row, ...)
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation
from models.school_model import School
from models.student import Student
from models.volunteer import EventParticipation, Skill, Volunteer
from routes.utils import (
    DISTRICT_MAPPINGS,
    map_cancellation_reason,
    map_event_format,
    map_session_type,
    parse_date,
    parse_event_skills,
)
from services.salesforce.utils import safe_parse_delivery_hours


def process_event_row(
    row: dict,
    success_count: int,
    error_count: int,
    errors: List[str],
    skipped_count: int,
) -> Tuple[int, int, int]:
    """
    Process a single event row from Salesforce data.

    This function handles the processing of individual event records from
    Salesforce API responses. It validates required fields, creates or updates
    Event objects, and handles relationships with districts, schools, and skills.

    Args:
        row: Event data from Salesforce
        success_count: Running count of successful operations
        error_count: Running count of failed operations
        errors: List to collect error messages
        skipped_count: Running count of skipped events (already exist)

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


def process_participation_row(
    row: dict,
    success_count: int,
    error_count: int,
    errors: List[str],
) -> Tuple[int, int]:
    """
    Process a single volunteer participation row from Salesforce data.

    This function handles volunteer participation records from Salesforce
    sync operations. It creates EventParticipation records linking
    volunteers to events with status and delivery hours.

    Args:
        row: Participation data from Salesforce
        success_count: Running count of successful operations
        error_count: Running count of failed operations
        errors: List to collect error messages

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


def process_student_participation_row(
    row: dict,
    success_count: int,
    error_count: int,
    errors: List[str],
    events_cache: Optional[Dict[str, int]] = None,
    students_cache: Optional[Dict[str, int]] = None,
    participations_by_sf_id: Optional[Set[str]] = None,
    participations_by_pair: Optional[Set[Tuple[int, int]]] = None,
) -> Tuple[int, int]:
    """
    Process a single student participation row from Salesforce data.

    This function handles student participation records from Salesforce sync
    operations. It creates EventStudentParticipation records linking students
    to events with status, delivery hours, and age group information.

    OPTIMIZED: Uses lightweight ID-only caches to reduce memory usage.
    Caches are updated during processing to prevent duplicate inserts.

    Args:
        row: Student participation data from Salesforce
        success_count: Running count of successful operations
        error_count: Running count of failed operations
        errors: List to collect error messages
        events_cache: Maps salesforce_id -> event_id (int)
        students_cache: Maps salesforce_individual_id -> student_id (int)
        participations_by_sf_id: Set of existing participation salesforce_ids
        participations_by_pair: Set of existing (event_id, student_id) pairs

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

        # Use lightweight ID cache if available, otherwise fall back to DB query
        if events_cache is not None:
            event_id = events_cache.get(event_sf_id)
        else:
            event = Event.query.filter_by(salesforce_id=event_sf_id).first()
            event_id = event.id if event else None

        if not event_id:
            errors.append(
                f"Event with Salesforce ID {event_sf_id} not found for participation {participation_sf_id}"
            )
            return success_count, error_count + 1

        # Use lightweight ID cache if available, otherwise fall back to DB query
        if students_cache is not None:
            student_id = students_cache.get(student_contact_sf_id)
        else:
            student = Student.query.filter(
                Student.salesforce_individual_id == student_contact_sf_id
            ).first()
            student_id = student.id if student else None

        if not student_id:
            errors.append(
                f"Student with Salesforce Contact ID {student_contact_sf_id} not found for participation {participation_sf_id}"
            )
            return success_count, error_count + 1

        # Check for existing participation by SF ID (use set for O(1) lookup)
        if participations_by_sf_id is not None:
            if participation_sf_id in participations_by_sf_id:
                return success_count, error_count  # Already exists, skip
        else:
            existing_participation = EventStudentParticipation.query.filter_by(
                salesforce_id=participation_sf_id
            ).first()
            if existing_participation:
                return success_count, error_count

        # Check for existing participation by event+student pair (use set for O(1) lookup)
        pair_key = (event_id, student_id)
        if participations_by_pair is not None:
            if pair_key in participations_by_pair:
                # Update existing record with SF ID if missing
                existing = EventStudentParticipation.query.filter_by(
                    event_id=event_id, student_id=student_id
                ).first()
                if existing and not existing.salesforce_id:
                    existing.salesforce_id = participation_sf_id
                    (
                        participations_by_sf_id.add(participation_sf_id)
                        if participations_by_sf_id is not None
                        else None
                    )
                return success_count + 1, error_count
        else:
            pair_participation = EventStudentParticipation.query.filter_by(
                event_id=event_id, student_id=student_id
            ).first()
            if pair_participation:
                if not pair_participation.salesforce_id:
                    pair_participation.salesforce_id = participation_sf_id
                return success_count + 1, error_count

        delivery_hours = safe_parse_delivery_hours(delivery_hours_str)

        # Create new participation record
        new_participation = EventStudentParticipation(
            event_id=event_id,
            student_id=student_id,
            status=status,
            delivery_hours=delivery_hours,
            age_group=age_group,
            salesforce_id=participation_sf_id,
        )
        db.session.add(new_participation)

        # Update caches to prevent duplicates in same batch
        if participations_by_sf_id is not None:
            participations_by_sf_id.add(participation_sf_id)
        if participations_by_pair is not None:
            participations_by_pair.add(pair_key)

        return success_count + 1, error_count

    except Exception as e:
        db.session.rollback()
        errors.append(
            f"Error processing student participation {row.get('Id', 'unknown')}: {str(e)}"
        )
        return success_count, error_count + 1


def fix_missing_participation_records(event: Event) -> None:
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
    except Exception as e:
        db.session.rollback()
        print(f"Error committing participation fixes: {str(e)}")
