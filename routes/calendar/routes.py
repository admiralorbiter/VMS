"""
Calendar Routes Module
=====================

This module provides calendar functionality for the Volunteer Management System (VMS),
handling calendar view display and event data API endpoints for FullCalendar integration.

Key Features:
- Calendar page display with FullCalendar integration
- Event data API for dynamic calendar loading
- Date range filtering for performance
- Event status color coding
- Past event identification and styling
- Extended event properties for tooltips

Main Endpoints:
- /calendar: Display main calendar page
- /calendar/events: API endpoint for event data (FullCalendar integration)

Calendar Integration:
- FullCalendar JavaScript library integration
- ISO date format handling
- Event color coding by status
- Responsive calendar display
- Tooltip information display

Event Properties:
- Basic: id, title, start, end dates
- Visual: color, className for styling
- Extended: location, type, status, description
- Metrics: volunteer_count, volunteers_needed, participant_count
- Metadata: format, is_past flag

Status Color Mapping:
- COMPLETED: Grey (#A0A0A0)
- CONFIRMED: Green (#28a745)
- CANCELLED: Red (#dc3545)
- REQUESTED: Yellow (#ffc107)
- DRAFT: Grey (#6c757d)
- PUBLISHED: Blue (#007bff)

Dependencies:
- FullCalendar JavaScript library
- Event model for data retrieval
- SQLAlchemy for database queries
- Flask Blueprint for routing

Models Used:
- Event: Event data and metadata
- EventStatus: Event status enumeration

Template Dependencies:
- calendar/calendar.html: Main calendar page template

API Response Format:
- JSON array of events compatible with FullCalendar
- Each event includes basic and extended properties
- Color coding and CSS classes for styling
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import and_, literal, or_

from models.event import Event, EventStatus

# Create calendar blueprint
calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/calendar")
def show_calendar():
    """
    Display the main calendar page.

    Returns the calendar template with FullCalendar integration.
    The calendar will load event data via AJAX calls to /calendar/events.

    Returns:
        Rendered calendar template with FullCalendar integration
    """
    return render_template("calendar/calendar.html")


@calendar_bp.route("/calendar/events")
def get_events():
    """
    API endpoint to fetch events for FullCalendar.

    This endpoint is called by FullCalendar to load events for the specified date range.
    It returns events in the format expected by FullCalendar with color coding
    and extended properties for tooltips and styling.

    Query Parameters:
        start (str): Start date in ISO format (provided by FullCalendar)
        end (str): End date in ISO format (provided by FullCalendar)

    Date Range Handling:
        - Converts ISO date strings to datetime objects
        - Handles timezone information (removes 'Z' suffix)
        - Provides fallback defaults for missing parameters
        - Filters events within the specified range

    Event Filtering:
        - Includes events that end within the range
        - Includes events with no end date
        - Excludes events that start after the range end
        - Orders events by start date

    Returns:
        JSON array of events with FullCalendar-compatible structure:
        - id: Event database ID
        - title: Event title
        - start: Start date in ISO format
        - end: End date in ISO format
        - color: Status-based color code
        - className: CSS class for styling
        - extendedProps: Additional event properties
    """
    # Get date range parameters from FullCalendar request
    start = request.args.get("start")
    end = request.args.get("end")

    # Add debug logging for troubleshooting
    print(f"Fetching events between {start} and {end}")

    # Convert string dates to datetime objects with fallback defaults
    # FullCalendar sends dates in ISO format, we remove 'Z' and parse
    start_date = datetime.fromisoformat(start.replace("Z", "")) if start else datetime.now() - timedelta(days=365)
    end_date = datetime.fromisoformat(end.replace("Z", "")) if end else datetime.now() + timedelta(days=365)

    # Query events within the specified date range
    # Include events that either end within the range or have no end date
    events = (
        Event.query.filter(
            or_(
                and_(Event.end_date.isnot(None), Event.end_date >= literal(start_date)),
                Event.end_date.is_(None),
            ),
            Event.start_date <= literal(end_date),
        )
        .order_by(getattr(Event, "start_date"))
        .all()
    )

    # Debug print for troubleshooting
    print(f"Found {len(events)} events")

    # Transform events into FullCalendar-compatible format
    calendar_events = []
    for event in events:
        # Debug print first event for troubleshooting
        if len(calendar_events) == 0:
            print(f"Sample event: {event.title}, {event.start_date}, {event.status}")

        # Determine if event is in the past for styling
        is_past = event.end_date < datetime.now() if event.end_date else event.start_date < datetime.now()

        # Color mapping for different event statuses
        # Each status gets a distinct color for visual differentiation
        color_map = {
            EventStatus.COMPLETED: "#A0A0A0",  # Grey for completed events
            EventStatus.CONFIRMED: "#28a745",  # Green for confirmed events
            EventStatus.CANCELLED: "#dc3545",  # Red for cancelled events
            EventStatus.REQUESTED: "#ffc107",  # Yellow for requested events
            EventStatus.DRAFT: "#6c757d",  # Grey for draft events
            EventStatus.PUBLISHED: "#007bff",  # Blue for published events
        }

        # Create FullCalendar event object with all necessary properties
        calendar_event = {
            "id": event.id,
            "title": event.title,
            "start": event.start_date.isoformat(),
            "end": (event.end_date or event.start_date + timedelta(hours=1)).isoformat(),
            "color": color_map.get(event.status, "#6c757d"),  # Default grey if status not found
            "className": "past-event" if is_past else "",  # CSS class for past events
            "extendedProps": {
                "location": event.location or "N/A",
                "type": event.type.value if event.type else "N/A",
                "status": event.status.value if event.status else "N/A",
                "description": event.description or "No description available",
                "volunteer_count": event.volunteer_count,
                "volunteers_needed": event.volunteers_needed or 0,
                "format": event.format.value if event.format else "N/A",
                "participant_count": event.participant_count,
                "is_past": is_past,
            },
        }
        calendar_events.append(calendar_event)

    return jsonify(calendar_events)
