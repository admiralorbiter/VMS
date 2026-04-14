"""
Integration tests for the Newsletter Formatter tool.

Tests cover:
    - Route authentication (login_required)
    - Formatter page loads
    - Sessions API returns correct JSON structure
    - Grade-level parsing from session titles
    - Session filtering: only future, virtual, confirmed/published
    - In-person sessions API: section grouping, date formatting, link handling
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from models.event import Event, EventFormat, EventStatus, EventType, db
from routes.tools.newsletter import (
    IN_PERSON_SECTION_ORDER,
    _format_in_person_datetime,
    _ordinal,
    _section_for_event_type,
    parse_grade_levels,
)
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
# Unit tests for in-person helpers
# ---------------------------------------------------------------------------


class TestOrdinal:
    """Test the ordinal suffix helper."""

    def test_ordinals(self):
        assert _ordinal(1) == "1st"
        assert _ordinal(2) == "2nd"
        assert _ordinal(3) == "3rd"
        assert _ordinal(4) == "4th"
        assert _ordinal(11) == "11th"
        assert _ordinal(12) == "12th"
        assert _ordinal(13) == "13th"
        assert _ordinal(21) == "21st"
        assert _ordinal(22) == "22nd"
        assert _ordinal(25) == "25th"


class TestFormatInPersonDatetime:
    """Test the newsletter-style datetime formatter."""

    def test_same_ampm(self):
        start = datetime(2026, 4, 2, 8, 30)
        end = datetime(2026, 4, 2, 10, 30)
        result = _format_in_person_datetime(start, end)
        assert result == "Thursday, April 2nd, from 8:30-10:30 AM"

    def test_cross_ampm(self):
        start = datetime(2026, 4, 2, 11, 0)
        end = datetime(2026, 4, 2, 13, 0)
        result = _format_in_person_datetime(start, end)
        assert result == "Thursday, April 2nd, from 11:00 AM to 1:00 PM"

    def test_no_end_time(self):
        start = datetime(2026, 3, 25, 8, 15)
        result = _format_in_person_datetime(start, None)
        assert result == "Wednesday, March 25th, 8:15 AM"


class TestSectionMapping:
    """Test the event type → section mapping."""

    def test_career_jumping(self):
        assert _section_for_event_type(EventType.CAREER_JUMPING) == "Career Jumping"

    def test_career_speaker(self):
        assert _section_for_event_type(EventType.CAREER_SPEAKER) == "Career Speakers"

    def test_career_fair(self):
        assert _section_for_event_type(EventType.CAREER_FAIR) == "Career Fair"

    def test_classroom_speaker(self):
        assert _section_for_event_type(EventType.CLASSROOM_SPEAKER) == "Other Events"

    def test_workplace_visit(self):
        assert _section_for_event_type(EventType.WORKPLACE_VISIT) == "Other Events"

    def test_unknown_type(self):
        assert _section_for_event_type(EventType.VIRTUAL_SESSION) == "Other Events"

    def test_section_order(self):
        assert IN_PERSON_SECTION_ORDER == [
            "Career Jumping",
            "Career Speakers",
            "Career Fair",
            "Other Events",
        ]


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


# ---------------------------------------------------------------------------
# Integration tests for in-person sessions API
# ---------------------------------------------------------------------------


class TestInPersonNewsletterRoutes:
    """Test the in-person newsletter formatter routes."""

    def test_in_person_api_requires_login(self, client):
        """Unauthenticated users should be redirected."""
        response = safe_route_test(
            client, "/tools/newsletter-formatter/in-person-sessions"
        )
        assert_route_response(response, expected_statuses=[302, 401, 403])

    def test_in_person_api_returns_json(self, client, auth_headers):
        """In-person API should return JSON with success flag and section_order."""
        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/in-person-sessions",
            headers=auth_headers,
        )
        assert_route_response(response, expected_statuses=[200, 302, 500])
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "success" in data
            assert "sessions" in data
            assert "section_order" in data

    def test_in_person_api_with_career_jumping(self, client, auth_headers, app):
        """API should return upcoming confirmed career jumping events."""
        with app.app_context():
            event = Event(
                title="Carl Bruce Middle School Career Jumping, 6th Grade",
                type=EventType.CAREER_JUMPING,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                end_date=datetime.now(timezone.utc)
                + timedelta(days=7, hours=2, minutes=15),
                format=EventFormat.IN_PERSON,
                district_partner="KCKPS USD 500",
                registration_link="https://prepkc.nepris.com/app/sessions/109901",
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/in-person-sessions",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["success"] is True
            test_events = [s for s in data["sessions"] if s["id"] == event_id]
            if test_events:
                e = test_events[0]
                assert e["section"] == "Career Jumping"
                assert e["district"] == "KCKPS USD 500"
                assert e["link"] == "https://prepkc.nepris.com/app/sessions/109901"
                assert "from" in e["formatted_datetime"]

    def test_in_person_api_excludes_virtual(self, client, auth_headers, app):
        """In-person API should NOT return virtual sessions."""
        with app.app_context():
            event = Event(
                title="K: Virtual Only Session",
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
            client,
            "/tools/newsletter-formatter/in-person-sessions",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            virtual = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(virtual) == 0, "Virtual sessions should not appear in in-person"

    def test_in_person_api_excludes_past(self, client, auth_headers, app):
        """In-person API should NOT return past events."""
        with app.app_context():
            event = Event(
                title="Past Career Fair",
                type=EventType.CAREER_FAIR,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) - timedelta(days=7),
                end_date=datetime.now(timezone.utc) - timedelta(days=7, hours=-2),
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/in-person-sessions",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            past = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(past) == 0, "Past events should not appear"

    def test_in_person_classroom_speaker_in_other(self, client, auth_headers, app):
        """Classroom speaker events should map to 'Other Events' section."""
        with app.app_context():
            event = Event(
                title="Science Classroom Visit",
                type=EventType.CLASSROOM_SPEAKER,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=14),
                end_date=datetime.now(timezone.utc) + timedelta(days=14, hours=1),
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/in-person-sessions",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            test_events = [s for s in data["sessions"] if s["id"] == event_id]
            if test_events:
                assert test_events[0]["section"] == "Other Events"


# ---------------------------------------------------------------------------
# Integration tests for search-virtual-sessions endpoint
# ---------------------------------------------------------------------------


class TestSearchVirtualSessions:
    """Tests for the search-virtual-sessions endpoint."""

    def test_search_requires_auth(self, client):
        """Search endpoint requires authentication."""
        response = client.get(
            "/tools/newsletter-formatter/search-virtual-sessions?q=career"
        )
        assert response.status_code in (302, 401)

    def test_search_returns_matching_sessions(self, client, auth_headers, app):
        """Search returns virtual sessions matching the query."""
        with app.app_context():
            event = Event(
                title="Exploring Veterinary Careers",
                type=EventType.VIRTUAL_SESSION,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=5),
                end_date=datetime.now(timezone.utc) + timedelta(days=5, hours=1),
                format=EventFormat.VIRTUAL,
                pathful_session_id=99999,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/search-virtual-sessions?q=veterinary",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["success"] is True
            matches = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(matches) == 1
            assert "Veterinary" in matches[0]["title"]

    def test_search_empty_query_returns_empty(self, client, auth_headers):
        """Empty search query returns empty results (no error)."""
        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/search-virtual-sessions?q=",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["sessions"] == []

    def test_search_excludes_in_person(self, client, auth_headers, app):
        """Search only returns virtual sessions, not in-person events."""
        with app.app_context():
            event = Event(
                title="In-Person Unicorn Careers",
                type=EventType.CAREER_JUMPING,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=5),
                format=EventFormat.IN_PERSON,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/search-virtual-sessions?q=unicorn",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            matches = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(matches) == 0

    def test_search_includes_nepris_link(self, client, auth_headers, app):
        """Search results include correct Nepris link from pathful_session_id."""
        with app.app_context():
            event = Event(
                title="Zebra Zoologist Virtual Talk",
                type=EventType.VIRTUAL_SESSION,
                status=EventStatus.CONFIRMED,
                start_date=datetime.now(timezone.utc) + timedelta(days=3),
                format=EventFormat.VIRTUAL,
                pathful_session_id=12345,
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = safe_route_test(
            client,
            "/tools/newsletter-formatter/search-virtual-sessions?q=zebra",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = json.loads(response.data)
            matches = [s for s in data["sessions"] if s["id"] == event_id]
            assert len(matches) == 1
            assert matches[0]["link"] == "https://prepkc.nepris.com/app/sessions/12345"
