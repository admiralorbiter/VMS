"""
Calendar Utility Functions

Provides ICS (iCalendar) file generation for event invites.
Used by public signup forms to attach calendar invites to confirmation emails.

FR-SELFSERV-405: Public signup shall attach calendar invites to confirmation emails.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional


def generate_event_ics(
    title: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    organizer_email: Optional[str] = None,
    organizer_name: Optional[str] = None,
    event_url: Optional[str] = None,
) -> str:
    """
    Generate an ICS (iCalendar) format calendar invite for an event.

    Args:
        title: Event title
        start_date: Event start datetime (should be timezone-aware)
        end_date: Event end datetime (defaults to start + 1 hour)
        location: Event location/address
        description: Event description
        organizer_email: Organizer's email address
        organizer_name: Organizer's display name
        event_url: URL to event details page

    Returns:
        ICS file content as string
    """
    # Generate unique ID for this calendar event
    uid = f"{uuid.uuid4()}@polaris.prepkc.org"

    # Default end time to 1 hour after start
    if end_date is None:
        end_date = start_date + timedelta(hours=1)

    # Format dates for ICS (UTC format: YYYYMMDDTHHMMSSZ)
    def format_datetime(dt: datetime) -> str:
        # Convert to UTC if timezone-aware, otherwise assume UTC
        if dt.tzinfo is not None:
            from datetime import timezone

            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    dtstart = format_datetime(start_date)
    dtend = format_datetime(end_date)
    dtstamp = format_datetime(datetime.utcnow())

    # Escape special characters in text fields
    def escape_text(text: str) -> str:
        if not text:
            return ""
        return (
            text.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )

    # Build ICS content
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PrepKC//Polaris VMS//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{escape_text(title)}",
    ]

    if location:
        lines.append(f"LOCATION:{escape_text(location)}")

    if description:
        # ICS requires line folding for long descriptions
        desc_escaped = escape_text(description)
        lines.append(f"DESCRIPTION:{desc_escaped}")

    if organizer_email:
        org_line = f"ORGANIZER"
        if organizer_name:
            org_line += f";CN={escape_text(organizer_name)}"
        org_line += f":mailto:{organizer_email}"
        lines.append(org_line)

    if event_url:
        lines.append(f"URL:{event_url}")

    # Set status and transparency
    lines.extend(
        [
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )

    return "\r\n".join(lines)


def generate_event_ics_from_model(event, signup_url: Optional[str] = None) -> str:
    """
    Generate ICS content from an Event model instance.

    Args:
        event: Event model instance
        signup_url: Optional URL to include in the event

    Returns:
        ICS file content as string
    """
    return generate_event_ics(
        title=event.title,
        start_date=event.start_date,
        end_date=event.end_date,
        location=event.location,
        description=event.description,
        organizer_email="events@prepkc.org",
        organizer_name="PrepKC",
        event_url=signup_url,
    )
