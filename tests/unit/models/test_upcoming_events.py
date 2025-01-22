import pytest
from models.upcoming_events import UpcomingEvent
from models import db
from datetime import datetime, timezone

def test_new_upcoming_event(app):
    """Test creating a new upcoming event"""
    with app.app_context():
        event = UpcomingEvent(
            salesforce_id='a005f000003TEST123',
            name='Test Event',
            available_slots=10,
            filled_volunteer_jobs=5,
            date_and_time='01/01/2024 09:00 AM to 11:00 AM',
            event_type='In Person',
            registration_link='https://example.com/register',
            display_on_website=True,
            start_date=datetime(2024, 1, 1, 9, 0)
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Test basic fields
        assert event.id is not None
        assert event.salesforce_id == 'a005f000003TEST123'
        assert event.name == 'Test Event'
        assert event.available_slots == 10
        assert event.filled_volunteer_jobs == 5
        assert event.date_and_time == '01/01/2024 09:00 AM to 11:00 AM'
        assert event.event_type == 'In Person'
        assert event.registration_link == 'https://example.com/register'
        assert event.display_on_website is True
        assert event.start_date == datetime(2024, 1, 1, 9, 0)
        
        # Test timestamps
        assert event.created_at is not None
        assert event.updated_at is not None
        
        # Cleanup
        db.session.delete(event)
        db.session.commit()

def test_to_dict(app, test_upcoming_event):
    """Test the to_dict method"""
    with app.app_context():
        event_dict = test_upcoming_event.to_dict()
        
        assert event_dict['Id'] == test_upcoming_event.salesforce_id
        assert event_dict['Name'] == test_upcoming_event.name
        assert event_dict['Available_Slots__c'] == test_upcoming_event.available_slots
        assert event_dict['Filled_Volunteer_Jobs__c'] == test_upcoming_event.filled_volunteer_jobs
        assert event_dict['Date_and_Time_for_Cal__c'] == test_upcoming_event.date_and_time
        assert event_dict['Session_Type__c'] == test_upcoming_event.event_type
        assert event_dict['Registration_Link__c'] == test_upcoming_event.registration_link
        assert event_dict['Display_on_Website__c'] == test_upcoming_event.display_on_website
        assert event_dict['Start_Date__c'] == test_upcoming_event.start_date.isoformat()

def test_upsert_from_salesforce(app):
    """Test the upsert_from_salesforce classmethod"""
    with app.app_context():
        sf_data = [{
            'Id': 'a005f000003TEST456',
            'Name': 'Salesforce Event',
            'Available_Slots__c': '15',
            'Filled_Volunteer_Jobs__c': '7',
            'Date_and_Time_for_Cal__c': '01/02/2024 10:00 AM to 12:00 PM',
            'Session_Type__c': 'Virtual',
            'Registration_Link__c': 'https://example.com/register/sf',
            'Display_on_Website__c': 'Yes',
            'Start_Date__c': '2024-01-02'
        }]
        
        # Test creating new record
        new_count, updated_count = UpcomingEvent.upsert_from_salesforce(sf_data)
        assert new_count == 1
        assert updated_count == 0
        
        # Verify record was created
        event = UpcomingEvent.query.filter_by(salesforce_id='a005f000003TEST456').first()
        assert event is not None
        assert event.name == 'Salesforce Event'
        assert event.display_on_website is True
        
        # Test updating existing record
        sf_data[0]['Name'] = 'Updated Event'
        sf_data[0]['Display_on_Website__c'] = 'No'  # This shouldn't change existing record
        new_count, updated_count = UpcomingEvent.upsert_from_salesforce(sf_data)
        assert new_count == 0
        assert updated_count == 1
        
        # Verify record was updated
        event = UpcomingEvent.query.filter_by(salesforce_id='a005f000003TEST456').first()
        assert event.name == 'Updated Event'
        assert event.display_on_website is True  # Should not have changed
        
        # Test date parsing error handling
        sf_data[0]['Start_Date__c'] = 'invalid-date'
        new_count, updated_count = UpcomingEvent.upsert_from_salesforce(sf_data)
        assert new_count == 0
        assert updated_count == 1
        
        # Cleanup
        db.session.query(UpcomingEvent).delete()
        db.session.commit() 