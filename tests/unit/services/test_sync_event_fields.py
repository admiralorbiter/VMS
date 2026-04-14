"""
Tests for Sprint 2: sync_event_participant_fields() and ensure_event_teacher()
"""

from datetime import datetime, timezone

import pytest

from models import db
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.teacher import Teacher, TeacherStatus
from services.teacher_service import ensure_event_teacher, sync_event_participant_fields


@pytest.fixture
def sprint2_event(app):
    """Create a test event for Sprint 2 tests."""
    event = Event(
        title="Test Sprint 2 Session",
        type=EventType.VIRTUAL_SESSION,
        format=EventFormat.VIRTUAL,
        status=EventStatus.COMPLETED,
        start_date=datetime.now(timezone.utc),
    )
    db.session.add(event)
    db.session.commit()
    yield event
    # Cleanup handled by app fixture teardown


@pytest.fixture
def sprint2_teachers(app):
    """Create test teachers for Sprint 2 tests."""
    t1 = Teacher(
        first_name="Alice",
        last_name="Smith",
        status=TeacherStatus.ACTIVE,
        active=True,
    )
    t2 = Teacher(
        first_name="Bob",
        last_name="Jones",
        status=TeacherStatus.ACTIVE,
        active=True,
    )
    db.session.add_all([t1, t2])
    db.session.commit()
    yield t1, t2


class TestEnsureEventTeacher:
    """Tests for ensure_event_teacher()."""

    def test_create_new(self, app, sprint2_event, sprint2_teachers):
        """Should create a new EventTeacher record."""
        t1, _ = sprint2_teachers
        et = ensure_event_teacher(sprint2_event.id, t1.id)
        db.session.flush()
        assert et is not None
        assert et.event_id == sprint2_event.id
        assert et.teacher_id == t1.id

    def test_idempotent(self, app, sprint2_event, sprint2_teachers):
        """Calling twice should return the same record, not create a duplicate."""
        t1, _ = sprint2_teachers
        ensure_event_teacher(sprint2_event.id, t1.id)
        db.session.flush()
        ensure_event_teacher(sprint2_event.id, t1.id)
        db.session.flush()

        count = EventTeacher.query.filter_by(
            event_id=sprint2_event.id, teacher_id=t1.id
        ).count()
        assert count == 1

    def test_with_kwargs(self, app, sprint2_event, sprint2_teachers):
        """Should pass optional fields to the EventTeacher."""
        t1, _ = sprint2_teachers
        et = ensure_event_teacher(
            sprint2_event.id, t1.id, status="attended", is_simulcast=True
        )
        db.session.flush()
        assert et.status == "attended"
        assert et.is_simulcast is True

    def test_update_existing_kwargs(self, app, sprint2_event, sprint2_teachers):
        """Should update optional fields on existing record."""
        t1, _ = sprint2_teachers
        ensure_event_teacher(sprint2_event.id, t1.id, status="registered")
        db.session.flush()
        et2 = ensure_event_teacher(sprint2_event.id, t1.id, status="attended")
        db.session.flush()
        assert et2.status == "attended"


class TestSyncEventParticipantFields:
    """Tests for sync_event_participant_fields()."""

    def test_sync_with_teachers(self, app, sprint2_event, sprint2_teachers):
        """Should populate event.educators from EventTeacher records."""
        t1, t2 = sprint2_teachers
        ensure_event_teacher(sprint2_event.id, t1.id)
        ensure_event_teacher(sprint2_event.id, t2.id)
        db.session.flush()

        sync_event_participant_fields(sprint2_event)

        assert sprint2_event.educators is not None
        assert "Alice Smith" in sprint2_event.educators
        assert "Bob Jones" in sprint2_event.educators
        assert sprint2_event.educator_ids is not None

    def test_sync_empty(self, app, sprint2_event):
        """Should clear fields when no teachers are linked."""
        sprint2_event.educators = "Old Data"
        db.session.flush()

        sync_event_participant_fields(sprint2_event)
        assert sprint2_event.educators is None
        assert sprint2_event.educator_ids is None

    def test_sync_educator_ids(self, app, sprint2_event, sprint2_teachers):
        """Should correctly build educator_ids from teacher IDs."""
        t1, _ = sprint2_teachers
        ensure_event_teacher(sprint2_event.id, t1.id)
        db.session.flush()

        sync_event_participant_fields(sprint2_event)

        assert str(t1.id) in sprint2_event.educator_ids

    def test_sync_deduplicates_names(self, app, sprint2_event, sprint2_teachers):
        """Should not duplicate educator names."""
        t1, _ = sprint2_teachers
        ensure_event_teacher(sprint2_event.id, t1.id)
        db.session.flush()

        sync_event_participant_fields(sprint2_event)

        # Educator name should appear exactly once
        assert sprint2_event.educators.count("Alice Smith") == 1
