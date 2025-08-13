from datetime import datetime

import pytest

from models import db
from models.attendance import EventAttendanceDetail
from models.event import Event


@pytest.fixture
def test_event(app):
    with app.app_context():
        event = Event(
            title="Attendance Test Event",
            type="IN_PERSON",
            start_date=datetime.now(),
            status="Confirmed",
            volunteers_needed=1,
        )
        db.session.add(event)
        db.session.commit()
        yield event
        db.session.delete(event)
        db.session.commit()


def test_create_attendance_detail(app, test_event):
    """Test creating an attendance detail record."""
    with app.app_context():
        attendance = EventAttendanceDetail(
            event_id=test_event.id,
            total_students=25,
            num_classrooms=3,
            rotations=2,
            is_stem=True,
            pathway="STEM",
        )
        db.session.add(attendance)
        db.session.commit()

        assert attendance.event_id == test_event.id
        assert attendance.total_students == 25
        assert attendance.num_classrooms == 3
        assert attendance.rotations == 2
        assert attendance.is_stem == True
        assert attendance.pathway == "STEM"


def test_calculate_students_per_volunteer(app, test_event):
    """Test the calculate_students_per_volunteer method."""
    with app.app_context():
        # Test case 1: Normal calculation
        attendance = EventAttendanceDetail(
            event_id=test_event.id, total_students=30, num_classrooms=3, rotations=2
        )
        result = attendance.calculate_students_per_volunteer()
        assert result == 20  # (30 / 3) * 2 = 10 * 2 = 20

        # Test case 2: Decimal result should be rounded down
        attendance.total_students = 25
        result = attendance.calculate_students_per_volunteer()
        assert result == 16  # (25 / 3) * 2 = 8.333... * 2 = 16.666... -> 16

        # Test case 3: Missing data should return None
        attendance.total_students = None
        result = attendance.calculate_students_per_volunteer()
        assert result is None

        # Test case 4: Zero values should return None
        attendance.total_students = 30
        attendance.num_classrooms = 0
        result = attendance.calculate_students_per_volunteer()
        assert result is None

        # Test case 5: Zero rotations should return None
        attendance.num_classrooms = 3
        attendance.rotations = 0
        result = attendance.calculate_students_per_volunteer()
        assert result is None


def test_update_students_per_volunteer(app, test_event):
    """Test the update_students_per_volunteer method."""
    with app.app_context():
        attendance = EventAttendanceDetail(
            event_id=test_event.id, total_students=30, num_classrooms=3, rotations=2
        )

        # Initially should be None
        assert attendance.students_per_volunteer is None

        # Update should calculate and set the value
        result = attendance.update_students_per_volunteer()
        assert result == 20  # (30 / 3) * 2 = 20
        assert attendance.students_per_volunteer == 20


def test_unique_event_id_constraint(app, test_event):
    with app.app_context():
        detail1 = EventAttendanceDetail(event_id=test_event.id)
        db.session.add(detail1)
        db.session.commit()
        # Try to add another detail for the same event_id
        detail2 = EventAttendanceDetail(event_id=test_event.id)
        db.session.add(detail2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
        db.session.delete(detail1)
        db.session.commit()


def test_nullable_fields(app, test_event):
    with app.app_context():
        detail = EventAttendanceDetail(event_id=test_event.id)
        db.session.add(detail)
        db.session.commit()
        # All optional fields should be None or default
        assert detail.num_classrooms is None
        assert detail.students_per_volunteer is None
        assert detail.total_students is None
        assert detail.attendance_in_sf is False
        assert detail.pathway is None
        assert detail.groups_rotations is None
        assert detail.is_stem is False
        assert detail.attendance_link is None
        db.session.delete(detail)
        db.session.commit()
