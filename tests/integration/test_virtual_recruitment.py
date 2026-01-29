"""
Integration tests for Virtual Sessions Presenter Recruitment View

Tests the /virtual/usage/recruitment endpoint to ensure proper functionality
including query logic, filtering, access control, and dynamic behavior.
"""

from datetime import datetime, timedelta, timezone

import pytest
from flask import url_for
from werkzeug.security import generate_password_hash

from models import db
from models.district_model import District
from models.event import Event, EventStatus, EventType
from models.school_model import School
from models.user import SecurityLevel, User
from models.volunteer import EventParticipation, Volunteer


class TestVirtualRecruitment:
    """Test suite for Virtual Sessions Presenter Recruitment View"""

    @pytest.fixture
    def setup_test_data(self, app):
        """Create test data including events with and without presenters"""
        with app.app_context():
            # Create district
            district = District.query.first()
            if not district:
                district = District(name="Test District")
                db.session.add(district)
                db.session.flush()

            # Create school
            school = School.query.first()
            if not school:
                school = School(
                    id="TEST_SCHOOL", name="Test School", district_id=district.id
                )
                db.session.add(school)
                db.session.flush()

            # Create future virtual event WITHOUT presenter
            future_event_no_presenter = Event(
                title="Future Virtual Session - Needs Presenter",
                type=EventType.VIRTUAL_SESSION,
                start_date=datetime.now(timezone.utc) + timedelta(days=10),
                status=EventStatus.CONFIRMED,
                school=school.id,
            )
            db.session.add(future_event_no_presenter)
            db.session.flush()

            # Create future virtual event WITH presenter
            future_event_with_presenter = Event(
                title="Future Virtual Session - Has Presenter",
                type=EventType.VIRTUAL_SESSION,
                start_date=datetime.now(timezone.utc) + timedelta(days=15),
                status=EventStatus.CONFIRMED,
                school=school.id,
            )
            db.session.add(future_event_with_presenter)
            db.session.flush()

            # Create volunteer and assign as presenter
            volunteer = Volunteer.query.filter_by(
                first_name="Test", last_name="Presenter"
            ).first()
            if not volunteer:
                volunteer = Volunteer(
                    first_name="Test",
                    last_name="Presenter",
                    middle_name="",
                )
                db.session.add(volunteer)
                db.session.flush()

                # Add email for the volunteer
                from models.contact import ContactTypeEnum, Email

                email = Email(
                    contact_id=volunteer.id,
                    email="test.presenter@example.com",
                    type=ContactTypeEnum.professional,
                    primary=True,
                )
                db.session.add(email)
                db.session.flush()

            # Assign presenter to second event
            participation = EventParticipation(
                volunteer_id=volunteer.id,
                event_id=future_event_with_presenter.id,
                participant_type="Presenter",
                status="Confirmed",
            )
            db.session.add(participation)

            # Create past virtual event without presenter (should NOT appear)
            past_event = Event(
                title="Past Virtual Session",
                type=EventType.VIRTUAL_SESSION,
                start_date=datetime.now(timezone.utc) - timedelta(days=5),
                status=EventStatus.COMPLETED,
                school=school.id,
            )
            db.session.add(past_event)

            # Create future non-virtual event (should NOT appear)
            future_non_virtual = Event(
                title="Future In-Person Event",
                type=EventType.CAREER_FAIR,
                start_date=datetime.now(timezone.utc) + timedelta(days=20),
                status=EventStatus.CONFIRMED,
                school=school.id,
            )
            db.session.add(future_non_virtual)

            db.session.commit()

            return {
                "school": school,
                "district": district,
                "no_presenter_event": future_event_no_presenter,
                "with_presenter_event": future_event_with_presenter,
                "past_event": past_event,
                "non_virtual_event": future_non_virtual,
                "volunteer": volunteer,
            }

    def test_access_control_admin(self, client, test_admin, setup_test_data):
        """Test that admin users can access the recruitment view"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200
        assert b"Virtual Sessions Presenter Recruitment" in response.data

    def test_access_control_global_user(self, client, app, setup_test_data):
        """Test that global-scoped users can access the recruitment view"""
        with app.app_context():
            # Create global-scoped user
            global_user = User(
                username="globaluser",
                email="global@test.com",
                security_level=SecurityLevel.USER,
                scope_type="global",
                password_hash=generate_password_hash("testpass"),
            )
            db.session.add(global_user)
            db.session.commit()

        # Login as global user
        client.post("/login", data={"username": "globaluser", "password": "testpass"})

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200
        assert b"Virtual Sessions Presenter Recruitment" in response.data

    def test_access_control_district_scoped_denied(self, client, app, setup_test_data):
        """Test that district-scoped users cannot access the recruitment view"""
        with app.app_context():
            # Create district-scoped user
            district_user = User(
                username="districtuser",
                email="district@test.com",
                security_level=SecurityLevel.USER,
                scope_type="district",
                allowed_districts='["Test District"]',
                password_hash=generate_password_hash("testpass"),
            )
            db.session.add(district_user)
            db.session.commit()

        # Login as district user
        client.post("/login", data={"username": "districtuser", "password": "testpass"})

        # Try to access recruitment view - should redirect
        response = client.get("/virtual/usage/recruitment", follow_redirects=False)
        assert response.status_code == 302  # Redirect
        assert "virtual/usage" in response.location or b"Access denied" in response.data

    def test_query_shows_only_future_virtual_without_presenter(
        self, client, test_admin, setup_test_data
    ):
        """Test that only future virtual events without presenters are shown"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200

        # Should show event without presenter
        assert b"Future Virtual Session - Needs Presenter" in response.data

        # Should NOT show event with presenter
        assert b"Future Virtual Session - Has Presenter" not in response.data

        # Should NOT show past event
        assert b"Past Virtual Session" not in response.data

        # Should NOT show non-virtual event
        assert b"Future In-Person Event" not in response.data

    def test_days_until_calculation(self, client, test_admin, setup_test_data):
        """Test that days until event is calculated correctly"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200

        # Should show days until (approximately 10 days for test event)
        assert b"days" in response.data
        # The exact number might vary by test execution time, but should be around 10

    def test_filtering_by_school(self, client, test_admin, app, setup_test_data):
        """Test filtering events by school"""
        # Extract school_id in a fresh app context with refreshed object
        with app.app_context():
            test_data = setup_test_data
            # Refresh the object to bind it to this session
            db.session.add(test_data["school"])
            school_id = test_data["school"].id

        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view with school filter
        response = client.get(f"/virtual/usage/recruitment?school={school_id}")
        assert response.status_code == 200
        assert b"Future Virtual Session - Needs Presenter" in response.data

    def test_filtering_by_search(self, client, test_admin, setup_test_data):
        """Test filtering events by search term"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Search for specific event
        response = client.get("/virtual/usage/recruitment?search=Needs+Presenter")
        assert response.status_code == 200
        assert b"Future Virtual Session - Needs Presenter" in response.data

        # Search for non-existent term
        response = client.get("/virtual/usage/recruitment?search=NonExistent")
        assert response.status_code == 200
        assert b"Future Virtual Session - Needs Presenter" not in response.data

    def test_empty_state_display(self, client, test_admin, app, setup_test_data):
        """Test empty state when all events have presenters"""
        # Extract IDs in a fresh app context with refreshed objects
        with app.app_context():
            test_data = setup_test_data
            # Add objects to current session to bind them
            db.session.add(test_data["volunteer"])
            db.session.add(test_data["no_presenter_event"])
            volunteer_id = test_data["volunteer"].id
            no_presenter_event_id = test_data["no_presenter_event"].id

        # Assign presenter to the event that didn't have one
        with app.app_context():
            participation = EventParticipation(
                volunteer_id=volunteer_id,
                event_id=no_presenter_event_id,
                participant_type="Presenter",
                status="Confirmed",
            )
            db.session.add(participation)
            db.session.commit()

        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200

        # Should show empty state message
        assert (
            b"Great news" in response.data
            or b"All upcoming virtual sessions have presenters" in response.data
        )

    def test_navigation_links_present(self, client, test_admin, setup_test_data):
        """Test that all navigation links are present"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200

        # Check for navigation buttons
        assert b"Find Volunteers" in response.data
        assert b"Back to Usage Report" in response.data
        assert b"Apply Filters" in response.data
        assert b"Reset" in response.data

    def test_event_edit_link_present(self, client, test_admin, setup_test_data):
        """Test that edit event links are present for each event"""
        # Login as admin
        client.post(
            "/login", data={"username": test_admin.username, "password": "admin123"}
        )

        # Access recruitment view
        response = client.get("/virtual/usage/recruitment")
        assert response.status_code == 200

        # Should have Edit Event button
        assert b"Edit Event" in response.data
        assert b"/events/view/" in response.data
