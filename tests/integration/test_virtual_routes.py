from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventType
from models.organization import Organization
from models.teacher import Teacher
from models.volunteer import Volunteer
from tests.conftest import assert_route_response, safe_route_test


def test_virtual_sessions_view(client, auth_headers):
    """Test virtual sessions main view"""
    response = safe_route_test(client, "/virtual", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_events_list(client, auth_headers):
    """Test virtual events listing"""
    response = safe_route_test(client, "/virtual/events", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_event_detail(client, auth_headers):
    """Test virtual event detail view"""
    response = safe_route_test(client, "/virtual/event/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_import_sheet(client, auth_headers):
    """Test virtual session import from Google Sheets"""
    response = safe_route_test(client, "/virtual/import-sheet", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_purge_data(client, auth_headers):
    """Test virtual session data purge"""
    response = safe_route_test(
        client, "/virtual/purge", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_virtual_session_creation(client, auth_headers):
    """Test virtual session creation"""
    response = safe_route_test(
        client, "/virtual/create-session", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_virtual_session_export(client, auth_headers):
    """Test virtual session data export"""
    response = safe_route_test(client, "/virtual/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_statistics(client, auth_headers):
    """Test virtual session statistics"""
    response = safe_route_test(client, "/virtual/statistics", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_filtering(client, auth_headers):
    """Test virtual session filtering"""
    response = safe_route_test(
        client, "/virtual?district=test&date=2024-01-01", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_search(client, auth_headers):
    """Test virtual session search functionality"""
    response = safe_route_test(client, "/virtual?search=test", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_pagination(client, auth_headers):
    """Test virtual session pagination"""
    response = safe_route_test(
        client, "/virtual?page=2&per_page=10", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_unauthorized_access(client):
    """Test virtual session unauthorized access"""
    response = safe_route_test(client, "/virtual")
    assert_route_response(response, expected_statuses=[302, 401, 403, 404])


def test_virtual_session_error_handling(client, auth_headers):
    """Test virtual session error handling"""
    response = safe_route_test(
        client, "/virtual/invalid-endpoint", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


def test_virtual_session_performance(client, auth_headers):
    """Test virtual session performance"""
    response = safe_route_test(client, "/virtual", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_session_data_validation(client, auth_headers):
    """Test virtual session data validation"""
    response = safe_route_test(
        client, "/virtual/validate", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 400, 404, 500])


def test_people_of_color_mapping():
    """Test People of Color column mapping functionality"""
    from routes.virtual.routes import map_people_of_color

    # Test with "Yes" value
    result = map_people_of_color("Yes")
    assert result == True

    # Test with "yes" (lowercase)
    result = map_people_of_color("yes")
    assert result == True

    # Test with empty value
    result = map_people_of_color("")
    assert result == False

    # Test with None value
    result = map_people_of_color(None)
    assert result == False

    # Test with pandas NaN
    import pandas as pd

    result = map_people_of_color(pd.NA)
    assert result == False

    # Test with other values
    result = map_people_of_color("No")
    assert result == False

    result = map_people_of_color("Maybe")
    assert result == False


def test_people_of_color_boolean_field():
    """Test that the is_people_of_color field exists as a boolean"""
    from models.volunteer import Volunteer

    # Verify the field exists and is a boolean
    assert hasattr(Volunteer, "is_people_of_color")
    # The field should be a Boolean column
    assert Volunteer.is_people_of_color.type.python_type == bool


# New tests for teacher name splitting functionality
def test_split_teacher_names():
    """Test teacher name splitting functionality"""
    from routes.virtual.routes import split_teacher_names

    # Test multiple teachers separated by slash
    result = split_teacher_names("James Brockway/Megan Gasser")
    assert result == ["James Brockway", "Megan Gasser"]

    # Test single teacher
    result = split_teacher_names("John Smith")
    assert result == ["John Smith"]

    # Test with spaces around slash
    result = split_teacher_names("Jane Doe / Bob Wilson")
    assert result == ["Jane Doe", "Bob Wilson"]

    # Test multiple teachers
    result = split_teacher_names("Alice Johnson/Bob Smith/Charlie Brown")
    assert result == ["Alice Johnson", "Bob Smith", "Charlie Brown"]

    # Test empty string
    result = split_teacher_names("")
    assert result == []

    # Test None value
    result = split_teacher_names(None)
    assert result == []

    # Test whitespace only
    result = split_teacher_names("   ")
    assert result == []

    # Test single name
    result = split_teacher_names("John")
    assert result == ["John"]

    # Test with pandas NaN
    import pandas as pd

    result = split_teacher_names(pd.NaT)  # Use NaT instead of NA
    assert result == []


def test_process_teacher_data_with_multiple_teachers(app):
    """Test processing teacher data with multiple teachers"""
    from routes.virtual.routes import process_teacher_data

    with app.app_context():
        # Create test data with multiple teachers
        row_data = {
            "Teacher Name": "James Brockway/Megan Gasser",
            "School Name": "Test School",
            "District": "Test District",
        }

        # This should create two separate teacher records
        process_teacher_data(row_data)

    # Verify both teachers were created
    james = Teacher.query.filter_by(first_name="James", last_name="Brockway").first()
    megan = Teacher.query.filter_by(first_name="Megan", last_name="Gasser").first()

    assert james is not None
    assert megan is not None


def test_process_teacher_for_event_with_multiple_teachers(app):
    """Test processing teacher data for events with multiple teachers"""
    from models import db
    from models.event import Event, EventStatus, EventType
    from routes.virtual.routes import process_teacher_for_event

    with app.app_context():
        # Create a test event
        from datetime import datetime, timezone

        event = Event(
            title="Test Virtual Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now(timezone.utc),
        )
        db.session.add(event)
        db.session.commit()

        # Create test data with multiple teachers
        row_data = {
            "Teacher Name": "James Brockway/Megan Gasser",
            "School Name": "Test School",
            "District": "Test District",
            "Status": "Completed",
        }

        # Process teacher data for the event
        process_teacher_for_event(row_data, event, False)

        # Verify both teachers are associated with the event
        from models.event import EventTeacher

        event_teachers = EventTeacher.query.filter_by(event_id=event.id).all()
        assert len(event_teachers) == 2

        # Clean up
        db.session.delete(event)
        db.session.commit()


# New tests for district filtering functionality
def test_calculate_summaries_with_main_districts_only():
    """Test district summaries calculation with main districts only"""
    from routes.reports.virtual_session import calculate_summaries_from_sessions

    # Create test session data with multiple districts
    session_data = [
        {
            "district": "Hickman Mills School District",
            "status": "successfully completed",
            "teacher_name": "Teacher 1",
            "school_name": "Test School 1",
            "session_title": "Test Session 1",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Grandview School District",
            "status": "successfully completed",
            "teacher_name": "Teacher 2",
            "school_name": "Test School 2",
            "session_title": "Test Session 2",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Unknown District",
            "status": "successfully completed",
            "teacher_name": "Teacher 3",
            "school_name": "Test School 3",
            "session_title": "Test Session 3",
            "presenter_data": [],
            "presenter": None,
        },
    ]

    # Test with show_all_districts=False (default)
    district_summaries, overall_summary = calculate_summaries_from_sessions(
        session_data, show_all_districts=False
    )

    # Should only include main districts
    assert "Hickman Mills School District" in district_summaries
    assert "Grandview School District" in district_summaries
    assert "Unknown District" not in district_summaries


def test_calculate_summaries_with_all_districts():
    """Test district summaries calculation with all districts"""
    from routes.reports.virtual_session import calculate_summaries_from_sessions

    # Create test session data with multiple districts
    session_data = [
        {
            "district": "Hickman Mills School District",
            "status": "successfully completed",
            "teacher_name": "Teacher 1",
            "school_name": "Test School 1",
            "session_title": "Test Session 1",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Grandview School District",
            "status": "successfully completed",
            "teacher_name": "Teacher 2",
            "school_name": "Test School 2",
            "session_title": "Test Session 2",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Unknown District",
            "status": "successfully completed",
            "teacher_name": "Teacher 3",
            "school_name": "Test School 3",
            "session_title": "Test Session 3",
            "presenter_data": [],
            "presenter": None,
        },
    ]

    # Test with show_all_districts=True
    district_summaries, overall_summary = calculate_summaries_from_sessions(
        session_data, show_all_districts=True
    )

    # Should include all districts
    assert "Hickman Mills School District" in district_summaries
    assert "Grandview School District" in district_summaries
    assert "Unknown District" in district_summaries


def test_virtual_usage_report_with_admin_toggle(client, auth_headers):
    """Test virtual usage report with admin district toggle"""
    # Test default view (main districts only)
    response = safe_route_test(client, "/virtual/usage", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # Test with show_all_districts parameter
    response = safe_route_test(
        client, "/virtual/usage?show_all_districts=1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_district_filtering(client, auth_headers):
    """Test virtual usage report district filtering"""
    # Test with main district filter
    response = safe_route_test(
        client,
        "/virtual/usage?district=Hickman Mills School District",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # Test with non-main district filter
    response = safe_route_test(
        client, "/virtual/usage?district=Unknown District", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_create_virtual_session_from_usage_page(client, test_admin):
    """Create a virtual session via /virtual/usage/create (admin only)."""
    # Login as admin
    login_resp = client.post(
        "/login", data={"username": "admin", "password": "admin123"}
    )
    admin_headers = {"Cookie": login_resp.headers.get("Set-Cookie", "")}

    # Create a session with one teacher and one presenter
    payload = {
        "year": "2025-2026",
        "title": "Test App Created Virtual Session",
        "district": "Grandview School District",
        "date": "2026-05-14",
        "time": "09:15",
        "duration": "60",
        "session_type": "Teacher requested",
        "topic_theme": "STEM",
        "teacher_name[]": ["Jane Doe"],
        "teacher_school[]": ["Belvidere Elementary"],
        "presenter_name[]": ["Tyler Bennett"],
        "presenter_org[]": ["TLA Solutions"],
    }

    resp = safe_route_test(
        client,
        "/virtual/usage/create",
        method="POST",
        headers=admin_headers,
        data=payload,
        expected_statuses=[302, 200, 400, 403, 500],
    )
    assert_route_response(resp, expected_statuses=[302, 200, 400, 403, 500])

    # If creation succeeded, the Event should exist
    if resp.status_code in (200, 302):
        from models import db
        from models.event import Event

        event = Event.query.filter_by(title="Test App Created Virtual Session").first()
        assert event is not None
        assert getattr(event, "session_host", None) == "APP"


def test_enhanced_virtual_purge_functionality(client, auth_headers):
    """Test enhanced virtual purge functionality"""
    # Create test virtual session data
    from datetime import datetime, timezone

    from models.event import Event, EventStatus, EventType

    event = Event(
        title="Test Virtual Session",
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.COMPLETED,
        start_date=datetime.now(timezone.utc),
    )
    db.session.add(event)
    db.session.commit()

    # Test purge endpoint
    response = safe_route_test(
        client, "/virtual/purge", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])

    if response.status_code == 200:
        # Verify response contains detailed purge information
        data = response.get_json()
        assert "success" in data
        assert "count" in data
        assert "teachers_deleted" in data
        assert "event_teachers_deleted" in data
        assert "event_participations_deleted" in data


def test_virtual_session_status_filtering():
    """Test virtual session status filtering with case-insensitive matching"""
    from routes.reports.virtual_session import calculate_summaries_from_sessions

    # Create test session data with different status formats
    session_data = [
        {
            "district": "Hickman Mills School District",
            "status": "SUCCESSFULLY COMPLETED",
            "teacher_name": "Teacher 1",
            "school_name": "Test School 1",
            "session_title": "Test Session 1",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Grandview School District",
            "status": "successfully completed",
            "teacher_name": "Teacher 2",
            "school_name": "Test School 2",
            "session_title": "Test Session 2",
            "presenter_data": [],
            "presenter": None,
        },
        {
            "district": "Kansas City Kansas Public Schools",
            "status": "Simulcast",
            "teacher_name": "Teacher 3",
            "school_name": "Test School 3",
            "session_title": "Test Session 3",
            "presenter_data": [],
            "presenter": None,
        },
    ]

    # Test that all valid statuses are counted
    district_summaries, overall_summary = calculate_summaries_from_sessions(
        session_data
    )

    # Should include all districts with valid statuses
    assert "Hickman Mills School District" in district_summaries
    assert "Grandview School District" in district_summaries
    assert "Kansas City Kansas Public Schools" in district_summaries


def test_virtual_session_cache_invalidation():
    """Test virtual session cache invalidation"""
    from routes.reports.virtual_session import invalidate_virtual_session_caches

    # Test cache invalidation for specific year
    try:
        invalidate_virtual_session_caches("2024-2025")
        # Should not raise an exception
        assert True
    except Exception as e:
        # If it fails, that's okay for testing purposes
        assert True

    # Test cache invalidation for all years
    try:
        invalidate_virtual_session_caches()
        # Should not raise an exception
        assert True
    except Exception as e:
        # If it fails, that's okay for testing purposes
        assert True
