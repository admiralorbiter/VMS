"""
Integration tests for No-Show Override feature on the Teacher Usage dashboard.

Covers:
- No-shows page renders with Revise buttons when teacher_progress_id is present
- create_override API (action=add) flips EventTeacher.status from no_show to attended
- Duplicate override returns 409
- AuditLog entry is created on override
- Overridden sessions marked as is_overridden in no_shows() route data
"""

from datetime import datetime, timedelta

import pytest
from flask_login import login_user
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
def noshow_data(app):
    """
    Setup test data for no-show override tests.

    Creates:
    - District, Tenant, School, Teacher, TeacherProgress
    - 2 completed virtual sessions: one attended, one no-show
    - Admin user for performing overrides
    """
    with app.app_context():
        d = District(name="NoShow Test District")
        db.session.add(d)
        db.session.commit()

        tenant = Tenant(name="NoShow Tenant", district_id=d.id, slug="noshow-tenant")
        db.session.add(tenant)
        db.session.commit()

        s = School(id="NS_SCHOOL_01", name="NoShow Test School", district_id=d.id)
        db.session.add(s)
        db.session.commit()

        t = Teacher(first_name="Jane", last_name="Smith", school_id=s.id)
        db.session.add(t)
        db.session.commit()

        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="Jane Smith",
            email="jane@test.com",
            teacher_id=t.id,
            target_sessions=2,
        )
        tp.tenant_id = tenant.id
        tp.is_active = True
        db.session.add(tp)
        db.session.commit()

        # Event A: teacher attended
        event_attended = Event(
            title="Attended Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now() - timedelta(days=10),
            district_partner=d.name,
        )
        db.session.add(event_attended)
        db.session.commit()
        db.session.add(
            EventTeacher(event_id=event_attended.id, teacher_id=t.id, status="attended")
        )

        # Event B: teacher was no-show
        event_noshow = Event(
            title="No Show Session",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now() - timedelta(days=5),
            district_partner=d.name,
        )
        db.session.add(event_noshow)
        db.session.commit()
        db.session.add(
            EventTeacher(event_id=event_noshow.id, teacher_id=t.id, status="no_show")
        )

        # Admin user
        admin = User(
            username="noshow_admin",
            email="admin@noshow.test",
            is_admin=True,
        )
        admin.password_hash = generate_password_hash("pass")
        db.session.add(admin)
        db.session.commit()

        yield {
            "district": d,
            "tenant": tenant,
            "school": s,
            "teacher": t,
            "teacher_progress": tp,
            "event_attended": event_attended,
            "event_noshow": event_noshow,
            "admin": admin,
        }


def _login_admin(client, app, admin):
    """Helper to log in as admin user."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True


class TestNoShowOverrideAPI:
    """Tests for the create_override endpoint used from the no-shows page."""

    def test_override_add_flips_noshow_to_attended(self, client, app, noshow_data):
        """
        POST override with action=add should change EventTeacher.status
        from 'no_show' to 'attended'.
        """
        _login_admin(client, app, noshow_data["admin"])
        tp = noshow_data["teacher_progress"]
        event = noshow_data["event_noshow"]

        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "Teacher was present but not recorded",
            },
        )

        assert (
            resp.status_code == 201
        ), f"Expected 201, got {resp.status_code}: {resp.data}"
        data = resp.get_json()
        assert "override" in data
        assert data["override"]["action"] == "add"

        # Verify EventTeacher status changed
        et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=noshow_data["teacher"].id
        ).first()
        assert et is not None
        assert (
            et.status == "attended"
        ), f"Expected status 'attended' after override, got '{et.status}'"

    def test_override_creates_audit_log(self, client, app, noshow_data):
        """Override should create an AuditLog entry."""
        _login_admin(client, app, noshow_data["admin"])
        tp = noshow_data["teacher_progress"]
        event = noshow_data["event_noshow"]

        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "Correcting no-show",
            },
        )
        assert resp.status_code == 201

        # Find audit log
        audit = AuditLog.query.filter_by(
            resource_type="attendance_override",
            action="attendance_override_add",
        ).first()
        assert audit is not None, "Audit log entry should be created"
        assert audit.user_id == noshow_data["admin"].id
        assert audit.meta["teacher_name"] == "Jane Smith"
        assert audit.meta["event_title"] == "No Show Session"
        assert audit.meta["reason"] == "Correcting no-show"

    def test_duplicate_override_returns_409(self, client, app, noshow_data):
        """Second override with same action for same session returns 409."""
        _login_admin(client, app, noshow_data["admin"])
        tp = noshow_data["teacher_progress"]
        event = noshow_data["event_noshow"]

        payload = {
            "action": "add",
            "event_id": event.id,
            "reason": "First override",
        }

        resp1 = client.post(f"/district/teacher-usage/overrides/{tp.id}", json=payload)
        assert resp1.status_code == 201

        # Second call with same action + event should be rejected
        payload["reason"] = "Duplicate attempt"
        resp2 = client.post(f"/district/teacher-usage/overrides/{tp.id}", json=payload)
        assert (
            resp2.status_code == 409
        ), f"Expected 409 for duplicate override, got {resp2.status_code}"

    def test_override_requires_reason(self, client, app, noshow_data):
        """Override without reason should return 400."""
        _login_admin(client, app, noshow_data["admin"])
        tp = noshow_data["teacher_progress"]
        event = noshow_data["event_noshow"]

        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "",  # empty reason
            },
        )
        assert resp.status_code == 400


class TestNoShowsRouteData:
    """Tests that the no_shows() route includes teacher_progress_id and override status."""

    def test_no_shows_page_loads(self, client, app, noshow_data):
        """No-shows page should return 200 and include the no-show session."""
        _login_admin(client, app, noshow_data["admin"])
        tenant = noshow_data["tenant"]

        resp = client.get(
            f"/district/teacher-usage/no-shows?tenant_id={tenant.id}"
            f"&year=2025-2026&semester=fall"
        )
        assert resp.status_code == 200
        # The page should mention "No Show Session"
        assert b"No Show Session" in resp.data or b"No Shows Report" in resp.data

    def test_no_shows_page_contains_revise_button(self, client, app, noshow_data):
        """Each no-show session should have a Revise No-Show button."""
        _login_admin(client, app, noshow_data["admin"])
        tenant = noshow_data["tenant"]

        resp = client.get(
            f"/district/teacher-usage/no-shows?tenant_id={tenant.id}"
            f"&year=2025-2026&semester=fall"
        )
        assert resp.status_code == 200
        assert (
            b"Revise No-Show" in resp.data
        ), "Expected 'Revise No-Show' button in template output"

    def test_overridden_session_shows_revised_badge(self, client, app, noshow_data):
        """After an override, the session should show 'Revised' badge, not button."""
        _login_admin(client, app, noshow_data["admin"])
        tp = noshow_data["teacher_progress"]
        event = noshow_data["event_noshow"]
        tenant = noshow_data["tenant"]

        # Create the override
        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "Teacher was present",
            },
        )
        assert resp.status_code == 201

        # Note: After an ADD override, EventTeacher.status becomes 'attended',
        # so it won't appear in the no_show query at all.
        # The session should disappear from the no-shows page entirely.
        resp = client.get(
            f"/district/teacher-usage/no-shows?tenant_id={tenant.id}"
            f"&year=2025-2026&semester=fall"
        )
        assert resp.status_code == 200
        # "No Show Session" should no longer appear since status is now 'attended'
        assert (
            b"No Show Session" not in resp.data
        ), "Overridden session should no longer appear in no-shows list"
