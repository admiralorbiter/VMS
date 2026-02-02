"""
Tenant Teacher Usage Routes
============================

Routes for Virtual Admin to view teacher progress/usage dashboard.
Shows which teachers have completed their virtual session goals.
"""

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from models import db
from models.teacher_progress import TeacherProgress
from models.tenant import Tenant
from models.user import TenantRole

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


def get_current_academic_year():
    """Get current academic year based on date."""
    today = datetime.now()
    if today.month >= 8:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


def get_current_semester():
    """Get current semester based on date (fall: Aug-Dec, spring: Jan-Jul)."""
    today = datetime.now()
    if today.month >= 8:
        return "fall"
    return "spring"


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

    if not district_name:
        # Can't match without district - return empty progress
        pass

    # Build teacher name aliases for matching
    # Keys are lowercase normalized names, values are teacher IDs
    teacher_progress_map = {}  # teacher_id -> completed_count
    teacher_alias_map = {}  # normalized_name -> teacher_id

    for teacher in teachers:
        teacher_progress_map[teacher.id] = 0

        # Create name variations for matching
        base_name = teacher.name.lower().strip()
        normalized_name = base_name.replace("-", " ").replace(".", "").replace(",", "")

        name_variations = [
            base_name,
            normalized_name,
            base_name.replace(".", "").replace(",", "").strip(),
        ]

        # Add first + last name variation if different from stored name
        parts = teacher.name.split()
        if len(parts) > 1:
            first_last = f"{parts[0]} {parts[-1]}".lower()
            name_variations.append(first_last)
            name_variations.append(first_last.replace("-", " "))

        # Store aliases pointing to teacher id
        for name_var in name_variations:
            if name_var:
                teacher_alias_map.setdefault(name_var, teacher.id)

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

    # Match sessions to teachers using Event.educators field
    for event in events:
        if not event.educators:
            continue

        # Parse semicolon-separated educator names
        educator_names = [
            name.strip() for name in event.educators.split(";") if name.strip()
        ]

        for educator_name in educator_names:
            educator_key = educator_name.lower().strip()
            educator_key_normalized = (
                educator_key.replace("-", " ").replace(".", "").replace(",", "")
            )

            # Try exact match first
            teacher_id = teacher_alias_map.get(educator_key) or teacher_alias_map.get(
                educator_key_normalized
            )

            if not teacher_id:
                # Try flexible matching - look for partial matches
                for name_key, alias_teacher_id in teacher_alias_map.items():
                    name_key_normalized = name_key.replace("-", " ")
                    # Check if either version matches (partial match)
                    if (
                        educator_key in name_key
                        or name_key in educator_key
                        or educator_key_normalized in name_key_normalized
                        or name_key_normalized in educator_key_normalized
                    ) and len(educator_key) > 3:
                        teacher_id = alias_teacher_id
                        break

            if teacher_id and teacher_id in teacher_progress_map:
                teacher_progress_map[teacher_id] += 1

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
        target = teacher.target_sessions or 1

        # Determine status
        if completed >= target:
            status_class = "achieved"
            status_text = "Goal Achieved"
            bd["goals_achieved"] += 1
        elif completed > 0:
            status_class = "in_progress"
            status_text = "In Progress"
            bd["goals_in_progress"] += 1
        else:
            status_class = "not_started"
            status_text = "Not Started"
            bd["goals_not_started"] += 1

        # Calculate progress percentage
        progress_pct = min(100, (completed / target * 100)) if target > 0 else 0

        bd["teachers"].append(
            {
                "id": teacher.id,
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

    # Calculate semester date range
    # Academic year format: "2025-2026"
    try:
        start_year = int(academic_year.split("-")[0])
    except (ValueError, IndexError):
        start_year = datetime.now().year

    if semester == "fall":
        date_from = datetime(start_year, 8, 1)
        date_to = datetime(start_year, 12, 31, 23, 59, 59)
    else:  # spring
        date_from = datetime(start_year + 1, 1, 1)
        date_to = datetime(start_year + 1, 7, 31, 23, 59, 59)

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

    # Calculate semester date range
    try:
        start_year = int(academic_year.split("-")[0])
    except (ValueError, IndexError):
        start_year = datetime.now().year

    if semester == "fall":
        date_from = datetime(start_year, 8, 1)
        date_to = datetime(start_year, 12, 31, 23, 59, 59)
    else:  # spring
        date_from = datetime(start_year + 1, 1, 1)
        date_to = datetime(start_year + 1, 7, 31, 23, 59, 59)

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
