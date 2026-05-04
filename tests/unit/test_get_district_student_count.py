from unittest.mock import MagicMock, patch

from models.event import EventType
from routes.reports.common import get_district_student_count_for_event


def test_virtual_session_teachers_count():
    event = MagicMock()
    event.type = EventType.VIRTUAL_SESSION

    teacher1 = MagicMock()
    teacher1.teacher.school_id = 1

    teacher2 = MagicMock()
    teacher2.teacher.school_id = 2

    teacher3 = MagicMock()
    teacher3.teacher.school_id = 3

    event.teacher_registrations = [teacher1, teacher2, teacher3]

    with patch("routes.reports.common.School") as MockSchool:
        # First 2 schools match district 100, 3rd doesn't
        mock_school_1 = MagicMock(district_id=100)
        mock_school_2 = MagicMock(district_id=100)
        mock_school_3 = MagicMock(district_id=200)

        MockSchool.query.filter_by.side_effect = [
            MagicMock(first=lambda: mock_school_1),
            MagicMock(first=lambda: mock_school_2),
            MagicMock(first=lambda: mock_school_3),
        ]

        result = get_district_student_count_for_event(event, 100)
        assert result == 50  # 2 teachers in district * 25


def test_in_person_with_attendance_detail_not_shared():
    event = MagicMock()
    event.type = EventType.IN_PERSON
    event.districts = [MagicMock()]  # Only 1 district
    event.district_partner = "Grandview"

    event.attendance_detail.total_students = 80

    result = get_district_student_count_for_event(event, 100)
    assert result == 80


@patch("routes.reports.common.db.session.query")
def test_in_person_without_attendance_detail(mock_query):
    event = MagicMock()
    event.type = EventType.IN_PERSON
    event.districts = [MagicMock()]
    event.district_partner = "Grandview"

    event.attendance_detail = None  # No manual attendance

    mock_count = (
        mock_query.return_value.join.return_value.join.return_value.filter.return_value.count
    )
    mock_count.return_value = 5

    result = get_district_student_count_for_event(event, 100)
    assert result == 5


@patch("routes.reports.common.db.session.query")
def test_in_person_with_attendance_detail_but_shared(mock_query):
    event = MagicMock()
    event.type = EventType.IN_PERSON
    event.districts = [MagicMock(), MagicMock()]  # 2 districts -> shared!
    event.district_partner = "Grandview, Hickman"

    event.attendance_detail.total_students = 80  # Should be ignored because it's shared

    mock_count = (
        mock_query.return_value.join.return_value.join.return_value.filter.return_value.count
    )
    mock_count.return_value = 12  # Fallback count

    result = get_district_student_count_for_event(event, 100)
    assert result == 12
