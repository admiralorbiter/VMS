"""
Tests for Draft Review Service
==============================

Tests the draft review queue, promotion, and dismissal functionality.
"""

from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import generate_password_hash

from models import db
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.event_flag import EventFlag, FlagType
from models.teacher import Teacher
from models.user import User


@pytest.fixture
def review_admin(app):
    """Create an admin user for draft review actions."""
    admin = User(
        username="draft_review_admin",
        email="draftadmin@example.com",
        password_hash=generate_password_hash("password"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def draft_event_high_confidence(app):
    """Draft event with attended students (high confidence)."""
    event = Event(
        title="High Confidence Draft Session",
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.DRAFT,
        start_date=datetime.now(timezone.utc) - timedelta(days=30),
        registered_student_count=25,
        attended_student_count=20,
        format=EventFormat.VIRTUAL,
        import_source="pathful_direct",
        pathful_session_id="99901",
    )
    db.session.add(event)
    db.session.commit()
    return event


@pytest.fixture
def draft_event_medium_confidence(app):
    """Draft event with registered but no attended students."""
    event = Event(
        title="Medium Confidence Draft Session",
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.DRAFT,
        start_date=datetime.now(timezone.utc) - timedelta(days=60),
        registered_student_count=30,
        attended_student_count=0,
        format=EventFormat.VIRTUAL,
        import_source="pathful_direct",
        pathful_session_id="99902",
    )
    db.session.add(event)
    db.session.commit()
    return event


@pytest.fixture
def draft_event_low_confidence(app):
    """Draft event with no student data at all."""
    event = Event(
        title="Low Confidence Draft Session",
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.DRAFT,
        start_date=datetime.now(timezone.utc) - timedelta(days=90),
        registered_student_count=0,
        attended_student_count=0,
        format=EventFormat.VIRTUAL,
        import_source="pathful_direct",
        pathful_session_id="99903",
    )
    db.session.add(event)
    db.session.commit()
    return event


@pytest.fixture
def draft_event_with_teacher(app, draft_event_high_confidence):
    """Draft event with a linked teacher (EventTeacher record)."""
    teacher = Teacher(
        first_name="Jane",
        last_name="Smith",
        active=True,
    )
    db.session.add(teacher)
    db.session.flush()

    et = EventTeacher(
        event_id=draft_event_high_confidence.id,
        teacher_id=teacher.id,
        status="registered",
    )
    db.session.add(et)
    db.session.commit()
    return draft_event_high_confidence, teacher, et


@pytest.fixture
def draft_event_with_flag(app, draft_event_high_confidence):
    """Draft event with an open NEEDS_ATTENTION flag."""
    flag = EventFlag(
        event_id=draft_event_high_confidence.id,
        flag_type=FlagType.NEEDS_ATTENTION,
        created_source="import_scan",
    )
    db.session.add(flag)
    db.session.commit()
    return draft_event_high_confidence, flag


class TestGetDraftReviewQueue:
    """Tests for get_draft_review_queue()."""

    def test_returns_past_draft_events(
        self, app, draft_event_high_confidence, draft_event_medium_confidence
    ):
        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()

        assert result["summary"]["total"] == 2
        event_ids = {item["event"].id for item in result["events"]}
        assert draft_event_high_confidence.id in event_ids
        assert draft_event_medium_confidence.id in event_ids

    def test_excludes_future_draft_events(self, app):
        """Future-date Draft events should not appear in the queue."""
        future_event = Event(
            title="Future Draft",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) + timedelta(days=30),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(future_event)
        db.session.commit()

        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        event_ids = {item["event"].id for item in result["events"]}
        assert future_event.id not in event_ids

    def test_excludes_non_virtual_events(self, app):
        """Non-virtual Draft events should not appear."""
        non_virtual = Event(
            title="In-Person Draft",
            type=EventType.IN_PERSON,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            format=EventFormat.IN_PERSON,
        )
        db.session.add(non_virtual)
        db.session.commit()

        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        event_ids = {item["event"].id for item in result["events"]}
        assert non_virtual.id not in event_ids

    def test_confidence_high(self, app, draft_event_high_confidence):
        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        item = next(
            i
            for i in result["events"]
            if i["event"].id == draft_event_high_confidence.id
        )
        assert item["confidence_level"] == "high"
        assert result["summary"]["high"] == 1

    def test_confidence_medium(self, app, draft_event_medium_confidence):
        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        item = next(
            i
            for i in result["events"]
            if i["event"].id == draft_event_medium_confidence.id
        )
        assert item["confidence_level"] == "medium"

    def test_confidence_low(self, app, draft_event_low_confidence):
        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        item = next(
            i
            for i in result["events"]
            if i["event"].id == draft_event_low_confidence.id
        )
        assert item["confidence_level"] == "low"

    def test_teacher_count_included(self, app, draft_event_with_teacher):
        event, teacher, et = draft_event_with_teacher

        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        item = next(i for i in result["events"] if i["event"].id == event.id)
        assert item["teacher_count"] == 1


class TestPromoteDraftEvents:
    """Tests for promote_draft_events()."""

    def test_promotes_draft_to_completed(
        self, app, draft_event_high_confidence, review_admin
    ):
        from services.draft_review_service import promote_draft_events

        result = promote_draft_events(
            [draft_event_high_confidence.id], user_id=review_admin.id
        )

        assert result["promoted"] == 1
        assert result["errors"] == []

        # Verify status changed
        event = db.session.get(Event, draft_event_high_confidence.id)
        assert event.status == EventStatus.COMPLETED

    def test_updates_event_teacher_to_attended(
        self, app, draft_event_with_teacher, review_admin
    ):
        """When attended_student_count > 0, teachers should be marked attended."""
        event, teacher, et = draft_event_with_teacher

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([event.id], user_id=review_admin.id)

        assert result["teachers_updated"] == 1
        refreshed_et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=teacher.id
        ).first()
        assert refreshed_et.status == "attended"
        assert refreshed_et.attendance_confirmed_at is not None

    def test_updates_event_teacher_to_no_show_when_no_attendance(
        self, app, review_admin
    ):
        """When attended_student_count is 0, teachers should be marked no_show."""
        event = Event(
            title="No Attendance Draft",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            registered_student_count=25,
            attended_student_count=0,
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.flush()

        teacher = Teacher(first_name="Bob", last_name="Jones", active=True)
        db.session.add(teacher)
        db.session.flush()

        et = EventTeacher(event_id=event.id, teacher_id=teacher.id, status="registered")
        db.session.add(et)
        db.session.commit()

        from services.draft_review_service import promote_draft_events

        promote_draft_events([event.id], user_id=review_admin.id)

        refreshed_et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=teacher.id
        ).first()
        assert refreshed_et.status == "no_show"

    def test_resolves_needs_attention_flag(
        self, app, draft_event_with_flag, review_admin
    ):
        event, flag = draft_event_with_flag

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([event.id], user_id=review_admin.id)

        assert result["flags_resolved"] == 1
        refreshed_flag = db.session.get(EventFlag, flag.id)
        assert refreshed_flag.is_resolved is True
        assert refreshed_flag.auto_resolved is True

    def test_skips_non_draft_events(self, app):
        """Should error on events that aren't Draft."""
        event = Event(
            title="Completed Event",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([event.id], user_id=1)
        assert result["promoted"] == 0
        assert len(result["errors"]) == 1

    def test_respects_admin_overrides(
        self, app, draft_event_high_confidence, review_admin
    ):
        """EventTeacher records with notes should not be updated."""
        teacher = Teacher(first_name="Override", last_name="Teacher", active=True)
        db.session.add(teacher)
        db.session.flush()

        et = EventTeacher(
            event_id=draft_event_high_confidence.id,
            teacher_id=teacher.id,
            status="registered",
            notes="Admin manually set this",
        )
        db.session.add(et)
        db.session.commit()

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events(
            [draft_event_high_confidence.id], user_id=review_admin.id
        )

        # Teacher count should be 0 because the override prevented update
        assert result["teachers_updated"] == 0
        refreshed_et = EventTeacher.query.filter_by(
            event_id=draft_event_high_confidence.id, teacher_id=teacher.id
        ).first()
        assert refreshed_et.status == "registered"  # Unchanged


class TestDismissDraftEvents:
    """Tests for dismiss_draft_events()."""

    def test_dismisses_draft_as_cancelled(
        self, app, draft_event_low_confidence, review_admin
    ):
        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [draft_event_low_confidence.id],
            cancellation_reason="Session never happened — draft review",
            user_id=review_admin.id,
        )

        assert result["dismissed"] == 1
        assert result["errors"] == []

        event = db.session.get(Event, draft_event_low_confidence.id)
        assert event.status == EventStatus.CANCELLED

    def test_sets_cancellation_reason_as_other(
        self, app, draft_event_low_confidence, review_admin
    ):
        """Should use CancellationReason.OTHER with the reason as notes."""
        from models.event_enums import CancellationReason
        from services.draft_review_service import dismiss_draft_events

        dismiss_draft_events(
            [draft_event_low_confidence.id],
            cancellation_reason="Session never happened — draft review",
            user_id=review_admin.id,
        )

        event = db.session.get(Event, draft_event_low_confidence.id)
        assert event.cancellation_reason == CancellationReason.OTHER

    def test_updates_teachers_to_no_show(self, app, review_admin):
        """Dismissed events should have teachers marked no_show."""
        event = Event(
            title="Dismiss Me",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.flush()

        teacher = Teacher(first_name="Dismiss", last_name="Teacher", active=True)
        db.session.add(teacher)
        db.session.flush()

        et = EventTeacher(event_id=event.id, teacher_id=teacher.id, status="registered")
        db.session.add(et)
        db.session.commit()

        from services.draft_review_service import dismiss_draft_events

        dismiss_draft_events(
            [event.id],
            cancellation_reason="Session never happened — draft review",
            user_id=review_admin.id,
        )

        refreshed_et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=teacher.id
        ).first()
        assert refreshed_et.status == "no_show"

    def test_resolves_needs_attention_flag_on_dismiss(
        self, app, draft_event_with_flag, review_admin
    ):
        event, flag = draft_event_with_flag

        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [event.id],
            cancellation_reason="Session never happened — draft review",
            user_id=review_admin.id,
        )

        assert result["flags_resolved"] == 1
        refreshed_flag = db.session.get(EventFlag, flag.id)
        assert refreshed_flag.is_resolved is True


# ── Edge-case / negative-path tests ─────────────────────────────────────


class TestPromoteEdgeCases:
    """Edge cases and error paths for promote_draft_events()."""

    def test_empty_event_ids_list(self, app, review_admin):
        """Promoting an empty list should be a no-op."""
        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([], user_id=review_admin.id)
        assert result["promoted"] == 0
        assert result["errors"] == []

    def test_nonexistent_event_id(self, app, review_admin):
        """Non-existent event ID should produce an error, not crash."""
        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([999999], user_id=review_admin.id)
        assert result["promoted"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]

    def test_mixed_valid_and_invalid_ids(
        self, app, draft_event_high_confidence, review_admin
    ):
        """Should promote valid events and report errors for invalid ones."""
        from services.draft_review_service import promote_draft_events

        result = promote_draft_events(
            [draft_event_high_confidence.id, 999999], user_id=review_admin.id
        )
        assert result["promoted"] == 1
        assert len(result["errors"]) == 1

        event = db.session.get(Event, draft_event_high_confidence.id)
        assert event.status == EventStatus.COMPLETED

    def test_promote_already_completed_event(self, app, review_admin):
        """Promoting an already-completed event should error gracefully."""
        event = Event(
            title="Already Completed",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([event.id], user_id=review_admin.id)
        assert result["promoted"] == 0
        assert len(result["errors"]) == 1
        assert "not Draft" in result["errors"][0]

    def test_promote_event_with_no_teachers(self, app, review_admin):
        """Events with zero teachers should still promote without error."""
        event = Event(
            title="No Teachers Draft",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            attended_student_count=5,
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import promote_draft_events

        result = promote_draft_events([event.id], user_id=review_admin.id)
        assert result["promoted"] == 1
        assert result["teachers_updated"] == 0
        assert result["errors"] == []


class TestDismissEdgeCases:
    """Edge cases and error paths for dismiss_draft_events()."""

    def test_empty_event_ids_list(self, app, review_admin):
        """Dismissing an empty list should be a no-op."""
        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [],
            cancellation_reason="test reason with enough chars",
            user_id=review_admin.id,
        )
        assert result["dismissed"] == 0
        assert result["errors"] == []

    def test_nonexistent_event_id(self, app, review_admin):
        """Non-existent event ID should produce an error."""
        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [999999],
            cancellation_reason="test reason with enough chars",
            user_id=review_admin.id,
        )
        assert result["dismissed"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0]

    def test_dismiss_already_cancelled_event(self, app, review_admin):
        """Dismissing an already-cancelled event should error gracefully."""
        event = Event(
            title="Already Cancelled",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CANCELLED,
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [event.id],
            cancellation_reason="test reason with enough chars",
            user_id=review_admin.id,
        )
        assert result["dismissed"] == 0
        assert len(result["errors"]) == 1
        assert "not Draft" in result["errors"][0]

    def test_dismiss_event_with_no_teachers(self, app, review_admin):
        """Events with zero teachers should still dismiss without error."""
        event = Event(
            title="No Teachers Dismiss",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import dismiss_draft_events

        result = dismiss_draft_events(
            [event.id],
            cancellation_reason="Session never happened — draft review",
            user_id=review_admin.id,
        )
        assert result["dismissed"] == 1
        assert result["errors"] == []


class TestQueueEdgeCases:
    """Edge cases for get_draft_review_queue()."""

    def test_empty_database_returns_empty_queue(self, app):
        """Queue should return empty results when no events exist."""
        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        assert result["summary"]["total"] == 0
        assert result["events"] == []

    def test_excludes_completed_events(self, app):
        """Completed events should not appear in draft queue."""
        event = Event(
            title="Completed Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            format=EventFormat.VIRTUAL,
        )
        db.session.add(event)
        db.session.commit()

        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue()
        assert result["summary"]["total"] == 0

    def test_district_filter(self, app):
        """Queue should filter by district_partner when specified."""
        event_a = Event(
            title="KCKPS Draft",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            district_partner="Kansas City, KS (KCKPS) Public Schools",
            format=EventFormat.VIRTUAL,
        )
        event_b = Event(
            title="KCPS Draft",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.DRAFT,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            district_partner="Kansas City, MO (KCPS) Public Schools",
            format=EventFormat.VIRTUAL,
        )
        db.session.add_all([event_a, event_b])
        db.session.commit()

        from services.draft_review_service import get_draft_review_queue

        result = get_draft_review_queue(
            district_name="Kansas City, KS (KCKPS) Public Schools"
        )
        assert result["summary"]["total"] == 1
        assert result["events"][0]["event"].id == event_a.id
