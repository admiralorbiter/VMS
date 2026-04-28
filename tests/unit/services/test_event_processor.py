from datetime import datetime, timezone

import pytest

from models import db
from models.data_quality_flag import DataQualityFlag, DataQualityIssueType
from models.event import Event
from models.volunteer import Volunteer
from services.salesforce.processors.event import process_participation_row


@pytest.fixture
def clean_db(app):
    """Fixture to ensure a clean database for testing."""
    with app.app_context():
        DataQualityFlag.query.delete()
        Event.query.delete()
        Volunteer.query.delete()
        db.session.commit()
        yield
        DataQualityFlag.query.delete()
        Event.query.delete()
        Volunteer.query.delete()
        db.session.commit()


def test_process_participation_missing_volunteer(clean_db, app):
    """Scenario 1: process_participation_row() with missing volunteer -> error_count+1, DQ flag created."""
    with app.app_context():
        # Create event but no volunteer
        event = Event(
            salesforce_id="SESSION001",
            title="Test Event",
            start_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        )
        db.session.add(event)
        db.session.commit()

        row = {
            "Id": "PARTICIPATION001",
            "Contact__c": "MISSING_VOLUNTEER",
            "Session__c": "SESSION001",
            "Status__c": "Attended",
        }

        errors = []
        success, error = process_participation_row(row, 0, 0, errors)

        assert success == 0
        assert error == 1
        assert len(errors) == 1
        assert "MISSING_VOLUNTEER" in errors[0]

        # Check DQ flag
        flag = DataQualityFlag.query.filter_by(
            entity_sf_id="PARTICIPATION001",
            issue_type=DataQualityIssueType.UNMATCHED_SF_PARTICIPATION,
        ).first()
        assert flag is not None
        assert flag.status == "open"
        assert "volunteer" in flag.details


def test_process_participation_missing_event(clean_db, app):
    """Scenario 2: process_participation_row() with missing event -> error_count+1, DQ flag created."""
    with app.app_context():
        # Create volunteer but no event
        vol = Volunteer(
            salesforce_individual_id="CONTACT001",
            first_name="Test",
            last_name="Volunteer",
        )
        db.session.add(vol)
        db.session.commit()

        row = {
            "Id": "PARTICIPATION002",
            "Contact__c": "CONTACT001",
            "Session__c": "MISSING_EVENT",
            "Status__c": "Attended",
        }

        errors = []
        success, error = process_participation_row(row, 0, 0, errors)

        assert success == 0
        assert error == 1
        assert len(errors) == 1

        flag = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION002").first()
        assert flag is not None
        assert "event" in flag.details


def test_process_participation_both_missing(clean_db, app):
    """Scenario 3: process_participation_row() with both missing -> single flag with both in details."""
    with app.app_context():
        row = {
            "Id": "PARTICIPATION003",
            "Contact__c": "MISSING_CONTACT",
            "Session__c": "MISSING_SESSION",
            "Status__c": "Attended",
        }

        errors = []
        success, error = process_participation_row(row, 0, 0, errors)

        assert success == 0
        assert error == 1

        flag = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION003").first()
        assert flag is not None
        assert "volunteer" in flag.details
        assert "event" in flag.details


def test_process_participation_idempotent_flag(clean_db, app):
    """Scenario 4: process_participation_row() called twice -> only one DQ flag."""
    with app.app_context():
        row = {
            "Id": "PARTICIPATION004",
            "Contact__c": "MISSING",
            "Session__c": "MISSING",
            "Status__c": "Attended",
        }

        process_participation_row(row, 0, 0, [])
        process_participation_row(row, 0, 0, [])

        flags = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION004").all()
        assert len(flags) == 1


def test_process_participation_success(clean_db, app):
    """Scenario 5: process_participation_row() with valid data -> success, no flag."""
    with app.app_context():
        vol = Volunteer(
            salesforce_individual_id="CONTACT001",
            first_name="Test",
            last_name="Volunteer",
        )
        event = Event(
            salesforce_id="SESSION001",
            title="Test Event",
            start_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        )
        db.session.add_all([vol, event])
        db.session.commit()

        row = {
            "Id": "PARTICIPATION005",
            "Contact__c": "CONTACT001",
            "Session__c": "SESSION001",
            "Status__c": "Attended",
            "Delivery_Hours__c": "2.5",
        }

        errors = []
        success, error = process_participation_row(row, 0, 0, errors)

        assert success == 1
        assert error == 0
        assert len(errors) == 0

        flag = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION005").first()
        assert flag is None


def test_process_participation_auto_resolve(clean_db, app):
    """Scenario 6: After successful import of previously-flagged ID -> flag auto-resolved."""
    with app.app_context():
        # First simulate a failure
        row = {
            "Id": "PARTICIPATION006",
            "Contact__c": "CONTACT006",
            "Session__c": "SESSION006",
            "Status__c": "Attended",
        }
        process_participation_row(row, 0, 0, [])

        flag = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION006").first()
        assert flag.status == "open"

        # Now create the missing data
        vol = Volunteer(
            salesforce_individual_id="CONTACT006",
            first_name="Test",
            last_name="Volunteer",
        )
        event = Event(
            salesforce_id="SESSION006",
            title="Test Event",
            start_date=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            end_date=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        )
        db.session.add_all([vol, event])
        db.session.commit()

        # Run again
        process_participation_row(row, 0, 0, [])

        # Check auto-resolution
        flag = DataQualityFlag.query.filter_by(entity_sf_id="PARTICIPATION006").first()
        assert flag.status == "auto_fixed"
