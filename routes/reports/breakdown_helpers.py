import logging

from sqlalchemy import or_

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventStudentParticipation, EventType
from models.school_model import School
from models.student import Student
from models.volunteer import Volunteer

# Local imports to avoid circular dependency
from routes.reports.common import (
    build_district_event_conditions,
    get_district_student_count_for_event,
    get_school_year_date_range,
)

logger = logging.getLogger(__name__)


def calculate_program_breakdown(
    district_id,
    school_year,
    host_filter="all",
    preloaded_events=None,
    preloaded_students=None,
    preloaded_hs_students=None,
    preloaded_volunteers=None,
    preloaded_teachers=None,
):
    """
    Calculate detailed program breakdown metrics for a district.
    """
    start_date, end_date = get_school_year_date_range(school_year)

    # Get district and schools
    district = District.query.filter_by(id=district_id).first()
    if not district:
        return {}

    schools = School.query.filter_by(district_id=district_id).all()
    school_ids = [school.id for school in schools]

    if preloaded_events is not None:
        base_events = preloaded_events
    else:
        # Build query conditions via shared helper (TD-063-X)
        query_conditions = build_district_event_conditions(district, schools=schools)

        # Base query for all completed events in date range
        base_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            db.or_(*query_conditions),
        )

        # Apply host filter if specified
        if host_filter == "prepkc":
            base_query = base_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        base_events = base_query.all()

    # Initialize breakdown structure
    breakdown = {
        "in_person_students": {"total": 0, "unique": 0},
        "in_person_volunteers": {"total": 0, "unique": 0},
        "in_person_events_count": 0,
        "career_jumping_students": {"total": 0, "unique": 0},
        "career_speakers_students": {"total": 0, "unique": 0},
        "career_college_fair_hs_students": {"total": 0, "unique": 0},
        "healthstart_students": {"total": 0, "unique": 0},
        "bfi_students": {"total": 0, "unique": 0},
        "dia_students": {"total": 0, "unique": 0},
        "sla_students": {"total": 0, "unique": 0},
        "client_connected_students": {"total": 0, "unique": 0},
        "p2t_students": {"total": 0, "unique": 0},
        "p2gd_students": {"total": 0, "unique": 0},
        "math_relays_count": 0,
        "virtual_sessions": {
            "teachers_engaged": {"total": 0, "unique": 0},
            "students_participated": {
                "total": 0,
                "unique": None,
            },  # None = not trackable
            "session_count": 0,
        },
    }

    # Track unique IDs
    unique_in_person_students = set()
    unique_in_person_volunteers = set()
    unique_career_jumping_students = set()
    unique_career_speakers_students = set()
    unique_career_fair_hs_students = set()
    unique_healthstart_students = set()
    unique_bfi_students = set()
    unique_dia_students = set()
    unique_sla_students = set()
    unique_client_connected_students = set()
    unique_p2t_students = set()
    unique_p2gd_students = set()
    unique_virtual_teachers = set()

    # 1. In-person events (exclude virtual_session and connector_session)
    if preloaded_events is not None:
        in_person_events = [
            e
            for e in base_events
            if e.type not in [EventType.VIRTUAL_SESSION, EventType.CONNECTOR_SESSION]
        ]
    else:
        in_person_events_query = base_query.filter(
            ~Event.type.in_([EventType.VIRTUAL_SESSION, EventType.CONNECTOR_SESSION])
        )
        in_person_events = in_person_events_query.all()

    for event in in_person_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["in_person_students"]["total"] += len(student_ids)
            unique_in_person_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["in_person_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_in_person_students.update(event_student_ids)

        if preloaded_volunteers is not None:
            vol_entries = preloaded_volunteers.get(event.id, [])
            breakdown["in_person_volunteers"]["total"] += len(vol_entries)
            for vol_id, _ in vol_entries:
                unique_in_person_volunteers.add(vol_id)
        else:
            volunteer_participations = [
                p
                for p in event.volunteer_participations
                if p.status in ["Attended", "Completed", "Successfully Completed"]
            ]
            breakdown["in_person_volunteers"]["total"] += len(volunteer_participations)
            for p in volunteer_participations:
                unique_in_person_volunteers.add(p.volunteer_id)

    breakdown["in_person_students"]["unique"] = len(unique_in_person_students)
    breakdown["in_person_volunteers"]["unique"] = len(unique_in_person_volunteers)
    breakdown["in_person_events_count"] = len(in_person_events)

    # 2. Career Jumping events
    if preloaded_events is not None:
        career_jumping_events = [
            e for e in base_events if e.type == EventType.CAREER_JUMPING
        ]
    else:
        career_jumping_events = base_query.filter(
            Event.type == EventType.CAREER_JUMPING
        ).all()

    for event in career_jumping_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["career_jumping_students"]["total"] += len(student_ids)
            unique_career_jumping_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["career_jumping_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_career_jumping_students.update(event_student_ids)

    breakdown["career_jumping_students"]["unique"] = len(unique_career_jumping_students)

    # 3. Career Speakers events
    if preloaded_events is not None:
        career_speakers_events = [
            e for e in base_events if e.type == EventType.CAREER_SPEAKER
        ]
    else:
        career_speakers_events = base_query.filter(
            Event.type == EventType.CAREER_SPEAKER
        ).all()

    for event in career_speakers_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["career_speakers_students"]["total"] += len(student_ids)
            unique_career_speakers_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["career_speakers_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_career_speakers_students.update(event_student_ids)

    breakdown["career_speakers_students"]["unique"] = len(
        unique_career_speakers_students
    )

    # 4. Career/College Fair events (high school students only)
    if preloaded_events is not None:
        career_fair_events = [
            e
            for e in base_events
            if e.type in [EventType.CAREER_FAIR, EventType.COLLEGE_APPLICATION_FAIR]
        ]
    else:
        career_fair_events = base_query.filter(
            Event.type.in_([EventType.CAREER_FAIR, EventType.COLLEGE_APPLICATION_FAIR])
        ).all()

    for event in career_fair_events:
        if preloaded_hs_students is not None:
            hs_student_ids = preloaded_hs_students.get(event.id, set())
            breakdown["career_college_fair_hs_students"]["total"] += len(hs_student_ids)
            unique_career_fair_hs_students.update(hs_student_ids)
        else:
            district_hs_student_participations = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                    School.level == "High",
                )
                .all()
            )

            hs_student_total_count = len(district_hs_student_participations)
            breakdown["career_college_fair_hs_students"][
                "total"
            ] += hs_student_total_count

            event_hs_student_ids = {
                student_id[0] for student_id in district_hs_student_participations
            }
            unique_career_fair_hs_students.update(event_hs_student_ids)

    breakdown["career_college_fair_hs_students"]["unique"] = len(
        unique_career_fair_hs_students
    )

    # 5. Health Start events
    if preloaded_events is not None:
        healthstart_events = [e for e in base_events if e.type == EventType.HEALTHSTART]
    else:
        healthstart_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.HEALTHSTART,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            healthstart_events_query = healthstart_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        healthstart_events = healthstart_events_query.all()

    for event in healthstart_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["healthstart_students"]["total"] += len(student_ids)
            unique_healthstart_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["healthstart_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_healthstart_students.update(event_student_ids)

    breakdown["healthstart_students"]["unique"] = len(unique_healthstart_students)

    # 6. BFI events
    if preloaded_events is not None:
        bfi_events = [e for e in base_events if e.type == EventType.BFI]
    else:
        bfi_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.BFI,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            bfi_events_query = bfi_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        bfi_events = bfi_events_query.all()

    for event in bfi_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["bfi_students"]["total"] += len(student_ids)
            unique_bfi_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["bfi_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_bfi_students.update(event_student_ids)

    breakdown["bfi_students"]["unique"] = len(unique_bfi_students)

    # 7. Virtual Sessions (Pathful only — VIRTUAL_SESSION)
    if preloaded_events is not None:
        virtual_events = [e for e in base_events if e.type == EventType.VIRTUAL_SESSION]
    else:
        virtual_events = base_query.filter(
            Event.type == EventType.VIRTUAL_SESSION
        ).all()

    breakdown["virtual_sessions"]["session_count"] = len(virtual_events)

    for event in virtual_events:
        if preloaded_teachers is not None:
            teacher_entries = preloaded_teachers.get(event.id, [])
            # In preloaded_teachers, all entries have already been filtered for attendance/registration
            confirmed_teachers = teacher_entries
            breakdown["virtual_sessions"]["teachers_engaged"]["total"] += len(
                confirmed_teachers
            )
            for t_id, _ in confirmed_teachers:
                unique_virtual_teachers.add(t_id)
            breakdown["virtual_sessions"]["students_participated"]["total"] += (
                len(confirmed_teachers) * 25
            )
        else:
            # Get confirmed teachers (attendance_confirmed_at is not None)
            confirmed_teacher_regs = [
                reg
                for reg in event.teacher_registrations
                if reg.attendance_confirmed_at is not None
            ]

            # Filter by district: only count teachers from this district's schools
            district_confirmed_teachers = []
            for reg in confirmed_teacher_regs:
                teacher = reg.teacher
                if teacher.school_id and teacher.school_id in school_ids:
                    district_confirmed_teachers.append(reg)
                    unique_virtual_teachers.add(reg.teacher_id)

            breakdown["virtual_sessions"]["teachers_engaged"]["total"] += len(
                district_confirmed_teachers
            )

            # Estimate students: confirmed teachers × 25
            breakdown["virtual_sessions"]["students_participated"]["total"] += (
                len(district_confirmed_teachers) * 25
            )

    breakdown["virtual_sessions"]["teachers_engaged"]["unique"] = len(
        unique_virtual_teachers
    )

    # 8. DIA events
    if preloaded_events is not None:
        dia_events = [
            e
            for e in base_events
            if e.type in [EventType.DIA, EventType.DIA_CLASSROOM_SPEAKER]
        ]
    else:
        dia_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type.in_([EventType.DIA, EventType.DIA_CLASSROOM_SPEAKER]),
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            dia_events_query = dia_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        dia_events = dia_events_query.all()

    for event in dia_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["dia_students"]["total"] += len(student_ids)
            unique_dia_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["dia_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_dia_students.update(event_student_ids)

    breakdown["dia_students"]["unique"] = len(unique_dia_students)

    # 9. SLA events
    if preloaded_events is not None:
        sla_events = [e for e in base_events if e.type == EventType.SLA]
    else:
        sla_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.SLA,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            sla_events_query = sla_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        sla_events = sla_events_query.all()

    for event in sla_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["sla_students"]["total"] += len(student_ids)
            unique_sla_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["sla_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_sla_students.update(event_student_ids)

    breakdown["sla_students"]["unique"] = len(unique_sla_students)

    # 10. Client Connected Project events
    if preloaded_events is not None:
        ccp_events = [
            e for e in base_events if e.type == EventType.CLIENT_CONNECTED_PROJECT
        ]
    else:
        ccp_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.CLIENT_CONNECTED_PROJECT,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            ccp_events_query = ccp_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        ccp_events = ccp_events_query.all()

    for event in ccp_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["client_connected_students"]["total"] += len(student_ids)
            unique_client_connected_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["client_connected_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_client_connected_students.update(event_student_ids)

    breakdown["client_connected_students"]["unique"] = len(
        unique_client_connected_students
    )

    # 11. P2T events
    if preloaded_events is not None:
        p2t_events = [e for e in base_events if e.type == EventType.P2T]
    else:
        p2t_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.P2T,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            p2t_events_query = p2t_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        p2t_events = p2t_events_query.all()

    for event in p2t_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["p2t_students"]["total"] += len(student_ids)
            unique_p2t_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["p2t_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_p2t_students.update(event_student_ids)

    breakdown["p2t_students"]["unique"] = len(unique_p2t_students)

    # 12. P2GD events
    if preloaded_events is not None:
        p2gd_events = [e for e in base_events if e.type == EventType.P2GD]
    else:
        p2gd_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.P2GD,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            p2gd_events_query = p2gd_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        p2gd_events = p2gd_events_query.all()

    for event in p2gd_events:
        if preloaded_students is not None:
            student_ids = preloaded_students.get(event.id, set())
            breakdown["p2gd_students"]["total"] += len(student_ids)
            unique_p2gd_students.update(student_ids)
        else:
            student_count = get_district_student_count_for_event(event, district_id)
            breakdown["p2gd_students"]["total"] += student_count

            district_student_ids = (
                db.session.query(EventStudentParticipation.student_id)
                .join(Student, EventStudentParticipation.student_id == Student.id)
                .join(School, Student.school_id == School.id)
                .filter(
                    EventStudentParticipation.event_id == event.id,
                    EventStudentParticipation.status == "Attended",
                    School.district_id == district_id,
                )
                .all()
            )
            event_student_ids = {student_id[0] for student_id in district_student_ids}
            unique_p2gd_students.update(event_student_ids)

    breakdown["p2gd_students"]["unique"] = len(unique_p2gd_students)

    # 13. Math Relays events (Count only)
    if preloaded_events is not None:
        math_relays_events = [e for e in base_events if e.type == EventType.MATH_RELAYS]
    else:
        math_relays_events_query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date.between(start_date, end_date),
            Event.type == EventType.MATH_RELAYS,
            db.or_(*query_conditions),
        )
        if host_filter == "prepkc":
            math_relays_events_query = math_relays_events_query.filter(
                db.or_(
                    Event.session_host.ilike("%PREPKC%"),
                    Event.session_host.ilike("%prepkc%"),
                    Event.session_host.ilike("%PrepKC%"),
                )
            )
        math_relays_events = math_relays_events_query.all()

    breakdown["math_relays_count"] = len(math_relays_events)

    breakdown["_unique_sets"] = {
        "in_person_students": list(unique_in_person_students),
        "in_person_volunteers": list(unique_in_person_volunteers),
        "career_jumping_students": list(unique_career_jumping_students),
        "career_speakers_students": list(unique_career_speakers_students),
        "career_college_fair_hs_students": list(unique_career_fair_hs_students),
        "healthstart_students": list(unique_healthstart_students),
        "bfi_students": list(unique_bfi_students),
        "dia_students": list(unique_dia_students),
        "sla_students": list(unique_sla_students),
        "client_connected_students": list(unique_client_connected_students),
        "p2t_students": list(unique_p2t_students),
        "p2gd_students": list(unique_p2gd_students),
        "virtual_teachers": list(unique_virtual_teachers),
    }

    return breakdown
