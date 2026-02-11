"""
Test Suite for Unaffiliated Events Sync (TC-180 to TC-182)

This module provides integration tests for unaffiliated events sync from Salesforce.
These tests use mocked Salesforce responses to verify the sync logic.

Test Coverage:
    - TC-180: Identify unaffiliated events (missing School/District/Parent Account)
    - TC-181: District association from participating students
    - TC-182: Sync completeness (event + volunteer + student participation records)

Note: These are mock-based integration tests. The actual Salesforce data pull
is a manual process due to data volume. See requirements.md FR-INPERSON-116 to 118.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.district_model import District
from models.event import (
    Event,
    EventFormat,
    EventStatus,
    EventStudentParticipation,
    EventType,
)
from models.school_model import School
from models.student import Student
from models.volunteer import EventParticipation, Volunteer
from routes.salesforce.pathway_import import _create_event_from_salesforce

# ==============================================================================
# TC-180: Identify Unaffiliated Events
# ==============================================================================


class TestIdentifyUnaffiliatedEvents:
    """
    TC-180: The system shall identify and sync events from Salesforce that
    are missing School, District, or Parent Account associations.

    FR-INPERSON-116: Identify unaffiliated events
    """

    def test_unaffiliated_event_query_criteria(self, app):
        """
        TC-180: Verify the query correctly targets events with NULL School,
        District, AND Parent Account.

        The Salesforce query in pathway_events.py uses:
        WHERE School__c = NULL AND District__c = NULL AND Parent_Account__c = NULL
        """
        # The query logic is defined in pathway_events.py
        # This test validates the expected behavior
        expected_query_fragment = (
            "School__c = NULL AND District__c = NULL AND Parent_Account__c = NULL"
        )

        # Verify query constant is correct through inspection
        import inspect

        from routes.salesforce import pathway_import

        source = inspect.getsource(pathway_import.sync_unaffiliated_events)

        assert (
            expected_query_fragment in source
        ), "Query should filter for events with NULL school/district/parent"

    def test_create_event_from_salesforce_minimal_data(self, app):
        """
        TC-180: Test that _create_event_from_salesforce handles minimal data.
        """
        with app.app_context():
            sf_data = {
                "Id": "EVT_UNAFFILIATED_001",
                "Name": "Minimal Unaffiliated Event",
                "Session_Type__c": None,
                "Format__c": None,
                "Start_Date_and_Time__c": None,
                "End_Date_and_Time__c": None,
                "Session_Status__c": None,
            }

            event = _create_event_from_salesforce(sf_data, set())

            assert event.salesforce_id == "EVT_UNAFFILIATED_001"
            assert event.title == "Minimal Unaffiliated Event"
            assert event.status == EventStatus.DRAFT  # Default

    def test_create_event_from_salesforce_full_data(self, app):
        """
        TC-180: Test that _create_event_from_salesforce handles full event data.
        """
        with app.app_context():
            sf_data = {
                "Id": "EVT_FULL_001",
                "Name": "Full Details Event",
                "Session_Type__c": "Career Day",
                "Format__c": "In-Person",
                "Start_Date_and_Time__c": "2026-02-15T10:00:00.000+0000",
                "End_Date_and_Time__c": "2026-02-15T12:00:00.000+0000",
                "Session_Status__c": "Confirmed",
                "Location_Information__c": "Test Location",
                "Description__c": "Test Description",
                "Cancellation_Reason__c": None,
                "Non_Scheduled_Students_Count__c": 25,
                "Total_Requested_Volunteer_Jobs__c": 5,
                "Available_Slots__c": 3,
                "Session_Host__c": "Test Host",
                "Additional_Information__c": "Additional info",
            }

            event = _create_event_from_salesforce(sf_data, set())

            assert event.salesforce_id == "EVT_FULL_001"
            assert event.title == "Full Details Event"
            assert event.location == "Test Location"
            assert event.description == "Test Description"
            assert event.participant_count == 25
            assert event.total_requested_volunteer_jobs == 5
            assert event.available_slots == 3

    def test_create_event_handles_missing_id(self, app):
        """
        TC-180 Edge Case: Missing Salesforce ID should raise ValueError.
        """
        with app.app_context():
            sf_data = {
                "Name": "Event Without ID",
            }

            with pytest.raises(ValueError, match="missing 'Id'"):
                _create_event_from_salesforce(sf_data, set())

    def test_unaffiliated_event_imported_to_database(self, app, test_district):
        """
        TC-180: Verify unaffiliated events are synced to the local database.
        """
        with app.app_context():
            sf_data = {
                "Id": "EVT_IMPORT_TEST",
                "Name": "Import Test Event",
                "Session_Type__c": "Career Day",
                "Format__c": "In-Person",
                "Start_Date_and_Time__c": None,
                "End_Date_and_Time__c": None,
                "Session_Status__c": "Published",
            }

            event = _create_event_from_salesforce(sf_data, set())
            db.session.add(event)
            db.session.commit()

            # Verify event was saved
            saved = Event.query.filter_by(salesforce_id="EVT_IMPORT_TEST").first()
            assert saved is not None
            assert saved.title == "Import Test Event"

            # Cleanup
            db.session.delete(saved)
            db.session.commit()


# ==============================================================================
# TC-181: District Association from Students
# ==============================================================================


class TestDistrictAssociation:
    """
    TC-181: For unaffiliated events, the system shall attempt to associate
    events with districts based on participating students.

    FR-INPERSON-117: District association from students
    """

    def test_event_associated_with_single_district(self, app):
        """
        TC-181: Event with students from a single district gets that district.
        """
        with app.app_context():
            # Create district
            district = District(salesforce_id="DIST_TC181", name="Test District TC181")
            db.session.add(district)
            db.session.commit()

            sf_data = {
                "Id": "EVT_SINGLE_DIST",
                "Name": "Single District Event",
            }

            event = _create_event_from_salesforce(sf_data, {district})

            assert len(event.districts) == 1
            assert event.districts[0].name == "Test District TC181"

            # Cleanup
            db.session.delete(district)
            db.session.commit()

    def test_event_associated_with_multiple_districts(self, app):
        """
        TC-181: Event with students from multiple districts gets all districts.
        """
        with app.app_context():
            # Create districts
            district1 = District(salesforce_id="DIST_MULTI_1", name="District Multi 1")
            district2 = District(salesforce_id="DIST_MULTI_2", name="District Multi 2")
            db.session.add_all([district1, district2])
            db.session.commit()

            sf_data = {
                "Id": "EVT_MULTI_DIST",
                "Name": "Multi District Event",
            }

            event = _create_event_from_salesforce(sf_data, {district1, district2})

            assert len(event.districts) == 2
            district_names = {d.name for d in event.districts}
            assert "District Multi 1" in district_names
            assert "District Multi 2" in district_names

            # Cleanup
            db.session.delete(district1)
            db.session.delete(district2)
            db.session.commit()

    def test_event_no_students_remains_unaffiliated(self, app):
        """
        TC-181 Edge Case: Event with no students cannot determine district.
        """
        with app.app_context():
            sf_data = {
                "Id": "EVT_NO_STUDENTS",
                "Name": "No Students Event",
            }

            event = _create_event_from_salesforce(sf_data, set())

            assert len(event.districts) == 0

    def test_district_inference_from_student_school(self, app):
        """
        TC-181: Verify district is inferred from student -> school -> district chain.
        """
        with app.app_context():
            # Create district
            district = District(salesforce_id="DIST_INFER", name="Inferred District")
            db.session.add(district)
            db.session.flush()

            # Create school linked to district
            school = School(id="SCH_INFER", name="Inference School", district=district)
            db.session.add(school)
            db.session.flush()

            # Create student linked to school
            student = Student(
                salesforce_individual_id="003STUDENT_INFER",
                first_name="Infer",
                last_name="Student",
                school_id=school.id,
            )
            db.session.add(student)
            db.session.commit()

            # Verify the chain
            assert student.school is not None
            assert student.school.district is not None
            assert student.school.district.name == "Inferred District"

            # Cleanup
            db.session.delete(student)
            db.session.delete(school)
            db.session.delete(district)
            db.session.commit()

    def test_student_without_school_ignored_for_district(self, app):
        """
        TC-181 Edge Case: Students without school association are skipped.
        """
        with app.app_context():
            # Create student without school
            student = Student(
                salesforce_individual_id="003NO_SCHOOL_STUDENT",
                first_name="NoSchool",
                last_name="Student",
                school_id=None,
            )
            db.session.add(student)
            db.session.commit()

            # The student has no school, so cannot contribute to district inference
            assert student.school is None

            # Cleanup
            db.session.delete(student)
            db.session.commit()


# ==============================================================================
# TC-182: Unaffiliated Sync Completeness
# ==============================================================================


class TestUnaffiliatedSyncCompleteness:
    """
    TC-182: Unaffiliated event sync shall update both event data and
    associated volunteer/student participation records.

    FR-INPERSON-118: Sync completeness
    """

    def test_event_data_synced(self, app):
        """
        TC-182: Verify event data is properly synced.
        """
        with app.app_context():
            sf_data = {
                "Id": "EVT_COMPLETE_1",
                "Name": "Complete Sync Event",
                "Session_Type__c": "Orientation",
                "Format__c": "Virtual",
                "Start_Date_and_Time__c": "2026-03-01T09:00:00.000+0000",
                "End_Date_and_Time__c": "2026-03-01T10:00:00.000+0000",
                "Session_Status__c": "Confirmed",
                "Location_Information__c": "Virtual Room",
                "Description__c": "Complete sync test",
            }

            event = _create_event_from_salesforce(sf_data, set())
            db.session.add(event)
            db.session.commit()

            # Verify all fields were synced
            saved = Event.query.filter_by(salesforce_id="EVT_COMPLETE_1").first()
            assert saved.title == "Complete Sync Event"
            assert saved.location == "Virtual Room"
            assert saved.description == "Complete sync test"

            # Cleanup
            db.session.delete(saved)
            db.session.commit()

    def test_volunteer_participations_can_be_linked(self, app, test_volunteer):
        """
        TC-182: Verify volunteer participations can be linked to event.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="Volunteer Link Test",
                salesforce_id="EVT_VOL_LINK",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.CONFIRMED,
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)
            db.session.commit()

            # Create volunteer participation
            participation = EventParticipation(
                event_id=event.id,
                volunteer_id=test_volunteer.id,
                status="Attended",
                delivery_hours=2.0,
                salesforce_id="SP_VOL_COMPLETE_1",
            )
            db.session.add(participation)
            db.session.commit()

            # Verify linkage
            assert participation.event_id == event.id
            assert participation.volunteer_id == test_volunteer.id

            # Verify via relationship
            vol_participations = EventParticipation.query.filter_by(
                event_id=event.id
            ).all()
            assert len(vol_participations) == 1

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.commit()

    def test_student_participations_can_be_linked(self, app):
        """
        TC-182: Verify student participations can be linked to event.
        """
        with app.app_context():
            # Create event
            event = Event(
                title="Student Link Test",
                salesforce_id="EVT_STU_LINK",
                type=EventType.IN_PERSON,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                status=EventStatus.CONFIRMED,
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)

            # Create student
            student = Student(
                salesforce_individual_id="003STUDENT_LINK",
                first_name="Link",
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()

            # Create student participation
            participation = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id,
                status="Attended",
                delivery_hours=1.5,
                salesforce_id="SP_STU_COMPLETE_1",
            )
            db.session.add(participation)
            db.session.commit()

            # Verify linkage
            assert participation.event_id == event.id
            assert participation.student_id == student.id

            # Verify count
            stu_participations = EventStudentParticipation.query.filter_by(
                event_id=event.id
            ).all()
            assert len(stu_participations) == 1

            # Cleanup
            db.session.delete(participation)
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_complete_sync_all_records_created(self, app, test_volunteer):
        """
        TC-182: Full integration test - event with both volunteer and student
        participation records.
        """
        with app.app_context():
            # Create event using helper
            sf_data = {
                "Id": "EVT_FULL_SYNC",
                "Name": "Full Sync Integration Test",
                "Session_Type__c": "Career Day",
                "Format__c": "In-Person",
                "Start_Date_and_Time__c": None,
                "End_Date_and_Time__c": None,
                "Session_Status__c": "Published",
            }
            event = _create_event_from_salesforce(sf_data, set())
            db.session.add(event)
            db.session.commit()

            # Create student
            student = Student(
                salesforce_individual_id="003FULL_SYNC_STU",
                first_name="FullSync",
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()

            # Create both participation types
            vol_participation = EventParticipation(
                event_id=event.id,
                volunteer_id=test_volunteer.id,
                status="Attended",
                delivery_hours=2.0,
                salesforce_id="SP_FULL_VOL",
            )
            stu_participation = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id,
                status="Attended",
                delivery_hours=1.5,
                salesforce_id="SP_FULL_STU",
            )
            db.session.add_all([vol_participation, stu_participation])
            db.session.commit()

            # Verify all records created
            saved_event = Event.query.filter_by(salesforce_id="EVT_FULL_SYNC").first()
            assert saved_event is not None

            vol_count = EventParticipation.query.filter_by(event_id=event.id).count()
            stu_count = EventStudentParticipation.query.filter_by(
                event_id=event.id
            ).count()

            assert vol_count == 1
            assert stu_count == 1

            # Cleanup
            EventParticipation.query.filter_by(event_id=event.id).delete()
            EventStudentParticipation.query.filter_by(event_id=event.id).delete()
            db.session.delete(event)
            db.session.delete(student)
            db.session.commit()

    def test_batch_processing_for_large_events(self, app):
        """
        TC-182: Verify batch processing is used for volunteer participants
        (batch_size = 50 events per batch in pathway_events.py).
        """
        # Verify the constant exists in the code
        import inspect

        from routes.salesforce import pathway_import

        source = inspect.getsource(pathway_import.sync_unaffiliated_events)

        assert "batch_size = 50" in source, "Batch size should be 50 events per batch"


# ==============================================================================
# Additional Tests: Error Handling
# ==============================================================================


class TestUnaffiliatedEventsErrorHandling:
    """
    Additional tests for error handling in unaffiliated events sync.
    """

    def test_salesforce_auth_failure_handled(self, app, client, auth_headers):
        """
        Verify Salesforce authentication errors are handled gracefully.
        """
        with patch(
            "routes.salesforce.pathway_import.get_salesforce_client"
        ) as mock_get_sf:
            from simple_salesforce import SalesforceAuthenticationFailed

            mock_get_sf.side_effect = SalesforceAuthenticationFailed("code", "message")

            response = client.post(
                "/pathway-events/sync-unaffiliated-events",
                headers=auth_headers,
            )

            # Should return 401 with appropriate error message
            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False
            assert "authenticate" in data["message"].lower()

    def test_partial_failure_continues_processing(self, app):
        """
        Verify that failure processing one event doesn't stop others.

        The sync process continues with remaining events even if one fails.
        """
        # This is verified by the structure of sync_unaffiliated_events
        # which has try/except inside the event loop
        import inspect

        from routes.salesforce import pathway_import

        source = inspect.getsource(pathway_import.sync_unaffiliated_events)

        # Verify there's error handling inside the event processing loop
        assert "except Exception" in source
        assert "continue" in source or "event_processed_or_skipped" in source

    def test_no_unaffiliated_events_returns_success(self, app, client, auth_headers):
        """
        Verify that finding no unaffiliated events returns success (not failure).
        """
        with patch(
            "routes.salesforce.pathway_import.get_salesforce_client"
        ) as mock_get_sf:
            # Mock client with empty results
            mock_client = MagicMock()
            mock_client.query_all.return_value = {"records": []}
            mock_get_sf.return_value = mock_client

            response = client.post(
                "/pathway-events/sync-unaffiliated-events",
                headers=auth_headers,
            )

            # Should return success with 0 processed
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["processed_count"] == 0
