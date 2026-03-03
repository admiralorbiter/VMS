"""
Virtual Routes Module
====================

Core routes for virtual session management: listing, viewing, and purging
virtual events. Data import is handled by routes/virtual/pathful_import.py.

Main Endpoints:
- GET /virtual: Main virtual sessions page
- POST /virtual/purge: Purge virtual session data
- GET /virtual/events: List virtual events (JSON)
- GET /virtual/event/<id>: Get specific virtual event (JSON)
"""

from flask import Blueprint, current_app, jsonify, render_template
from flask_login import login_required

from models.contact import LocalStatusEnum
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType, db
from models.teacher import Teacher
from models.volunteer import EventParticipation, Volunteer
from routes.decorators import admin_required

virtual_bp = Blueprint("virtual", __name__, url_prefix="/virtual")

# Register Virtual Usage (report-style) routes under the Virtual blueprint.
# NOTE: This import is intentionally placed after the blueprint is created to avoid circular imports.
try:
    from routes.virtual.usage import load_usage_routes as _load_usage_routes

    _load_usage_routes()
except Exception:
    # Non-fatal during certain tooling/import contexts; the server runtime will surface issues.
    pass

# Register Legacy Redirects for backward compatibility.
# Redirects /virtual/<slug> URLs to new /district/<slug>/portal URLs.
# NOTE: This replaces the old district_portal, magic_link, teacher_dashboard, and issues imports.
try:
    from routes.virtual import legacy_redirects  # noqa: F401
except Exception:
    # Non-fatal during certain tooling/import contexts; the server runtime will surface issues.
    pass

# Register Pathful Import routes under the Virtual blueprint.
# NOTE: This import is intentionally placed after the blueprint is created to avoid circular imports.
try:
    from routes.virtual.pathful_import import (
        load_pathful_routes as _load_pathful_routes,
    )

    _load_pathful_routes()
except Exception:
    # Non-fatal during certain tooling/import contexts; the server runtime will surface issues.
    pass


@virtual_bp.route("/virtual")
def virtual():
    """
    Display the main virtual sessions page.

    Provides the main interface for virtual session management
    and data import operations.

    Returns:
        Rendered virtual sessions template
    """
    return render_template("virtual/index.html")


@virtual_bp.route("/purge", methods=["POST"])
@login_required
@admin_required
def purge_virtual():
    """Remove all virtual session records and related data"""
    try:
        # Get all virtual session event IDs first
        virtual_event_ids = (
            db.session.query(Event.id)
            .filter(Event.type == EventType.VIRTUAL_SESSION)
            .all()
        )
        virtual_event_ids = [event_id[0] for event_id in virtual_event_ids]

        # Delete event-teacher associations for virtual sessions
        event_teacher_deleted = 0
        if virtual_event_ids:
            event_teacher_deleted = EventTeacher.query.filter(
                EventTeacher.event_id.in_(virtual_event_ids)
            ).delete(synchronize_session=False)

        # Delete event participations for virtual sessions (presenters/volunteers)
        event_participation_deleted = 0
        if virtual_event_ids:
            event_participation_deleted = EventParticipation.query.filter(
                EventParticipation.event_id.in_(virtual_event_ids)
            ).delete(synchronize_session=False)

        # Then delete the virtual session events
        deleted_count = Event.query.filter_by(type=EventType.VIRTUAL_SESSION).delete(
            synchronize_session=False
        )

        # Clean up orphaned teachers that were only created for virtual sessions
        # Find teachers who have no remaining event associations
        orphaned_teachers = Teacher.query.filter(
            ~Teacher.event_registrations.any()
        ).all()

        teacher_deleted_count = 0
        for teacher in orphaned_teachers:
            # Only delete teachers who were likely created for virtual sessions
            # (teachers without schools or with minimal data)
            if not teacher.school_id or not teacher.department:
                db.session.delete(teacher)
                teacher_deleted_count += 1

        # Commit all changes
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully purged {deleted_count} virtual sessions, {teacher_deleted_count} orphaned teachers, {event_teacher_deleted} teacher associations, and {event_participation_deleted} event participations",
                "count": deleted_count,
                "teachers_deleted": teacher_deleted_count,
                "event_teachers_deleted": event_teacher_deleted,
                "event_participations_deleted": event_participation_deleted,
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Purge failed", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@virtual_bp.route("/events", methods=["GET"])
@login_required
def list_events():
    """List all virtual events with their associated teachers and presenters"""
    try:
        events = (
            Event.query.filter_by(type=EventType.VIRTUAL_SESSION)
            .order_by(Event.start_date.desc())
            .all()
        )

        events_data = []
        for event in events:
            # Get all teacher participants
            teacher_data = [
                {
                    "id": et.teacher_id,
                    "name": f"{et.teacher.first_name} {et.teacher.last_name}",
                    "school": et.teacher.school.name if et.teacher.school else None,
                    "status": et.status,
                    "is_simulcast": et.is_simulcast,
                }
                for et in event.teacher_registrations
            ]

            # Derive presenter info from participations/volunteer since we no longer store on event
            presenter_participations = [
                p
                for p in getattr(event, "volunteer_participations", [])
                if getattr(p, "participant_type", "") == "Presenter"
            ]
            presenter_name = None
            presenter_org = None
            presenter_location_type = None
            if presenter_participations:
                # take the first presenter participation for summary
                p = presenter_participations[0]
                if getattr(p, "volunteer", None):
                    v = p.volunteer
                    presenter_name = f"{v.first_name} {v.last_name}".strip()
                    presenter_org = v.organization_name
                    try:
                        if v.local_status == LocalStatusEnum.local:
                            presenter_location_type = "Local (KS/MO)"
                        elif v.local_status == LocalStatusEnum.non_local:
                            presenter_location_type = "Non-local"
                        else:
                            presenter_location_type = None
                    except Exception:
                        presenter_location_type = None

            events_data.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "date": (
                        event.start_date.strftime("%Y-%m-%d")
                        if event.start_date
                        else None
                    ),
                    "time": (
                        event.start_date.strftime("%I:%M %p")
                        if event.start_date
                        else None
                    ),
                    "status": event.status,
                    "session_type": event.additional_information,
                    "topic": event.series,
                    "session_link": event.registration_link,
                    "presenter_name": presenter_name,
                    "presenter_organization": presenter_org,
                    "presenter_location_type": presenter_location_type,
                    "teachers": teacher_data,
                }
            )

        return jsonify({"success": True, "events": events_data})

    except Exception as e:
        current_app.logger.error("Error fetching events", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@virtual_bp.route("/event/<int:event_id>", methods=["GET"])
@login_required
def get_event(event_id):
    """Get detailed information about a specific virtual event"""
    try:
        event = Event.query.filter_by(
            id=event_id, type=EventType.VIRTUAL_SESSION
        ).first_or_404()

        # Get teacher participation details
        teacher_data = [
            {
                "id": et.teacher_id,
                "name": f"{et.teacher.first_name} {et.teacher.last_name}",
                "school": et.teacher.school.name if et.teacher.school else None,
                "status": et.status,
                "is_simulcast": et.is_simulcast,
            }
            for et in event.teacher_registrations
        ]

        # Derive presenter info for detail response
        presenter_participations = [
            p
            for p in getattr(event, "volunteer_participations", [])
            if getattr(p, "participant_type", "") == "Presenter"
        ]
        presenter_name = None
        presenter_org = None
        presenter_location_type = None
        if presenter_participations:
            p = presenter_participations[0]
            if getattr(p, "volunteer", None):
                v = p.volunteer
                presenter_name = f"{v.first_name} {v.last_name}".strip()
                presenter_org = v.organization_name
                try:
                    if v.local_status == LocalStatusEnum.local:
                        presenter_location_type = "Local (KS/MO)"
                    elif v.local_status == LocalStatusEnum.non_local:
                        presenter_location_type = "Non-local"
                    else:
                        presenter_location_type = None
                except Exception:
                    presenter_location_type = None

        return jsonify(
            {
                "success": True,
                "event": {
                    "id": event.id,
                    "title": event.title,
                    "date": (
                        event.start_date.strftime("%Y-%m-%d")
                        if event.start_date
                        else None
                    ),
                    "time": (
                        event.start_date.strftime("%I:%M %p")
                        if event.start_date
                        else None
                    ),
                    "status": event.status,
                    "session_type": event.additional_information,
                    "topic": event.series,
                    "session_link": event.registration_link,
                    "presenter_name": presenter_name,
                    "presenter_organization": presenter_org,
                    "presenter_location_type": presenter_location_type,
                    "teachers": teacher_data,
                },
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error fetching event {event_id}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400
