"""
Management Routes — Core admin panel, logs, cache refresh, and user management.

This module defines the management_bp blueprint and contains the core
administrative route handlers. Domain-specific routes are registered
from sibling modules via register_*_routes() functions.
"""

import json
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from models import db
from models.district_model import District
from models.event import EventType
from models.google_sheet import GoogleSheet
from models.reports import (
    DistrictYearEndReport,
    FirstTimeVolunteerReportCache,
    OrganizationDetailCache,
    OrganizationSummaryCache,
    RecentVolunteersReportCache,
    RecruitmentCandidatesCache,
)
from models.sync_log import SyncLog
from models.user import SecurityLevel, User
from routes.decorators import (
    admin_required,
    handle_route_errors,
    security_level_required,
)

# Import sub-module registration functions
from routes.management.bug_reports import register_bug_report_routes
from routes.management.data_integrity import register_data_integrity_routes
from routes.management.google_sheets import register_google_sheets_routes
from routes.management.import_data import register_import_data_routes
from routes.reports.common import get_school_year_date_range
from routes.reports.recent_volunteers import (
    _derive_filtered_from_base,
    _query_active_volunteers_all,
    _query_first_time_in_range,
    _serialize_for_cache,
)
from routes.reports.virtual_session import invalidate_virtual_session_caches
from services.user_service import update_user_fields

management_bp = Blueprint("management", __name__)

# Register domain-specific routes
register_data_integrity_routes(management_bp)
register_google_sheets_routes(management_bp)
register_import_data_routes(management_bp)
register_bug_report_routes(management_bp)


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------


@management_bp.route("/admin")
@login_required
def admin():
    """
    Display the main admin panel.

    Provides administrative interface for password changes (all users) and
    user management (admin only). All logged-in users can access this page
    to change their password, but only admins can see user management features.

    Permission Requirements:
        - Login required (any security level)
        - User management features restricted to ADMIN (3) level

    Returns:
        Rendered admin template with password change form and optionally user list

    Raises:
        Redirect to login if not authenticated
    """
    # Allow all logged-in users to access admin panel for password changes
    # But restrict user management features to admins only (handled in template)

    # Filter data based on user scope
    if current_user.scope_type == "district":
        # District-scoped users only see themselves
        users = [current_user]
        # Only show their allowed districts
        if current_user.allowed_districts:
            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )
                districts = (
                    District.query.filter(District.name.in_(allowed_districts))
                    .order_by(District.name)
                    .all()
                )
            except (json.JSONDecodeError, TypeError):
                districts = []
        else:
            districts = []
    else:
        # Global users see all data
        users = User.query.all()
        # Load districts for district scoping
        districts = District.query.order_by(District.name).all()

    # Provide academic years with Google Sheets for the dropdown (virtual sessions only)
    sheet_years = [
        sheet.academic_year
        for sheet in GoogleSheet.query.filter_by(purpose="virtual_sessions")
        .order_by(GoogleSheet.academic_year.desc())
        .all()
    ]

    # Get latest sync logs for status indicators (TC-220)
    latest_sync = SyncLog.get_latest_by_type("events_and_participants")
    latest_student_sync = SyncLog.get_latest_by_type("student_participants")
    latest_overall_sync = SyncLog.get_recent_logs(limit=1)
    latest_overall_sync = latest_overall_sync[0] if latest_overall_sync else None

    return render_template(
        "management/admin.html",
        users=users,
        districts=districts,
        sheet_years=sheet_years,
        latest_sync=latest_sync,
        latest_student_sync=latest_student_sync,
        latest_overall_sync=latest_overall_sync,
    )


# ---------------------------------------------------------------------------
# Logs & audit
# ---------------------------------------------------------------------------


@management_bp.route("/admin/sync-logs")
@login_required
@admin_required
def view_sync_logs():
    """
    Display historical sync logs.

    Permission Requirements:
        - Admin access required
    """
    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = SyncLog.query.order_by(SyncLog.started_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    logs = pagination.items

    # Pre-parse error_message JSON for template rendering
    for log in logs:
        if log.error_message:
            try:
                log.error_details = json.loads(log.error_message)
            except Exception:
                # Fallback: wrap raw string as a single-item list
                log.error_details = [
                    {"record_id": "", "record_name": "", "message": log.error_message}
                ]
        else:
            log.error_details = None

    return render_template(
        "management/sync_logs.html",
        logs=logs,
        pagination=pagination,
        title="Sync History",
    )


@management_bp.route("/admin/audit-logs")
@login_required
@admin_required
def audit_logs():
    """
    Simple audit log viewer with basic filters.
    Query params:
      - action, resource_type, user_id
    """

    from models.audit_log import AuditLog

    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    action = request.args.get("action", "").strip()
    resource_type = request.args.get("resource_type", "").strip()
    user_id = request.args.get("user_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=50, type=int)

    if action:
        q = q.filter(AuditLog.action == action)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if start_date:
        try:
            q = q.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        except Exception:
            pass
    if end_date:
        try:
            q = q.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        except Exception:
            pass

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    # Render a minimal list directly if template is missing
    try:
        return render_template(
            "management/audit_logs.html",
            logs=logs,
            pagination=pagination,
            filters={
                "action": action,
                "resource_type": resource_type,
                "user_id": user_id,
                "start_date": start_date or "",
                "end_date": end_date or "",
                "page": page,
                "per_page": per_page,
            },
        )
    except Exception:
        # Fallback text view
        return jsonify(
            [
                {
                    "at": log.created_at.isoformat() if log.created_at else None,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "method": log.method,
                    "path": log.path,
                    "ip": log.ip,
                }
                for log in logs
            ]
        )


# ---------------------------------------------------------------------------
# Cache refresh
# ---------------------------------------------------------------------------


@management_bp.route("/management/refresh-all-caches", methods=["POST"])
@login_required
@admin_required
@handle_route_errors
def refresh_all_caches():
    """
    Refresh/invalidate all report caches.

    Optional query params:
      - scope: one of 'all' (default), 'virtual', 'org', 'district', 'first_time_volunteer', 'recent_volunteers'
      - school_year: for district caches (YYZZ), also used for recent volunteers if provided
      - host_filter: for district caches, defaults to 'all'
      - date_from/date_to (YYYY-MM-DD): optional for recent volunteers when school_year not provided
      - title: optional title filter applied for recent volunteers caches

    Returns JSON with counts of deleted/invalidated/updated records.
    Requires admin.
    """
    scope = request.args.get("scope", "all").lower()
    school_year = request.args.get("school_year")
    host_filter = request.args.get("host_filter", "all")

    summary = {"scope": scope, "deleted": {}, "invalidated": [], "updated": {}}

    if scope in ("all", "virtual"):
        invalidate_virtual_session_caches()  # all years
        summary["invalidated"].append("virtual_session_caches")

    if scope in ("all", "org"):
        deleted_detail = OrganizationDetailCache.query.delete()
        deleted_summary = OrganizationSummaryCache.query.delete()
        db.session.commit()
        summary["deleted"]["OrganizationDetailCache"] = deleted_detail
        summary["deleted"]["OrganizationSummaryCache"] = deleted_summary

    if scope in ("all", "first_time_volunteer"):
        deleted_ftv = FirstTimeVolunteerReportCache.query.delete()
        db.session.commit()
        summary["deleted"]["FirstTimeVolunteerReportCache"] = deleted_ftv

    # Recruitment candidates caches
    if scope in ("all", "recruitment"):
        deleted_recruitment = RecruitmentCandidatesCache.query.delete()
        db.session.commit()
        summary["deleted"]["RecruitmentCandidatesCache"] = deleted_recruitment

    if scope in ("all", "district"):
        # If a specific school_year is provided, scope deletion; else delete all
        if school_year:
            deleted_district = DistrictYearEndReport.query.filter_by(
                school_year=school_year, host_filter=host_filter
            ).delete()
        else:
            deleted_district = DistrictYearEndReport.query.delete()
        db.session.commit()
        summary["deleted"]["DistrictYearEndReport"] = deleted_district

    # Recent Volunteers caches (base + per-event-type typed caches)
    if scope in ("all", "recent_volunteers"):
        # Determine date window
        rv_school_year = request.args.get("school_year")
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")
        title_filter = (request.args.get("title") or "").strip() or None

        try:
            if rv_school_year:
                start_dt, end_dt = get_school_year_date_range(rv_school_year)
            else:
                # Fallback: parse provided dates or default to last 365 days
                end_dt = (
                    datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if date_to_str
                    else datetime.now(timezone.utc)
                )
                start_dt = (
                    datetime.strptime(date_from_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if date_from_str
                    else end_dt - timedelta(days=365)
                )
        except Exception:
            # On parse error, default last 365 days
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=365)

        # Build BASE cache (ALL types)
        base_active = _query_active_volunteers_all(start_dt, end_dt, title_filter)
        base_first = _query_first_time_in_range(start_dt, end_dt)
        base_payload = _serialize_for_cache(base_active, base_first)

        # Upsert BASE row
        base_key = "ALL"
        updated_counts = {"base": 0, "typed": 0}
        try:
            existing_base = RecentVolunteersReportCache.query.filter_by(
                school_year=rv_school_year or None,
                date_from=(
                    start_dt.date() if (start_dt and not rv_school_year) else None
                ),
                date_to=(end_dt.date() if (end_dt and not rv_school_year) else None),
                event_types=base_key,
                title_filter=title_filter or None,
            ).first()
            if not existing_base:
                existing_base = RecentVolunteersReportCache(
                    school_year=rv_school_year or None,
                    date_from=(
                        start_dt.date() if (start_dt and not rv_school_year) else None
                    ),
                    date_to=(
                        end_dt.date() if (end_dt and not rv_school_year) else None
                    ),
                    event_types=base_key,
                    title_filter=title_filter or None,
                    report_data=base_payload,
                )
                db.session.add(existing_base)
            else:
                existing_base.report_data = base_payload
                existing_base.last_updated = datetime.now(timezone.utc)
            db.session.commit()
            updated_counts["base"] = 1
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to save RecentVolunteers BASE cache: {e}")

        # Derive and upsert typed caches for each EventType
        try:
            for et in EventType:
                active_typed, first_typed = _derive_filtered_from_base(
                    base_active, base_first, [et]
                )
                typed_payload = _serialize_for_cache(active_typed, first_typed)
                typed_key = et.value
                typed_row = RecentVolunteersReportCache.query.filter_by(
                    school_year=rv_school_year or None,
                    date_from=(
                        start_dt.date() if (start_dt and not rv_school_year) else None
                    ),
                    date_to=(
                        end_dt.date() if (end_dt and not rv_school_year) else None
                    ),
                    event_types=typed_key,
                    title_filter=title_filter or None,
                ).first()
                if not typed_row:
                    typed_row = RecentVolunteersReportCache(
                        school_year=rv_school_year or None,
                        date_from=(
                            start_dt.date()
                            if (start_dt and not rv_school_year)
                            else None
                        ),
                        date_to=(
                            end_dt.date() if (end_dt and not rv_school_year) else None
                        ),
                        event_types=typed_key,
                        title_filter=title_filter or None,
                        report_data=typed_payload,
                    )
                    db.session.add(typed_row)
                else:
                    typed_row.report_data = typed_payload
                    typed_row.last_updated = datetime.now(timezone.utc)
                db.session.commit()
                updated_counts["typed"] += 1
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Failed to save RecentVolunteers typed cache for {et.value if 'et' in locals() else 'unknown'}: {e}"
            )

        summary["updated"]["RecentVolunteersReportCache"] = updated_counts

    return jsonify({"success": True, "message": "Caches refreshed", "result": summary})


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@management_bp.route("/management/users/<int:user_id>/edit", methods=["GET"])
@login_required
@security_level_required(SecurityLevel.SUPERVISOR)
def edit_user_form(user_id):
    """Route to render the user edit modal"""
    user = User.query.get_or_404(user_id)

    # Check if current user has permission to edit this user
    if not current_user.can_manage_user(user) and current_user.id != user_id:
        return jsonify({"error": "Unauthorized to edit this user"}), 403

    # Get all tenants for the dropdown (sorted by name)
    from models.tenant import Tenant

    tenants = Tenant.query.order_by(Tenant.name).all()

    return render_template(
        "management/user_edit_modal.html", user=user, tenants=tenants
    )


@management_bp.route("/management/users/<int:user_id>", methods=["PUT"])
@login_required
@security_level_required(SecurityLevel.SUPERVISOR)
def update_user(user_id):
    """Route to handle the user update form submission"""
    user = User.query.get_or_404(user_id)

    # Check if current user has permission to edit this user
    if not current_user.can_manage_user(user) and current_user.id != user_id:
        return jsonify({"error": "Unauthorized to edit this user"}), 403

    # Get form data
    email = request.form.get("email")
    security_level = int(request.form.get("security_level", 0))
    new_password = request.form.get("new_password")
    tenant_id = request.form.get("tenant_id")
    tenant_id = int(tenant_id) if tenant_id else None

    # If not admin, restrict ability to escalate privileges
    if not current_user.is_admin and security_level > current_user.security_level:
        return (
            jsonify({"error": "Cannot assign security level higher than your own"}),
            403,
        )

    # Build update kwargs
    update_kwargs = {"email": email}

    # Regular users should only be able to update security level if they outrank
    if current_user.is_admin or current_user.security_level > user.security_level:
        update_kwargs["security_level"] = security_level

    # Only admins can change tenant affiliation
    if current_user.is_admin:
        update_kwargs["tenant_id"] = tenant_id

    # Update via service
    success, error = update_user_fields(
        user,
        password=new_password if new_password else None,
        **update_kwargs,
    )

    if not success:
        return (
            jsonify({"success": False, "error": error or "Failed to update user"}),
            500,
        )

    return jsonify({"success": True, "message": "User updated successfully"}), 200
