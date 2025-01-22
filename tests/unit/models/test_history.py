import pytest
from datetime import datetime
from models.history import History
from models import db
from models.event import Event
from models.volunteer import Volunteer

def test_new_history(app, test_event, test_volunteer):
    """Test creating a new history record"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
                action='test_action',
                summary='Test summary',
                description='Test description',
                activity_type='Test Activity',
                activity_date=datetime.utcnow(),
                activity_status='Completed',
                salesforce_id='a005f000003XNa7AAG'
            )
            
            db.session.add(history)
            db.session.flush()
            
            # Basic assertions
            assert history.id is not None
            assert history.event_id == event.id
            assert history.volunteer_id == volunteer.id
            assert history.action == 'test_action'
            assert history.summary == 'Test summary'
            assert history.description == 'Test description'
            assert history.activity_type == 'Test Activity'
            assert isinstance(history.activity_date, datetime)
            assert history.activity_status == 'Completed'
            assert history.salesforce_id == 'a005f000003XNa7AAG'
            assert history.is_deleted is False
            assert isinstance(history.created_at, datetime)
            assert isinstance(history.last_modified_at, datetime)
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_history_relationships(app, test_event, test_volunteer):
    """Test history relationships with Event and Volunteer"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
                action='test_relationship',
                summary='Test relationship summary'
            )
            db.session.add(history)
            db.session.flush()
            
            # Test relationship with Event
            assert history.event_id == event.id
            assert history in event.histories.all()
            
            # Test relationship with Volunteer
            assert history.volunteer_id == volunteer.id
            assert history in volunteer.histories.all()
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_history_cascade_delete(app, test_event, test_volunteer):
    """Test cascade delete behavior"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
                action='test_cascade',
                summary='Test cascade summary'
            )
            db.session.add(history)
            db.session.flush()
            
            # Get the history ID for later verification
            history_id = history.id
            
            # Delete the volunteer (should cascade to history)
            db.session.delete(volunteer)
            db.session.flush()
            
            # Verify history record was deleted
            deleted_history = db.session.get(History, history_id)
            assert deleted_history is None
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_history_soft_delete(app, test_event, test_volunteer):
    """Test soft delete functionality"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
                action='test_soft_delete',
                summary='Test soft delete summary'
            )
            db.session.add(history)
            db.session.flush()
            
            # Soft delete the record
            history.is_deleted = True
            db.session.flush()
            
            # Verify the record still exists but is marked as deleted
            assert history.is_deleted is True
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close()

def test_history_timestamps(app, test_event, test_volunteer):
    """Test timestamp behavior"""
    with app.app_context():
        db.session.remove()
        db.session.begin()
        
        # Get fresh instances in this session
        event = db.session.get(Event, test_event.id)
        volunteer = db.session.get(Volunteer, test_volunteer.id)
        
        try:
            history = History(
                event_id=event.id,
                volunteer_id=volunteer.id,
                action='test_timestamps',
                summary='Test timestamps summary'
            )
            db.session.add(history)
            db.session.flush()
            
            # Store initial timestamps
            created_at = history.created_at
            last_modified = history.last_modified_at
            
            # Update the record
            history.summary = 'Updated summary'
            db.session.flush()
            
            # Verify timestamps
            assert history.created_at == created_at  # Should not change
            assert history.last_modified_at > last_modified  # Should be updated
            
            db.session.commit()
        except:
            db.session.rollback()
            raise
        finally:
            db.session.close() 