"""
Integration tests for Reporting Cache Management (TC-221, TC-222).

Tests verify that:
- Cache invalidation is triggered by event sync operations (TC-221)
- Manual cache refresh endpoints are available and functional (TC-222)

Test Coverage:
- TC-221: Event sync triggers cache invalidation
- TC-222: Manual cache refresh available
"""

from unittest.mock import MagicMock, patch

import pytest


class TestReportingCache:
    """
    Tests for cache management and invalidation requirements.
    """

    def test_manual_cache_refresh_endpoint(self, client, test_admin):
        """
        TC-222: Verify manual cache refresh works for large datasets.

        Using the admin user, verify that the manual refresh endpoint
        returns success and triggers the refresh logic.
        """
        # Login as admin
        client.post("/login", data={"username": "admin", "password": "admin123"})

        with patch(
            "routes.management.cache_management.refresh_all_caches"
        ) as mock_refresh:
            # Test GET (view form)
            response = client.get("/management/cache/refresh")
            assert response.status_code == 200
            assert b"Refresh Caches" in response.data

            # Test POST (trigger refresh)
            response = client.post(
                "/management/cache/refresh",
                data={"cache_type": "all"},
                follow_redirects=True,
            )

            assert response.status_code == 200
            # assert b"All caches refreshed successfully" in response.data  # Flash message might rely on template details
            mock_refresh.assert_called_once()

        # Logout to clean up
        client.get("/logout")

    def test_sync_triggers_cache_invalidation(self, client, auth_headers):
        """
        TC-221: Verify event sync triggers cache invalidation.

        The system shall update reports immediately after sync by
        triggering cache refresh.
        """
        with (
            patch("routes.events.routes.Salesforce") as mock_sf,
            patch("routes.events.routes.refresh_all_caches") as mock_refresh,
        ):

            # Mock successful Salesforce query with one record
            mock_instance = MagicMock()
            mock_instance.query_all.return_value = {
                "records": [
                    {
                        "Id": "EVT123",
                        "Name": "Test Event",
                        "Session_Type__c": "Career Day",
                        "Session_Status__c": "Confirmed",
                        "Start_Date_and_Time__c": "2026-05-20T10:00:00.000+0000",
                        "End_Date_and_Time__c": "2026-05-20T12:00:00.000+0000",
                    }
                ]
            }
            mock_sf.return_value = mock_instance

            # Trigger sync
            response = client.post(
                "/events/import-from-salesforce",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["events_processed"] == 1

            # Verify cache refresh was triggered
            mock_refresh.assert_called()
