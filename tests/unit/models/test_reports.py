import time
from datetime import datetime, timezone

import pytest

from models import db
from models.district_model import District
from models.organization import Organization
from models.reports import DistrictEngagementReport, DistrictYearEndReport, OrganizationDetailCache, OrganizationReport, OrganizationSummaryCache


@pytest.fixture
def test_district(app):
    with app.app_context():
        district = District(salesforce_id="DIST001", name="Test District")
        db.session.add(district)
        db.session.commit()
        yield district
        # Cleanup - delete related reports first
        DistrictYearEndReport.query.filter_by(district_id=district.id).delete()
        DistrictEngagementReport.query.filter_by(district_id=district.id).delete()
        db.session.commit()
        db.session.delete(district)
        db.session.commit()


@pytest.fixture
def test_organization(app):
    with app.app_context():
        org = Organization(name="Test Organization", description="Test Description", type="Business")
        db.session.add(org)
        db.session.commit()
        yield org
        # Cleanup - delete related reports first
        OrganizationReport.query.filter_by(organization_id=org.id).delete()
        db.session.commit()
        db.session.delete(org)
        db.session.commit()


def test_district_year_end_report(app, test_district):
    with app.app_context():
        report_data = {"total_events": 50, "total_volunteers": 100, "total_students": 500}
        events_data = {"in_person": 30, "virtual": 20}

        report = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data=report_data, events_data=events_data)
        db.session.add(report)
        db.session.commit()

        assert report.id is not None
        assert str(report.district_id) == str(test_district.id)  # Convert to string for comparison
        assert report.school_year == "2024"
        assert report.host_filter == "all"
        assert report.report_data == report_data
        assert report.events_data == events_data
        assert report.last_updated is not None
        assert report.district.name == "Test District"

        # Cleanup
        db.session.delete(report)
        db.session.commit()


def test_district_engagement_report(app, test_district):
    with app.app_context():
        summary_stats = {"total_engagements": 25, "active_volunteers": 75}
        volunteers_data = [{"id": 1, "name": "Volunteer 1"}, {"id": 2, "name": "Volunteer 2"}]

        report = DistrictEngagementReport(district_id=test_district.id, school_year="2024", summary_stats=summary_stats, volunteers_data=volunteers_data)
        db.session.add(report)
        db.session.commit()

        assert report.id is not None
        assert str(report.district_id) == str(test_district.id)  # Convert to string for comparison
        assert report.school_year == "2024"
        assert report.summary_stats == summary_stats
        assert report.volunteers_data == volunteers_data
        assert report.last_updated is not None

        # Cleanup
        db.session.delete(report)
        db.session.commit()


def test_organization_report(app, test_organization):
    with app.app_context():
        summary_stats = {"total_events": 15, "total_volunteers": 30}
        in_person_events = [{"id": 1, "title": "Event 1"}, {"id": 2, "title": "Event 2"}]

        report = OrganizationReport(
            organization_id=test_organization.id, school_year="2024", summary_stats=summary_stats, in_person_events_data=in_person_events
        )
        db.session.add(report)
        db.session.commit()

        assert report.id is not None
        assert str(report.organization_id) == str(test_organization.id)  # Convert to string for comparison
        assert report.school_year == "2024"
        assert report.summary_stats == summary_stats
        assert report.in_person_events_data == in_person_events
        assert report.last_updated is not None

        # Cleanup
        db.session.delete(report)
        db.session.commit()


def test_organization_summary_cache(app):
    with app.app_context():
        organizations_data = [{"id": 1, "name": "Org 1", "event_count": 10}, {"id": 2, "name": "Org 2", "event_count": 15}]

        cache = OrganizationSummaryCache(school_year="2024", organizations_data=organizations_data)
        db.session.add(cache)
        db.session.commit()

        assert cache.id is not None
        assert cache.school_year == "2024"
        assert cache.organizations_data == organizations_data
        assert cache.last_updated is not None
        assert repr(cache) == "<OrganizationSummaryCache 2024>"

        # Cleanup
        db.session.delete(cache)
        db.session.commit()


def test_organization_detail_cache(app):
    with app.app_context():
        in_person_events = [{"id": 1, "title": "In-Person Event 1"}, {"id": 2, "title": "In-Person Event 2"}]
        virtual_events = [{"id": 3, "title": "Virtual Event 1"}]
        summary_stats = {"total_events": 3, "total_volunteers": 25}

        cache = OrganizationDetailCache(
            organization_id=1,
            school_year="2024",
            organization_name="Test Org",
            in_person_events=in_person_events,
            virtual_events=virtual_events,
            summary_stats=summary_stats,
        )
        db.session.add(cache)
        db.session.commit()

        assert cache.id is not None
        assert cache.organization_id == 1
        assert cache.school_year == "2024"
        assert cache.organization_name == "Test Org"
        assert cache.in_person_events == in_person_events
        assert cache.virtual_events == virtual_events
        assert cache.summary_stats == summary_stats
        assert cache.last_updated is not None
        assert repr(cache) == "<OrganizationDetailCache Test Org 2024>"

        # Cleanup
        db.session.delete(cache)
        db.session.commit()


def test_unique_constraints(app, test_district):
    with app.app_context():
        # Test DistrictYearEndReport unique constraint
        report1 = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data={"test": "data"})
        db.session.add(report1)
        db.session.commit()

        # Try to create duplicate
        report2 = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data={"test": "data2"})
        db.session.add(report2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

        db.session.delete(report1)
        db.session.commit()


def test_json_field_validation(app, test_district):
    with app.app_context():
        # Test with complex JSON data
        complex_data = {
            "nested": {"level1": {"level2": ["item1", "item2"], "numbers": [1, 2, 3, 4, 5]}},
            "arrays": [{"name": "Item 1", "value": 100}, {"name": "Item 2", "value": 200}],
            "booleans": [True, False, True],
            "null_values": [None, "not_null", None],
        }

        report = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data=complex_data)
        db.session.add(report)
        db.session.commit()

        assert report.report_data == complex_data
        assert report.report_data["nested"]["level1"]["level2"] == ["item1", "item2"]
        assert report.report_data["arrays"][0]["name"] == "Item 1"

        db.session.delete(report)
        db.session.commit()


def test_timestamp_behavior(app, test_district):
    with app.app_context():
        report = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data={"test": "data"})
        db.session.add(report)
        db.session.commit()

        initial_updated = report.last_updated

        # Add a small delay to ensure different timestamps
        time.sleep(0.1)

        # Update the report and manually update timestamp
        report.report_data = {"test": "updated_data"}
        report.last_updated = datetime.now(timezone.utc)
        db.session.commit()

        # last_updated should change
        assert report.last_updated > initial_updated

        # Cleanup
        db.session.delete(report)
        db.session.commit()


def test_foreign_key_relationships(app, test_district, test_organization):
    with app.app_context():
        # Test district relationship
        district_report = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data={"test": "data"})
        db.session.add(district_report)
        db.session.commit()

        assert str(district_report.district_id) == str(test_district.id)
        assert district_report.district.name == "Test District"

        # Test organization relationship
        org_report = OrganizationReport(organization_id=test_organization.id, school_year="2024", summary_stats={"test": "data"})
        db.session.add(org_report)
        db.session.commit()

        assert str(org_report.organization_id) == str(test_organization.id)
        assert org_report.organization.name == "Test Organization"

        # Cleanup
        db.session.delete(district_report)
        db.session.delete(org_report)
        db.session.commit()


def test_cache_invalidation_scenarios(app, test_district):
    with app.app_context():
        # Create initial cache
        report = DistrictYearEndReport(district_id=test_district.id, school_year="2024", host_filter="all", report_data={"version": 1})
        db.session.add(report)
        db.session.commit()

        # Simulate cache invalidation by updating
        report.report_data = {"version": 2}
        db.session.commit()

        # Verify the update
        updated_report = db.session.get(DistrictYearEndReport, report.id)
        assert updated_report.report_data["version"] == 2

        db.session.delete(report)
        db.session.commit()
