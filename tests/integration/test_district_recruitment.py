"""
Integration tests for District Recruitment Routes

Test Cases:
- TC-1101: Dashboard shows events needing volunteers
- TC-1102: Events sorted by urgency
- TC-1103: Urgency calculation is correct
- TC-1110: Candidates ranked by score
- TC-1111: Score includes participation history
- TC-1112: Score includes recency
- TC-1120: Log outreach attempt
- TC-1121: Track outreach outcomes
- TC-1122: View outreach history
- TC-1123: Confirmed outcome adds to roster
"""

from datetime import datetime, timedelta, timezone

import pytest

from models import OutreachAttempt
from models.district_participation import DistrictParticipation
from routes.district.recruitment import calculate_urgency, score_volunteer_for_event


class TestUrgencyCalculation:
    """Tests for FR-SELFSERV-401: Urgency indicators."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_urgency_calculation_exists(self, app):
        """TC-1101: Urgency calculation function exists."""
        with app.app_context():
            assert callable(calculate_urgency)

    def test_urgency_critical_threshold(self, app):
        """TC-1103: Critical urgency for <3 days and <50% filled."""
        with app.app_context():
            # Create mock event
            class MockEvent:
                start_date = datetime.now() + timedelta(days=2)
                volunteers_needed = 10

            urgency_level, score = calculate_urgency(MockEvent(), 3)
            assert urgency_level == "critical"

    def test_urgency_warning_threshold(self, app):
        """TC-1103: Warning urgency for <7 days and <75% filled."""
        with app.app_context():

            class MockEvent:
                start_date = datetime.now() + timedelta(days=5)
                volunteers_needed = 10

            urgency_level, score = calculate_urgency(MockEvent(), 6)
            assert urgency_level == "warning"

    def test_urgency_on_track_threshold(self, app):
        """TC-1103: On track when well-staffed."""
        with app.app_context():

            class MockEvent:
                start_date = datetime.now() + timedelta(days=14)
                volunteers_needed = 10

            urgency_level, score = calculate_urgency(MockEvent(), 8)
            assert urgency_level == "on_track"

    def test_urgency_score_sorting(self, app):
        """TC-1102: Higher urgency scores for more urgent events."""
        with app.app_context():

            class CriticalEvent:
                start_date = datetime.now() + timedelta(days=1)
                volunteers_needed = 10

            class WarningEvent:
                start_date = datetime.now() + timedelta(days=5)
                volunteers_needed = 10

            critical_level, critical_score = calculate_urgency(CriticalEvent(), 2)
            warning_level, warning_score = calculate_urgency(WarningEvent(), 5)

            assert critical_score > warning_score


class TestVolunteerScoring:
    """Tests for FR-SELFSERV-402: Volunteer scoring."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_scoring_function_exists(self, app):
        """TC-1110: Volunteer scoring function exists."""
        with app.app_context():
            assert callable(score_volunteer_for_event)

    def test_scoring_returns_breakdown(self, app):
        """TC-1110: Scoring returns score breakdown."""
        with app.app_context():
            # Mock volunteer and event
            class MockVolunteer:
                id = 1
                organization_name = "Test Org"
                skills = []

            class MockEvent:
                id = 1
                type = None
                start_date = datetime.now() + timedelta(days=7)

            result = score_volunteer_for_event(
                MockVolunteer(), MockEvent(), tenant_id=1
            )

            assert "score" in result
            assert "breakdown" in result
            assert "reasons" in result


class TestOutreachModel:
    """Tests for FR-SELFSERV-403: Outreach tracking."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_outreach_model_exists(self, app):
        """TC-1120: OutreachAttempt model exists."""
        with app.app_context():
            assert OutreachAttempt is not None

    def test_outreach_method_choices(self, app):
        """TC-1121: Outreach has method choices."""
        with app.app_context():
            methods = [m[0] for m in OutreachAttempt.METHOD_CHOICES]
            assert "email" in methods
            assert "phone" in methods
            assert "text" in methods
            assert "in_person" in methods

    def test_outreach_outcome_choices(self, app):
        """TC-1121: Outreach has outcome choices."""
        with app.app_context():
            outcomes = [o[0] for o in OutreachAttempt.OUTCOME_CHOICES]
            assert "no_response" in outcomes
            assert "interested" in outcomes
            assert "declined" in outcomes
            assert "confirmed" in outcomes


class TestRecruitmentRoutes:
    """Tests for recruitment route registration."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_recruitment_dashboard_route_exists(self, app):
        """TC-1101: Recruitment dashboard route exists."""
        with app.app_context():
            from routes.district.recruitment import recruitment_dashboard

            assert callable(recruitment_dashboard)

    def test_recruitment_event_route_exists(self, app):
        """TC-1110: Recruitment event route exists."""
        with app.app_context():
            from routes.district.recruitment import recruitment_event

            assert callable(recruitment_event)

    def test_log_outreach_route_exists(self, app):
        """TC-1120: Log outreach route exists."""
        with app.app_context():
            from routes.district.recruitment import log_outreach

            assert callable(log_outreach)

    def test_outreach_history_route_exists(self, app):
        """TC-1122: Outreach history route exists."""
        with app.app_context():
            from routes.district.recruitment import outreach_history

            assert callable(outreach_history)
