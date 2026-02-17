"""
Integration tests for Organization Report Excel export routes.

Tests the actual HTTP endpoints for Excel export, specifically verifying
that all school_year parameter values (including 'all_time') are handled
without errors. These tests assert status_code == 200, NOT the permissive
[200, 404, 500] pattern, so server errors will fail.
"""

from datetime import datetime, timedelta

import pytest

from models import db
from models.event import Event, EventType
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, Volunteer, VolunteerStatus


@pytest.fixture
def org_excel_data(client):
    """
    Seed minimal data for organization Excel export tests.

    Creates one organization with one volunteer who attended one event,
    enough to exercise all Excel export code paths.
    """
    # Create organization
    org = Organization(name="Excel Test Corp", type="Corporate")
    db.session.add(org)
    db.session.commit()

    # Create volunteer
    vol = Volunteer(
        first_name="Jane",
        last_name="Exporter",
        status=VolunteerStatus.ACTIVE,
    )
    db.session.add(vol)
    db.session.commit()

    # Link volunteer to organization
    vol_org = VolunteerOrganization(
        volunteer_id=vol.id, organization_id=org.id, is_primary=True
    )
    db.session.add(vol_org)
    db.session.commit()

    # Create event within current school year
    event = Event(
        title="Excel Test Event",
        start_date=datetime.now() - timedelta(days=10),
        type=EventType.IN_PERSON,
    )
    db.session.add(event)
    db.session.commit()

    # Add participation
    participation = EventParticipation(
        volunteer_id=vol.id,
        event_id=event.id,
        status="Attended",
        delivery_hours=3.0,
    )
    db.session.add(participation)
    db.session.commit()

    yield {"org": org, "vol": vol, "event": event}


class TestOrganizationReportDetailExcel:
    """Tests for /reports/organization/report/detail/<id>/excel endpoint."""

    def test_detail_excel_default_school_year(
        self, client, auth_headers, org_excel_data
    ):
        """Excel export with default school year should return 200 with xlsx content."""
        org = org_excel_data["org"]
        response = client.get(
            f"/reports/organization/report/detail/{org.id}/excel",
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            f"Response: {response.data[:500]}"
        )
        assert (
            "spreadsheetml" in response.content_type
            or "application/vnd" in response.content_type
        )

    def test_detail_excel_all_time(self, client, auth_headers, org_excel_data):
        """
        Excel export with school_year=all_time should return 200.

        This is the exact scenario that caused the ValueError crash:
        get_school_year_date_range('all_time') tried int('al').
        """
        org = org_excel_data["org"]
        response = client.get(
            f"/reports/organization/report/detail/{org.id}/excel?school_year=all_time",
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"Expected 200 for all_time export, got {response.status_code}. "
            f"Response: {response.data[:500]}"
        )

    def test_detail_excel_specific_school_year(
        self, client, auth_headers, org_excel_data
    ):
        """Excel export with a specific school year should return 200."""
        org = org_excel_data["org"]
        response = client.get(
            f"/reports/organization/report/detail/{org.id}/excel?school_year=2526",
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"Expected 200 for specific year export, got {response.status_code}. "
            f"Response: {response.data[:500]}"
        )

    def test_detail_excel_invalid_org_returns_404(self, client, auth_headers):
        """Excel export for non-existent org should return 404."""
        response = client.get(
            "/reports/organization/report/detail/999999/excel",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestOrganizationReportSummaryExcel:
    """Tests for /reports/organization/report/excel endpoint."""

    def test_summary_excel_default_school_year(
        self, client, auth_headers, org_excel_data
    ):
        """Summary Excel export with default school year should return 200."""
        response = client.get(
            "/reports/organization/report/excel",
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            f"Response: {response.data[:500]}"
        )

    def test_summary_excel_all_time(self, client, auth_headers, org_excel_data):
        """
        Summary Excel export with school_year=all_time should return 200.

        The summary report also calls get_school_year_date_range, so it's
        vulnerable to the same bug if all_time is ever passed.
        """
        response = client.get(
            "/reports/organization/report/excel?school_year=all_time",
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"Expected 200 for summary all_time export, got {response.status_code}. "
            f"Response: {response.data[:500]}"
        )
