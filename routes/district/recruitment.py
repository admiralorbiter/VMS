"""
District Recruitment Routes

Provides recruitment tools for district administrators to proactively
fill volunteer gaps for events.

FR-SELFSERV-401: Recruitment Dashboard
FR-SELFSERV-402: Volunteer Scoring & Matching
FR-SELFSERV-403: Outreach Tracking
"""

from datetime import datetime, timezone

from flask import (
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
from models.event import Event, EventStatus
from models.outreach import OutreachAttempt
from models.volunteer import Volunteer
from routes.district import district_bp
from routes.district.events import require_district_admin, require_tenant_context

# =============================================================================
# Urgency Calculation
# =============================================================================


def calculate_urgency(event, confirmed_count):
    """
    Calculate urgency level for an event based on fill rate and time remaining.

    Returns:
        tuple: (urgency_level, urgency_score)
        - urgency_level: 'critical', 'warning', or 'on_track'
        - urgency_score: numeric score for sorting (higher = more urgent)
    """
    if not event.start_date or not event.volunteers_needed:
        return ("on_track", 0)

    days_until = (event.start_date.date() - datetime.now().date()).days
    fill_rate = (
        confirmed_count / event.volunteers_needed
        if event.volunteers_needed > 0
        else 1.0
    )

    # Calculate urgency score (higher = more urgent)
    urgency_score = 0

    # Time factor: closer events get higher urgency
    if days_until <= 0:
        urgency_score += 100  # Event is today or past
    elif days_until <= 3:
        urgency_score += 80
    elif days_until <= 7:
        urgency_score += 50
    elif days_until <= 14:
        urgency_score += 30
    else:
        urgency_score += 10

    # Fill rate factor: lower fill rate = higher urgency
    if fill_rate < 0.25:
        urgency_score += 50
    elif fill_rate < 0.50:
        urgency_score += 35
    elif fill_rate < 0.75:
        urgency_score += 20
    else:
        urgency_score += 5

    # Determine level based on thresholds
    if days_until <= 3 and fill_rate < 0.50:
        urgency_level = "critical"
    elif days_until <= 7 and fill_rate < 0.75:
        urgency_level = "warning"
    else:
        urgency_level = "on_track"

    return (urgency_level, urgency_score)


def get_events_needing_volunteers(tenant_id):
    """
    Get events that need more volunteers, with urgency calculation.

    FR-SELFSERV-401: Recruitment dashboard showing events with urgency indicators.
    """
    # Get upcoming events that need volunteers (Draft or Published, not Completed/Cancelled)
    events = (
        Event.query.filter(
            Event.tenant_id == tenant_id,
            Event.status.in_([EventStatus.DRAFT, EventStatus.PUBLISHED]),
            Event.start_date > datetime.now(),
            Event.volunteers_needed > 0,
        )
        .order_by(Event.start_date)
        .all()
    )

    result = []
    for event in events:
        confirmed = DistrictParticipation.query.filter_by(
            event_id=event.id,
            tenant_id=tenant_id,
            status="confirmed",
        ).count()

        invited = DistrictParticipation.query.filter_by(
            event_id=event.id,
            tenant_id=tenant_id,
            status="invited",
        ).count()

        # Show events that need more volunteers
        if confirmed < event.volunteers_needed:
            urgency_level, urgency_score = calculate_urgency(event, confirmed)
            result.append(
                {
                    "event": event,
                    "confirmed": confirmed,
                    "invited": invited,
                    "needed": event.volunteers_needed,
                    "remaining": event.volunteers_needed - confirmed,
                    "fill_rate": confirmed / event.volunteers_needed,
                    "urgency_level": urgency_level,
                    "urgency_score": urgency_score,
                }
            )

    # Sort by urgency score (highest first)
    return sorted(result, key=lambda x: x["urgency_score"], reverse=True)


# =============================================================================
# Volunteer Scoring (FR-SELFSERV-402)
# =============================================================================


def score_volunteer_for_event(volunteer, event, tenant_id):
    """
    Calculate a relevance score for a volunteer for a specific event.

    FR-SELFSERV-402: Rank volunteer candidates using scoring based on
    participation history, skills match, and location.

    Returns:
        dict: {score, breakdown, reasons}
    """
    score = 0
    breakdown = {}
    reasons = []

    # 1. Participation History (30% weight)
    past_participations = DistrictParticipation.query.filter_by(
        volunteer_id=volunteer.id,
        tenant_id=tenant_id,
        status="attended",
    ).count()

    history_score = min(past_participations * 5, 30)  # Max 30 points
    breakdown["history"] = history_score
    score += history_score
    if past_participations > 0:
        reasons.append(f"Attended {past_participations} past events")

    # 2. Recency (20% weight) - Recent activity is valued
    last_attendance = (
        DistrictParticipation.query.filter_by(
            volunteer_id=volunteer.id,
            tenant_id=tenant_id,
            status="attended",
        )
        .order_by(DistrictParticipation.attended_at.desc())
        .first()
    )

    if last_attendance and last_attendance.attended_at:
        days_since = (datetime.now(timezone.utc) - last_attendance.attended_at).days
        if days_since < 30:
            recency_score = 20
            reasons.append("Active in last 30 days")
        elif days_since < 90:
            recency_score = 15
            reasons.append("Active in last 90 days")
        elif days_since < 180:
            recency_score = 10
        else:
            recency_score = 5
    else:
        recency_score = 0
    breakdown["recency"] = recency_score
    score += recency_score

    # 3. Skills Match (25% weight)
    # Check if volunteer has skills matching event type
    skill_score = 0
    if hasattr(volunteer, "skills") and volunteer.skills:
        event_type_keywords = _get_event_type_keywords(
            event.type.value if event.type else ""
        )
        for skill in volunteer.skills:
            skill_name = (
                skill.skill.name.lower()
                if hasattr(skill, "skill")
                else skill.name.lower()
            )
            if any(kw in skill_name for kw in event_type_keywords):
                skill_score += 8
                reasons.append(f"Has relevant skill: {skill_name}")
        skill_score = min(skill_score, 25)  # Cap at 25
    breakdown["skills"] = skill_score
    score += skill_score

    # 4. Organization/Proximity (15% weight)
    proximity_score = 0
    if volunteer.organization_name:
        proximity_score = 10
        reasons.append(f"From: {volunteer.organization_name}")
    breakdown["proximity"] = proximity_score
    score += proximity_score

    # 5. Availability (10% weight) - Not already assigned to this event
    is_available = not DistrictParticipation.query.filter_by(
        volunteer_id=volunteer.id,
        event_id=event.id,
        tenant_id=tenant_id,
    ).first()

    availability_score = 10 if is_available else 0
    breakdown["availability"] = availability_score
    score += availability_score
    if not is_available:
        reasons.append("Already assigned to this event")

    return {
        "score": score,
        "breakdown": breakdown,
        "reasons": reasons,
    }


def _get_event_type_keywords(event_type):
    """Get keywords associated with an event type for skill matching."""
    keywords_map = {
        "career_fair": ["career", "professional", "business", "networking"],
        "classroom_presentation": ["teaching", "education", "presentation", "speaking"],
        "mock_interview": ["interview", "hr", "hiring", "professional"],
        "job_shadow": ["mentoring", "professional", "shadowing"],
        "field_trip": ["tour", "hosting", "organization"],
        "mentoring": ["mentoring", "coaching", "guidance"],
        "workshop": ["training", "workshop", "facilitation"],
    }
    return keywords_map.get(event_type, ["volunteer", "community"])


def get_ranked_candidates(event_id, tenant_id, limit=50):
    """
    Get volunteers ranked by relevance for an event.

    FR-SELFSERV-402: System shall rank volunteer candidates using scoring.
    """
    event = Event.query.get(event_id)
    if not event:
        return []

    # Get all active volunteers in this tenant
    volunteers = (
        Volunteer.query.join(DistrictVolunteer)
        .filter(
            DistrictVolunteer.tenant_id == tenant_id,
            DistrictVolunteer.status == "active",
        )
        .all()
    )

    # Score each volunteer
    candidates = []
    for volunteer in volunteers:
        scoring = score_volunteer_for_event(volunteer, event, tenant_id)

        # Get outreach history
        outreach_count = OutreachAttempt.query.filter_by(
            volunteer_id=volunteer.id,
            event_id=event_id,
            tenant_id=tenant_id,
        ).count()

        last_outreach = (
            OutreachAttempt.query.filter_by(
                volunteer_id=volunteer.id,
                event_id=event_id,
                tenant_id=tenant_id,
            )
            .order_by(OutreachAttempt.attempted_at.desc())
            .first()
        )

        candidates.append(
            {
                "volunteer": volunteer,
                "score": scoring["score"],
                "breakdown": scoring["breakdown"],
                "reasons": scoring["reasons"],
                "outreach_count": outreach_count,
                "last_outreach": last_outreach,
            }
        )

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]


# =============================================================================
# Routes
# =============================================================================


@district_bp.route("/recruitment")
@login_required
@require_tenant_context
def recruitment_dashboard():
    """
    Recruitment dashboard showing events that need volunteers.

    FR-SELFSERV-401: Display events with urgency indicators.
    """
    events_needing = get_events_needing_volunteers(g.tenant_id)

    # Summary stats
    total_needed = sum(e["remaining"] for e in events_needing)
    critical_count = sum(1 for e in events_needing if e["urgency_level"] == "critical")
    warning_count = sum(1 for e in events_needing if e["urgency_level"] == "warning")

    return render_template(
        "district/recruitment/dashboard.html",
        events=events_needing,
        total_needed=total_needed,
        critical_count=critical_count,
        warning_count=warning_count,
        page_title="Recruitment Dashboard",
    )


@district_bp.route("/recruitment/event/<int:event_id>")
@login_required
@require_tenant_context
def recruitment_event(event_id):
    """
    Recruitment view for a specific event with candidate list.

    FR-SELFSERV-401, FR-SELFSERV-402: Event-specific recruitment with ranked candidates.
    """
    event = Event.query.filter_by(id=event_id, tenant_id=g.tenant_id).first_or_404()

    # Get recruitment stats
    confirmed = DistrictParticipation.query.filter_by(
        event_id=event_id, tenant_id=g.tenant_id, status="confirmed"
    ).count()
    invited = DistrictParticipation.query.filter_by(
        event_id=event_id, tenant_id=g.tenant_id, status="invited"
    ).count()

    urgency_level, urgency_score = calculate_urgency(event, confirmed)

    # Get ranked candidates
    candidates = get_ranked_candidates(event_id, g.tenant_id)

    # Get outreach history
    outreach_history = (
        OutreachAttempt.query.filter_by(event_id=event_id, tenant_id=g.tenant_id)
        .order_by(OutreachAttempt.attempted_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "district/recruitment/event.html",
        event=event,
        confirmed=confirmed,
        invited=invited,
        candidates=candidates,
        outreach_history=outreach_history,
        urgency_level=urgency_level,
        page_title=f"Recruit for: {event.title}",
    )


@district_bp.route("/recruitment/outreach", methods=["POST"])
@login_required
@require_district_admin
def log_outreach():
    """
    Log a recruitment outreach attempt.

    FR-SELFSERV-403: District staff shall be able to log outreach attempts
    and track outcomes.
    """
    volunteer_id = request.form.get("volunteer_id", type=int)
    event_id = request.form.get("event_id", type=int)
    method = request.form.get("method")
    outcome = request.form.get("outcome", "pending")
    notes = request.form.get("notes", "").strip() or None

    if not all([volunteer_id, event_id, method]):
        flash("Missing required fields.", "error")
        return redirect(request.referrer or url_for("district.recruitment_dashboard"))

    # Verify volunteer belongs to tenant
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id, tenant_id=g.tenant_id
    ).first()
    if not district_vol:
        flash("Volunteer not found in your district.", "error")
        return redirect(request.referrer or url_for("district.recruitment_dashboard"))

    # Verify event belongs to tenant
    event = Event.query.filter_by(id=event_id, tenant_id=g.tenant_id).first()
    if not event:
        flash("Event not found.", "error")
        return redirect(request.referrer or url_for("district.recruitment_dashboard"))

    try:
        OutreachAttempt.log_attempt(
            volunteer_id=volunteer_id,
            event_id=event_id,
            tenant_id=g.tenant_id,
            method=method,
            outcome=outcome,
            notes=notes,
            attempted_by_id=current_user.id,
        )

        volunteer = Volunteer.query.get(volunteer_id)
        flash(
            f"Logged {method} outreach to {volunteer.first_name} {volunteer.last_name}.",
            "success",
        )

        # If confirmed, also assign to event roster
        if outcome == "confirmed":
            existing = DistrictParticipation.query.filter_by(
                volunteer_id=volunteer_id,
                event_id=event_id,
                tenant_id=g.tenant_id,
            ).first()

            if existing:
                existing.status = "confirmed"
                existing.confirmed_at = datetime.now(timezone.utc)
            else:
                participation = DistrictParticipation(
                    volunteer_id=volunteer_id,
                    event_id=event_id,
                    tenant_id=g.tenant_id,
                    status="confirmed",
                    confirmed_at=datetime.now(timezone.utc),
                )
                db.session.add(participation)
            db.session.commit()
            flash(
                f"{volunteer.first_name} has been added to the event roster.", "success"
            )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error logging outreach: {e}")
        flash("An error occurred while logging outreach.", "error")

    return redirect(url_for("district.recruitment_event", event_id=event_id))


@district_bp.route("/recruitment/outreach/<int:outreach_id>/update", methods=["POST"])
@login_required
@require_district_admin
def update_outreach(outreach_id):
    """Update the outcome of an outreach attempt."""
    outreach = OutreachAttempt.query.filter_by(
        id=outreach_id, tenant_id=g.tenant_id
    ).first_or_404()

    outcome = request.form.get("outcome")
    notes = request.form.get("notes", "").strip() or None

    if outcome:
        outreach.update_outcome(outcome, notes)
        flash("Outreach updated.", "success")

    return redirect(url_for("district.recruitment_event", event_id=outreach.event_id))


@district_bp.route("/recruitment/outreach/history/<int:volunteer_id>/<int:event_id>")
@login_required
@require_tenant_context
def outreach_history(volunteer_id, event_id):
    """Get outreach history for a volunteer/event pair (JSON)."""
    history = OutreachAttempt.get_history(volunteer_id, event_id, g.tenant_id)

    return jsonify(
        [
            {
                "id": h.id,
                "method": h.method,
                "outcome": h.outcome,
                "notes": h.notes,
                "attempted_at": h.attempted_at.isoformat() if h.attempted_at else None,
                "attempted_by": h.attempted_by.name if h.attempted_by else None,
            }
            for h in history
        ]
    )
