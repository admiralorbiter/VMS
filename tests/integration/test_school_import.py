"""
Integration tests for Salesforce School, District, and Class Import Routes.

Tests cover district-before-school ordering, school create/update,
TD-021 name-based reconciliation with FK migration, class import with
year parsing, and error handling.
"""

from unittest.mock import MagicMock, patch

import pytest

# Patch paths match the module where the name is *used*.
PATCH_SF_CLIENT = "routes.salesforce.school_import.get_salesforce_client"
PATCH_SAFE_QUERY = "routes.salesforce.school_import.safe_query_all"
PATCH_DELTA = "services.salesforce.DeltaSyncHelper"
# The school_levels import is called inside the function
PATCH_SCHOOL_LEVELS = "routes.management.import_data.update_school_levels"


def _delta_no_sync():
    mock = MagicMock()
    mock.get_delta_info.return_value = {
        "actual_delta": False,
        "requested_delta": False,
        "watermark": None,
        "watermark_formatted": None,
    }
    return mock


class TestSchoolImport:
    """Tests for the combined school + district import endpoint."""

    def test_district_created(self, client, auth_headers, app):
        """Districts are successfully imported from Salesforce."""
        district_row = {
            "Id": "001DIST00000001",
            "Name": "Test District",
            "School_Code_External_ID__c": "D001",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
            patch(PATCH_SCHOOL_LEVELS) as mock_levels,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            # First call: district query; second call: school query
            mock_query.side_effect = [
                {"records": [district_row]},
                {"records": []},
            ]
            mock_levels.return_value = MagicMock(json={"updated": 0})

            response = client.post(
                "/management/import-schools",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        from models.district_model import District

        with app.app_context():
            d = District.query.filter_by(salesforce_id="001DIST00000001").first()
            assert d is not None
            assert d.name == "Test District"
            assert d.district_code == "D001"

    def test_school_with_district_parent(self, client, auth_headers, app):
        """School linked to parent district via ParentId."""
        district_row = {
            "Id": "001DIST00000001",
            "Name": "Test District",
            "School_Code_External_ID__c": "D001",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }
        school_row = {
            "Id": "001SCH000000001",
            "Name": "Test Elementary",
            "ParentId": "001DIST00000001",
            "Connector_Account_Name__c": "test_elementary",
            "School_Code_External_ID__c": "S001",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
            patch(PATCH_SCHOOL_LEVELS) as mock_levels,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [district_row]},
                {"records": [school_row]},
            ]
            mock_levels.return_value = MagicMock(json={"updated": 0})

            response = client.post(
                "/management/import-schools",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        from models.school_model import School

        with app.app_context():
            school = School.query.filter_by(id="001SCH000000001").first()
            assert school is not None
            assert school.name == "Test Elementary"
            assert school.district_id is not None

    def test_school_without_district(self, client, auth_headers, app):
        """School with no ParentId gets district_id=None."""
        school_row = {
            "Id": "001SCH000000002",
            "Name": "Independent School",
            "ParentId": None,
            "Connector_Account_Name__c": None,
            "School_Code_External_ID__c": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
            patch(PATCH_SCHOOL_LEVELS) as mock_levels,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": []},  # No districts
                {"records": [school_row]},
            ]
            mock_levels.return_value = MagicMock(json={"updated": 0})

            response = client.post(
                "/management/import-schools",
                headers=auth_headers,
            )

        assert response.status_code == 200

        from models.school_model import School

        with app.app_context():
            school = School.query.filter_by(id="001SCH000000002").first()
            assert school is not None
            assert school.district_id is None

    def test_existing_school_updated(self, client, auth_headers, app):
        """Existing school (by ID) is updated, not duplicated."""
        from models import db
        from models.school_model import School

        with app.app_context():
            existing = School(id="001SCH000000001", name="Old Name")
            db.session.add(existing)
            db.session.commit()

        school_row = {
            "Id": "001SCH000000001",
            "Name": "New Name",
            "ParentId": None,
            "Connector_Account_Name__c": "new_name",
            "School_Code_External_ID__c": "S001",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
            patch(PATCH_SCHOOL_LEVELS) as mock_levels,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": []},
                {"records": [school_row]},
            ]
            mock_levels.return_value = MagicMock(json={"updated": 0})

            response = client.post(
                "/management/import-schools",
                headers=auth_headers,
            )

        assert response.status_code == 200

        with app.app_context():
            schools = School.query.filter_by(id="001SCH000000001").all()
            assert len(schools) == 1
            assert schools[0].name == "New Name"


class TestTD021SchoolReconciliation:
    """Tests for TD-021: Name-based school reconciliation with FK migration."""

    def test_name_match_migrates_fk_references(self, client, auth_headers, app):
        """
        When a school exists with a VRT* ID but same name as a Salesforce school,
        the system migrates all FK references from the old ID to the new SF ID.
        """
        from models import db
        from models.school_model import School
        from models.teacher import Teacher

        with app.app_context():
            # Pre-create a VRT school and a teacher pointing to it
            vrt_school = School(id="VRT000001", name="Lincoln Elementary")
            db.session.add(vrt_school)
            db.session.flush()

            teacher = Teacher(
                first_name="Test",
                last_name="Teacher",
                school_id="VRT000001",
            )
            db.session.add(teacher)
            db.session.commit()
            teacher_id = teacher.id

        # Now import from Salesforce with same name but different ID
        school_row = {
            "Id": "001SCH_SF_001",
            "Name": "Lincoln Elementary",
            "ParentId": None,
            "Connector_Account_Name__c": "lincoln_elementary",
            "School_Code_External_ID__c": "S_LINCOLN",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
            patch(PATCH_SCHOOL_LEVELS) as mock_levels,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": []},  # No districts
                {"records": [school_row]},
            ]
            mock_levels.return_value = MagicMock(json={"updated": 0})

            response = client.post(
                "/management/import-schools",
                headers=auth_headers,
            )

        assert response.status_code == 200

        with app.app_context():
            # VRT school should be gone
            old = School.query.filter_by(id="VRT000001").first()
            assert old is None

            # New SF school should exist
            new_school = School.query.filter_by(id="001SCH_SF_001").first()
            assert new_school is not None
            assert new_school.name == "Lincoln Elementary"

            # Teacher FK should point to new ID
            teacher = db.session.get(Teacher, teacher_id)
            assert teacher.school_id == "001SCH_SF_001"


class TestDistrictOnlyImport:
    """Tests for the district-only import endpoint."""

    def test_district_only_endpoint_exists(self, client, auth_headers):
        """District-only endpoint exists and accepts POST requests.

        District import logic is fully tested via import_schools; this just
        verifies the route is registered and doesn't return 404.
        """
        with patch(PATCH_SF_CLIENT), patch(PATCH_SAFE_QUERY) as mock_query:

            mock_query.return_value = {"records": []}

            response = client.post(
                "/management/import-districts",
                headers=auth_headers,
                follow_redirects=True,
            )

        # Endpoint should not return 404 or 405
        assert response.status_code not in (404, 405)


class TestClassImport:
    """Tests for the class import endpoint."""

    def test_new_class_created(self, client, auth_headers, app):
        """New class is created with year parsed from Salesforce."""
        from models import db
        from models.school_model import School

        with app.app_context():
            school = School(id="001SCH000000001", name="Test School")
            db.session.add(school)
            db.session.commit()

        class_row = {
            "Id": "a01CLASS0000001",
            "Name": "Grade 9 - 2025",
            "School__c": "001SCH000000001",
            "Class_Year_Number__c": "2025",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [class_row]}

            response = client.post(
                "/management/import-classes",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.class_model import Class

        with app.app_context():
            cls = Class.query.filter_by(salesforce_id="a01CLASS0000001").first()
            assert cls is not None
            assert cls.name == "Grade 9 - 2025"
            assert cls.class_year == 2025

    def test_existing_class_updated(self, client, auth_headers, app):
        """Existing class (by salesforce_id) is updated."""
        from models import db
        from models.class_model import Class
        from models.school_model import School

        with app.app_context():
            school = School(id="001SCH000000001", name="Test School")
            db.session.add(school)
            db.session.flush()

            cls = Class(
                salesforce_id="a01CLASS0000001",
                name="Old Name",
                school_salesforce_id="001SCH000000001",
                class_year=2024,
            )
            db.session.add(cls)
            db.session.commit()

        class_row = {
            "Id": "a01CLASS0000001",
            "Name": "Updated Name",
            "School__c": "001SCH000000001",
            "Class_Year_Number__c": "2025",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [class_row]}

            response = client.post(
                "/management/import-classes",
                headers=auth_headers,
            )

        assert response.status_code == 200

        with app.app_context():
            cls = Class.query.filter_by(salesforce_id="a01CLASS0000001").first()
            assert cls.name == "Updated Name"
            assert cls.class_year == 2025

    def test_invalid_class_year_recorded_as_error(self, client, auth_headers, app):
        """Invalid Class_Year_Number__c causes an error for that record."""
        class_row = {
            "Id": "a01CLASS_BAD",
            "Name": "Bad Year Class",
            "School__c": "001SCH000000001",
            "Class_Year_Number__c": "not-a-number",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [class_row]}

            response = client.post(
                "/management/import-classes",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["error_count"] == 1
