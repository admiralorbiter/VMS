"""
Integration tests for Organization Reporting Dashboard (TC-720 to TC-722).

Tests organization participation totals, unique counts, and volunteer drilldowns.
"""

from datetime import datetime, timedelta

import pytest

from models import Event, Volunteer, db
from models.organization import Organization, VolunteerOrganization
from models.volunteer import EventParticipation, VolunteerStatus


class TestOrganizationReporting:
    """
    Integration tests for Organization Reporting Dashboard (TC-720 to TC-722).
    """

    @pytest.fixture
    def reporting_data(self, client):
        """
        Seed data for organization reporting tests based on Test Pack 6 specs.
        
        Creates:
        - TechCorp: 10 total hours (highest)
        - StartupCo: 5 total hours
        - SmallBiz: 3 total hours
        """
        # Create Organizations
        techcorp = Organization(name="TechCorp", type="Corporate")
        startupco = Organization(name="StartupCo", type="Startup")
        smallbiz = Organization(name="SmallBiz", type="Small Business")

        db.session.add_all([techcorp, startupco, smallbiz])
        db.session.commit()

        # Create Volunteers
        v1 = Volunteer(
            first_name="Alice", last_name="Tech", status=VolunteerStatus.ACTIVE
        )
        v2 = Volunteer(
            first_name="Bob", last_name="Tech", status=VolunteerStatus.ACTIVE
        )
        v3 = Volunteer(
            first_name="Charlie", last_name="Startup", status=VolunteerStatus.ACTIVE
        )
        v4 = Volunteer(
            first_name="Diana", last_name="Small", status=VolunteerStatus.ACTIVE
        )

        db.session.add_all([v1, v2, v3, v4])
        db.session.commit()

        # Link Volunteers to Organizations
        vol_org1 = VolunteerOrganization(
            volunteer_id=v1.id, organization_id=techcorp.id, is_primary=True
        )
        vol_org2 = VolunteerOrganization(
            volunteer_id=v2.id, organization_id=techcorp.id, is_primary=True
        )
        vol_org3 = VolunteerOrganization(
            volunteer_id=v3.id, organization_id=startupco.id, is_primary=True
        )
        vol_org4 = VolunteerOrganization(
            volunteer_id=v4.id, organization_id=smallbiz.id, is_primary=True
        )

        db.session.add_all([vol_org1, vol_org2, vol_org3, vol_org4])
        db.session.commit()

        # Create Events (within current school year)
        event = Event(title="Test Event", start_date=datetime.now() - timedelta(days=10))
        db.session.add(event)
        db.session.commit()

        # Log Hours:
        # TechCorp: Alice=6h + Bob=4h = 10h total (highest)
        # StartupCo: Charlie=5h
        # SmallBiz: Diana=3h
        self._add_participation(v1, 6, event)
        self._add_participation(v2, 4, event)
        self._add_participation(v3, 5, event)
        self._add_participation(v4, 3, event)

        return {
            "techcorp": techcorp,
            "startupco": startupco,
            "smallbiz": smallbiz,
            "v1": v1,
            "v2": v2,
            "v3": v3,
            "v4": v4,
            "event": event,
        }

    def _add_participation(self, volunteer, hours, event):
        """Helper to add event participation."""
        p = EventParticipation(
            volunteer_id=volunteer.id,
            event_id=event.id,
            status="Attended",
            delivery_hours=float(hours),
        )
        db.session.add(p)
        db.session.commit()

    def test_organization_totals_ranking(self, client, reporting_data):
        """
        TC-720: Verify organizations are ranked by total hours descending.
        Expected: TechCorp (10h) > StartupCo (5h) > SmallBiz (3h)
        """
        from sqlalchemy import desc, func

        results = (
            db.session.query(
                Organization,
                func.sum(EventParticipation.delivery_hours).label("total_hours"),
            )
            .join(
                VolunteerOrganization,
                Organization.id == VolunteerOrganization.organization_id,
            )
            .join(Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id)
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .filter(EventParticipation.status.in_(["Attended", "Completed", "Successfully Completed"]))
            .group_by(Organization.id)
            .order_by(desc("total_hours"))
            .all()
        )

        # Assert ordering
        assert len(results) == 3
        assert results[0][0].name == "TechCorp" and results[0].total_hours == 10
        assert results[1][0].name == "StartupCo" and results[1].total_hours == 5
        assert results[2][0].name == "SmallBiz" and results[2].total_hours == 3

    def test_unique_organization_count(self, client, reporting_data):
        """
        TC-721: Verify unique organization count is correct.
        Expected: 3 unique organizations with volunteer participation.
        """
        from sqlalchemy import func

        unique_org_count = (
            db.session.query(func.count(func.distinct(Organization.id)))
            .join(
                VolunteerOrganization,
                Organization.id == VolunteerOrganization.organization_id,
            )
            .join(Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id)
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .filter(EventParticipation.status.in_(["Attended", "Completed", "Successfully Completed"]))
            .scalar()
        )

        assert unique_org_count == 3

    def test_organization_drilldown_volunteers(self, client, reporting_data):
        """
        TC-722: Verify organization drilldown lists volunteers correctly.
        Expected: TechCorp drilldown shows Alice (6h) and Bob (4h).
        """
        from sqlalchemy import desc, func

        techcorp = reporting_data["techcorp"]

        # Query volunteers for TechCorp
        volunteer_data = (
            db.session.query(
                Volunteer,
                func.count(func.distinct(Event.id)).label("event_count"),
                func.sum(EventParticipation.delivery_hours).label("total_hours"),
            )
            .join(
                VolunteerOrganization,
                Volunteer.id == VolunteerOrganization.volunteer_id,
            )
            .join(EventParticipation, Volunteer.id == EventParticipation.volunteer_id)
            .join(Event, EventParticipation.event_id == Event.id)
            .filter(
                VolunteerOrganization.organization_id == techcorp.id,
                EventParticipation.status.in_(["Attended", "Completed", "Successfully Completed"]),
            )
            .group_by(Volunteer.id)
            .order_by(desc("total_hours"))
            .all()
        )

        # Assert volunteers are listed correctly
        assert len(volunteer_data) == 2

        # Alice should be first (6 hours)
        assert volunteer_data[0][0].first_name == "Alice"
        assert volunteer_data[0].total_hours == 6

        # Bob should be second (4 hours)
        assert volunteer_data[1][0].first_name == "Bob"
        assert volunteer_data[1].total_hours == 4

        # Total hours for TechCorp should be 10
        total_hours = sum(v.total_hours for v in volunteer_data)
        assert total_hours == 10
