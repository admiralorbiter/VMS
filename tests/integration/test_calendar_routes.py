import pytest
from datetime import datetime, timedelta
from flask import url_for
import json

def test_show_calendar_view(client, auth_headers):
    """Test the calendar view page loads correctly"""
    response = client.get('/calendar', headers=auth_headers)
    assert response.status_code == 200
    assert b'Event Calendar' in response.data

def test_get_calendar_events(client, auth_headers, test_calendar_events):
    """Test the calendar events API endpoint"""
    # Get events for current month
    start_date = datetime.now().replace(day=1).isoformat()
    end_date = (datetime.now() + timedelta(days=32)).replace(day=1).isoformat()
    
    response = client.get(
        f'/calendar/events?start={start_date}&end={end_date}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    events = json.loads(response.data)
    
    # Verify we got a list of events
    assert isinstance(events, list)
    assert len(events) == len(test_calendar_events)
    
    # Check structure of first event
    first_event = events[0]
    assert 'id' in first_event
    assert 'title' in first_event
    assert 'start' in first_event
    assert 'end' in first_event
    assert 'color' in first_event
    assert 'extendedProps' in first_event
    
    # Verify extended properties
    extended_props = first_event['extendedProps']
    assert 'location' in extended_props
    assert 'type' in extended_props
    assert 'status' in extended_props
    assert 'description' in extended_props
    assert 'volunteer_count' in extended_props
    assert 'volunteers_needed' in extended_props
    assert 'format' in extended_props
    assert 'is_past' in extended_props

def test_get_calendar_events_date_filtering(client, auth_headers, test_calendar_events):
    """Test calendar events API with date filtering"""
    # Get only future events
    future_date = (datetime.now() + timedelta(days=1)).isoformat()
    end_date = (datetime.now() + timedelta(days=30)).isoformat()
    
    response = client.get(
        f'/calendar/events?start={future_date}&end={end_date}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    events = json.loads(response.data)
    
    # Should only get future events
    assert len(events) == 1
    assert events[0]['title'] == 'Future Event'

def test_get_calendar_events_status_colors(client, auth_headers, test_calendar_events):
    """Test that events have correct status-based colors"""
    response = client.get('/calendar/events', headers=auth_headers)
    assert response.status_code == 200
    events = json.loads(response.data)
    
    # Create a map of expected colors
    status_color_map = {
        'Completed': '#A0A0A0',
        'Confirmed': '#28a745',
        'Published': '#007bff'
    }
    
    # Verify each event has the correct color based on its status
    for event in events:
        status = event['extendedProps']['status']
        assert event['color'] == status_color_map[status]

def test_get_calendar_events_past_flag(client, auth_headers, test_calendar_events):
    """Test that past events are correctly flagged"""
    response = client.get('/calendar/events', headers=auth_headers)
    assert response.status_code == 200
    events = json.loads(response.data)
    
    for event in events:
        if event['title'] == 'Past Event':
            assert event['extendedProps']['is_past'] is True
            assert 'past-event' in event['className']
        else:
            assert event['extendedProps']['is_past'] is False
            assert 'past-event' not in event['className'] 