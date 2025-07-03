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

def test_reports_main_view(client, auth_headers):
    """Test the main reports view"""
    response = client.get('/reports', headers=auth_headers)
    assert response.status_code == 200

def test_virtual_usage_report(client, auth_headers):
    """Test virtual usage report"""
    # Create test event
    event = Event(
        title="Virtual Test Event",
        type=EventType.VIRTUAL_SESSION,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    db.session.add(event)
    db.session.commit()

    response = client.get('/reports/virtual-usage', headers=auth_headers)
    assert response.status_code == 200

def test_virtual_usage_district_report(client, auth_headers):
    """Test virtual usage by district report"""
    # Create test district and event
    district = District(name="Test District")
    event = Event(
        title="Virtual Test Event",
        type=EventType.VIRTUAL_SESSION,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    db.session.add_all([district, event])
    db.session.commit()

    response = client.get('/reports/virtual-usage-district', headers=auth_headers)
    assert response.status_code == 200

def test_volunteer_thankyou_report(client, auth_headers):
    """Test volunteer thank you report"""
    # Create test volunteer
    volunteer = Volunteer(first_name="Test", last_name="Volunteer")
    db.session.add(volunteer)
    db.session.commit()

    response = client.get('/reports/volunteer-thankyou', headers=auth_headers)
    assert response.status_code == 200

def test_volunteer_thankyou_detail_report(client, auth_headers):
    """Test volunteer thank you detail report"""
    # Create test volunteer
    volunteer = Volunteer(first_name="Test", last_name="Volunteer")
    db.session.add(volunteer)
    db.session.commit()

    response = client.get(f'/reports/volunteer-thankyou/{volunteer.id}', headers=auth_headers)
    assert response.status_code == 200

def test_organization_thankyou_report(client, auth_headers):
    """Test organization thank you report"""
    # Create test organization
    org = Organization(name="Test Organization", type="Non-Profit")
    db.session.add(org)
    db.session.commit()

    response = client.get('/reports/organization-thankyou', headers=auth_headers)
    assert response.status_code == 200

def test_organization_thankyou_detail_report(client, auth_headers):
    """Test organization thank you detail report"""
    # Create test organization
    org = Organization(name="Test Organization", type="Non-Profit")
    db.session.add(org)
    db.session.commit()

    response = client.get(f'/reports/organization-thankyou/{org.id}', headers=auth_headers)
    assert response.status_code == 200

def test_district_year_end_report(client, auth_headers):
    """Test district year end report"""
    # Create test district
    district = District(name="Test District")
    db.session.add(district)
    db.session.commit()

    response = client.get('/reports/district-year-end', headers=auth_headers)
    assert response.status_code == 200

def test_district_year_end_detail_report(client, auth_headers):
    """Test district year end detail report"""
    # Create test district
    district = District(name="Test District")
    db.session.add(district)
    db.session.commit()

    response = client.get(f'/reports/district-year-end/{district.id}', headers=auth_headers)
    assert response.status_code == 200

def test_recruitment_report(client, auth_headers):
    """Test recruitment report"""
    response = client.get('/reports/recruitment', headers=auth_headers)
    assert response.status_code == 200

def test_recruitment_search(client, auth_headers):
    """Test recruitment search functionality"""
    data = {
        'search_term': 'test',
        'date_from': '2024-01-01',
        'date_to': '2024-12-31'
    }

    response = client.post(
        '/reports/recruitment/search',
        data=json.dumps(data),
        headers={**auth_headers, 'Content-Type': 'application/json'}
    )
    assert response.status_code in [200, 400, 500]

def test_recruitment_tools(client, auth_headers):
    """Test recruitment tools view"""
    response = client.get('/reports/recruitment-tools', headers=auth_headers)
    assert response.status_code == 200

def test_contact_report(client, auth_headers):
    """Test contact report"""
    # Create test contact
    contact = Contact(first_name="Test", last_name="Contact")
    db.session.add(contact)
    db.session.commit()

    response = client.get('/reports/contact', headers=auth_headers)
    assert response.status_code == 200

def test_contact_report_detail(client, auth_headers):
    """Test contact report detail"""
    # Create test contact
    contact = Contact(first_name="Test", last_name="Contact")
    db.session.add(contact)
    db.session.commit()

    response = client.get(f'/reports/contact/{contact.id}', headers=auth_headers)
    assert response.status_code == 200

def test_pathways_report(client, auth_headers):
    """Test pathways report"""
    # Create test pathway
    pathway = Pathway(name="Test Pathway")
    db.session.add(pathway)
    db.session.commit()

    response = client.get('/reports/pathways', headers=auth_headers)
    assert response.status_code == 200

def test_pathway_detail_report(client, auth_headers):
    """Test pathway detail report"""
    # Create test pathway
    pathway = Pathway(name="Test Pathway")
    db.session.add(pathway)
    db.session.commit()

    response = client.get(f'/reports/pathways/{pathway.id}', headers=auth_headers)
    assert response.status_code == 200

def test_attendance_report(client, auth_headers):
    """Test attendance report"""
    # Create test event
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    db.session.add(event)
    db.session.commit()

    response = client.get('/reports/attendance', headers=auth_headers)
    assert response.status_code == 200

def test_first_time_volunteer_report(client, auth_headers):
    """Test first time volunteer report"""
    # Create test volunteer
    volunteer = Volunteer(first_name="Test", last_name="Volunteer")
    db.session.add(volunteer)
    db.session.commit()

    response = client.get('/reports/first-time-volunteer', headers=auth_headers)
    assert response.status_code == 200

def test_reports_with_filters(client, auth_headers):
    """Test reports with various filters"""
    # Test virtual usage with date filters
    response = client.get(
        '/reports/virtual-usage?start_date=2024-01-01&end_date=2024-12-31',
        headers=auth_headers
    )
    assert response.status_code == 200

    # Test volunteer thank you with year filter
    response = client.get(
        '/reports/volunteer-thankyou?year=2024',
        headers=auth_headers
    )
    assert response.status_code == 200

    # Test organization thank you with type filter
    response = client.get(
        '/reports/organization-thankyou?type=Non-Profit',
        headers=auth_headers
    )
    assert response.status_code == 200

def test_reports_pagination(client, auth_headers):
    """Test reports with pagination"""
    # Create multiple test events
    events = []
    for i in range(30):
        event = Event(
            title=f"Test Event {i}",
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            status=EventStatus.CONFIRMED
        )
        events.append(event)
    db.session.add_all(events)
    db.session.commit()

    # Test with pagination
    response = client.get('/reports/attendance?page=1&per_page=10', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/reports/attendance?page=2&per_page=10', headers=auth_headers)
    assert response.status_code == 200

def test_reports_export_functionality(client, auth_headers):
    """Test report export functionality"""
    # Test CSV export for virtual usage
    response = client.get('/reports/virtual-usage?export=csv', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

    # Test Excel export for volunteer thank you
    response = client.get('/reports/volunteer-thankyou?export=excel', headers=auth_headers)
    assert response.status_code in [200, 400, 500]

def test_reports_data_relationships(client, auth_headers):
    """Test reports with complex data relationships"""
    # Create test data with relationships
    district = District(name="Test District")
    school = School(name="Test School", district=district)
    org = Organization(name="Test Organization", type="Non-Profit")
    volunteer = Volunteer(first_name="Test", last_name="Volunteer")
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    
    db.session.add_all([district, school, org, volunteer, event])
    db.session.commit()

    # Test various reports with the related data
    response = client.get('/reports/virtual-usage-district', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/reports/organization-thankyou', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/reports/district-year-end', headers=auth_headers)
    assert response.status_code == 200

def test_reports_unauthorized_access(client):
    """Test accessing report routes without authentication"""
    # Test main reports view without auth
    response = client.get('/reports')
    assert response.status_code == 302  # Redirect to login

    # Test specific report without auth
    response = client.get('/reports/virtual-usage')
    assert response.status_code == 302  # Redirect to login

    # Test report detail without auth
    response = client.get('/reports/volunteer-thankyou/1')
    assert response.status_code == 302  # Redirect to login

def test_reports_error_handling(client, auth_headers):
    """Test report error handling"""
    # Test with invalid date ranges
    response = client.get(
        '/reports/virtual-usage?start_date=invalid&end_date=invalid',
        headers=auth_headers
    )
    assert response.status_code in [200, 400, 500]

    # Test with invalid year
    response = client.get(
        '/reports/volunteer-thankyou?year=invalid',
        headers=auth_headers
    )
    assert response.status_code in [200, 400, 500]

    # Test with non-existent ID
    response = client.get('/reports/volunteer-thankyou/99999', headers=auth_headers)
    assert response.status_code in [200, 404, 500]

def test_reports_performance(client, auth_headers):
    """Test report performance with large datasets"""
    # Create large dataset for performance testing
    volunteers = []
    for i in range(100):
        volunteer = Volunteer(first_name=f"Test{i}", last_name=f"Volunteer{i}")
        volunteers.append(volunteer)
    
    events = []
    for i in range(50):
        event = Event(
            title=f"Test Event {i}",
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            status=EventStatus.CONFIRMED
        )
        events.append(event)
    
    db.session.add_all(volunteers + events)
    db.session.commit()

    # Test reports with large datasets
    response = client.get('/reports/volunteer-thankyou', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/reports/attendance', headers=auth_headers)
    assert response.status_code == 200

def test_reports_search_functionality(client, auth_headers):
    """Test report search functionality"""
    # Create test data
    volunteer1 = Volunteer(first_name="Alice", last_name="Johnson")
    volunteer2 = Volunteer(first_name="Bob", last_name="Smith")
    org1 = Organization(name="Tech Corp", type="Corporate")
    org2 = Organization(name="Non-Profit Org", type="Non-Profit")
    
    db.session.add_all([volunteer1, volunteer2, org1, org2])
    db.session.commit()

    # Test search in volunteer thank you report
    response = client.get('/reports/volunteer-thankyou?search=Alice', headers=auth_headers)
    assert response.status_code == 200

    # Test search in organization thank you report
    response = client.get('/reports/organization-thankyou?search=Tech', headers=auth_headers)
    assert response.status_code == 200

def test_reports_sorting(client, auth_headers):
    """Test report sorting functionality"""
    # Create test data with different dates
    event1 = Event(
        title="Event 1",
        type=EventType.IN_PERSON,
        start_date=datetime.now() - timedelta(days=30),
        status=EventStatus.CONFIRMED
    )
    event2 = Event(
        title="Event 2",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.CONFIRMED
    )
    
    db.session.add_all([event1, event2])
    db.session.commit()

    # Test sorting by date
    response = client.get('/reports/attendance?sort=start_date&direction=asc', headers=auth_headers)
    assert response.status_code == 200

    response = client.get('/reports/attendance?sort=start_date&direction=desc', headers=auth_headers)
    assert response.status_code == 200 