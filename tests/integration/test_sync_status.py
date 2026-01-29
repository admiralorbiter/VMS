"""
Integration tests for Sync Status Indicators (TC-220).

Tests verify that:
- Sync operations record results to SyncLog (record counts, time, status)
- The admin dashboard displays the latest sync info
- The sync history page is accessible and displays results
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from models.sync_log import SyncStatus


class TestSyncStatus:
    """
    Tests for FR-INPERSON-131 / TC-220 (Sync Status Indicators).
    """

    def test_full_sync_visibility_flow(self, client, auth_headers, test_admin):
        """
        TC-220: Comprehensive test flow from sync to dashboard visibility.
        """
        # 1. Trigger sync
        with patch("routes.events.routes.Salesforce") as mock_sf:
            mock_instance = MagicMock()
            mock_instance.query_all.side_effect = [
                {"records": []},  # Events
                {"records": []},  # Participants
            ]
            mock_sf.return_value = mock_instance
            resp = client.post("/events/import-from-salesforce", headers=auth_headers)
            assert resp.status_code == 200

        # 2. Login as admin manually in this test session
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        assert b"Logout" in login_resp.data  # Successful login should show Logout link
        assert b"admin" in login_resp.data.lower()

        # 3. Check dashboard
        dashboard = client.get("/admin")
        assert dashboard.status_code == 200
        assert b"Admin Dashboard" in dashboard.data

        # Check if we see the admin restricted section
        if b"Last Salesforce Sync" not in dashboard.data:
            print(
                f"DEBUG: Last Salesforce Sync not in data. Data size: {len(dashboard.data)}"
            )
            # Check for other admin info
            if b"Create New User" in dashboard.data:
                print("DEBUG: 'Create New User' IS in data (Admin section is visible)")
            else:
                print("DEBUG: 'Create New User' NOT in data (Admin section HIDDEN)")

        assert b"Last Salesforce Sync" in dashboard.data
        assert b"Success" in dashboard.data

        # 4. Check sync logs
        logs_page = client.get("/admin/sync-logs")
        assert logs_page.status_code == 200
        assert b"Sync History" in logs_page.data
        assert b"Success" in logs_page.data
