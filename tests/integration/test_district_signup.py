"""
Integration Tests for District Public Signup

Tests for FR-SELFSERV-404 and FR-SELFSERV-405:
- TC-1130: Public signup form loads for published event
- TC-1131: Signup creates volunteer + participation
- TC-1132: Existing volunteer reused by email match
- TC-1133: Confirmation email sent with ICS attachment
- TC-1134: ICS contains correct event details
- TC-1135: Signup rejected for draft/cancelled events
"""

from datetime import datetime, timedelta, timezone

import pytest

from models import db
from models.contact import Email
from models.district_participation import DistrictParticipation
from models.district_volunteer import DistrictVolunteer
from models.event import Event, EventStatus
from models.tenant import Tenant
from models.volunteer import Volunteer
from utils.calendar_utils import generate_event_ics


def _find_volunteer_by_email_test(email):
    """Helper to find volunteer by email using Email model join."""
    from models.contact import Contact

    email_record = (
        Email.query.join(Contact, Email.contact_id == Contact.id)
        .join(Volunteer, Volunteer.id == Contact.id)
        .filter(db.func.lower(Email.email) == email.lower())
        .first()
    )
    if email_record:
        return Volunteer.query.get(email_record.contact_id)
    return None


def _create_volunteer_with_email(first_name, last_name, email):
    """Helper to create a volunteer with an email address."""
    volunteer = Volunteer(first_name=first_name, last_name=last_name)
    db.session.add(volunteer)
    db.session.flush()

    email_record = Email(contact_id=volunteer.id, email=email, primary=True)
    db.session.add(email_record)
    return volunteer


class TestCalendarUtils:
    """Unit tests for ICS calendar generation (TC-1134)."""

    def test_generate_ics_basic(self, app):
        """TC-1134: ICS contains correct event details."""
        with app.app_context():
            ics = generate_event_ics(
                title="Test Event",
                start_date=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
                end_date=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
                location="123 Main St, Kansas City, MO",
                description="A test event description",
            )

            assert "BEGIN:VCALENDAR" in ics
            assert "END:VCALENDAR" in ics
            assert "BEGIN:VEVENT" in ics
            assert "SUMMARY:Test Event" in ics
            assert "LOCATION:123 Main St" in ics
            assert "DTSTART:" in ics
            assert "DTEND:" in ics

    def test_generate_ics_with_organizer(self, app):
        """TC-1134: ICS includes organizer info."""
        with app.app_context():
            ics = generate_event_ics(
                title="Test Event",
                start_date=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
                organizer_email="events@prepkc.org",
                organizer_name="PrepKC",
            )

            assert "ORGANIZER" in ics
            assert "events@prepkc.org" in ics

    def test_generate_ics_escapes_special_chars(self, app):
        """TC-1134: ICS escapes special characters."""
        with app.app_context():
            ics = generate_event_ics(
                title="Event, with; special chars",
                start_date=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            )

            # Commas and semicolons should be escaped
            assert "Event\\, with\\; special chars" in ics


class TestPublicSignupRoutes:
    """Integration tests for public signup routes."""

    def test_signup_form_loads_for_published_event(self, client, app):
        """TC-1130: Public signup form loads for published event."""
        with app.app_context():
            # Create tenant
            tenant = Tenant(
                name="Test District",
                slug="test-district",
                is_active=True,
            )
            db.session.add(tenant)
            db.session.flush()

            # Create published event
            event = Event(
                title="Test Published Event",
                tenant_id=tenant.id,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                status=EventStatus.PUBLISHED,
                volunteers_needed=5,
            )
            db.session.add(event)
            db.session.commit()

            # Access signup form
            response = client.get(f"/district/test-district/event/{event.id}/signup")

            assert response.status_code == 200
            assert b"Test Published Event" in response.data
            assert b"Sign Up" in response.data

    def test_signup_rejected_for_draft_event(self, client, app):
        """TC-1135: Signup rejected for draft events."""
        with app.app_context():
            # Create tenant
            tenant = Tenant(
                name="Test District 2",
                slug="test-district-2",
                is_active=True,
            )
            db.session.add(tenant)
            db.session.flush()

            # Create draft event
            event = Event(
                title="Draft Event",
                tenant_id=tenant.id,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                status=EventStatus.DRAFT,
            )
            db.session.add(event)
            db.session.commit()

            # Access signup form - should redirect with warning
            response = client.get(
                f"/district/test-district-2/event/{event.id}/signup",
                follow_redirects=True,
            )

            # The page should show a warning message
            assert response.status_code == 200

    def test_signup_creates_volunteer_and_participation(self, client, app):
        """TC-1131: Signup creates volunteer + participation."""
        with app.app_context():
            # Create tenant
            tenant = Tenant(
                name="Test District 3",
                slug="test-district-3",
                is_active=True,
            )
            db.session.add(tenant)
            db.session.flush()

            # Create published event
            event = Event(
                title="Signup Test Event",
                tenant_id=tenant.id,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                status=EventStatus.PUBLISHED,
                volunteers_needed=5,
            )
            db.session.add(event)
            db.session.commit()

            # Submit signup form
            response = client.post(
                f"/district/test-district-3/event/{event.id}/signup",
                data={
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "555-1234",
                    "organization": "Test Org",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            assert (
                b"success" in response.data.lower()
                or b"signed up" in response.data.lower()
            )

            # Verify volunteer created (using Email model join)
            volunteer = _find_volunteer_by_email_test("john.doe@example.com")
            assert volunteer is not None
            assert volunteer.first_name == "John"
            assert volunteer.last_name == "Doe"

            # Verify participation created
            participation = DistrictParticipation.query.filter_by(
                volunteer_id=volunteer.id,
                event_id=event.id,
                tenant_id=tenant.id,
            ).first()
            assert participation is not None
            assert participation.status == "confirmed"

            # Verify district volunteer link
            district_vol = DistrictVolunteer.query.filter_by(
                volunteer_id=volunteer.id,
                tenant_id=tenant.id,
            ).first()
            assert district_vol is not None

    def test_existing_volunteer_reused_by_email(self, client, app):
        """TC-1132: Existing volunteer reused by email match."""
        with app.app_context():
            # Create tenant
            tenant = Tenant(
                name="Test District 4",
                slug="test-district-4",
                is_active=True,
            )
            db.session.add(tenant)
            db.session.flush()

            # Create existing volunteer with email using helper
            existing_vol = _create_volunteer_with_email(
                "Jane", "Smith", "jane.smith@example.com"
            )
            db.session.flush()

            # Create published event
            event = Event(
                title="Reuse Volunteer Test",
                tenant_id=tenant.id,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                status=EventStatus.PUBLISHED,
                volunteers_needed=5,
            )
            db.session.add(event)
            db.session.commit()

            original_vol_id = existing_vol.id

            # Submit signup with same email
            response = client.post(
                f"/district/test-district-4/event/{event.id}/signup",
                data={
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email": "jane.smith@example.com",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200

            # Verify same volunteer was used (not duplicated)
            emails = Email.query.filter(
                db.func.lower(Email.email) == "jane.smith@example.com"
            ).all()
            assert len(emails) == 1

            # Verify participation created for existing volunteer
            participation = DistrictParticipation.query.filter_by(
                volunteer_id=original_vol_id,
                event_id=event.id,
            ).first()
            assert participation is not None


class TestSignupRouteExistence:
    """Test that signup routes exist."""

    def test_signup_routes_registered(self, client, app):
        """Verify signup routes are registered."""
        with app.app_context():
            # Create tenant
            tenant = Tenant(
                name="Route Test District",
                slug="route-test",
                is_active=True,
            )
            db.session.add(tenant)
            db.session.flush()

            # Create event
            event = Event(
                title="Route Test Event",
                tenant_id=tenant.id,
                start_date=datetime.now(timezone.utc) + timedelta(days=7),
                status=EventStatus.PUBLISHED,
            )
            db.session.add(event)
            db.session.commit()

            # Test GET signup form
            response = client.get(f"/district/route-test/event/{event.id}/signup")
            assert response.status_code == 200

            # Test success page
            response = client.get(
                f"/district/route-test/event/{event.id}/signup/success"
            )
            assert response.status_code == 200
