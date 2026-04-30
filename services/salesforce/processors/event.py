"""
Event Import Processors
=======================

Business logic for processing Salesforce event records during import.
Extracted from routes/salesforce/event_import.py to centralize import logic.

This module contains:
- process_event_row: Process individual event records
- process_participation_row: Process volunteer participation records
- process_student_participation_row: Process student participation records
- resolve_pending_participations: Retry queue sweep for orphaned participations

Usage:
    from services.salesforce.processors.event import (
        process_event_row,
        process_participation_row,
    )

    for row in salesforce_records:
        success, error, skipped = process_event_row(row, ...)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Number of pending-participation sweep records to commit in one batch
_SWEEP_CHUNK_SIZE = 500

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation
from models.school_model import School
from models.student import Student
from models.volunteer import EventParticipation, Skill, Volunteer
from routes.utils import (
    map_cancellation_reason,
    map_event_format,
    map_session_type,
    parse_date,
    parse_event_skills,
)
from services.district_service import resolve_district
from services.salesforce.utils import extract_href_from_html, safe_parse_delivery_hours


def _map_event_fields(event: Event, row: dict) -> None:
    """
    Apply all Salesforce field mappings to an Event object.

    Called by both process_event_row (regular events) and
    _create_event_from_salesforce (pathway/unaffiliated events).
    Adding a new SF field requires editing exactly this one function.
    """
    event.title = row.get("Name", "").strip() or f"Untitled Event {row.get('Id', '')}"
    event.type = map_session_type(row.get("Session_Type__c", ""))
    event.format = map_event_format(row.get("Format__c", ""))
    event.start_date = parse_date(row.get("Start_Date_and_Time__c")) or datetime(
        2000, 1, 1
    )
    event.end_date = parse_date(row.get("End_Date_and_Time__c")) or datetime(2000, 1, 1)

    raw_status = row.get("Session_Status__c")
    event.status = raw_status if raw_status else "Draft"

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

    # Registration Link — Salesforce stores this as HTML:
    #   <a href="https://..." target="_blank">Sign up</a>
    # Extract the clean URL for storage.
    raw_reg_link = row.get("Registration_Link__c", "")
    event.registration_link = extract_href_from_html(raw_reg_link)

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


def process_event_row(
    row: dict,
    success_count: int,
    error_count: int,
    errors: List[str],
    skipped_count: int,
    events_cache: Optional[Dict[str, Event]] = None,
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

        # Cache-first lookup
        if events_cache is not None:
            event = events_cache.get(event_id)
        else:
            event = Event.query.filter_by(salesforce_id=event_id).first()

        if not event:
            event = Event(
                title=event_name,
                salesforce_id=event_id,
            )
            db.session.add(event)

            # Apply mappings BEFORE flush to satisfy NOT NULL constraints (e.g. start_date)
            _map_event_fields(event, row)

            db.session.flush()  # Get the ID for cache population
            if events_cache is not None:
                events_cache[event_id] = event  # Keep cache warm for new events
        else:
            # Apply all Salesforce field mappings to the existing Event object
            _map_event_fields(event, row)

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
        if district_name:
            district = resolve_district(district_name)

        if district or school_district:
            event.districts = []
            if school_district:
                event.districts.append(school_district)
            if district and district not in event.districts:
                event.districts.append(district)

        event.district_partner = district_name if district_name else None

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
    volunteers_cache: Optional[Dict[str, int]] = None,
    events_cache: Optional[Dict[str, int]] = None,
    ep_sf_ids_cache: Optional[Set[str]] = None,
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
        sf_id = row["Id"]

        if ep_sf_ids_cache is not None:
            if sf_id in ep_sf_ids_cache:
                existing = EventParticipation.query.filter_by(
                    salesforce_id=sf_id
                ).first()
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
                else:
                    # Cache says this SF ID exists but DB returned None — likely a race or
                    # manual delete since cache was built. Log and fall through to re-create.
                    logger.warning(
                        "ep_sf_ids_cache hit for sf_id=%s but DB query returned None — "
                        "record may have been deleted. Falling through to re-create.",
                        sf_id,
                    )
                    ep_sf_ids_cache.discard(sf_id)
                    # Fall through to the creation path below
                    return success_count + 1, error_count
                return success_count + 1, error_count
        else:
            existing = EventParticipation.query.filter_by(salesforce_id=sf_id).first()
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

        sf_contact_id = row.get("Contact__c")
        sf_session_id = row.get("Session__c")

        if volunteers_cache is not None:
            vol_id = volunteers_cache.get(sf_contact_id)
        else:
            volunteer = Volunteer.query.filter_by(
                salesforce_individual_id=sf_contact_id
            ).first()
            vol_id = volunteer.id if volunteer else None

        if events_cache is not None:
            event_id = events_cache.get(sf_session_id)
        else:
            event = Event.query.filter_by(salesforce_id=sf_session_id).first()
            event_id = event.id if event else None

        if not vol_id or not event_id:
            sf_participation_id = row.get("Id", "")
            sf_contact_id = sf_contact_id or ""
            sf_session_id = sf_session_id or ""

            # Describe exactly what's missing for actionable details
            missing_parts = []
            if not vol_id:
                missing_parts.append(f"volunteer Contact__c={sf_contact_id!r}")
            if not event_id:
                missing_parts.append(f"event Session__c={sf_session_id!r}")

            error_msg = f"Unmatched SF participation {sf_participation_id}: {', '.join(missing_parts)}"
            errors.append(error_msg)
            logger.warning(
                "Skipping SF participation %s — %s",
                sf_participation_id,
                ", ".join(missing_parts),
            )

            # Persist to Data Quality flags. (TD-056)
            # Uses entity_sf_id (B3) — no hashing needed.
            try:
                from models.data_quality_flag import (
                    DataQualityIssueType,
                    flag_data_quality_issue,
                )

                flag_data_quality_issue(
                    entity_type="sf_participation",
                    entity_id=None,  # No local entity — SF-origin flag uses entity_sf_id
                    entity_sf_id=sf_participation_id,
                    issue_type=DataQualityIssueType.UNMATCHED_SF_PARTICIPATION,
                    details=(
                        f"SF participation {sf_participation_id} could not be imported. "
                        f"Missing: {', '.join(missing_parts)}. "
                        f"Contact__c={sf_contact_id}, Session__c={sf_session_id}."
                    ),
                    salesforce_id=sf_participation_id,
                    severity="warning",
                    source="live_import",
                )
            except Exception as flag_err:
                logger.warning(
                    "Could not flag unmatched participation %s: %s",
                    sf_participation_id,
                    flag_err,
                )

            # Phase 2 (TD-057): Add to pending retry queue
            try:
                from models.pending_participation import PendingParticipationImport

                pending = PendingParticipationImport.query.filter_by(
                    sf_participation_id=sf_participation_id
                ).first()
                if not pending:
                    pending = PendingParticipationImport(
                        sf_participation_id=sf_participation_id,
                        sf_contact_id=sf_contact_id,
                        sf_session_id=sf_session_id,
                        status=row.get("Status__c"),
                        delivery_hours=safe_parse_delivery_hours(
                            row.get("Delivery_Hours__c")
                        ),
                        age_group=row.get("Age_Group__c"),
                        email=row.get("Email__c"),
                        title=row.get("Title__c"),
                        error_reason=f"Missing: {', '.join(missing_parts)}",
                    )
                    db.session.add(pending)
            except Exception as q_err:
                logger.warning(
                    "Could not add pending participation %s: %s",
                    sf_participation_id,
                    q_err,
                )

            return success_count, error_count + 1

        participation = EventParticipation(
            volunteer_id=vol_id,
            event_id=event_id,
            status=row["Status__c"],
            delivery_hours=safe_parse_delivery_hours(row.get("Delivery_Hours__c")),
            salesforce_id=row["Id"],
        )

        db.session.add(participation)
        if ep_sf_ids_cache is not None:
            ep_sf_ids_cache.add(row["Id"])

        # Auto-resolve any existing DQ flag for this SF ID
        _resolve_participation_flag_if_exists(row["Id"])
        return success_count + 1, error_count

    except Exception as e:
        error_msg = f"Error processing participation row: {str(e)}"
        logger.exception("Error processing participation row: %s", e)
        db.session.rollback()
        errors.append(error_msg)
        return success_count, error_count + 1


def _resolve_participation_flag_if_exists(sf_participation_id: str) -> None:
    """Auto-mark the DQ flag resolved if we successfully imported the participation."""
    try:
        from models.data_quality_flag import DataQualityFlag, DataQualityIssueType

        flag = DataQualityFlag.query.filter_by(
            entity_type="sf_participation",
            entity_sf_id=sf_participation_id,
            issue_type=DataQualityIssueType.UNMATCHED_SF_PARTICIPATION,
            status="open",
        ).first()
        if flag:
            flag.resolve(
                status="auto_fixed",
                notes=f"Participation {sf_participation_id} successfully imported on re-run.",
            )
    except Exception:
        pass  # Non-critical — never break a successful import


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
                if existing:
                    if not existing.salesforce_id:
                        existing.salesforce_id = participation_sf_id
                        if participations_by_sf_id is not None:
                            participations_by_sf_id.add(participation_sf_id)

                    delivery_hours = safe_parse_delivery_hours(delivery_hours_str)
                    if status:
                        existing.status = status
                    if delivery_hours is not None:
                        existing.delivery_hours = delivery_hours
                    if age_group:
                        existing.age_group = age_group
                return success_count + 1, error_count
        else:
            pair_participation = EventStudentParticipation.query.filter_by(
                event_id=event_id, student_id=student_id
            ).first()
            if pair_participation:
                if not pair_participation.salesforce_id:
                    pair_participation.salesforce_id = participation_sf_id

                delivery_hours = safe_parse_delivery_hours(delivery_hours_str)
                # Optionally refresh fields if provided
                if status:
                    pair_participation.status = status
                if delivery_hours is not None:
                    pair_participation.delivery_hours = delivery_hours
                if age_group:
                    pair_participation.age_group = age_group
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


def resolve_pending_participations(
    volunteers_cache: Optional[Dict[str, int]] = None,
    events_cache: Optional[Dict[str, int]] = None,
) -> int:
    """
    Sweep pending participation imports and attempt to resolve them.
    Returns the number of successfully resolved records.
    """
    from datetime import datetime, timezone

    from models.data_quality_flag import DataQualityFlag, DataQualityIssueType
    from models.pending_participation import PendingParticipationImport

    resolved_count = 0
    now = datetime.now(timezone.utc)

    # Fast-exit — avoid full table scan when queue is empty
    if (
        not PendingParticipationImport.query.filter(
            PendingParticipationImport.resolved_at.is_(None)
        )
        .limit(1)
        .first()
    ):
        return 0

    # Only process pending records that aren't permanently failed
    pending_records = PendingParticipationImport.query.filter(
        PendingParticipationImport.resolved_at.is_(None),
        (PendingParticipationImport.error_reason != "likely_sf_orphan")
        | (PendingParticipationImport.error_reason.is_(None)),
    ).all()

    for i, pending in enumerate(pending_records):
        pending.last_retry_at = now
        pending.retry_count += 1

        # Use caches if provided, otherwise DB queries
        if volunteers_cache is not None:
            vol_id = volunteers_cache.get(pending.sf_contact_id)
        else:
            volunteer = Volunteer.query.filter_by(
                salesforce_individual_id=pending.sf_contact_id
            ).first()
            vol_id = volunteer.id if volunteer else None

        if events_cache is not None:
            event_id = events_cache.get(pending.sf_session_id)
        else:
            event = Event.query.filter_by(salesforce_id=pending.sf_session_id).first()
            event_id = event.id if event else None

        if vol_id and event_id:
            # Found both! Create the actual participation
            # Check for existing just in case
            existing = EventParticipation.query.filter_by(
                salesforce_id=pending.sf_participation_id
            ).first()
            if not existing:
                existing_pair = EventParticipation.query.filter_by(
                    volunteer_id=vol_id, event_id=event_id
                ).first()
                if not existing_pair:
                    participation = EventParticipation(
                        volunteer_id=vol_id,
                        event_id=event_id,
                        status=pending.status,
                        delivery_hours=pending.delivery_hours,
                        salesforce_id=pending.sf_participation_id,
                        age_group=pending.age_group,
                        email=pending.email,
                        title=pending.title,
                    )
                    db.session.add(participation)

            # Mark resolved
            pending.resolved_at = now
            pending.error_reason = None
            resolved_count += 1

            # Resolve DQ flag
            _resolve_participation_flag_if_exists(pending.sf_participation_id)

        else:
            # Still missing
            if pending.retry_count > 10:
                pending.error_reason = "likely_sf_orphan"

        # Chunked commit for resilience — crash mid-sweep only loses the current chunk
        if (i + 1) % _SWEEP_CHUNK_SIZE == 0:
            try:
                db.session.commit()
                print(
                    f"  -> Sweep: committed chunk {(i+1) // _SWEEP_CHUNK_SIZE} ({resolved_count} resolved so far)"
                )
            except Exception as commit_err:
                db.session.rollback()
                print(f"  -> Sweep: chunk commit failed: {commit_err}")
                logger.exception(
                    "Error during pending participation sweep chunk: %s", commit_err
                )

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Error during pending participation sweep final commit: %s", e)

    return resolved_count
