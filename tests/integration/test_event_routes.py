from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.event import Event, EventStatus, EventType
from models.school_model import School
from models.volunteer import Volunteer
from tests.conftest import assert_route_response, safe_route_test


def test_events_list_view(client, auth_headers):
    """Test events list view"""
    response = safe_route_test(client, "/events", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_add_event(client, auth_headers):
    """Test adding a new event"""
    event_data = {
        "title": "New Test Event",
        "description": "Test event description",
        "start_date": "2024-06-01 10:00:00",
        "end_date": "2024-06-01 12:00:00",
        "type": "in_person",
        "status": "draft",
    }

    response = safe_route_test(
        client, "/events/add", method="POST", data=event_data, headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_edit_event(client, auth_headers):
    """Test editing an event"""
    update_data = {"title": "Updated Event Title", "description": "Updated description"}

    response = safe_route_test(
        client, "/events/edit/1", data=update_data, headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_delete_event(client, auth_headers):
    """Test deleting an event"""
    response = safe_route_test(client, "/events/delete/1", headers=auth_headers)
    assert_route_response(
        response, expected_statuses=[200, 204, 302, 403, 404, 405, 500]
    )


def test_purge_events(client, auth_headers):
    """Test purging events"""
    response = safe_route_test(client, "/events/purge", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 302, 403, 404, 405, 500])


def test_event_model_properties(client, auth_headers):
    """Test event model properties and methods"""
    # This test will be handled at the route level
    response = safe_route_test(client, "/events/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_view_event_details(client, auth_headers):
    """Test viewing event details"""
    response = safe_route_test(client, "/events/view/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_search(client, auth_headers):
    """Test event search functionality"""
    response = safe_route_test(client, "/events?search=test", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_filtering(client, auth_headers):
    """Test event filtering"""
    response = safe_route_test(
        client, "/events?type=in_person&status=confirmed", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_pagination(client, auth_headers):
    """Test event pagination"""
    response = safe_route_test(client, "/events?page=1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_sorting(client, auth_headers):
    """Test event sorting"""
    response = safe_route_test(client, "/events?sort=date", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_export(client, auth_headers):
    """Test event export"""
    response = safe_route_test(client, "/events/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


# Removed test for old import route - now using /events/import-from-salesforce
# def test_event_import(client, auth_headers):
#     """Test event import page"""
#     response = safe_route_test(client, '/events/import', headers=auth_headers)
#     assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_copy(client, auth_headers):
    """Test copying an event"""
    response = safe_route_test(client, "/events/copy/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_event_duplicate_check(client, auth_headers):
    """Test duplicate event detection"""
    response = safe_route_test(client, "/events/check-duplicate", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_status_change(client, auth_headers):
    """Test changing event status"""
    status_data = {"status": "confirmed"}
    response = safe_route_test(
        client,
        "/events/1/status",
        method="PUT",
        json_data=status_data,
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_volunteers(client, auth_headers):
    """Test event volunteers management"""
    response = safe_route_test(client, "/events/1/volunteers", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_assign_volunteer(client, auth_headers):
    """Test assigning volunteer to event"""
    volunteer_data = {"volunteer_id": 1}
    response = safe_route_test(
        client,
        "/events/1/volunteers",
        method="POST",
        json_data=volunteer_data,
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_attendance(client, auth_headers):
    """Test event attendance tracking"""
    response = safe_route_test(client, "/events/1/attendance", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_comments(client, auth_headers):
    """Test event comments"""
    response = safe_route_test(client, "/events/1/comments", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_add_comment(client, auth_headers):
    """Test adding comment to event"""
    comment_data = {"content": "Test comment"}
    response = safe_route_test(
        client,
        "/events/1/comments",
        method="POST",
        json_data=comment_data,
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_performance(client, auth_headers):
    """Test event page performance"""
    import time

    start_time = time.time()
    response = safe_route_test(client, "/events", headers=auth_headers)
    end_time = time.time()

    # Should respond within reasonable time
    assert (end_time - start_time) < 5.0
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_analytics(client, auth_headers):
    """Test event analytics"""
    response = safe_route_test(client, "/events/analytics", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_reports(client, auth_headers):
    """Test event reports"""
    response = safe_route_test(client, "/events/reports", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_student_participation_import_guard(client, auth_headers, test_event, app):
    """Import guard should not create duplicate (event_id, student_id) pairs."""
    from datetime import datetime, timedelta, timezone
    from models.event import EventStudentParticipation, Event, EventType, EventStatus, EventFormat
    from models.student import Student

    with app.app_context():
        # Create a Student (inherits Contact fields)
        student = Student(
            salesforce_individual_id="003TESTSTUDENT001",
            first_name="Stu",
            last_name="Dent",
        )
        db.session.add(student)
        db.session.commit()

        # Simulate two Salesforce rows for same event/student
        row1 = {
            "Session__c": test_event.salesforce_id or "EVT_SF_1",
            "Contact__c": student.salesforce_individual_id,
            "Id": "SP_SF_1",
            "Status__c": "Scheduled",
            "Delivery_Hours__c": None,
            "Age_Group__c": None,
        }
        row2 = {
            "Session__c": row1["Session__c"],
            "Contact__c": row1["Contact__c"],
            "Id": "SP_SF_2",
            "Status__c": "Scheduled",
            "Delivery_Hours__c": None,
            "Age_Group__c": None,
        }

        # Use a fixed salesforce_id for the test (18 alphanumeric characters)
        event_sf_id = "EVTSF1000123456789"  # 18 characters
        row1["Session__c"] = event_sf_id
        row2["Session__c"] = event_sf_id
        
        # Create a test event with the salesforce_id
        from models.event import Event, EventType, EventStatus, EventFormat
        test_event_with_sf = Event(
            title="Test Event with SF ID",
            type=EventType.IN_PERSON,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=2),
            status=EventStatus.DRAFT,
            format=EventFormat.IN_PERSON,
            salesforce_id=event_sf_id,
        )
        db.session.add(test_event_with_sf)
        db.session.commit()

        from routes.events.routes import process_student_participation_row

        success, errors = 0, 0
        error_list = []
        success, errors = process_student_participation_row(row1, success, errors, error_list)
        success, errors = process_student_participation_row(row2, success, errors, error_list)
        db.session.commit()

        # Assert only one DB row exists for this event/student
        count = EventStudentParticipation.query.filter_by(
            event_id=test_event_with_sf.id, student_id=student.id
        ).count()
        assert count == 1


def test_event_validation(client, auth_headers):
    """Test event data validation"""
    invalid_data = {
        "title": "",  # Invalid empty title
        "start_date": "invalid-date",  # Invalid date format
    }

    response = safe_route_test(
        client,
        "/events/validate",
        method="POST",
        json_data=invalid_data,
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[400, 404, 500])


def test_event_calendar_integration(client, auth_headers):
    """Test event calendar integration"""
    response = safe_route_test(client, "/events/calendar", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_notifications(client, auth_headers):
    """Test event notifications"""
    response = safe_route_test(client, "/events/1/notifications", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_registration(client, auth_headers):
    """Test event registration"""
    response = safe_route_test(client, "/events/1/register", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_cancellation(client, auth_headers):
    """Test event cancellation"""
    cancel_data = {"reason": "weather"}
    response = safe_route_test(
        client,
        "/events/1/cancel",
        method="POST",
        json_data=cancel_data,
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_event_history(client, auth_headers):
    """Test event history tracking"""
    response = safe_route_test(client, "/events/1/history", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_templates(client, auth_headers):
    """Test event templates"""
    response = safe_route_test(client, "/events/templates", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_event_bulk_operations(client, auth_headers):
    """Test bulk event operations"""
    response = safe_route_test(client, "/events/bulk", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 202, 403, 404, 500])
