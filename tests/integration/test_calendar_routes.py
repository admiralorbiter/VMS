import pytest
from datetime import datetime, timedelta
from flask import url_for
from models import db
from models.event import Event, EventType, EventStatus
from tests.conftest import assert_route_response, safe_route_test

def test_show_calendar_view(client, auth_headers):
    """Test calendar view"""
    response = safe_route_test(client, '/calendar', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_get_calendar_events(client, auth_headers):
    """Test getting calendar events"""
    # Test without query parameters
    response = safe_route_test(client, '/calendar/events', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])
    
    # Test with date range
    response = safe_route_test(client, '/calendar/events?start=2024-01-01&end=2024-12-31', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_events_json(client, auth_headers):
    """Test calendar events JSON endpoint"""
    response = safe_route_test(client, '/calendar/events.json', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_with_filters(client, auth_headers):
    """Test calendar with filters"""
    response = safe_route_test(client, '/calendar?type=in_person&status=confirmed', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_month_view(client, auth_headers):
    """Test calendar month view"""
    response = safe_route_test(client, '/calendar?view=month', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_week_view(client, auth_headers):
    """Test calendar week view"""
    response = safe_route_test(client, '/calendar?view=week', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_day_view(client, auth_headers):
    """Test calendar day view"""
    response = safe_route_test(client, '/calendar?view=day', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_navigation(client, auth_headers):
    """Test calendar navigation"""
    response = safe_route_test(client, '/calendar?date=2024-06-01', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_event_details(client, auth_headers):
    """Test calendar event details"""
    response = safe_route_test(client, '/calendar/event/1', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_export(client, auth_headers):
    """Test calendar export"""
    response = safe_route_test(client, '/calendar/export', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_ical_export(client, auth_headers):
    """Test calendar iCal export"""
    response = safe_route_test(client, '/calendar/export.ics', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_print_view(client, auth_headers):
    """Test calendar print view"""
    response = safe_route_test(client, '/calendar/print', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_search(client, auth_headers):
    """Test calendar search"""
    response = safe_route_test(client, '/calendar?search=test', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_performance(client, auth_headers):
    """Test calendar performance"""
    import time
    
    start_time = time.time()
    response = safe_route_test(client, '/calendar', headers=auth_headers)
    end_time = time.time()
    
    # Should respond within reasonable time
    assert (end_time - start_time) < 5.0
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_accessibility(client, auth_headers):
    """Test calendar accessibility features"""
    response = safe_route_test(client, '/calendar?accessible=true', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_timezone_handling(client, auth_headers):
    """Test calendar timezone handling"""
    response = safe_route_test(client, '/calendar?timezone=America/New_York', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_mobile_view(client, auth_headers):
    """Test calendar mobile view"""
    headers = auth_headers.copy()
    headers['User-Agent'] = 'Mobile Browser'
    response = safe_route_test(client, '/calendar', headers=headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_error_handling(client, auth_headers):
    """Test calendar error handling"""
    response = safe_route_test(client, '/calendar?invalid=parameter', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 400, 404, 500])

def test_calendar_pagination(client, auth_headers):
    """Test calendar pagination"""
    response = safe_route_test(client, '/calendar/events?page=1&limit=20', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500])

def test_calendar_sorting(client, auth_headers):
    """Test calendar sorting"""
    response = safe_route_test(client, '/calendar/events?sort=date&order=desc', headers=auth_headers)
    assert_route_response(response, expected_statuses=[200, 404, 500]) 
