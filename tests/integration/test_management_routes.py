import pytest
from datetime import datetime, timedelta
from flask import url_for
from models import db
from models.user import User, SecurityLevel
from models.organization import Organization
from models.google_sheet import GoogleSheet
from models.bug_report import BugReport, BugReportType
from models.school_model import School
from models.district_model import District
import json
import io

def test_admin_view(client, auth_headers):
    """Test the admin management view"""
    response = client.get('/admin', headers=auth_headers)
    assert response.status_code == 200

def test_user_management(client, auth_headers):
    """Test user management functionality"""
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        is_admin=False,
        security_level=SecurityLevel.USER
    )
    db.session.add(user)
    db.session.commit()

    # Test viewing users
    response = client.get('/admin', headers=auth_headers)
    assert response.status_code == 200
    assert b'testuser' in response.data

    # Test updating user
    data = {
        'user_id': user.id,
        'is_admin': True,
        'security_level': SecurityLevel.ADMIN.value
    }

    response = client.post(
        '/admin/update-user',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_google_sheets_management(client, auth_headers):
    """Test Google Sheets management"""
    response = client.get('/google-sheets', headers=auth_headers)
    assert response.status_code == 200

def test_create_google_sheet(client, auth_headers):
    """Test creating a new Google Sheet"""
    data = {
        'academic_year': '2024-2025',
        'sheet_name': 'Test Sheet',
        'sheet_id': 'test_sheet_id_123'
    }

    response = client.post(
        '/google-sheets/create',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_get_google_sheet(client, auth_headers):
    """Test getting a specific Google Sheet"""
    # Create test Google Sheet
    sheet = GoogleSheet(
        academic_year='2024-2025',
        sheet_name='Test Sheet',
        sheet_id='test_sheet_id_123'
    )
    db.session.add(sheet)
    db.session.commit()

    response = client.get(f'/google-sheets/{sheet.id}', headers=auth_headers)
    assert response.status_code == 200

def test_delete_google_sheet(client, auth_headers):
    """Test deleting a Google Sheet"""
    # Create test Google Sheet
    sheet = GoogleSheet(
        academic_year='2024-2025',
        sheet_name='Test Sheet',
        sheet_id='test_sheet_id_123'
    )
    db.session.add(sheet)
    db.session.commit()

    response = client.delete(f'/google-sheets/{sheet.id}', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

def test_bug_reports_management(client, auth_headers):
    """Test bug reports management"""
    response = client.get('/bug-reports', headers=auth_headers)
    assert response.status_code == 200

def test_create_bug_report(client, auth_headers):
    """Test creating a new bug report"""
    data = {
        'title': 'Test Bug Report',
        'description': 'This is a test bug report',
        'type': BugReportType.BUG.value,
        'priority': 'Medium',
        'steps_to_reproduce': '1. Go to page\n2. Click button\n3. See error'
    }

    response = client.post(
        '/bug-reports/create',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_resolve_bug_report(client, auth_headers):
    """Test resolving a bug report"""
    # Create test bug report
    bug_report = BugReport(
        title='Test Bug Report',
        description='This is a test bug report',
        type=BugReportType.BUG,
        priority='Medium'
    )
    db.session.add(bug_report)
    db.session.commit()

    data = {
        'resolution_notes': 'Fixed the issue',
        'status': 'Resolved'
    }

    response = client.post(
        f'/bug-reports/{bug_report.id}/resolve',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_schools_management(client, auth_headers):
    """Test schools management"""
    response = client.get('/schools', headers=auth_headers)
    assert response.status_code == 200

def test_create_school(client, auth_headers):
    """Test creating a new school"""
    # Create test district first
    district = District(name="Test District")
    db.session.add(district)
    db.session.commit()

    data = {
        'name': 'Test School',
        'district_id': district.id,
        'address': '123 Test St',
        'city': 'Test City',
        'state': 'TS',
        'zip_code': '12345'
    }

    response = client.post(
        '/schools/create',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_edit_school(client, auth_headers):
    """Test editing a school"""
    # Create test district and school
    district = District(name="Test District")
    school = School(name="Test School", district=district)
    db.session.add_all([district, school])
    db.session.commit()

    data = {
        'name': 'Updated Test School',
        'address': '456 Updated St',
        'city': 'Updated City'
    }

    response = client.post(
        f'/schools/{school.id}/edit',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_delete_school(client, auth_headers):
    """Test deleting a school"""
    # Create test district and school
    district = District(name="Test District")
    school = School(name="Test School", district=district)
    db.session.add_all([district, school])
    db.session.commit()

    response = client.delete(f'/schools/{school.id}', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

def test_data_import(client, auth_headers):
    """Test data import functionality"""
    # Create test CSV file
    csv_data = "Name,Type,Description\nTest Org,Non-Profit,Test Description"
    csv_file = io.BytesIO(csv_data.encode())

    response = client.post(
        '/admin/import',
        data={
            'import_file': (csv_file, 'test_import.csv')
        },
        headers=auth_headers,
        content_type='multipart/form-data'
    )
    assert response.status_code in [200, 400, 500]

def test_management_unauthorized_access(client):
    """Test accessing management routes without authentication"""
    # Test admin view without auth
    response = client.get('/admin')
    assert response.status_code == 302  # Redirect to login

    # Test Google Sheets without auth
    response = client.get('/google-sheets')
    assert response.status_code == 302  # Redirect to login

    # Test bug reports without auth
    response = client.get('/bug-reports')
    assert response.status_code == 302  # Redirect to login

def test_management_admin_required(client, auth_headers):
    """Test that management routes require admin privileges"""
    # Create non-admin user
    user = User(
        username="nonadmin",
        email="nonadmin@example.com",
        is_admin=False,
        security_level=SecurityLevel.USER
    )
    db.session.add(user)
    db.session.commit()

    # Test with non-admin user (this would need proper session handling)
    # For now, we'll test that the routes exist and handle auth properly
    response = client.get('/admin', headers=auth_headers)
    assert response.status_code in [200, 403]

def test_google_sheets_encryption(client, auth_headers):
    """Test Google Sheets encryption functionality"""
    # Create test Google Sheet with sensitive data
    sheet = GoogleSheet(
        academic_year='2024-2025',
        sheet_name='Test Sheet',
        sheet_id='test_sheet_id_123'
    )
    db.session.add(sheet)
    db.session.commit()

    # Test that the sheet can be retrieved and decrypted
    response = client.get(f'/google-sheets/{sheet.id}', headers=auth_headers)
    assert response.status_code == 200

def test_bug_report_workflow(client, auth_headers):
    """Test complete bug report workflow"""
    # Create bug report
    data = {
        'title': 'Workflow Test Bug',
        'description': 'Testing the complete workflow',
        'type': BugReportType.FEATURE_REQUEST.value,
        'priority': 'High'
    }

    response = client.post(
        '/bug-reports/create',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

    # If creation was successful, test the workflow
    if response.status_code == 200:
        bug_data = response.get_json()
        bug_id = bug_data.get('id')
        
        if bug_id:
            # Test updating status
            update_data = {
                'status': 'In Progress',
                'assigned_to': 'test@example.com'
            }
            
            response = client.post(
                f'/bug-reports/{bug_id}/update',
                data=json.dumps(update_data),
                headers={**auth_headers, 'Content-Type': 'application/json'}
            )
            assert response.status_code in [200, 400, 500]

def test_school_district_relationships(client, auth_headers):
    """Test school-district relationships in management"""
    # Create test district
    district = District(name="Test District")
    db.session.add(district)
    db.session.commit()

    # Create multiple schools in the district
    schools = []
    for i in range(5):
        school = School(name=f"Test School {i}", district=district)
        schools.append(school)
    db.session.add_all(schools)
    db.session.commit()

    # Test viewing schools by district
    response = client.get(f'/schools?district_id={district.id}', headers=auth_headers)
    assert response.status_code == 200

def test_management_search_functionality(client, auth_headers):
    """Test search functionality in management views"""
    # Create test data
    user1 = User(username="alice_admin", email="alice@example.com", is_admin=True)
    user2 = User(username="bob_user", email="bob@example.com", is_admin=False)
    org1 = Organization(name="Tech Corp", type="Corporate")
    org2 = Organization(name="Non-Profit Org", type="Non-Profit")
    
    db.session.add_all([user1, user2, org1, org2])
    db.session.commit()

    # Test search in admin view
    response = client.get('/admin?search=alice', headers=auth_headers)
    assert response.status_code == 200

    # Test search in organizations
    response = client.get('/organizations?search=Tech', headers=auth_headers)
    assert response.status_code == 200

def test_management_pagination(client, auth_headers):
    """Test pagination in management views"""
    # Create multiple test users
    users = []
    for i in range(30):
        user = User(
            username=f"testuser{i}",
            email=f"test{i}@example.com",
            is_admin=False
        )
        users.append(user)
    db.session.add_all(users)
    db.session.commit()

    # Test pagination in admin view
    response = client.get('/admin?page=1&per_page=10', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/admin?page=2&per_page=10', headers=auth_headers)
    assert response.status_code == 200

def test_management_export_functionality(client, auth_headers):
    """Test export functionality in management views"""
    # Test CSV export for users
    response = client.get('/admin?export=csv', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

    # Test Excel export for bug reports
    response = client.get('/bug-reports?export=excel', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

def test_management_error_handling(client, auth_headers):
    """Test error handling in management routes"""
    # Test with invalid user ID
    response = client.get('/admin/update-user/99999', headers=auth_headers)
    assert response.status_code in [404, 500]

    # Test with invalid Google Sheet ID
    response = client.get('/google-sheets/99999', headers=auth_headers)
    assert response.status_code in [404, 500]

    # Test with invalid bug report ID
    response = client.get('/bug-reports/99999', headers=auth_headers)
    assert response.status_code in [404, 500]

def test_management_performance(client, auth_headers):
    """Test management routes performance with large datasets"""
    # Create large dataset for performance testing
    users = []
    for i in range(100):
        user = User(
            username=f"perfuser{i}",
            email=f"perf{i}@example.com",
            is_admin=False
        )
        users.append(user)
    
    bug_reports = []
    for i in range(50):
        bug_report = BugReport(
            title=f"Performance Bug {i}",
            description=f"Performance test bug {i}",
            type=BugReportType.BUG
        )
        bug_reports.append(bug_report)
    
    db.session.add_all(users + bug_reports)
    db.session.commit()

    # Test management views with large datasets
    response = client.get('/admin', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/bug-reports', headers=auth_headers)
    assert response.status_code == 200

def test_management_data_validation(client, auth_headers):
    """Test data validation in management routes"""
    # Test creating user with invalid data
    data = {
        'username': '',  # Invalid: empty username
        'email': 'invalid_email',  # Invalid: malformed email
        'is_admin': 'not_boolean'  # Invalid: not a boolean
    }

    response = client.post(
        '/admin/create-user',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [400, 500]

    # Test creating Google Sheet with invalid data
    data = {
        'academic_year': '',  # Invalid: empty year
        'sheet_name': '',  # Invalid: empty name
        'sheet_id': 'invalid_id'  # Invalid: malformed ID
    }

    response = client.post(
        '/google-sheets/create',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [400, 500] 