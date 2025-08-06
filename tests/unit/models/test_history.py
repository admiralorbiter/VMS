from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.event import Event
from models.history import History, HistoryType
from models.volunteer import Volunteer


def test_new_history(app, test_event, test_volunteer):
    """Test creating a new history record with all fields"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
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
            assert history.volunteer_id == volunteer.id
            assert history.action == "test_action"
            assert history.summary == "Test summary"
            assert history.description == "Test description"
            assert history.activity_type == "Test Activity"
            assert isinstance(history.activity_date, datetime)
            assert history.activity_status == "Completed"
            assert history.salesforce_id == "a005f000003XNa7AAG"
            assert history.is_deleted is False
            assert isinstance(history.created_at, datetime)
            assert isinstance(history.last_modified_at, datetime)
            assert history.additional_metadata == {"test_key": "test_value"}
            assert history.history_type == "note"

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_history_type_enum_conversion(app, test_volunteer):
    """Test HistoryType enum conversion"""
    with app.app_context():
        history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc))

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
            history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc), notes="")  # Should raise error

        # Test missing volunteer_id
        with pytest.raises(Exception):
            history = History(activity_date=datetime.now(timezone.utc))
            db.session.add(history)
            db.session.flush()


def test_is_recent_property(app, test_volunteer):
    """Test is_recent property with different dates"""
    with app.app_context():
        # Test recent history
        recent_history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc))
        assert recent_history.is_recent is True

        # Test old history
        old_history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc) - timedelta(days=31))
        assert old_history.is_recent is False


def test_to_dict_method(app, test_volunteer, test_user):
    """Test to_dict method with various field combinations"""
    with app.app_context():
        history = History(
            volunteer_id=test_volunteer.id,
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
        assert dict_repr["volunteer_id"] == test_volunteer.id
        assert dict_repr["notes"] == "Test notes"
        assert dict_repr["history_type"] == "note"
        assert dict_repr["metadata"] == {"key": "value"}
        assert dict_repr["created_by"] == test_user.username


def test_soft_delete_and_restore(app, test_volunteer, test_user):
    """Test soft delete and restore functionality with user tracking"""
    with app.app_context():
        history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc))

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
        history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc))
        db.session.add(history)
        db.session.flush()

        assert history.id is not None
        assert history.history_type == "note"  # Default value
        assert history.additional_metadata is None
        assert history.description is None


def test_history_type_case_sensitivity(app, test_volunteer):
    """Test history_type case sensitivity handling"""
    with app.app_context():
        history = History(volunteer_id=test_volunteer.id, activity_date=datetime.now(timezone.utc))

        # Test different case variations
        history.history_type_enum = "NOTE"
        assert history.history_type == "note"

        history.history_type_enum = "Activity"
        assert history.history_type == "activity"


def test_history_relationships(app, test_event, test_volunteer):
    """Test history relationships with Event and Volunteer"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(event_id=event.id, volunteer_id=volunteer.id, action="test_relationship", summary="Test relationship summary")
            db.session.add(history)
            db.session.flush()

            # Test relationship with Event
            assert history.event_id == event.id
            assert history in event.histories.all()

            # Test relationship with Volunteer
            assert history.volunteer_id == volunteer.id
            assert history in volunteer.histories.all()

            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()


def test_history_cascade_delete(app, test_event, test_volunteer):
    """Test cascade delete behavior"""
    with app.app_context():
        db.session.remove()
        db.session.begin()

        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)

        try:
            history = History(event_id=event.id, volunteer_id=volunteer.id, action="test_cascade", summary="Test cascade summary")
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
            history = History(event_id=event.id, volunteer_id=volunteer.id, action="test_soft_delete", summary="Test soft delete summary")
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
            history = History(event_id=event.id, volunteer_id=volunteer.id, action="test_timestamps", summary="Test timestamps summary")
            db.session.add(history)
            db.session.commit()

            # Store initial timestamps
            created_at = history.created_at
            last_modified = history.last_modified_at

            # Update the record
            history.summary = "Updated summary"
            db.session.commit()

            # Verify timestamps
            assert history.created_at == created_at  # Should not change
            # Add a small delay to ensure timestamp difference
            import time

            time.sleep(0.001)
            assert history.last_modified_at >= last_modified  # Should be updated

        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()
