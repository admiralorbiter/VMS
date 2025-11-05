import warnings
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


def test_validate_history_type_comprehensive(app, test_volunteer):
    """Test comprehensive history_type validation"""
    with app.app_context():
        # Test all enum values
        enum_values = [
            HistoryType.NOTE,
            HistoryType.ACTIVITY,
            HistoryType.STATUS_CHANGE,
            HistoryType.ENGAGEMENT,
            HistoryType.SYSTEM,
            HistoryType.OTHER,
        ]

        for enum_val in enum_values:
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                history_type=enum_val.value,
            )
            assert history.history_type == enum_val.value.lower()
            assert history.history_type_enum == enum_val

        # Test None handling (defaults to NOTE)
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            history_type=None,
        )
        assert history.history_type == HistoryType.NOTE.value

        # Test invalid values (fallback to OTHER with warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                history_type="completely_invalid",
            )
            assert history.history_type == HistoryType.OTHER.value
            assert len(w) > 0
            assert "Invalid history_type value" in str(w[0].message)

        # Test name-based lookup (e.g., "STATUS_CHANGE")
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
        )
        history.history_type = "STATUS_CHANGE"
        assert history.history_type == "status_change"
        assert history.history_type_enum == HistoryType.STATUS_CHANGE

        # Test case-insensitive string handling
        history.history_type = "ENGAGEMENT"
        assert history.history_type == "engagement"
        assert history.history_type_enum == HistoryType.ENGAGEMENT

        history.history_type = "system"
        assert history.history_type == "system"
        assert history.history_type_enum == HistoryType.SYSTEM


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

        # Test whitespace-only notes validation
        with pytest.raises(ValueError):
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                notes="   ",  # Should raise error
            )

        # Test notes with valid content
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            notes="Valid notes content",
        )
        assert history.notes == "Valid notes content"

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

        # Test boundary condition - exactly 30 days ago (should be recent)
        boundary_recent = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        assert boundary_recent.is_recent is True

        # Test boundary condition - exactly 31 days ago (should not be recent)
        boundary_old = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc) - timedelta(days=31),
        )
        assert boundary_old.is_recent is False

        # Test None activity_date edge case
        none_history = History(contact_id=test_volunteer.id, activity_date=None)
        assert none_history.is_recent is False


def test_to_dict_method(app, test_volunteer, test_user):
    """Test to_dict method with various field combinations"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            notes="Test notes",
            history_type="note",
            created_by_id=test_user.id,
            updated_by_id=test_user.id,
            email_message_id="test-email-id-123",
            additional_metadata={"key": "value"},
            salesforce_id="a005f000003XNa7AAG",
            action="test_action",
            summary="Test summary",
            description="Test description",
            activity_type="Test Activity",
            activity_status="Completed",
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
        assert dict_repr["email_message_id"] == "test-email-id-123"
        assert dict_repr["salesforce_id"] == "a005f000003XNa7AAG"
        assert dict_repr["action"] == "test_action"
        assert dict_repr["summary"] == "Test summary"
        assert dict_repr["description"] == "Test description"
        assert dict_repr["activity_type"] == "Test Activity"
        assert dict_repr["activity_status"] == "Completed"
        assert dict_repr["updated_at"] is None  # Column removed from schema
        assert isinstance(dict_repr["activity_date"], str)  # Should be ISO format
        assert isinstance(dict_repr["created_at"], str)  # Should be ISO format

        # Test with None values for optional fields
        history_minimal = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
        )
        db.session.add(history_minimal)
        db.session.flush()

        dict_minimal = history_minimal.to_dict()
        assert dict_minimal["email_message_id"] is None
        assert dict_minimal["salesforce_id"] is None
        assert dict_minimal["created_by"] is None
        assert dict_minimal["metadata"] is None
        assert dict_minimal["notes"] is None


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


def test_validate_activity_date(app, test_volunteer):
    """Test comprehensive activity_date validation"""
    with app.app_context():
        # Test string format parsing - ISO format
        history = History(
            contact_id=test_volunteer.id,
            activity_date="2024-01-15 10:00:00",
        )
        assert isinstance(history.activity_date, datetime)
        assert history.activity_date.tzinfo is not None  # Should be timezone-aware

        # Test ISO format with date only
        history = History(
            contact_id=test_volunteer.id,
            activity_date="2024-01-15",
        )
        assert isinstance(history.activity_date, datetime)

        # Test US date format
        history = History(
            contact_id=test_volunteer.id,
            activity_date="01/15/2024 10:00:00",
        )
        assert isinstance(history.activity_date, datetime)

        # Test US date format (date only)
        history = History(
            contact_id=test_volunteer.id,
            activity_date="01/15/2024",
        )
        assert isinstance(history.activity_date, datetime)

        # Test ISO format with T separator
        history = History(
            contact_id=test_volunteer.id,
            activity_date="2024-01-15T10:00:00",
        )
        assert isinstance(history.activity_date, datetime)

        # Test timezone-aware datetime
        aware_dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        history = History(
            contact_id=test_volunteer.id,
            activity_date=aware_dt,
        )
        assert history.activity_date == aware_dt
        assert history.activity_date.tzinfo is not None

        # Test timezone-naive datetime (should be converted to UTC with warning)
        naive_dt = datetime(2024, 1, 15, 10, 0, 0)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            history = History(
                contact_id=test_volunteer.id,
                activity_date=naive_dt,
            )
            assert history.activity_date.tzinfo is not None
            assert len(w) > 0
            assert "Timezone-naive datetime" in str(w[0].message)

        # Test None handling
        history = History(
            contact_id=test_volunteer.id,
            activity_date=None,
        )
        assert history.activity_date is None

        # Test empty string handling
        history = History(
            contact_id=test_volunteer.id,
            activity_date="",
        )
        assert history.activity_date is None

        # Test invalid date format (should return None with warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            history = History(
                contact_id=test_volunteer.id,
                activity_date="invalid-date-format",
            )
            assert history.activity_date is None
            assert len(w) > 0
            assert "Invalid date format" in str(w[0].message)

        # Test invalid type (should return None with warning)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            history = History(
                contact_id=test_volunteer.id,
                activity_date=12345,  # Invalid type
            )
            assert history.activity_date is None
            assert len(w) > 0
            assert "Invalid type" in str(w[0].message)


def test_validate_salesforce_id_field(app, test_volunteer):
    """Test Salesforce ID validation"""
    with app.app_context():
        # Test valid Salesforce ID
        valid_id = "a005f000003XNa7AAG"
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            salesforce_id=valid_id,
        )
        assert history.salesforce_id == valid_id

        # Test None handling
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            salesforce_id=None,
        )
        assert history.salesforce_id is None

        # Test invalid Salesforce ID format (should raise ValueError)
        with pytest.raises(ValueError):
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                salesforce_id="invalid",  # Too short
            )

        # Test invalid Salesforce ID - wrong length
        with pytest.raises(ValueError):
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                salesforce_id="a005f000003XNa7AA",  # 17 characters
            )

        # Test invalid Salesforce ID - contains invalid characters
        with pytest.raises(ValueError):
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
                salesforce_id="a005f000003XNa7AAG!",  # Contains invalid character
            )


def test_history_init_automatic_activity_date(app, test_volunteer):
    """Test automatic activity_date setting in __init__"""
    with app.app_context():
        # Create history without activity_date
        history = History(contact_id=test_volunteer.id)

        # Should automatically set activity_date to current time
        assert history.activity_date is not None
        assert isinstance(history.activity_date, datetime)
        assert history.activity_date.tzinfo is not None

        # Verify it's recent (within last few seconds)
        time_diff = (datetime.now(timezone.utc) - history.activity_date).total_seconds()
        assert time_diff >= 0  # Should be in the past or now
        assert time_diff < 5  # Should be within last 5 seconds

        # If activity_date is explicitly provided, use that instead
        specific_date = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        history2 = History(
            contact_id=test_volunteer.id,
            activity_date=specific_date,
        )
        assert history2.activity_date == specific_date


def test_history_repr(app, test_volunteer):
    """Test __repr__ method"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            history_type="activity",
        )
        db.session.add(history)
        db.session.flush()

        repr_str = repr(history)
        assert "History" in repr_str
        assert str(history.id) in repr_str
        assert "activity" in repr_str
        assert "2024-01-15" in repr_str


def test_email_message_id_field(app, test_volunteer):
    """Test email_message_id field for email tracking"""
    with app.app_context():
        # Test setting email_message_id
        email_id = "test-email-message-id-123"
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            email_message_id=email_id,
        )
        assert history.email_message_id == email_id

        # Test None email_message_id
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            email_message_id=None,
        )
        assert history.email_message_id is None

        # Test email_message_id in to_dict
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            email_message_id=email_id,
        )
        db.session.add(history)
        db.session.flush()

        dict_repr = history.to_dict()
        assert dict_repr["email_message_id"] == email_id


def test_history_created_by_relationship(app, test_volunteer, test_user):
    """Test comprehensive created_by relationship"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            created_by_id=test_user.id,
        )

        db.session.add(history)
        db.session.flush()
        history_id = history.id

        # Test relationship access
        assert history.created_by_id == test_user.id
        assert history.created_by is not None
        assert history.created_by.id == test_user.id
        assert history.created_by.username == test_user.username

        # Test backref - compare by ID to avoid SQLAlchemy object comparison issues
        created_histories = test_user.created_histories.all()
        created_history_ids = [h.id for h in created_histories]
        assert history_id in created_history_ids

        # Test None created_by_id
        history2 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            created_by_id=None,
        )
        db.session.add(history2)
        db.session.flush()
        assert history2.created_by is None


def test_history_updated_by_relationship(app, test_volunteer, test_user):
    """Test comprehensive updated_by relationship"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            updated_by_id=test_user.id,
        )

        db.session.add(history)
        db.session.flush()
        history_id = history.id

        # Test relationship access
        assert history.updated_by_id == test_user.id
        assert history.updated_by is not None
        assert history.updated_by.id == test_user.id
        assert history.updated_by.username == test_user.username

        # Test backref - compare by ID to avoid SQLAlchemy object comparison issues
        updated_histories = test_user.updated_histories.all()
        updated_history_ids = [h.id for h in updated_histories]
        assert history_id in updated_history_ids

        # Test None updated_by_id
        history2 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            updated_by_id=None,
        )
        db.session.add(history2)
        db.session.flush()
        assert history2.updated_by is None

        # Test updated_by_id setting via soft_delete and restore
        history3 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
        )
        db.session.add(history3)
        db.session.flush()

        history3.soft_delete(test_user.id)
        assert history3.updated_by_id == test_user.id
        assert history3.updated_by.id == test_user.id

        history3.restore(test_user.id)
        assert history3.updated_by_id == test_user.id


@pytest.mark.slow
def test_history_event_cascade_delete(app, test_event, test_volunteer):
    """Test event cascade delete behavior"""
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
                action="test_event_cascade",
                summary="Test event cascade summary",
            )
            db.session.add(history)
            db.session.flush()

            # Get the history ID for later verification
            history_id = history.id

            # Delete the event (should cascade to history)
            db.session.delete(event)
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


def test_history_type_enum_all_values(app, test_volunteer):
    """Test all HistoryType enum values"""
    with app.app_context():
        # Test all enum values
        enum_tests = [
            (HistoryType.NOTE, "note"),
            (HistoryType.ACTIVITY, "activity"),
            (HistoryType.STATUS_CHANGE, "status_change"),
            (HistoryType.ENGAGEMENT, "engagement"),
            (HistoryType.SYSTEM, "system"),
            (HistoryType.OTHER, "other"),
        ]

        for enum_val, expected_str in enum_tests:
            history = History(
                contact_id=test_volunteer.id,
                activity_date=datetime.now(timezone.utc),
            )
            history.history_type_enum = enum_val
            assert history.history_type == expected_str
            assert history.history_type_enum == enum_val


def test_history_type_choices(app):
    """Test HistoryType FormEnum integration"""
    with app.app_context():
        # Test choices() method for form integration
        choices = HistoryType.choices()
        assert isinstance(choices, list)
        assert len(choices) > 0

        # Verify all enum values are in choices
        # FormEnum.choices() returns [(member.name, member.value), ...]
        # So choice[0] is the enum name (e.g., "NOTE") and choice[1] is the value (e.g., "note")
        enum_values = [
            HistoryType.NOTE,
            HistoryType.ACTIVITY,
            HistoryType.STATUS_CHANGE,
            HistoryType.ENGAGEMENT,
            HistoryType.SYSTEM,
            HistoryType.OTHER,
        ]
        choice_names = [
            choice[0] for choice in choices
        ]  # First element is the enum name
        choice_vals = [
            choice[1] for choice in choices
        ]  # Second element is the enum value

        for enum_val in enum_values:
            # Check that enum name is in choices
            assert enum_val.name in choice_names
            # Check that enum value is in choices
            assert enum_val.value in choice_vals

        # Test choices_required() method
        choices_required = HistoryType.choices_required()
        assert isinstance(choices_required, list)
        assert len(choices_required) > 0
        # Should have same structure as choices()
        assert len(choices_required) == len(choices)


def test_history_with_all_optional_fields(app, test_volunteer, test_user, test_event):
    """Test history with all optional fields populated"""
    with app.app_context():
        history = History(
            contact_id=test_volunteer.id,
            event_id=test_event.id,
            activity_date=datetime.now(timezone.utc),
            action="comprehensive_test",
            summary="Test with all fields",
            description="Comprehensive test description",
            activity_type="Test Activity Type",
            activity_status="In Progress",
            history_type="activity",
            notes="Comprehensive test notes",
            email_message_id="test-email-123",
            salesforce_id="a005f000003XNa7AAG",
            created_by_id=test_user.id,
            updated_by_id=test_user.id,
            additional_metadata={"test": "data", "nested": {"key": "value"}},
        )

        db.session.add(history)
        db.session.flush()

        # Verify all fields
        assert history.contact_id == test_volunteer.id
        assert history.event_id == test_event.id
        assert history.action == "comprehensive_test"
        assert history.summary == "Test with all fields"
        assert history.description == "Comprehensive test description"
        assert history.activity_type == "Test Activity Type"
        assert history.activity_status == "In Progress"
        assert history.history_type == "activity"
        assert history.notes == "Comprehensive test notes"
        assert history.email_message_id == "test-email-123"
        assert history.salesforce_id == "a005f000003XNa7AAG"
        assert history.created_by_id == test_user.id
        assert history.updated_by_id == test_user.id
        assert history.additional_metadata == {
            "test": "data",
            "nested": {"key": "value"},
        }


def test_history_additional_metadata_json(app, test_volunteer):
    """Test JSON metadata handling"""
    with app.app_context():
        # Test with simple JSON metadata
        simple_metadata = {"key": "value", "number": 123}
        history = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            additional_metadata=simple_metadata,
        )
        assert history.additional_metadata == simple_metadata

        # Test with nested JSON metadata
        nested_metadata = {
            "level1": {"level2": {"level3": "deep_value"}, "array": [1, 2, 3]}
        }
        history2 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            additional_metadata=nested_metadata,
        )
        assert history2.additional_metadata == nested_metadata
        assert (
            history2.additional_metadata["level1"]["level2"]["level3"] == "deep_value"
        )

        # Test with None metadata
        history3 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            additional_metadata=None,
        )
        assert history3.additional_metadata is None

        # Test metadata in to_dict
        history4 = History(
            contact_id=test_volunteer.id,
            activity_date=datetime.now(timezone.utc),
            additional_metadata={"test": "metadata"},
        )
        db.session.add(history4)
        db.session.flush()

        dict_repr = history4.to_dict()
        assert dict_repr["metadata"] == {"test": "metadata"}
