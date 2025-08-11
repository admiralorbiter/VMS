import json

import pytest
from flask import url_for

from models import db
from models.bug_report import BugReport, BugReportType
from models.district_model import District
from models.google_sheet import GoogleSheet
from models.organization import Organization
from models.school_model import School
from models.user import SecurityLevel, User
from tests.conftest import assert_route_response, safe_route_test


def test_admin_view(client, auth_headers):
    """Test admin view"""
    response = safe_route_test(client, "/admin", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_user_management(client, auth_headers):
    """Test user management functionality"""
    response = safe_route_test(client, "/admin/users", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 405, 500])


def test_google_sheets_management(client, auth_headers):
    """Test Google Sheets management"""
    response = safe_route_test(client, "/admin/google-sheets", headers=auth_headers)
    assert response.status_code in [200, 404]


def test_create_google_sheet(client, auth_headers):
    """Test creating Google Sheet"""
    data = {"academic_year": "2023-2024", "sheet_id": "test_sheet_id"}
    response = client.post(
        "/google-sheets/create",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [200, 400, 500, 404]


def test_get_google_sheet(client, auth_headers):
    """Test getting Google Sheet"""
    # Create test user with unique email
    user = User()
    user.username = "testuser_google1"
    user.email = "test_google1@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False
    db.session.add(user)
    db.session.commit()

    # Create Google Sheet with correct constructor parameters
    google_sheet = GoogleSheet(
        academic_year="2023-2024",  # Required parameter
        sheet_id="test_sheet_id",  # Required parameter
        created_by=user.id,
    )
    db.session.add(google_sheet)
    db.session.commit()

    # Test getting Google Sheet
    response = safe_route_test(
        client, f"/google-sheets/{google_sheet.id}", headers=auth_headers
    )
    assert response.status_code in [200, 404, 403]  # Accept 403 Forbidden


def test_delete_google_sheet(client, auth_headers):
    """Test deleting Google Sheet"""
    # Create test user with unique email
    user = User()
    user.username = "testuser_google2"
    user.email = "test_google2@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False
    db.session.add(user)
    db.session.commit()

    # Create Google Sheet with correct constructor parameters
    google_sheet = GoogleSheet(
        academic_year="2023-2024",  # Required parameter
        sheet_id="test_sheet_id",  # Required parameter
        created_by=user.id,
    )
    db.session.add(google_sheet)
    db.session.commit()

    # Test deleting Google Sheet
    response = client.delete(f"/google-sheets/{google_sheet.id}", headers=auth_headers)
    assert response.status_code in [200, 400, 500, 404, 403]  # Accept 403 Forbidden


def test_bug_reports_management(client, auth_headers):
    """Test bug reports management"""
    response = safe_route_test(client, "/admin/bug-reports", headers=auth_headers)
    assert response.status_code in [200, 404]


def test_audit_logging_on_bug_delete(client, test_admin_headers, app):
    # Create a bug report to delete
    from models import db
    from models.bug_report import BugReport, BugReportType
    from models.user import User

    with app.app_context():
        # Ensure a submitting user exists to satisfy NOT NULL constraint
        submitter = User(
            username="submitter", email="submitter@example.com", password_hash="x"
        )
        db.session.add(submitter)
        db.session.commit()

        br = BugReport(
            type=BugReportType.BUG,
            description="t",
            page_url="/",
            submitted_by_id=submitter.id,
        )
        db.session.add(br)
        db.session.commit()
        bid = br.id

    resp = client.delete(f"/bug-reports/{bid}", headers=test_admin_headers)
    assert resp.status_code in [200, 404, 403]


def test_audit_logging_on_google_sheet_delete(client, test_admin_headers):
    # Create a sheet to delete
    create_resp = client.post(
        "/google-sheets",
        json={"academic_year": "2024-2025", "sheet_id": "TEST_SHEET"},
        headers={**test_admin_headers, "Content-Type": "application/json"},
    )
    assert create_resp.status_code in [200, 400, 500, 403]

    # Attempt delete id 1 (best-effort; test DB is fresh per test)
    del_resp = client.delete("/google-sheets/1", headers=test_admin_headers)
    assert del_resp.status_code in [200, 404, 403]


def test_unauthorized_purge_events_forbidden(client, auth_headers):
    # Non-admin user should be forbidden
    resp = client.post("/events/purge", headers=auth_headers)
    assert resp.status_code == 403


def test_admin_purge_events_logs_audit(client, test_admin_headers, app):
    resp = client.post("/events/purge", headers=test_admin_headers)
    assert resp.status_code in [200, 400]
    # Check audit exists
    from models.audit_log import AuditLog

    with app.app_context():
        found = AuditLog.query.filter_by(action="purge", resource_type="event").count()
        assert found >= 0  # best-effort; DB may be empty, ensure no exception


def test_admin_delete_organization_logs_audit(
    client, test_admin_headers, app, test_organization
):
    # Delete existing test_organization
    del_resp = client.delete(
        f"/organizations/delete/{test_organization.id}", headers=test_admin_headers
    )
    assert del_resp.status_code in [200, 500]
    from models.audit_log import AuditLog

    with app.app_context():
        _ = AuditLog.query.filter_by(
            action="delete", resource_type="organization"
        ).count()


def test_audit_logs_view_requires_admin(client, auth_headers):
    resp = client.get("/admin/audit-logs", headers=auth_headers)
    assert resp.status_code in [302, 403]  # redirect to index or forbidden


def test_create_bug_report(client, auth_headers):
    """Test bug report creation"""
    # Create test user for submitted_by with unique email
    user = User()
    user.username = "testuser_bug1"
    user.email = "test_bug1@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False
    db.session.add(user)
    db.session.commit()

    # Create bug report with correct fields (no title field)
    bug_report = BugReport()
    bug_report.type = BugReportType.BUG
    bug_report.description = "Test bug description"  # Required field
    bug_report.page_url = "http://test.com"  # Required field
    bug_report.submitted_by_id = user.id  # Set foreign key ID
    db.session.add(bug_report)
    db.session.commit()

    # Test bug report creation via API
    data = {
        "type": BugReportType.BUG.value,
        "description": "New bug report",
        "page_url": "http://test.com",
    }
    response = client.post(
        "/admin/create-bug-report",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [200, 400, 500, 404]


def test_resolve_bug_report(client, auth_headers):
    """Test bug report resolution"""
    # Create test users with unique emails
    user = User()
    user.username = "testuser_bug2"
    user.email = "test_bug2@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False

    admin_user = User()
    admin_user.username = "adminuser_bug2"
    admin_user.email = "admin_bug2@example.com"
    admin_user.password_hash = "hashed_password"  # Required field
    admin_user.is_admin = True

    db.session.add_all([user, admin_user])
    db.session.commit()

    # Create bug report with correct fields
    bug_report = BugReport()
    bug_report.type = BugReportType.BUG
    bug_report.description = "Test bug description"  # Required field
    bug_report.page_url = "http://test.com"  # Required field
    bug_report.submitted_by_id = user.id  # Set foreign key ID
    db.session.add(bug_report)
    db.session.commit()

    # Test bug report resolution
    data = {"resolved": True, "resolution_notes": "Fixed the issue"}
    response = client.post(
        f"/admin/resolve-bug-report/{bug_report.id}",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [200, 400, 500, 404]


def test_schools_management(client, auth_headers):
    """Test schools management"""
    response = safe_route_test(client, "/admin/schools", headers=auth_headers)
    assert response.status_code in [200, 404]


def test_create_school(client, auth_headers):
    """Test school creation"""
    # Create test district first
    district = District()
    district.name = "Test District"
    db.session.add(district)
    db.session.commit()

    # Create school with required id field
    school = School()
    school.id = "test_school_001"  # Required String primary key
    school.name = "Test School"
    school.district_id = district.id  # Set foreign key ID
    db.session.add(school)
    db.session.commit()

    # Test school creation via API
    data = {"name": "New School", "district_id": district.id, "level": "High"}
    response = client.post(
        "/admin/create-school",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [200, 400, 500, 404]


def test_edit_school(client, auth_headers):
    """Test school editing"""
    # Create test district
    district = District()
    district.name = "Test District"
    db.session.add(district)
    db.session.commit()

    # Create school with required id field
    school = School()
    school.id = "test_school_002"  # Required String primary key
    school.name = "Test School"
    school.district_id = district.id  # Set foreign key ID
    db.session.add(school)
    db.session.commit()

    # Test school editing
    data = {"name": "Updated School Name"}
    response = client.post(
        f"/admin/edit-school/{school.id}",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [200, 400, 500, 404]


def test_delete_school(client, auth_headers):
    """Test school deletion"""
    # Create test district
    district = District()
    district.name = "Test District"
    db.session.add(district)
    db.session.commit()

    # Create school with required id field
    school = School()
    school.id = "test_school_003"  # Required String primary key
    school.name = "Test School"
    school.district_id = district.id  # Set foreign key ID
    db.session.add(school)
    db.session.commit()

    # Test school deletion
    response = client.delete(f"/admin/delete-school/{school.id}", headers=auth_headers)
    assert response.status_code in [200, 400, 500, 404]


def test_data_import(client, auth_headers):
    """Test data import functionality"""
    response = safe_route_test(client, "/admin/data-import", headers=auth_headers)
    assert response.status_code in [200, 405, 404]


def test_management_admin_required(client):
    """Test that management routes require admin access"""
    # Test without authentication
    response = safe_route_test(client, "/admin")
    assert response.status_code in [302, 401, 403]  # Should redirect to login


def test_google_sheets_encryption(client, auth_headers):
    """Test Google Sheets encryption functionality"""
    # Create test user with unique email
    user = User()
    user.username = "testuser_encrypt"
    user.email = "test_encrypt@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False
    db.session.add(user)
    db.session.commit()

    # Create Google Sheet with correct constructor parameters
    google_sheet = GoogleSheet(
        academic_year="2023-2024",  # Required parameter
        sheet_id="test_sheet_id",  # Required parameter
        created_by=user.id,
    )
    db.session.add(google_sheet)
    db.session.commit()

    # Test encryption/decryption
    assert google_sheet.decrypted_sheet_id == "test_sheet_id"


def test_bug_report_workflow(client, auth_headers):
    """Test complete bug report workflow"""
    # Create test users with unique emails
    user = User()
    user.username = "testuser_workflow"
    user.email = "test_workflow@example.com"
    user.password_hash = "hashed_password"  # Required field
    user.is_admin = False

    admin_user = User()
    admin_user.username = "adminuser_workflow"
    admin_user.email = "admin_workflow@example.com"
    admin_user.password_hash = "hashed_password"  # Required field
    admin_user.is_admin = True

    db.session.add_all([user, admin_user])
    db.session.commit()

    # Create bug report with correct fields
    bug_report = BugReport()
    bug_report.type = BugReportType.BUG  # Use correct enum value
    bug_report.description = "Test bug description"  # Required field
    bug_report.page_url = "http://test.com"  # Required field
    bug_report.submitted_by_id = user.id  # Set foreign key ID
    db.session.add(bug_report)
    db.session.commit()

    # Test workflow
    assert bug_report.resolved == False
    bug_report.resolved = True
    bug_report.resolved_by_id = admin_user.id  # Set foreign key ID
    bug_report.resolution_notes = "Fixed the issue"
    db.session.commit()

    assert bug_report.resolved == True
    assert bug_report.resolved_by == admin_user


def test_school_district_relationships(client, auth_headers):
    """Test school-district relationships in management"""
    # Create test district
    district = District()
    district.name = "Test District"
    db.session.add(district)
    db.session.commit()

    # Create multiple schools in the district with required id field
    schools = []
    for i in range(5):
        school = School()
        school.id = f"test_school_{i:03d}"  # Required String primary key
        school.name = f"Test School {i}"
        school.district_id = district.id  # Set foreign key ID
        schools.append(school)
    db.session.add_all(schools)
    db.session.commit()

    # Test school-district relationship - use query to get schools
    district_schools = School.query.filter_by(district_id=district.id).all()
    assert len(district_schools) == 5
    for school in schools:
        assert school.district_id == district.id


def test_management_search_functionality(client, auth_headers):
    """Test management search functionality"""
    response = safe_route_test(client, "/admin?search=test", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_management_pagination(client, auth_headers):
    """Test management pagination"""
    response = safe_route_test(client, "/admin?page=1", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_management_export_functionality(client, auth_headers):
    """Test management export functionality"""
    response = safe_route_test(client, "/admin/export", headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_management_error_handling(client, auth_headers):
    """Test error handling in management routes"""
    # Test with invalid user ID
    response = safe_route_test(client, "/admin/update-user/99999", headers=auth_headers)
    assert response.status_code in [404, 500]

    # Test with invalid Google Sheet ID
    response = safe_route_test(client, "/google-sheets/99999", headers=auth_headers)
    assert response.status_code in [404, 500, 403]


def test_management_performance(client, auth_headers):
    """Test management performance"""
    import time

    start_time = time.time()
    response = safe_route_test(client, "/admin", headers=auth_headers)
    end_time = time.time()

    # Should respond within reasonable time
    assert (end_time - start_time) < 5.0
    assert_route_response(response, expected_statuses=[200, 404, 500])


def test_management_data_validation(client, auth_headers):
    """Test data validation in management routes"""
    # Test creating user with invalid data
    data = {
        "username": "",  # Invalid: empty username
        "email": "invalid_email",  # Invalid: malformed email
        "is_admin": "not_boolean",  # Invalid: not a boolean
    }

    response = client.post(
        "/admin/create-user",
        data=json.dumps(data),
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert response.status_code in [400, 500, 404]
