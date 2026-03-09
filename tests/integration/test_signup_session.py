"""
Integration tests for the Sign Up for Upcoming Session feature.

Covers:
- create_override for a future event sets EventTeacher.status to 'registered'
- create_override for a past event keeps EventTeacher.status as 'attended'
- search_sessions with upcoming_only=1 only returns future sessions
- Teacher detail page shows the Sign Up button
"""

from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import generate_password_hash

from models import db
from models.attendance_override import AttendanceOverride, OverrideAction
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from models.tenant import Tenant
from models.user import TenantRole, User


@pytest.fixture
def signup_data(app):
    """
    Setup data for sign-up tests.

    Creates:
    - District, Tenant, School, Teacher, TeacherProgress
    - 1 past event (completed), 1 future event (confirmed)
    - Admin user with tenant
    """
    with app.app_context():
        d = District(name="SignUp Test District")
        db.session.add(d)
        db.session.commit()

        tenant = Tenant(name="SignUp Tenant", district_id=d.id, slug="signup-tenant")
        db.session.add(tenant)
        db.session.commit()

        s = School(id="SU_SCHOOL_01", name="SignUp School", district_id=d.id)
        db.session.add(s)
        db.session.commit()

        t = Teacher(first_name="Alex", last_name="Johnson", school_id=s.id)
        db.session.add(t)
        db.session.commit()

        tp = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building=s.name,
            name="Alex Johnson",
            email="alex@test.com",
            teacher_id=t.id,
            target_sessions=2,
        )
        tp.tenant_id = tenant.id
        tp.is_active = True
        db.session.add(tp)
        db.session.commit()

        # Past event: completed
        event_past = Event(
            title="Past Session Alpha",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.COMPLETED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now(timezone.utc) - timedelta(days=10),
            district_partner=d.name,
        )
        db.session.add(event_past)
        db.session.commit()

        # Future event: confirmed
        event_future = Event(
            title="Future Session Beta",
            type=EventType.VIRTUAL_SESSION,
            status=EventStatus.CONFIRMED,
            format=EventFormat.VIRTUAL,
            start_date=datetime.now(timezone.utc) + timedelta(days=30),
            district_partner=d.name,
        )
        db.session.add(event_future)
        db.session.commit()

        # Admin user scoped to the tenant
        admin = User(
            username="signup_admin",
            email="admin@signup.test",
            is_admin=True,
            tenant_id=tenant.id,
            tenant_role=TenantRole.ADMIN,
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
            "event_past": event_past,
            "event_future": event_future,
            "admin": admin,
        }


def _login_admin(client, admin):
    """Helper to log in as admin user."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True


class TestOverrideStatusByDate:
    """Tests that create_override sets correct EventTeacher.status based on event date."""

    def test_future_event_override_sets_registered(self, client, app, signup_data):
        """Override for a future event should set EventTeacher.status to 'registered'."""
        _login_admin(client, signup_data["admin"])
        tp = signup_data["teacher_progress"]
        event = signup_data["event_future"]

        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "Signing up teacher for upcoming session",
            },
        )

        assert (
            resp.status_code == 201
        ), f"Expected 201, got {resp.status_code}: {resp.data}"

        et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=signup_data["teacher"].id
        ).first()
        assert et is not None, "EventTeacher should be created"
        assert (
            et.status == "registered"
        ), f"Expected status 'registered' for future event, got '{et.status}'"
        # Future events should not have attendance_confirmed_at
        assert (
            et.attendance_confirmed_at is None
        ), "attendance_confirmed_at should be None for future event sign-up"

    def test_past_event_override_still_sets_attended(self, client, app, signup_data):
        """Override for a past event should set EventTeacher.status to 'attended'."""
        _login_admin(client, signup_data["admin"])
        tp = signup_data["teacher_progress"]
        event = signup_data["event_past"]

        resp = client.post(
            f"/district/teacher-usage/overrides/{tp.id}",
            json={
                "action": "add",
                "event_id": event.id,
                "reason": "Teacher was present at past session",
            },
        )

        assert (
            resp.status_code == 201
        ), f"Expected 201, got {resp.status_code}: {resp.data}"

        et = EventTeacher.query.filter_by(
            event_id=event.id, teacher_id=signup_data["teacher"].id
        ).first()
        assert et is not None
        assert (
            et.status == "attended"
        ), f"Expected status 'attended' for past event, got '{et.status}'"
        assert (
            et.attendance_confirmed_at is not None
        ), "attendance_confirmed_at should be set for past event"


class TestSearchSessionsUpcomingOnly:
    """Tests for the search_sessions endpoint with upcoming_only filter."""

    def test_upcoming_only_excludes_past_sessions(self, client, app, signup_data):
        """search_sessions with upcoming_only=1 should only return future sessions."""
        _login_admin(client, signup_data["admin"])

        resp = client.get("/district/teacher-usage/sessions/search?upcoming_only=1")
        assert resp.status_code == 200

        data = resp.get_json()
        sessions = data["sessions"]

        # Should contain the future session
        titles = [s["title"] for s in sessions]
        assert (
            "Future Session Beta" in titles
        ), f"Expected 'Future Session Beta' in results, got {titles}"
        # Should NOT contain the past session
        assert (
            "Past Session Alpha" not in titles
        ), f"Past session should be excluded with upcoming_only=1, got {titles}"

    def test_search_without_upcoming_only_returns_both(self, client, app, signup_data):
        """search_sessions without upcoming_only should return both past and future."""
        _login_admin(client, signup_data["admin"])

        resp = client.get("/district/teacher-usage/sessions/search")
        assert resp.status_code == 200

        data = resp.get_json()
        titles = [s["title"] for s in data["sessions"]]
        # Should contain both
        assert "Future Session Beta" in titles
        assert "Past Session Alpha" in titles


class TestTeacherDetailSignUpButton:
    """Tests that the teacher detail page includes Sign Up for Session button."""

    def test_teacher_detail_has_signup_button(self, client, app, signup_data):
        """Teacher detail page should have 'Sign Up for Session' button."""
        _login_admin(client, signup_data["admin"])
        tp = signup_data["teacher_progress"]
        tenant = signup_data["tenant"]

        resp = client.get(
            f"/district/teacher-usage/teacher/{tp.id}?tenant_id={tenant.id}"
        )
        assert resp.status_code == 200
        assert (
            b"Sign Up for Session" in resp.data
        ), "Expected 'Sign Up for Session' button in teacher detail page"
