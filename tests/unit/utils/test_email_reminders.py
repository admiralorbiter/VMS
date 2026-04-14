"""
Unit Tests for Email Reminder Utilities
========================================

Tests for the email reminder utility functions including session querying,
HTML/text list building, context generation, and template rendering.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.email import EmailTemplate
from models.event import Event, EventFormat, EventStatus, EventType
from models.teacher_progress import TeacherProgress
from utils.email_reminders import (
    build_session_list_html,
    build_session_list_text,
    build_teacher_reminder_context,
    get_completed_session_count,
    get_upcoming_virtual_sessions,
)


@pytest.fixture
def upcoming_sessions(app):
    """Create test virtual sessions for reminder tests."""
    with app.app_context():
        sessions = []
        now = datetime.now(timezone.utc)

        # Upcoming confirmed session
        s1 = Event(
            title="Healthcare Careers Exploration",
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            start_date=now + timedelta(days=10),
            status=EventStatus.CONFIRMED,
            career_cluster="Health Sciences",
        )
        db.session.add(s1)
        sessions.append(s1)

        # Upcoming requested session
        s2 = Event(
            title="Engineering & Technology Panel",
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            start_date=now + timedelta(days=20),
            status=EventStatus.REQUESTED,
            career_cluster="STEM",
        )
        db.session.add(s2)
        sessions.append(s2)

        # Past session (should NOT appear in upcoming)
        s3 = Event(
            title="Past Session",
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            start_date=now - timedelta(days=5),
            status=EventStatus.COMPLETED,
        )
        db.session.add(s3)

        # Cancelled session (should NOT appear in upcoming)
        s4 = Event(
            title="Cancelled Session",
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            start_date=now + timedelta(days=15),
            status=EventStatus.CANCELLED,
        )
        db.session.add(s4)

        # Non-virtual session (should NOT appear)
        s5 = Event(
            title="In-Person Career Fair",
            type=EventType.CAREER_FAIR,
            format=EventFormat.IN_PERSON,
            start_date=now + timedelta(days=12),
            status=EventStatus.CONFIRMED,
        )
        db.session.add(s5)

        db.session.commit()
        yield sessions


@pytest.fixture
def sample_teacher(app):
    """Create a sample TeacherProgress record."""
    with app.app_context():
        teacher = TeacherProgress(
            academic_year="2025-2026",
            virtual_year="2025-2026",
            building="Banneker Elementary",
            name="Tahra Arnold",
            email="tahra.arnold@kckps.org",
            grade="K",
            target_sessions=1,
        )
        db.session.add(teacher)
        db.session.commit()
        yield teacher


class TestGetUpcomingVirtualSessions:
    """Tests for get_upcoming_virtual_sessions."""

    def test_returns_only_future_virtual_sessions(self, app, upcoming_sessions):
        """Should only return future virtual sessions with active statuses."""
        with app.app_context():
            sessions = get_upcoming_virtual_sessions()
            # Should get the 2 upcoming active sessions, not past/cancelled/non-virtual
            assert len(sessions) == 2
            titles = [s.title for s in sessions]
            assert "Healthcare Careers Exploration" in titles
            assert "Engineering & Technology Panel" in titles
            assert "Past Session" not in titles
            assert "Cancelled Session" not in titles
            assert "In-Person Career Fair" not in titles

    def test_ordered_by_start_date(self, app, upcoming_sessions):
        """Sessions should be ordered by start date ascending."""
        with app.app_context():
            sessions = get_upcoming_virtual_sessions()
            if len(sessions) >= 2:
                assert sessions[0].start_date <= sessions[1].start_date

    def test_filters_by_tenant_id(self, app, upcoming_sessions):
        """Should filter by tenant_id when provided."""
        with app.app_context():
            # No sessions have tenant_id set, so filtering should return empty
            sessions = get_upcoming_virtual_sessions(tenant_id=9999)
            assert len(sessions) == 0

    def test_returns_empty_when_no_sessions(self, app):
        """Should return empty list when no sessions exist."""
        with app.app_context():
            sessions = get_upcoming_virtual_sessions()
            assert sessions == []


class TestBuildSessionListHtml:
    """Tests for build_session_list_html."""

    def test_returns_table_with_sessions(self, app, upcoming_sessions):
        """Should return an HTML table with session data."""
        with app.app_context():
            html = build_session_list_html(upcoming_sessions)
            assert "<table" in html
            assert "Healthcare Careers Exploration" in html
            assert "Engineering & Technology Panel" in html
            assert "Health Sciences" in html
            assert "STEM" in html

    def test_returns_empty_message_for_no_sessions(self):
        """Should return a 'no sessions' message when list is empty."""
        html = build_session_list_html([])
        assert "No upcoming sessions" in html
        assert "<table" not in html

    def test_handles_missing_career_cluster(self, app):
        """Should handle sessions without a career_cluster field."""
        with app.app_context():
            session = Event(
                title="No Cluster Session",
                type=EventType.VIRTUAL_SESSION,
                format=EventFormat.VIRTUAL,
                start_date=datetime.now(timezone.utc) + timedelta(days=5),
                status=EventStatus.CONFIRMED,
                career_cluster=None,
            )
            db.session.add(session)
            db.session.commit()

            html = build_session_list_html([session])
            # Should use em-dash fallback
            assert "—" in html


class TestBuildSessionListText:
    """Tests for build_session_list_text."""

    def test_returns_text_list_with_sessions(self, app, upcoming_sessions):
        """Should return a plain text list with session data."""
        with app.app_context():
            text = build_session_list_text(upcoming_sessions)
            assert "Healthcare Careers Exploration" in text
            assert "Engineering & Technology Panel" in text
            assert "Health Sciences" in text

    def test_returns_empty_message_for_no_sessions(self):
        """Should return a 'no sessions' message when list is empty."""
        text = build_session_list_text([])
        assert "No upcoming sessions" in text


class TestBuildTeacherReminderContext:
    """Tests for build_teacher_reminder_context."""

    def test_builds_complete_context(self, app, sample_teacher, upcoming_sessions):
        """Should build a complete context dict with all required placeholders."""
        with app.app_context():
            context = build_teacher_reminder_context(
                teacher=sample_teacher,
                sessions=upcoming_sessions,
                completed_count=0,
                district_name="Kansas City Kansas Public Schools",
            )

            assert context["teacher_name"] == "Tahra Arnold"
            assert context["building_name"] == "Banneker Elementary"
            assert context["district_name"] == "Kansas City Kansas Public Schools"
            assert "login_url" in context
            assert "contact_email" in context
            assert "<table" in context["session_list"]
            assert "Healthcare" in context["session_list_text"]

    def test_context_has_all_required_keys(self, app, sample_teacher):
        """Context should contain all keys required by the template."""
        with app.app_context():
            context = build_teacher_reminder_context(
                teacher=sample_teacher,
                sessions=[],
                completed_count=0,
            )

            required_keys = [
                "teacher_name",
                "building_name",
                "district_name",
                "session_list",
                "session_list_text",
                "login_url",
                "contact_email",
            ]
            for key in required_keys:
                assert key in context, f"Missing required key: {key}"


class TestTemplateRendering:
    """Tests for template rendering with the session reminder template."""

    def test_template_renders_without_missing_placeholders(self, app, sample_teacher):
        """The file-synced template should render cleanly with a complete context."""
        with app.app_context():
            # Sync templates from file definitions
            from utils.email import render_template as email_render
            from utils.template_sync import sync_file_templates

            sync_file_templates()

            template = EmailTemplate.query.filter_by(
                purpose_key="teacher_session_reminder", is_active=True
            ).first()
            assert (
                template is not None
            ), "teacher_session_reminder template not found after sync"

            # Build a context
            context = build_teacher_reminder_context(
                teacher=sample_teacher,
                sessions=[],
                completed_count=0,
            )

            subject, html_body, text_body = email_render(template, context)

            # No unreplaced placeholders should remain
            assert "{{" not in subject
            assert "{{" not in html_body
            assert "{{" not in text_body

            # Personalized content should be present
            assert "Tahra Arnold" in html_body
            assert "Kansas City Kansas Public Schools" in subject
            # Login URL and contact info should be rendered
            assert "/login" in html_body
            assert "Log in to the VMS portal" in html_body
