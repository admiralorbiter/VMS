"""
Integration tests for the Presenter No-Show Session Credit feature.

Covers:
- GET /session-credit page loads with a valid event (by pathful_id and event_id)
- POST /session-credit/bulk grants attended status to all selected teachers
- POST /session-credit/bulk skips teachers that already have an active override
- POST /session-credit/bulk requires a reason (returns 400 if empty)
- POST /session-credit/bulk creates AuditLog entries for each grant
"""

from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from models import db
from models.attendance_override import AttendanceOverride, OverrideAction
from models.audit_log import AuditLog
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from models.tenant import Tenant
from models.user import User


@pytest.fixture
def session_credit_data(app):
    """
    Setup test data for session credit tests.

    Creates:
    - District, Tenant, School, 3 Teachers, 3 TeacherProgress records
    - 1 completed virtual session that all 3 teachers are registered for
    - Admin user
    """
    with app.app_context():
        d = District(name="Credit Test District")
        db.session.add(d)
        db.session.commit()

        tenant = Tenant(name="Credit Tenant", district_id=d.id, slug="credit-tenant")
        db.session.add(tenant)
        db.session.commit()

        school = School(id="CR_SCHOOL_01", name="Credit Test School", district_id=d.id)
        db.session.add(school)
        db.session.commit()

        teachers = []
        tp_records = []
        for i, name in enumerate(["Alice", "Bob", "Carol"]):
            t = Teacher(first_name=name, last_name="Test", school_id=school.id)
            db.session.add(t)
            db.session.commit()

            tp = TeacherProgress(
                academic_year="2025-2026",
                virtual_year="2025-2026",
                building=school.name,
                name=f"{name} Test",
                email=f"{name.lower()}@test.com",
                teacher_id=t.id,
                target_sessions=2,
            )
            tp.tenant_id = tenant.id
            tp.is_active = True
            db.session.add(tp)
            db.session.commit()

            teachers.append(t)
            tp_records.append(tp)

        # Completed virtual session — presenter no-showed
        event = Event(
            title="Shakespeare No-Show Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now() - timedelta(days=1),
            district_partner=d.name,
            pathful_session_id="999001",
        )
        db.session.add(event)
        db.session.commit()

        # All 3 teachers registered (no_show because presenter didn't arrive)
        for t in teachers:
            et = EventTeacher(event_id=event.id, teacher_id=t.id, status="no_show")
            db.session.add(et)
        db.session.commit()

        # Admin user
        admin = User(
            username="credit_admin",
            email="admin@credit.test",
            is_admin=True,
        )
        admin.password_hash = generate_password_hash("pass")
        db.session.add(admin)
        db.session.commit()

        yield {
            "district": d,
            "tenant": tenant,
            "school": school,
            "teachers": teachers,
            "teacher_progress": tp_records,
            "event": event,
            "admin": admin,
        }


def _login(client, admin):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True


class TestSessionCreditPage:
    """Tests for GET /district/teacher-usage/session-credit."""

    def test_page_loads_with_pathful_id(self, client, app, session_credit_data):
        """Page should load and show the session when given a Pathful session ID."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tenant_id = session_credit_data["tenant"].id

        resp = client.get(
            f"/district/teacher-usage/session-credit?pathful_id={event.pathful_session_id}&tenant_id={tenant_id}"
        )
        assert resp.status_code == 200
        assert b"Shakespeare No-Show Session" in resp.data

    def test_page_loads_with_full_pathful_url(self, client, app, session_credit_data):
        """Page should parse the numeric ID from a full Pathful URL."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tenant_id = session_credit_data["tenant"].id

        url = f"https://app.pathful.com/wbl/sessions/{event.pathful_session_id}"
        resp = client.get(
            f"/district/teacher-usage/session-credit?pathful_id={url}&tenant_id={tenant_id}"
        )
        assert resp.status_code == 200
        assert b"Shakespeare No-Show Session" in resp.data

    def test_page_shows_teacher_names(self, client, app, session_credit_data):
        """Page should list all registered teachers for the session."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tenant_id = session_credit_data["tenant"].id

        resp = client.get(
            f"/district/teacher-usage/session-credit?pathful_id={event.pathful_session_id}&tenant_id={tenant_id}"
        )
        assert resp.status_code == 200
        assert b"Alice Test" in resp.data
        assert b"Bob Test" in resp.data
        assert b"Carol Test" in resp.data

    def test_page_shows_error_for_unknown_session(
        self, client, app, session_credit_data
    ):
        """Page should show an error message when no session is found."""
        _login(client, session_credit_data["admin"])

        resp = client.get("/district/teacher-usage/session-credit?pathful_id=999999999")
        assert resp.status_code == 200
        assert b"No session found" in resp.data


class TestBulkSessionCredit:
    """Tests for POST /district/teacher-usage/session-credit/bulk."""

    def test_bulk_credit_grants_attended_to_all(self, client, app, session_credit_data):
        """All selected teachers should have EventTeacher.status changed to 'attended'."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tp_ids = [tp.id for tp in session_credit_data["teacher_progress"]]

        resp = client.post(
            "/district/teacher-usage/session-credit/bulk",
            json={
                "event_id": event.id,
                "teacher_progress_ids": tp_ids,
                "reason": "Presenter no-show — Shakespeare session",
            },
        )
        assert (
            resp.status_code == 201
        ), f"Expected 201, got {resp.status_code}: {resp.data}"
        data = resp.get_json()
        assert len(data["granted"]) == 3
        assert len(data["skipped"]) == 0
        assert len(data["errors"]) == 0

        # Verify all 3 EventTeacher records are now 'attended'
        with app.app_context():
            for teacher in session_credit_data["teachers"]:
                et = EventTeacher.query.filter_by(
                    event_id=event.id, teacher_id=teacher.id
                ).first()
                assert et is not None
                assert (
                    et.status == "attended"
                ), f"Expected 'attended' for teacher {teacher.id}, got '{et.status}'"

    def test_bulk_credit_skips_already_overridden(
        self, client, app, session_credit_data
    ):
        """Teachers with an existing active ADD override should be silently skipped."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tp_records = session_credit_data["teacher_progress"]

        # Pre-create an override for the first teacher
        with app.app_context():
            existing = AttendanceOverride(
                teacher_progress_id=tp_records[0].id,
                event_id=event.id,
                action=OverrideAction.ADD,
                reason="Pre-existing override",
                created_by=session_credit_data["admin"].id,
            )
            db.session.add(existing)
            db.session.commit()

        tp_ids = [tp.id for tp in tp_records]
        resp = client.post(
            "/district/teacher-usage/session-credit/bulk",
            json={
                "event_id": event.id,
                "teacher_progress_ids": tp_ids,
                "reason": "Presenter no-show",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data["granted"]) == 2  # only the 2 others
        assert len(data["skipped"]) == 1  # first teacher skipped
        assert data["skipped"][0]["teacher_progress_id"] == tp_records[0].id

    def test_bulk_credit_requires_reason(self, client, app, session_credit_data):
        """Bulk credit with empty reason should return 400."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tp_ids = [tp.id for tp in session_credit_data["teacher_progress"]]

        resp = client.post(
            "/district/teacher-usage/session-credit/bulk",
            json={
                "event_id": event.id,
                "teacher_progress_ids": tp_ids,
                "reason": "",
            },
        )
        assert resp.status_code == 400

    def test_bulk_credit_creates_audit_logs(self, client, app, session_credit_data):
        """An AuditLog entry should be created for each granted teacher."""
        _login(client, session_credit_data["admin"])
        event = session_credit_data["event"]
        tp_ids = [tp.id for tp in session_credit_data["teacher_progress"]]

        resp = client.post(
            "/district/teacher-usage/session-credit/bulk",
            json={
                "event_id": event.id,
                "teacher_progress_ids": tp_ids,
                "reason": "Audit log test",
            },
        )
        assert resp.status_code == 201

        with app.app_context():
            audit_entries = AuditLog.query.filter_by(
                action="attendance_override_add",
                resource_type="attendance_override",
            ).all()
            # Should have one entry per teacher
            assert (
                len(audit_entries) >= 3
            ), f"Expected at least 3 audit entries, got {len(audit_entries)}"
            # All should be marked as bulk
            for entry in audit_entries:
                assert entry.meta.get("bulk") is True

    def test_bulk_credit_requires_event_id(self, client, app, session_credit_data):
        """Missing event_id should return 400."""
        _login(client, session_credit_data["admin"])
        tp_ids = [tp.id for tp in session_credit_data["teacher_progress"]]

        resp = client.post(
            "/district/teacher-usage/session-credit/bulk",
            json={
                "teacher_progress_ids": tp_ids,
                "reason": "Missing event",
            },
        )
        assert resp.status_code == 400
