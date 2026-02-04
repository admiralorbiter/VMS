"""
Integration tests for Sync Error Handling (TC-200).

Tests verify that the system correctly handles various sync scenarios:
- No events to sync (success with 0 count)
- Salesforce authentication failure (401 error)
- General API errors (500 error)
- Partial failures (success with error details)

Test Coverage:
- TC-200: Distinguish no events vs failure
"""

from unittest.mock import MagicMock, patch

import pytest
from simple_salesforce.exceptions import SalesforceAuthenticationFailed


class TestSyncErrorHandling:
    """
    TC-200: The system shall distinguish 'no events to sync' from 'sync failure'.
    """

    def test_no_events_returns_success(self, client, auth_headers):
        """
        TC-200: Verify that finding no events returns success (200 OK)
        with 0 processed count, not an error.
        """
        with patch(
            "routes.salesforce.event_import.get_salesforce_client"
        ) as mock_get_sf:
            # Mock empty results for event query
            mock_instance = MagicMock()
            mock_instance.query_all.return_value = {"records": []}
            mock_get_sf.return_value = mock_instance

            response = client.post(
                "/events/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["events_processed"] == 0
            # errors is a list in the response, not a count
            assert len(data["errors"]) == 0

    def test_auth_failure_returns_error(self, client, auth_headers):
        """
        TC-200: Verify that Salesforce authentication failure returns
        appropriate error status (401 Unauthorized).
        """
        with patch(
            "routes.salesforce.event_import.get_salesforce_client"
        ) as mock_get_sf:
            # Mock authentication failure
            mock_get_sf.side_effect = SalesforceAuthenticationFailed(
                "https://test.salesforce.com", "Auth Failed"
            )

            response = client.post(
                "/events/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False
            assert "authenticate" in data["message"]

    def test_general_api_error_returns_failure(self, client, auth_headers):
        """
        TC-200: Verify that general API errors return failure status (500).
        """
        with patch(
            "routes.salesforce.event_import.get_salesforce_client"
        ) as mock_get_sf:
            # Mock general exception
            mock_get_sf.side_effect = Exception("General connection error")

            response = client.post(
                "/events/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "connection error" in data["error"]
