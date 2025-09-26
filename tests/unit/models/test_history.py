from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.contact import Contact
from models.event import Event
from models.history import History, HistoryType
from models.teacher import Teacher
from models.volunteer import Volunteer


@pytest.mark.slow
def test_new_history(app, test_event, test_volunteer):
    """Test creating a new history record with all fields"""
    with app.app_context():
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                contact_id=volunteer.id,
                action="test_action",
                summary="Test summary",
                description="Test description",
                activity_type="Test Activity",
                activity_date=datetime.now(timezone.utc),
                activity_status="Completed",
                history_type="note",
                salesforce_id="a005f000003XNa7AAG",
                additional_metadata={"test_key": "test_value"},
            )

            db.session.add(history)
            db.session.flush()

            # Basic assertions
            assert history.id is not None
            assert history.event_id == event.id
            assert history.contact_id == volunteer.id
            assert (
                history.volunteer_id == volunteer.id
            )  # Backward compatibility property
            assert history.contact_type == "volunteer"  # New property
            assert history.action == "test_action"
            assert history.summary == "Test summary"
            assert history.description == "Test description"
            assert history.activity_type == "Test Activity"
            assert isinstance(history.activity_date, datetime)
            assert history.activity_status == "Completed"
            assert history.salesforce_id == "a005f000003XNa7AAG"
            assert history.is_deleted is False
            assert isinstance(history.created_at, datetime)
            assert history.additional_metadata == {"test_key": "test_value"}
            assert history.history_type == "note"

            db.session.commit()
        except:
            db.session.rollback()
            raise


def test_history_type_enum_conversion(app, test_volunteer):
    """Test HistoryType enum conversion"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id, activity_date=datetime.now(timezone.utc)
        )

        # Test setting via enum
        history.history_type_enum = HistoryType.ACTIVITY
        assert history.history_type == "activity"
        assert history.history_type_enum == HistoryType.ACTIVITY

        # Test setting via string
        history.history_type_enum = "note"
        assert history.history_type == "note"
        assert history.history_type_enum == HistoryType.NOTE

        # Test invalid type handling
        history.history_type = "invalid_type"
        assert history.history_type_enum == HistoryType.OTHER


def test_history_validation(app, test_volunteer):
    """Test validation rules"""
    with app.app_context():
        # Test empty notes validation
        with pytest.raises(ValueError):
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                notes="",  # Should raise error
            )

        # Test missing contact_id
        with pytest.raises(Exception):
            history = History(activity_date=datetime.now(timezone.utc))
            db.session.add(history)
            db.session.flush()


def test_is_recent_property(app, test_volunteer):
    """Test is_recent property with different dates"""
    with app.app_context():
        # Test recent history
        recent_history = History(
            contact_id=test_volunteer.id, activity_date=datetime.now(timezone.utc)
        )
        assert recent_history.is_recent is True

        # Test old history
        old_history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc) - timedelta(days=31),
        )
        assert old_history.is_recent is False


def test_to_dict_method(app, test_volunteer, test_user):
    """Test to_dict method with various field combinations"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            notes="Test notes",
            history_type="note",
            created_by_id=test_user.id,
            additional_metadata={"key": "value"},
        )

        # Add to session and flush to establish relationships
        db.session.add(history)
        db.session.flush()

        dict_repr = history.to_dict()
        assert dict_repr["contact_id"] == test_volunteer.id
        assert dict_repr["volunteer_id"] == test_volunteer.id  # Backward compatibility
        assert dict_repr["contact_type"] == "volunteer"  # New property
        assert dict_repr["notes"] == "Test notes"
        assert dict_repr["history_type"] == "note"
        assert dict_repr["metadata"] == {"key": "value"}
        assert dict_repr["created_by"] == test_user.username


def test_soft_delete_and_restore(app, test_volunteer, test_user):
    """Test soft delete and restore functionality with user tracking"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id, activity_date=datetime.now(timezone.utc)
        )

        # Test soft delete
        history.soft_delete(test_user.id)
        assert history.is_deleted is True
        assert history.updated_by_id == test_user.id

        # Test restore
        history.restore(test_user.id)
        assert history.is_deleted is False
        assert history.updated_by_id == test_user.id


# New edge cases to test:


def test_history_with_null_optional_fields(app, test_volunteer):
    """Test creating history with minimal required fields"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id, activity_date=datetime.now(timezone.utc)
        )
        db.session.add(history)
        db.session.flush()

        assert history.id is not None
        assert history.history_type == "note"  # Default value
        assert history.additional_metadata is None
        assert history.description is None


def test_history_type_case_sensitivity(app, test_volunteer):
    """Test history_type case sensitivity handling"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id, activity_date=datetime.now(timezone.utc)
        )

        # Test different case variations
        history.history_type_enum = "NOTE"
        assert history.history_type == "note"

        history.history_type_enum = "Activity"
        assert history.history_type == "activity"


@pytest.mark.slow
def test_history_relationships(app, test_event, test_volunteer):
    """Test history relationships with Event and Volunteer"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                contact_id=volunteer.id,
                action="test_relationship",
                summary="Test relationship summary",
            )
            db.session.add(history)
            db.session.flush()

            # Test relationship with Event
            assert history.event_id == event.id
            # Use limit(1) to avoid loading all histories
            event_histories = event.histories.limit(1).all()
            assert len(event_histories) > 0

            # Test relationship with Volunteer
            assert history.contact_id == volunteer.id
            assert history.volunteer_id == volunteer.id  # Backward compatibility
            # Use limit(1) to avoid loading all histories
            volunteer_histories = volunteer.histories.limit(1).all()
            assert len(volunteer_histories) > 0

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


@pytest.mark.slow
def test_history_cascade_delete(app, test_event, test_volunteer):
    """Test cascade delete behavior"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                contact_id=volunteer.id,
                action="test_cascade",
                summary="Test cascade summary",
            )
            db.session.add(history)
            db.session.flush()

            # Get the history ID for later verification
            history_id = history.id

            # Delete the volunteer (should cascade to history)
            db.session.delete(volunteer)
            db.session.flush()

            # Verify history record was deleted
            deleted_history = db.session.get(History, history_id)
            assert deleted_history is None

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_history_soft_delete(app, test_event, test_volunteer):
    """Test soft delete functionality"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                contact_id=volunteer.id,
                action="test_soft_delete",
                summary="Test soft delete summary",
            )
            db.session.add(history)
            db.session.flush()

            # Soft delete the record
            history.is_deleted = True
            db.session.flush()

            # Verify the record still exists but is marked as deleted
            assert history.is_deleted is True

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_history_timestamps(app, test_event, test_volunteer):
    """Test timestamp behavior"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                contact_id=volunteer.id,
                action="test_timestamps",
                summary="Test timestamps summary",
            )
            db.session.add(history)
            db.session.commit()

            # Store initial timestamp
            created_at = history.created_at

            # Update the record
            history.summary = "Updated summary"
            db.session.commit()

            # Verify timestamp
            assert history.created_at == created_at  # Should not change
            # Note: updated_at column was removed from schema

        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


# New tests for enhanced contact functionality


@pytest.mark.slow
def test_history_with_teacher_contact(app, test_event):
    """Test creating history with a teacher contact"""
    with app.app_context():
        # Create a test teacher
        teacher = Teacher(
            first_name="Test", last_name="Teacher", salesforce_individual_id="T001"
        )
        db.session.add(teacher)
        db.session.flush()

        try:
            history = History(
                event_id=test_event.id,
                contact_id=teacher.id,
                action="teacher_activity",
                summary="Teacher participated in event",
                activity_date=datetime.now(timezone.utc),
                history_type="activity",
            )
            db.session.add(history)
            db.session.flush()

            # Test the new properties
            assert history.contact_id == teacher.id
            # Properties work after the object is saved and relationships are loaded
            db.session.flush()
            assert history.teacher_id == teacher.id  # Should return teacher ID
            assert history.volunteer_id is None  # Should be None for teachers
            assert history.contact_type == "teacher"

            # Test to_dict output
            dict_repr = history.to_dict()
            assert dict_repr["contact_id"] == teacher.id
            assert dict_repr["teacher_id"] == teacher.id
            assert dict_repr["volunteer_id"] is None
            assert dict_repr["contact_type"] == "teacher"

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.delete(teacher)
            db.session.commit()


def test_history_contact_type_properties(app, test_volunteer):
    """Test contact type properties for different contact types"""
    with app.app_context():
        # Test with volunteer
        volunteer_history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            summary="Volunteer activity",
        )

        # Save to database so properties can access relationships
        db.session.add(volunteer_history)
        db.session.flush()

        assert volunteer_history.contact_type == "volunteer"
        assert volunteer_history.volunteer_id == test_volunteer.id
        assert volunteer_history.teacher_id is None

        # Test with teacher
        teacher = Teacher(
            first_name="Test", last_name="Teacher", salesforce_individual_id="T002"
        )
        db.session.add(teacher)
        db.session.flush()

        try:
            teacher_history = History(
                contact_id=teacher.id,
                activity_date=datetime.now(timezone.utc),
                summary="Teacher activity",
            )

            # Save to database so properties can access relationships
            db.session.add(teacher_history)
            db.session.flush()

            assert teacher_history.contact_type == "teacher"
            assert teacher_history.teacher_id == teacher.id
            assert teacher_history.volunteer_id is None

            db.session.delete(teacher)
            db.session.commit()
        except:
            db.session.rollback()
            raise


def test_history_backward_compatibility(app, test_volunteer):
    """Test that old volunteer_id property still works for backward compatibility"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            summary="Backward compatibility test",
        )

        # Save to database so properties can access relationships
        db.session.add(history)
        db.session.flush()

        # The volunteer_id property should still work
        assert history.volunteer_id == test_volunteer.id

        # But we can't set it directly (it's read-only)
        with pytest.raises(AttributeError):
            history.volunteer_id = 999  # This should fail
