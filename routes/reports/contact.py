from datetime import datetime, timezone

from flask import Blueprint, render_template, request
from flask_login import login_required

from models.event import Event, EventStatus

# Create blueprint
contact_bp = Blueprint("contact", __name__)


def load_routes(bp):
    @bp.route("/reports/contact")
    @login_required
    def contact_report():
        # Get search parameters
        search = request.args.get("search", "").strip()
        sort = request.args.get("sort", "start_date")
        order = request.args.get("order", "asc")

        # Base query for future events that are confirmed
        query = Event.query.filter(
            Event.start_date >= datetime.now(timezone.utc),  # Only future events
            Event.status == EventStatus.CONFIRMED,
        )

        # Apply search if provided
        if search:
            query = query.filter(Event.title.ilike(f"%{search}%"))

        # Apply sorting
        if sort == "title":
            query = query.order_by(
                Event.title.asc() if order == "asc" else Event.title.desc()
            )
        elif sort == "location":
            query = query.order_by(
                Event.location.asc() if order == "asc" else Event.location.desc()
            )
        else:  # default to date
            query = query.order_by(
                Event.start_date.asc() if order == "asc" else Event.start_date.desc()
            )

        upcoming_events = query.all()

        # Get participant counts for each event
        event_stats = {}
        for event in upcoming_events:
            participations = event.volunteer_participations
            event_stats[event.id] = {
                "volunteer_count": len(participations),
            }

        return render_template(
            "reports/events/contact_report.html",
            events=upcoming_events,
            event_stats=event_stats,
            search=search,
            sort=sort,
            order=order,
        )

    @bp.route("/reports/contact/<int:event_id>")
    @login_required
    def contact_report_detail(event_id):
        from models import eagerload_event_bundle

        event = eagerload_event_bundle(Event.query).get_or_404(event_id)

        # Get sort parameters
        sort = request.args.get("sort", "name")
        order = request.args.get("order", "asc")

        # Get all participants for this event
        participations = event.volunteer_participations

        # Group participants by status
        participants_by_status = {"Scheduled": [], "Unscheduled": []}

        for participation in participations:
            if participation.status == "Scheduled":
                participants_by_status["Scheduled"].append(participation)
            else:
                participants_by_status["Unscheduled"].append(participation)

        # Sort participants in each group
        for status in participants_by_status:
            participants = participants_by_status[status]
            if sort == "name":
                participants.sort(
                    key=lambda p: f"{p.volunteer.first_name} {p.volunteer.last_name}",
                    reverse=(order == "desc"),
                )
            elif sort == "title":
                participants.sort(
                    key=lambda p: p.title or p.volunteer.title or "",
                    reverse=(order == "desc"),
                )
            elif sort == "email":
                participants.sort(
                    key=lambda p: p.volunteer.primary_email or "",
                    reverse=(order == "desc"),
                )
            elif sort == "organization":
                participants.sort(
                    key=lambda p: (
                        p.volunteer.organizations[0].name
                        if p.volunteer.organizations
                        else ""
                    ),
                    reverse=(order == "desc"),
                )

        return render_template(
            "reports/events/contact_report_detail.html",
            event=event,
            participants_by_status=participants_by_status,
            sort=sort,
            order=order,
        )
