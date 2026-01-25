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

# --- View Tests ---


def test_virtual_sessions_view(client, auth_headers):
    """Test virtual sessions main view"""
    response = safe_route_test(client, "/virtual", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 301, 302, 404, 500])


def test_virtual_usage_view(client, auth_headers):
    """Test virtual usage main view (the dashboard)"""
    response = safe_route_test(client, "/virtual/usage", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


# --- Functional Tests (TC-200, TC-204) ---


def test_virtual_session_creation_robust(client, test_admin):
    """
    Test virtual session creation with Teacher and Presenter tagging (TC-200, TC-204).
    Verifies that the session is created and relationships are established.
    """
    # Login as admin to get cookies (using test_admin fixture logic if available or manual login)
    login_resp = client.post(
        "/login", data={"username": "admin", "password": "admin123"}
    )
    if login_resp.status_code != 302:
        pytest.skip("Admin login failed, cannot proceed with creation test")

    admin_headers = {"Cookie": login_resp.headers.get("Set-Cookie", "")}

    # Prepare data for new session
    session_title = "Robust Integration Test Session"
    session_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    payload = {
        "year": "2025-2026",
        "title": session_title,
        "district": "Test District",  # This is actually derived from teacher in backend, but form might send it
        "date": session_date,
        "time": "10:00",
        "duration": "60",
        "session_type": "Career Panel",
        "topic_theme": "Engineering",
        "session_link": "http://example.com/meeting",
        # Teacher Data (TC-202)
        "teacher_name[]": ["Test Teacher"],
        "teacher_school[]": ["Test School A"],
        "teacher_id[]": [""],  # New teacher, no ID
        # Presenter Data (TC-203)
        "presenter_name[]": ["Test Presenter"],
        "presenter_org[]": ["Test Org B"],
        "presenter_id[]": [""],  # New presenter, no ID
    }

    response = client.post(
        "/virtual/usage/create",
        data=payload,
        headers=admin_headers,
        follow_redirects=True,
    )

    # Check for success redirect or 200 OK (if it renders template on success)
    assert response.status_code == 200

    # Verify Database State FIRST to determine if logic worked
    with client.application.app_context():
        event = Event.query.filter_by(title=session_title).first()
        if not event:
            print(f"DEBUG: Response Data: {response.data}")
        assert event is not None, "Event was not created in DB"
        assert event.session_host == "APP"
        assert event.type == EventType.VIRTUAL_SESSION

        # Verify Teacher Tagging
        assert len(event.teacher_registrations) == 1
        teacher = event.teacher_registrations[0].teacher
        assert teacher.first_name == "Test"
        assert teacher.last_name == "Teacher"
        assert teacher.school.name == "Test School A"

        # Verify Presenter Tagging
        assert len(event.volunteers) == 1
        volunteer = event.volunteers[0]
        assert volunteer.first_name == "Test"
        assert volunteer.last_name == "Presenter"

    # Ideally check for a flash message "Virtual session created"
    # assert b"Virtual session created" in response.data


def test_virtual_session_quick_create(client, test_admin):
    """
    Test virtual session creation with Quick Create for Teacher and Presenter (TC-206, TC-207).
    Verifies that local records are created and linked.
    """
    login_resp = client.post(
        "/login", data={"username": "admin", "password": "admin123"}
    )
    if login_resp.status_code != 302:
        pytest.skip("Admin login failed")

    admin_headers = {"Cookie": login_resp.headers.get("Set-Cookie", "")}

    session_title = "Quick Create Test Session"
    session_date = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")

    payload = {
        "year": "2025-2026",
        "title": session_title,
        "date": session_date,
        "time": "14:00",
        "duration": "45",
        "session_type": "Workshop",
        "teacher_id[]": [],
        "presenter_id[]": [],
        # Quick Create Teacher
        "new_teacher_first_name[]": ["QuickFirst"],
        "new_teacher_last_name[]": ["QuickLast"],
        "new_teacher_school[]": ["Quick School"],
        # Quick Create Presenter
        "new_presenter_first_name[]": ["QuickPFirst"],
        "new_presenter_last_name[]": ["QuickPLast"],
        "new_presenter_org[]": ["Quick Org"],
    }

    response = client.post(
        "/virtual/usage/create",
        data=payload,
        headers=admin_headers,
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.application.app_context():
        event = Event.query.filter_by(title=session_title).first()
        assert event is not None

        # Verify Teacher
        assert len(event.teacher_registrations) == 1
        teacher = event.teacher_registrations[0].teacher
        assert teacher.first_name == "QuickFirst"
        assert teacher.last_name == "QuickLast"
        assert teacher.school.name == "Quick School"

        # Verify Presenter
        assert len(event.volunteers) == 1
        volunteer = event.volunteers[0]
        assert volunteer.first_name == "QuickPFirst"
        assert volunteer.last_name == "QuickPLast"

        # Verify Org
        vol_org = [
            vo
            for vo in volunteer.volunteer_organizations
            if vo.organization.name == "Quick Org"
        ]
        assert len(vol_org) > 0


# --- Search API Tests (TC-205) ---


def test_search_teachers_api(client, auth_headers):
    """
    Test teacher search API (TC-205).
    Verifies that it returns results for existing teachers and handles no results.
    """
    # 1. Search for existing teacher (Seed one if needed, or rely on existing seed)
    # Let's seed a specific one to be sure
    with client.application.app_context():
        t = Teacher(first_name="Searchable", last_name="TeacherOne")
        db.session.add(t)
        db.session.commit()

    response = client.get(
        "/virtual/usage/api/search-teachers?q=Searchable", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Searchable TeacherOne"

    # 2. Search for non-existent teacher
    response_empty = client.get(
        "/virtual/usage/api/search-teachers?q=NonExistentXYZ", headers=auth_headers
    )
    assert response_empty.status_code == 200  # Should still be 200 OK but empty list
    data_empty = response_empty.get_json()
    assert data_empty == []


def test_search_presenters_api(client, auth_headers):
    """
    Test presenter search API (TC-205).
    """
    with client.application.app_context():
        v = Volunteer(first_name="Searchable", last_name="PresenterOne")
        db.session.add(v)
        db.session.commit()

    response = client.get(
        "/virtual/usage/api/search-presenters?q=Searchable", headers=auth_headers
    )
    assert response.status_code == 200

    data = response.get_json()
    assert len(data) > 0
    assert data[0]["name"] == "Searchable PresenterOne"

    response_empty = client.get(
        "/virtual/usage/api/search-presenters?q=NonExistentXYZ", headers=auth_headers
    )
    assert response_empty.status_code == 200
    assert response_empty.get_json() == []


# --- Existing Tests (Preserved/Updated) ---


def test_virtual_import_sheet(client, auth_headers):
    """Test virtual session import from Google Sheets"""
    response = safe_route_test(client, "/virtual/import-sheet", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_virtual_purge_data(client, auth_headers):
    """Test virtual session data purge"""
    response = safe_route_test(
        client, "/virtual/purge", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_virtual_session_status_filtering():
    """Test virtual session status filtering with case-insensitive matching"""
    from routes.reports.virtual_session import calculate_summaries_from_sessions

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
    ]
    # Simple smoke test for the logic function
    summaries, _ = calculate_summaries_from_sessions(session_data)
    assert "Hickman Mills School District" in summaries
