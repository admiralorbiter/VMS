"""
Session Status Classification Service
======================================

Shared logic for classifying teacher session statuses across all views
(usage dashboard, reports, and multi-tenant teacher usage).

This module is the single source of truth for:
- Normalizing status strings from Pathful imports and internal data
- Classifying teacher registrations into completed/planned/needs_review/no_show/cancelled
- Detecting stale sessions (past events stuck in non-terminal statuses)

Classification Rules:
    COMPLETED/SIMULCAST/count  → "completed"
    CONFIRMED/PUBLISHED/REQUESTED/DRAFT + future → "planned"
    CONFIRMED/PUBLISHED/REQUESTED + past → "needs_review" (stale)
    Teacher no-show detected   → "no_show"
    Teacher cancellation       → "cancelled"
    Otherwise                  → "skipped"
"""

from datetime import datetime, timezone
from enum import Enum

from models.event_enums import EventStatus


class SessionClassification(str, Enum):
    """Result of classifying a teacher's participation in a session."""

    COMPLETED = "completed"
    PLANNED = "planned"
    NEEDS_REVIEW = "needs_review"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


def sanitize_status(text):
    """Normalize a status string for robust comparison.

    Handles None, strips whitespace, lowercases, and replaces common
    separators (hyphens, underscores, slashes, etc.) with spaces.
    Collapses multiple spaces into one.

    This replaces the inline ``_sanitize()``, ``_sanitize_status()``,
    and ``_norm()`` helpers scattered across route files.

    Args:
        text: Raw status string (may be None)

    Returns:
        Normalized lowercase string with single-space separators
    """
    if not text:
        return ""
    t = str(text).lower().strip()
    for ch in ["_", "-", "/", "\\", ",", ".", "  "]:
        t = t.replace(ch, " ")
    while "  " in t:
        t = t.replace("  ", " ")
    return t


def _is_teacher_no_show(teacher_reg_status, event_original_status, event_status):
    """Detect whether this registration represents a teacher no-show.

    Checks three layers (most specific first):
    1. Teacher registration status (e.g. "teacher no-show", "no show")
    2. Event original_status_string (e.g. "Teacher No-Show")
    3. Event status enum + original status mentions "teacher"

    Args:
        teacher_reg_status: Sanitized teacher registration status string
        event_original_status: Sanitized event.original_status_string
        event_status: EventStatus enum value

    Returns:
        True if teacher no-show is detected
    """
    # Layer 1: Registration-level no-show
    if (
        "teacher no show" in teacher_reg_status
        or "no show" in teacher_reg_status
        or "did not attend" in teacher_reg_status
    ):
        return True

    # Layer 2: Event-level no-show (original status string)
    if (
        "teacher no show" in event_original_status
        or "teacher did not attend" in event_original_status
    ):
        return True

    # Layer 3: Event status enum is NO_SHOW and original status mentions teacher
    if event_status == EventStatus.NO_SHOW and "teacher" in event_original_status:
        return True

    return False


def _is_teacher_cancellation(teacher_reg_status):
    """Detect whether this registration represents a teacher cancellation.

    Args:
        teacher_reg_status: Sanitized teacher registration status string

    Returns:
        True if cancellation/withdrawal is detected
    """
    return (
        "cancel" in teacher_reg_status
        or "withdraw" in teacher_reg_status
        or "inclement weather" in teacher_reg_status
        or "technical" in teacher_reg_status
    )


def _is_completed(event, teacher_reg_status, event_original_status):
    """Detect whether this registration represents a completed session.

    Checks:
    - Event status is COMPLETED or SIMULCAST
    - original_status_string indicates completion
    - Teacher registration has "count" status
    - Teacher registration has "attended" or "completed" status
    - Teacher has attendance_confirmed_at set

    Args:
        event: Event model instance
        teacher_reg_status: Sanitized teacher registration status string
        event_original_status: Sanitized event.original_status_string

    Returns:
        True if session should count as completed
    """
    # Event-level completion
    if event.status in (EventStatus.COMPLETED, EventStatus.SIMULCAST):
        return True

    # Original status string indicates completion
    if event_original_status in ("completed", "successfully completed"):
        return True

    # "moved to in-person" counts as completed
    if "moved to in person" in event_original_status:
        return True

    # Teacher registration "count" status
    if "count" in teacher_reg_status:
        return True

    # Teacher registration confirms attendance
    if "attended" in teacher_reg_status or "completed" in teacher_reg_status:
        return True

    return False


def classify_teacher_session(event, teacher_reg=None, now=None):
    """Classify a single event + teacher registration into a status bucket.

    This is the single source of truth for session classification, replacing
    duplicated logic across three route files.

    Priority order:
    1. No-show detection (most important — affects force-override logic)
    2. Cancellation detection
    3. Completed detection
    4. Planned/Needs Review (based on event status + date)

    Args:
        event: Event model instance (must have .status, .start_date,
               .original_status_string)
        teacher_reg: Optional EventTeacher model instance (has .status,
                     .attendance_confirmed_at)
        now: Current datetime (timezone-aware). Defaults to utcnow().

    Returns:
        SessionClassification enum value
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Normalize status strings
    event_original_status = sanitize_status(
        getattr(event, "original_status_string", None)
    )
    teacher_reg_status = sanitize_status(
        getattr(teacher_reg, "status", None) if teacher_reg else None
    )

    # 1. No-show detection (highest priority)
    if _is_teacher_no_show(teacher_reg_status, event_original_status, event.status):
        return SessionClassification.NO_SHOW

    # 2. Cancellation detection
    if _is_teacher_cancellation(teacher_reg_status):
        return SessionClassification.CANCELLED

    # 3. Completed detection
    if _is_completed(event, teacher_reg_status, event_original_status):
        # Also check attendance_confirmed_at as a secondary signal
        return SessionClassification.COMPLETED

    # Check attendance_confirmed_at on the registration (without other signals)
    if teacher_reg and getattr(teacher_reg, "attendance_confirmed_at", None):
        return SessionClassification.COMPLETED

    # 4. Planned vs Needs Review (based on event status + date)
    # Determine if the event is in the future
    event_start_date = event.start_date
    if event_start_date and event_start_date.tzinfo is None:
        event_start_date = event_start_date.replace(tzinfo=timezone.utc)

    is_future = event_start_date and event_start_date > now

    # Statuses that indicate a session is in-flight (not terminal)
    in_flight_statuses = (
        EventStatus.CONFIRMED,
        EventStatus.PUBLISHED,
        EventStatus.REQUESTED,
        EventStatus.DRAFT,
    )

    if event.status in in_flight_statuses:
        if is_future:
            return SessionClassification.PLANNED
        else:
            return SessionClassification.NEEDS_REVIEW

    # Check original_status_string for draft/registered (legacy data)
    if event_original_status in ("draft", "registered"):
        if is_future:
            return SessionClassification.PLANNED
        else:
            return SessionClassification.NEEDS_REVIEW

    # 5. Indeterminate — don't count
    return SessionClassification.SKIPPED


def detect_stale_reason(event, last_import_date=None):
    """Determine why a past session is still in a non-terminal status.

    Useful for surfacing actionable information to admins about sessions
    that should have been updated by a Pathful import but weren't.

    Args:
        event: Event model instance
        last_import_date: Date of the most recent Pathful import (optional)

    Returns:
        str: Reason code — one of:
            - "no_import_since_session": Last import was before the event date
            - "import_missed": Import happened after event but didn't update it
            - "unknown": Can't determine (no import data available)
    """
    if not last_import_date:
        return "unknown"

    event_date = event.start_date
    if event_date and event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    if (
        last_import_date
        and hasattr(last_import_date, "tzinfo")
        and last_import_date.tzinfo is None
    ):
        last_import_date = last_import_date.replace(tzinfo=timezone.utc)

    if event_date and last_import_date:
        if last_import_date < event_date:
            return "no_import_since_session"
        else:
            return "import_missed"

    return "unknown"
