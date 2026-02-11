"""
DIA Events Report Module
========================

This module provides reporting functionality for Data in Action (DIA) events.
It shows DIA events that have been filled with volunteer information and
those that remain unfilled, along with volunteer contact details.

Key Features:
- Lists all DIA events (events with type containing "DIA")
- Shows filled events with volunteer details and emails
- Shows unfilled events that need volunteers
- Provides volunteer contact information for filled events
- Clean, organized display of event status
- Performance-optimized with caching mechanism

DIA Event Types:
- DIA: General Data in Action events
- DIA_CLASSROOM_SPEAKER: DIA classroom speaker events

Report Sections:
1. Filled Events: Events with volunteers assigned, showing volunteer details
2. Unfilled Events: Events without volunteers that need to be filled

Performance Optimizations:
- Report data caching to reduce database queries
- Cache invalidation after 24 hours
- Optional cache refresh via ?refresh=1 parameter
- Serialization/deserialization for efficient storage

Dependencies:
- Event model for DIA event data
- Volunteer model for volunteer information
- EventParticipation model for event-volunteer relationships
- Email model for volunteer contact information
- DIAEventsReportCache model for caching
"""

from datetime import datetime, timedelta, timezone

from flask import render_template, request
from flask_login import login_required
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from models import db
from models.contact import Email
from models.event import Event, EventType
from models.reports import DIAEventsReportCache
from models.volunteer import EventParticipation


def _serialize_for_cache(filled_events: list[dict], unfilled_events: list) -> dict:
    """
    Serialize DIA events data for cache storage.

    Converts event objects and datetime fields to JSON-serializable format.

    Args:
        filled_events: List of dicts containing event and volunteer data
        unfilled_events: List of Event objects without volunteers

    Returns:
        dict: Serialized data ready for JSON storage
    """

    def ser_dt(value):
        """Serialize datetime to ISO format string."""
        if not value:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        try:
            return value.isoformat()
        except Exception:
            return str(value)

    # Serialize filled events
    filled_serialized = []
    for item in filled_events:
        event = item["event"]
        event_data = {
            "id": event.id,
            "title": event.title,
            "type": event.type.value if event.type else None,
            "start_date": ser_dt(event.start_date),
            "end_date": ser_dt(event.end_date),
            "location": event.location,
            "school_id": event.school,
            "school_name": event.school_obj.name if event.school_obj else None,
            "status": event.status.value if event.status else None,
            "description": event.description,
            "salesforce_id": event.salesforce_id,
            "salesforce_url": event.salesforce_url,
        }

        volunteers_data = []
        for volunteer in item["volunteers"]:
            volunteers_data.append(
                {
                    "name": volunteer["name"],
                    "email": volunteer["email"],
                    "organization": volunteer["organization"],
                    "status": volunteer["status"],
                    "participant_type": volunteer["participant_type"],
                }
            )

        filled_serialized.append({"event": event_data, "volunteers": volunteers_data})

    # Serialize unfilled events
    unfilled_serialized = []
    for event in unfilled_events:
        unfilled_serialized.append(
            {
                "id": event.id,
                "title": event.title,
                "type": event.type.value if event.type else None,
                "start_date": ser_dt(event.start_date),
                "end_date": ser_dt(event.end_date),
                "location": event.location,
                "school_id": event.school,
                "school_name": event.school_obj.name if event.school_obj else None,
                "status": event.status.value if event.status else None,
                "description": event.description,
                "salesforce_id": event.salesforce_id,
                "salesforce_url": event.salesforce_url,
                "volunteers_needed": (
                    event.volunteers_needed
                    if hasattr(event, "volunteers_needed")
                    else None
                ),
            }
        )

    return {"filled_events": filled_serialized, "unfilled_events": unfilled_serialized}


def _deserialize_from_cache(payload: dict) -> tuple[list[dict], list[dict]]:
    """
    Deserialize DIA events data from cache.

    Converts ISO format strings back to datetime objects and reconstructs
    the data structure expected by the template.

    Args:
        payload: Serialized cache data

    Returns:
        tuple: (filled_events, unfilled_events) as expected by the template
    """

    def parse_dt(value):
        """Parse ISO format string to datetime."""
        if not value:
            return None
        try:
            # If pure date like 'YYYY-MM-DD', coerce to midnight UTC
            if isinstance(value, str) and "T" not in value:
                return datetime.fromisoformat(value + "T00:00:00+00:00")
            return datetime.fromisoformat(value)
        except Exception:
            return None

    filled_out = []
    for item in payload.get("filled_events") or []:
        event_data = item["event"]
        # Convert serialized event dict back to dict format expected by template
        event_dict = {
            "id": event_data["id"],
            "title": event_data["title"],
            "type": event_data["type"],
            "start_date": parse_dt(event_data["start_date"]),
            "end_date": parse_dt(event_data["end_date"]),
            "location": event_data["location"],
            "school_id": event_data.get("school_id"),
            "school_name": event_data.get("school_name"),
            "status": event_data["status"],
            "description": event_data["description"],
            "salesforce_id": event_data.get("salesforce_id"),
            "salesforce_url": event_data.get("salesforce_url"),
        }

        volunteers_data = []
        for volunteer in item["volunteers"]:
            volunteers_data.append(
                {
                    "name": volunteer["name"],
                    "email": volunteer["email"],
                    "organization": volunteer["organization"],
                    "status": volunteer["status"],
                    "participant_type": volunteer["participant_type"],
                }
            )

        filled_out.append({"event": event_dict, "volunteers": volunteers_data})

    unfilled_out = []
    for event_data in payload.get("unfilled_events") or []:
        unfilled_out.append(
            {
                "id": event_data["id"],
                "title": event_data["title"],
                "type": event_data["type"],
                "start_date": parse_dt(event_data["start_date"]),
                "end_date": parse_dt(event_data["end_date"]),
                "location": event_data["location"],
                "school_id": event_data.get("school_id"),
                "school_name": event_data.get("school_name"),
                "status": event_data["status"],
                "description": event_data["description"],
                "salesforce_id": event_data.get("salesforce_id"),
                "salesforce_url": event_data.get("salesforce_url"),
                "volunteers_needed": event_data.get("volunteers_needed"),
            }
        )

    return filled_out, unfilled_out


def _is_cache_valid(cache_record, max_age_hours: int = 24) -> bool:
    """
    Check if a cache record is still valid based on age.

    Args:
        cache_record: Cache model instance
        max_age_hours: Maximum age in hours before cache expires (default: 24)

    Returns:
        bool: True if cache is valid, False otherwise
    """
    if not cache_record or not getattr(cache_record, "last_updated", None):
        return False

    last_updated = cache_record.last_updated
    # Normalize to timezone-aware UTC
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return (now - last_updated) < timedelta(hours=max_age_hours)


def _query_dia_events():
    """
    Query all upcoming DIA events from the database.

    Returns:
        tuple: (filled_events, unfilled_events) where:
            - filled_events: List of dicts with event and volunteer data
            - unfilled_events: List of Event objects without volunteers
    """
    # Get all upcoming DIA events that actually need volunteers
    now = datetime.now(timezone.utc)
    dia_events = (
        Event.query.filter(
            and_(
                or_(
                    Event.type == EventType.DIA,
                    Event.type == EventType.DIA_CLASSROOM_SPEAKER,
                ),
                Event.start_date > now,  # Only upcoming events
                # Filter to only show events that need volunteers
                # This excludes events like "Hills" and "STEAM Studio" that don't need volunteers
                or_(
                    Event.volunteers_needed > 0,  # Events with explicit volunteer needs
                    # Events with "Voices Behind the Data" in title typically need volunteers
                    Event.title.like("%Voices Behind the Data%"),
                    # Events with "Data Ethics Speaker" in title typically need volunteers
                    Event.title.like("%Data Ethics Speaker%"),
                    # Events with "Project Mentors" in title typically need volunteers
                    Event.title.like("%Project Mentors%"),
                ),
            )
        )
        .order_by(Event.start_date.asc())
        .all()
    )

    filled_events = []
    unfilled_events = []

    for event in dia_events:
        # Get volunteers for this event through EventParticipation
        event_participations = (
            EventParticipation.query.filter_by(event_id=event.id)
            .options(joinedload(EventParticipation.volunteer))
            .all()
        )

        if event_participations:
            # Event is filled - collect volunteer details
            volunteers = []
            for participation in event_participations:
                volunteer = participation.volunteer
                if volunteer:
                    # Get primary email by querying the Email model directly
                    primary_email = None
                    primary_email_obj = Email.query.filter_by(
                        contact_id=volunteer.id, primary=True
                    ).first()

                    if primary_email_obj:
                        primary_email = primary_email_obj.email
                    else:
                        # If no primary email, get any email
                        any_email_obj = Email.query.filter_by(
                            contact_id=volunteer.id
                        ).first()
                        if any_email_obj:
                            primary_email = any_email_obj.email

                    # Get organization name from VolunteerOrganization relationship
                    organization_name = "N/A"

                    # First try to get organization from VolunteerOrganization relationship
                    from models.organization import VolunteerOrganization

                    vol_org = VolunteerOrganization.query.filter_by(
                        volunteer_id=volunteer.id, is_primary=True
                    ).first()

                    # If no primary organization, get any organization
                    if not vol_org:
                        vol_org = VolunteerOrganization.query.filter_by(
                            volunteer_id=volunteer.id
                        ).first()

                    if vol_org and vol_org.organization:
                        organization_name = vol_org.organization.name
                    elif (
                        volunteer.organization_name
                        and not volunteer.organization_name.startswith("00")
                    ):
                        # Only use organization_name if it doesn't look like a Salesforce ID
                        organization_name = volunteer.organization_name

                    volunteers.append(
                        {
                            "name": f"{volunteer.first_name} {volunteer.last_name}".strip(),
                            "email": primary_email,
                            "organization": organization_name,
                            "status": participation.status,
                            "participant_type": participation.participant_type
                            or "Volunteer",
                        }
                    )

            filled_events.append({"event": event, "volunteers": volunteers})
        else:
            # Event is unfilled
            unfilled_events.append(event)

    return filled_events, unfilled_events


def load_routes(bp):
    """
    Load DIA events report routes into the provided blueprint.

    Args:
        bp: Flask Blueprint to register routes with
    """

    @bp.route("/reports/dia-events")
    @login_required
    def dia_events():
        """
        Display the DIA events report with caching for improved performance.

        Shows all DIA events (events with type containing "DIA") organized into:
        - Filled events: Events with volunteers assigned
        - Unfilled events: Events without volunteers

        For filled events, shows:
        - Event details (title, date, location, school)
        - Volunteer information (name, email, organization)
        - Event status and participation details

        For unfilled events, shows:
        - Event details (title, date, location, school)
        - Volunteer requirements
        - Event status

        Performance Features:
        - Uses cached data when available (24-hour validity)
        - Supports ?refresh=1 to force cache refresh
        - Serializes data for efficient storage

        Returns:
            Rendered DIA events report template
        """
        # Check for cache refresh request
        refresh = request.args.get("refresh", "0") == "1"

        # Try to get cached data first
        cache = DIAEventsReportCache.query.first()

        if cache and not refresh and _is_cache_valid(cache):
            # Use cached data
            payload = cache.report_data or {}
            filled_events, unfilled_events = _deserialize_from_cache(payload)
        else:
            # Query fresh data from database
            filled_events, unfilled_events = _query_dia_events()

            # Serialize and save to cache
            cache_payload = _serialize_for_cache(filled_events, unfilled_events)

            try:
                if not cache:
                    # Create new cache entry
                    cache = DIAEventsReportCache(report_data=cache_payload)
                    db.session.add(cache)
                else:
                    # Update existing cache entry
                    cache.report_data = cache_payload
                    cache.last_updated = datetime.now(timezone.utc)

                db.session.commit()
            except Exception:
                # If cache save fails, rollback and continue with fresh data
                db.session.rollback()

        # Calculate totals
        total_dia_events = len(filled_events) + len(unfilled_events)
        filled_count = len(filled_events)
        unfilled_count = len(unfilled_events)

        # Normalize cache timestamp to timezone-aware UTC for template
        cache_timestamp = None
        if cache and cache.last_updated:
            cache_timestamp = cache.last_updated
            # Ensure timezone-aware (SQLite may return naive datetimes)
            if cache_timestamp.tzinfo is None:
                cache_timestamp = cache_timestamp.replace(tzinfo=timezone.utc)

        return render_template(
            "reports/events/dia_events.html",
            filled_events=filled_events,
            unfilled_events=unfilled_events,
            total_dia_events=total_dia_events,
            filled_count=filled_count,
            unfilled_count=unfilled_count,
            cache_last_updated=cache_timestamp,
            now=datetime.now(timezone.utc),
        )
