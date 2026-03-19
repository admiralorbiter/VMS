"""
Draft Review Service
====================

Service for triaging past-date Draft virtual events.

Provides:
- Queue query with heuristic confidence scoring
- Bulk promotion (Draft → Completed) with EventTeacher status update
- Bulk dismissal (Draft → Cancelled) with reason tracking
"""

import logging
from datetime import datetime, timezone

from models import db
from models.event import Event, EventStatus, EventType
from models.event_enums import CancellationReason
from models.event_flag import EventFlag, FlagType

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_ET = None


def _get_et():
    global _ET
    if _ET is None:
        from models.event import EventTeacher

        _ET = EventTeacher
    return _ET


# ── Confidence heuristic ────────────────────────────────────────────────


def _classify_confidence(event):
    """Classify a Draft event's likelihood of being a real session.

    Returns:
        tuple: (level, label) where level is 'high', 'medium', or 'low'
    """
    att_stu = event.attended_student_count or 0
    reg_stu = event.registered_student_count or 0

    if att_stu > 0:
        return "high", "Likely Completed"
    elif reg_stu > 0:
        return "medium", "Needs Review"
    else:
        return "low", "Likely Never Happened"


# ── Queue query ─────────────────────────────────────────────────────────


def get_draft_review_queue(
    tenant_id=None, district_name=None, date_from=None, date_to=None
):
    """Get past-date Draft virtual events for admin triage.

    Args:
        tenant_id: Optional tenant filter (for district-scoped view)
        district_name: Optional district name filter
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        dict with 'events' list and 'summary' stats
    """
    ET = _get_et()
    now = datetime.now(timezone.utc)

    query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status == EventStatus.DRAFT,
        Event.start_date < now,
        Event.start_date.isnot(None),
    )

    if district_name:
        query = query.filter(Event.district_partner == district_name)
    if date_from:
        query = query.filter(Event.start_date >= date_from)
    if date_to:
        query = query.filter(Event.start_date <= date_to)

    events = query.order_by(Event.start_date.desc()).all()

    # Enrich each event with teacher count and confidence
    results = []
    summary = {"total": 0, "high": 0, "medium": 0, "low": 0}

    for event in events:
        teacher_count = ET.query.filter_by(event_id=event.id).count()
        confidence_level, confidence_label = _classify_confidence(event)

        summary["total"] += 1
        summary[confidence_level] += 1

        results.append(
            {
                "event": event,
                "teacher_count": teacher_count,
                "confidence_level": confidence_level,
                "confidence_label": confidence_label,
            }
        )

    return {"events": results, "summary": summary}


# ── Bulk promote ────────────────────────────────────────────────────────


def promote_draft_events(event_ids, user_id):
    """Promote Draft events to Completed and update EventTeacher statuses.

    For each event:
    1. Set status to COMPLETED
    2. Update EventTeacher records:
       - If attended_student_count > 0 → teachers marked 'attended'
       - Otherwise → teachers marked 'no_show'
    3. Auto-resolve NEEDS_ATTENTION flags

    Args:
        event_ids: List of event IDs to promote
        user_id: ID of the admin performing the action

    Returns:
        dict: Summary with counts and any errors
    """
    ET = _get_et()
    promoted = 0
    teachers_updated = 0
    flags_resolved = 0
    errors = []

    for event_id in event_ids:
        try:
            event = Event.query.get(event_id)
            if not event:
                errors.append(f"Event {event_id} not found")
                continue
            if event.status != EventStatus.DRAFT:
                errors.append(
                    f"Event {event_id} is not Draft (is {event.status.value})"
                )
                continue

            # 1. Update event status
            event.status = EventStatus.COMPLETED

            # 2. Update EventTeacher statuses
            # Use the same logic as processing.py: attended_student_count > 0
            # implies real attendance; otherwise no_show
            att_stu = event.attended_student_count or 0
            new_et_status = "attended" if att_stu > 0 else "no_show"

            et_records = ET.query.filter_by(event_id=event.id).all()
            for et in et_records:
                # Respect admin overrides (records with notes)
                if not et.notes and et.status == "registered":
                    et.status = new_et_status
                    if new_et_status == "attended":
                        et.attendance_confirmed_at = datetime.now(timezone.utc)
                    teachers_updated += 1

            # 3. Auto-resolve NEEDS_ATTENTION flags
            open_flags = EventFlag.query.filter_by(
                event_id=event.id,
                flag_type=FlagType.NEEDS_ATTENTION,
                is_resolved=False,
            ).all()
            for flag in open_flags:
                flag.resolve(
                    notes="Auto-resolved: Draft promoted to Completed via review queue",
                    resolved_by=user_id,
                    auto=True,
                )
                flags_resolved += 1

            promoted += 1

        except Exception as e:
            logger.error("Error promoting event %d: %s", event_id, e)
            errors.append(f"Event {event_id}: {str(e)}")

    if promoted > 0:
        db.session.commit()
        logger.info(
            "Draft review: promoted %d events (%d teachers updated, %d flags resolved) by user %d",
            promoted,
            teachers_updated,
            flags_resolved,
            user_id,
        )

    return {
        "promoted": promoted,
        "teachers_updated": teachers_updated,
        "flags_resolved": flags_resolved,
        "errors": errors,
    }


# ── Bulk dismiss ────────────────────────────────────────────────────────


def dismiss_draft_events(event_ids, cancellation_reason, user_id):
    """Dismiss Draft events as Cancelled.

    For each event:
    1. Set status to CANCELLED
    2. Record cancellation reason
    3. Update EventTeacher records to 'no_show'
    4. Auto-resolve NEEDS_ATTENTION flags

    Args:
        event_ids: List of event IDs to dismiss
        cancellation_reason: Reason for dismissal
        user_id: ID of the admin performing the action

    Returns:
        dict: Summary with counts and any errors
    """
    ET = _get_et()
    dismissed = 0
    flags_resolved = 0
    errors = []

    for event_id in event_ids:
        try:
            event = Event.query.get(event_id)
            if not event:
                errors.append(f"Event {event_id} not found")
                continue
            if event.status != EventStatus.DRAFT:
                errors.append(
                    f"Event {event_id} is not Draft (is {event.status.value})"
                )
                continue

            # 1. Update event status
            event.status = EventStatus.CANCELLED
            # Use the proper set_cancellation_reason method (DEC-008)
            # which handles validation and audit fields
            event.set_cancellation_reason(
                reason=CancellationReason.OTHER,
                notes=(
                    cancellation_reason
                    if len(cancellation_reason) >= 10
                    else f"Draft review: {cancellation_reason}"
                ),
                user_id=user_id,
            )

            # 2. Update EventTeacher records to no_show
            et_records = ET.query.filter_by(event_id=event.id).all()
            for et in et_records:
                if not et.notes and et.status == "registered":
                    et.status = "no_show"

            # 3. Auto-resolve NEEDS_ATTENTION flags
            open_flags = EventFlag.query.filter_by(
                event_id=event.id,
                flag_type=FlagType.NEEDS_ATTENTION,
                is_resolved=False,
            ).all()
            for flag in open_flags:
                flag.resolve(
                    notes=f"Auto-resolved: Draft dismissed as Cancelled ({cancellation_reason})",
                    resolved_by=user_id,
                    auto=True,
                )
                flags_resolved += 1

            dismissed += 1

        except Exception as e:
            logger.error("Error dismissing event %d: %s", event_id, e)
            errors.append(f"Event {event_id}: {str(e)}")

    if dismissed > 0:
        db.session.commit()
        logger.info(
            "Draft review: dismissed %d events (%d flags resolved) by user %d",
            dismissed,
            flags_resolved,
            user_id,
        )

    return {
        "dismissed": dismissed,
        "flags_resolved": flags_resolved,
        "errors": errors,
    }
