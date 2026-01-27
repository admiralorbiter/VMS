"""
District Event Management Routes

Routes for district administrators to create, manage, and view events
within their tenant context.

Requirements:
- FR-SELFSERV-201: Create events with title, date, time, location, description, volunteer needs
- FR-SELFSERV-202: Edit event details up until event completion
- FR-SELFSERV-203: Cancel events with volunteer notification
- FR-SELFSERV-204: Calendar view with month/week/day navigation

Routes:
- GET  /district/events              - List district events
- GET  /district/events/calendar     - Calendar view (FR-SELFSERV-204)
- GET  /district/events/calendar/api - Calendar events API
- GET  /district/events/new          - New event form
- POST /district/events              - Create event
- GET  /district/events/<id>         - View event details
- GET  /district/events/<id>/edit    - Edit event form
- POST /district/events/<id>         - Update event
- POST /district/events/<id>/cancel  - Cancel event
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from models import db
from models.district_participation import DistrictParticipation
from models.district_volunteer import DistrictVolunteer
from models.event import Event, EventFormat, EventStatus, EventType
from models.volunteer import Volunteer
from routes.district import district_bp

# District event types (simplified subset)
DISTRICT_EVENT_TYPES = [
    (EventType.CAREER_FAIR.value, "Career Fair"),
    (EventType.CAREER_SPEAKER.value, "Career Speaker"),
    (EventType.CLASSROOM_SPEAKER.value, "Classroom Speaker"),
    (EventType.VOLUNTEER_ENGAGEMENT.value, "Volunteer Engagement"),
    (EventType.MENTORING.value, "Mentoring"),
    (EventType.WORKPLACE_VISIT.value, "Workplace Visit"),
]


def require_tenant_context(f):
    """Decorator to require tenant context for district routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get("tenant"):
            flash(
                "You must be logged in with a district account to access this page.",
                "error",
            )
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def require_district_admin(f):
    """Decorator to require district admin access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not g.get("tenant"):
            flash("District access required.", "error")
            return redirect(url_for("index"))
        # For now, any authenticated user with tenant context can manage events
        # TODO: Add district admin role check
        return f(*args, **kwargs)

    return decorated_function


@district_bp.route("/events")
@login_required
@require_tenant_context
def list_events():
    """List events for current tenant."""
    # Get filter parameters
    status_filter = request.args.get("status", "all")

    # Base query - scope to tenant
    query = Event.query.filter(Event.tenant_id == g.tenant_id)

    # Apply status filter
    if status_filter != "all":
        try:
            status = EventStatus(status_filter)
            query = query.filter(Event.status == status)
        except ValueError:
            pass

    # Order by date descending
    query = query.order_by(Event.start_date.desc())

    events = query.all()

    return render_template(
        "district/events/list.html",
        events=events,
        status_filter=status_filter,
        EventStatus=EventStatus,
        page_title=f"Events - {g.tenant.name}",
    )


@district_bp.route("/events/new")
@login_required
@require_district_admin
def new_event():
    """Show new event form."""
    return render_template(
        "district/events/form.html",
        event=None,
        event_types=DISTRICT_EVENT_TYPES,
        EventFormat=EventFormat,
        page_title="Create Event",
        form_action=url_for("district.create_event"),
    )


@district_bp.route("/events", methods=["POST"])
@login_required
@require_district_admin
def create_event():
    """Create a new event (FR-SELFSERV-201)."""
    try:
        # Parse form data
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        event_type = request.form.get(
            "event_type", EventType.VOLUNTEER_ENGAGEMENT.value
        )
        event_format = request.form.get("format", EventFormat.IN_PERSON.value)
        volunteers_needed = request.form.get("volunteers_needed", 0, type=int)

        # Parse dates
        start_date_str = request.form.get("start_date")
        start_time_str = request.form.get("start_time", "09:00")
        end_date_str = request.form.get("end_date")
        end_time_str = request.form.get("end_time")

        # Validate required fields
        errors = []
        if not title:
            errors.append("Title is required")
        if not start_date_str:
            errors.append("Start date is required")
        if not location:
            errors.append("Location is required")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("district.new_event"))

        # Parse start datetime
        start_datetime = datetime.strptime(
            f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)

        # Parse end datetime if provided
        end_datetime = None
        if end_date_str and end_time_str:
            end_datetime = datetime.strptime(
                f"{end_date_str} {end_time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)

        # Create event
        event = Event(
            title=title,
            description=description,
            location=location,
            type=EventType(event_type),
            format=EventFormat(event_format),
            start_date=start_datetime,
            end_date=end_datetime,
            volunteers_needed=volunteers_needed,
            status=EventStatus.DRAFT,
            tenant_id=g.tenant_id,
        )

        db.session.add(event)
        db.session.commit()

        current_app.logger.info(
            f"Event created: {event.id} - '{event.title}' by user {current_user.id} "
            f"for tenant {g.tenant.slug}"
        )

        flash(f"Event '{title}' created successfully!", "success")
        return redirect(url_for("district.view_event", event_id=event.id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating event: {e}")
        flash("An error occurred while creating the event.", "error")
        return redirect(url_for("district.new_event"))


@district_bp.route("/events/<int:event_id>")
@login_required
@require_tenant_context
def view_event(event_id):
    """View event details with volunteer roster."""
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    # Get roster (district participations) for this event
    roster = (
        DistrictParticipation.query.filter_by(event_id=event_id, tenant_id=g.tenant_id)
        .join(Volunteer, Volunteer.id == DistrictParticipation.volunteer_id)
        .order_by(DistrictParticipation.invited_at.desc())
        .all()
    )

    return render_template(
        "district/events/detail.html",
        event=event,
        roster=roster,
        EventStatus=EventStatus,
        page_title=event.title,
    )


@district_bp.route("/events/<int:event_id>/edit")
@login_required
@require_district_admin
def edit_event(event_id):
    """Show edit event form (FR-SELFSERV-202)."""
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    # Cannot edit completed or cancelled events
    if event.status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
        flash("Cannot edit completed or cancelled events.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    return render_template(
        "district/events/form.html",
        event=event,
        event_types=DISTRICT_EVENT_TYPES,
        EventFormat=EventFormat,
        page_title=f"Edit: {event.title}",
        form_action=url_for("district.update_event", event_id=event_id),
    )


@district_bp.route("/events/<int:event_id>", methods=["POST"])
@login_required
@require_district_admin
def update_event(event_id):
    """Update an existing event (FR-SELFSERV-202)."""
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    # Cannot edit completed or cancelled events
    if event.status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
        flash("Cannot edit completed or cancelled events.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        # Update fields
        event.title = request.form.get("title", "").strip()
        event.description = request.form.get("description", "").strip()
        event.location = request.form.get("location", "").strip()
        event.type = EventType(request.form.get("event_type", event.type.value))
        event.format = EventFormat(request.form.get("format", event.format.value))
        event.volunteers_needed = request.form.get("volunteers_needed", 0, type=int)

        # Parse dates
        start_date_str = request.form.get("start_date")
        start_time_str = request.form.get("start_time", "09:00")
        end_date_str = request.form.get("end_date")
        end_time_str = request.form.get("end_time")

        if start_date_str:
            event.start_date = datetime.strptime(
                f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)

        if end_date_str and end_time_str:
            event.end_date = datetime.strptime(
                f"{end_date_str} {end_time_str}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
        else:
            event.end_date = None

        # Update status if provided
        new_status = request.form.get("status")
        if new_status:
            event.status = EventStatus(new_status)

        db.session.commit()

        current_app.logger.info(f"Event updated: {event.id} by user {current_user.id}")

        flash("Event updated successfully!", "success")
        return redirect(url_for("district.view_event", event_id=event_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating event: {e}")
        flash("An error occurred while updating the event.", "error")
        return redirect(url_for("district.edit_event", event_id=event_id))


@district_bp.route("/events/<int:event_id>/cancel", methods=["POST"])
@login_required
@require_district_admin
def cancel_event(event_id):
    """Cancel an event (FR-SELFSERV-203)."""
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    if event.status == EventStatus.CANCELLED:
        flash("Event is already cancelled.", "info")
        return redirect(url_for("district.view_event", event_id=event_id))

    if event.status == EventStatus.COMPLETED:
        flash("Cannot cancel a completed event.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        event.status = EventStatus.CANCELLED
        db.session.commit()

        current_app.logger.info(
            f"Event cancelled: {event.id} by user {current_user.id}"
        )

        # TODO: Send notification emails to signed-up volunteers (FR-SELFSERV-203)

        flash(f"Event '{event.title}' has been cancelled.", "success")
        return redirect(url_for("district.view_event", event_id=event_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling event: {e}")
        flash("An error occurred while cancelling the event.", "error")
        return redirect(url_for("district.view_event", event_id=event_id))


@district_bp.route("/events/<int:event_id>/publish", methods=["POST"])
@login_required
@require_district_admin
def publish_event(event_id):
    """Publish a draft event."""
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    if event.status != EventStatus.DRAFT:
        flash("Only draft events can be published.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        event.status = EventStatus.PUBLISHED
        db.session.commit()

        flash(f"Event '{event.title}' has been published!", "success")
        return redirect(url_for("district.view_event", event_id=event_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error publishing event: {e}")
        flash("An error occurred while publishing the event.", "error")
        return redirect(url_for("district.view_event", event_id=event_id))


# =============================================================================
# Calendar Routes (FR-SELFSERV-204)
# =============================================================================


@district_bp.route("/events/calendar")
@login_required
@require_tenant_context
def calendar_view():
    """Display calendar view of district events (FR-SELFSERV-204)."""
    return render_template(
        "district/events/calendar.html",
        page_title=f"Calendar - {g.tenant.name}",
    )


@district_bp.route("/events/calendar/api")
@login_required
@require_tenant_context
def calendar_api():
    """
    API endpoint for FullCalendar to fetch tenant-scoped events.

    Query Parameters:
        start: Start date in ISO format (from FullCalendar)
        end: End date in ISO format (from FullCalendar)

    Returns:
        JSON array of events compatible with FullCalendar
    """
    # Get date range from FullCalendar request
    start = request.args.get("start")
    end = request.args.get("end")

    # Parse dates with fallback defaults
    start_date = (
        datetime.fromisoformat(start.replace("Z", ""))
        if start
        else datetime.now() - timedelta(days=365)
    )
    end_date = (
        datetime.fromisoformat(end.replace("Z", ""))
        if end
        else datetime.now() + timedelta(days=365)
    )

    # Query events scoped to tenant and within date range
    events = (
        Event.query.filter(
            Event.tenant_id == g.tenant_id,
            Event.start_date <= end_date,
            Event.start_date >= start_date - timedelta(days=31),  # Include overlapping
        )
        .order_by(Event.start_date)
        .all()
    )

    # Status color mapping
    color_map = {
        EventStatus.COMPLETED: "#A0A0A0",  # Grey
        EventStatus.CONFIRMED: "#28a745",  # Green
        EventStatus.CANCELLED: "#dc3545",  # Red
        EventStatus.REQUESTED: "#ffc107",  # Yellow
        EventStatus.DRAFT: "#6c757d",  # Grey
        EventStatus.PUBLISHED: "#007bff",  # Blue
    }

    # Transform to FullCalendar format
    calendar_events = []
    for event in events:
        is_past = (
            event.end_date < datetime.now(timezone.utc)
            if event.end_date
            else event.start_date < datetime.now(timezone.utc)
        )

        calendar_events.append(
            {
                "id": event.id,
                "title": event.title,
                "start": event.start_date.isoformat() if event.start_date else None,
                "end": (
                    (
                        event.end_date or event.start_date + timedelta(hours=1)
                    ).isoformat()
                    if event.start_date
                    else None
                ),
                "color": color_map.get(event.status, "#6c757d"),
                "className": "past-event" if is_past else "",
                "url": url_for("district.view_event", event_id=event.id),
                "extendedProps": {
                    "location": event.location or "N/A",
                    "type": event.type.value if event.type else "N/A",
                    "status": event.status.value if event.status else "N/A",
                    "description": event.description or "No description",
                    "volunteer_count": event.volunteer_count,
                    "volunteers_needed": event.volunteers_needed or 0,
                    "format": event.format.value if event.format else "N/A",
                    "is_past": is_past,
                },
            }
        )

    return jsonify(calendar_events)


# =============================================================================
# Event Roster Management Routes (FR-SELFSERV-304)
# =============================================================================


@district_bp.route("/events/<int:event_id>/roster/add", methods=["POST"])
@login_required
@require_district_admin
def add_to_roster(event_id):
    """
    Assign a volunteer to an event roster.

    FR-SELFSERV-304: Assign volunteers with participation type and status tracking
    """
    # Verify event belongs to tenant
    event = Event.query.filter(
        Event.id == event_id, Event.tenant_id == g.tenant_id
    ).first_or_404()

    # Check event is not completed or cancelled
    if event.status in [EventStatus.COMPLETED, EventStatus.CANCELLED]:
        flash("Cannot add volunteers to completed or cancelled events.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    volunteer_id = request.form.get("volunteer_id", type=int)
    if not volunteer_id:
        flash("Please select a volunteer.", "error")
        return redirect(url_for("district.view_event", event_id=event_id))

    # Verify volunteer is in this tenant's pool
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id, tenant_id=g.tenant_id
    ).first()

    if not district_vol:
        flash("Volunteer not found in your district.", "error")
        return redirect(url_for("district.view_event", event_id=event_id))

    # Check if already assigned
    existing = DistrictParticipation.query.filter_by(
        volunteer_id=volunteer_id, event_id=event_id, tenant_id=g.tenant_id
    ).first()

    if existing:
        flash("Volunteer is already assigned to this event.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        # Create participation record
        participation = DistrictParticipation(
            volunteer_id=volunteer_id,
            event_id=event_id,
            tenant_id=g.tenant_id,
            status="invited",
            participation_type=request.form.get("participation_type", "volunteer"),
            invited_by=current_user.id,
            invited_at=datetime.now(timezone.utc),
            notes=request.form.get("notes", "").strip() or None,
        )
        db.session.add(participation)
        db.session.commit()

        volunteer = Volunteer.query.get(volunteer_id)
        flash(
            f"Added {volunteer.first_name} {volunteer.last_name} to the event roster.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding to roster: {e}")
        flash("An error occurred while adding the volunteer.", "error")

    return redirect(url_for("district.view_event", event_id=event_id))


@district_bp.route(
    "/events/<int:event_id>/roster/<int:participation_id>/status", methods=["POST"]
)
@login_required
@require_district_admin
def update_participation_status(event_id, participation_id):
    """
    Update a volunteer's participation status.

    FR-SELFSERV-304: Track confirmation status (Invited, Confirmed, Declined, Attended)
    """
    participation = DistrictParticipation.query.filter_by(
        id=participation_id, event_id=event_id, tenant_id=g.tenant_id
    ).first_or_404()

    new_status = request.form.get("status")
    valid_statuses = ["invited", "confirmed", "declined", "attended", "no_show"]

    if new_status not in valid_statuses:
        flash("Invalid status.", "error")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        old_status = participation.status
        participation.status = new_status

        # Update timestamp based on new status
        now = datetime.now(timezone.utc)
        if new_status == "confirmed" and not participation.confirmed_at:
            participation.confirmed_at = now
        elif new_status == "attended" and not participation.attended_at:
            participation.attended_at = now

        db.session.commit()

        volunteer = Volunteer.query.get(participation.volunteer_id)
        flash(
            f"Updated {volunteer.first_name} {volunteer.last_name}'s status to {new_status}.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating participation status: {e}")
        flash("An error occurred while updating the status.", "error")

    return redirect(url_for("district.view_event", event_id=event_id))


@district_bp.route(
    "/events/<int:event_id>/roster/<int:participation_id>/remove", methods=["POST"]
)
@login_required
@require_district_admin
def remove_from_roster(event_id, participation_id):
    """Remove a volunteer from the event roster."""
    participation = DistrictParticipation.query.filter_by(
        id=participation_id, event_id=event_id, tenant_id=g.tenant_id
    ).first_or_404()

    # Don't allow removal of attended volunteers
    if participation.status == "attended":
        flash("Cannot remove volunteers who have already attended.", "warning")
        return redirect(url_for("district.view_event", event_id=event_id))

    try:
        volunteer = Volunteer.query.get(participation.volunteer_id)
        name = f"{volunteer.first_name} {volunteer.last_name}"

        db.session.delete(participation)
        db.session.commit()

        flash(f"Removed {name} from the event roster.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing from roster: {e}")
        flash("An error occurred.", "error")

    return redirect(url_for("district.view_event", event_id=event_id))


@district_bp.route("/events/<int:event_id>/roster/search")
@login_required
@require_tenant_context
def search_volunteers_for_event(event_id):
    """
    Search volunteers in tenant pool for assignment to event.

    Returns JSON for AJAX autocomplete.
    """
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    # Get volunteers in this tenant who are NOT already on this event's roster
    existing_volunteer_ids = (
        db.session.query(DistrictParticipation.volunteer_id)
        .filter_by(event_id=event_id, tenant_id=g.tenant_id)
        .subquery()
    )

    results = (
        Volunteer.query.join(
            DistrictVolunteer, DistrictVolunteer.volunteer_id == Volunteer.id
        )
        .filter(
            DistrictVolunteer.tenant_id == g.tenant_id,
            DistrictVolunteer.status == "active",
            Volunteer.id.notin_(existing_volunteer_ids),
            db.or_(
                Volunteer.first_name.ilike(f"%{query}%"),
                Volunteer.last_name.ilike(f"%{query}%"),
                Volunteer.organization_name.ilike(f"%{query}%"),
            ),
        )
        .limit(10)
        .all()
    )

    return jsonify(
        [
            {
                "id": v.id,
                "name": f"{v.first_name} {v.last_name}",
                "email": v.primary_email,
                "organization": v.organization_name,
            }
            for v in results
        ]
    )
