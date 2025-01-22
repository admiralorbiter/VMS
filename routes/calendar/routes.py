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
    # Get date range parameters from the request (FullCalendar sends these automatically)
    start = request.args.get('start')
    end = request.args.get('end')
    
    # Convert string dates to datetime objects
    start_date = datetime.fromisoformat(start.replace('Z', '')) if start else datetime.now() - timedelta(days=365)
    end_date = datetime.fromisoformat(end.replace('Z', '')) if end else datetime.now() + timedelta(days=365)
    
    # Query events within the date range
    events = Event.query.filter(
        and_(
            or_(Event.end_date >= start_date, Event.end_date.is_(None)),
            Event.start_date <= end_date
        )
    ).order_by(Event.start_date).all()
    
    # Format events for FullCalendar
    calendar_events = []
    for event in events:
        # Define color based on event status and whether it's past
        is_past = event.end_date < datetime.now() if event.end_date else event.start_date < datetime.now()
        
        color_map = {
            EventStatus.COMPLETED: '#A0A0A0',    # Grey for completed
            EventStatus.CONFIRMED: '#28a745',    # Green for confirmed
            EventStatus.CANCELLED: '#dc3545',    # Red for cancelled
            EventStatus.REQUESTED: '#ffc107',    # Yellow for requested
            EventStatus.DRAFT: '#6c757d',        # Grey for draft
            EventStatus.PUBLISHED: '#007bff'     # Blue for published
        }
        
        # Calculate event end time (use start_date + 1 hour if no end_date)
        end_time = event.end_date if event.end_date else event.start_date + timedelta(hours=1)
        
        # Format the event for the calendar
        calendar_event = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': end_time.isoformat(),
            'color': color_map.get(event.status, '#6c757d'),
            'className': 'past-event' if is_past else '',
            'extendedProps': {
                'location': event.location or 'N/A',
                'type': event.type.value if event.type else 'N/A',
                'status': event.status.value if event.status else 'N/A',
                'description': event.description or 'No description available',
                'volunteer_count': event.volunteer_count,
                'volunteer_needed': event.volunteer_needed,
                'format': event.format.value if event.format else 'N/A',
                'participant_count': event.participant_count,
                'is_past': is_past
            }
        }
        
        calendar_events.append(calendar_event)
    
    return jsonify(calendar_events) 