import pytest
from datetime import datetime, timedelta
from models.event import (
    Event, EventComment, EventType, EventFormat, EventStatus, 
    CancellationReason, AttendanceStatus, EventAttendance
)
from models import db
from models.volunteer import Volunteer
from models.district_model import District
from models.volunteer import Skill

def test_new_event(app):
    """Test creating a new event"""
    with app.app_context():
        event = Event(
            title='Test Event',
            description='Test Description',
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            volunteers_needed=5  # Changed from volunteer_needed
        )
        db.session.add(event)
        db.session.commit()
        
        assert event.id is not None
        assert event.title == 'Test Event'
        assert event.description == 'Test Description'
        assert event.type == EventType.IN_PERSON
        assert event.volunteers_needed == 5  # Changed assertion

def test_event_relationships(app, test_event, test_volunteer, test_district, test_skill):
    """Test event relationships with volunteers, districts, and skills"""
    with app.app_context():
        # Start fresh session
        db.session.remove()
        db.session.begin()
        
        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        district = db.session.get(District, test_district.id)
        skill = db.session.get(Skill, test_skill.id)
        
        try:
            # Test volunteer relationship
            event.volunteers.append(volunteer)
            db.session.flush()
            assert event.volunteers_needed == 5
            
            # Test district relationship
            event.districts.append(district)
            db.session.flush()
            assert len(event.districts) == 1
            
            # Test skill relationship
            event.skills.append(skill)
            db.session.flush()
            assert len(event.skills) == 1
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_event_comments(app, test_event):
    """Test event comments"""
    with app.app_context():
        comment = EventComment(
            event_id=test_event.id,
            content='Test comment'
        )
        db.session.add(comment)
        db.session.commit()

        assert len(test_event.comments.all()) == 1
        assert test_event.comments.first().content == 'Test comment'

def test_event_attendance(app, test_event):
    """Test event attendance tracking"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        try:
            # Create attendance record
            attendance = EventAttendance(
                event_id=test_event.id,
                status=AttendanceStatus.IN_PROGRESS,
                total_attendance=10,
                last_taken=datetime.utcnow()
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            # Use db.session.get() instead of query.get()
            event = db.session.get(Event, test_event.id)
            assert event.attendance is not None
            assert event.attendance.status == AttendanceStatus.IN_PROGRESS
            assert event.attendance.total_attendance == 10
            
        except Exception as e:
            db.session.rollback()
            raise e
        finally:
            db.session.close()

def test_event_properties(test_event):
    """Test event property methods"""
    # Test display_status
    assert test_event.display_status == 'Draft'

    # Test salesforce_url
    assert test_event.salesforce_url is None
    test_event.salesforce_id = 'a005f000003XNa7AAG'
    assert test_event.salesforce_url == 'https://prep-kc.lightning.force.com/lightning/r/Session__c/a005f000003XNa7AAG/view'

    # Test is_virtual
    assert not test_event.is_virtual
    test_event.type = EventType.VIRTUAL_SESSION
    assert test_event.is_virtual

@pytest.mark.parametrize('invalid_data', [
    {
        'description': 'Test Description',
        'type': EventType.IN_PERSON,
        'start_date': datetime.utcnow(),
        # Missing required title
    },
    {
        'title': 'Test Event',
        'description': 'Test Description',
        'type': EventType.IN_PERSON,
        # Missing required start_date
    }
])
def test_invalid_event_data(app, invalid_data):
    """Test that invalid event data raises appropriate errors"""
    with app.app_context():
        with pytest.raises(Exception):
            invalid_event = Event(**invalid_data)
            db.session.add(invalid_event)
            db.session.commit()

def test_event_update_from_csv(app, test_event):
    """Test updating event from CSV data"""
    csv_data = {
        'Date': '12/25/2024',
        'Session ID': 'TEST123',
        'Title': 'Updated Event',
        'Series or Event Title': 'Test Series',
        'Status': EventStatus.CONFIRMED,
        'Duration': '60',
        'School': 'Test School',
        'District or Company': 'Test District',
        'Registered Student Count': '20',
        'Attended Student Count': '15',
        'SignUp Role': 'educator',
        'Name': 'Test Educator',
        'User Auth Id': 'EDU123',
        'Volunteers Needed': '8'  # Added this field if you're handling it in update_from_csv
    }
    
    test_event.update_from_csv(csv_data)
    
    assert test_event.session_id == 'TEST123'
    assert test_event.title == 'Updated Event'
    assert test_event.series == 'Test Series'
    assert test_event.status == EventStatus.CONFIRMED
    assert test_event.duration == 60
    assert test_event.school == 'Test School'
    assert test_event.district_partner == 'Test District'
    assert test_event.registered_count == 20
    assert test_event.attended_count == 15
    assert test_event.educators == 'Test Educator'
    assert test_event.educator_ids == 'EDU123'
    assert test_event.volunteers_needed == 8  # Added assertion if handling this in update_from_csv

def test_event_merge_duplicate(app, test_event):
    """Test merging duplicate event data"""
    duplicate_data = {
        'Registered Student Count': '10',
        'Attended Student Count': '8',
        'SignUp Role': 'professional',
        'Name': 'John Doe',
        'District or Company': 'Test Company'
    }
    
    initial_registered = test_event.registered_count
    initial_attended = test_event.attended_count
    
    test_event.merge_duplicate(duplicate_data)
    
    assert test_event.registered_count == initial_registered + 10
    assert test_event.attended_count == initial_attended + 8
    assert len(test_event.volunteers) == 1  # New volunteer should be added 

def test_event_cancellation(app, test_event):
    """Test event cancellation"""
    with app.app_context():
        test_event.status = EventStatus.CANCELLED
        test_event.cancellation_reason = CancellationReason.WEATHER
        db.session.commit()
        
        assert test_event.status == EventStatus.CANCELLED
        assert test_event.cancellation_reason == CancellationReason.WEATHER

def test_event_virtual_fields(app):
    """Test virtual event specific fields"""
    with app.app_context():
        virtual_event = Event(
            title='Virtual Test Event',
            description='Virtual Test Description',
            type=EventType.VIRTUAL_SESSION,
            start_date=datetime.now(),
            status=EventStatus.DRAFT,
            format=EventFormat.VIRTUAL,
            session_id='TEST123',
            series='Test Series',
            duration=60,
            school='Test School',
            district_partner='Test District',
            educators='Test Educator',
            educator_ids='EDU123',
            volunteers_needed=3  # Changed from volunteer_needed
        )
        db.session.add(virtual_event)
        db.session.commit()
        
        assert virtual_event.is_virtual
        assert virtual_event.session_id == 'TEST123'
        assert virtual_event.series == 'Test Series'
        assert virtual_event.duration == 60
        assert virtual_event.volunteers_needed == 3  # Changed assertion
        
        db.session.delete(virtual_event)
        db.session.commit()

def test_event_merge_duplicate_with_educator(app, test_event):
    """Test merging duplicate event data with educator"""
    educator_data = {
        'Registered Student Count': '10',
        'Attended Student Count': '8',
        'SignUp Role': 'educator',
        'Name': 'Jane Smith',
        'User Auth Id': 'EDU456'
    }
    
    test_event.merge_duplicate(educator_data)
    
    assert test_event.educators == 'Jane Smith'
    assert test_event.educator_ids == 'EDU456'

def test_event_merge_duplicate_professional_with_company(app, test_event):
    """Test merging duplicate event data with professional and company"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)
        
        try:
            professional_data = {
                'SignUp Role': 'professional',
                'Name': 'John Professional',
                'District or Company': 'Test Corp'
            }
            
            event.merge_duplicate(professional_data)
            db.session.flush()
            
            # Verify volunteer was created and linked
            assert len(event.volunteers) == 1
            volunteer = event.volunteers[0]
            assert volunteer.first_name == 'John'
            assert volunteer.last_name == 'Professional'
            
            # Verify organization was created and linked
            from models.organization import Organization
            org = Organization.query.filter_by(name='Test Corp').first()
            assert org is not None
            assert volunteer.volunteer_organizations[0].organization.name == 'Test Corp'
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_event_update_from_csv_invalid_date(app, test_event):
    """Test updating event from CSV data with invalid date"""
    invalid_csv_data = {
        # Missing Date field
        'Session ID': 'TEST123'
    }
    
    with pytest.raises(ValueError, match="Date is required"):
        test_event.update_from_csv(invalid_csv_data)

def test_event_update_from_csv_professional(app, test_event):
    """Test updating event from CSV data with professional"""
    csv_data = {
        'Date': '12/25/2024',
        'Title': 'Updated Event',
        'SignUp Role': 'professional',
        'Name': 'Jane Professional',
        'District or Company': 'Test Corp',
        'Status': EventStatus.CONFIRMED,
        'Duration': '60'
    }
    
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Use db.session.get() instead of query.get()
        event = db.session.get(Event, test_event.id)
        
        try:
            with db.session.no_autoflush:
                event.update_from_csv(csv_data)
                db.session.flush()
                
                # Verify volunteer was created and linked
                assert len(event.volunteers) == 1
                volunteer = event.volunteers[0]
                assert volunteer.first_name == 'Jane'
                assert volunteer.last_name == 'Professional'
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_event_update_from_csv_handles_errors(app, test_event):
    """Test handling of errors during CSV update"""
    invalid_csv_data = {
        'Date': '12/25/2024',
        'Status': EventStatus.CONFIRMED
        # Missing Title which is required
    }
    
    with app.app_context():
        db.session.begin_nested()
        try:
            with pytest.raises(ValueError) as exc_info:
                test_event.update_from_csv(invalid_csv_data)
            assert "Title is required" in str(exc_info.value)
            db.session.rollback()
        except:
            db.session.rollback()
            raise 