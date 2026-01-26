from datetime import date, datetime

import pytest

from app import db
from models import District, School, Teacher, TeacherProgress, TeacherProgressArchive
from routes.virtual.usage import (
    get_current_virtual_year,
    get_semester_dates,
    snapshot_semester_progress,
)

# --- Helper Tests ---


def test_get_semester_dates():
    # Test Fall sem dates
    start, end = get_semester_dates("2025-2026", "Fall")
    assert start == datetime(2025, 7, 1, 0, 0, 0)
    assert end == datetime(2025, 12, 31, 23, 59, 59)

    # Test Spring sem dates
    start, end = get_semester_dates("2025-2026", "Spring")
    assert start == datetime(2026, 1, 1, 0, 0, 0)
    assert end == datetime(2026, 6, 30, 23, 59, 59)


# --- Integration Tests ---


@pytest.fixture
def kckps_district(client):
    district = District(name="Kansas City Kansas Public Schools")
    db.session.add(district)
    db.session.commit()
    return district


@pytest.fixture
def sample_teacher_progress(kckps_district):
    from models.contact import ContactTypeEnum, Email

    # Create school/teacher
    school = School(
        id="TESTSCHOOL001", name="Test School", district_id=kckps_district.id
    )
    db.session.add(school)

    teacher = Teacher(first_name="Test", last_name="Teacher")
    teacher.school_obj = school
    db.session.add(teacher)

    # Add email
    email = Email(email="test@kck.edu", type=ContactTypeEnum.professional, primary=True)
    teacher.emails.append(email)
    db.session.add(email)

    db.session.commit()

    # Create progress record
    tp = TeacherProgress(
        teacher_id=teacher.id,
        academic_year="2025-2026",
        virtual_year="2025-2026",
        name="Test Teacher",
        email="test@kck.edu",
        building="Test School",
        target_sessions=10,
    )
    db.session.add(tp)
    db.session.commit()
    return tp


def test_snapshot_semester_progress(client, kckps_district, sample_teacher_progress):
    # Snapshot Fall 2025
    virtual_year = "2025-2026"
    semester_name = "Fall 2025"
    date_from = datetime(2025, 7, 1)
    date_to = datetime(2025, 12, 31)
    pass

    # Create Events to generate stats
    from models.event import Event, EventStatus, EventTeacher, EventType

    date_event = datetime(2025, 10, 15)  # In Fall

    event = Event(
        title="Test Session",
        type=EventType.VIRTUAL_SESSION,
        start_date=date_event,
        status=EventStatus.COMPLETED,
    )
    event.districts.append(kckps_district)
    db.session.add(event)

    # Link teacher
    teacher = Teacher.query.get(sample_teacher_progress.teacher_id)
    et = EventTeacher(event=event, teacher=teacher, status="Attended")
    db.session.add(et)
    db.session.commit()

    # Now run snapshot
    virtual_year = "2025-2026"
    semester_name = "Fall 2025"
    date_from = datetime(2025, 7, 1)
    date_to = datetime(2025, 12, 31)

    success, count = snapshot_semester_progress(
        kckps_district.name, virtual_year, semester_name, date_from, date_to
    )

    assert success is True
    assert count == 1

    # Verify Archive
    archive = TeacherProgressArchive.query.filter_by(
        semester_name=semester_name
    ).first()
    assert archive is not None
    assert archive.teacher_progress_id == sample_teacher_progress.id
    assert archive.completed_sessions == 1  # Calculated from event
    assert archive.virtual_year == virtual_year


def test_snapshot_idempotency(client, kckps_district, sample_teacher_progress):
    # Run once
    virtual_year = "2025-2026"
    semester_name = "Fall 2025"
    date_from = datetime(2025, 7, 1)
    date_to = datetime(2025, 12, 31)

    snapshot_semester_progress(
        kckps_district.name, virtual_year, semester_name, date_from, date_to
    )

    # Run again
    success, count = snapshot_semester_progress(
        kckps_district.name, virtual_year, semester_name, date_from, date_to
    )

    assert success is True
    assert count == 0  # Should count 0 new records

    # Verify only 1 record total
    archives = TeacherProgressArchive.query.filter_by(semester_name=semester_name).all()
    assert len(archives) == 1


def test_manual_archive_route(client, test_admin_headers, kckps_district):
    # Use admin headers
    resp = client.post(
        f"/virtual/usage/district/{kckps_district.name}/teacher-progress/manual-archive",
        headers=test_admin_headers,
        follow_redirects=False,
    )

    from urllib.parse import unquote

    assert resp.status_code == 302
    location = unquote(resp.headers["Location"])
    # Check for core components of the URL rather than exact prefix, to be resilient to Blueprint prefix changes
    assert f"/district/{kckps_district.name}/teacher-progress" in location
