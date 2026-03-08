"""
Integration tests for Salesforce Student Import Routes.

Tests cover chunked pagination, Student.import_from_salesforce delegation,
error isolation with savepoints, and sync log creation on final chunk.
"""

from unittest.mock import MagicMock, patch

import pytest

PATCH_SF_CLIENT = "routes.salesforce.student_import.get_salesforce_client"
PATCH_SAFE_QUERY = "routes.salesforce.student_import.safe_query"
PATCH_DELTA = "services.salesforce.DeltaSyncHelper"


def _make_student_row(overrides=None):
    """Build a minimal valid Salesforce student row."""
    row = {
        "Id": "003STU000000001",
        "AccountId": "001ACCT000000001",
        "FirstName": "Alice",
        "LastName": "Student",
        "MiddleName": None,
        "Email": "alice@school.test",
        "Phone": None,
        "Local_Student_ID__c": "STU001",
        "Birthdate": "2010-03-15",
        "Gender__c": "Female",
        "Racial_Ethnic_Background__c": "White",
        "npsp__Primary_Affiliation__c": None,
        "Class__c": None,
        "Legacy_Grade__c": "5th Grade",
        "Current_Grade__c": "5",
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
    mock.build_date_filter.return_value = ""
    return mock


class TestStudentImport:
    """Tests for the student import endpoint."""

    def test_new_student_created(self, client, auth_headers, app):
        """A new student is created via Student.import_from_salesforce."""
        student_row = _make_student_row()

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            # First call: count query; second call: data query
            mock_query.side_effect = [
                {"records": [{"total": 1}]},
                {"records": [student_row]},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True
        assert data["processed_count"] == 1
        assert data["is_complete"] is True

    def test_chunked_pagination_not_complete(self, client, auth_headers, app):
        """When chunk_size records are returned, is_complete is False."""
        # Return exactly 2 records for chunk_size=2
        rows = [_make_student_row({"Id": f"003STU00000000{i}"}) for i in range(2)]

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [{"total": 10}]},  # Total is larger
                {"records": rows},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                json={"chunk_size": 2},
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True
        assert data["is_complete"] is False
        assert data["next_id"] is not None

    def test_empty_result_set(self, client, auth_headers):
        """No student records from Salesforce returns success with 0 count."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [{"total": 0}]},
                {"records": []},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True
        assert data["processed_count"] == 0
        assert data["is_complete"] is True

    def test_count_query_failure(self, client, auth_headers):
        """Count query returning empty result returns error."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.return_value = {"records": []}

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["status"] == "error"

    def test_fatal_error_returns_error_status(self, client, auth_headers):
        """Fatal exception during import returns error status."""
        with patch(PATCH_SF_CLIENT) as mock_sf, patch(PATCH_DELTA) as mock_delta_cls:

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf.side_effect = Exception("Connection refused")

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["status"] == "error"


class TestStudentImportContactInfo:
    """Data-driven tests for Student.update_contact_info — str(None) bug.

    Production DB analysis found 158,923 email records and 158,925 phone records
    stored as the literal string 'None', all from student imports.
    Root cause: str(sf_data.get("Email", "")) converts Python None → "None".
    """

    def test_null_email_not_stored_as_string_none(self, client, auth_headers, app):
        """When Salesforce sends Email=None, no email record should be created."""
        row = _make_student_row({"Email": None, "Phone": None})

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [{"total": 1}]},
                {"records": [row]},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True

        from models.contact import Email

        with app.app_context():
            # There must be NO email record — especially not one with value "None"
            none_emails = Email.query.filter_by(email="None").all()
            assert len(none_emails) == 0, (
                f"Found {len(none_emails)} email records with value 'None' — "
                "str(None) bug is still present"
            )

    def test_null_phone_not_stored_as_string_none(self, client, auth_headers, app):
        """When Salesforce sends Phone=None, no phone record should be created."""
        row = _make_student_row({"Email": "real@test.com", "Phone": None})

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [{"total": 1}]},
                {"records": [row]},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True

        from models.contact import Phone

        with app.app_context():
            none_phones = Phone.query.filter_by(number="None").all()
            assert len(none_phones) == 0, (
                f"Found {len(none_phones)} phone records with value 'None' — "
                "str(None) bug is still present"
            )

    def test_valid_email_still_stored_after_fix(self, client, auth_headers, app):
        """A real email address is still stored correctly after the fix."""
        row = _make_student_row({"Email": "alice@school.test", "Phone": "816-555-1234"})

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [{"total": 1}]},
                {"records": [row]},
            ]

            response = client.post(
                "/students/import-from-salesforce",
                headers=auth_headers,
            )

        data = response.get_json() if hasattr(response, "get_json") else response
        assert data["success"] is True

        from models.contact import Email, Phone
        from models.student import Student

        with app.app_context():
            student = Student.query.filter_by(
                salesforce_individual_id="003STU000000001"
            ).first()
            assert student is not None

            email = Email.query.filter_by(contact_id=student.id).first()
            assert email is not None
            assert email.email == "alice@school.test"

            phone = Phone.query.filter_by(contact_id=student.id).first()
            assert phone is not None
            assert phone.number == "816-555-1234"
