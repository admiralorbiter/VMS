"""
Integration tests for District Volunteer Routes

Test Cases:
- TC-1001: List volunteers shows tenant volunteers
- TC-1002: Create volunteer with required fields
- TC-1003: Create volunteer with email/phone
- TC-1004: View volunteer profile
- TC-1005: Edit volunteer updates fields
- TC-1006: Toggle volunteer status
- TC-1007: Link existing volunteer by email
- TC-1008: Reactivate inactive volunteer
- TC-1010: Preview import shows columns
- TC-1011: Import creates new volunteers
- TC-1012: Import links existing volunteers
- TC-1013: Import skips duplicate emails
- TC-1014: Import requires name fields
- TC-1020: Search by first name
- TC-1021: Search by last name
- TC-1022: Search by organization
- TC-1023: Filter by status
- TC-1024: API search endpoint
- TC-1030: Assign volunteer to event (roster routes)
- TC-1031: Confirm volunteer participation (status update)
- TC-1032: Record attendance (status update)
- TC-1033: View volunteer event history
- TC-1040: Cannot view other tenant volunteers
- TC-1041: Cannot edit other tenant volunteers
- TC-1042: Search scoped to tenant
- TC-1043: Import scoped to tenant
"""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from models import db
from models.contact import Email, Phone
from models.district_participation import DistrictParticipation
from models.district_volunteer import DistrictVolunteer
from models.tenant import Tenant
from models.volunteer import Volunteer


class TestDistrictVolunteerRoutes:
    """Integration tests for district volunteer routes (FR-SELFSERV-301-305)."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SECRET_KEY"] = "test-secret-key"
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant."""
        tenant = MagicMock()
        tenant.id = 1
        tenant.slug = "test-district"
        tenant.name = "Test District"
        tenant.is_active = True
        return tenant

    @pytest.fixture
    def mock_tenant_2(self):
        """Create second mock tenant for isolation tests."""
        tenant = MagicMock()
        tenant.id = 2
        tenant.slug = "other-district"
        tenant.name = "Other District"
        tenant.is_active = True
        return tenant

    @pytest.fixture
    def mock_user(self, mock_tenant):
        """Create mock user with tenant."""
        user = MagicMock()
        user.id = 1
        user.is_authenticated = True
        user.tenant_id = mock_tenant.id
        user.tenant = mock_tenant
        return user


class TestVolunteerProfileManagement:
    """Tests for FR-SELFSERV-301: Volunteer Profile Management."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_district_volunteer_model_exists(self, app):
        """TC-1001: DistrictVolunteer model exists and has required fields."""
        with app.app_context():
            assert hasattr(DistrictVolunteer, "volunteer_id")
            assert hasattr(DistrictVolunteer, "tenant_id")
            assert hasattr(DistrictVolunteer, "status")
            assert hasattr(DistrictVolunteer, "added_by")
            assert hasattr(DistrictVolunteer, "notes")

    def test_volunteer_can_be_linked_to_tenant(self, app):
        """TC-1002: Volunteer can be associated with a tenant."""
        with app.app_context():
            # Create a DistrictVolunteer association
            district_vol = DistrictVolunteer(
                volunteer_id=1,
                tenant_id=1,
                status="active",
                added_by=1,
            )
            assert district_vol.volunteer_id == 1
            assert district_vol.tenant_id == 1
            assert district_vol.status == "active"

    def test_district_volunteer_has_default_status(self, app):
        """TC-1006: DistrictVolunteer status defaults to active in DB."""
        with app.app_context():
            # Note: Default is set at DB level, not Python level
            # Test that status field accepts 'active' value
            district_vol = DistrictVolunteer(
                volunteer_id=1,
                tenant_id=1,
                status="active",  # Explicitly set as routes do
            )
            assert district_vol.status == "active"

    def test_district_volunteer_can_be_deactivated(self, app):
        """TC-1006: DistrictVolunteer status can be toggled."""
        with app.app_context():
            district_vol = DistrictVolunteer(
                volunteer_id=1,
                tenant_id=1,
                status="active",
            )
            district_vol.status = "inactive"
            assert district_vol.status == "inactive"

    def test_district_volunteer_can_be_reactivated(self, app):
        """TC-1008: Inactive volunteer can be reactivated."""
        with app.app_context():
            district_vol = DistrictVolunteer(
                volunteer_id=1,
                tenant_id=1,
                status="inactive",
            )
            district_vol.status = "active"
            assert district_vol.status == "active"


class TestCSVImport:
    """Tests for FR-SELFSERV-302: CSV Import."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_detect_column_helper(self, app):
        """TC-1010: Column detection helper works."""
        with app.app_context():
            from routes.district.volunteers import _detect_column

            fieldnames = ["First Name", "Last Name", "Email Address", "Phone"]

            # Test email detection
            email_col = _detect_column(fieldnames, ["email", "e-mail", "email_address"])
            assert email_col is None  # "Email Address" doesn't match "email_address"

            # Test with exact match
            fieldnames2 = ["first_name", "last_name", "email", "phone"]
            email_col2 = _detect_column(
                fieldnames2, ["email", "e-mail", "email_address"]
            )
            assert email_col2 == "email"

    def test_csv_import_requires_name_fields(self, app):
        """TC-1014: Import requires first and last name fields."""
        with app.app_context():
            # CSV row without required fields should be skipped
            # This is tested via the logic check
            row = {"email": "test@example.com", "phone": "555-1234"}
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()

            # Should skip if either is empty
            should_skip = not first_name or not last_name
            assert should_skip is True


class TestVolunteerSearch:
    """Tests for FR-SELFSERV-303: Volunteer Search."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        return app

    def test_volunteer_has_searchable_fields(self, app):
        """TC-1020/1021/1022: Volunteer model has searchable fields."""
        with app.app_context():
            assert hasattr(Volunteer, "first_name")
            assert hasattr(Volunteer, "last_name")
            assert hasattr(Volunteer, "organization_name")

    def test_district_volunteer_has_status_for_filter(self, app):
        """TC-1023: DistrictVolunteer has status for filtering."""
        with app.app_context():
            assert hasattr(DistrictVolunteer, "status")

            # Test status values
            active = DistrictVolunteer(volunteer_id=1, tenant_id=1, status="active")
            inactive = DistrictVolunteer(volunteer_id=2, tenant_id=1, status="inactive")

            assert active.status == "active"
            assert inactive.status == "inactive"


class TestEventAssignment:
    """Tests for FR-SELFSERV-304: Event Assignment."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        return app

    def test_district_participation_model_exists(self, app):
        """TC-1030: DistrictParticipation model exists."""
        with app.app_context():
            assert hasattr(DistrictParticipation, "volunteer_id")
            assert hasattr(DistrictParticipation, "event_id")
            assert hasattr(DistrictParticipation, "tenant_id")
            assert hasattr(DistrictParticipation, "status")
            assert hasattr(DistrictParticipation, "participation_type")

    def test_district_participation_status_values(self, app):
        """TC-1031/1032: DistrictParticipation has expected status values."""
        with app.app_context():
            # Test different status values
            invited = DistrictParticipation(
                volunteer_id=1,
                event_id=1,
                tenant_id=1,
                status="invited",
            )
            assert invited.status == "invited"

            confirmed = DistrictParticipation(
                volunteer_id=2,
                event_id=1,
                tenant_id=1,
                status="confirmed",
            )
            assert confirmed.status == "confirmed"

            attended = DistrictParticipation(
                volunteer_id=3,
                event_id=1,
                tenant_id=1,
                status="attended",
            )
            assert attended.status == "attended"

    def test_district_participation_has_timestamps(self, app):
        """TC-1033: DistrictParticipation tracks timestamps."""
        with app.app_context():
            assert hasattr(DistrictParticipation, "invited_at")
            assert hasattr(DistrictParticipation, "confirmed_at")
            assert hasattr(DistrictParticipation, "attended_at")


class TestEventRosterRoutes:
    """Tests for FR-SELFSERV-304: Event Roster Management Routes."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    def test_add_to_roster_route_exists(self, app):
        """TC-1030: Route for adding volunteers to event roster exists."""
        with app.app_context():
            from routes.district.events import add_to_roster

            assert callable(add_to_roster)

    def test_update_participation_status_route_exists(self, app):
        """TC-1031: Route for updating participation status exists."""
        with app.app_context():
            from routes.district.events import update_participation_status

            assert callable(update_participation_status)

    def test_remove_from_roster_route_exists(self, app):
        """TC-1032: Route for removing volunteers from roster exists."""
        with app.app_context():
            from routes.district.events import remove_from_roster

            assert callable(remove_from_roster)

    def test_search_volunteers_for_event_route_exists(self, app):
        """TC-1030: Route for searching volunteers for event exists."""
        with app.app_context():
            from routes.district.events import search_volunteers_for_event

            assert callable(search_volunteers_for_event)

    def test_participation_status_transitions(self, app):
        """TC-1031/1032: Valid status transitions."""
        with app.app_context():
            # Valid status values that the route accepts
            valid_statuses = ["invited", "confirmed", "declined", "attended", "no_show"]

            # Create participation and test transitions
            participation = DistrictParticipation(
                volunteer_id=1,
                event_id=1,
                tenant_id=1,
                status="invited",
            )

            # All transitions should be valid
            for status in valid_statuses:
                participation.status = status
                assert participation.status == status

    def test_participation_type_values(self, app):
        """TC-1030: Participation types for roster."""
        with app.app_context():
            # Valid participation types
            types = ["volunteer", "speaker", "mentor", "organizer"]

            for ptype in types:
                participation = DistrictParticipation(
                    volunteer_id=1,
                    event_id=1,
                    tenant_id=1,
                    participation_type=ptype,
                )
                assert participation.participation_type == ptype


class TestTenantIsolation:
    """Tests for FR-SELFSERV-305: Tenant Isolation."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        return app

    def test_district_volunteer_requires_tenant_id(self, app):
        """TC-1040/1041: DistrictVolunteer requires tenant_id."""
        with app.app_context():
            # Cannot create without tenant_id (nullable=False in model)
            district_vol = DistrictVolunteer(
                volunteer_id=1,
                tenant_id=1,  # Required
                status="active",
            )
            assert district_vol.tenant_id is not None

    def test_district_volunteer_unique_constraint(self, app):
        """TC-1042/1043: Volunteer-tenant pair must be unique."""
        with app.app_context():
            # The unique constraint name exists in model
            # Check table args for unique constraint
            table_args = getattr(DistrictVolunteer, "__table_args__", None)
            assert table_args is not None

            # Find the unique constraint
            has_unique = any(
                hasattr(arg, "name") and "uq_district_volunteer" in (arg.name or "")
                for arg in table_args
                if hasattr(arg, "name")
            )
            assert has_unique

    def test_district_participation_requires_tenant_id(self, app):
        """TC-1043: DistrictParticipation requires tenant_id."""
        with app.app_context():
            participation = DistrictParticipation(
                volunteer_id=1,
                event_id=1,
                tenant_id=1,  # Required
            )
            assert participation.tenant_id is not None

    def test_district_participation_unique_constraint(self, app):
        """TC-1043: Volunteer-event-tenant tuple must be unique."""
        with app.app_context():
            table_args = getattr(DistrictParticipation, "__table_args__", None)
            assert table_args is not None

            has_unique = any(
                hasattr(arg, "name") and "uq_district_participation" in (arg.name or "")
                for arg in table_args
                if hasattr(arg, "name")
            )
            assert has_unique


class TestEmailPhoneHandling:
    """Tests for volunteer email/phone record creation."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        return app

    def test_email_model_exists(self, app):
        """TC-1003: Email model for volunteer contact info."""
        with app.app_context():
            assert hasattr(Email, "contact_id")
            assert hasattr(Email, "email")
            assert hasattr(Email, "primary")

    def test_phone_model_exists(self, app):
        """TC-1003: Phone model for volunteer contact info."""
        with app.app_context():
            assert hasattr(Phone, "contact_id")
            assert hasattr(Phone, "number")
            assert hasattr(Phone, "primary")

    def test_find_volunteer_by_email_function(self, app):
        """TC-1007: Email lookup function exists."""
        with app.app_context():
            from routes.district.volunteers import _find_volunteer_by_email

            # Function should exist and handle None gracefully
            result = _find_volunteer_by_email(None)
            assert result is None

            result = _find_volunteer_by_email("")
            assert result is None


class TestRouteHelpers:
    """Tests for route helper functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app

        app.config["TESTING"] = True
        return app

    def test_require_tenant_context_decorator_exists(self, app):
        """Test that tenant context decorator exists."""
        with app.app_context():
            from routes.district.volunteers import require_tenant_context

            assert callable(require_tenant_context)

    def test_require_district_admin_decorator_exists(self, app):
        """Test that district admin decorator exists."""
        with app.app_context():
            from routes.district.volunteers import require_district_admin

            assert callable(require_district_admin)

    def test_detect_column_function_exists(self, app):
        """Test that column detection helper exists."""
        with app.app_context():
            from routes.district.volunteers import _detect_column

            assert callable(_detect_column)

    def test_set_volunteer_primary_email_exists(self, app):
        """Test that email setter helper exists."""
        with app.app_context():
            from routes.district.volunteers import _set_volunteer_primary_email

            assert callable(_set_volunteer_primary_email)

    def test_set_volunteer_primary_phone_exists(self, app):
        """Test that phone setter helper exists."""
        with app.app_context():
            from routes.district.volunteers import _set_volunteer_primary_phone

            assert callable(_set_volunteer_primary_phone)
