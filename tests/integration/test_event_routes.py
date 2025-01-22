import pytest
from datetime import datetime, timedelta
from flask import url_for
from models import db
from models.event import Event, EventType, EventStatus, EventFormat, CancellationReason
from models.volunteer import Volunteer, Skill
import json
import io

def test_events_list_view(client, auth_headers):
    """Test the events list view with various filters"""
    # Create test event
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(hours=2),
        status=EventStatus.CONFIRMED,
        format=EventFormat.IN_PERSON
    )
    db.session.add(event)
    db.session.commit()

    # Test basic list view
    response = client.get('/events', headers=auth_headers)
    assert response.status_code == 200
    assert b'Test Event' in response.data

    # Test with filters
    filters = {
        'search': 'Test',
        'type': EventType.IN_PERSON.value,
        'status': EventStatus.CONFIRMED.value,
        'start_date': datetime.now().strftime('%Y-%m-%d'),
        'end_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    }
    response = client.get('/events', query_string=filters, headers=auth_headers)
    assert response.status_code == 200
    assert b'Test Event' in response.data

def test_add_event(client, auth_headers):
    """Test adding a new event"""
    # Create test skills
    skill = Skill(name="Python")
    db.session.add(skill)
    db.session.commit()

    data = {
        'title': 'New Event',
        'type': EventType.IN_PERSON.value,
        'start_date': datetime.now().strftime('%Y-%m-%dT%H:%M'),
        'end_date': (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        'location': 'Test Location',
        'status': EventStatus.DRAFT.value,
        'format': EventFormat.IN_PERSON.value,
        'description': 'Test Description',
        'volunteers_needed': '5',
        'skills[]': [skill.id]
    }

    response = client.post(
        '/events/add',
        data=data,
        headers=auth_headers,
        follow_redirects=True
    )
    assert response.status_code == 200

    # Verify event was created using db.session.get()
    event = Event.query.filter_by(title='New Event').first()  # This is fine as it uses filter_by
    assert event is not None
    assert event.volunteers_needed == 5
    assert len(event.skills) == 1
    assert event.skills[0].name == "Python"

def test_edit_event(client, auth_headers):
    """Test editing an existing event"""
    # Create test event
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(hours=2),
        status=EventStatus.DRAFT,
        format=EventFormat.IN_PERSON
    )
    db.session.add(event)
    db.session.commit()

    # Create test skill
    skill = Skill(name="JavaScript")
    db.session.add(skill)
    db.session.commit()

    data = {
        'title': 'Updated Event',
        'type': EventType.VIRTUAL_SESSION.value,
        'start_date': datetime.now().strftime('%Y-%m-%dT%H:%M'),
        'end_date': (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M'),
        'location': 'New Location',
        'status': EventStatus.CONFIRMED.value,
        'format': EventFormat.VIRTUAL.value,
        'description': 'Updated Description',
        'volunteers_needed': 10,
        'skills[]': [skill.id]
    }

    response = client.post(
        f'/events/edit/{event.id}',
        data=data,
        headers=auth_headers,
        follow_redirects=True
    )
    assert response.status_code == 200

    # Verify event was updated using db.session.get()
    updated_event = db.session.get(Event, event.id)  # Using the new method
    assert updated_event.title == 'Updated Event'
    assert updated_event.type == EventType.VIRTUAL_SESSION
    assert updated_event.volunteers_needed == 10
    assert len(updated_event.skills) == 1
    assert updated_event.skills[0].name == "JavaScript"

def test_delete_event(client, auth_headers):
    """Test deleting an event"""
    # Create test event
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.DRAFT
    )
    db.session.add(event)
    db.session.commit()

    response = client.delete(
        f'/events/delete/{event.id}',
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify event was deleted using session.get()
    deleted_event = db.session.get(Event, event.id)
    assert deleted_event is None

def test_purge_events(client, auth_headers):
    """Test purging all events"""
    # Create test event
    event = Event(
        title="Test Event",
        type=EventType.IN_PERSON,
        start_date=datetime.now(),
        status=EventStatus.DRAFT
    )
    db.session.add(event)
    db.session.commit()

    response = client.post(
        '/events/purge',
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify all events were deleted
    events_count = Event.query.count()
    assert events_count == 0

def test_event_model_properties(app):
    """Test Event model properties and methods"""
    with app.app_context():
        event = Event(
            title="Test Event",
            type=EventType.IN_PERSON,
            start_date=datetime.now(),
            status=EventStatus.DRAFT
        )
        db.session.add(event)
        
        # Add volunteers
        volunteer = Volunteer(first_name="Test", last_name="Volunteer")
        db.session.add(volunteer)
        event.volunteers.append(volunteer)
        db.session.commit()

        # Test volunteer_count property
        assert event.volunteer_count == 1

        # Test CSV data update
        csv_data = {
            'Date': '01/01/2024',
            'Title': 'Updated Title',
            'Series or Event Title': 'Test Series',
            'Duration': '60',
            'Status': 'Confirmed',
            'School': 'Test School',
            'District or Company': 'Test District',
            'Registered Student Count': '20',
            'Attended Student Count': '15',
            'SignUp Role': 'professional',
            'Name': 'John Doe',
            'User Auth Id': 'AUTH123'
        }
        event.update_from_csv(csv_data)
        assert event.title == 'Updated Title'
        assert event.registered_count == 20 