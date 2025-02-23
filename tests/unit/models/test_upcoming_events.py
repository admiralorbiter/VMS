import pytest
from models.upcoming_events import UpcomingEvent
from models import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_

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

def test_validate_slots(app):
    """Test slot validation"""
    with app.app_context():
        # Test valid integer inputs
        event = UpcomingEvent(
            salesforce_id='test123',
            name='Test Event',
            available_slots=10,
            filled_volunteer_jobs=5
        )
        assert event.available_slots == 10
        assert event.filled_volunteer_jobs == 5

        # Test float inputs from Salesforce
        event = UpcomingEvent(
            salesforce_id='test124',
            name='Test Event',
            available_slots=10.0,
            filled_volunteer_jobs=5.0
        )
        assert event.available_slots == 10
        assert event.filled_volunteer_jobs == 5

        # Test string inputs from Salesforce
        event = UpcomingEvent(
            salesforce_id='test125',
            name='Test Event',
            available_slots="10",
            filled_volunteer_jobs="5"
        )
        assert event.available_slots == 10
        assert event.filled_volunteer_jobs == 5

        # Test filled slots exceeding available (should be allowed based on Salesforce data)
        event = UpcomingEvent(
            salesforce_id='test126',
            name='Test Event',
            available_slots=5,
            filled_volunteer_jobs=10
        )
        assert event.available_slots == 5
        assert event.filled_volunteer_jobs == 10

        # Test negative values
        with pytest.raises(ValueError):
            UpcomingEvent(
                salesforce_id='test127',
                name='Test Event',
                available_slots=-1
            )

def test_validate_registration_link(app):
    """Test registration link validation"""
    with app.app_context():
        # Test HTML anchor tag
        event = UpcomingEvent(
            salesforce_id='test123',
            name='Test Event',
            registration_link='<a href="https://example.com">Sign up</a>'
        )
        assert event.registration_link == 'https://example.com'

        # Test raw URL
        event = UpcomingEvent(
            salesforce_id='test124',
            name='Test Event',
            registration_link='https://example.com'
        )
        assert event.registration_link == 'https://example.com'

        # Test invalid URL
        with pytest.raises(ValueError):
            UpcomingEvent(
                salesforce_id='test125',
                name='Test Event',
                registration_link='not-a-url'
            )

def test_past_events_deletion(app):
    """Test deletion of past events"""
    with app.app_context():
        # Create past event
        past_event = UpcomingEvent(
            salesforce_id='past123',
            name='Past Event',
            start_date=datetime.now(timezone.utc) - timedelta(days=2)
        )
        
        # Create future event
        future_event = UpcomingEvent(
            salesforce_id='future123',
            name='Future Event',
            start_date=datetime.now(timezone.utc) + timedelta(days=2)
        )
        
        db.session.add(past_event)
        db.session.add(future_event)
        db.session.commit()

        # Delete past events
        yesterday = datetime.now().date() - timedelta(days=1)
        deleted_count = UpcomingEvent.query.filter(
            or_(
                UpcomingEvent.start_date < yesterday,
                UpcomingEvent.available_slots <= 0
            )
        ).delete()
        db.session.commit()

        assert deleted_count == 1
        assert UpcomingEvent.query.count() == 1
        assert UpcomingEvent.query.first().salesforce_id == 'future123'

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
            'Registration_Link__c': '<a href="https://example.com/register/sf">Sign up</a>',
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
        assert event.registration_link == 'https://example.com/register/sf'
        
        # Test updating existing record
        sf_data[0]['Name'] = 'Updated Event'
        sf_data[0]['Display_on_Website__c'] = 'No'  # This shouldn't change existing record
        new_count, updated_count = UpcomingEvent.upsert_from_salesforce(sf_data)
        assert new_count == 0
        assert updated_count == 1
        
        # Verify record was updated but display_on_website wasn't changed
        event = UpcomingEvent.query.filter_by(salesforce_id='a005f000003TEST456').first()
        assert event.name == 'Updated Event'
        assert event.display_on_website is True
        
        # Cleanup
        db.session.query(UpcomingEvent).delete()
        db.session.commit()

def test_event_visibility_and_deletion_rules(app):
    """Test comprehensive event visibility and deletion rules"""
    with app.app_context():
        # Setup test events
        events = [
            # Past event
            UpcomingEvent(
                salesforce_id='past123',
                name='Past Event',
                start_date=datetime.now(timezone.utc) - timedelta(days=2),
                display_on_website=True,
                available_slots=5
            ),
            # Future event with no slots
            UpcomingEvent(
                salesforce_id='future_no_slots',
                name='Future No Slots',
                start_date=datetime.now(timezone.utc) + timedelta(days=2),
                display_on_website=True,
                available_slots=0
            ),
            # Future event with slots but not displayed
            UpcomingEvent(
                salesforce_id='future_hidden',
                name='Future Hidden',
                start_date=datetime.now(timezone.utc) + timedelta(days=2),
                display_on_website=False,
                available_slots=5
            ),
            # Future event with slots and displayed
            UpcomingEvent(
                salesforce_id='future_visible',
                name='Future Visible',
                start_date=datetime.now(timezone.utc) + timedelta(days=2),
                display_on_website=True,
                available_slots=5
            )
        ]
        
        # Add all events
        for event in events:
            db.session.add(event)
        db.session.commit()

        # Test deletion rules
        yesterday = datetime.now().date() - timedelta(days=1)
        deleted_count = UpcomingEvent.query.filter(
            or_(
                UpcomingEvent.start_date < yesterday,
                UpcomingEvent.available_slots <= 0
            )
        ).delete()
        db.session.commit()

        # Should delete past event and no slots event
        assert deleted_count == 2
        
        # Test visibility rules
        visible_events = UpcomingEvent.query.filter_by(display_on_website=True).all()
        assert len(visible_events) == 1
        assert visible_events[0].salesforce_id == 'future_visible'

        # Verify remaining events
        all_events = UpcomingEvent.query.all()
        assert len(all_events) == 2  # future_hidden and future_visible
        
        # Cleanup
        db.session.query(UpcomingEvent).delete()
        db.session.commit()

def test_visibility_toggle(app):
    """Test toggling event visibility"""
    with app.app_context():
        event = UpcomingEvent(
            salesforce_id='test123',
            name='Test Event',
            start_date=datetime.now(timezone.utc) + timedelta(days=2),
            display_on_website=False,
            available_slots=5
        )
        db.session.add(event)
        db.session.commit()

        # Test toggling visibility
        event.display_on_website = True
        db.session.commit()
        
        # Verify visibility in queries
        visible_events = UpcomingEvent.query.filter_by(display_on_website=True).all()
        assert len(visible_events) == 1
        assert visible_events[0].salesforce_id == 'test123'

        # Cleanup
        db.session.delete(event)
        db.session.commit() 