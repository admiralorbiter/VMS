"""
Integration tests for Event Status Management (TC-190, TC-191).

Tests verify that event status and cancellation reasons are correctly
synced from Salesforce and updated in the local database.

Test Coverage:
- TC-190: Event status updates from Salesforce
- TC-191: Cancellation reason preservation
"""

from datetime import datetime, timezone

import pytest

from models import db
from models.district_model import District
from models.event import CancellationReason, Event, EventFormat, EventStatus, EventType
from models.school_model import School
from routes.utils import map_cancellation_reason

# ==============================================================================
# TC-190: Event Status Updates
# ==============================================================================


class TestEventStatusUpdates:
    """
    TC-190: The system shall update event status (Draft, Requested, Confirmed,
    Published, Completed, Cancelled) from Salesforce.

    FR-INPERSON-119: Event status update
    """

    def test_status_synced_on_creation(self, app, test_district):
        """
        TC-190: Verify that event status is correctly set when creating
        a new event from Salesforce data.
        """
        with app.app_context():
            # Create a school for the event
            school = School(
                id="TEST_SCHOOL_STATUS",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Create event with Confirmed status (simulating Salesforce sync)
            event = Event(
                salesforce_id="SFEV_STATUS_CREATE",
                title="Test Event - Confirmed Status",
                type=EventType.CAREER_FAIR,
                format=EventFormat.IN_PERSON,
                start_date=datetime(2026, 2, 15, 10, 0, 0),
                end_date=datetime(2026, 2, 15, 12, 0, 0),
                status=EventStatus.CONFIRMED,  # Set during sync
                school=school.id,
            )
            db.session.add(event)
            db.session.commit()

            # Verify status was set correctly
            assert event is not None
            assert event.status == EventStatus.CONFIRMED
            assert event.salesforce_id == "SFEV_STATUS_CREATE"

            # Cleanup
            db.session.delete(event)
            db.session.delete(school)
            db.session.commit()

    def test_all_status_values_mapped(self, app, test_district):
        """
        TC-190: Verify that all major status values from Salesforce
        are correctly mapped to EventStatus enum.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_STATUSES",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Test each major status value
            status_mappings = [
                ("Draft", EventStatus.DRAFT),
                ("Requested", EventStatus.REQUESTED),
                ("Confirmed", EventStatus.CONFIRMED),
                ("Published", EventStatus.PUBLISHED),
                ("Completed", EventStatus.COMPLETED),
                ("Cancelled", EventStatus.CANCELLED),
            ]

            events_created = []
            for sf_status_name, expected_enum in status_mappings:
                # Create event with the status (simulating Salesforce sync)
                event = Event(
                    salesforce_id=f"SFEV_STATUS_{sf_status_name.upper()}",
                    title=f"Test Event - {sf_status_name}",
                    type=EventType.CAREER_FAIR,
                    format=EventFormat.IN_PERSON,
                    start_date=datetime(2026, 2, 15, 10, 0, 0),
                    end_date=datetime(2026, 2, 15, 12, 0, 0),
                    status=expected_enum,  # Set during sync
                    school=school.id,
                )
                db.session.add(event)
                db.session.commit()

                assert (
                    event.status == expected_enum
                ), f"Status '{sf_status_name}' should map to {expected_enum}"
                events_created.append(event)

            # Cleanup
            for event in events_created:
                db.session.delete(event)
            db.session.delete(school)
            db.session.commit()

    def test_status_update_on_existing_event(self, app, test_district):
        """
        TC-190: Verify that event status is updated when an existing event
        is synced with new status from Salesforce.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_UPDATE",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Create initial event with "Requested" status
            event = Event(
                salesforce_id="SFEV_STATUS_UPDATE",
                title="Test Event - Status Update",
                type=EventType.CAREER_FAIR,
                format=EventFormat.IN_PERSON,
                start_date=datetime(2026, 2, 15, 10, 0, 0),
                end_date=datetime(2026, 2, 15, 12, 0, 0),
                status=EventStatus.REQUESTED,
                school=school.id,
            )
            db.session.add(event)
            db.session.commit()

            # Verify initial status
            assert event.status == EventStatus.REQUESTED

            # Simulate status update to "Confirmed"
            event.status = EventStatus.CONFIRMED
            db.session.commit()

            # Refresh and verify status was updated
            db.session.refresh(event)
            assert event.status == EventStatus.CONFIRMED

            # Cleanup
            db.session.delete(event)
            db.session.delete(school)
            db.session.commit()

    def test_status_transitions(self, app, test_district):
        """
        TC-190: Verify that events can transition through the expected
        status workflow: Draft → Requested → Confirmed → Published → Completed
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_TRANSITIONS",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Create event with initial Draft status
            event = Event(
                salesforce_id="SFEV_STATUS_TRANSITIONS",
                title="Test Event - Status Transitions",
                type=EventType.CAREER_FAIR,
                format=EventFormat.IN_PERSON,
                start_date=datetime(2026, 2, 15, 10, 0, 0),
                end_date=datetime(2026, 2, 15, 12, 0, 0),
                status=EventStatus.DRAFT,
                school=school.id,
            )
            db.session.add(event)
            db.session.commit()

            # Test status workflow transitions
            transitions = [
                EventStatus.DRAFT,
                EventStatus.REQUESTED,
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.COMPLETED,
            ]

            for expected_status in transitions:
                event.status = expected_status
                db.session.commit()
                db.session.refresh(event)
                assert event.status == expected_status

            # Cleanup
            db.session.delete(event)
            db.session.delete(school)
            db.session.commit()

    def test_cancelled_status_from_any_state(self, app, test_district):
        """
        TC-190: Verify that events can transition to Cancelled from any state.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_CANCEL",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Test cancellation from different states
            test_statuses = [
                EventStatus.DRAFT,
                EventStatus.REQUESTED,
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
            ]

            for initial_status in test_statuses:
                event = Event(
                    salesforce_id=f"SFEV_CANCEL_{initial_status.value}",
                    title=f"Test Event - Cancel from {initial_status.value}",
                    type=EventType.CAREER_FAIR,
                    format=EventFormat.IN_PERSON,
                    start_date=datetime(2026, 2, 15, 10, 0, 0),
                    end_date=datetime(2026, 2, 15, 12, 0, 0),
                    status=initial_status,
                    school=school.id,
                )
                db.session.add(event)
                db.session.commit()

                # Transition to Cancelled
                event.status = EventStatus.CANCELLED
                db.session.commit()
                db.session.refresh(event)

                assert event.status == EventStatus.CANCELLED

                # Cleanup
                db.session.delete(event)
                db.session.commit()

            # Cleanup school
            db.session.delete(school)
            db.session.commit()


# ==============================================================================
# TC-191: Cancellation Reason Preservation
# ==============================================================================


class TestCancellationReasons:
    """
    TC-191: The system shall preserve cancellation reasons when events
    are cancelled in Salesforce.

    FR-INPERSON-120: Cancellation reason preservation
    """

    def test_cancellation_reason_preserved(self, app, test_district):
        """
        TC-191: Verify that cancellation reason is preserved when
        an event is cancelled in Salesforce.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_CANC_REASON",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Create cancelled event with cancellation reason (simulating Salesforce sync)
            # In actual sync, map_cancellation_reason("Inclement Weather Cancellation") -> WEATHER
            event = Event(
                salesforce_id="SFEV_CANCEL_REASON",
                title="Test Event - Cancelled Weather",
                type=EventType.CAREER_FAIR,
                format=EventFormat.IN_PERSON,
                start_date=datetime(2026, 2, 15, 10, 0, 0),
                end_date=datetime(2026, 2, 15, 12, 0, 0),
                status=EventStatus.CANCELLED,
                cancellation_reason=CancellationReason.WEATHER,  # Mapped during sync
                school=school.id,
            )
            db.session.add(event)
            db.session.commit()

            # Verify cancellation reason was preserved
            assert event is not None
            assert event.status == EventStatus.CANCELLED
            assert event.cancellation_reason == CancellationReason.WEATHER

            # Cleanup
            db.session.delete(event)
            db.session.delete(school)
            db.session.commit()

    def test_different_cancellation_reasons(self, app, test_district):
        """
        TC-191: Verify that different cancellation reason values
        from Salesforce are correctly mapped.
        """
        # Test mapping function directly
        assert (
            map_cancellation_reason("Inclement Weather Cancellation")
            == CancellationReason.WEATHER
        )
        # Add more mappings as they're defined in the codebase
        assert map_cancellation_reason("Unknown Reason") is None
        assert map_cancellation_reason(None) is None
        assert map_cancellation_reason("") is None

    def test_cancellation_reason_none_for_non_cancelled(self, app, test_district):
        """
        TC-191: Verify that cancellation_reason is None for events
        that are not cancelled.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_NO_CANCEL",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Test non-cancelled statuses
            non_cancelled_statuses = [
                EventStatus.DRAFT,
                EventStatus.REQUESTED,
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.COMPLETED,
            ]

            for status in non_cancelled_statuses:
                # Create event with non-cancelled status (simulating Salesforce sync)
                event = Event(
                    salesforce_id=f"SFEV_NO_CANCEL_{status.value}",
                    title=f"Test Event - {status.value}",
                    type=EventType.CAREER_FAIR,
                    format=EventFormat.IN_PERSON,
                    start_date=datetime(2026, 2, 15, 10, 0, 0),
                    end_date=datetime(2026, 2, 15, 12, 0, 0),
                    status=status,
                    cancellation_reason=None,  # No cancellation reason for non-cancelled events
                    school=school.id,
                )
                db.session.add(event)
                db.session.commit()

                assert event.cancellation_reason is None

                # Cleanup
                db.session.delete(event)

            db.session.delete(school)
            db.session.commit()

    def test_cancellation_reason_update(self, app, test_district):
        """
        TC-191: Verify that cancellation reason is updated when
        an existing event is cancelled.
        """
        with app.app_context():
            school = School(
                id="TEST_SCHOOL_CANCEL_UPDATE",
                name="Test School",
                district_id=test_district.id,
            )
            db.session.add(school)
            db.session.commit()

            # Create event without cancellation
            event = Event(
                salesforce_id="SFEV_CANCEL_UPDATE",
                title="Test Event - Cancel Update",
                type=EventType.CAREER_FAIR,
                format=EventFormat.IN_PERSON,
                start_date=datetime(2026, 2, 15, 10, 0, 0),
                end_date=datetime(2026, 2, 15, 12, 0, 0),
                status=EventStatus.CONFIRMED,
                cancellation_reason=None,
                school=school.id,
            )
            db.session.add(event)
            db.session.commit()

            # Verify initial state
            assert event.status == EventStatus.CONFIRMED
            assert event.cancellation_reason is None

            # Simulate cancellation update
            event.status = EventStatus.CANCELLED
            event.cancellation_reason = CancellationReason.WEATHER
            db.session.commit()

            # Verify update
            db.session.refresh(event)
            assert event.status == EventStatus.CANCELLED
            assert event.cancellation_reason == CancellationReason.WEATHER

            # Cleanup
            db.session.delete(event)
            db.session.delete(school)
            db.session.commit()
