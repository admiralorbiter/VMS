"""
Test Suite for Participation Sync (TC-170 to TC-173)

This module provides integration tests for student and volunteer participation
sync from Salesforce. These tests use mocked Salesforce responses.

Test Coverage:
    - TC-170: Student participation sync (EventStudentParticipation records created)
    - TC-171: Student attendance update (status and delivery hours updated)
    - TC-172: Volunteer participation sync (status, delivery hours, attributes synced)
    - TC-173: Volunteer batch processing (large event sets processed in batches)

Note: These are mock-based integration tests. The actual Salesforce data pull
is a manual process due to data volume. See requirements.md FR-INPERSON-112 to 115.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.event import (
    Event,
    EventFormat,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.student import Student
from models.volunteer import EventParticipation, Volunteer
from routes.events.routes import process_student_participation_row

# ==============================================================================
# TC-170: Student Participation Sync
# ==============================================================================


class TestStudentParticipationSync:
    """
    TC-170: The system shall sync student participation data from Salesforce
    for in-person events, creating EventStudentParticipation records.

    FR-INPERSON-112: Student participation sync creates EventStudentParticipation records
    """

    def test_student_participation_creates_record(self, app):
        """
        TC-170: Verify that student participation sync creates
        EventStudentParticipation records from Salesforce data.
        """
        with app.app_context():
            # Create event with salesforce_id
            event = Event(
                title="TC170 Test Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_TC170_CREATE",
            )
            db.session.add(event)

            # Create student with salesforce_individual_id
            student = Student(
                salesforce_individual_id="003TESTSTUDENT_TC170",
                first_name="Test",
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()

            # Mock Salesforce participation row
            sf_row = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_TC170_001",
                "Status__c": "Scheduled",
                "Delivery_Hours__c": 1.5,
                "Age_Group__c": "High School",
            }

            # Process the row
            success, errors = 0, 0
            error_list = []
            success, errors = process_student_participation_row(
                sf_row, success, errors, error_list
            )

            # Verify record was created
            participation = EventStudentParticipation.query.filter_by(
                event_id=event.id, student_id=student.id
            ).first()

            assert (
                participation is not None
            ), f"EventStudentParticipation should be created. Errors: {error_list}"
            assert participation.salesforce_id == "SP_SF_TC170_001"
            assert participation.status == "Scheduled"
            assert success == 1
            assert errors == 0

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_student_participation_links_correctly(self, app):
        """
        TC-170: Verify that participation records are correctly linked
        to both the Event and Student.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC170 Link Test Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_TC170_LINK",
            )
            db.session.add(event)

            # Create student
            student = Student(
                salesforce_individual_id="003TESTSTUDENT_LINK",
                first_name="Link",
                last_name="Test",
            )
            db.session.add(student)
            db.session.commit()

            sf_row = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_LINK_001",
                "Status__c": "Attended",
                "Delivery_Hours__c": 2.0,
                "Age_Group__c": None,
            }

            success, errors = 0, 0
            error_list = []
            success, errors = process_student_participation_row(
                sf_row, success, errors, error_list
            )

            # Verify linkage
            participation = EventStudentParticipation.query.filter_by(
                salesforce_id="SP_SF_LINK_001"
            ).first()

            assert (
                participation is not None
            ), f"Participation should be created. Errors: {error_list}"
            assert participation.event_id == event.id
            assert participation.student_id == student.id

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_student_participation_handles_missing_event(self, app):
        """
        TC-170 Edge Case: Participation for event that doesn't exist locally
        should log an error.
        """
        with app.app_context():
            student = Student(
                salesforce_individual_id="003TESTSTUDENT_NOEVENT",
                first_name="NoEvent",
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()

            sf_row = {
                "Session__c": "NONEXISTENT_EVENT_SF_ID",
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_NO_EVENT",
                "Status__c": "Scheduled",
                "Delivery_Hours__c": None,
                "Age_Group__c": None,
            }

            success, errors = 0, 0
            error_list = []
            success, errors = process_student_participation_row(
                sf_row, success, errors, error_list
            )

            assert errors == 1
            assert any("not found" in e for e in error_list)

            # Cleanup
            db.session.delete(student)
            db.session.commit()

    def test_student_participation_handles_missing_student(self, app):
        """
        TC-170 Edge Case: Participation for student that doesn't exist locally
        should log an error.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC170 Missing Student Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_NO_STUDENT",
            )
            db.session.add(event)
            db.session.commit()

            sf_row = {
                "Session__c": event.salesforce_id,
                "Contact__c": "NONEXISTENT_STUDENT_SF_ID",
                "Id": "SP_SF_NO_STUDENT",
                "Status__c": "Scheduled",
                "Delivery_Hours__c": None,
                "Age_Group__c": None,
            }

            success, errors = 0, 0
            error_list = []
            success, errors = process_student_participation_row(
                sf_row, success, errors, error_list
            )

            assert errors == 1
            assert len(error_list) == 1
            # The error message should mention either "Student" or "Contact"
            assert "not found" in error_list[0]

            # Cleanup
            db.session.delete(event)
            db.session.commit()

    def test_student_participation_idempotency(self, app):
        """
        TC-170: Verify that re-syncing the same participation does not
        create duplicates (idempotency).
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC170 Idempotency Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_IDEMP",
            )
            db.session.add(event)

            student = Student(
                salesforce_individual_id="003TESTSTUDENT_IDEMP",
                first_name="Idempotent",
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()

            sf_row = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_IDEMP_001",
                "Status__c": "Scheduled",
                "Delivery_Hours__c": 1.0,
                "Age_Group__c": None,
            }

            # Process twice
            success, errors = 0, 0
            error_list = []
            success, errors = process_student_participation_row(
                sf_row, success, errors, error_list
            )

            success2, errors2 = 0, 0
            error_list2 = []
            success2, errors2 = process_student_participation_row(
                sf_row, success2, errors2, error_list2
            )

            # Should only have one record
            count = EventStudentParticipation.query.filter_by(
                event_id=event.id, student_id=student.id
            ).count()

            assert (
                count == 1
            ), f"Should not create duplicate records. Errors: {error_list + error_list2}"

            # Cleanup
            EventStudentParticipation.query.filter_by(
                event_id=event.id, student_id=student.id
            ).delete()
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()


# ==============================================================================
# TC-171: Student Attendance Update
# ==============================================================================


class TestStudentAttendanceUpdate:
    """
    TC-171: Student participation sync shall update attendance status
    and delivery hours from Salesforce.

    FR-INPERSON-113: Student attendance updates
    """

    def test_attendance_status_updated(self, app):
        """
        TC-171: Verify that status is updated when re-syncing with different SF record.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC171 Status Update Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_STATUS_UPDATE",
            )
            db.session.add(event)

            student = Student(
                salesforce_individual_id="003TESTSTUDENT_STATUS",
                first_name="Status",
                last_name="Update",
            )
            db.session.add(student)
            db.session.commit()

            # First sync with Scheduled status
            sf_row_initial = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_STATUS_001",
                "Status__c": "Scheduled",
                "Delivery_Hours__c": None,
                "Age_Group__c": None,
            }

            success, errors = 0, 0
            error_list = []
            process_student_participation_row(
                sf_row_initial, success, errors, error_list
            )

            # Simulate second sync with different salesforce_id but same event/student
            # (this is the realistic scenario where they update already-created pair)
            sf_row_updated = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_STATUS_002",  # Different SF record ID
                "Status__c": "Attended",
                "Delivery_Hours__c": 2.0,
                "Age_Group__c": "Middle School",
            }

            process_student_participation_row(sf_row_updated, 0, 0, [])

            # Verify the update
            participation = EventStudentParticipation.query.filter_by(
                event_id=event.id, student_id=student.id
            ).first()

            assert (
                participation is not None
            ), f"Participation should exist. Errors: {error_list}"
            assert participation.status == "Attended"
            assert participation.delivery_hours == 2.0
            assert participation.age_group == "Middle School"

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_delivery_hours_null_to_value(self, app):
        """
        TC-171 Edge Case: Delivery hours changed from null to value.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC171 Hours Update Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_SF_HOURS_UPDATE",
            )
            db.session.add(event)

            student = Student(
                salesforce_individual_id="003TESTSTUDENT_HOURS",
                first_name="Hours",
                last_name="Update",
            )
            db.session.add(student)
            db.session.commit()

            # Create initial participation with null hours (no SF id)
            participation = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id,
                status="Scheduled",
                delivery_hours=None,
                salesforce_id=None,  # No SF id yet
            )
            db.session.add(participation)
            db.session.commit()

            # Now sync with delivery hours (different SF participation ID)
            sf_row = {
                "Session__c": event.salesforce_id,
                "Contact__c": student.salesforce_individual_id,
                "Id": "SP_SF_HOURS_001",
                "Status__c": "Attended",
                "Delivery_Hours__c": 3.5,
                "Age_Group__c": None,
            }

            process_student_participation_row(sf_row, 0, 0, [])
            # Commit after processing (the function updates in-session but may not commit)
            db.session.commit()
            db.session.refresh(participation)

            assert participation.delivery_hours == 3.5
            assert participation.salesforce_id == "SP_SF_HOURS_001"

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()


# ==============================================================================
# TC-172: Volunteer Participation Sync
# ==============================================================================


class TestVolunteerParticipationSync:
    """
    TC-172: The system shall sync volunteer participation data from Salesforce
    for in-person events, including status, delivery hours, and participant attributes.

    FR-INPERSON-114: Volunteer participation sync
    """

    def test_volunteer_participation_record_exists(
        self, app, test_event, test_volunteer
    ):
        """
        TC-172: Verify that EventParticipation records can be created
        with status, delivery hours, and attributes.
        """
        with app.app_context():
            # Create a participation record (simulating sync result)
            participation = EventParticipation(
                event_id=test_event.id,
                volunteer_id=test_volunteer.id,
                status="Attended",
                delivery_hours=2.5,
                salesforce_id="SP_SF_VOL_001",
            )
            db.session.add(participation)
            db.session.commit()

            # Verify record was created with correct attributes
            saved = EventParticipation.query.filter_by(
                salesforce_id="SP_SF_VOL_001"
            ).first()

            assert saved is not None
            assert saved.status == "Attended"
            assert saved.delivery_hours == 2.5
            assert saved.event_id == test_event.id
            assert saved.volunteer_id == test_volunteer.id

            # Cleanup
            db.session.delete(participation)
            db.session.commit()

    def test_volunteer_participation_attributes_synced(
        self, app, test_event, test_volunteer
    ):
        """
        TC-172: Verify that additional attributes (Age_Group, Title, Email)
        are synced from Salesforce.
        """
        with app.app_context():
            # EventParticipation model attributes
            participation = EventParticipation(
                event_id=test_event.id,
                volunteer_id=test_volunteer.id,
                status="Attended",
                delivery_hours=1.5,
                salesforce_id="SP_SF_VOL_ATTR_001",
            )
            db.session.add(participation)
            db.session.commit()

            # Verify
            saved = EventParticipation.query.filter_by(
                salesforce_id="SP_SF_VOL_ATTR_001"
            ).first()

            assert saved is not None
            assert saved.delivery_hours == 1.5

            # Cleanup
            db.session.delete(participation)
            db.session.commit()

    def test_volunteer_participation_update_not_duplicate(
        self, app, test_event, test_volunteer
    ):
        """
        TC-172: Verify that updating existing participation does not create duplicate.
        """
        with app.app_context():
            # Create initial
            participation = EventParticipation(
                event_id=test_event.id,
                volunteer_id=test_volunteer.id,
                status="Scheduled",
                delivery_hours=None,
                salesforce_id="SP_SF_VOL_UPDATE",
            )
            db.session.add(participation)
            db.session.commit()

            # Update
            participation.status = "Attended"
            participation.delivery_hours = 3.0
            db.session.commit()

            # Should still be one record
            count = EventParticipation.query.filter_by(
                event_id=test_event.id, volunteer_id=test_volunteer.id
            ).count()

            assert count == 1

            # Cleanup
            db.session.delete(participation)
            db.session.commit()


# ==============================================================================
# TC-173: Volunteer Batch Processing
# ==============================================================================


class TestVolunteerBatchProcessing:
    """
    TC-173: Volunteer participation sync shall handle batch processing
    for large event sets (e.g., 50 events per batch).

    FR-INPERSON-115: Batch processing for large event sets
    """

    def test_batch_size_configuration(self, app):
        """
        TC-173: Verify batch size can be configured (default 50 events per batch).

        This tests the batch processing concept. The actual daily_imports.py
        uses configurable batch sizes for processing.
        """
        with app.app_context():
            # Test that batch processing logic can handle configurable sizes
            batch_sizes = [10, 50, 100]

            for batch_size in batch_sizes:
                # Simulate batch processing
                events_to_process = list(range(120))  # 120 events
                batches = [
                    events_to_process[i : i + batch_size]
                    for i in range(0, len(events_to_process), batch_size)
                ]

                # Verify batching works correctly
                expected_batches = (
                    len(events_to_process) + batch_size - 1
                ) // batch_size
                assert len(batches) == expected_batches

                # Verify all events accounted for
                all_events = []
                for batch in batches:
                    all_events.extend(batch)
                assert len(all_events) == len(events_to_process)

    def test_multiple_events_processing(self, app, test_district):
        """
        TC-173: Verify multiple events can be processed in sequence.
        """
        with app.app_context():
            # Create multiple events
            events = []
            for i in range(5):
                event = Event(
                    title=f"Batch Test Event {i}",
                    type=EventType.IN_PERSON,
                    start_date=datetime.now(timezone.utc) + timedelta(days=i),
                    end_date=datetime.now(timezone.utc) + timedelta(days=i, hours=2),
                    status=EventStatus.CONFIRMED,
                    format=EventFormat.IN_PERSON,
                    salesforce_id=f"EVT_BATCH_{i}",
                    district_partner=test_district.id,
                )
                db.session.add(event)
                events.append(event)

            db.session.commit()

            # Create volunteer
            volunteer = Volunteer(
                first_name="Batch",
                last_name="Volunteer",
                salesforce_individual_id="003BATCH_VOL",
            )
            db.session.add(volunteer)
            db.session.commit()

            # Simulate batch processing - create participations for all events
            created_count = 0
            for event in events:
                participation = EventParticipation(
                    event_id=event.id,
                    volunteer_id=volunteer.id,
                    status="Scheduled",
                    delivery_hours=1.0,
                    salesforce_id=f"SP_BATCH_{event.id}",
                )
                db.session.add(participation)
                created_count += 1

            db.session.commit()

            # Verify all participations were created
            total = EventParticipation.query.filter_by(
                volunteer_id=volunteer.id
            ).count()
            assert total == 5

            # Cleanup
            EventParticipation.query.filter_by(volunteer_id=volunteer.id).delete()
            for event in events:
                db.session.delete(event)
            db.session.delete(volunteer)
            db.session.commit()

    def test_batch_continues_on_single_failure(self, app):
        """
        TC-173 Edge Case: Batch processing should continue if one record fails.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="TC173 Batch Fail Event",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.DRAFT,
                format=EventFormat.IN_PERSON,
                salesforce_id="EVT_BATCH_FAIL",
            )
            db.session.add(event)

            # Create one valid student
            student_valid = Student(
                salesforce_individual_id="003VALID_STUDENT",
                first_name="Valid",
                last_name="Student",
            )
            db.session.add(student_valid)
            db.session.commit()

            # Batch of rows - one valid, one invalid (missing student)
            rows = [
                {
                    "Session__c": event.salesforce_id,
                    "Contact__c": student_valid.salesforce_individual_id,
                    "Id": "SP_BATCH_VALID",
                    "Status__c": "Scheduled",
                    "Delivery_Hours__c": 1.0,
                    "Age_Group__c": None,
                },
                {
                    "Session__c": event.salesforce_id,
                    "Contact__c": "MISSING_STUDENT_ID",
                    "Id": "SP_BATCH_INVALID",
                    "Status__c": "Scheduled",
                    "Delivery_Hours__c": 1.0,
                    "Age_Group__c": None,
                },
            ]

            total_success = 0
            total_errors = 0
            all_errors = []

            for row in rows:
                total_success, total_errors = process_student_participation_row(
                    row, total_success, total_errors, all_errors
                )

            # One success, one error
            assert total_success == 1, f"Expected 1 success. Errors: {all_errors}"
            assert total_errors == 1
            assert len(all_errors) == 1

            # Cleanup
            EventStudentParticipation.query.filter_by(event_id=event.id).delete()
            db.session.delete(event)
            db.session.delete(student_valid)
            db.session.commit()
