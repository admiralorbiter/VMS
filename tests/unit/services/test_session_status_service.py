"""
Unit tests for services.session_status_service.

Tests the shared session classification logic that replaces duplicated
inline code across three route files.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from services.session_status_service import (
    SessionClassification,
    classify_teacher_session,
    detect_stale_reason,
    sanitize_status,
)

# ---------------------------------------------------------------------------
# sanitize_status
# ---------------------------------------------------------------------------


class TestSanitizeStatus:
    def test_none_returns_empty(self):
        assert sanitize_status(None) == ""

    def test_empty_string(self):
        assert sanitize_status("") == ""

    def test_lowercases(self):
        assert sanitize_status("Teacher No-Show") == "teacher no show"

    def test_replaces_hyphens(self):
        assert sanitize_status("no-show") == "no show"

    def test_replaces_underscores(self):
        assert sanitize_status("no_show") == "no show"

    def test_replaces_slashes(self):
        assert sanitize_status("cancel/withdraw") == "cancel withdraw"

    def test_collapses_spaces(self):
        assert sanitize_status("teacher   no   show") == "teacher no show"

    def test_strips_whitespace(self):
        assert sanitize_status("  completed  ") == "completed"

    def test_mixed_separators(self):
        assert sanitize_status("Teacher_No-Show/Test") == "teacher no show test"


# ---------------------------------------------------------------------------
# Helpers for creating mock events and teacher registrations
# ---------------------------------------------------------------------------


def _make_event(
    status,
    start_date=None,
    original_status_string=None,
):
    """Create a mock Event with the given properties."""
    event = MagicMock()
    event.status = status
    event.start_date = start_date or datetime.now(timezone.utc)
    event.original_status_string = original_status_string
    return event


def _make_teacher_reg(status=None, attendance_confirmed_at=None):
    """Create a mock EventTeacher with the given properties."""
    reg = MagicMock()
    reg.status = status
    reg.attendance_confirmed_at = attendance_confirmed_at
    return reg


def _future():
    return datetime.now(timezone.utc) + timedelta(days=10)


def _past():
    return datetime.now(timezone.utc) - timedelta(days=10)


# ---------------------------------------------------------------------------
# classify_teacher_session — Completed
# ---------------------------------------------------------------------------


class TestClassifyCompleted:
    def test_completed_status(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        assert classify_teacher_session(event) == SessionClassification.COMPLETED

    def test_simulcast_status(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.SIMULCAST, start_date=_past())
        assert classify_teacher_session(event) == SessionClassification.COMPLETED

    def test_original_status_successfully_completed(self):
        from models.event_enums import EventStatus

        event = _make_event(
            EventStatus.REQUESTED,
            start_date=_past(),
            original_status_string="Successfully Completed",
        )
        assert classify_teacher_session(event) == SessionClassification.COMPLETED

    def test_teacher_reg_attended(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.REQUESTED, start_date=_past())
        reg = _make_teacher_reg(status="attended")
        assert classify_teacher_session(event, reg) == SessionClassification.COMPLETED

    def test_teacher_reg_count_status(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.NO_SHOW, start_date=_past())
        reg = _make_teacher_reg(status="count")
        assert classify_teacher_session(event, reg) == SessionClassification.COMPLETED

    def test_attendance_confirmed_at(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.REQUESTED, start_date=_past())
        reg = _make_teacher_reg(attendance_confirmed_at=datetime.now(timezone.utc))
        assert classify_teacher_session(event, reg) == SessionClassification.COMPLETED

    def test_moved_to_in_person(self):
        from models.event_enums import EventStatus

        event = _make_event(
            EventStatus.REQUESTED,
            start_date=_past(),
            original_status_string="Moved to In-Person Session",
        )
        assert classify_teacher_session(event) == SessionClassification.COMPLETED


# ---------------------------------------------------------------------------
# classify_teacher_session — Planned (future)
# ---------------------------------------------------------------------------


class TestClassifyPlanned:
    def test_confirmed_future(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.CONFIRMED, start_date=_future())
        assert classify_teacher_session(event) == SessionClassification.PLANNED

    def test_published_future(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.PUBLISHED, start_date=_future())
        assert classify_teacher_session(event) == SessionClassification.PLANNED

    def test_requested_future(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.REQUESTED, start_date=_future())
        assert classify_teacher_session(event) == SessionClassification.PLANNED

    def test_draft_future(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.DRAFT, start_date=_future())
        assert classify_teacher_session(event) == SessionClassification.PLANNED


# ---------------------------------------------------------------------------
# classify_teacher_session — Needs Review (past, non-terminal)
# ---------------------------------------------------------------------------


class TestClassifyNeedsReview:
    def test_confirmed_past(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.CONFIRMED, start_date=_past())
        assert classify_teacher_session(event) == SessionClassification.NEEDS_REVIEW

    def test_published_past(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.PUBLISHED, start_date=_past())
        assert classify_teacher_session(event) == SessionClassification.NEEDS_REVIEW

    def test_requested_past(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.REQUESTED, start_date=_past())
        assert classify_teacher_session(event) == SessionClassification.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# classify_teacher_session — No-Show
# ---------------------------------------------------------------------------


class TestClassifyNoShow:
    def test_teacher_reg_no_show(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="no_show")
        assert classify_teacher_session(event, reg) == SessionClassification.NO_SHOW

    def test_teacher_reg_teacher_no_show_text(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="Teacher No-Show")
        assert classify_teacher_session(event, reg) == SessionClassification.NO_SHOW

    def test_event_level_teacher_no_show(self):
        from models.event_enums import EventStatus

        event = _make_event(
            EventStatus.NO_SHOW,
            start_date=_past(),
            original_status_string="Teacher No-Show",
        )
        assert classify_teacher_session(event) == SessionClassification.NO_SHOW

    def test_event_status_no_show_with_teacher_in_original(self):
        from models.event_enums import EventStatus

        event = _make_event(
            EventStatus.NO_SHOW,
            start_date=_past(),
            original_status_string="teacher issue",
        )
        assert classify_teacher_session(event) == SessionClassification.NO_SHOW


# ---------------------------------------------------------------------------
# classify_teacher_session — Cancelled
# ---------------------------------------------------------------------------


class TestClassifyCancelled:
    def test_teacher_cancel(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="Teacher Cancelation")
        assert classify_teacher_session(event, reg) == SessionClassification.CANCELLED

    def test_teacher_withdraw(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="Withdrawn-Time Constraint")
        assert classify_teacher_session(event, reg) == SessionClassification.CANCELLED

    def test_inclement_weather(self):
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="Inclement Weather Cancellation")
        assert classify_teacher_session(event, reg) == SessionClassification.CANCELLED


# ---------------------------------------------------------------------------
# classify_teacher_session — Priority order
# ---------------------------------------------------------------------------


class TestClassifyPriority:
    def test_no_show_takes_priority_over_completed(self):
        """No-show on the registration overrides completed event status."""
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.COMPLETED, start_date=_past())
        reg = _make_teacher_reg(status="no_show")
        assert classify_teacher_session(event, reg) == SessionClassification.NO_SHOW

    def test_cancellation_takes_priority_over_planned(self):
        """Cancelled registration should not count as planned."""
        from models.event_enums import EventStatus

        event = _make_event(EventStatus.CONFIRMED, start_date=_future())
        reg = _make_teacher_reg(status="Teacher Cancelation")
        assert classify_teacher_session(event, reg) == SessionClassification.CANCELLED


# ---------------------------------------------------------------------------
# classify_teacher_session — Timezone handling
# ---------------------------------------------------------------------------


class TestClassifyTimezone:
    def test_naive_start_date_treated_as_utc(self):
        """Naive datetime should be treated as UTC and not crash."""
        from models.event_enums import EventStatus

        future_naive = datetime.now() + timedelta(days=10)
        event = _make_event(EventStatus.CONFIRMED, start_date=future_naive)
        assert classify_teacher_session(event) == SessionClassification.PLANNED


# ---------------------------------------------------------------------------
# detect_stale_reason
# ---------------------------------------------------------------------------


class TestDetectStaleReason:
    def test_no_import_date(self):
        event = _make_event(MagicMock(), start_date=_past())
        assert detect_stale_reason(event) == "unknown"

    def test_import_before_event(self):
        event = _make_event(MagicMock(), start_date=_past())
        import_date = _past() - timedelta(days=5)
        assert detect_stale_reason(event, import_date) == "no_import_since_session"

    def test_import_after_event(self):
        event = _make_event(MagicMock(), start_date=_past())
        import_date = datetime.now(timezone.utc)
        assert detect_stale_reason(event, import_date) == "import_missed"
