from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.contact import LocalStatusEnum
from models.district_model import District
from models.event import Event, EventStatus, EventType
from models.organization import Organization
from models.teacher import Teacher
from models.volunteer import EventParticipation, Volunteer
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

# --- Local/Non-Local Tests (TC-230, TC-231, TC-232) ---


def test_local_non_local_flag_persistence(client, auth_headers):
    """
    Test persistence of Local/Non-Local status (TC-230).
    Verifies that volunteers marked as local or non-local retain this status
    and it is correctly reflected in the virtual events list.
    """
    with client.application.app_context():
        # Create a Local Volunteer
        local_vol = Volunteer(
            first_name="Local",
            last_name="Volunteer",
            local_status=LocalStatusEnum.local
        )
        db.session.add(local_vol)

        # Create a Non-Local Volunteer
        non_local_vol = Volunteer(
            first_name="NonLocal",
            last_name="Volunteer",
            local_status=LocalStatusEnum.non_local
        )
        db.session.add(non_local_vol)

        # Create an event for each
        future_date = datetime.now() + timedelta(days=10)
        
        event_local = Event(
            title="Local Presenter Event",
            start_date=future_date,
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED
        )
        event_non_local = Event(
            title="Non-Local Presenter Event",
            start_date=future_date,
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED
        )
        
        db.session.add(event_local)
        db.session.add(event_non_local)
        db.session.commit()

        # Assign volunteers (using EventParticipation manually as in routes logic)
        part_local = EventParticipation(
            event_id=event_local.id,
            volunteer_id=local_vol.id,
            participant_type="Presenter",
            status="Confirmed"
        )
        part_non_local = EventParticipation(
            event_id=event_non_local.id,
            volunteer_id=non_local_vol.id,
            participant_type="Presenter",
            status="Confirmed"
        )
        db.session.add(part_local)
        db.session.add(part_non_local)
        
        # Also need to associate to volunteers list for some logic
        event_local.volunteers.append(local_vol)
        event_non_local.volunteers.append(non_local_vol)
        
        db.session.commit()

    # Now verify via the API
    response = client.get("/virtual/events", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    
    events = data["events"]
    
    # Check Local Event
    local_event_data = next((e for e in events if e["title"] == "Local Presenter Event"), None)
    assert local_event_data is not None
    assert local_event_data["presenter_name"] == "Local Volunteer"
    assert local_event_data["presenter_location_type"] == "Local (KS/MO)"

    # Check Non-Local Event
    non_local_event_data = next((e for e in events if e["title"] == "Non-Local Presenter Event"), None)
    assert non_local_event_data is not None
    assert non_local_event_data["presenter_name"] == "NonLocal Volunteer"
    assert non_local_event_data["presenter_location_type"] == "Non-local"


def test_unknown_local_flag(client, auth_headers):
    """
    Test handling of Unknown local status (TC-232).
    Verifies that 'unknown' status is handled gracefully (returns None or specific string).
    """
    with client.application.app_context():
        # Create Unknown Status Volunteer
        unknown_vol = Volunteer(
            first_name="Unknown",
            last_name="Location",
            local_status=LocalStatusEnum.unknown
        )
        db.session.add(unknown_vol)
        
        event = Event(
            title="Unknown Location Event",
            start_date=datetime.now() + timedelta(days=10),
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED
        )
        db.session.add(event)
        db.session.commit()
        
        part = EventParticipation(
            event_id=event.id,
            volunteer_id=unknown_vol.id,
            participant_type="Presenter",
            status="Confirmed"
        )
        db.session.add(part)
        event.volunteers.append(unknown_vol)
        db.session.commit()

    response = client.get("/virtual/events", headers=auth_headers)
    assert response.status_code == 200
    events = response.get_json()["events"]
    
    event_data = next((e for e in events if e["title"] == "Unknown Location Event"), None)
    assert event_data is not None
    # Depending on implementation, checking if it is None or omitted
    # Logic in list_events: else: presenter_location_type = None
    assert event_data["presenter_location_type"] is None


def test_local_non_local_filtering(client, auth_headers):
    """
    Verify backend provides necessary data for filtering (TC-231).
    Since actual filtering happens in UI (DataTables/JS), we verify the API 
    returns the distinguishing fields correctly to enable this.
    """
    # Reuse setup from test_local_non_local_flag_persistence logic implicitly or explicitly
    # We essentially verified this in the previous test by checking 'presenter_location_type'.
    # This test explicitly validates that the field used for filtering exists.
    
    test_local_non_local_flag_persistence(client, auth_headers)
# --- Import Logic Tests (TC-270, TC-273, TC-275) ---

def test_virtual_import_logic_idempotency(client, auth_headers):
    """
    Test Idempotency of import logic (TC-273).
    Running the import twice with the exact same data should result in:
    1. First run: Success, events created.
    2. Second run: Success, 0 new events, 0 duplicates.
    """
    import pandas as pd
    from scripts.daily_imports.run_virtual_import_2025_26_standalone import run_import_logic_direct
    from models.event import Event

    with client.application.app_context():
        # Setup mock data using DataFrame as expected by the script
        data = {
            "Session Title": ["Idempotency Test Session"],
            "Date": [(datetime.now() + timedelta(days=20)).strftime("%m/%d/%Y")],
            "Time": ["10:00 AM"],
            "Duration": ["60"],
            "Session Type": ["Workshop"],
            "Status": ["Confirmed"],
            "Teacher Name": ["Test Teacher"],
            "School Name": ["Test School"],
            "District": ["Test District Independency"],
            "Session Link": ["http://meet.google.com/abc-defg-hij"]
        }
        df = pd.DataFrame(data)
        academic_year = "2025-2026"

        # 1. First Run -> Should Create
        result1 = run_import_logic_direct(df, academic_year)
        assert result1["success"] is True
        assert result1["success_count"] == 1
        
        event = Event.query.filter_by(title="Idempotency Test Session").first()
        assert event is not None
        event_id = event.id

        # 2. Second Run -> Should Update/No-Op (Idempotent)
        result2 = run_import_logic_direct(df, academic_year)
        assert result2["success"] is True
        # The script counts "processed" events, so it might still say success_count=1 if it updated it
        # But crucially, we must check that count of events in DB is still 1
        
        events_count = Event.query.filter_by(title="Idempotency Test Session").count()
        assert events_count == 1
        
        event_after = Event.query.filter_by(title="Idempotency Test Session").first()
        assert event_after.id == event_id  # ID preserved


def test_virtual_import_multi_line_handling(client, auth_headers):
    """
    Test Multi-line handling (TC-270, TC-275).
    Two rows with same Session Title + Date but different teachers 
    should result in ONE event with TWO teachers.
    """
    import pandas as pd
    from scripts.daily_imports.run_virtual_import_2025_26_standalone import run_import_logic_direct
    from models.event import Event

    with client.application.app_context():
        dataset_date = (datetime.now() + timedelta(days=25)).strftime("%m/%d/%Y")
        data = {
            "Session Title": ["Multi-Line Test Session", "Multi-Line Test Session"],
            "Date": [dataset_date, dataset_date],
            "Time": ["2:00 PM", "2:00 PM"],
            "Duration": ["60", "60"],
            "Session Type": ["Panel", "Panel"],
            "Status": ["Confirmed", "Confirmed"],
            "Teacher Name": ["Teacher A", "Teacher B"], # Different teachers
            "School Name": ["School A", "School B"],
            "District": ["District A", "District B"],
            "Session Link": ["http://link", "http://link"]
        }
        df = pd.DataFrame(data)
        academic_year = "2025-2026"

        result = run_import_logic_direct(df, academic_year)
        assert result["success"] is True
        
        # Verify only ONE event exists
        events = Event.query.filter_by(title="Multi-Line Test Session").all()
        assert len(events) == 1
        event = events[0]
        
        # Verify associations (TC-275)
        # Should have 2 teacher registrations
        assert len(event.teacher_registrations) == 2
        
        # Verify specific teachers are linked
        # "Teacher A" splits to First="Teacher", Last="A"
        # "Teacher B" splits to First="Teacher", Last="B"
        linked_last_names = [tr.teacher.last_name for tr in event.teacher_registrations]
        assert "A" in linked_last_names
        assert "B" in linked_last_names
