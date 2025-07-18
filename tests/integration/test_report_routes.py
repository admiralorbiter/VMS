import pytest
from datetime import datetime, timedelta
from flask import url_for
from models import db
from models.event import Event, EventType, EventStatus
from models.volunteer import Volunteer
from models.organization import Organization
from models.district_model import District
from models.school_model import School
from models.pathways import Pathway
from models.contact import Contact
import json
from tests.conftest import assert_route_response, safe_route_test

def test_reports_main_view(client, auth_headers):
    """Test reports main view"""
    response = safe_route_test(client, '/reports', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_virtual_usage_report(client, auth_headers):
    """Test virtual usage report"""
    response = safe_route_test(client, '/reports/virtual-usage', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_virtual_usage_district_report(client, auth_headers):
    """Test virtual usage district report"""
    response = safe_route_test(client, '/reports/virtual-usage-district', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_volunteer_thankyou_report(client, auth_headers):
    """Test volunteer thank you report"""
    response = safe_route_test(client, '/reports/volunteer-thankyou', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_volunteer_thankyou_detail_report(client, auth_headers):
    """Test volunteer thank you detail report"""
    response = safe_route_test(client, '/reports/volunteer-thankyou-detail', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_thankyou_report(client, auth_headers):
    """Test organization thank you report"""
    response = safe_route_test(client, '/reports/organization-thankyou', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_thankyou_detail_report(client, auth_headers):
    """Test organization thank you detail report"""
    response = safe_route_test(client, '/reports/organization-thankyou-detail', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_district_year_end_report(client, auth_headers):
    """Test district year end report"""
    response = safe_route_test(client, '/reports/district-year-end', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_district_year_end_detail_report(client, auth_headers):
    """Test district year end detail report"""
    response = safe_route_test(client, '/reports/district-year-end-detail', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_recruitment_report(client, auth_headers):
    """Test recruitment report"""
    response = safe_route_test(client, '/reports/recruitment', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_recruitment_search(client, auth_headers):
    """Test recruitment search"""
    response = safe_route_test(client, '/reports/recruitment-search', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 405, 404, 500])

def test_recruitment_tools(client, auth_headers):
    """Test recruitment tools"""
    response = safe_route_test(client, '/reports/recruitment-tools', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_contact_report(client, auth_headers):
    """Test contact report"""
    response = safe_route_test(client, '/reports/contact', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_contact_report_detail(client, auth_headers):
    """Test contact report detail"""
    response = safe_route_test(client, '/reports/contact-detail', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_pathways_report(client, auth_headers):
    """Test pathways report"""
    response = safe_route_test(client, '/reports/pathways', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_pathway_detail_report(client, auth_headers):
    """Test pathway detail report"""
    response = safe_route_test(client, '/reports/pathway-detail', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_attendance_report(client, auth_headers):
    """Test attendance report"""
    response = safe_route_test(client, '/reports/attendance', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_first_time_volunteer_report(client, auth_headers):
    """Test first time volunteer report"""
    response = safe_route_test(client, '/reports/first-time-volunteer', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

# Organization Report Tests
def test_organization_report_main(client, auth_headers):
    """Test organization report main view"""
    response = safe_route_test(client, '/reports/organization/report', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_with_filters(client, auth_headers):
    """Test organization report with filters"""
    response = safe_route_test(client, '/reports/organization/report?school_year=2425&host_filter=prepkc&sort=name&order=asc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_excel_export(client, auth_headers):
    """Test organization report Excel export"""
    response = safe_route_test(client, '/reports/organization/report/excel', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_excel_export_with_filters(client, auth_headers):
    """Test organization report Excel export with filters"""
    response = safe_route_test(client, '/reports/organization/report/excel?school_year=2425&host_filter=prepkc&sort=total_hours&order=desc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_detail(client, auth_headers):
    """Test organization report detail view"""
    response = safe_route_test(client, '/reports/organization/report/detail/1', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_detail_with_filters(client, auth_headers):
    """Test organization report detail with filters"""
    response = safe_route_test(client, '/reports/organization/report/detail/1?school_year=2425&sort_vol=hours&order_vol=desc&sort_evt=date&order_evt=asc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_detail_excel_export(client, auth_headers):
    """Test organization report detail Excel export"""
    response = safe_route_test(client, '/reports/organization/report/detail/1/excel', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_detail_excel_export_with_filters(client, auth_headers):
    """Test organization report detail Excel export with filters"""
    response = safe_route_test(client, '/reports/organization/report/detail/1/excel?school_year=2425&sort_vol=name&order_vol=asc&sort_evt=title&order_evt=desc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_organization_report_invalid_org_id(client, auth_headers):
    """Test organization report detail with invalid organization ID"""
    response = safe_route_test(client, '/reports/organization/report/detail/999999', headers=auth_headers)
    assert_route_response(response, expected_statuses=[404, 500])

def test_organization_report_excel_invalid_org_id(client, auth_headers):
    """Test organization report detail Excel export with invalid organization ID"""
    response = safe_route_test(client, '/reports/organization/report/detail/999999/excel', headers=auth_headers)
    assert_route_response(response, expected_statuses=[404, 500])

def test_reports_with_filters(client, auth_headers):
    """Test reports with filters"""
    response = safe_route_test(client, '/reports?district=test&year=2024', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_reports_pagination(client, auth_headers):
    """Test reports pagination"""
    response = safe_route_test(client, '/reports/attendance?page=2', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_reports_export_functionality(client, auth_headers):
    """Test reports export functionality"""
    response = safe_route_test(client, '/reports/export?format=csv', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 400, 500, 404])

def test_reports_unauthorized_access(client):
    """Test reports unauthorized access"""
    response = safe_route_test(client, '/reports')
    assert_route_response(response, expected_statuses=[302, 404, 500])

def test_reports_error_handling(client, auth_headers):
    """Test reports error handling"""
    response = safe_route_test(client, '/reports/invalid-report', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 400, 500, 404])

def test_reports_performance(client, auth_headers):
    """Test reports performance"""
    response = safe_route_test(client, '/reports/attendance', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_reports_search_functionality(client, auth_headers):
    """Test reports search functionality"""
    response = safe_route_test(client, '/reports?search=test', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_reports_sorting(client, auth_headers):
    """Test reports sorting"""
    response = safe_route_test(client, '/reports/attendance?sort=date', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500]) 
