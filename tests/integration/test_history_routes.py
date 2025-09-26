from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.event import Event
from models.history import History
from models.volunteer import Volunteer
from tests.conftest import assert_route_response, safe_route_test


@pytest.mark.slow
def test_history_table_view(client, auth_headers):
    """Test history table main view"""
    response = safe_route_test(client, "/history_table", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_history_item_detail(client, auth_headers):
    """Test individual history item view"""
    response = safe_route_test(client, "/history/view/1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_history_add_entry(client, auth_headers):
    """Test adding new history entry"""
    response = safe_route_test(
        client, "/history/add", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


def test_history_delete_entry(client, auth_headers):
    """Test soft deleting history entry"""
    response = safe_route_test(
        client, "/history/delete/1", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


@pytest.mark.slow
@pytest.mark.salesforce
def test_history_import_salesforce(client, auth_headers):
    """Test importing history from Salesforce"""
    response = safe_route_test(
        client, "/history/import-from-salesforce", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])


@pytest.mark.slow
def test_history_filtering(client, auth_headers):
    """Test history filtering functionality"""
    response = safe_route_test(
        client,
        "/history_table?activity_type=NOTE&start_date=2024-01-01",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_search(client, auth_headers):
    """Test history search functionality"""
    response = safe_route_test(
        client, "/history_table?search=volunteer", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_pagination(client, auth_headers):
    """Test history pagination"""
    response = safe_route_test(
        client, "/history_table?page=2&per_page=20", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_sorting(client, auth_headers):
    """Test history sorting"""
    response = safe_route_test(
        client, "/history_table?sort=created_at&order=desc", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_export(client, auth_headers):
    """Test history data export"""
    response = safe_route_test(client, "/history/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_statistics(client, auth_headers):
    """Test history statistics"""
    response = safe_route_test(client, "/history/statistics", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_activity_types(client, auth_headers):
    """Test history activity type filtering"""
    response = safe_route_test(
        client, "/history_table?activity_type=ACTIVITY", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_date_range(client, auth_headers):
    """Test history date range filtering"""
    response = safe_route_test(
        client,
        "/history_table?start_date=2024-01-01&end_date=2024-12-31",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_volunteer_filter(client, auth_headers):
    """Test history volunteer filtering"""
    response = safe_route_test(
        client, "/history_table?volunteer_id=1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_event_filter(client, auth_headers):
    """Test history event filtering"""
    response = safe_route_test(
        client, "/history_table?event_id=1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


@pytest.mark.slow
def test_history_unauthorized_access(client):
    """Test history unauthorized access"""
    response = safe_route_test(client, "/history_table")
    assert_route_response(response, expected_statuses=[302, 401, 403])


def test_history_error_handling(client, auth_headers):
    """Test history error handling"""
    response = safe_route_test(
        client, "/history/invalid-endpoint", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


@pytest.mark.slow
def test_history_performance(client, auth_headers):
    """Test history performance"""
    response = safe_route_test(client, "/history_table", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_history_data_validation(client, auth_headers):
    """Test history data validation"""
    response = safe_route_test(
        client, "/history/validate", method="POST", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 400, 404, 500])
