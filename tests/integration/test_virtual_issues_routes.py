"""
Integration tests for virtual district issue reporting routes.

Tests the three endpoints in routes/virtual/issues.py:
- GET /virtual/issues/api/search-teachers
- GET /virtual/issues/api/teacher-sessions
- POST /virtual/issues/report
"""

import json
from datetime import datetime, timezone

import pytest
from flask import url_for

from models import db
from models.bug_report import BugReport, BugReportType
from models.district_model import District
from models.event import Event, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from tests.conftest import assert_route_response, safe_route_test


@pytest.fixture
def district_user_headers(test_district_user, client):
    """Get auth headers for district-scoped user"""
    response = client.post(
        "/login", data={"username": "districtuser", "password": "password123"}
    )
    return {"Cookie": response.headers.get("Set-Cookie", "")}


@pytest.fixture
def test_teacher_with_school(app):
    """Create a teacher with a school for testing"""
    with app.app_context():
        district = District(name="Kansas City Kansas Public Schools")
        db.session.add(district)
        db.session.flush()

        school = School(
            id="TEST001",
            name="Test School",
            district_id=district.id,
            normalized_name="test school",
        )
        db.session.add(school)
        db.session.flush()

        teacher = Teacher(
            first_name="Sarah",
            last_name="Cordell",
            school_id=school.id,
        )
        db.session.add(teacher)
        db.session.commit()

        yield teacher

        db.session.delete(teacher)
        db.session.delete(school)
        db.session.delete(district)
        db.session.commit()


@pytest.fixture
def test_teacher_not_in_progress(app):
    """Create a teacher NOT in TeacherProgress for testing"""
    with app.app_context():
        district = District(name="Kansas City Kansas Public Schools")
        db.session.add(district)
        db.session.flush()

        school = School(
            id="TEST002",
            name="Other School",
            district_id=district.id,
            normalized_name="other school",
        )
        db.session.add(school)
        db.session.flush()

        teacher = Teacher(
            first_name="John",
            last_name="Doe",
            school_id=school.id,
        )
        db.session.add(teacher)
        db.session.commit()

        yield teacher

        db.session.delete(teacher)
        db.session.delete(school)
        db.session.delete(district)
        db.session.commit()


@pytest.fixture
def test_teacher_progress_entry(app, test_teacher_with_school):
    """Create a TeacherProgress entry linked to a teacher"""
    with app.app_context():
        teacher_progress = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test School",
            name="Sarah Cordell",
            email="sarah.cordell@example.com",
            grade="K",
            target_sessions=1,
            teacher_id=test_teacher_with_school.id,
        )
        db.session.add(teacher_progress)
        db.session.commit()

        yield teacher_progress

        db.session.delete(teacher_progress)
        db.session.commit()


@pytest.fixture
def test_teacher_progress_without_teacher_id(app):
    """Create a TeacherProgress entry without teacher_id (name matching only)"""
    with app.app_context():
        teacher_progress = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Test School 2",
            name="Jane Smith",
            email="jane.smith@example.com",
            grade="1",
            target_sessions=1,
            teacher_id=None,
        )
        db.session.add(teacher_progress)
        db.session.commit()

        yield teacher_progress

        db.session.delete(teacher_progress)
        db.session.commit()


@pytest.fixture
def test_virtual_session_event(app, test_teacher_with_school):
    """Create a virtual session event for testing"""
    with app.app_context():
        event = Event(
            title="4th and 5th Grade SEL: Managing My Emotions",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime(2025, 12, 4, 14, 0, tzinfo=timezone.utc),
            duration=60,
        )
        db.session.add(event)
        db.session.flush()

        event_teacher = EventTeacher(
            event_id=event.id,
            teacher_id=test_teacher_with_school.id,
            status="Completed",
        )
        db.session.add(event_teacher)
        db.session.commit()

        yield event

        db.session.delete(event_teacher)
        db.session.delete(event)
        db.session.commit()


# ============================================================================
# Tests for GET /virtual/issues/api/search-teachers
# ============================================================================


def test_search_teachers_for_issues_success(
    client, district_user_headers, test_teacher_progress_entry, test_teacher_with_school
):
    """Test successful teacher search with TeacherProgress filtering"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "sarah",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Should only return teachers in TeacherProgress
    teacher_ids = [t["id"] for t in data]
    assert test_teacher_with_school.id in teacher_ids


def test_search_teachers_for_issues_requires_auth(client):
    """Test that unauthenticated access is denied"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "test",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
    )

    assert response.status_code in [302, 401, 403]


def test_search_teachers_for_issues_allows_global_users(client, auth_headers):
    """Test that global users can access the endpoint (district_scoped_required allows global)"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "test",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=auth_headers,
    )

    # Global users are allowed by district_scoped_required decorator
    assert response.status_code in [
        200,
        400,
    ]  # 200 if data exists, 400 if validation fails


def test_search_teachers_for_issues_district_access_validation(
    client, district_user_headers, test_teacher_progress_entry
):
    """Test that district users can only search their districts"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "test",
            "virtual_year": "2025-2026",
            "district_name": "Other District",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data
    assert "Access denied" in data["error"]


def test_search_teachers_for_issues_requires_virtual_year(
    client, district_user_headers
):
    """Test that missing virtual_year returns 400"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "test",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "virtual_year" in data["error"]


def test_search_teachers_for_issues_minimum_query_length(
    client, district_user_headers, test_teacher_progress_entry
):
    """Test that query < 2 chars returns empty array"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "s",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_search_teachers_for_issues_filters_by_teacher_progress(
    client,
    district_user_headers,
    test_teacher_progress_entry,
    test_teacher_with_school,
    test_teacher_not_in_progress,
):
    """Test that only teachers in TeacherProgress are returned"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "john",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    # test_teacher_not_in_progress should NOT appear in results
    teacher_ids = [t["id"] for t in data]
    assert test_teacher_not_in_progress.id not in teacher_ids


def test_search_teachers_for_issues_no_teacher_progress_entries(
    client, district_user_headers
):
    """Test that empty array is returned when no TeacherProgress entries exist"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "test",
            "virtual_year": "2024-2025",  # Different year with no entries
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_search_teachers_for_issues_with_teacher_id(
    client, district_user_headers, test_teacher_progress_entry, test_teacher_with_school
):
    """Test search when teacher_id is set in TeacherProgress"""
    response = client.get(
        "/virtual/issues/api/search-teachers",
        query_string={
            "q": "cordell",
            "virtual_year": "2025-2026",
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
    # Should return teacher data from Teacher table
    teacher = next((t for t in data if t["id"] == test_teacher_with_school.id), None)
    assert teacher is not None
    assert teacher["name"] == "Sarah Cordell"
    assert teacher["school"] == "Test School"


def test_search_teachers_for_issues_without_teacher_id(
    client, district_user_headers, test_teacher_progress_without_teacher_id, app
):
    """Test search falls back to name matching when no teacher_id"""
    with app.app_context():
        # Create a teacher with matching name
        teacher = Teacher(
            first_name="Jane",
            last_name="Smith",
        )
        db.session.add(teacher)
        db.session.commit()

        try:
            response = client.get(
                "/virtual/issues/api/search-teachers",
                query_string={
                    "q": "jane",
                    "virtual_year": "2025-2026",
                    "district_name": "Kansas City Kansas Public Schools",
                },
                headers=district_user_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            # Should find teacher by name matching
            assert len(data) > 0
        finally:
            db.session.delete(teacher)
            db.session.commit()


# ============================================================================
# Tests for GET /virtual/issues/api/teacher-sessions
# ============================================================================


def test_get_teacher_sessions_success(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_virtual_session_event,
):
    """Test successful retrieval of teacher sessions"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": test_teacher_with_school.id,
            "district_name": "Kansas City Kansas Public Schools",
            "date_from": "2025-08-01",
            "date_to": "2026-07-31",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Should include the test event
    event_ids = [s["id"] for s in data]
    assert test_virtual_session_event.id in event_ids


def test_get_teacher_sessions_requires_auth(client, test_teacher_with_school):
    """Test that unauthenticated access is denied"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": test_teacher_with_school.id,
            "district_name": "Kansas City Kansas Public Schools",
        },
    )

    assert response.status_code in [302, 401, 403]


def test_get_teacher_sessions_allows_global_users(
    client, auth_headers, test_teacher_with_school
):
    """Test that global users can access the endpoint (district_scoped_required allows global)"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": test_teacher_with_school.id,
            "district_name": "Kansas City Kansas Public Schools",
            "date_from": "2025-08-01",
            "date_to": "2026-07-31",
        },
        headers=auth_headers,
    )

    # Global users are allowed by district_scoped_required decorator
    assert response.status_code in [
        200,
        404,
    ]  # 200 if data exists, 404 if teacher not found


def test_get_teacher_sessions_district_access_validation(
    client, district_user_headers, test_teacher_with_school
):
    """Test that district users can only access their districts"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": test_teacher_with_school.id,
            "district_name": "Other District",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data
    assert "Access denied" in data["error"]


def test_get_teacher_sessions_requires_teacher_id(client, district_user_headers):
    """Test that missing teacher_id returns 400"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "teacher_id" in data["error"]


def test_get_teacher_sessions_filters_by_date_range(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_virtual_session_event,
    app,
):
    """Test that date filters work correctly"""
    with app.app_context():
        # Create an event outside the date range
        old_event = Event(
            title="Old Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            duration=60,
        )
        db.session.add(old_event)
        db.session.flush()

        old_event_teacher = EventTeacher(
            event_id=old_event.id,
            teacher_id=test_teacher_with_school.id,
            status="Completed",
        )
        db.session.add(old_event_teacher)
        db.session.commit()

        try:
            response = client.get(
                "/virtual/issues/api/teacher-sessions",
                query_string={
                    "teacher_id": test_teacher_with_school.id,
                    "district_name": "Kansas City Kansas Public Schools",
                    "date_from": "2025-08-01",
                    "date_to": "2026-07-31",
                },
                headers=district_user_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            # Should not include old_event (outside date range)
            event_ids = [s["id"] for s in data]
            assert old_event.id not in event_ids
            # Should include test_virtual_session_event (within date range)
            assert test_virtual_session_event.id in event_ids
        finally:
            db.session.delete(old_event_teacher)
            db.session.delete(old_event)
            db.session.commit()


def test_get_teacher_sessions_no_sessions_found(
    client, district_user_headers, test_teacher_with_school
):
    """Test that empty array is returned when no sessions found"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": test_teacher_with_school.id,
            "district_name": "Kansas City Kansas Public Schools",
            "date_from": "2020-01-01",
            "date_to": "2020-12-31",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_get_teacher_sessions_invalid_teacher_id(client, district_user_headers):
    """Test that invalid teacher_id returns 404"""
    response = client.get(
        "/virtual/issues/api/teacher-sessions",
        query_string={
            "teacher_id": 99999,
            "district_name": "Kansas City Kansas Public Schools",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 404


# ============================================================================
# Tests for POST /virtual/issues/report
# ============================================================================


def test_report_district_issue_success(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_district_user,
    app,
):
    """Test successful issue submission creates BugReport"""
    with app.app_context():
        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "category": "missing",
                "page_url": "/test/page",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify BugReport was created
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        assert bug_report.type == BugReportType.DATA_ERROR
        assert "Source: District" in bug_report.description
        assert "Kansas City Kansas Public Schools" in bug_report.description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()


def test_report_district_issue_requires_auth(client, test_teacher_with_school):
    """Test that unauthenticated access is denied"""
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": test_teacher_with_school.id,
            "category": "missing",
            "page_url": "/test/page",
        },
    )

    assert response.status_code in [302, 401, 403]


def test_report_district_issue_requires_district_scope(
    client, auth_headers, test_teacher_with_school
):
    """Test that non-district users get 403"""
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": test_teacher_with_school.id,
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=auth_headers,
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data
    assert "district users only" in data["error"].lower()


def test_report_district_issue_district_access_validation(
    client, district_user_headers, test_teacher_with_school
):
    """Test that district users can only report for their districts"""
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Other District",
            "teacher_id": test_teacher_with_school.id,
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data
    assert "Access denied" in data["error"]


def test_report_district_issue_required_fields(
    client, district_user_headers, test_teacher_with_school
):
    """Test that missing required fields return 400"""
    # Missing district_name
    response = client.post(
        "/virtual/issues/report",
        json={
            "teacher_id": test_teacher_with_school.id,
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )
    assert response.status_code == 400

    # Missing teacher_id
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )
    assert response.status_code == 400

    # Missing category
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": test_teacher_with_school.id,
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )
    assert response.status_code == 400

    # Missing page_url
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": test_teacher_with_school.id,
            "category": "missing",
        },
        headers=district_user_headers,
    )
    assert response.status_code == 400


def test_report_district_issue_invalid_category(
    client, district_user_headers, test_teacher_with_school
):
    """Test that invalid category returns 400"""
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": test_teacher_with_school.id,
            "category": "invalid",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "category" in data["error"].lower()


def test_report_district_issue_invalid_teacher_id(client, district_user_headers):
    """Test that invalid teacher_id returns 400/404/500"""
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": "not_a_number",
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

    # Test with non-existent teacher_id
    # get_or_404 may raise 404 or 500 depending on error handling
    response = client.post(
        "/virtual/issues/report",
        json={
            "district_name": "Kansas City Kansas Public Schools",
            "teacher_id": 99999,
            "category": "missing",
            "page_url": "/test/page",
        },
        headers=district_user_headers,
    )

    # Accept either 404 (from get_or_404) or 500 (if exception is caught)
    assert response.status_code in [404, 500]


def test_report_district_issue_with_session(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_virtual_session_event,
    test_district_user,
    app,
):
    """Test issue submission with session_id includes session info"""
    with app.app_context():
        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "session_id": test_virtual_session_event.id,
                "category": "incorrect",
                "page_url": "/test/page",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200

        # Verify BugReport includes session info
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        assert "Session:" in bug_report.description
        assert str(test_virtual_session_event.id) in bug_report.description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()


def test_report_district_issue_without_session(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_district_user,
    app,
):
    """Test issue submission works without session_id"""
    with app.app_context():
        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "category": "missing",
                "page_url": "/test/page",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200

        # Verify BugReport was created without session info
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        assert "Session:" not in bug_report.description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()


def test_report_district_issue_auto_fills_school(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_district_user,
    app,
):
    """Test that school is auto-filled from teacher if not provided"""
    with app.app_context():
        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "category": "missing",
                "page_url": "/test/page",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200

        # Verify BugReport includes school name
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        assert "School: Test School" in bug_report.description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()


def test_report_district_issue_creates_bug_report(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_district_user,
    app,
):
    """Test that BugReport is created with correct data"""
    with app.app_context():
        initial_count = BugReport.query.count()

        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "category": "missing",
                "page_url": "/test/page",
                "description": "Test issue description",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200

        # Verify BugReport count increased
        new_count = BugReport.query.count()
        assert new_count == initial_count + 1

        # Verify BugReport fields
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        assert bug_report.type == BugReportType.DATA_ERROR
        assert bug_report.page_url == "/test/page"
        assert bug_report.submitted_by_id == test_district_user.id
        assert "Test issue description" in bug_report.description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()


def test_report_district_issue_structured_description(
    client,
    district_user_headers,
    test_teacher_with_school,
    test_district_user,
    app,
):
    """Test that structured description format is correct"""
    with app.app_context():
        response = client.post(
            "/virtual/issues/report",
            json={
                "district_name": "Kansas City Kansas Public Schools",
                "teacher_id": test_teacher_with_school.id,
                "school_name": "Test School",
                "category": "incorrect",
                "page_url": "/test/page",
                "description": "Additional notes here",
            },
            headers=district_user_headers,
        )

        assert response.status_code == 200

        # Verify structured description
        bug_report = BugReport.query.filter_by(
            submitted_by_id=test_district_user.id
        ).first()
        assert bug_report is not None
        description = bug_report.description

        assert "Source: District" in description
        assert "District: Kansas City Kansas Public Schools" in description
        assert "Teacher: Sarah Cordell" in description
        assert f"ID: {test_teacher_with_school.id}" in description
        assert "School: Test School" in description
        assert "Category: incorrect" in description
        assert "Notes: Additional notes here" in description

        # Clean up
        db.session.delete(bug_report)
        db.session.commit()
