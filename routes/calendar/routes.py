from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
from models.event import Event, EventStatus
from sqlalchemy import and_, or_

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/calendar')
def show_calendar():
    return render_template('calendar/calendar.html')

@calendar_bp.route('/calendar/events')
def get_events():
    # Get date range parameters from the request
    start = request.args.get('start')
    end = request.args.get('end')
    
    # Add debug logging
    print(f"Fetching events between {start} and {end}")
    
    # Convert string dates to datetime objects
    start_date = datetime.fromisoformat(start.replace('Z', '')) if start else datetime.now() - timedelta(days=365)
    end_date = datetime.fromisoformat(end.replace('Z', '')) if end else datetime.now() + timedelta(days=365)
    
    # Query events
    events = Event.query.filter(
        and_(
            or_(Event.end_date >= start_date, Event.end_date.is_(None)),
            Event.start_date <= end_date
        )
    ).order_by(Event.start_date).all()
    
    # Debug print
    print(f"Found {len(events)} events")
    
    calendar_events = []
    for event in events:
        # Debug print first event
        if len(calendar_events) == 0:
            print(f"Sample event: {event.title}, {event.start_date}, {event.status}")
            
        is_past = event.end_date < datetime.now() if event.end_date else event.start_date < datetime.now()
        
        color_map = {
            EventStatus.COMPLETED: '#A0A0A0',    # Grey for completed
            EventStatus.CONFIRMED: '#28a745',    # Green for confirmed
            EventStatus.CANCELLED: '#dc3545',    # Red for cancelled
            EventStatus.REQUESTED: '#ffc107',    # Yellow for requested
            EventStatus.DRAFT: '#6c757d',        # Grey for draft
            EventStatus.PUBLISHED: '#007bff'     # Blue for published
        }
        
        calendar_event = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': (event.end_date or event.start_date + timedelta(hours=1)).isoformat(),
            'color': color_map.get(event.status, '#6c757d'),
            'className': 'past-event' if is_past else '',
            'extendedProps': {
                'location': event.location or 'N/A',
                'type': event.type.value if event.type else 'N/A',
                'status': event.status.value if event.status else 'N/A',
                'description': event.description or 'No description available',
                'volunteer_count': event.volunteer_count,
                'volunteers_needed': event.volunteers_needed or 0,
                'format': event.format.value if event.format else 'N/A',
                'participant_count': event.participant_count,
                'is_past': is_past
            }
        }
        calendar_events.append(calendar_event)
    
    return jsonify(calendar_events)