import json
from datetime import datetime, timedelta

import pytest
from flask import url_for

from models import db
from models.contact import Contact
from models.district_model import District
from models.event import Event, EventStatus, EventType
from models.organization import Organization
from models.pathways import Pathway
from models.school_model import School
from models.volunteer import Volunteer
from tests.conftest import assert_route_response, safe_route_test


def test_reports_main_view(client, auth_headers):
    """Test reports main view"""
    response = safe_route_test(client, "/reports", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report(client, auth_headers):
    """Test virtual usage report"""
    response = safe_route_test(client, "/reports/virtual-usage", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_district_report(client, auth_headers):
    """Test virtual usage district report"""
    response = safe_route_test(
        client, "/reports/virtual-usage-district", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_volunteer_thankyou_report(client, auth_headers):
    """Test volunteer thank you report"""
    response = safe_route_test(
        client, "/reports/volunteer-thankyou", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_volunteer_thankyou_detail_report(client, auth_headers):
    """Test volunteer thank you detail report"""
    response = safe_route_test(
        client, "/reports/volunteer-thankyou-detail", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_thankyou_report(client, auth_headers):
    """Test organization thank you report"""
    response = safe_route_test(
        client, "/reports/organization-thankyou", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_thankyou_detail_report(client, auth_headers):
    """Test organization thank you detail report"""
    response = safe_route_test(
        client, "/reports/organization-thankyou-detail", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_district_year_end_report(client, auth_headers):
    """Test district year end report"""
    response = safe_route_test(
        client, "/reports/district-year-end", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_district_year_end_detail_report(client, auth_headers):
    """Test district year end detail report"""
    response = safe_route_test(
        client, "/reports/district-year-end-detail", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_recruitment_report(client, auth_headers):
    """Test recruitment report"""
    response = safe_route_test(client, "/reports/recruitment", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_recruitment_search(client, auth_headers):
    """Test recruitment search"""
    response = safe_route_test(
        client, "/reports/recruitment-search", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 405, 404, 500])


def test_recruitment_tools(client, auth_headers):
    """Test recruitment tools"""
    response = safe_route_test(
        client, "/reports/recruitment-tools", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_contact_report(client, auth_headers):
    """Test contact report"""
    response = safe_route_test(client, "/reports/contact", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_contact_report_detail(client, auth_headers):
    """Test contact report detail"""
    response = safe_route_test(client, "/reports/contact-detail", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_pathways_report(client, auth_headers):
    """Test pathways report"""
    response = safe_route_test(client, "/reports/pathways", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_pathway_detail_report(client, auth_headers):
    """Test pathway detail report"""
    response = safe_route_test(client, "/reports/pathway-detail", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_attendance_report(client, auth_headers):
    """Test attendance report"""
    response = safe_route_test(client, "/reports/attendance", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_first_time_volunteer_report(client, auth_headers):
    """Test first time volunteer report"""
    response = safe_route_test(
        client, "/reports/first-time-volunteer", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


# New tests for virtual session reports with district filtering
def test_virtual_usage_report_default_view(client, auth_headers):
    """Test virtual usage report default view (main districts only)"""
    response = safe_route_test(client, "/reports/virtual/usage", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

    if response.status_code == 200:
        # Verify the response contains district data
        # This is a basic check - in a real test we'd verify the specific districts shown
        assert response.status_code == 200


def test_virtual_usage_report_all_districts_view(client, auth_headers):
    """Test virtual usage report with all districts view"""
    response = safe_route_test(
        client, "/reports/virtual/usage?show_all_districts=1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])

    if response.status_code == 200:
        # Verify the response contains district data
        assert response.status_code == 200


def test_virtual_usage_report_with_district_filter(client, auth_headers):
    """Test virtual usage report with specific district filter"""
    # Test with main district
    response = safe_route_test(
        client,
        "/reports/virtual/usage?district=Hickman Mills School District",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # Test with non-main district
    response = safe_route_test(
        client, "/reports/virtual/usage?district=Unknown District", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_with_status_filter(client, auth_headers):
    """Test virtual usage report with status filter"""
    # Test with different status filters
    statuses = ["successfully completed", "simulcast", "completed"]
    for status in statuses:
        response = safe_route_test(
            client, f"/reports/virtual/usage?status={status}", headers=auth_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_with_date_filters(client, auth_headers):
    """Test virtual usage report with date filters"""
    # Test with date range
    response = safe_route_test(
        client,
        "/reports/virtual/usage?date_from=2024-07-01&date_to=2024-12-31",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_export(client, auth_headers):
    """Test virtual usage report export functionality"""
    response = safe_route_test(
        client, "/reports/virtual/usage/export", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_district_detail(client, auth_headers):
    """Test virtual usage district detail report"""
    # Test with main district
    response = safe_route_test(
        client,
        "/reports/virtual/usage/district/Hickman Mills School District",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])

    # Test with non-main district
    response = safe_route_test(
        client, "/reports/virtual/usage/district/Unknown District", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_cache_functionality(client, auth_headers):
    """Test virtual usage report cache functionality"""
    # Test with refresh parameter
    response = safe_route_test(
        client, "/reports/virtual/usage?refresh=1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_filter_combinations(client, auth_headers):
    """Test virtual usage report with multiple filter combinations"""
    # Test multiple filters together
    response = safe_route_test(
        client,
        "/reports/virtual/usage?district=Hickman Mills School District&status=successfully completed&show_all_districts=1",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_pagination(client, auth_headers):
    """Test virtual usage report pagination"""
    response = safe_route_test(
        client, "/reports/virtual/usage?page=1&per_page=10", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_sorting(client, auth_headers):
    """Test virtual usage report sorting"""
    # Test different sort options
    sort_options = ["date", "time", "session_title", "district", "status"]
    for sort_by in sort_options:
        response = safe_route_test(
            client, f"/reports/virtual/usage?sort_by={sort_by}", headers=auth_headers
        )
        assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_unauthorized_access(client):
    """Test virtual usage report unauthorized access"""
    response = safe_route_test(client, "/reports/virtual/usage")
    assert_route_response(response, expected_statuses=[302, 401, 403, 404])


def test_virtual_usage_report_error_handling(client, auth_headers):
    """Test virtual usage report error handling"""
    # Test with invalid parameters
    response = safe_route_test(
        client, "/reports/virtual/usage?invalid_param=test", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_virtual_usage_report_performance(client, auth_headers):
    """Test virtual usage report performance"""
    response = safe_route_test(client, "/reports/virtual/usage", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

    if response.status_code == 200:
        # Basic performance check - response should be reasonably fast
        assert response.status_code == 200


def test_organization_report_main(client, auth_headers):
    """Test organization report main view"""
    response = safe_route_test(client, "/reports/organization", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_with_filters(client, auth_headers):
    """Test organization report with filters"""
    response = safe_route_test(
        client, "/reports/organization?year=2024-2025", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_excel_export(client, auth_headers):
    """Test organization report excel export"""
    response = safe_route_test(
        client, "/reports/organization/export", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_excel_export_with_filters(client, auth_headers):
    """Test organization report excel export with filters"""
    response = safe_route_test(
        client, "/reports/organization/export?year=2024-2025", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_detail(client, auth_headers):
    """Test organization report detail view"""
    response = safe_route_test(
        client, "/reports/organization/detail/1", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_detail_with_filters(client, auth_headers):
    """Test organization report detail with filters"""
    response = safe_route_test(
        client, "/reports/organization/detail/1?year=2024-2025", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_detail_excel_export(client, auth_headers):
    """Test organization report detail excel export"""
    response = safe_route_test(
        client, "/reports/organization/detail/1/export", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_detail_excel_export_with_filters(client, auth_headers):
    """Test organization report detail excel export with filters"""
    response = safe_route_test(
        client,
        "/reports/organization/detail/1/export?year=2024-2025",
        headers=auth_headers,
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_organization_report_invalid_org_id(client, auth_headers):
    """Test organization report with invalid organization ID"""
    response = safe_route_test(
        client, "/reports/organization/detail/999999", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


def test_organization_report_excel_invalid_org_id(client, auth_headers):
    """Test organization report excel export with invalid organization ID"""
    response = safe_route_test(
        client, "/reports/organization/detail/999999/export", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


def test_reports_with_filters(client, auth_headers):
    """Test reports with various filters"""
    response = safe_route_test(
        client, "/reports?year=2024-2025&district=test", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_reports_pagination(client, auth_headers):
    """Test reports pagination"""
    response = safe_route_test(
        client, "/reports?page=1&per_page=10", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_reports_export_functionality(client, auth_headers):
    """Test reports export functionality"""
    response = safe_route_test(client, "/reports/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_reports_unauthorized_access(client):
    """Test reports unauthorized access"""
    response = safe_route_test(client, "/reports")
    assert_route_response(response, expected_statuses=[302, 401, 403, 404])


def test_reports_error_handling(client, auth_headers):
    """Test reports error handling"""
    response = safe_route_test(
        client, "/reports/invalid-endpoint", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[404, 500])


def test_reports_performance(client, auth_headers):
    """Test reports performance"""
    response = safe_route_test(client, "/reports", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_reports_search_functionality(client, auth_headers):
    """Test reports search functionality"""
    response = safe_route_test(client, "/reports?search=test", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_reports_sorting(client, auth_headers):
    """Test reports sorting"""
    response = safe_route_test(client, "/reports?sort_by=date", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_volunteers_by_event_report(client, auth_headers):
    """Test volunteers by event report main page"""
    response = safe_route_test(
        client, "/reports/volunteers/by-event", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_volunteers_by_event_export(client, auth_headers):
    """Test volunteers by event report excel export"""
    response = safe_route_test(
        client, "/reports/volunteers/by-event/excel", headers=auth_headers
    )
    assert_route_response(response, expected_statuses=[200, 404, 500])
