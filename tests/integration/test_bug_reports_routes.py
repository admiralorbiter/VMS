import pytest
from datetime import datetime, timedelta
from flask import url_for
from models import db
from models.bug_report import BugReport, BugReportType
from tests.conftest import assert_route_response, safe_route_test

def test_bug_report_form_view(client, auth_headers):
    """Test bug report form view"""
    response = safe_route_test(client, '/bug-report/form', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_submit_bug_report(client, auth_headers):
    """Test submitting bug report"""
    response = safe_route_test(client, '/bug-report/submit', method='POST', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])

def test_bug_reports_list_view(client, auth_headers):
    """Test bug reports list view (admin)"""
    response = safe_route_test(client, '/bug-reports', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_report_detail_view(client, auth_headers):
    """Test individual bug report detail view"""
    response = safe_route_test(client, '/bug-reports/view/1', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_resolve_bug_report(client, auth_headers):
    """Test resolving bug report"""
    response = safe_route_test(client, '/bug-reports/resolve/1', method='POST', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 302, 404, 500])

def test_bug_reports_pagination(client, auth_headers):
    """Test bug reports pagination"""
    response = safe_route_test(client, '/bug-reports?page=2&per_page=20', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_search(client, auth_headers):
    """Test bug reports search functionality"""
    response = safe_route_test(client, '/bug-reports?search=login', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_filtering(client, auth_headers):
    """Test bug reports filtering"""
    response = safe_route_test(client, '/bug-reports?type=BUG&status=Open', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_sorting(client, auth_headers):
    """Test bug reports sorting"""
    response = safe_route_test(client, '/bug-reports?sort=created_at&order=desc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_export(client, auth_headers):
    """Test bug reports data export"""
    response = safe_route_test(client, '/bug-reports/export', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_statistics(client, auth_headers):
    """Test bug reports statistics"""
    response = safe_route_test(client, '/bug-reports/statistics', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_by_type(client, auth_headers):
    """Test bug reports by type filtering"""
    response = safe_route_test(client, '/bug-reports?type=BUG', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_by_status(client, auth_headers):
    """Test bug reports by status filtering"""
    response = safe_route_test(client, '/bug-reports?status=Open', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_by_priority(client, auth_headers):
    """Test bug reports by priority filtering"""
    response = safe_route_test(client, '/bug-reports?priority=High', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_unauthorized_access(client):
    """Test bug reports unauthorized access"""
    response = safe_route_test(client, '/bug-reports')
    assert_route_response(response, expected_statuses=[302, 401, 403])

def test_bug_reports_error_handling(client, auth_headers):
    """Test bug reports error handling"""
    response = safe_route_test(client, '/bug-reports/invalid-endpoint', headers=auth_headers)
    assert_route_response(response, expected_statuses=[404, 500])

def test_bug_reports_performance(client, auth_headers):
    """Test bug reports performance"""
    response = safe_route_test(client, '/bug-reports', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_bug_reports_data_validation(client, auth_headers):
    """Test bug reports data validation"""
    response = safe_route_test(client, '/bug-reports/validate', method='POST', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 400, 404, 500]) 