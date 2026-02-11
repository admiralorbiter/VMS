"""
Event Flag Scanner Service
==========================

Scans events for data quality issues and creates/resolves flags automatically.
Supports Phase D-1 of the Pathful Import refactor.

Key Features:
- Auto-scan after imports to detect issues
- Individual event scanning for targeted checks
- Auto-resolution when issues are fixed
- Avoids duplicate flags for the same issue
"""

from datetime import datetime, timezone
from typing import List, Optional

from flask import current_app

from models import db
from models.event import Event, EventStatus, EventType
from models.event_flag import EventFlag, FlagType


def create_flag_if_not_exists(
    event_id: int,
    flag_type: str,
    created_by: Optional[int] = None,
    created_source: str = "import_scan",
) -> Optional[EventFlag]:
    """
    Create a flag for an event if one doesn't already exist (unresolved).

    Args:
        event_id: Event ID to flag
        flag_type: Type of flag (from FlagType constants)
        created_by: User ID who created (None for system)
        created_source: How the flag was created

    Returns:
        EventFlag if created, None if already exists
    """
    # Check for existing unresolved flag of this type
    existing = EventFlag.query.filter_by(
        event_id=event_id,
        flag_type=flag_type,
        is_resolved=False,
    ).first()

    if existing:
        return None  # Already flagged

    flag = EventFlag(
        event_id=event_id,
        flag_type=flag_type,
        created_by=created_by,
        created_source=created_source,
    )
    db.session.add(flag)
    return flag


def _is_event_past(event: Event) -> bool:
    """
    Safely check if an event is in the past, handling timezone-naive dates.
    """
    if not event.start_date:
        return False

    now = datetime.now(timezone.utc)
    start = event.start_date

    # Handle naive datetime by assuming UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    return start < now


def scan_event_for_flags(
    event: Event,
    created_by: Optional[int] = None,
    created_source: str = "import_scan",
) -> List[EventFlag]:
    """
    Scan a single event for flag conditions and create any needed flags.

    Args:
        event: Event to scan
        created_by: User ID who triggered the scan
        created_source: Source of the scan

    Returns:
        List of newly created flags
    """
    new_flags = []

    # Only scan virtual session events
    if event.type != EventType.VIRTUAL_SESSION:
        return new_flags

    # Condition 1: NEEDS_ATTENTION - Draft event with past date
    if event.status == EventStatus.DRAFT and _is_event_past(event):
        flag = create_flag_if_not_exists(
            event.id, FlagType.NEEDS_ATTENTION, created_by, created_source
        )
        if flag:
            new_flags.append(flag)

    # Condition 2: MISSING_TEACHER - Event has no teacher assigned
    # Check both teacher_registrations relationship and educators text field
    has_teacher = len(event.teacher_registrations) > 0 or (
        event.educators and event.educators.strip()
    )
    if not has_teacher:
        flag = create_flag_if_not_exists(
            event.id, FlagType.MISSING_TEACHER, created_by, created_source
        )
        if flag:
            new_flags.append(flag)

    # Condition 3: MISSING_PRESENTER - Completed event has no presenter
    if event.status == EventStatus.COMPLETED:
        has_presenter = len(event.volunteers) > 0 or (
            event.professionals and event.professionals.strip()
        )
        if not has_presenter:
            flag = create_flag_if_not_exists(
                event.id, FlagType.MISSING_PRESENTER, created_by, created_source
            )
            if flag:
                new_flags.append(flag)

    # Condition 4: NEEDS_REASON - Cancelled event has no cancellation reason
    if event.status == EventStatus.CANCELLED and not event.cancellation_reason:
        flag = create_flag_if_not_exists(
            event.id, FlagType.NEEDS_REASON, created_by, created_source
        )
        if flag:
            new_flags.append(flag)

    return new_flags


def scan_and_create_flags(
    event_ids: Optional[List[int]] = None,
    created_by: Optional[int] = None,
    created_source: str = "import_scan",
) -> dict:
    """
    Scan events for flag conditions and create any needed flags.

    Args:
        event_ids: List of event IDs to scan (None = scan all virtual events)
        created_by: User ID who triggered the scan
        created_source: Source of the scan ('import_scan', 'nightly_scan', 'manual')

    Returns:
        dict with scan results: created_count, scanned_count, flag_types
    """
    results = {
        "scanned_count": 0,
        "created_count": 0,
        "flag_types": {},
    }

    # Build query
    query = Event.query.filter(Event.type == EventType.VIRTUAL_SESSION)

    if event_ids:
        query = query.filter(Event.id.in_(event_ids))

    events = query.all()

    for event in events:
        results["scanned_count"] += 1

        flags = scan_event_for_flags(event, created_by, created_source)
        for flag in flags:
            results["created_count"] += 1
            results["flag_types"][flag.flag_type] = (
                results["flag_types"].get(flag.flag_type, 0) + 1
            )

    if results["created_count"] > 0:
        db.session.commit()
        current_app.logger.info(
            f"Flag scan complete: {results['created_count']} flags created "
            f"for {results['scanned_count']} events"
        )

    return results


def check_and_auto_resolve_flags(event: Event) -> List[EventFlag]:
    """
    Check if any open flags on an event can be auto-resolved.

    Call this after modifying an event to auto-close flags when issues are fixed.

    Args:
        event: Event to check

    Returns:
        List of flags that were auto-resolved
    """
    resolved = []

    open_flags = EventFlag.query.filter_by(
        event_id=event.id,
        is_resolved=False,
    ).all()

    for flag in open_flags:
        should_resolve = False
        note = None

        if flag.flag_type == FlagType.NEEDS_ATTENTION:
            # Resolve if status is no longer Draft
            if event.status != EventStatus.DRAFT:
                should_resolve = True
                status_val = (
                    event.status.value
                    if hasattr(event.status, "value")
                    else str(event.status)
                )
                note = f"Status changed to {status_val}"

        elif flag.flag_type == FlagType.MISSING_TEACHER:
            # Resolve if teacher now assigned
            has_teacher = len(event.teacher_registrations) > 0 or (
                event.educators and event.educators.strip()
            )
            if has_teacher:
                should_resolve = True
                note = "Teacher now assigned"

        elif flag.flag_type == FlagType.MISSING_PRESENTER:
            # Resolve if presenter now assigned
            has_presenter = len(event.volunteers) > 0 or (
                event.professionals and event.professionals.strip()
            )
            if has_presenter:
                should_resolve = True
                note = "Presenter now assigned"

        elif flag.flag_type == FlagType.NEEDS_REASON:
            # Resolve if cancellation reason now set
            if event.cancellation_reason:
                should_resolve = True
                reason_val = (
                    event.cancellation_reason.value
                    if hasattr(event.cancellation_reason, "value")
                    else str(event.cancellation_reason)
                )
                note = f"Reason set: {reason_val}"

        if should_resolve:
            flag.resolve(notes=note, auto=True)
            resolved.append(flag)

    return resolved


def get_flag_summary(
    district_id: Optional[str] = None,
    include_resolved: bool = False,
) -> dict:
    """
    Get summary statistics for event flags.

    Args:
        district_id: Optional district to filter by
        include_resolved: Include resolved flags in counts

    Returns:
        dict with flag counts by type and total
    """
    query = db.session.query(EventFlag)

    if not include_resolved:
        query = query.filter(EventFlag.is_resolved == False)

    if district_id:
        query = query.join(Event).filter(Event.district_partner == district_id)

    flags = query.all()

    summary = {
        "total": len(flags),
        "by_type": {},
    }

    for flag in flags:
        summary["by_type"][flag.flag_type] = (
            summary["by_type"].get(flag.flag_type, 0) + 1
        )

    return summary
