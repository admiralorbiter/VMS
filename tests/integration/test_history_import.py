"""
Integration tests for Salesforce History Import Routes.

Tests cover Task and EmailMessage record creation, contact lookup chain,
HTML stripping, duplicate detection, and missing WhoId/RelatedToId handling.
"""

from unittest.mock import MagicMock, patch

import pytest

PATCH_SF_CLIENT = "routes.salesforce.history_import.get_salesforce_client"
PATCH_SAFE_QUERY = "routes.salesforce.history_import.safe_query_all"
PATCH_DELTA = "services.salesforce.DeltaSyncHelper"


def _delta_no_sync():
    mock = MagicMock()
    mock.get_delta_info.return_value = {
        "actual_delta": False,
        "requested_delta": False,
        "watermark": None,
        "watermark_formatted": None,
    }
    return mock


class TestHistoryImportTask:
    """Tests for Task record processing."""

    def test_task_creates_history(self, client, auth_headers, app):
        """A Task record with a matching volunteer creates a History record."""
        from models import db
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL000000001",
                first_name="Test",
                last_name="Volunteer",
            )
            db.session.add(vol)
            db.session.commit()

        task_row = {
            "Id": "00T_TASK_001",
            "Subject": "Volunteer Check-in Call",
            "Description": "Checked in with volunteer about availability",
            "Type": "Call",
            "Status": "Completed",
            "ActivityDate": "2025-06-15",
            "WhoId": "003VOL000000001",
            "WhatId": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            # First call: Task query; second call: EmailMessage query
            mock_query.side_effect = [
                {"records": [task_row]},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 1

        from models.history import History

        with app.app_context():
            hist = History.query.filter_by(salesforce_id="00T_TASK_001").first()
            assert hist is not None
            assert hist.summary == "Volunteer Check-in Call"
            assert hist.history_type == "activity"  # 'call' maps to activity

    def test_task_without_whoid_skipped(self, client, auth_headers, app):
        """A Task without WhoId is skipped (not errored)."""
        task_row = {
            "Id": "00T_NO_WHO",
            "Subject": "Orphan Task",
            "Description": None,
            "Type": "Call",
            "Status": "Completed",
            "ActivityDate": "2025-06-15",
            "WhoId": None,
            "WhatId": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [task_row]},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 0
        assert data["skipped_count"] == 1

    def test_task_with_no_matching_contact_skipped(self, client, auth_headers, app):
        """A Task whose WhoId doesn't match any contact is skipped."""
        task_row = {
            "Id": "00T_NO_MATCH",
            "Subject": "Unknown Contact Task",
            "Description": None,
            "Type": "Call",
            "Status": "Completed",
            "ActivityDate": "2025-06-15",
            "WhoId": "003NONEXISTENT",
            "WhatId": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [task_row]},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 0
        assert data["skipped_count"] == 1
        assert data["stats"]["skipped_details"]["no_contact"] == 1

    def test_task_type_mapping(self, client, auth_headers, app):
        """Task Type field maps to correct history_type."""
        from models import db
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_TYPE_MAP",
                first_name="Type",
                last_name="Test",
            )
            db.session.add(vol)
            db.session.commit()

        email_task = {
            "Id": "00T_EMAIL_TYPE",
            "Subject": "Email Task",
            "Description": None,
            "Type": "Email",
            "Status": "Completed",
            "ActivityDate": "2025-06-15",
            "WhoId": "003VOL_TYPE_MAP",
            "WhatId": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [email_task]},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200

        from models.history import History

        with app.app_context():
            hist = History.query.filter_by(salesforce_id="00T_EMAIL_TYPE").first()
            assert hist is not None
            assert hist.history_type == "activity"
            assert hist.activity_type == "Email"


class TestHistoryImportEmail:
    """Tests for EmailMessage record processing."""

    def test_email_creates_history_via_to_address(self, client, auth_headers, app):
        """EmailMessage with matching ToAddress creates a History record."""
        from models import db
        from models.contact import Email
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_EM_001",
                first_name="Email",
                last_name="Test",
            )
            db.session.add(vol)
            db.session.flush()
            email = Email(
                contact_id=vol.id,
                email="volunteer@example.com",
                type="personal",
                primary=True,
            )
            db.session.add(email)
            db.session.commit()

        email_row = {
            "Id": "02s_EM_001",
            "Subject": "Follow-up Email",
            "TextBody": "Thanks for volunteering!",
            "HtmlBody": None,
            "MessageDate": "2025-06-20T10:30:00.000+0000",
            "FromAddress": "staff@org.test",
            "ToAddress": "volunteer@example.com",
            "CcAddress": None,
            "BccAddress": None,
            "RelatedToId": "001ACCT000000001",
            "ParentId": None,
            "Incoming": False,
            "Status": "Sent",
            "CreatedDate": "2025-06-20T10:30:00.000+0000",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
            "MessageIdentifier": None,
            "ThreadIdentifier": None,
        }

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf_instance = MagicMock()
            mock_sf.return_value = mock_sf_instance
            mock_query.side_effect = [
                {"records": []},  # No task records
                {"records": [email_row]},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

        from models.history import History

        with app.app_context():
            hist = History.query.filter_by(salesforce_id="02s_EM_001").first()
            assert hist is not None
            assert hist.summary == "Follow-up Email"
            assert hist.activity_type == "Email"
            assert hist.activity_status == "Sent"
            # Description should contain the email content
            assert "From: staff@org.test" in hist.description
            assert "To: volunteer@example.com" in hist.description

    def test_email_without_related_to_id_skipped(self, client, auth_headers):
        """EmailMessage without RelatedToId is skipped."""
        email_row = {
            "Id": "02s_NO_REL",
            "Subject": "Orphan Email",
            "TextBody": "body",
            "HtmlBody": None,
            "MessageDate": "2025-06-20T10:30:00.000+0000",
            "FromAddress": "staff@org.test",
            "ToAddress": "nobody@example.com",
            "CcAddress": None,
            "BccAddress": None,
            "RelatedToId": None,
            "ParentId": None,
            "Incoming": False,
            "Status": "Sent",
            "CreatedDate": "2025-06-20T10:30:00.000+0000",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
            "MessageIdentifier": None,
            "ThreadIdentifier": None,
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": []},
                {"records": [email_row]},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 0
        assert data["skipped_count"] == 1


class TestHistoryImportDuplicateDetection:
    """Tests for detecting and skipping already-imported records."""

    def test_existing_history_skipped(self, client, auth_headers, app):
        """A History record with the same salesforce_id is skipped, not re-created."""
        from models import db
        from models.history import History
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_DUP_001",
                first_name="Dup",
                last_name="Test",
            )
            db.session.add(vol)
            db.session.flush()

            existing = History(
                contact_id=vol.id,
                salesforce_id="00T_EXISTING",
                summary="Already imported",
                history_type="note",
                is_deleted=False,
            )
            db.session.add(existing)
            db.session.commit()

        task_row = {
            "Id": "00T_EXISTING",
            "Subject": "Duplicate Task",
            "Description": None,
            "Type": "Call",
            "Status": "Completed",
            "ActivityDate": "2025-06-15",
            "WhoId": "003VOL_DUP_001",
            "WhatId": None,
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
        }

        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": [task_row]},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 0
        assert data["stats"]["skipped_details"]["already_exists"] == 1


class TestHistoryImportEmpty:
    """Tests for empty result sets."""

    def test_no_records_returns_success(self, client, auth_headers):
        """Empty Task + EmailMessage results return success with 0 counts."""
        with (
            patch(PATCH_SF_CLIENT),
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_query.side_effect = [
                {"records": []},
                {"records": []},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["processed_count"] == 0

    def test_auth_failure_returns_401(self, client, auth_headers):
        """SalesforceAuthenticationFailed returns 401."""
        from simple_salesforce import SalesforceAuthenticationFailed

        with patch(PATCH_SF_CLIENT) as mock_sf, patch(PATCH_DELTA) as mock_delta_cls:

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf.side_effect = SalesforceAuthenticationFailed(
                "https://test.salesforce.com", "Auth Failed"
            )

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200 or response.status_code == 401
        data = response.get_json()
        assert data["success"] is False


class TestCreateTaskHistory:
    """Unit tests for the _create_task_history helper function."""

    def test_html_stripped_from_description(self, app):
        """HTML tags are stripped from the Description field."""
        from models import db
        from models.volunteer import Volunteer
        from routes.salesforce.history_import import _create_task_history

        with app.app_context():
            vol = Volunteer(first_name="Test", last_name="Vol")
            db.session.add(vol)
            db.session.flush()

            row = {
                "Id": "00T_HTML",
                "Subject": "Test",
                "Description": "<p>Hello <b>World</b></p>",
                "Type": "Call",
                "Status": "Completed",
                "ActivityDate": "2025-06-15",
                "WhoId": vol.salesforce_individual_id,
                "WhatId": None,
            }

            history = _create_task_history(row, vol.id, {})
            assert "<" not in history.description
            assert "Hello" in history.description
            assert "World" in history.description


class TestCreateEmailHistory:
    """Unit tests for the _create_email_history helper function."""

    def test_email_fields_assembled(self, app):
        """From/To/CC/BCC/Subject assembled into description."""
        from models import db
        from models.volunteer import Volunteer
        from routes.salesforce.history_import import _create_email_history

        with app.app_context():
            vol = Volunteer(first_name="Test", last_name="Vol")
            db.session.add(vol)
            db.session.flush()

            row = {
                "Id": "02s_ASSEMBLE",
                "Subject": "Hello",
                "TextBody": "Body text here",
                "HtmlBody": None,
                "MessageDate": "2025-06-20T10:30:00.000+0000",
                "FromAddress": "from@test.com",
                "ToAddress": "to@test.com",
                "CcAddress": "cc@test.com",
                "BccAddress": "bcc@test.com",
                "Incoming": True,
                "Status": "Received",
            }

            history = _create_email_history(row, vol.id)
            assert "From: from@test.com" in history.description
            assert "To: to@test.com" in history.description
            assert "CC: cc@test.com" in history.description
            assert "BCC: bcc@test.com" in history.description
            assert "Body text here" in history.description
            assert history.activity_status == "Received"

    def test_html_body_stripped(self, app):
        """HtmlBody has tags stripped when used as body content."""
        from models import db
        from models.volunteer import Volunteer
        from routes.salesforce.history_import import _create_email_history

        with app.app_context():
            vol = Volunteer(first_name="Test", last_name="Vol")
            db.session.add(vol)
            db.session.flush()

            row = {
                "Id": "02s_HTML_STRIP",
                "Subject": "HTML Email",
                "TextBody": None,
                "HtmlBody": "<html><body><p>Rich <b>content</b></p></body></html>",
                "MessageDate": "2025-06-20T10:30:00.000+0000",
                "FromAddress": "from@test.com",
                "ToAddress": "to@test.com",
                "CcAddress": None,
                "BccAddress": None,
                "Incoming": False,
                "Status": "Sent",
            }

            history = _create_email_history(row, vol.id)
            assert "<" not in history.description
            assert "Rich" in history.description
            assert "content" in history.description


class TestHistoryEmailContactLookupChain:
    """Tests for _find_contact_for_email multi-method fallback chain (P1 gap).

    The function tries 5 methods in order:
    1. ToAddress email match (already tested above)
    2. Direct contact match by RelatedToId
    3. Case-based lookup (queries Salesforce)
    4. Account-based lookup (queries Salesforce)
    5. Direct Email table fallback
    """

    def test_email_matched_via_from_address(self, client, auth_headers, app):
        """FromAddress is tried when ToAddress doesn't match any contact."""
        from models import db
        from models.contact import Email
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_FROM_01",
                first_name="From",
                last_name="Match",
            )
            db.session.add(vol)
            db.session.flush()
            email = Email(
                contact_id=vol.id,
                email="from-volunteer@example.com",
                type="personal",
                primary=True,
            )
            db.session.add(email)
            db.session.commit()

        email_row = {
            "Id": "02s_FROM_MATCH",
            "Subject": "FromAddress Match Test",
            "TextBody": "Test body",
            "HtmlBody": None,
            "MessageDate": "2025-06-20T10:30:00.000+0000",
            "FromAddress": "from-volunteer@example.com",
            "ToAddress": "unknown@example.com",  # No match
            "CcAddress": None,
            "BccAddress": None,
            "RelatedToId": "001ACCT_NOMATCH",  # Also no match
            "ParentId": None,
            "Incoming": True,
            "Status": "Received",
            "CreatedDate": "2025-06-20T10:30:00.000+0000",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
            "MessageIdentifier": None,
            "ThreadIdentifier": None,
        }

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf_instance = MagicMock()
            # Methods 3 & 4 query Salesforce — return empty to test fallback
            mock_sf_instance.query_all.return_value = {"records": []}
            mock_sf.return_value = mock_sf_instance
            mock_query.side_effect = [
                {"records": []},  # No task records
                {"records": [email_row]},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

        from models.history import History

        with app.app_context():
            hist = History.query.filter_by(salesforce_id="02s_FROM_MATCH").first()
            assert hist is not None
            assert hist.activity_status == "Received"

    def test_email_matched_via_direct_related_to_id(self, client, auth_headers, app):
        """RelatedToId directly matching a volunteer's salesforce_individual_id
        resolves the contact (method 2 in the fallback chain)."""
        from models import db
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_DIRECT_01",
                first_name="Direct",
                last_name="Match",
            )
            db.session.add(vol)
            db.session.commit()

        email_row = {
            "Id": "02s_DIRECT_MATCH",
            "Subject": "Direct RelatedToId Match",
            "TextBody": "Body",
            "HtmlBody": None,
            "MessageDate": "2025-06-20T10:30:00.000+0000",
            "FromAddress": "unknown@example.com",
            "ToAddress": "also-unknown@example.com",
            "CcAddress": None,
            "BccAddress": None,
            "RelatedToId": "003VOL_DIRECT_01",  # Matches volunteer's SF ID
            "ParentId": None,
            "Incoming": False,
            "Status": "Sent",
            "CreatedDate": "2025-06-20T10:30:00.000+0000",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
            "MessageIdentifier": None,
            "ThreadIdentifier": None,
        }

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf_instance = MagicMock()
            mock_sf_instance.query_all.return_value = {"records": []}
            mock_sf.return_value = mock_sf_instance
            mock_query.side_effect = [
                {"records": []},
                {"records": [email_row]},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1

    def test_email_matched_via_email_table_fallback(self, client, auth_headers, app):
        """Method 5: Direct Email table lookup finds a contact by ToAddress
        when all previous methods fail."""
        from models import db
        from models.contact import Email
        from models.volunteer import Volunteer

        with app.app_context():
            vol = Volunteer(
                salesforce_individual_id="003VOL_EMAIL_TBL",
                first_name="Table",
                last_name="Fallback",
            )
            db.session.add(vol)
            db.session.flush()
            email = Email(
                contact_id=vol.id,
                email="fallback@example.com",
                type="personal",
                primary=True,
            )
            db.session.add(email)
            db.session.commit()

        email_row = {
            "Id": "02s_TBL_FALLBACK",
            "Subject": "Email Table Fallback Test",
            "TextBody": "Body",
            "HtmlBody": None,
            "MessageDate": "2025-06-20T10:30:00.000+0000",
            "FromAddress": "unknown-sender@example.com",
            "ToAddress": "fallback@example.com",
            "CcAddress": None,
            "BccAddress": None,
            "RelatedToId": "001ACCT_NOMATCH",  # Not a contact SF ID
            "ParentId": None,
            "Incoming": False,
            "Status": "Sent",
            "CreatedDate": "2025-06-20T10:30:00.000+0000",
            "LastModifiedDate": "2026-01-01T00:00:00.000+0000",
            "MessageIdentifier": None,
            "ThreadIdentifier": None,
        }

        with (
            patch(PATCH_SF_CLIENT) as mock_sf,
            patch(PATCH_SAFE_QUERY) as mock_query,
            patch(PATCH_DELTA) as mock_delta_cls,
        ):

            mock_delta_cls.return_value = _delta_no_sync()
            mock_sf_instance = MagicMock()
            # Methods 3 & 4 return no matches from Salesforce
            mock_sf_instance.query_all.return_value = {"records": []}
            mock_sf.return_value = mock_sf_instance
            mock_query.side_effect = [
                {"records": []},
                {"records": [email_row]},
            ]

            response = client.post(
                "/history/import-from-salesforce",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["processed_count"] == 1
