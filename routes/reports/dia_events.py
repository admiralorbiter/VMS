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

DIA Event Types:
- DIA: General Data in Action events
- DIA_CLASSROOM_SPEAKER: DIA classroom speaker events

Report Sections:
1. Filled Events: Events with volunteers assigned, showing volunteer details
2. Unfilled Events: Events without volunteers that need to be filled

Dependencies:
- Event model for DIA event data
- Volunteer model for volunteer information
- EventParticipation model for event-volunteer relationships
- Email model for volunteer contact information
"""

from datetime import datetime, timezone

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from models import db
from models.contact import Email
from models.event import Event, EventType
from models.volunteer import EventParticipation, Volunteer


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
        Display the DIA events report.

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

        Returns:
            Rendered DIA events report template
        """
        # Get all upcoming DIA events (events with type containing "DIA")
        now = datetime.now(timezone.utc)
        dia_events = (
            Event.query.filter(
                and_(
                    or_(
                        Event.type == EventType.DIA,
                        Event.type == EventType.DIA_CLASSROOM_SPEAKER,
                    ),
                    Event.start_date > now,  # Only upcoming events
                )
            )
            .order_by(Event.start_date.asc())
            .all()
        )  # Order by start date ascending for upcoming events

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

                        volunteers.append(
                            {
                                "name": f"{volunteer.first_name} {volunteer.last_name}".strip(),
                                "email": primary_email,
                                "organization": volunteer.organization_name or "N/A",
                                "status": participation.status,
                                "participant_type": participation.participant_type
                                or "Volunteer",
                            }
                        )

                filled_events.append({"event": event, "volunteers": volunteers})
            else:
                # Event is unfilled
                unfilled_events.append(event)

        return render_template(
            "reports/events/dia_events.html",
            filled_events=filled_events,
            unfilled_events=unfilled_events,
            total_dia_events=len(dia_events),
            filled_count=len(filled_events),
            unfilled_count=len(unfilled_events),
        )
