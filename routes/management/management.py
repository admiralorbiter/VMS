"""
Management Routes Module
=======================

This module provides comprehensive administrative functionality for the
Volunteer Management System (VMS). It handles user management, data import
operations, Google Sheets integration, and system administration tasks.

Key Features:
- User administration and management
- Salesforce data import operations
- Google Sheets configuration and management
- School and district data management
- Bug report administration
- System configuration and maintenance

Main Endpoints:
- /admin: Main admin panel
- /admin/import: Data import functionality
- /management/import-classes: Import class data from Salesforce
- /google-sheets: Google Sheets management
- /management/import-schools: Import school data from Salesforce
- /management/import-districts: Import district data from Salesforce
- /schools: School management interface
- /bug-reports: Bug report administration
- /management/users/<id>/edit: User editing interface

Administrative Functions:
- User creation, editing, and management
- Security level management
- System configuration
- Data import and synchronization
- Google Sheets integration
- Bug report resolution

Salesforce Integration:
- Class data import from Salesforce
- School data import from Salesforce
- District data import from Salesforce
- Authentication and error handling
- Batch processing with rollback support

Google Sheets Management:
- Academic year-based sheet configuration
- Sheet ID management and encryption
- Year range validation and availability
- CRUD operations for sheet configurations

Security Features:
- Role-based access control
- Security level validation
- Admin-only operations
- Input validation and sanitization
- Error handling with user feedback

Dependencies:
- Flask Blueprint for routing
- Salesforce API integration
- Google Sheets API integration
- Database models for all entities
- Encryption utilities for sensitive data
- Academic year utilities

Models Used:
- User: User management and authentication
- Class: Class data and associations
- School: School information and relationships
- District: District data and organization
- BugReport: Bug report management
- GoogleSheet: Google Sheets configuration
- Database session for persistence

Template Dependencies:
- management/admin.html: Main admin panel
- management/google_sheets.html: Google Sheets management
- management/schools.html: School management interface
- management/bug_reports.html: Bug report administration
- management/resolve_form.html: Bug report resolution form
"""

import os
from datetime import datetime, timezone

import pandas as pd
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
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash

from config import Config
from models import db
from models.bug_report import BugReport, BugReportType
from models.class_model import Class
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
from models.school_model import School
from models.sync_log import SyncLog
from models.user import SecurityLevel, User
from routes.decorators import global_users_only
from routes.reports.common import get_school_year_date_range
from routes.reports.recent_volunteers import (
    _derive_filtered_from_base,
    _query_active_volunteers_all,
    _query_first_time_in_range,
    _serialize_for_cache,
)
from routes.reports.virtual_session import invalidate_virtual_session_caches
from routes.utils import log_audit_action
from utils.academic_year import get_academic_year_range

management_bp = Blueprint("management", __name__)


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
            import json

            try:
                allowed_districts = (
                    json.loads(current_user.allowed_districts)
                    if isinstance(current_user.allowed_districts, str)
                    else current_user.allowed_districts
                )
                from models.district_model import District

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
        from models.district_model import District

        districts = District.query.order_by(District.name).all()

    # Provide academic years with Google Sheets for the dropdown (virtual sessions only)
    from models.google_sheet import GoogleSheet

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


@management_bp.route("/admin/sync-logs")
@login_required
def view_sync_logs():
    """
    Display historical sync logs.

    Permission Requirements:
        - Admin access required
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("management.admin"))

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = SyncLog.query.order_by(SyncLog.started_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    logs = pagination.items

    return render_template(
        "management/sync_logs.html",
        logs=logs,
        pagination=pagination,
        title="Sync History",
    )


@management_bp.route("/admin/audit-logs")
@login_required
def audit_logs():
    """
    Simple audit log viewer with basic filters.
    Query params:
      - action, resource_type, user_id
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("index"))

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


@management_bp.route("/admin/scan-student-participation-duplicates")
@login_required
def scan_student_participation_duplicates():
    """
    Scan for duplicate EventStudentParticipation records by (event_id, student_id).

    Admin-only utility to help decide on enforcing a unique constraint.
    Returns a simple HTML view if template exists, otherwise JSON.
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("index"))

    from sqlalchemy import func

    from models.event import EventStudentParticipation

    dup_pairs = (
        db.session.query(
            EventStudentParticipation.event_id,
            EventStudentParticipation.student_id,
            func.count("*").label("cnt"),
        )
        .group_by(
            EventStudentParticipation.event_id,
            EventStudentParticipation.student_id,
        )
        .having(func.count("*") > 1)
        .all()
    )

    results = []
    for event_id, student_id, cnt in dup_pairs:
        records = (
            db.session.query(EventStudentParticipation)
            .filter(
                EventStudentParticipation.event_id == event_id,
                EventStudentParticipation.student_id == student_id,
            )
            .all()
        )
        results.append(
            {
                "event_id": event_id,
                "student_id": student_id,
                "count": int(cnt or 0),
                "records": [
                    {
                        "id": r.id,
                        "salesforce_id": r.salesforce_id,
                        "status": r.status,
                        "delivery_hours": r.delivery_hours,
                        "created_at": getattr(r, "created_at", None),
                    }
                    for r in records
                ],
            }
        )

    try:
        return render_template(
            "management/scan_student_participation_duplicates.html",
            duplicates=results,
        )
    except Exception:
        # Fallback JSON if template not present
        return jsonify({"duplicates": results, "total_pairs": len(results)})


@management_bp.route("/admin/dedupe-student-participations", methods=["POST"])
@management_bp.route("/dedupe-student-participations", methods=["POST"])
@login_required
def dedupe_student_participations():
    """
    Admin action: deduplicate EventStudentParticipation by (event_id, student_id).

    Strategy per duplicate pair:
      - Keep the earliest created record (smallest id).
      - Merge fields (prefer non-null status, delivery_hours, age_group, salesforce_id).
      - Delete the other records.
    Returns JSON summary.
    """
    if not current_user.is_admin:
        return jsonify({"error": "Admin only"}), 403

    from sqlalchemy import func

    from models.event import EventStudentParticipation

    summary = {"pairs": 0, "deleted": 0, "updated": 0}

    dup_pairs = (
        db.session.query(
            EventStudentParticipation.event_id,
            EventStudentParticipation.student_id,
            func.count("*").label("cnt"),
        )
        .group_by(
            EventStudentParticipation.event_id,
            EventStudentParticipation.student_id,
        )
        .having(func.count("*") > 1)
        .all()
    )

    for event_id, student_id, cnt in dup_pairs:
        records = (
            db.session.query(EventStudentParticipation)
            .filter(
                EventStudentParticipation.event_id == event_id,
                EventStudentParticipation.student_id == student_id,
            )
            .order_by(EventStudentParticipation.id.asc())
            .all()
        )
        if not records:
            continue
        summary["pairs"] += 1

        keeper = records[0]
        for rec in records[1:]:
            # Merge non-null fields into keeper
            if getattr(keeper, "salesforce_id", None) is None and rec.salesforce_id:
                keeper.salesforce_id = rec.salesforce_id
            if getattr(rec, "status", None):
                keeper.status = rec.status
            if getattr(rec, "delivery_hours", None) is not None:
                keeper.delivery_hours = rec.delivery_hours
            if getattr(rec, "age_group", None):
                keeper.age_group = rec.age_group
            db.session.delete(rec)
            summary["deleted"] += 1
        summary["updated"] += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e), "summary": summary}), 500

    return jsonify({"success": True, "summary": summary})


@management_bp.route("/admin/import", methods=["POST"])
@login_required
def import_data():
    """
    Handle data import functionality.

    Processes file uploads for data import operations. Currently
    a placeholder for future import functionality.

    Permission Requirements:
        - Admin access required

    Form Parameters:
        import_file: File to import

    Returns:
        Redirect to admin panel with success/error message

    Raises:
        403: Unauthorized access attempt
    """
    if not current_user.is_admin:
        return {"error": "Unauthorized"}, 403

    if "import_file" not in request.files:
        flash("No file provided", "error")
        return redirect(url_for("management.admin"))

    file = request.files["import_file"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("management.admin"))

    # TODO: Process the file and import data
    # This will be implemented after creating the model

    flash("Import started successfully", "success")
    return redirect(url_for("management.admin"))


# Google Sheet Management Routes
@management_bp.route("/google-sheets")
@login_required
def google_sheets():
    """
    Display Google Sheets management interface.

    Shows all configured Google Sheets with their academic years
    and provides options for creating new sheet configurations.

    Permission Requirements:
        - Admin access required

    Returns:
        Rendered Google Sheets management template

    Template Variables:
        sheets: List of all Google Sheet configurations
        available_years: Academic years available for new sheets
        sheet_years: Years that already have sheet configurations
    """
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("index"))
    sheets = (
        GoogleSheet.query.filter_by(purpose="virtual_sessions")
        .order_by(GoogleSheet.academic_year.desc())
        .all()
    )
    all_years = get_academic_year_range(2018, 2032)
    used_years = {sheet.academic_year for sheet in sheets}
    available_years = [y for y in all_years if y not in used_years]
    sheet_years = [sheet.academic_year for sheet in sheets]
    return render_template(
        "management/google_sheets.html",
        sheets=sheets,
        available_years=available_years,
        sheet_years=sheet_years,
    )


@management_bp.route("/google-sheets", methods=["POST"])
@login_required
def create_google_sheet():
    """
    Create a new Google Sheet configuration.

    Creates a new Google Sheet record with encrypted sheet ID
    and associates it with an academic year.

    Permission Requirements:
        - Admin access required

    Request Body (JSON):
        academic_year: Academic year for the sheet
        sheet_id: Google Sheet ID to associate

    Validation:
        - Academic year and sheet ID are required
        - No duplicate academic years allowed
        - Encryption key must be configured

    Returns:
        JSON response with success status and sheet data

    Raises:
        400: Missing required fields or duplicate academic year
        403: Unauthorized access attempt
        500: Database or encryption error
    """
    print("GOOGLE SHEETS ROUTE HIT")
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        # Debug environment variable
        encryption_key = os.getenv("ENCRYPTION_KEY")
        print(f"DEBUG: ENCRYPTION_KEY exists: {encryption_key is not None}")
        if encryption_key:
            print(f"DEBUG: ENCRYPTION_KEY length: {len(encryption_key)}")
        else:
            print("DEBUG: ENCRYPTION_KEY is None or empty")

        data = request.get_json()
        print("GOT DATA:", data)
        academic_year = data.get("academic_year")
        sheet_id = data.get("sheet_id")
        print("ACADEMIC YEAR:", academic_year, "SHEET ID:", sheet_id)

        if not all([academic_year, sheet_id]):
            return jsonify({"error": "Academic year and sheet ID are required"}), 400

        existing = GoogleSheet.query.filter_by(
            academic_year=academic_year, purpose="virtual_sessions"
        ).first()
        if existing:
            return (
                jsonify(
                    {
                        "error": f"Virtual sessions sheet for academic year {academic_year} already exists"
                    }
                ),
                400,
            )

        print(f"DEBUG: About to create GoogleSheet with sheet_id: {sheet_id}")
        new_sheet = GoogleSheet(
            academic_year=academic_year,
            sheet_id=sheet_id,
            created_by=current_user.id,
            purpose="virtual_sessions",
        )
        print("DEBUG: GoogleSheet created successfully")

        db.session.add(new_sheet)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Google Sheet for {academic_year} created successfully",
                "sheet": new_sheet.to_dict(),
            }
        )
    except Exception as e:
        print("EXCEPTION:", e)
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/management/refresh-all-caches", methods=["POST"])
@login_required
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
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    scope = request.args.get("scope", "all").lower()
    school_year = request.args.get("school_year")
    host_filter = request.args.get("host_filter", "all")

    summary = {"scope": scope, "deleted": {}, "invalidated": [], "updated": {}}
    try:
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
                    from datetime import datetime, timedelta, timezone

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
                from datetime import datetime, timedelta, timezone

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
                    date_to=(
                        end_dt.date() if (end_dt and not rv_school_year) else None
                    ),
                    event_types=base_key,
                    title_filter=title_filter or None,
                ).first()
                if not existing_base:
                    existing_base = RecentVolunteersReportCache(
                        school_year=rv_school_year or None,
                        date_from=(
                            start_dt.date()
                            if (start_dt and not rv_school_year)
                            else None
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
                current_app.logger.error(
                    f"Failed to save RecentVolunteers BASE cache: {e}"
                )

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
                            start_dt.date()
                            if (start_dt and not rv_school_year)
                            else None
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
                                end_dt.date()
                                if (end_dt and not rv_school_year)
                                else None
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

        return jsonify(
            {"success": True, "message": "Caches refreshed", "result": summary}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["PUT"])
@login_required
def update_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        data = request.get_json()
        if "sheet_id" in data:
            sheet.update_sheet_id(data["sheet_id"])
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": f"Google Sheet updated successfully",
                "sheet": sheet.to_dict(),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["DELETE"])
@login_required
def delete_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        academic_year = sheet.academic_year
        db.session.delete(sheet)
        db.session.commit()
        log_audit_action(
            action="delete", resource_type="google_sheet", resource_id=sheet_id
        )
        return jsonify(
            {
                "success": True,
                "message": f"Google Sheet for {academic_year} deleted successfully",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/google-sheets/<int:sheet_id>", methods=["GET"])
@login_required
def get_google_sheet(sheet_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    try:
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        return jsonify({"success": True, "sheet": sheet.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@management_bp.route("/management/import-districts", methods=["POST"])
@login_required
def import_districts():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account
        WHERE Type = 'School District'
        """

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain="login",
        )

        # Execute the query
        result = sf.query_all(salesforce_query)
        sf_rows = result.get("records", [])

        success_count = 0
        error_count = 0
        errors = []

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                # Check if district exists
                existing_district = District.query.filter_by(
                    salesforce_id=row["Id"]
                ).first()

                if existing_district:
                    # Update existing district
                    existing_district.name = row["Name"]
                    existing_district.district_code = row["School_Code_External_ID__c"]
                else:
                    # Create new district
                    new_district = District(
                        salesforce_id=row["Id"],
                        name=row["Name"],
                        district_code=row["School_Code_External_ID__c"],
                    )
                    db.session.add(new_district)

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing district {row.get('Name')}: {str(e)}")

        # Commit changes
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully processed {success_count} districts with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }
        )

    except SalesforceAuthenticationFailed:
        return (
            jsonify(
                {"success": False, "message": "Failed to authenticate with Salesforce"}
            ),
            401,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/schools")
@login_required
@global_users_only
def schools():
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("index"))

    # Filters and pagination
    district_q = request.args.get("district_q", "").strip()
    school_q = request.args.get("school_q", "").strip()
    level_q = request.args.get("level", "").strip()
    d_page = request.args.get("d_page", type=int, default=1)
    d_per_page = request.args.get("d_per_page", type=int, default=25)
    s_page = request.args.get("s_page", type=int, default=1)
    s_per_page = request.args.get("s_per_page", type=int, default=25)

    # Districts query
    dq = District.query
    if district_q:
        like = f"%{district_q.lower()}%"
        # Support name and district_code if present
        code_col = getattr(District, "district_code", None)
        if code_col is not None:
            dq = dq.filter(
                func.lower(District.name).like(like) | func.lower(code_col).like(like)
            )
        else:
            dq = dq.filter(func.lower(District.name).like(like))
    districts_pagination = dq.order_by(District.name).paginate(
        page=d_page, per_page=d_per_page, error_out=False
    )
    districts = districts_pagination.items

    # Schools query
    sq = School.query
    if school_q:
        sq = sq.filter(func.lower(School.name).like(f"%{school_q.lower()}%"))
    if district_q:
        sq = sq.join(District, isouter=True).filter(
            func.lower(District.name).like(f"%{district_q.lower()}%")
        )
    if level_q:
        sq = sq.filter(func.lower(School.level) == level_q.lower())
    schools_pagination = sq.order_by(School.name).paginate(
        page=s_page, per_page=s_per_page, error_out=False
    )
    schools = schools_pagination.items
    sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else None
    )

    return render_template(
        "management/schools.html",
        districts=districts,
        schools=schools,
        d_pagination=districts_pagination,
        s_pagination=schools_pagination,
        filters={
            "district_q": district_q,
            "school_q": school_q,
            "level": level_q,
            "d_page": d_page,
            "d_per_page": d_per_page,
            "s_page": s_page,
            "s_per_page": s_per_page,
        },
        sheet_url=sheet_url,
    )


@management_bp.route("/management/schools/<school_id>", methods=["DELETE"])
@login_required
def delete_school(school_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        school = School.query.get_or_404(school_id)
        db.session.delete(school)
        db.session.commit()
        log_audit_action(action="delete", resource_type="school", resource_id=school_id)
        return jsonify({"success": True, "message": "School deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@management_bp.route("/management/districts/<district_id>", methods=["DELETE"])
@login_required
def delete_district(district_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        district = District.query.get_or_404(district_id)
        db.session.delete(district)  # This will cascade delete associated schools
        db.session.commit()
        log_audit_action(
            action="delete", resource_type="district", resource_id=district_id
        )
        return jsonify(
            {
                "success": True,
                "message": "District and associated schools deleted successfully",
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@management_bp.route("/bug-reports")
@login_required
def bug_reports():
    if not current_user.is_admin:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("index"))

    # Get filter parameters
    status_filter = request.args.get("status", "all")  # all, open, resolved
    type_filter = request.args.get("type", "all")  # all, bug, data_error, other
    search_query = request.args.get("search", "").strip()

    # Start with base query
    query = BugReport.query

    # Apply status filter
    if status_filter == "open":
        query = query.filter(BugReport.resolved == False)
    elif status_filter == "resolved":
        query = query.filter(BugReport.resolved == True)

    # Apply type filter
    if type_filter == "bug":
        query = query.filter(BugReport.type == BugReportType.BUG)
    elif type_filter == "data_error":
        query = query.filter(BugReport.type == BugReportType.DATA_ERROR)
    elif type_filter == "other":
        query = query.filter(BugReport.type == BugReportType.OTHER)

    # Apply search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                BugReport.description.ilike(search_term),
                BugReport.page_title.ilike(search_term),
                BugReport.page_url.ilike(search_term),
            )
        )

    # Order by newest first
    reports = query.order_by(BugReport.created_at.desc()).all()

    # Separate open and resolved reports for template
    open_reports = [r for r in reports if not r.resolved]
    resolved_reports = [r for r in reports if r.resolved]

    return render_template(
        "management/bug_reports.html",
        reports=reports,
        open_reports=open_reports,
        resolved_reports=resolved_reports,
        BugReportType=BugReportType,
        status_filter=status_filter,
        type_filter=type_filter,
        search_query=search_query,
    )


@management_bp.route("/bug-reports/<int:report_id>/resolve", methods=["POST"])
@login_required
def resolve_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        report = BugReport.query.get_or_404(report_id)
        report.resolved = True
        report.resolved_by_id = current_user.id
        report.resolved_at = datetime.now(timezone.utc)
        report.resolution_notes = request.form.get("notes", "")

        db.session.commit()

        # If HTMX request, return redirect response
        if request.headers.get("HX-Request"):
            from flask import make_response

            response = make_response()
            response.headers["HX-Redirect"] = url_for("management.bug_reports")
            return response

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/bug-reports/<int:report_id>", methods=["DELETE"])
@login_required
def delete_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        report = BugReport.query.get_or_404(report_id)
        db.session.delete(report)
        db.session.commit()
        log_audit_action(
            action="delete", resource_type="bug_report", resource_id=report_id
        )
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@management_bp.route("/bug-reports/<int:report_id>/resolve-form")
@login_required
def get_resolve_form(report_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    report = BugReport.query.get_or_404(report_id)
    return render_template(
        "management/resolve_form.html", report_id=report_id, report=report
    )


@management_bp.route("/management/update-school-levels", methods=["POST"])
@login_required
def update_school_levels():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        sheet_id = os.getenv("SCHOOL_MAPPING_GOOGLE_SHEET")
        if not sheet_id:
            raise ValueError("School mapping Google Sheet ID not configured")

        # Try primary URL format
        csv_url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        )

        try:
            df = pd.read_csv(csv_url)
        except Exception as e:
            current_app.logger.error(f"Failed to read CSV: {str(e)}")
            # Try alternative URL format
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            df = pd.read_csv(csv_url)

        success_count = 0
        error_count = 0
        errors = []

        # Process each row
        for _, row in df.iterrows():
            try:
                # Skip rows without an ID or Level
                if pd.isna(row["Id"]) or pd.isna(row["Level"]):
                    continue

                # Find the school by Salesforce ID
                school = School.query.get(row["Id"])
                if school:
                    school.level = row["Level"].strip()
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"School not found with ID: {row['Id']}")

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing school {row.get('Id')}: {str(e)}")

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully updated {success_count} schools with {error_count} errors",
                "processed_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("School level update failed", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


@management_bp.route("/management/users/<int:user_id>/edit", methods=["GET"])
@login_required
def edit_user_form(user_id):
    """Route to render the user edit modal"""
    if (
        not current_user.is_admin
        and not current_user.security_level >= SecurityLevel.SUPERVISOR
    ):
        return jsonify({"error": "Unauthorized"}), 403

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
def update_user(user_id):
    """Route to handle the user update form submission"""
    if (
        not current_user.is_admin
        and not current_user.security_level >= SecurityLevel.SUPERVISOR
    ):
        return jsonify({"error": "Unauthorized"}), 403

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

    # Update user
    user.email = email

    # Regular users should only be able to update their own security level if they're an admin
    if current_user.is_admin or current_user.security_level > user.security_level:
        user.security_level = security_level

    # Only admins can change tenant affiliation
    if current_user.is_admin:
        user.tenant_id = tenant_id

    # Update password if provided
    if new_password:
        user.password_hash = generate_password_hash(new_password)

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "User updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
