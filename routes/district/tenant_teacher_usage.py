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

        # Must be Virtual Admin or Tenant Admin
        allowed_roles = [
            TenantRole.VIRTUAL_ADMIN,
            TenantRole.ADMIN,
            TenantRole.COORDINATOR,
        ]
        if current_user.tenant_role not in allowed_roles:
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for("district.virtual_sessions"))

        return f(*args, **kwargs)

    return decorated_function


# Note: get_current_academic_year and get_current_semester are imported from
# services.academic_year_service


def get_tenant_district_name():
    """Get district name for current user's tenant."""
    if not current_user.tenant_id:
        return None
    tenant = Tenant.query.get(current_user.tenant_id)
    return tenant.name if tenant else None


def compute_teacher_progress(tenant_id, academic_year, date_from=None, date_to=None):
    """
    Compute teacher progress data for a tenant.

    Matches imported teachers against completed virtual sessions using
    the Event.educators field (semicolon-separated teacher names).

    Returns dict of building -> {teachers: [], stats}
    """
    from models import Event
    from models.event import EventStatus, EventType
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

    # Get the tenant's linked district name for filtering sessions
    tenant = Tenant.query.get(tenant_id)
    district_name = None
    if tenant:
        if tenant.district:
            district_name = tenant.district.name
        else:
            district_name = tenant.get_setting("linked_district_name")

    # Build teacher name aliases using shared service
    teacher_progress_map, teacher_alias_map = build_teacher_alias_map(teachers)

    # Query completed virtual sessions for this district
    events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION, Event.status == EventStatus.COMPLETED
    )

    if district_name:
        events_query = events_query.filter(Event.district_partner == district_name)

    # Apply date filters if provided
    if date_from:
        events_query = events_query.filter(Event.start_date >= date_from)
    if date_to:
        events_query = events_query.filter(Event.start_date <= date_to)

    events = events_query.all()

    # Match sessions to teachers using shared service
    teacher_progress_map = count_sessions_for_teachers(
        events, teacher_alias_map, teacher_progress_map
    )

    # ── Apply attendance overrides (FR-VIRTUAL-234, FR-VIRTUAL-238) ────
    active_overrides = AttendanceOverride.query.filter(
        AttendanceOverride.teacher_progress_id.in_([t.id for t in teachers]),
        AttendanceOverride.is_active == True,  # noqa: E712
    ).all()
    for ov in active_overrides:
        tid = ov.teacher_progress_id
        if tid in teacher_progress_map:
            if ov.action == OverrideAction.ADD:
                teacher_progress_map[tid] += 1
            elif ov.action == OverrideAction.REMOVE:
                teacher_progress_map[tid] = max(0, teacher_progress_map[tid] - 1)

    # Also count planned/upcoming sessions (confirmed, published, requested)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    planned_events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status.in_(
            [EventStatus.CONFIRMED, EventStatus.PUBLISHED, EventStatus.REQUESTED]
        ),
        Event.start_date >= now,
    )
    if district_name:
        planned_events_query = planned_events_query.filter(
            Event.district_partner == district_name
        )
    planned_events = planned_events_query.all()

    # Build a separate map for planned session counts
    planned_progress_map = {t.id: 0 for t in teachers}
    planned_progress_map = count_sessions_for_teachers(
        planned_events, teacher_alias_map, planned_progress_map
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
        target = teacher.target_sessions or 1

        # Determine status (consider both completed and planned sessions)
        if completed >= target:
            status_class = "achieved"
            status_text = "Goal Achieved"
            bd["goals_achieved"] += 1
        elif completed > 0 or planned > 0:
            status_class = "in_progress"
            status_text = "In Progress"
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
    tenant_id = current_user.tenant_id
    district_name = get_tenant_district_name()

    # For global admins without tenant, show message
    if not tenant_id:
        flash("Please select a tenant to view teacher usage.", "warning")
        return redirect(url_for("main.index"))

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
    tenant_id = current_user.tenant_id
    district_name = get_tenant_district_name() or "District"

    if not tenant_id:
        flash("No tenant assigned.", "error")
        return redirect(url_for("main.index"))

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

    Uses the same name-based matching against Event.educators that the
    usage dashboard relies on, so results are consistent regardless of
    whether the TeacherProgress record has a linked teacher_id.
    """
    from datetime import datetime, timezone

    from models.event import Event, EventStatus, EventType
    from services.teacher_matching_service import (
        build_teacher_alias_map,
        match_educator_to_teacher,
    )

    tp = TeacherProgress.query.get_or_404(teacher_progress_id)
    district_name = get_tenant_district_name() or "Your District"

    # Resolve the tenant's linked district name (same as compute_teacher_progress)
    tenant = Tenant.query.get(current_user.tenant_id)
    linked_district = None
    if tenant:
        if tenant.district:
            linked_district = tenant.district.name
        else:
            linked_district = tenant.get_setting("linked_district_name")

    # Build alias map for just this one teacher
    _, alias_map = build_teacher_alias_map([tp])

    # Query ALL virtual sessions for this district (completed + future)
    events_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
    )
    if linked_district:
        events_query = events_query.filter(Event.district_partner == linked_district)
    events = events_query.order_by(Event.start_date.desc()).all()

    now = datetime.now(timezone.utc)
    past_sessions = []
    upcoming_sessions = []

    for event in events:
        if not event.educators:
            continue

        # Check if this teacher is listed in the educators field
        educator_names = [n.strip() for n in event.educators.split(";") if n.strip()]
        matched = any(
            match_educator_to_teacher(name, alias_map) == tp.id
            for name in educator_names
        )
        if not matched:
            continue

        # Get presenter info from volunteers
        presenter_name = ""
        presenter_org = ""
        if event.volunteers:
            vol = event.volunteers[0]
            presenter_name = f"{vol.first_name} {vol.last_name}".strip()
            presenter_org = vol.organization_name or ""

        start_date = event.start_date
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

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
            "attendance_status": "",
        }

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

    # Add sessions credited via override that aren't already in the list
    existing_event_ids = {s["id"] for s in past_sessions}
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

                past_sessions.append(
                    {
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
                        "attendance_status": "",
                        "is_override": True,
                        "override_reason": ov.reason,
                    }
                )

    # Tag override sessions in existing list
    override_add_event_ids = {ov.event_id for ov in add_overrides}
    for session in past_sessions:
        if "is_override" not in session:
            session["is_override"] = session["id"] in override_add_event_ids

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
    from models.event import Event, EventStatus, EventType

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

    # Verify event exists and is a completed virtual session
    event = Event.query.get(event_id)
    if not event:
        return jsonify({"error": "Event not found."}), 404
    if event.type != EventType.VIRTUAL_SESSION:
        return jsonify({"error": "Event is not a virtual session."}), 400
    if event.status != EventStatus.COMPLETED:
        return jsonify({"error": "Event is not completed."}), 400

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
    """Search completed virtual sessions for the add-to-session modal.

    Query params: q (search term), limit (default 20)
    """
    from models.event import Event, EventStatus, EventType

    query_str = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 50)

    # Get tenant's district
    tenant = Tenant.query.get(current_user.tenant_id)
    linked_district = None
    if tenant:
        if tenant.district:
            linked_district = tenant.district.name
        else:
            linked_district = tenant.get_setting("linked_district_name")

    # Base query: completed virtual sessions in this district
    sessions_query = Event.query.filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.status == EventStatus.COMPLETED,
    )
    if linked_district:
        sessions_query = sessions_query.filter(
            Event.district_partner == linked_district
        )

    # Apply search filter if provided
    if query_str:
        search_pattern = f"%{query_str}%"
        sessions_query = sessions_query.filter(
            db.or_(
                Event.title.ilike(search_pattern),
                Event.series.ilike(search_pattern),
            )
        )

    sessions = sessions_query.order_by(Event.start_date.desc()).limit(limit).all()

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
            }
        )

    return jsonify({"sessions": results})
