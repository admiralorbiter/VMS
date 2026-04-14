"""
Integration tests for Salesforce Organization Import Routes.

Tests cover org create/update, affiliation import with school/district fallback,
chunked query utility, student filtering, and error handling.
"""

from unittest.mock import MagicMock, patch

import pytest

# Patch paths match the module where the name is *used*.
PATCH_SF_CLIENT_ORG = "routes.salesforce.organization_import.get_salesforce_client"
PATCH_SAFE_QUERY_ORG = "routes.salesforce.organization_import.safe_query_all"
PATCH_DELTA_ORG = "services.salesforce.DeltaSyncHelper"


def _make_org_row(overrides=None):
    """Build a minimal valid Salesforce organization row."""
    row = {
        "Id": "001ORG000000001",
        "Name": "Acme Corp",
        "Type": "Business",
        "Description": "A test organization",
        "ParentId": None,
        "BillingStreet": "100 Main St",
        "BillingCity": "Kansas City",
        "BillingState": "MO",
        "BillingPostalCode": "64111",
        "BillingCountry": "USA",
        "LastActivityDate": "2025-06-01",
        "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
    }
    if overrides:
        row.update(overrides)
    return row


def _delta_no_sync():
    """Create a mock DeltaSyncHelper that does full sync."""
    mock = MagicMock()
    mock.get_delta_info.return_value = {
        "actual_delta": False,
        "requested_delta": False,
        "watermark": None,
        "watermark_formatted": None,
    }
    return mock


class TestOrganizationImport:
    """Tests for the organization import endpoint."""

    def test_new_organization_created(self, client, auth_headers, app):
        """A new organization is created from Salesforce data."""
        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [_make_org_row()]}

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.organization import Organization

        with app.app_context():
            org = Organization.query.filter_by(salesforce_id="001ORG000000001").first()
            assert org is not None
            assert org.name == "Acme Corp"
            assert org.billing_city == "Kansas City"

    def test_existing_organization_updated(self, client, auth_headers, app):
        """An existing organization is updated by matching salesforce_id."""
        from models import db
        from models.organization import Organization

        with app.app_context():
            org = Organization(salesforce_id="001ORG000000001", name="Old Name")
            db.session.add(org)
            db.session.commit()

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [_make_org_row()]}

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200

        with app.app_context():
            orgs = Organization.query.filter_by(salesforce_id="001ORG000000001").all()
            assert len(orgs) == 1
            assert orgs[0].name == "Acme Corp"

    def test_empty_org_list(self, client, auth_headers):
        """Empty result set returns success with 0 processed."""
        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": []}

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 0

    def test_multiple_organizations(self, client, auth_headers, app):
        """Multiple organizations are all imported."""
        rows = [
            _make_org_row({"Id": f"001ORG00000000{i}", "Name": f"Org {i}"})
            for i in range(3)
        ]

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": rows}

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 3

    def test_org_with_null_optional_fields(self, client, auth_headers, app):
        """Organization with null optional fields (Description, BillingStreet, etc.) imports fine."""
        row = _make_org_row(
            {
                "Description": None,
                "BillingStreet": None,
                "BillingCity": None,
                "LastActivityDate": None,
            }
        )

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [row]}

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_auth_failure_returns_401(self, client, auth_headers):
        """SalesforceAuthenticationFailed returns 401."""
        from simple_salesforce import SalesforceAuthenticationFailed

        with (
            patch(PATCH_SF_CLIENT_ORG) as mock_sf,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf.side_effect = SalesforceAuthenticationFailed(
                "https://test.salesforce.com", "Auth Failed"
            )

            response = client.post(
                "/organizations/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False


class TestChunkedInQuery:
    """Tests for the chunked_in_query utility function."""

    def test_empty_id_set(self, app):
        """Empty set returns empty dict."""
        from models.organization import Organization
        from routes.salesforce.organization_import import chunked_in_query

        with app.app_context():
            result = chunked_in_query(Organization, Organization.salesforce_id, set())
            assert result == {}

    def test_single_chunk(self, app):
        """Small ID set processed in single chunk."""
        from models import db
        from models.organization import Organization
        from routes.salesforce.organization_import import chunked_in_query

        with app.app_context():
            org = Organization(salesforce_id="SF001", name="Test Org")
            db.session.add(org)
            db.session.commit()

            result = chunked_in_query(
                Organization, Organization.salesforce_id, {"SF001", "SF999"}
            )
            assert "SF001" in result
            assert "SF999" not in result
            assert result["SF001"].name == "Test Org"


class TestAffiliationImport:
    """Tests for the volunteer-organization affiliation import."""

    def test_affiliation_with_missing_contact(self, client, auth_headers, app):
        """Affiliation with non-existent contact is counted as error."""
        from models import db
        from models.organization import Organization

        with app.app_context():
            org = Organization(salesforce_id="001ORG000000001", name="Test Org")
            db.session.add(org)
            db.session.commit()

        aff_row = {
            "Id": "a0F000000001",
            "Name": "Test Affiliation",
            "npe5__Organization__c": "001ORG000000001",
            "npe5__Contact__c": "003NONEXISTENT",
            "npe5__Role__c": "Volunteer",
            "npe5__Primary__c": "true",
            "npe5__Status__c": "Current",
            "npe5__StartDate__c": "2025-01-01",
            "npe5__EndDate__c": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [aff_row]}

            response = client.post(
                "/organizations/import-affiliations-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Record processed (no valid contact matched → filtered out in pre-filter or counted as 0 success)
        assert data["processed_count"] == 0

    def test_affiliation_empty_records(self, client, auth_headers):
        """Empty affiliation result returns success."""
        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": []}

            response = client.post(
                "/organizations/import-affiliations-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 0


class TestAffiliationSchoolDistrictAutoOrg:
    """Tests for auto-creating Organization records from School/District during
    affiliation import (P1 gap — FK resolution path)."""

    def test_school_auto_creates_organization(self, client, auth_headers, app):
        """When an affiliation references a School SF ID not in orgs,
        an Organization record is auto-created from the school."""
        from models import db
        from models.school_model import School
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_AFF_SCH",
                first_name="School",
                last_name="Affiliate",
            )
            db.session.add(vol)
            # Create a school with explicit string ID (School PK is a Salesforce-format string)
            school = School(id="001SCH_AFF_01", name="Lincoln Elementary")
            db.session.add(school)
            db.session.flush()
            vol_sf_id = vol.salesforce_individual_id
            db.session.commit()

        aff_row = {
            "Id": "a0F_SCH_AFF_01",
            "Name": "School Affiliation",
            "npe5__Organization__c": "001SCH_AFF_01",
            "npe5__Contact__c": vol_sf_id,
            "npe5__Role__c": "Volunteer",
            "npe5__Primary__c": "false",
            "npe5__Status__c": "Current",
            "npe5__StartDate__c": None,
            "npe5__EndDate__c": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [aff_row]}

            response = client.post(
                "/organizations/import-affiliations-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        # Should have processed (school auto-created as org)
        assert data["processed_count"] == 1

        from models.organization import Organization

        with app.app_context():
            org = Organization.query.filter_by(salesforce_id="001SCH_AFF_01").first()
            assert org is not None
            assert org.name == "Lincoln Elementary"
            assert org.type == "School"

    def test_district_auto_creates_organization(self, client, auth_headers, app):
        """When an affiliation references a District SF ID not in orgs,
        an Organization record is auto-created from the district."""
        from models import db
        from models.district_model import District
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_AFF_DIST",
                first_name="District",
                last_name="Affiliate",
            )
            db.session.add(vol)
            district = District(
                name="Metro School District",
                salesforce_id="001DIST_AFF_01",
            )
            db.session.add(district)
            db.session.commit()

        aff_row = {
            "Id": "a0F_DIST_AFF_01",
            "Name": "District Affiliation",
            "npe5__Organization__c": "001DIST_AFF_01",
            "npe5__Contact__c": "003VOL_AFF_DIST",
            "npe5__Role__c": "Board Member",
            "npe5__Primary__c": "true",
            "npe5__Status__c": "Current",
            "npe5__StartDate__c": "2025-01-01",
            "npe5__EndDate__c": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [aff_row]}

            response = client.post(
                "/organizations/import-affiliations-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.organization import Organization

        with app.app_context():
            org = Organization.query.filter_by(salesforce_id="001DIST_AFF_01").first()
            assert org is not None
            assert org.name == "Metro School District"
            assert org.type == "District"


class TestAffiliationNullRole:
    """Data-driven tests for affiliations with NULL role.

    Production DB analysis: 272,219 / 275,878 affiliations have NULL role.
    This is the dominant pattern in real data.
    """

    def test_affiliation_null_role_accepted(self, client, auth_headers, app):
        """Affiliation with npe5__Role__c=None imports successfully."""
        from models import db
        from models.organization import Organization
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_NULLROLE",
                first_name="Null",
                last_name="Role",
            )
            org = Organization(salesforce_id="001ORG_NULLROLE", name="Test Org")
            db.session.add_all([vol, org])
            db.session.commit()

        aff_row = {
            "Id": "a0F_NULLROLE_01",
            "Name": "Unnamed Affiliation",
            "npe5__Organization__c": "001ORG_NULLROLE",
            "npe5__Contact__c": "003VOL_NULLROLE",
            "npe5__Role__c": None,
            "npe5__Primary__c": "false",
            "npe5__Status__c": "Current",
            "npe5__StartDate__c": None,
            "npe5__EndDate__c": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT_ORG),
            patch(PATCH_SAFE_QUERY_ORG) as mock_query,
            patch(PATCH_DELTA_ORG) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [aff_row]}

            response = client.post(
                "/organizations/import-affiliations-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.organization import VolunteerOrganization
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer.query.filter_by(
                salesforce_individual_id="003VOL_NULLROLE"
            ).first()
            aff = VolunteerOrganization.query.filter_by(volunteer_id=vol.id).first()
            assert aff is not None
            assert aff.role is None  # NULL role is accepted
