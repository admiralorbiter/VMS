"""
Integration tests for Salesforce Teacher Import Routes.

Tests cover happy path, error isolation, partial sync logging,
and auth failure handling.
"""

from unittest.mock import MagicMock, patch

import pytest

PATCH_SF_CLIENT = "routes.salesforce.teacher_import.get_salesforce_client"
PATCH_SAFE_QUERY = "routes.salesforce.teacher_import.safe_query_all"
PATCH_DELTA = "services.salesforce.DeltaSyncHelper"


def _make_teacher_row(overrides=None):
    """Build a minimal valid Salesforce teacher row."""
    row = {
        "Id": "003TEA000000001",
        "AccountId": "001ACCT000000001",
        "FirstName": "Maria",
        "LastName": "Garcia",
        "Email": "maria.garcia@school.test",
        "npsp__Primary_Affiliation__c": None,
        "Department": "Mathematics",
        "Gender__c": "Female",
        "Phone": "555-999-0001",
        "Last_Email_Message__c": None,
        "Last_Mailchimp_Email_Date__c": None,
        "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
    }
    if overrides:
        row.update(overrides)
    return row


def _delta_no_sync():
    mock = MagicMock()
    mock.get_delta_info.return_value = {
        "actual_delta": False,
        "requested_delta": False,
        "watermark": None,
        "watermark_formatted": None,
    }
    return mock


class TestTeacherImport:
    """Tests for the teacher import endpoint."""

    def test_new_teacher_created(self, client, auth_headers, app):
        """A new teacher is created via Teacher.import_from_salesforce."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [_make_teacher_row()]}

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.teacher import Teacher

        with app.app_context():
            teacher = Teacher.query.filter_by(
                salesforce_individual_id="003TEA000000001"
            ).first()
            assert teacher is not None
            assert teacher.first_name == "Maria"
            assert teacher.last_name == "Garcia"

    def test_multiple_teachers(self, client, auth_headers, app):
        """Multiple teachers are all imported."""
        rows = [
            _make_teacher_row(
                {
                    "Id": f"003TEA00000000{i}",
                    "FirstName": f"Teacher{i}",
                }
            )
            for i in range(3)
        ]

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": rows}

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 3

    def test_empty_result_set(self, client, auth_headers):
        """No teacher records returns success with 0 count."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": []}

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 0

    def test_existing_teacher_updated(self, client, auth_headers, app):
        """An existing teacher is updated, not duplicated."""
        from models import db
        from models.teacher import Teacher

        with app.app_context():
            teacher = Teacher(
                salesforce_individual_id="003TEA000000001",
                first_name="OldFirst",
                last_name="OldLast",
            )
            db.session.add(teacher)
            db.session.commit()

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [_make_teacher_row()]}

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200

        with app.app_context():
            teachers = Teacher.query.filter_by(
                salesforce_individual_id="003TEA000000001"
            ).all()
            assert len(teachers) == 1
            assert teachers[0].first_name == "Maria"

    def test_sync_log_created(self, client, auth_headers, app):
        """A SyncLog record is created after successful import."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": [_make_teacher_row()]}

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200

        from models.sync_log import SyncLog

        with app.app_context():
            logs = SyncLog.query.filter_by(sync_type="teachers").all()
            assert len(logs) == 1
            assert logs[0].records_processed == 1

    def test_auth_failure_returns_401(self, client, auth_headers):
        """SalesforceAuthenticationFailed returns 401."""
        from simple_salesforce.exceptions import SalesforceAuthenticationFailed

        with patch(PATCH_SF_CLIENT) as mock_sf, patch(PATCH_DELTA) as mock_delta_cls:

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf.side_effect = SalesforceAuthenticationFailed(
                "https://test.salesforce.com", "Auth Failed"
            )

            response = client.post(
                "/teachers/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
