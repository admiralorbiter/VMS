"""
Integration tests for District Dashboard (US-501, US-503).
Verifies access control and progress metric calculations.
"""

from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from models.user import User


@pytest.fixture
def dashboard_data(app):
    """
    Setup test data for District Dashboard tests.
    Matches the scenario in Implementation Plan:
    - District: 'Test District'
    - Schools: School A, School B
    - Teachers: Alice, Ian, Evan, Nora
    - Events: Mix of Completed and Future to test status logic.
    """
    with app.app_context():
        # 1. create District
        d1 = District(name="Test District")
        d2 = District(name="Other District")
        db.session.add_all([d1, d2])
        db.session.commit()

        # 2. Create Schools
        # School model uses String PK (Salesforce Format), so we must provide IDs
        s_a = School(id="SCHOOL_A_TEST_ID", name="School A", district_id=d1.id)
        s_b = School(id="SCHOOL_B_TEST_ID", name="School B", district_id=d1.id)
        s_c = School(id="SCHOOL_C_TEST_ID", name="School C", district_id=d2.id)
        db.session.add_all([s_a, s_b, s_c])
        db.session.commit()

        # 3. Create Teachers
        t_alice = Teacher(first_name="Alice", last_name="Teacher", school_id=s_a.id)
        t_ian = Teacher(first_name="Ian", last_name="Teacher", school_id=s_a.id)
        t_evan = Teacher(first_name="Evan", last_name="Teacher", school_id=s_b.id)
        t_nora = Teacher(first_name="Nora", last_name="Teacher", school_id=s_b.id)
        t_zack = Teacher(first_name="Zack", last_name="Teacher", school_id=s_c.id)
        db.session.add_all([t_alice, t_ian, t_evan, t_nora, t_zack])
        db.session.commit()

        # 3b. Create TeacherProgress entries (Required for Dashboard visibility)
        from models.teacher_progress import TeacherProgress

        current_vy = "2025-2026"
        current_ay = "2025-2026"

        tp_alice = TeacherProgress(
            academic_year=current_ay,
            virtual_year=current_vy,
            building=s_a.name,
            name="Alice Teacher",
            email="alice@test.com",
            teacher_id=t_alice.id,
            target_sessions=2,
        )
        tp_ian = TeacherProgress(
            academic_year=current_ay,
            virtual_year=current_vy,
            building=s_a.name,
            name="Ian Teacher",
            email="ian@test.com",
            teacher_id=t_ian.id,
            target_sessions=2,
        )
        tp_evan = TeacherProgress(
            academic_year=current_ay,
            virtual_year=current_vy,
            building=s_b.name,
            name="Evan Teacher",
            email="evan@test.com",
            teacher_id=t_evan.id,
            target_sessions=2,
        )
        tp_nora = TeacherProgress(
            academic_year=current_ay,
            virtual_year=current_vy,
            building=s_b.name,
            name="Nora Teacher",
            email="nora@test.com",
            teacher_id=t_nora.id,
            target_sessions=2,
        )

        # Zack in other district
        tp_zack = TeacherProgress(
            academic_year=current_ay,
            virtual_year=current_vy,
            building=s_c.name,
            name="Zack Teacher",
            email="zack@test.com",
            teacher_id=t_zack.id,
            target_sessions=2,
        )

        db.session.add_all([tp_alice, tp_ian, tp_evan, tp_nora, tp_zack])

        # Set district_name for non-tenant filtering (compute_teacher_progress_tracking fallback)
        for tp in [tp_alice, tp_ian, tp_evan, tp_nora]:
            tp.district_name = "Test District"
        tp_zack.district_name = "Other District"

        db.session.commit()

        # 4. Create Events
        # Alice: 1 Completed
        e_completed = Event(
            title="Completed Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now() - timedelta(days=5),
            districts=[d1],
            district_partner=d1.name,
        )

        # Ian: 1 Future
        e_future = Event(
            title="Future Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED,
            start_date=datetime.now() + timedelta(days=5),
            districts=[d1],
            district_partner=d1.name,
        )

        # Evan: 1 Completed + 1 Future
        e_evan_comp = Event(
            title="Evan Completed",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now() - timedelta(days=2),
            districts=[d1],
            district_partner=d1.name,
        )
        e_evan_fut = Event(
            title="Evan Future",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED,
            start_date=datetime.now() + timedelta(days=10),
            districts=[d1],
            district_partner=d1.name,
        )

        # Zack: 1 Completed (Different District)
        e_zack = Event(
            title="Zack Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            start_date=datetime.now() - timedelta(days=1),
            districts=[d2],
        )

        db.session.add_all([e_completed, e_future, e_evan_comp, e_evan_fut, e_zack])
        db.session.commit()

        # 5. Link Teachers
        # Alice -> Completed
        db.session.add(EventTeacher(event_id=e_completed.id, teacher_id=t_alice.id))
        # Ian -> Future
        db.session.add(EventTeacher(event_id=e_future.id, teacher_id=t_ian.id))
        # Evan -> Completed + Future
        db.session.add(EventTeacher(event_id=e_evan_comp.id, teacher_id=t_evan.id))
        db.session.add(EventTeacher(event_id=e_evan_fut.id, teacher_id=t_evan.id))
        # Zack -> Zack's event
        db.session.add(EventTeacher(event_id=e_zack.id, teacher_id=t_zack.id))

        db.session.commit()

        return {
            "district": d1,
            "other_district": d2,
            "teachers": {
                "alice": t_alice,
                "ian": t_ian,
                "evan": t_evan,
                "nora": t_nora,
                "zack": t_zack,
            },
        }


@pytest.fixture
def district_viewer_client(client, dashboard_data):
    """Returns a client authenticated as a District Viewer for 'Test District'."""
    with client.application.app_context():
        # Create user
        user = User(
            username="district_viewer",
            email="viewer@test.com",
            scope_type="district",
            allowed_districts='["Test District"]',
        )
        user.password_hash = generate_password_hash("password")
        db.session.add(user)
        db.session.commit()

    # Login
    client.post("/login", data={"username": "district_viewer", "password": "password"})
    return client


def test_district_dashboard_access_tc001(district_viewer_client):
    """TC-001: District Viewer login - Dashboard loads for own district."""
    # Based on usage.py `compute_virtual_session_data` and typical reporting routes
    response = district_viewer_client.get(
        "/virtual/usage", query_string={"district": "Test District"}
    )
    assert response.status_code == 200
    assert b"Test District" in response.data


def test_district_scoping_enforcement_tc002(district_viewer_client):
    """TC-002: District scoping via URL tampering - Access denied to other districts."""
    response = district_viewer_client.get(
        "/virtual/usage", query_string={"district": "Other District"}
    )

    # Verify sensitive data from other district is NOT shown
    # "Zack" is the teacher in Other District
    assert b"Zack" not in response.data


def test_teacher_status_logic_tc012_tc013_tc014(app):
    """
    TC-012, TC-013, TC-014: Verify progress status logic using TeacherProgress model.
    Logic:
    - Achieved: Completed >= Target
    - In Progress: (Completed + Planned) >= Target AND Completed < Target
    - Not Started: (Completed + Planned) < Target
    """
    from models.teacher_progress import TeacherProgress

    # Default target is 1
    # [TC-012] Status Labels
    # Case: Alice (1 Completed, 0 Planned) -> Achieved
    tp_alice = TeacherProgress(
        academic_year="2025-2026",
        virtual_year="2025-2026",
        building="School A",
        name="Alice",
        email="alice@test.com",
        target_sessions=1,
    )
    status_alice = tp_alice.get_progress_status(
        completed_sessions=1, planned_sessions=0
    )
    assert status_alice["status"] == "achieved"
    assert status_alice["status_text"] == "Goal Achieved"

    # Case: Ian (0 Completed, 1 Planned) -> In Progress
    tp_ian = TeacherProgress(
        academic_year="2025-2026",
        virtual_year="2025-2026",
        building="School A",
        name="Ian",
        email="ian@test.com",
        target_sessions=1,
    )
    status_ian = tp_ian.get_progress_status(completed_sessions=0, planned_sessions=1)
    assert status_ian["status"] == "in_progress"
    assert status_ian["status_text"] == "In Progress"

    # [TC-013] Edge Case: Completed + Future (Precedence)
    # Case: Evan (1 Completed, 1 Planned) -> Achieved (Completed takes precedence)
    tp_evan = TeacherProgress(
        academic_year="2025-2026",
        virtual_year="2025-2026",
        building="School B",
        name="Evan",
        email="evan@test.com",
        target_sessions=1,
    )
    status_evan = tp_evan.get_progress_status(completed_sessions=1, planned_sessions=1)
    assert status_evan["status"] == "achieved"

    # [TC-014] Not Started Definition
    # Case: Nora (0 Completed, 0 Planned) -> Not Started
    tp_nora = TeacherProgress(
        academic_year="2025-2026",
        virtual_year="2025-2026",
        building="School B",
        name="Nora",
        email="nora@test.com",
        target_sessions=1,
    )
    status_nora = tp_nora.get_progress_status(completed_sessions=0, planned_sessions=0)
    assert status_nora["status"] == "not_started"
    assert status_nora["status_text"] == "Needs Planning"


def test_school_drilldown_tc011(app, dashboard_data):
    """
    TC-011: School A drilldown - Shows Alice + Ian only.
    Verifies that compute_teacher_progress_tracking groups teachers by school correctly.
    """
    from routes.virtual.usage import compute_teacher_progress_tracking

    with app.app_context():
        # Call the logic function directly (bypassing route's KCK restriction)
        # Note: The function ignores district_name argument (potential bug?), so we can pass anything.
        school_data = compute_teacher_progress_tracking(
            district_name="Test District",
            virtual_year="2025-2026",
            date_from=datetime(2025, 8, 1),
            date_to=datetime(2026, 7, 31),
        )

        # Verify School A contains Alice and Ian
        assert "School A" in school_data
        school_a_data = school_data["School A"]
        # Access 'teachers' key which holds list of dicts with 'name' property
        school_a_teachers = [t["name"] for t in school_a_data["teachers"]]
        assert "Alice Teacher" in school_a_teachers
        assert "Ian Teacher" in school_a_teachers
        assert "Evan Teacher" not in school_a_teachers
        assert len(school_a_data["teachers"]) == 2

        # Verify School B contains Evan and Nora
        assert "School B" in school_data
        school_b_data = school_data["School B"]
        school_b_teachers = [t["name"] for t in school_b_data["teachers"]]
        assert "Evan Teacher" in school_b_teachers
        assert "Nora Teacher" in school_b_teachers
        assert len(school_b_data["teachers"]) == 2


def test_compute_teacher_progress_filters_by_attendance(app):
    """
    Verify compute_teacher_progress only counts EventTeacher records with
    status='attended' (not 'registered' or 'no_show') as completed sessions.
    """
    from models.teacher_progress import TeacherProgress
    from models.tenant import Tenant
    from routes.district.tenant_teacher_usage import compute_teacher_progress

    with app.app_context():
        # Setup: district, tenant, school, teachers
        d = District(name="Attendance Test District")
        db.session.add(d)
        db.session.commit()

        tenant = Tenant(
            name="Attendance Tenant", district_id=d.id, slug="attendance-tenant"
        )
        db.session.add(tenant)
        db.session.commit()

        s = School(id="ATT_SCHOOL_01", name="Attendance School", district_id=d.id)
        db.session.add(s)
        db.session.commit()

        # Three teachers
        t_attended = Teacher(first_name="Attended", last_name="Teacher", school_id=s.id)
        t_registered = Teacher(
            first_name="Registered", last_name="Teacher", school_id=s.id
        )
        t_noshow = Teacher(first_name="NoShow", last_name="Teacher", school_id=s.id)
        db.session.add_all([t_attended, t_registered, t_noshow])
        db.session.commit()

        # TeacherProgress entries linked to tenant
        tp_attended = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="Attended Teacher",
            email="attended@test.com",
            teacher_id=t_attended.id,
            target_sessions=1,
        )
        tp_attended.tenant_id = tenant.id
        tp_attended.is_active = True

        tp_registered = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="Registered Teacher",
            email="registered@test.com",
            teacher_id=t_registered.id,
            target_sessions=1,
        )
        tp_registered.tenant_id = tenant.id
        tp_registered.is_active = True

        tp_noshow = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="NoShow Teacher",
            email="noshow@test.com",
            teacher_id=t_noshow.id,
            target_sessions=1,
        )
        tp_noshow.tenant_id = tenant.id
        tp_noshow.is_active = True
        db.session.add_all([tp_attended, tp_registered, tp_noshow])
        db.session.commit()

        # One completed event linked to all three teachers with different statuses
        from models.event import EventFormat

        e = Event(
            title="Attendance Filter Test",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now() - timedelta(days=3),
            districts=[d],
            district_partner=d.name,
        )
        db.session.add(e)
        db.session.commit()

        # Link teachers with different statuses
        db.session.add(
            EventTeacher(event_id=e.id, teacher_id=t_attended.id, status="attended")
        )
        db.session.add(
            EventTeacher(event_id=e.id, teacher_id=t_registered.id, status="registered")
        )
        db.session.add(
            EventTeacher(event_id=e.id, teacher_id=t_noshow.id, status="no_show")
        )
        db.session.commit()

        # Call compute_teacher_progress
        result = compute_teacher_progress(tenant.id, "2025-2026")

        # Flatten all teachers from the result
        all_teachers = []
        for building_data in result.values():
            all_teachers.extend(building_data.get("teachers", []))

        # Find each teacher's completed count
        attended_info = next(
            (t for t in all_teachers if t["name"] == "Attended Teacher"), None
        )
        registered_info = next(
            (t for t in all_teachers if t["name"] == "Registered Teacher"), None
        )
        noshow_info = next(
            (t for t in all_teachers if t["name"] == "NoShow Teacher"), None
        )

        # Only "Attended Teacher" should have completed_sessions = 1
        assert attended_info is not None
        assert attended_info["completed_sessions"] == 1, (
            f"Teacher with status='attended' should have 1 completed session, "
            f"got {attended_info['completed_sessions']}"
        )

        # "Registered Teacher" should have 0 completed sessions
        assert registered_info is not None
        assert registered_info["completed_sessions"] == 0, (
            f"Teacher with status='registered' should have 0 completed sessions, "
            f"got {registered_info['completed_sessions']}"
        )

        # "NoShow Teacher" should have 0 completed sessions
        assert noshow_info is not None
        assert noshow_info["completed_sessions"] == 0, (
            f"Teacher with status='no_show' should have 0 completed sessions, "
            f"got {noshow_info['completed_sessions']}"
        )


def test_compute_teacher_progress_null_teacher_id_backfill(app):
    """
    Verify compute_teacher_progress backfills null teacher_id on
    TeacherProgress and then correctly counts the teacher's sessions.

    Scenario: A TeacherProgress record exists with teacher_id=None, but a
    matching Teacher record exists in the DB with an EventTeacher link to a
    completed event.  After backfill, the session should be counted.
    """
    from models.teacher_progress import TeacherProgress
    from models.tenant import Tenant
    from routes.district.tenant_teacher_usage import compute_teacher_progress

    with app.app_context():
        # Setup: district, tenant, school, teacher
        d = District(name="Backfill Test District")
        db.session.add(d)
        db.session.commit()

        tenant = Tenant(
            name="Backfill Tenant", district_id=d.id, slug="backfill-tenant"
        )
        db.session.add(tenant)
        db.session.commit()

        s = School(id="BF_SCHOOL_01", name="Backfill School", district_id=d.id)
        db.session.add(s)
        db.session.commit()

        # Teacher record exists in DB
        t = Teacher(
            first_name="Elizabeth",
            last_name="Arteberry",
            email="elizabeth.arteberry@test.com",
            school_id=s.id,
        )
        db.session.add(t)
        db.session.commit()

        # TeacherProgress with teacher_id=None (the bug condition)
        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="Elizabeth Arteberry",
            email="elizabeth.arteberry@test.com",
            teacher_id=None,  # <-- null, the bug
            target_sessions=1,
        )
        tp.tenant_id = tenant.id
        tp.is_active = True
        db.session.add(tp)
        db.session.commit()

        # Verify teacher_id is None before calling compute
        assert tp.teacher_id is None

        # Create a completed event linked to the Teacher via EventTeacher
        from models.event import EventFormat

        e = Event(
            title="Backfill Test Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now() - timedelta(days=3),
            districts=[d],
            district_partner=d.name,
        )
        db.session.add(e)
        db.session.commit()

        db.session.add(EventTeacher(event_id=e.id, teacher_id=t.id, status="attended"))
        db.session.commit()

        # Call compute_teacher_progress — should backfill and count
        result = compute_teacher_progress(tenant.id, "2025-2026")

        # teacher_id should now be set
        db.session.refresh(tp)
        assert (
            tp.teacher_id == t.id
        ), f"Backfill should have set teacher_id to {t.id}, got {tp.teacher_id}"

        # The teacher should have 1 completed session
        all_teachers = []
        for building_data in result.values():
            all_teachers.extend(building_data.get("teachers", []))

        teacher_info = next(
            (t for t in all_teachers if t["name"] == "Elizabeth Arteberry"), None
        )
        assert teacher_info is not None, "Teacher should appear in results"
        assert teacher_info["completed_sessions"] == 1, (
            f"After backfill, teacher should have 1 completed session, "
            f"got {teacher_info['completed_sessions']}"
        )
        assert teacher_info["goal_status_text"] == "Goal Achieved"
