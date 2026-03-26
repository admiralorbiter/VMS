"""
Tenant Teacher Usage Routes
============================

Routes for Virtual Admin to view teacher progress/usage dashboard.
Shows which teachers have completed their virtual session goals.
"""

from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from models.attendance_override import AttendanceOverride, OverrideAction
from models.audit_log import AuditLog
from models.teacher_data_flag import TeacherDataFlag, TeacherDataFlagType
from models.teacher_progress import TeacherProgress
from models.tenant import Tenant
from models.user import TenantRole
from services.academic_year_service import (
    get_current_academic_year,
    get_current_semester,
    get_semester_dates,
)
from services.teacher_matching_service import (
    build_teacher_alias_map,
    count_sessions_for_teachers,
)

teacher_usage_bp = Blueprint(
    "teacher_usage", __name__, url_prefix="/district/teacher-usage"
)


def virtual_admin_required(f):
    """Decorator to require Virtual Admin or higher tenant role."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("login"))

        # Global admins can access everything
        if current_user.is_admin:
            return f(*args, **kwargs)

        # Must have a tenant
        if not current_user.tenant_id:
            flash("This feature is only available for district users.", "error")
            return redirect(url_for("index"))

        # All tenant roles can access teacher usage dashboard
        allowed_roles = [
            TenantRole.VIRTUAL_ADMIN,
            TenantRole.ADMIN,
            TenantRole.COORDINATOR,
            TenantRole.USER,
        ]
        if current_user.tenant_role not in allowed_roles:
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for("district.virtual_sessions"))

        return f(*args, **kwargs)

    return decorated_function


# Note: get_current_academic_year and get_current_semester are imported from
# services.academic_year_service


def get_tenant_district_name(tenant_id=None):
    """Get district name for a tenant (defaults to current user's tenant)."""
    tid = tenant_id or current_user.tenant_id
    if not tid:
        return None
    tenant = Tenant.query.get(tid)
    return tenant.name if tenant else None


def _backfill_teacher_ids(teachers):
    """Resolve null teacher_id on TeacherProgress records.

    Delegates to the centralized ``resolve_teacher_for_tp`` in
    ``teacher_matching_service`` for consistent matching across the system.
    """
    from services.teacher_matching_service import resolve_teacher_for_tp

    orphans = [t for t in teachers if t.teacher_id is None]
    if not orphans:
        return

    linked = 0
    for tp in orphans:
        if resolve_teacher_for_tp(tp):
            linked += 1

    if linked:
        db.session.commit()


def compute_teacher_progress(tenant_id, academic_year, date_from=None, date_to=None):
    """
    Compute teacher progress data for a tenant.

    Counting strategy (EventTeacher-primary, text-supplementary):
    1. EventTeacher path (primary): count FK-linked events (all TeacherProgress
       have teacher_id, so this catches everything)
    2. Text path (supplementary): match teacher names in event.educators for
       events NOT already counted (catches edge cases with unresolvable names)

    Returns dict of building -> {teachers: [], stats}
    """
    from models import Event
    from models.event import EventStatus, EventTeacher, EventType
    from models.tenant import Tenant

    # Get all active teachers for this tenant/year
    teachers = (
        TeacherProgress.query.filter_by(
            tenant_id=tenant_id, academic_year=academic_year, is_active=True
        )
        .order_by(TeacherProgress.building, TeacherProgress.name)
        .all()
    )

    if not teachers:
        return {}

    # ── Backfill null teacher_id values ────────────────────────────────
    # TeacherProgress records imported before FK backfill logic was added
    # may have teacher_id = None.  Resolve by name/email matching.
    _backfill_teacher_ids(teachers)

    # Get the tenant's linked district name(s) for filtering sessions.
    # We use ALL known variants (canonical name + aliases) because
    # Event.district_partner stores Pathful-imported strings that may
    # not match the canonical District.name.
    from services.district_service import get_district_name_variants

    tenant = Tenant.query.get(tenant_id)
    district_names = set()
    if tenant:
        if tenant.district:
            district_names = get_district_name_variants(tenant.district)
        else:
            linked = tenant.get_setting("linked_district_name")
            if linked:
                district_names = {linked}

    # Map teacher_id -> list of TeacherProgress IDs (for EventTeacher lookups)
    teacher_id_to_tp = {}
    for t in teachers:
        if t.teacher_id:
            teacher_id_to_tp.setdefault(t.teacher_id, []).append(t.id)

    # Build text alias map for supplementary matching
    teacher_progress_map, teacher_alias_map = build_teacher_alias_map(teachers)

    # ── COMPLETED sessions ─────────────────────────────────────────────
    # Primary: EventTeacher FK links
    #
    # Two sets track different things:
    #   all_et_event_ids     – every event linked via EventTeacher (any status)
    #                          used to exclude events from supplementary text-matching
    #   counted_events_per_tp – (tp_id, event_id) pairs that were actually counted
    #                          (attended/completed) — used for override logic
    all_et_event_ids = set()
    counted_events_per_tp = set()  # {(tp_id, event_id), ...}
    if teacher_id_to_tp:
        # Query ALL EventTeacher records (including no_show) to build exclusion set
        all_et_query = EventTeacher.query.join(Event).filter(
            EventTeacher.teacher_id.in_(teacher_id_to_tp.keys()),
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
        )
        # NOTE: We intentionally do NOT filter by district_partner here.
        # The EventTeacher FK already proves the teacher attended the event,
        # and TeacherProgress scopes them to the correct tenant.  Pathful
        # sometimes assigns the wrong district_partner to multi-district
        # sessions (e.g. a KCKPS event labelled "Hogan Preparatory Academy"),
        # which would cause attended sessions to be silently dropped.
        # The district_partner filter is only applied on the supplementary
        # text-matching path below where there is no FK proof of attendance.
        if date_from:
            all_et_query = all_et_query.filter(Event.start_date >= date_from)
        if date_to:
            all_et_query = all_et_query.filter(Event.start_date <= date_to)

        for et in all_et_query.all():
            all_et_event_ids.add(et.event_id)
            # Only count attended/completed toward progress
            if et.status in ("attended", "completed"):
                for tp_id in teacher_id_to_tp.get(et.teacher_id, []):
                    if tp_id in teacher_progress_map:
                        teacher_progress_map[tp_id] += 1
                        counted_events_per_tp.add((tp_id, et.event_id))

    # Supplementary: text matching for events NOT linked via EventTeacher.
    # Uses all_et_event_ids (not just counted) so that no_show events
    # are excluded from text-matching and don't get double-counted.
    events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION, Event.status == EventStatus.COMPLETED
    )
    if district_names:
        events_query = events_query.filter(Event.district_partner.in_(district_names))
    if date_from:
        events_query = events_query.filter(Event.start_date >= date_from)
    if date_to:
        events_query = events_query.filter(Event.start_date <= date_to)
    events = events_query.all()

    supplementary_events = [e for e in events if e.id not in all_et_event_ids]
    if supplementary_events:
        teacher_progress_map = count_sessions_for_teachers(
            supplementary_events, teacher_alias_map, teacher_progress_map
        )

    # ── Apply attendance overrides (FR-VIRTUAL-234, FR-VIRTUAL-238) ────
    # Both ADD and REMOVE overrides are event-aware:
    # - ADD:    only increment if this event was NOT already counted
    #           AND the event is in the past (future sign-ups don't count)
    # - REMOVE: only decrement if this event WAS counted as attended
    # Stale ADD overrides (event already counted via import) are auto-resolved.
    import logging
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    logger = logging.getLogger(__name__)
    active_overrides = AttendanceOverride.query.filter(
        AttendanceOverride.teacher_progress_id.in_([t.id for t in teachers]),
        AttendanceOverride.is_active == True,  # noqa: E712
    ).all()
    for ov in active_overrides:
        tid = ov.teacher_progress_id
        if tid in teacher_progress_map:
            if ov.action == OverrideAction.ADD:
                if (tid, ov.event_id) not in counted_events_per_tp:
                    # Only count past sessions toward progress —
                    # future sign-ups (registered) should NOT count
                    event = Event.query.get(ov.event_id)
                    if event and event.start_date:
                        ev_date = event.start_date
                        if ev_date.tzinfo is None:
                            ev_date = ev_date.replace(tzinfo=timezone.utc)
                        if ev_date >= now:
                            continue  # Skip future events
                    teacher_progress_map[tid] += 1
                    counted_events_per_tp.add((tid, ov.event_id))
                else:
                    # Stale ADD — event already counted via import data
                    ov.reverse(
                        reason="Auto-resolved: event already counted via import data"
                    )
                    logger.info(
                        "Auto-resolved stale ADD override %d " "(tp=%d, event=%d)",
                        ov.id,
                        tid,
                        ov.event_id,
                    )
            elif ov.action == OverrideAction.REMOVE:
                # Only subtract if this event was actually counted
                if (tid, ov.event_id) in counted_events_per_tp:
                    teacher_progress_map[tid] = max(0, teacher_progress_map[tid] - 1)

    # ── PLANNED sessions (upcoming: confirmed/published/requested) ─────

    planned_events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status.in_(
            [EventStatus.CONFIRMED, EventStatus.PUBLISHED, EventStatus.REQUESTED]
        ),
        Event.start_date >= now,
    )
    if district_names:
        planned_events_query = planned_events_query.filter(
            Event.district_partner.in_(district_names)
        )
    planned_events = planned_events_query.all()

    planned_progress_map = {t.id: 0 for t in teachers}

    # Primary: count via EventTeacher FK links (picks up override sign-ups)
    if teacher_id_to_tp:
        planned_et_query = EventTeacher.query.join(Event).filter(
            EventTeacher.teacher_id.in_(teacher_id_to_tp.keys()),
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status.in_(
                [EventStatus.CONFIRMED, EventStatus.PUBLISHED, EventStatus.REQUESTED]
            ),
            Event.start_date >= now,
        )
        planned_et_event_ids = set()
        for et in planned_et_query.all():
            planned_et_event_ids.add(et.event_id)
            for tp_id in teacher_id_to_tp.get(et.teacher_id, []):
                if tp_id in planned_progress_map:
                    planned_progress_map[tp_id] += 1

        # Text-matching fallback: only for events NOT already counted via FK
        text_planned_events = [
            e for e in planned_events if e.id not in planned_et_event_ids
        ]
    else:
        text_planned_events = planned_events

    # Supplementary: text matching
    planned_progress_map = count_sessions_for_teachers(
        text_planned_events, teacher_alias_map, planned_progress_map
    )

    # ── NEEDS REVIEW sessions (past date, not completed) ───────────────
    # These are events that already happened but were never marked as
    in_planning_statuses = [
        EventStatus.CONFIRMED,
        EventStatus.PUBLISHED,
        EventStatus.REQUESTED,
    ]
    in_planning_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status.in_(in_planning_statuses),
        Event.start_date < now,
    )
    if district_names:
        in_planning_query = in_planning_query.filter(
            Event.district_partner.in_(district_names)
        )
    if date_from:
        in_planning_query = in_planning_query.filter(Event.start_date >= date_from)
    if date_to:
        in_planning_query = in_planning_query.filter(Event.start_date <= date_to)
    in_planning_events = in_planning_query.all()

    in_planning_map = {t.id: 0 for t in teachers}
    in_planning_map = count_sessions_for_teachers(
        in_planning_events, teacher_alias_map, in_planning_map
    )

    # Aggregate by building
    building_data = {}

    for teacher in teachers:
        building = teacher.building or "Unknown"

        if building not in building_data:
            building_data[building] = {
                "total_teachers": 0,
                "goals_achieved": 0,
                "goals_in_progress": 0,
                "goals_not_started": 0,
                "teachers": [],
            }

        bd = building_data[building]
        bd["total_teachers"] += 1

        # Get matched session count
        completed = teacher_progress_map[teacher.id]
        planned = planned_progress_map[teacher.id]
        in_planning = in_planning_map[teacher.id]
        target = teacher.target_sessions or 1

        # Determine status (consider completed, planned, and in-planning sessions)
        if completed >= target:
            status_class = "achieved"
            status_text = "Goal Achieved"
            bd["goals_achieved"] += 1
        elif completed > 0 or planned > 0:
            status_class = "in_progress"
            status_text = "In Progress"
            bd["goals_in_progress"] += 1
        elif in_planning > 0:
            status_class = "in_planning"
            status_text = "Needs Review"
            bd["goals_in_progress"] += 1
        else:
            status_class = "not_started"
            status_text = "Not Started"
            bd["goals_not_started"] += 1

        # Calculate progress percentage
        progress_pct = min(100, (completed / target * 100)) if target > 0 else 0

        # Check for open data flags
        open_flags_count = TeacherDataFlag.query.filter_by(
            teacher_progress_id=teacher.id, is_resolved=False
        ).count()

        bd["teachers"].append(
            {
                "id": teacher.id,
                "teacher_id": teacher.teacher_id,
                "name": teacher.name,
                "email": teacher.email,
                "grade": teacher.grade or "",
                "target_sessions": target,
                "completed_sessions": completed,
                "progress_percentage": progress_pct,
                "goal_status_class": status_class,
                "goal_status_text": status_text,
                "progress_class": (
                    "achieved"
                    if completed >= target
                    else ("warning" if completed > 0 else "danger")
                ),
                "has_open_flags": open_flags_count > 0,
                "open_flags_count": open_flags_count,
            }
        )

    # Sort buildings alphabetically
    return dict(sorted(building_data.items()))


@teacher_usage_bp.route("/")
@login_required
@virtual_admin_required
def index():
    """Main teacher usage/progress dashboard."""
    academic_year = request.args.get("year", get_current_academic_year())
    semester = request.args.get("semester", get_current_semester())

    # Admin users can specify a tenant via query param
    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        tenant_id = admin_tenant_id
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            flash("Tenant not found.", "error")
            return redirect(url_for("virtual.virtual_sessions"))
        district_name = tenant.district.name if tenant.district else tenant.name
    else:
        tenant_id = current_user.tenant_id
        district_name = get_tenant_district_name()

    # For global admins without tenant, redirect to sessions page
    if not tenant_id:
        flash("Please select a tenant to view teacher usage.", "warning")
        return redirect(url_for("virtual.virtual_sessions"))

    # Get available years
    years = (
        db.session.query(TeacherProgress.academic_year)
        .filter_by(tenant_id=tenant_id)
        .distinct()
        .all()
    )
    year_options = (
        sorted([y[0] for y in years], reverse=True) if years else [academic_year]
    )

    # Calculate semester date range using shared service
    date_from, date_to = get_semester_dates(academic_year, semester)

    # Compute progress data for this semester
    teacher_progress_data = compute_teacher_progress(
        tenant_id=tenant_id,
        academic_year=academic_year,
        date_from=date_from,
        date_to=date_to,
    )

    return render_template(
        "district/teacher_usage/index.html",
        district_name=district_name or "Your District",
        academic_year=academic_year,
        year_options=year_options,
        semester=semester,
        teacher_progress_data=teacher_progress_data,
        admin_tenant_id=admin_tenant_id,
    )


@teacher_usage_bp.route("/export")
@login_required
@virtual_admin_required
def export_excel():
    """Export teacher progress to Excel."""
    import io

    from flask import send_file

    try:
        import pandas as pd
    except ImportError:
        flash("Export requires pandas. Please contact administrator.", "error")
        return redirect(url_for("teacher_usage.index"))

    academic_year = request.args.get("year", get_current_academic_year())
    semester = request.args.get("semester", get_current_semester())

    # Admin users can specify a tenant via query param
    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        tenant_id = admin_tenant_id
        tenant = Tenant.query.get(tenant_id)
        district_name = (
            tenant.district.name
            if tenant and tenant.district
            else tenant.name if tenant else "District"
        )
    else:
        tenant_id = current_user.tenant_id
        district_name = get_tenant_district_name() or "District"

    if not tenant_id:
        flash("No tenant assigned.", "error")
        return redirect(url_for("virtual.virtual_sessions"))

    # Calculate semester date range using shared service
    date_from, date_to = get_semester_dates(academic_year, semester)

    # Get progress data
    teacher_progress_data = compute_teacher_progress(
        tenant_id=tenant_id,
        academic_year=academic_year,
        date_from=date_from,
        date_to=date_to,
    )

    # Flatten to rows
    rows = []
    for building, data in teacher_progress_data.items():
        for teacher in data["teachers"]:
            rows.append(
                {
                    "Building": building,
                    "Name": teacher["name"],
                    "Email": teacher["email"],
                    "Grade": teacher["grade"],
                    "Target Sessions": teacher["target_sessions"],
                    "Completed Sessions": teacher["completed_sessions"],
                    "Status": teacher["goal_status_text"],
                }
            )

    if not rows:
        flash("No data to export.", "warning")
        return redirect(url_for("teacher_usage.index", year=academic_year))

    df = pd.DataFrame(rows)

    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Teacher Progress")
    output.seek(0)

    filename = (
        f"{district_name.replace(' ', '_')}_Teacher_Progress_{academic_year}.xlsx"
    )

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# ── Teacher Detail View ───────────────────────────────────────────────


@teacher_usage_bp.route("/teacher/<int:teacher_progress_id>")
@login_required
@virtual_admin_required
def teacher_detail(teacher_progress_id):
    """View a teacher's virtual session history from the usage dashboard.

    Dual-path matching (EventTeacher-primary, text-supplementary):
    1. EventTeacher path (primary): find FK-linked sessions (all TeacherProgress
       have teacher_id, so this catches everything)
    2. Text path (supplementary): match teacher name in event.educators for
       events NOT found via EventTeacher (catches edge cases)
    Deduplicates via matched_event_ids.
    """
    from datetime import datetime, timezone

    from models.event import Event, EventStatus, EventTeacher, EventType
    from services.teacher_matching_service import (
        build_teacher_alias_map,
        match_educator_to_teacher,
    )

    tp = TeacherProgress.query.get_or_404(teacher_progress_id)

    # Admin users can specify a tenant via query param
    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        effective_tenant_id = admin_tenant_id
    else:
        effective_tenant_id = current_user.tenant_id

    district_name = get_tenant_district_name(effective_tenant_id) or "Your District"

    # Resolve the tenant's linked district name(s) — use all variants
    from services.district_service import get_district_name_variants

    tenant = Tenant.query.get(effective_tenant_id)
    district_names = set()
    if tenant:
        if tenant.district:
            district_names = get_district_name_variants(tenant.district)
        else:
            linked = tenant.get_setting("linked_district_name")
            if linked:
                district_names = {linked}

    now = datetime.now(timezone.utc)
    past_sessions = []
    upcoming_sessions = []
    matched_event_ids = set()

    def _build_session_data(event, et=None):
        """Build session data dict from an Event, with optional EventTeacher metadata."""
        presenter_name = ""
        presenter_org = ""
        if event.volunteers:
            vol = event.volunteers[0]
            presenter_name = f"{vol.first_name} {vol.last_name}".strip()
            presenter_org = vol.organization_name or ""

        start_date = event.start_date
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        return {
            "id": event.id,
            "title": event.title or "Untitled Session",
            "date": start_date.date() if start_date else None,
            "time": start_date.time() if start_date else None,
            "datetime": start_date,
            "status": event.status.value if event.status else "unknown",
            "topic_theme": event.series or "",
            "session_link": event.registration_link or "",
            "presenter_name": presenter_name,
            "presenter_org": presenter_org,
            "is_simulcast": getattr(et, "is_simulcast", False) if et else False,
            "attendance_status": (et.status or "") if et else "",
        }

    def _classify_session(session_data, event):
        """Add session to past or upcoming list based on date."""
        start_date = session_data["datetime"]
        if start_date and start_date < now:
            past_sessions.append(session_data)
        elif start_date and start_date >= now:
            if event.status in [
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
                EventStatus.COMPLETED,
            ]:
                upcoming_sessions.append(session_data)

    # --- Path 1 (primary): EventTeacher FK links ---
    if tp.teacher_id:
        et_links = EventTeacher.query.filter_by(teacher_id=tp.teacher_id).all()
        for et in et_links:
            event = et.event
            if not event or event.type != EventType.VIRTUAL_SESSION:
                continue

            matched_event_ids.add(event.id)
            session_data = _build_session_data(event, et)
            _classify_session(session_data, event)

    # --- Path 2 (supplementary): Text matching for unmatched events ---
    _, alias_map = build_teacher_alias_map([tp])

    events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
    )
    if district_names:
        events_query = events_query.filter(Event.district_partner.in_(district_names))
    events = events_query.order_by(Event.start_date.desc()).all()

    for event in events:
        if event.id in matched_event_ids:
            continue  # Already found via EventTeacher
        if not event.educators:
            continue

        educator_names = [n.strip() for n in event.educators.split(";") if n.strip()]
        matched = any(
            match_educator_to_teacher(name, alias_map) == tp.id
            for name in educator_names
        )
        if not matched:
            continue

        matched_event_ids.add(event.id)
        session_data = _build_session_data(event)
        _classify_session(session_data, event)

    # ── Merge attendance overrides into session lists ──────────────────
    add_overrides = AttendanceOverride.query.filter_by(
        teacher_progress_id=tp.id,
        action=OverrideAction.ADD,
        is_active=True,
    ).all()

    # Build set of event IDs that have active "remove" overrides
    remove_override_event_ids = set(
        ov.event_id
        for ov in AttendanceOverride.query.filter_by(
            teacher_progress_id=tp.id,
            action=OverrideAction.REMOVE,
            is_active=True,
        ).all()
    )

    # Tag existing sessions that have been removed via override
    past_sessions = [
        s for s in past_sessions if s["id"] not in remove_override_event_ids
    ]

    # Add sessions credited via override that aren't already in either list
    existing_event_ids = {s["id"] for s in past_sessions} | {
        s["id"] for s in upcoming_sessions
    }
    for ov in add_overrides:
        if ov.event_id not in existing_event_ids:
            event = Event.query.get(ov.event_id)
            if event:
                start_date = event.start_date
                if start_date and start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

                presenter_name = ""
                presenter_org = ""
                if event.volunteers:
                    vol = event.volunteers[0]
                    presenter_name = f"{vol.first_name} {vol.last_name}".strip()
                    presenter_org = vol.organization_name or ""

                session_data = {
                    "id": event.id,
                    "title": event.title or "Untitled Session",
                    "date": start_date.date() if start_date else None,
                    "time": start_date.time() if start_date else None,
                    "datetime": start_date,
                    "status": event.status.value if event.status else "unknown",
                    "topic_theme": event.series or "",
                    "session_link": event.registration_link or "",
                    "presenter_name": presenter_name,
                    "presenter_org": presenter_org,
                    "is_simulcast": False,
                    "is_override": True,
                    "override_id": ov.id,
                    "override_reason": ov.reason,
                }

                # Classify into correct list based on event date
                if start_date and start_date >= now:
                    session_data["attendance_status"] = "registered"
                    upcoming_sessions.append(session_data)
                else:
                    session_data["attendance_status"] = "attended"
                    past_sessions.append(session_data)

    # Tag override sessions in existing lists (both past and upcoming)
    override_add_map = {ov.event_id: ov.id for ov in add_overrides}
    override_reason_map = {ov.event_id: ov.reason for ov in add_overrides}
    for session in past_sessions + upcoming_sessions:
        if "is_override" not in session:
            session["is_override"] = session["id"] in override_add_map
            if session["is_override"]:
                session["override_id"] = override_add_map[session["id"]]
                session["override_reason"] = override_reason_map.get(session["id"], "")

    # Sort: past desc, upcoming asc
    past_sessions.sort(
        key=lambda x: x["datetime"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    upcoming_sessions.sort(
        key=lambda x: x["datetime"] or datetime.max.replace(tzinfo=timezone.utc),
    )

    # Get active overrides for template
    active_overrides = (
        AttendanceOverride.query.filter_by(
            teacher_progress_id=tp.id,
            is_active=True,
        )
        .order_by(AttendanceOverride.created_at.desc())
        .all()
    )

    return render_template(
        "district/teacher_usage/teacher_detail.html",
        teacher_progress=tp,
        past_sessions=past_sessions,
        upcoming_sessions=upcoming_sessions,
        district_name=district_name,
        no_link_message=None,
        active_overrides=active_overrides,
    )


# ── Data Flag API ──────────────────────────────────────────────────────


@teacher_usage_bp.route("/flags/<int:teacher_progress_id>", methods=["POST"])
@login_required
@virtual_admin_required
def create_flag(teacher_progress_id):
    """Create a new data flag for a teacher."""
    tp = TeacherProgress.query.get_or_404(teacher_progress_id)

    data = request.get_json(silent=True) or {}
    flag_type = data.get("flag_type", "")
    details = data.get("details", "").strip()

    if flag_type not in TeacherDataFlagType.all_types():
        return jsonify({"error": "Invalid flag type"}), 400

    flag = TeacherDataFlag(
        teacher_progress_id=tp.id,
        flag_type=flag_type,
        details=details or None,
        created_by=current_user.id,
    )
    db.session.add(flag)
    db.session.commit()

    return jsonify({"message": "Flag created", "flag": flag.to_dict()}), 201


@teacher_usage_bp.route("/flags/<int:teacher_progress_id>", methods=["GET"])
@login_required
@virtual_admin_required
def list_flags(teacher_progress_id):
    """List open flags for a teacher."""
    flags = (
        TeacherDataFlag.query.filter_by(
            teacher_progress_id=teacher_progress_id, is_resolved=False
        )
        .order_by(TeacherDataFlag.created_at.desc())
        .all()
    )
    return jsonify({"flags": [f.to_dict() for f in flags]})


@teacher_usage_bp.route("/flags/<int:flag_id>/resolve", methods=["POST"])
@login_required
@virtual_admin_required
def resolve_flag(flag_id):
    """Resolve a data flag."""
    flag = TeacherDataFlag.query.get_or_404(flag_id)
    data = request.get_json(silent=True) or {}
    flag.resolve(
        notes=data.get("notes", "").strip() or None,
        resolved_by=current_user.id,
    )
    db.session.commit()
    return jsonify({"message": "Flag resolved", "flag": flag.to_dict()})


# ── Attendance Override API (FR-VIRTUAL-234 – FR-VIRTUAL-243) ─────────


@teacher_usage_bp.route("/overrides/<int:teacher_progress_id>", methods=["POST"])
@login_required
@virtual_admin_required
def create_override(teacher_progress_id):
    """Create an attendance override (add or remove a teacher from a session).

    Expects JSON: {action: "add"|"remove", event_id: int, reason: str}
    """
    from datetime import datetime, timezone

    from models.event import Event, EventStatus, EventTeacher, EventType

    tp = TeacherProgress.query.get_or_404(teacher_progress_id)

    # Verify tenant scoping (FR-VIRTUAL-239)
    if not current_user.is_admin and tp.tenant_id != current_user.tenant_id:
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    event_id = data.get("event_id")
    reason = data.get("reason", "").strip()

    # Validate inputs
    if action not in OverrideAction.all_actions():
        return jsonify({"error": "Invalid action. Must be 'add' or 'remove'."}), 400
    if not event_id:
        return jsonify({"error": "event_id is required."}), 400
    if not reason:
        return jsonify({"error": "A reason is required for attendance overrides."}), 400

    # Verify event exists and is a valid virtual session
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found."}), 404
    if event.type != EventType.VIRTUAL_SESSION:
        return jsonify({"error": "Event is not a virtual session."}), 400
    allowed_statuses = [
        EventStatus.COMPLETED,
        EventStatus.CONFIRMED,
        EventStatus.PUBLISHED,
        EventStatus.REQUESTED,
        EventStatus.DRAFT,
    ]
    if event.status not in allowed_statuses:
        return jsonify({"error": "Event status does not allow overrides."}), 400

    # Check for duplicate active override
    existing = AttendanceOverride.query.filter_by(
        teacher_progress_id=tp.id,
        event_id=event_id,
        action=action,
        is_active=True,
    ).first()
    if existing:
        return (
            jsonify(
                {
                    "error": f"An active '{action}' override already exists for this session.",
                    "existing_override": existing.to_dict(),
                }
            ),
            409,
        )

    # Create the override
    override = AttendanceOverride(
        teacher_progress_id=tp.id,
        event_id=event_id,
        action=action,
        reason=reason,
        created_by=current_user.id,
    )
    db.session.add(override)

    # Sync EventTeacher record when teacher has a linked teacher_id
    if tp.teacher_id:
        et = EventTeacher.query.filter_by(
            event_id=event_id, teacher_id=tp.teacher_id
        ).first()
        if action == OverrideAction.ADD:
            # Future events get 'registered' (signup), past events get 'attended'
            event_date = event.start_date
            if event_date and event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            is_future = event_date and event_date >= datetime.now(timezone.utc)
            new_status = "registered" if is_future else "attended"

            if et:
                et.status = new_status
                if not is_future:
                    et.attendance_confirmed_at = datetime.now(timezone.utc)
                et.notes = f"Override add: {reason}"
            else:
                # Create new EventTeacher
                et = EventTeacher(
                    event_id=event_id,
                    teacher_id=tp.teacher_id,
                    status=new_status,
                    attendance_confirmed_at=(
                        datetime.now(timezone.utc) if not is_future else None
                    ),
                    notes=f"Override add: {reason}",
                )
                db.session.add(et)
        elif action == OverrideAction.REMOVE:
            if et:
                et.status = "no_show"
                et.notes = f"Override remove: {reason}"

    # Create audit log entry (FR-VIRTUAL-241)
    audit = AuditLog(
        user_id=current_user.id,
        action=f"attendance_override_{action}",
        resource_type="attendance_override",
        resource_id=str(override.id),
        method="POST",
        path=request.path,
        ip=request.remote_addr,
        meta={
            "teacher_progress_id": tp.id,
            "teacher_name": tp.name,
            "event_id": event.id,
            "event_title": event.title,
            "override_action": action,
            "reason": reason,
        },
    )
    db.session.add(audit)
    db.session.commit()

    return (
        jsonify(
            {
                "message": f"Override created: {override.action_display}",
                "override": override.to_dict(),
            }
        ),
        201,
    )


@teacher_usage_bp.route("/overrides/<int:teacher_progress_id>", methods=["GET"])
@login_required
@virtual_admin_required
def list_overrides(teacher_progress_id):
    """List active overrides for a teacher."""
    overrides = (
        AttendanceOverride.query.filter_by(
            teacher_progress_id=teacher_progress_id,
            is_active=True,
        )
        .order_by(AttendanceOverride.created_at.desc())
        .all()
    )
    return jsonify({"overrides": [o.to_dict() for o in overrides]})


@teacher_usage_bp.route("/overrides/<int:override_id>/reverse", methods=["POST"])
@login_required
@virtual_admin_required
def reverse_override(override_id):
    """Reverse an attendance override (FR-VIRTUAL-243).

    Expects JSON: {reason: str}
    """
    override = AttendanceOverride.query.get_or_404(override_id)

    if not override.is_active:
        return jsonify({"error": "This override has already been reversed."}), 400

    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "").strip()
    if not reason:
        return jsonify({"error": "A reason is required to reverse an override."}), 400

    override.reverse(reason=reason, reversed_by=current_user.id)

    # When reversing an ADD override, clean up the EventTeacher record
    if override.action == OverrideAction.ADD:
        from models.event import EventTeacher

        tp = TeacherProgress.query.get(override.teacher_progress_id)
        if tp and tp.teacher_id:
            et = EventTeacher.query.filter_by(
                event_id=override.event_id, teacher_id=tp.teacher_id
            ).first()
            if et:
                if et.notes and "Override add:" in et.notes:
                    # This EventTeacher was created/modified by the override — delete it
                    db.session.delete(et)
                else:
                    # Pre-existing record (e.g. from Pathful import), revert status
                    et.status = "no_show"
                    et.notes = f"Reversed override: {reason}"

    # Audit log for reversal
    audit = AuditLog(
        user_id=current_user.id,
        action="attendance_override_reverse",
        resource_type="attendance_override",
        resource_id=str(override.id),
        method="POST",
        path=request.path,
        ip=request.remote_addr,
        meta={
            "teacher_progress_id": override.teacher_progress_id,
            "event_id": override.event_id,
            "original_action": override.action,
            "reversal_reason": reason,
        },
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify(
        {
            "message": "Override reversed",
            "override": override.to_dict(),
        }
    )


@teacher_usage_bp.route("/sessions/search", methods=["GET"])
@login_required
@virtual_admin_required
def search_sessions():
    """Search virtual sessions for the add-to-session modal.

    Scoped to the current semester. Shows all sessions by default;
    optionally filtered by title/series search query.
    Query params: q (search term), limit (default 50), upcoming_only (if truthy, only future sessions)
    """
    from models.event import Event, EventStatus, EventType

    query_str = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 50)), 100)
    upcoming_only = request.args.get("upcoming_only", "")

    # Get tenant's district
    tenant = Tenant.query.get(current_user.tenant_id)
    linked_district = None
    if tenant:
        if tenant.district:
            linked_district = tenant.district.name
        else:
            linked_district = tenant.get_setting("linked_district_name")

    # Scope to current semester
    academic_year = get_current_academic_year()
    semester = get_current_semester()
    date_from, date_to = get_semester_dates(academic_year, semester)

    # Base query: virtual sessions in this district for current semester
    sessions_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status.in_(
            [
                EventStatus.COMPLETED,
                EventStatus.CONFIRMED,
                EventStatus.PUBLISHED,
                EventStatus.REQUESTED,
                EventStatus.DRAFT,
            ]
        ),
    )
    if linked_district:
        sessions_query = sessions_query.filter(
            Event.district_partner == linked_district
        )
    if date_from:
        sessions_query = sessions_query.filter(Event.start_date >= date_from)
    if date_to:
        sessions_query = sessions_query.filter(Event.start_date <= date_to)

    # Apply optional search filter
    if query_str:
        search_pattern = f"%{query_str}%"
        sessions_query = sessions_query.filter(
            db.or_(
                Event.title.ilike(search_pattern),
                Event.series.ilike(search_pattern),
            )
        )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    all_sessions = sessions_query.all()

    # Filter to upcoming-only if requested (for sign-up modal)
    if upcoming_only:
        filtered = []
        for ev in all_sessions:
            sd = ev.start_date
            if sd:
                if sd.tzinfo is None:
                    sd = sd.replace(tzinfo=timezone.utc)
                if sd >= now:
                    filtered.append(ev)
        all_sessions = filtered

    # Sort by proximity to current date (closest first)
    def proximity_key(event):
        if event.start_date:
            sd = event.start_date
            if sd.tzinfo is None:
                sd = sd.replace(tzinfo=timezone.utc)
            return abs((sd - now).total_seconds())
        return float("inf")

    all_sessions.sort(key=proximity_key)
    sessions = all_sessions[:limit]

    results = []
    for event in sessions:
        start_date = event.start_date
        results.append(
            {
                "id": event.id,
                "title": event.title or "Untitled Session",
                "date": start_date.strftime("%Y-%m-%d") if start_date else None,
                "date_display": (
                    start_date.strftime("%B %d, %Y") if start_date else "Unknown"
                ),
                "series": event.series or "",
                "status": event.status.value if event.status else "Unknown",
            }
        )

    return jsonify({"sessions": results})


# ── No Shows Report ───────────────────────────────────────────────────


@teacher_usage_bp.route("/no-shows")
@login_required
@virtual_admin_required
def no_shows():
    """View all teacher no-shows for a semester, grouped by school then teacher.

    Respects the same year/semester/tenant_id filters as the main dashboard.
    """
    from collections import defaultdict

    from models.event import Event, EventStatus, EventTeacher, EventType
    from services.district_service import get_district_name_variants

    academic_year = request.args.get("year", get_current_academic_year())
    semester = request.args.get("semester", get_current_semester())

    # Admin users can specify a tenant via query param
    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        tenant_id = admin_tenant_id
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            flash("Tenant not found.", "error")
            return redirect(url_for("virtual.virtual_sessions"))
        district_name = tenant.district.name if tenant.district else tenant.name
    else:
        tenant_id = current_user.tenant_id
        district_name = get_tenant_district_name()

    if not tenant_id:
        flash("Please select a tenant to view no-shows.", "warning")
        return redirect(url_for("virtual.virtual_sessions"))

    # Get tenant's district name variants for filtering
    tenant = Tenant.query.get(tenant_id)
    district_names = set()
    if tenant:
        if tenant.district:
            district_names = get_district_name_variants(tenant.district)
        else:
            linked = tenant.get_setting("linked_district_name")
            if linked:
                district_names = {linked}

    # Calculate semester date range
    date_from, date_to = get_semester_dates(academic_year, semester)

    # Query EventTeacher records with no_show status, joined to Event
    no_show_query = (
        db.session.query(EventTeacher, Event)
        .join(Event, EventTeacher.event_id == Event.id)
        .filter(
            EventTeacher.status == "no_show",
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
        )
    )
    if district_names:
        no_show_query = no_show_query.filter(Event.district_partner.in_(district_names))
    if date_from:
        no_show_query = no_show_query.filter(Event.start_date >= date_from)
    if date_to:
        no_show_query = no_show_query.filter(Event.start_date <= date_to)

    no_show_records = no_show_query.order_by(Event.start_date.desc()).all()

    # Get all active TeacherProgress for this tenant/year for building lookup
    tp_entries = TeacherProgress.query.filter_by(
        tenant_id=tenant_id, academic_year=academic_year, is_active=True
    ).all()
    teacher_id_to_building = {}
    teacher_id_to_tp_name = {}
    teacher_id_to_tp_id = {}
    for tp in tp_entries:
        if tp.teacher_id:
            teacher_id_to_building[tp.teacher_id] = tp.building or "Unknown"
            teacher_id_to_tp_name[tp.teacher_id] = tp.name
            teacher_id_to_tp_id[tp.teacher_id] = tp.id

    # Check for active "add" overrides so we can mark already-overridden sessions
    active_add_overrides = set()
    if teacher_id_to_tp_id:
        tp_ids = list(teacher_id_to_tp_id.values())
        existing_overrides = AttendanceOverride.query.filter(
            AttendanceOverride.teacher_progress_id.in_(tp_ids),
            AttendanceOverride.action == OverrideAction.ADD,
            AttendanceOverride.is_active == True,
        ).all()
        for ov in existing_overrides:
            active_add_overrides.add((ov.teacher_progress_id, ov.event_id))

    # Group by school -> teacher -> sessions
    # Structure: {school: {teacher_name: [session_dicts]}}
    school_data = defaultdict(lambda: defaultdict(list))
    total_no_shows = 0

    for et, event in no_show_records:
        # Only include teachers that belong to this tenant
        if et.teacher_id not in teacher_id_to_building:
            continue

        building = teacher_id_to_building[et.teacher_id]
        teacher_name = teacher_id_to_tp_name.get(et.teacher_id, "Unknown Teacher")

        start_date = event.start_date
        tp_id = teacher_id_to_tp_id.get(et.teacher_id)
        is_overridden = (tp_id, event.id) in active_add_overrides
        school_data[building][teacher_name].append(
            {
                "event_id": event.id,
                "title": event.title or "Untitled Session",
                "date": start_date.strftime("%B %d, %Y") if start_date else "Unknown",
                "date_sort": start_date.isoformat() if start_date else "",
                "series": event.series or "",
                "teacher_progress_id": tp_id,
                "is_overridden": is_overridden,
            }
        )
        total_no_shows += 1

    # Sort schools alphabetically
    sorted_school_data = dict(sorted(school_data.items()))
    # Sort teachers within each school
    for school in sorted_school_data:
        sorted_school_data[school] = dict(sorted(sorted_school_data[school].items()))

    total_teachers = sum(len(teachers) for teachers in sorted_school_data.values())

    return render_template(
        "district/teacher_usage/no_shows.html",
        school_data=sorted_school_data,
        total_no_shows=total_no_shows,
        total_schools=len(sorted_school_data),
        total_teachers=total_teachers,
        district_name=district_name or "Your District",
        academic_year=academic_year,
        semester=semester,
        admin_tenant_id=admin_tenant_id,
    )


@teacher_usage_bp.route("/no-shows/export")
@login_required
@virtual_admin_required
def no_shows_export_csv():
    """Export no-shows data as CSV.

    Same filters as the no-shows viewer.
    """
    import csv
    import io
    from collections import defaultdict

    from flask import Response

    from models.event import Event, EventStatus, EventTeacher, EventType
    from services.district_service import get_district_name_variants

    academic_year = request.args.get("year", get_current_academic_year())
    semester = request.args.get("semester", get_current_semester())

    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        tenant_id = admin_tenant_id
        tenant = Tenant.query.get(tenant_id)
        district_name = (
            tenant.district.name
            if tenant and tenant.district
            else tenant.name if tenant else "District"
        )
    else:
        tenant_id = current_user.tenant_id
        district_name = get_tenant_district_name() or "District"

    if not tenant_id:
        flash("No tenant assigned.", "error")
        return redirect(url_for("virtual.virtual_sessions"))

    # Get tenant's district name variants
    tenant = Tenant.query.get(tenant_id)
    district_names = set()
    if tenant:
        if tenant.district:
            district_names = get_district_name_variants(tenant.district)
        else:
            linked = tenant.get_setting("linked_district_name")
            if linked:
                district_names = {linked}

    date_from, date_to = get_semester_dates(academic_year, semester)

    # Query no-show records
    no_show_query = (
        db.session.query(EventTeacher, Event)
        .join(Event, EventTeacher.event_id == Event.id)
        .filter(
            EventTeacher.status == "no_show",
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
        )
    )
    if district_names:
        no_show_query = no_show_query.filter(Event.district_partner.in_(district_names))
    if date_from:
        no_show_query = no_show_query.filter(Event.start_date >= date_from)
    if date_to:
        no_show_query = no_show_query.filter(Event.start_date <= date_to)

    no_show_records = no_show_query.order_by(Event.start_date.desc()).all()

    # Build building/name lookups from TeacherProgress
    tp_entries = TeacherProgress.query.filter_by(
        tenant_id=tenant_id, academic_year=academic_year, is_active=True
    ).all()
    teacher_id_to_building = {}
    teacher_id_to_tp_name = {}
    for tp in tp_entries:
        if tp.teacher_id:
            teacher_id_to_building[tp.teacher_id] = tp.building or "Unknown"
            teacher_id_to_tp_name[tp.teacher_id] = tp.name

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["School", "Teacher", "Session Date", "Session Title", "Series"])

    for et, event in no_show_records:
        if et.teacher_id not in teacher_id_to_building:
            continue

        building = teacher_id_to_building[et.teacher_id]
        teacher_name = teacher_id_to_tp_name.get(et.teacher_id, "Unknown")
        start_date = event.start_date

        writer.writerow(
            [
                building,
                teacher_name,
                start_date.strftime("%Y-%m-%d") if start_date else "",
                event.title or "Untitled Session",
                event.series or "",
            ]
        )

    csv_content = output.getvalue()
    output.close()

    import re

    safe_name = re.sub(r"[^\w]+", "_", district_name).strip("_")
    filename = f"{safe_name}_No_Shows_{academic_year}_{semester}.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Audit Log Viewer (Admin-only) ─────────────────────────────────────


@teacher_usage_bp.route("/audit")
@login_required
@virtual_admin_required
def audit_log():
    """View audit log entries related to teacher usage changes.

    Scoped to attendance_override resource_type. Admin-only.
    Query params: start_date, end_date, action, per_page, page.
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("teacher_usage.index"))

    from models.user import User

    admin_tenant_id = request.args.get("tenant_id", type=int)

    # Build query scoped to teacher-usage audit entries
    q = AuditLog.query.filter(
        AuditLog.resource_type == "attendance_override",
    ).order_by(AuditLog.created_at.desc())

    # Filters
    action_filter = request.args.get("action", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    if action_filter:
        q = q.filter(AuditLog.action == action_filter)
    if start_date:
        try:
            from datetime import datetime

            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        except Exception:
            pass
    if end_date:
        try:
            from datetime import datetime

            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        except Exception:
            pass

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # Pre-load user names for display
    user_ids = {log.user_id for log in logs if log.user_id}
    users_map = {}
    if user_ids:
        users = User.query.filter(User.id.in_(user_ids)).all()
        users_map = {
            u.id: f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username
            for u in users
        }

    # Get distinct actions for the filter dropdown
    action_choices = (
        db.session.query(AuditLog.action)
        .filter(AuditLog.resource_type == "attendance_override")
        .distinct()
        .all()
    )
    action_choices = sorted([a[0] for a in action_choices])

    return render_template(
        "district/teacher_usage/audit_log.html",
        logs=logs,
        pagination=pagination,
        users_map=users_map,
        action_choices=action_choices,
        admin_tenant_id=admin_tenant_id,
        filters={
            "action": action_filter,
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "per_page": per_page,
        },
    )


@teacher_usage_bp.route("/audit/export")
@login_required
@virtual_admin_required
def audit_export_csv():
    """Export teacher usage audit log entries as CSV.

    Same filters as the audit viewer. Admin-only.
    """
    import csv
    import io

    from flask import Response

    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    from models.user import User

    # Build query (same as audit_log route)
    q = AuditLog.query.filter(
        AuditLog.resource_type == "attendance_override",
    ).order_by(AuditLog.created_at.desc())

    action_filter = request.args.get("action", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    if action_filter:
        q = q.filter(AuditLog.action == action_filter)
    if start_date:
        try:
            from datetime import datetime

            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        except Exception:
            pass
    if end_date:
        try:
            from datetime import datetime

            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        except Exception:
            pass

    logs = q.all()

    # Pre-load user names
    user_ids = {log.user_id for log in logs if log.user_id}
    users_map = {}
    if user_ids:
        users = User.query.filter(User.id.in_(user_ids)).all()
        users_map = {
            u.id: f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username
            for u in users
        }

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Timestamp (UTC)",
            "User",
            "Action",
            "Teacher",
            "Event/Session",
            "Reason",
            "IP Address",
            "Resource ID",
        ]
    )

    for log in logs:
        meta = log.meta or {}
        writer.writerow(
            [
                log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
                users_map.get(
                    log.user_id, f"User #{log.user_id}" if log.user_id else "System"
                ),
                log.action or "",
                meta.get("teacher_name", ""),
                meta.get("event_title", ""),
                meta.get("reason", meta.get("reversal_reason", "")),
                log.ip or "",
                log.resource_id or "",
            ]
        )

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=teacher_usage_audit_log.csv"
        },
    )


# ── Presenter No-Show / Session Credit ───────────────────────────────


@teacher_usage_bp.route("/session-credit")
@login_required
@virtual_admin_required
def session_credit():
    """Admin page to grant attendance credit for a session where the presenter no-showed.

    Accepts query params:
      - event_id (int): internal Event primary key, OR
      - pathful_id (str): Pathful session ID (e.g. from URL https://app.pathful.com/wbl/sessions/109933)
      - tenant_id (int): admin-only tenant override
    """
    from models.event import Event, EventTeacher, EventType

    # Tenant scoping
    admin_tenant_id = request.args.get("tenant_id", type=int)
    if current_user.is_admin and admin_tenant_id:
        effective_tenant_id = admin_tenant_id
    else:
        effective_tenant_id = current_user.tenant_id

    district_name = get_tenant_district_name(effective_tenant_id) or "Your District"

    event = None
    teachers = []
    error = None

    # Look up event by internal ID or Pathful session ID
    event_id = request.args.get("event_id", type=int)
    pathful_url_or_id = request.args.get("pathful_id", "").strip()

    if event_id:
        event = Event.query.get(event_id)
        if not event:
            error = f"No event found with internal ID {event_id}."
    elif pathful_url_or_id:
        # Strip full URL down to just the numeric ID at the end
        import re

        match = re.search(r"(\d+)\s*$", pathful_url_or_id)
        if match:
            pathful_id_str = match.group(1)
            event = Event.query.filter_by(pathful_session_id=pathful_id_str).first()
            if not event:
                error = f"No session found matching Pathful ID '{pathful_id_str}'. It may not have been imported yet."
        else:
            error = "Could not parse a Pathful session ID from the value entered."

    if event and event.type != EventType.VIRTUAL_SESSION:
        error = "That event is not a virtual session and cannot be credited here."
        event = None

    if event:
        # Load all teachers registered for this session
        et_records = EventTeacher.query.filter_by(event_id=event.id).all()

        # Build TeacherProgress lookup for this tenant
        tp_map = {}  # teacher_id -> TeacherProgress
        if et_records:
            teacher_ids = [et.teacher_id for et in et_records if et.teacher_id]
            tp_entries = TeacherProgress.query.filter(
                TeacherProgress.teacher_id.in_(teacher_ids),
                TeacherProgress.tenant_id == effective_tenant_id,
                TeacherProgress.is_active == True,
            ).all()
            tp_map = {tp.teacher_id: tp for tp in tp_entries}

        # Check which TPs already have an active override for this event
        tp_ids_with_override = set()
        if tp_map:
            existing_overrides = AttendanceOverride.query.filter(
                AttendanceOverride.teacher_progress_id.in_(
                    [tp.id for tp in tp_map.values()]
                ),
                AttendanceOverride.event_id == event.id,
                AttendanceOverride.action == OverrideAction.ADD,
                AttendanceOverride.is_active == True,
            ).all()
            tp_ids_with_override = {ov.teacher_progress_id for ov in existing_overrides}

        for et in et_records:
            if not et.teacher_id:
                continue
            tp = tp_map.get(et.teacher_id)
            teachers.append(
                {
                    "teacher_id": et.teacher_id,
                    "name": tp.name if tp else f"Teacher #{et.teacher_id}",
                    "building": tp.building if tp else "Unknown",
                    "status": et.status or "unknown",
                    "teacher_progress_id": tp.id if tp else None,
                    "already_credited": tp.id in tp_ids_with_override if tp else False,
                }
            )

        # Sort by school then name
        teachers.sort(key=lambda t: (t["building"], t["name"]))

    return render_template(
        "district/teacher_usage/session_credit.html",
        event=event,
        teachers=teachers,
        error=error,
        district_name=district_name,
        admin_tenant_id=admin_tenant_id,
        queried_pathful=pathful_url_or_id,
        queried_event_id=event_id,
    )


@teacher_usage_bp.route("/session-credit/bulk", methods=["POST"])
@login_required
@virtual_admin_required
def bulk_session_credit():
    """Grant attendance credit to multiple teachers for a single session.

    Expects JSON:
      {
        "event_id": 123,
        "teacher_progress_ids": [45, 67, 89],
        "reason": "Presenter no-show — credit granted by admin"
      }

    Returns a summary of successes and skips (already-overridden teachers).
    """
    from datetime import datetime, timezone

    from models.event import Event, EventStatus, EventTeacher, EventType

    data = request.get_json(silent=True) or {}
    event_id = data.get("event_id")
    tp_ids = data.get("teacher_progress_ids", [])
    reason = data.get("reason", "").strip()

    if not event_id:
        return jsonify({"error": "event_id is required."}), 400
    if not tp_ids or not isinstance(tp_ids, list):
        return jsonify({"error": "teacher_progress_ids must be a non-empty list."}), 400
    if not reason:
        return jsonify({"error": "A reason is required."}), 400

    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found."}), 404
    if event.type != EventType.VIRTUAL_SESSION:
        return jsonify({"error": "Event is not a virtual session."}), 400

    allowed_statuses = [
        EventStatus.COMPLETED,
        EventStatus.CONFIRMED,
        EventStatus.PUBLISHED,
        EventStatus.REQUESTED,
        EventStatus.DRAFT,
    ]
    if event.status not in allowed_statuses:
        return jsonify({"error": "Event status does not allow overrides."}), 400

    now = datetime.now(timezone.utc)
    event_date = event.start_date
    if event_date and event_date.tzinfo is None:
        event_date = event_date.replace(tzinfo=timezone.utc)
    is_future = event_date and event_date >= now

    granted = []
    skipped = []
    errors = []

    for tp_id in tp_ids:
        tp = TeacherProgress.query.get(tp_id)
        if not tp:
            errors.append(
                {"teacher_progress_id": tp_id, "reason": "TeacherProgress not found."}
            )
            continue

        # Tenant scoping
        if not current_user.is_admin and tp.tenant_id != current_user.tenant_id:
            errors.append({"teacher_progress_id": tp_id, "reason": "Access denied."})
            continue

        # Skip if already overridden
        existing = AttendanceOverride.query.filter_by(
            teacher_progress_id=tp.id,
            event_id=event_id,
            action=OverrideAction.ADD,
            is_active=True,
        ).first()
        if existing:
            skipped.append({"teacher_progress_id": tp_id, "name": tp.name})
            continue

        # Create override
        override = AttendanceOverride(
            teacher_progress_id=tp.id,
            event_id=event_id,
            action=OverrideAction.ADD,
            reason=reason,
            created_by=current_user.id,
        )
        db.session.add(override)

        # Sync EventTeacher
        if tp.teacher_id:
            et = EventTeacher.query.filter_by(
                event_id=event_id, teacher_id=tp.teacher_id
            ).first()
            new_status = "registered" if is_future else "attended"
            if et:
                et.status = new_status
                if not is_future:
                    et.attendance_confirmed_at = now
                et.notes = f"Override add: {reason}"
            else:
                et = EventTeacher(
                    event_id=event_id,
                    teacher_id=tp.teacher_id,
                    status=new_status,
                    attendance_confirmed_at=(now if not is_future else None),
                    notes=f"Override add: {reason}",
                )
                db.session.add(et)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="attendance_override_add",
            resource_type="attendance_override",
            resource_id="bulk",
            method="POST",
            path=request.path,
            ip=request.remote_addr,
            meta={
                "teacher_progress_id": tp.id,
                "teacher_name": tp.name,
                "event_id": event.id,
                "event_title": event.title,
                "override_action": "add",
                "reason": reason,
                "bulk": True,
            },
        )
        db.session.add(audit)
        granted.append({"teacher_progress_id": tp_id, "name": tp.name})

    db.session.commit()

    return (
        jsonify(
            {
                "granted": granted,
                "skipped": skipped,
                "errors": errors,
                "summary": f"Credit granted to {len(granted)} teacher(s). {len(skipped)} already credited. {len(errors)} error(s).",
            }
        ),
        201,
    )
