import pytest
from models.attendance import EventAttendanceDetail
from models.event import Event
from models import db
from datetime import datetime

@pytest.fixture
def test_event(app):
    with app.app_context():
        event = Event(
            title='Attendance Test Event',
            type='IN_PERSON',
            start_date=datetime.now(),
            status='Confirmed',
            volunteers_needed=1
        )
        db.session.add(event)
        db.session.commit()
        yield event
        db.session.delete(event)
        db.session.commit()

def test_create_attendance_detail(app, test_event):
    with app.app_context():
        detail = EventAttendanceDetail(
            event_id=test_event.id,
            num_classrooms=3,
            students_per_volunteer=10,
            total_students=30,
            attendance_in_sf=True,
            pathway='STEM',
            groups_rotations='Group A',
            is_stem=True,
            attendance_link='http://example.com/attendance'
        )
        db.session.add(detail)
        db.session.commit()
        assert detail.id is not None
        assert detail.event_id == test_event.id
        assert detail.num_classrooms == 3
        assert detail.students_per_volunteer == 10
        assert detail.total_students == 30
        assert detail.attendance_in_sf is True
        assert detail.pathway == 'STEM'
        assert detail.groups_rotations == 'Group A'
        assert detail.is_stem is True
        assert detail.attendance_link == 'http://example.com/attendance'
        # Relationship
        assert detail.event.id == test_event.id
        # __repr__ and __str__
        assert str(detail) == f'AttendanceDetail for Event {test_event.id}'
        assert f'<EventAttendanceDetail event_id={test_event.id}' in repr(detail)
        # Cleanup
        db.session.delete(detail)
        db.session.commit()

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