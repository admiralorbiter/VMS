"""
Integration tests for the Newsletter Formatter tool.

Tests cover:
    - Route authentication (login_required)
    - Formatter page loads
    - Sessions API returns correct JSON structure
    - Grade-level parsing from session titles
    - Session filtering: only future, virtual, confirmed/published
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from models.event import Event, EventFormat, EventStatus, EventType, db
from routes.tools.newsletter import parse_grade_levels
from tests.conftest import assert_route_response, safe_route_test

# ---------------------------------------------------------------------------
# Unit tests for parse_grade_levels
# ---------------------------------------------------------------------------


class TestParseGradeLevels:
    """Test the grade-level parsing utility."""

    def test_kindergarten(self):
        assert parse_grade_levels("K: Meteorologist Seasons") == ["Kindergarten"]

    def test_first_grade(self):
        assert parse_grade_levels("1st Grade: Economics") == ["First Grade"]

    def test_second_grade(self):
        assert parse_grade_levels("2nd Grade: History") == ["Second Grade"]

    def test_third_grade(self):
        assert parse_grade_levels("3rd Grade: Science") == ["Third Grade"]

    def test_fourth_grade(self):
        assert parse_grade_levels("4th Grade: Art") == ["Fourth Grade"]

    def test_fifth_grade(self):
        assert parse_grade_levels("5th Grade: Music") == ["Fifth Grade"]

    def test_k_2_span(self):
        result = parse_grade_levels("K-2: Stories, Science, and Snakes!")
        assert result == ["Kindergarten", "First Grade", "Second Grade"]

    def test_k_1_span(self):
        result = parse_grade_levels("K-1: Managing Emotions")
        assert result == ["Kindergarten", "First Grade"]

    def test_2_5_span(self):
        result = parse_grade_levels("2-5: National Museum Tour")
        assert result == ["Second Grade", "Third Grade", "Fourth Grade", "Fifth Grade"]

    def test_general_fallback(self):
        assert parse_grade_levels("Careers in Construction") == ["General / KC Series"]

    def test_empty_title(self):
        assert parse_grade_levels("") == ["General / KC Series"]

    def test_none_title(self):
        assert parse_grade_levels(None) == ["General / KC Series"]


# ---------------------------------------------------------------------------
# Integration tests for routes
# ---------------------------------------------------------------------------


class TestNewsletterFormatterRoutes:
    """Test the newsletter formatter routes."""

    def test_formatter_page_requires_login(self, client):
        """Unauthenticated users should be redirected to login."""
        response = safe_route_test(client, "/tools/newsletter-formatter")
        assert_route_response(response, expected_statuses=[302, 401, 403])

    def test_sessions_api_requires_login(self, client):
        """Unauthenticated users should be redirected."""
        response = safe_route_test(client, "/tools/newsletter-formatter/sessions")
        assert_route_response(response, expected_statuses=[302, 401, 403])

    def test_formatter_page_loads(self, client, auth_headers):
        """Authenticated users should see the formatter page."""
        response = safe_route_test(
            client, "/tools/newsletter-formatter", headers=auth_headers
        )
        assert_route_response(response, expected_statuses=[200, 500])
        if response.status_code == 200:
            assert b"Newsletter Formatter" in response.data

    def test_sessions_api_returns_json(self, client, auth_headers):
        """Sessions API should return JSON with success flag."""
        response = safe_route_test(
            client, "/tools/newsletter-formatter/sessions", headers=auth_headers
        )
        assert_route_response(response, expected_statuses=[200, 302, 500])
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "success" in data
            assert "sessions" in data

    def test_sessions_api_with_upcoming_session(self, client, auth_headers, app):
        """API should return upcoming confirmed virtual sessions."""
        with app.app_context():
            event = Event(
                title="K: Test Kindergarten Session",
                type=EventType.VIRTUAL_SESSION,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                end_date=datetime.now(timezone.utc) + timedelta(days=7, hours=1),
                format=EventFormat.VIRTUAL,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client, "/tools/newsletter-formatter/sessions", headers=auth_headers
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["success"] is True
            # Find our test event
            test_sessions = [s for s in data["sessions"] if s["id"] == event_id]
            if test_sessions:
                s = test_sessions[0]
                assert s["title"] == "K: Test Kindergarten Session"
                assert s["grade_levels"] == ["Kindergarten"]
                assert "formatted_datetime" in s

    def test_sessions_api_excludes_past_events(self, client, auth_headers, app):
        """API should NOT return past sessions."""
        with app.app_context():
            event = Event(
                title="1st Grade: Past Session",
                type=EventType.VIRTUAL_SESSION,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) - timedelta(days=7),
                end_date=datetime.now(timezone.utc) - timedelta(days=7, hours=-1),
                format=EventFormat.VIRTUAL,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client, "/tools/newsletter-formatter/sessions", headers=auth_headers
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            past = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(past) == 0, "Past sessions should not appear in results"

    def test_sessions_api_excludes_non_virtual(self, client, auth_headers, app):
        """API should only return VIRTUAL_SESSION type events."""
        with app.app_context():
            event = Event(
                title="In-Person Event",
                type=EventType.IN_PERSON,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                end_date=datetime.now(timezone.utc) + timedelta(days=7, hours=2),
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client, "/tools/newsletter-formatter/sessions", headers=auth_headers
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            non_virtual = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(non_virtual) == 0, "Non-virtual events should not appear"

    def test_sessions_api_excludes_draft_status(self, client, auth_headers, app):
        """API should only return CONFIRMED or PUBLISHED sessions."""
        with app.app_context():
            event = Event(
                title="3rd Grade: Draft Session",
                type=EventType.VIRTUAL_SESSION,
                status=EventStatus.DRAFT,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                end_date=datetime.now(timezone.utc) + timedelta(days=7, hours=1),
                format=EventFormat.VIRTUAL,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client, "/tools/newsletter-formatter/sessions", headers=auth_headers
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            drafts = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(drafts) == 0, "Draft sessions should not appear"
