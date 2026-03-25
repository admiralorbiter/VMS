"""
Pathful Import Routes
=====================

Route handler registration for Pathful import features.
Utility functions have been extracted to sibling modules:
  - parsing.py: date/name parsing, constants, validation
  - matching.py: entity matching/creation, cache builder
  - processing.py: row-level import processing
"""

from datetime import datetime

import pandas as pd
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from models import db
from models.event import Event, EventFormat, EventStatus, EventType
from models.pathful_import import (
    PathfulImportLog,
    PathfulImportType,
    PathfulUnmatchedRecord,
    PathfulUserProfile,
    ResolutionStatus,
)
from models.school_model import School
from models.teacher_progress import TeacherProgress
from models.tenant import Tenant
from models.volunteer import Volunteer
from routes.decorators import admin_required, handle_route_errors
from services.scoping import get_user_district_name, is_tenant_user, scope_events_query

# Import from sibling modules
from .matching import build_import_caches
from .parsing import admin_or_tenant_required, validate_session_report_columns
from .processing import process_session_report_row


def load_pathful_routes():
    """
    Load Pathful import routes onto the virtual blueprint.

    This function is called from routes.virtual.routes after the blueprint is created.
    """
    from routes.virtual.routes import virtual_bp

    @virtual_bp.route("/pathful/import", methods=["GET", "POST"])
    @login_required
    @admin_required
    def pathful_import():
        """
        Handle Pathful file upload and import.

        GET: Display upload form
        POST: Process uploaded file
        """
        if request.method == "GET":
            # Show upload form
            recent_imports = (
                PathfulImportLog.query.order_by(PathfulImportLog.started_at.desc())
                .limit(10)
                .all()
            )

            return render_template(
                "virtual/pathful/import.html",
                recent_imports=recent_imports,
            )

        # POST: Process upload
        if "file" not in request.files:
            flash("No file uploaded", "error")
            return redirect(url_for("virtual.pathful_import"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("virtual.pathful_import"))

        # Validate file type
        filename = secure_filename(file.filename)
        if not filename.endswith((".xlsx", ".xls")):
            flash(
                "Invalid file type. Please upload an Excel file (.xlsx or .xls)",
                "error",
            )
            return redirect(url_for("virtual.pathful_import"))

        try:
            # Create import log
            import_log = PathfulImportLog(
                filename=filename,
                import_type=PathfulImportType.SESSION_REPORT,
                imported_by=current_user.id,
            )
            db.session.add(import_log)
            db.session.flush()  # Get the ID

            # Read Excel file
            df = pd.read_excel(file)
            import_log.total_rows = len(df)

            # Validate columns
            is_valid, missing_cols = validate_session_report_columns(df)
            if not is_valid:
                flash(f"Missing required columns: {', '.join(missing_cols)}", "error")
                db.session.rollback()
                return redirect(url_for("virtual.pathful_import"))

            # Build caches to avoid per-row DB queries
            import time as import_time

            cache_start = import_time.time()
            caches = build_import_caches()
            print(f"Cache build time: {import_time.time() - cache_start:.1f}s")

            # Process rows
            processed_events = {}  # Cache events by session_id
            process_start = import_time.time()

            for index, row in df.iterrows():
                process_session_report_row(
                    row=row,
                    row_index=index + 1,  # 1-based row number
                    import_log=import_log,
                    processed_events=processed_events,
                    caches=caches,
                )

                # Progress output every 500 rows
                if (index + 1) % 500 == 0 or index + 1 == len(df):
                    elapsed = import_time.time() - process_start
                    rate = (index + 1) / elapsed if elapsed > 0 else 0
                    print(f"  â†’ Row {index + 1}/{len(df)} ({rate:.0f} rows/sec)")

            # Regenerate text cache from EventTeacher (source of truth)
            from services.teacher_service import sync_event_participant_fields

            for evt in processed_events.values():
                sync_event_participant_fields(evt)

            # Mark complete
            import_log.mark_complete()
            db.session.commit()

            # Phase D-4: Log import completion
            from routes.utils import log_audit_action

            log_audit_action(
                action="pol.import.completed",
                resource_type="pathful_import",
                resource_id=import_log.id,
                metadata={
                    "import_type": "pathful_virtual_sessions",
                    "counts": {
                        "processed": import_log.processed_rows,
                        "created": import_log.created_events,
                        "updated": import_log.updated_events,
                        "unmatched": import_log.unmatched_count,
                    },
                    "filename": getattr(file, "filename", "unknown"),
                },
            )

            # Success message with stats
            flash(
                f"Import completed: {import_log.processed_rows} rows processed, "
                f"{import_log.created_events} events created, "
                f"{import_log.updated_events} events updated, "
                f"{import_log.unmatched_count} unmatched records.",
                "success",
            )

            return redirect(url_for("virtual.pathful_import_history"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Pathful import error: %s", str(e))
            flash(f"Import failed: {str(e)}", "error")
            return redirect(url_for("virtual.pathful_import"))

    @virtual_bp.route("/pathful/import-history")
    @login_required
    @admin_required
    def pathful_import_history():
        """View history of Pathful imports."""
        imports = PathfulImportLog.query.order_by(
            PathfulImportLog.started_at.desc()
        ).all()

        return render_template(
            "virtual/pathful/import_history.html",
            imports=imports,
        )

    def get_match_suggestions(unmatched_record, limit=5):
        """
        Get match suggestions for an unmatched record using User Profile email.
        Returns dict with profile data and potential matches.
        """
        import json

        result = {
            "profile": None,
            "email": None,
            "school": None,
            "teacher_matches": [],
            "volunteer_matches": [],
        }

        # Extract pathful_user_id from raw_data
        raw_data = unmatched_record.raw_data
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except:
                return result

        if not raw_data:
            return result

        pathful_user_id = str(
            raw_data.get("User Auth Id") or raw_data.get("UserAuthId") or ""
        )
        if not pathful_user_id:
            return result

        # Look up User Profile
        profile = PathfulUserProfile.query.filter_by(
            pathful_user_id=pathful_user_id
        ).first()
        if not profile:
            return result

        result["profile"] = profile
        result["email"] = profile.login_email
        result["school"] = profile.school or profile.district_or_company

        # Find potential matches by email
        if profile.login_email:
            email_lower = profile.login_email.lower()

            # Search TeacherProgress
            teacher_matches = (
                TeacherProgress.query.filter(
                    db.func.lower(TeacherProgress.email) == email_lower
                )
                .limit(limit)
                .all()
            )
            result["teacher_matches"] = [
                {"id": t.id, "name": t.name, "email": t.email} for t in teacher_matches
            ]

            # Search Volunteers - join with Email model
            from models.contact import Email as ContactEmail

            volunteer_matches = (
                Volunteer.query.join(
                    ContactEmail, Volunteer.id == ContactEmail.contact_id
                )
                .filter(db.func.lower(ContactEmail.email) == email_lower)
                .limit(limit)
                .all()
            )
            result["volunteer_matches"] = [
                {
                    "id": v.id,
                    "name": f"{v.first_name} {v.last_name}".strip(),
                    "email": v.primary_email or "",
                }
                for v in volunteer_matches
            ]

        return result

    @virtual_bp.route("/pathful/unmatched")
    @login_required
    @admin_required
    def pathful_unmatched():
        """View and manage unmatched records with enhanced suggestions."""
        status_filter = request.args.get("status", "pending")
        type_filter = request.args.get("type", "all")
        page = request.args.get("page", 1, type=int)
        per_page = 50

        query = PathfulUnmatchedRecord.query

        if status_filter != "all":
            query = query.filter(
                PathfulUnmatchedRecord.resolution_status == status_filter
            )

        if type_filter != "all":
            query = query.filter(PathfulUnmatchedRecord.unmatched_type == type_filter)

        # Get summary counts
        total_pending = PathfulUnmatchedRecord.query.filter_by(
            resolution_status="pending"
        ).count()
        total_resolved = PathfulUnmatchedRecord.query.filter_by(
            resolution_status="resolved"
        ).count()
        total_ignored = PathfulUnmatchedRecord.query.filter_by(
            resolution_status="ignored"
        ).count()

        # Count by type (pending only)
        teacher_pending = PathfulUnmatchedRecord.query.filter_by(
            resolution_status="pending", unmatched_type="teacher"
        ).count()
        volunteer_pending = PathfulUnmatchedRecord.query.filter_by(
            resolution_status="pending", unmatched_type="volunteer"
        ).count()

        # Paginate results
        unmatched = query.order_by(PathfulUnmatchedRecord.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Enrich with suggestions (only for displayed page)
        enriched_records = []
        for record in unmatched.items:
            suggestions = get_match_suggestions(record)
            enriched_records.append(
                {
                    "record": record,
                    "suggestions": suggestions,
                }
            )

        return render_template(
            "virtual/pathful/unmatched.html",
            unmatched=unmatched,
            enriched_records=enriched_records,
            status_filter=status_filter,
            type_filter=type_filter,
            total_pending=total_pending,
            total_resolved=total_resolved,
            total_ignored=total_ignored,
            teacher_pending=teacher_pending,
            volunteer_pending=volunteer_pending,
        )

    @virtual_bp.route("/pathful/unmatched/<int:record_id>/resolve", methods=["POST"])
    @login_required
    @admin_required
    def resolve_unmatched(record_id):
        """Resolve an unmatched record."""
        record = PathfulUnmatchedRecord.query.get_or_404(record_id)

        action = request.form.get("action")
        notes = request.form.get("notes", "")

        if action == "ignore":
            record.resolve(
                status=ResolutionStatus.IGNORED,
                notes=notes,
                resolved_by=current_user.id,
            )
            flash("Record marked as ignored.", "success")

        elif action == "create_teacher":
            # Create a new TeacherProgress record
            # This is a placeholder - would need more form fields
            flash("Teacher creation not yet implemented.", "warning")

        elif action == "create_volunteer":
            # Create a new Volunteer record
            flash("Volunteer creation not yet implemented.", "warning")

        elif action == "match_teacher":
            teacher_id = request.form.get("teacher_id")
            if teacher_id:
                record.resolve(
                    status=ResolutionStatus.RESOLVED,
                    notes=notes,
                    resolved_by=current_user.id,
                    teacher_id=int(teacher_id),
                )
                flash("Record matched to teacher.", "success")

        elif action == "match_volunteer":
            volunteer_id = request.form.get("volunteer_id")
            if volunteer_id:
                record.resolve(
                    status=ResolutionStatus.RESOLVED,
                    notes=notes,
                    resolved_by=current_user.id,
                    volunteer_id=int(volunteer_id),
                )
                flash("Record matched to volunteer.", "success")

        db.session.commit()
        return redirect(url_for("virtual.pathful_unmatched"))

    @virtual_bp.route("/pathful/unmatched/bulk-resolve", methods=["POST"])
    @login_required
    @admin_required
    def bulk_resolve_unmatched():
        """Bulk resolve multiple unmatched records."""
        record_ids = request.form.getlist("record_ids")
        action = request.form.get("action")
        notes = request.form.get("notes", "Bulk action")

        # Limit to 100 records per operation
        if len(record_ids) > 100:
            flash("Maximum 100 records can be processed at once.", "error")
            return redirect(url_for("virtual.pathful_unmatched"))

        if not record_ids:
            flash("No records selected.", "warning")
            return redirect(url_for("virtual.pathful_unmatched"))

        resolved_count = 0

        for record_id in record_ids:
            try:
                record = PathfulUnmatchedRecord.query.get(int(record_id))
                if not record or record.resolution_status != "pending":
                    continue

                if action == "ignore":
                    record.resolve(
                        status=ResolutionStatus.IGNORED,
                        notes=notes,
                        resolved_by=current_user.id,
                    )
                    resolved_count += 1

            except Exception as e:
                current_app.logger.error("Error resolving record %s: %s", record_id, e)
                continue

        db.session.commit()
        flash(f"Successfully resolved {resolved_count} records.", "success")
        return redirect(url_for("virtual.pathful_unmatched"))

    # API endpoints for AJAX operations
    @virtual_bp.route("/api/pathful/import/<int:import_id>")
    @login_required
    def api_pathful_import_status(import_id):
        """Get status of a specific import (API)."""
        import_log = PathfulImportLog.query.get_or_404(import_id)
        return jsonify(import_log.to_dict())

    @virtual_bp.route("/api/pathful/unmatched/<int:record_id>")
    @login_required
    def api_pathful_unmatched_detail(record_id):
        """Get details of an unmatched record (API)."""
        record = PathfulUnmatchedRecord.query.get_or_404(record_id)
        return jsonify(record.to_dict())

    @virtual_bp.route("/pathful/import/<int:import_id>")
    @login_required
    @admin_required
    def pathful_import_detail(import_id):
        """
        View details of a specific import batch.

        Shows:
        - Import summary statistics
        - Events created/updated in this batch
        - Unmatched records from this batch
        """
        import_log = PathfulImportLog.query.get_or_404(import_id)

        # Get unmatched records for this import
        unmatched_records = (
            PathfulUnmatchedRecord.query.filter_by(import_log_id=import_id)
            .order_by(PathfulUnmatchedRecord.row_number)
            .limit(100)
            .all()
        )

        unmatched_count = PathfulUnmatchedRecord.query.filter_by(
            import_log_id=import_id
        ).count()

        pending_count = PathfulUnmatchedRecord.query.filter_by(
            import_log_id=import_id, resolution_status=ResolutionStatus.PENDING
        ).count()

        return render_template(
            "virtual/pathful/import_detail.html",
            import_log=import_log,
            unmatched_records=unmatched_records,
            unmatched_count=unmatched_count,
            pending_count=pending_count,
        )

    @virtual_bp.route("/pathful/participants")
    @login_required
    @admin_required
    def pathful_participants():
        """
        View matched participants (educators and professionals) from Pathful imports.

        Shows:
        - Educators (TeacherProgress with pathful_user_id)
        - Professionals (Volunteer with pathful_user_id)
        """
        tab = request.args.get("tab", "educators")
        page = request.args.get("page", 1, type=int)
        per_page = 50

        if tab == "educators":
            # Get teachers with pathful_user_id
            query = TeacherProgress.query.filter(
                TeacherProgress.pathful_user_id.isnot(None)
            ).order_by(TeacherProgress.id.desc())

            participants = query.paginate(page=page, per_page=per_page, error_out=False)
            total_count = query.count()
        else:
            # Get volunteers with pathful_user_id
            query = Volunteer.query.filter(
                Volunteer.pathful_user_id.isnot(None)
            ).order_by(Volunteer.id.desc())

            participants = query.paginate(page=page, per_page=per_page, error_out=False)
            total_count = query.count()

        # Get counts for tabs
        educator_count = TeacherProgress.query.filter(
            TeacherProgress.pathful_user_id.isnot(None)
        ).count()

        professional_count = Volunteer.query.filter(
            Volunteer.pathful_user_id.isnot(None)
        ).count()

        return render_template(
            "virtual/pathful/participants.html",
            participants=participants,
            tab=tab,
            total_count=total_count,
            educator_count=educator_count,
            professional_count=professional_count,
        )

    @virtual_bp.route("/api/pathful/events")
    @login_required
    def api_pathful_events():
        """API endpoint for events DataTable."""
        # Get DataTables parameters
        draw = request.args.get("draw", 1, type=int)
        start = request.args.get("start", 0, type=int)
        length = request.args.get("length", 50, type=int)
        search = request.args.get("search[value]", "")

        # Base query
        query = Event.query.filter(Event.import_source == "pathful_direct")

        # Apply search
        if search:
            query = query.filter(
                db.or_(
                    Event.title.ilike(f"%{search}%"),
                    Event.career_cluster.ilike(f"%{search}%"),
                    Event.pathful_session_id.ilike(f"%{search}%"),
                )
            )

        # Get total count
        total_count = Event.query.filter(
            Event.import_source == "pathful_direct"
        ).count()
        filtered_count = query.count()

        # Apply ordering
        order_column = request.args.get("order[0][column]", "0", type=int)
        order_dir = request.args.get("order[0][dir]", "desc")

        columns = [
            Event.id,
            Event.title,
            Event.start_date,
            Event.career_cluster,
            Event.status,
        ]
        if order_column < len(columns):
            if order_dir == "asc":
                query = query.order_by(columns[order_column].asc())
            else:
                query = query.order_by(columns[order_column].desc())
        else:
            query = query.order_by(Event.start_date.desc())

        # Paginate
        events = query.offset(start).limit(length).all()

        # Format data
        data = []
        for event in events:
            data.append(
                {
                    "id": event.id,
                    "title": event.title or "Untitled",
                    "date": (
                        event.start_date.strftime("%Y-%m-%d")
                        if event.start_date
                        else ""
                    ),
                    "career_cluster": event.career_cluster or "",
                    "status": event.status.value if event.status else "",
                    "students": event.registered_student_count or 0,
                    "pathful_id": event.pathful_session_id or "",
                }
            )

        return jsonify(
            {
                "draw": draw,
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }
        )

    # =============================================================================
    # USER REPORT IMPORT ROUTES
    # =============================================================================

    # Required columns for User Report import
    REQUIRED_USER_REPORT_COLUMNS = [
        "UserAuthId",
        "SignUpRole",
        "Name",
    ]

    OPTIONAL_USER_REPORT_COLUMNS = [
        "LoginEmail",
        "NotificationEmail",
        "School",
        "District or Company",
        "JobTitle",
        "GradeCluster",
        "Skills",
        "City",
        "State",
        "PostalCode",
        "JoinDate",
        "LastLoginDate",
        "LoginCount",
        "CountOfDaysLoggedInLast30Days",
        "LastSessionDate",
        "ActiveSubscriptionType",
        "ActiveSubscriptionName",
        "Affiliations",
    ]

    def parse_user_report_date(date_value):
        """Parse date from User Report, handling various formats."""
        if date_value is None or (
            isinstance(date_value, float) and pd.isna(date_value)
        ):
            return None

        if hasattr(date_value, "to_pydatetime"):
            try:
                result = date_value.to_pydatetime()
                if pd.isna(result):
                    return None
                return result
            except Exception:
                return None

        if isinstance(date_value, datetime):
            return date_value

        date_str = str(date_value).strip()
        if date_str.lower() in ("nat", "nan", "none", ""):
            return None

        # Try common date formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    @virtual_bp.route("/pathful/import-users", methods=["GET", "POST"])
    @login_required
    @admin_required
    def pathful_import_users():
        """Import User Report from Pathful export."""
        if request.method == "GET":
            # Get recent User Report imports
            recent_imports = (
                PathfulImportLog.query.filter_by(
                    import_type=PathfulImportType.USER_REPORT
                )
                .order_by(PathfulImportLog.started_at.desc())
                .limit(5)
                .all()
            )

            # Get profile statistics
            total_profiles = PathfulUserProfile.query.count()
            linked_count = PathfulUserProfile.query.filter(
                db.or_(
                    PathfulUserProfile.teacher_progress_id.isnot(None),
                    PathfulUserProfile.volunteer_id.isnot(None),
                )
            ).count()

            return render_template(
                "virtual/pathful/import_users.html",
                recent_imports=recent_imports,
                total_profiles=total_profiles,
                linked_count=linked_count,
            )

        # POST - Process file upload
        if "file" not in request.files:
            flash("No file uploaded", "error")
            return redirect(url_for("virtual.pathful_import_users"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("virtual.pathful_import_users"))

        if not file.filename.endswith((".xlsx", ".xls")):
            flash(
                "Invalid file format. Please upload an Excel file (.xlsx or .xls)",
                "error",
            )
            return redirect(url_for("virtual.pathful_import_users"))

        # Create import log
        import_log = PathfulImportLog(
            filename=secure_filename(file.filename),
            import_type=PathfulImportType.USER_REPORT,
            imported_by=current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(import_log)
        db.session.commit()

        try:
            # Read Excel file
            df = pd.read_excel(file)

            # Validate required columns
            missing_columns = [
                col for col in REQUIRED_USER_REPORT_COLUMNS if col not in df.columns
            ]
            if missing_columns:
                flash(
                    f"Missing required columns: {', '.join(missing_columns)}", "error"
                )
                import_log.error_count = 1
                import_log.error_details = f"Missing columns: {missing_columns}"
                import_log.mark_complete()
                db.session.commit()
                return redirect(url_for("virtual.pathful_import_users"))

            import_log.total_rows = len(df)

            # Process rows
            created_count = 0
            updated_count = 0
            linked_count = 0
            skipped_count = 0
            errors = []

            for idx, row in df.iterrows():
                try:
                    signup_role = str(row.get("SignUpRole", "")).strip()

                    # Skip students and parents
                    if signup_role not in ["Educator", "Professional"]:
                        skipped_count += 1
                        continue

                    pathful_user_id = str(row.get("UserAuthId", "")).strip()
                    if not pathful_user_id or pathful_user_id == "nan":
                        skipped_count += 1
                        continue

                    # Check for existing profile
                    existing = PathfulUserProfile.query.filter_by(
                        pathful_user_id=pathful_user_id
                    ).first()

                    if existing:
                        # Update existing profile
                        profile = existing
                        updated_count += 1
                    else:
                        # Create new profile
                        profile = PathfulUserProfile(
                            pathful_user_id=pathful_user_id,
                            signup_role=signup_role,
                            import_log_id=import_log.id,
                        )
                        db.session.add(profile)
                        created_count += 1

                    # Update profile fields
                    profile.signup_role = signup_role
                    profile.name = str(row.get("Name", "")).strip() or None
                    profile.login_email = str(row.get("LoginEmail", "")).strip() or None
                    profile.notification_email = (
                        str(row.get("NotificationEmail", "")).strip() or None
                    )
                    profile.school = str(row.get("School", "")).strip() or None
                    profile.district_or_company = (
                        str(row.get("District or Company", "")).strip() or None
                    )
                    profile.job_title = str(row.get("JobTitle", "")).strip() or None
                    profile.grade_cluster = (
                        str(row.get("GradeCluster", "")).strip() or None
                    )

                    # Skills and affiliations
                    skills = row.get("Skills", "")
                    if pd.notna(skills):
                        profile.skills = str(skills).strip() or None
                    affiliations = row.get("Affiliations", "")
                    if pd.notna(affiliations):
                        profile.affiliations = str(affiliations).strip() or None

                    # Location
                    profile.city = str(row.get("City", "")).strip() or None
                    profile.state = str(row.get("State", "")).strip() or None
                    profile.postal_code = str(row.get("PostalCode", "")).strip() or None

                    # Parse dates
                    profile.join_date = parse_user_report_date(row.get("JoinDate"))
                    profile.last_login_date = parse_user_report_date(
                        row.get("LastLoginDate")
                    )
                    profile.last_session_date = parse_user_report_date(
                        row.get("LastSessionDate")
                    )

                    # Activity metrics
                    login_count = row.get("LoginCount")
                    if pd.notna(login_count):
                        try:
                            profile.login_count = int(login_count)
                        except (ValueError, TypeError):
                            pass

                    days_30 = row.get("CountOfDaysLoggedInLast30Days")
                    if pd.notna(days_30):
                        try:
                            profile.days_logged_in_last_30 = int(days_30)
                        except (ValueError, TypeError):
                            pass

                    # Subscription
                    profile.subscription_type = (
                        str(row.get("ActiveSubscriptionType", "")).strip() or None
                    )
                    profile.subscription_name = (
                        str(row.get("ActiveSubscriptionName", "")).strip() or None
                    )

                    # Auto-link to existing records
                    if not profile.is_linked:
                        if signup_role == "Educator":
                            # Try pathful_user_id first (fastest)
                            teacher_progress = TeacherProgress.query.filter_by(
                                pathful_user_id=pathful_user_id
                            ).first()
                            if teacher_progress:
                                profile.link_to_teacher_progress(teacher_progress.id)
                                linked_count += 1
                            else:
                                # Fallback: email/name matching via centralized service
                                from services.teacher_matching_service import (
                                    normalize_name,
                                )

                                if profile.login_email:
                                    tp = TeacherProgress.query.filter(
                                        func.lower(TeacherProgress.email)
                                        == profile.login_email.strip().lower()
                                    ).first()
                                    if tp:
                                        profile.link_to_teacher_progress(tp.id)
                                        if not tp.pathful_user_id:
                                            tp.pathful_user_id = pathful_user_id
                                        linked_count += 1
                                    elif profile.name:
                                        prof_norm = normalize_name(profile.name)
                                        if prof_norm:
                                            tps = TeacherProgress.query.filter(
                                                TeacherProgress.name.isnot(None)
                                            ).all()
                                            for cand in tps:
                                                if (
                                                    normalize_name(cand.name)
                                                    == prof_norm
                                                ):
                                                    profile.link_to_teacher_progress(
                                                        cand.id
                                                    )
                                                    if not cand.pathful_user_id:
                                                        cand.pathful_user_id = (
                                                            pathful_user_id
                                                        )
                                                    linked_count += 1
                                                    break
                        elif signup_role == "Professional":
                            # Try to find Volunteer with this pathful_user_id
                            volunteer = Volunteer.query.filter_by(
                                pathful_user_id=pathful_user_id
                            ).first()
                            if volunteer:
                                profile.link_to_volunteer(volunteer.id)
                                linked_count += 1

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")
                    continue

            # Update import log
            import_log.processed_rows = created_count + updated_count
            import_log.skipped_rows = skipped_count
            import_log.created_teachers = (
                created_count  # Repurposing for profiles created
            )
            import_log.matched_teachers = (
                updated_count  # Repurposing for profiles updated
            )
            import_log.error_count = len(errors)
            if errors:
                import_log.error_details = "\n".join(errors[:50])  # Limit to 50 errors
            import_log.mark_complete()

            db.session.commit()

            flash(
                f"User Report imported successfully: {created_count} created, "
                f"{updated_count} updated, {linked_count} auto-linked, "
                f"{skipped_count} skipped (students/parents)",
                "success",
            )
            return redirect(url_for("virtual.pathful_users"))

        except Exception as e:
            db.session.rollback()
            import_log.error_count = 1
            import_log.error_details = str(e)
            import_log.mark_complete()
            db.session.commit()

            current_app.logger.error("User Report import failed: %s", str(e))
            flash(f"Import failed: {str(e)}", "error")
            return redirect(url_for("virtual.pathful_import_users"))

    @virtual_bp.route("/pathful/users")
    @login_required
    @admin_required
    def pathful_users():
        """View all imported Pathful user profiles."""
        page = request.args.get("page", 1, type=int)
        per_page = 50
        role_filter = request.args.get("role", "")
        link_filter = request.args.get("linked", "")
        search = request.args.get("search", "").strip()

        query = PathfulUserProfile.query

        # Apply filters
        if role_filter:
            query = query.filter(PathfulUserProfile.signup_role == role_filter)

        if link_filter == "linked":
            query = query.filter(
                db.or_(
                    PathfulUserProfile.teacher_progress_id.isnot(None),
                    PathfulUserProfile.volunteer_id.isnot(None),
                )
            )
        elif link_filter == "unlinked":
            query = query.filter(
                PathfulUserProfile.teacher_progress_id.is_(None),
                PathfulUserProfile.volunteer_id.is_(None),
            )

        if search:
            query = query.filter(
                db.or_(
                    PathfulUserProfile.name.ilike(f"%{search}%"),
                    PathfulUserProfile.login_email.ilike(f"%{search}%"),
                    PathfulUserProfile.school.ilike(f"%{search}%"),
                    PathfulUserProfile.pathful_user_id.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(PathfulUserProfile.name)
        profiles = query.paginate(page=page, per_page=per_page, error_out=False)

        # Get counts for filter badges
        total_count = PathfulUserProfile.query.count()
        educator_count = PathfulUserProfile.query.filter_by(
            signup_role="Educator"
        ).count()
        professional_count = PathfulUserProfile.query.filter_by(
            signup_role="Professional"
        ).count()
        linked_count = PathfulUserProfile.query.filter(
            db.or_(
                PathfulUserProfile.teacher_progress_id.isnot(None),
                PathfulUserProfile.volunteer_id.isnot(None),
            )
        ).count()

        return render_template(
            "virtual/pathful/users.html",
            profiles=profiles,
            total_count=total_count,
            educator_count=educator_count,
            professional_count=professional_count,
            linked_count=linked_count,
            filters={
                "role": role_filter,
                "linked": link_filter,
                "search": search,
            },
        )

    @virtual_bp.route("/api/pathful/users/<int:profile_id>/link", methods=["POST"])
    @login_required
    @admin_required
    def api_link_pathful_user(profile_id):
        """Manually link a Pathful user profile to a Polaris record."""
        profile = PathfulUserProfile.query.get_or_404(profile_id)
        data = request.get_json()

        link_type = data.get("link_type")  # 'teacher_progress' or 'volunteer'
        record_id = data.get("record_id")

        if not link_type or not record_id:
            return (
                jsonify({"success": False, "error": "Missing link_type or record_id"}),
                400,
            )

        try:
            if link_type == "teacher_progress":
                profile.link_to_teacher_progress(record_id)
            elif link_type == "volunteer":
                profile.link_to_volunteer(record_id)
            else:
                return jsonify({"success": False, "error": "Invalid link_type"}), 400

            db.session.commit()
            return jsonify({"success": True, "profile": profile.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    # =============================================================================
    # MANUAL SESSION CREATION & TEACHER SEARCH API
    # =============================================================================

    @virtual_bp.route("/sessions/create", methods=["POST"])
    @login_required
    @admin_required
    def create_virtual_session():
        """
        Manually create a virtual session.

        Creates a new Event with type=VIRTUAL_SESSION from form data and
        optionally links teachers via EventTeacher association.
        """
        from models.event import EventTeacher
        from models.teacher import Teacher

        title = request.form.get("title", "").strip()
        start_date_str = request.form.get("start_date", "").strip()

        if not title or not start_date_str:
            flash("Title and Date are required.", "error")
            return redirect(url_for("virtual.virtual_sessions"))

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for("virtual.virtual_sessions"))

        # Parse optional fields
        district_partner = request.form.get("district_partner", "").strip() or None
        career_cluster = request.form.get("career_cluster", "").strip() or None
        school_id = request.form.get("school", "").strip() or None
        status_str = request.form.get("status", "Confirmed").strip()
        teacher_ids_str = request.form.get("teacher_ids", "").strip()

        try:
            registered_student_count = int(
                request.form.get("registered_student_count", "0") or "0"
            )
        except ValueError:
            registered_student_count = 0

        # Map status
        try:
            status = EventStatus(status_str)
        except ValueError:
            status = EventStatus.CONFIRMED

        # Create the event
        event = Event(
            title=title,
            start_date=start_date,
            type=EventType.VIRTUAL_SESSION,
            format=EventFormat.VIRTUAL,
            status=status,
            district_partner=district_partner,
            career_cluster=career_cluster,
            school=school_id,
            registered_student_count=registered_student_count,
            import_source="manual",
        )
        db.session.add(event)
        db.session.flush()  # Get the event ID

        # Link teachers if provided
        # Use 'attended' for completed events, 'registered' otherwise
        teacher_status = (
            "attended" if status in (EventStatus.COMPLETED,) else "registered"
        )
        linked_teachers = 0
        if teacher_ids_str:
            for tid_str in teacher_ids_str.split(","):
                tid_str = tid_str.strip()
                if not tid_str:
                    continue
                try:
                    tid = int(tid_str)
                    teacher = Teacher.query.get(tid)
                    if teacher:
                        et = EventTeacher(
                            event_id=event.id,
                            teacher_id=teacher.id,
                            status=teacher_status,
                        )
                        db.session.add(et)
                        linked_teachers += 1
                except (ValueError, TypeError):
                    continue

        db.session.commit()

        msg = f'Session "{title}" created successfully.'
        if linked_teachers:
            msg += f" {linked_teachers} teacher(s) linked."
        flash(msg, "success")
        return redirect(url_for("virtual.virtual_sessions"))

    @virtual_bp.route("/api/teachers/search")
    @login_required
    @admin_required
    def api_search_teachers():
        """
        Search teachers by name for the session creation modal.

        Returns JSON array of matching teachers: [{id, name, school_name}]
        """
        from models.teacher import Teacher

        q = request.args.get("q", "").strip()
        if not q or len(q) < 2:
            return jsonify([])

        teachers = (
            Teacher.query.filter(
                db.or_(
                    Teacher.first_name.ilike(f"%{q}%"),
                    Teacher.last_name.ilike(f"%{q}%"),
                    (Teacher.first_name + " " + Teacher.last_name).ilike(f"%{q}%"),
                )
            )
            .limit(20)
            .all()
        )

        results = []
        for t in teachers:
            school_name = t.school.name if t.school else ""
            results.append(
                {
                    "id": t.id,
                    "name": f"{t.first_name or ''} {t.last_name or ''}".strip(),
                    "school_name": school_name,
                }
            )

        return jsonify(results)

    # =============================================================================
    # VIRTUAL SESSION EDIT VIEW
    # =============================================================================

    @virtual_bp.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def edit_virtual_session(session_id):
        """
        Dedicated virtual session edit page with teacher management.

        GET: Display the edit form with current session data and linked teachers.
        POST: Save changes to session fields and teacher list.
        """
        from models.event import EventTeacher
        from models.teacher import Teacher

        event = db.session.get(Event, session_id)
        if not event or event.type != EventType.VIRTUAL_SESSION:
            flash("Virtual session not found.", "error")
            return redirect(url_for("virtual.virtual_sessions"))

        if request.method == "POST":
            # Update fields
            title = request.form.get("title", "").strip()
            start_date_str = request.form.get("start_date", "").strip()

            if not title or not start_date_str:
                flash("Title and Date are required.", "error")
                return redirect(
                    url_for("virtual.edit_virtual_session", session_id=session_id)
                )

            try:
                event.start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format.", "error")
                return redirect(
                    url_for("virtual.edit_virtual_session", session_id=session_id)
                )

            event.title = title
            event.district_partner = (
                request.form.get("district_partner", "").strip() or None
            )
            event.career_cluster = (
                request.form.get("career_cluster", "").strip() or None
            )
            event.school = request.form.get("school", "").strip() or None

            try:
                event.registered_student_count = int(
                    request.form.get("registered_student_count", "0") or "0"
                )
            except ValueError:
                event.registered_student_count = 0

            status_str = request.form.get("status", "Confirmed").strip()
            try:
                event.status = EventStatus(status_str)
            except ValueError:
                event.status = EventStatus.CONFIRMED

            db.session.commit()
            flash(f'Session "{event.title}" updated successfully.', "success")
            return redirect(url_for("events.view_event", id=session_id))

        # GET: Gather data for the form
        # Current teachers linked to this event
        linked_teachers = []
        for et in event.teacher_registrations:
            t = et.teacher
            linked_teachers.append(
                {
                    "id": t.id,
                    "name": f"{t.first_name or ''} {t.last_name or ''}".strip(),
                    "school_name": t.school.name if t.school else "",
                    "status": et.status or "registered",
                    "source": "event_teacher",
                }
            )

        # Also include text-based educators from Pathful imports
        if event.educators:
            for educator_name in event.educators.split(";"):
                educator_name = educator_name.strip()
                if educator_name:
                    linked_teachers.append(
                        {
                            "id": None,
                            "name": educator_name,
                            "school_name": "",
                            "status": "imported",
                            "source": "text_field",
                        }
                    )

        # Get districts and clusters for datalists
        districts = (
            db.session.query(Event.district_partner)
            .filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.district_partner.isnot(None),
                Event.district_partner != "",
            )
            .distinct()
            .order_by(Event.district_partner)
            .all()
        )
        districts = [d[0] for d in districts]

        career_clusters = (
            db.session.query(Event.career_cluster)
            .filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.career_cluster.isnot(None),
                Event.career_cluster != "",
            )
            .distinct()
            .order_by(Event.career_cluster)
            .all()
        )
        career_clusters = [c[0] for c in career_clusters]

        return render_template(
            "virtual/session_edit.html",
            event=event,
            linked_teachers=linked_teachers,
            districts=districts,
            career_clusters=career_clusters,
        )

    @virtual_bp.route("/sessions/<int:session_id>/teachers", methods=["POST"])
    @login_required
    @admin_required
    def add_session_teacher(session_id):
        """Add a teacher to a virtual session via AJAX."""
        from models.event import EventStatus, EventTeacher
        from models.teacher import Teacher

        event = db.session.get(Event, session_id)
        if not event:
            return jsonify({"success": False, "error": "Session not found"}), 404

        data = request.get_json()
        teacher_id = data.get("teacher_id")
        if not teacher_id:
            return jsonify({"success": False, "error": "teacher_id required"}), 400

        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            return jsonify({"success": False, "error": "Teacher not found"}), 404

        # Check if already linked
        existing = EventTeacher.query.filter_by(
            event_id=session_id, teacher_id=teacher_id
        ).first()
        if existing:
            return jsonify({"success": False, "error": "Teacher already linked"}), 409

        # Set status based on event completion: 'attended' for completed, 'registered' otherwise
        teacher_status = (
            "attended" if event.status == EventStatus.COMPLETED else "registered"
        )
        et = EventTeacher(
            event_id=session_id, teacher_id=teacher_id, status=teacher_status
        )
        db.session.add(et)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "teacher": {
                    "id": teacher.id,
                    "name": f"{teacher.first_name or ''} {teacher.last_name or ''}".strip(),
                    "school_name": teacher.school.name if teacher.school else "",
                },
            }
        )

    @virtual_bp.route(
        "/sessions/<int:session_id>/teachers/<int:teacher_id>/remove",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def remove_session_teacher(session_id, teacher_id):
        """Remove a teacher from a virtual session via AJAX."""
        from models.event import EventTeacher

        et = EventTeacher.query.filter_by(
            event_id=session_id, teacher_id=teacher_id
        ).first()
        if not et:
            return jsonify({"success": False, "error": "Link not found"}), 404

        db.session.delete(et)
        db.session.commit()
        return jsonify({"success": True})

    # =============================================================================
    # SIMPLIFIED VIRTUAL SESSIONS VIEW
    # =============================================================================
    # This is a clean, simple replacement for the complex /usage route.
    # It directly queries Pathful-imported virtual sessions without legacy logic.

    @virtual_bp.route("/sessions")
    @login_required
    @admin_or_tenant_required
    def virtual_sessions():
        """
        Simplified Virtual Sessions view.

        This replaces the complex /usage route with a clean, direct query
        of Pathful-imported virtual session data.

        Phase D-3: District Admin Access (DEC-009)
        - Staff/admin users see all sessions
        - Tenant users see only their district's sessions
        """
        from datetime import datetime

        # Determine user's district for scoping (Phase D-3)
        user_district = get_user_district_name(current_user)
        is_tenant = is_tenant_user(current_user)

        # Get filter parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)

        # Date range (default: current academic year Aug-Jul)
        today = datetime.now()
        if today.month >= 8:
            default_start = datetime(today.year, 8, 1)
            default_end = datetime(today.year + 1, 7, 31, 23, 59, 59)
        else:
            default_start = datetime(today.year - 1, 8, 1)
            default_end = datetime(today.year, 7, 31, 23, 59, 59)

        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")

        try:
            date_from = (
                datetime.strptime(date_from_str, "%Y-%m-%d")
                if date_from_str
                else default_start
            )
        except ValueError:
            date_from = default_start

        try:
            date_to = (
                datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                if date_to_str
                else default_end
            )
        except ValueError:
            date_to = default_end

        # Other filters
        career_cluster = request.args.get("career_cluster", "")
        district = request.args.get("district", "")
        school = request.args.get("school", "")
        status = request.args.get("status", "")
        search = request.args.get("search", "")

        # Sort: validate and apply for all sortable columns
        ALLOWED_SORTS = (
            "date",
            "title",
            "district",
            "school",
            "educators",
            "presenters",
            "cluster",
            "students",
            "status",
        )
        sort_param = request.args.get("sort", "date")
        if sort_param not in ALLOWED_SORTS:
            sort_param = "date"
        dir_param = request.args.get("dir", "desc")
        if dir_param not in ("asc", "desc"):
            dir_param = "desc"

        # Base query - all virtual sessions (include dateless/unscheduled events)
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            db.or_(
                db.and_(
                    Event.start_date >= date_from,
                    Event.start_date <= date_to,
                ),
                Event.start_date.is_(None),  # Include unscheduled events
            ),
        )

        # Phase D-3: Apply tenant scoping for district admins
        query = scope_events_query(query, current_user)

        # Apply filters
        if career_cluster:
            query = query.filter(Event.career_cluster == career_cluster)

        if district:
            query = query.filter(Event.district_partner == district)

        if school:
            query = query.filter(Event.school == school)

        if status:
            if status == "Unscheduled":
                query = query.filter(Event.start_date.is_(None))
            else:
                try:
                    status_enum = EventStatus(status)
                    query = query.filter(Event.status == status_enum)
                except ValueError:
                    pass

        if search:
            # Search by Title, Educator(s), and Presenter(s) only (case-insensitive, partial match)
            query = query.filter(
                db.or_(
                    Event.title.ilike(f"%{search}%"),
                    Event.educators.ilike(f"%{search}%"),
                    Event.professionals.ilike(f"%{search}%"),
                )
            )

        # Order and paginate with eager loading for related data
        from sqlalchemy.orm import joinedload

        query = query.options(
            joinedload(Event.school_obj),
            joinedload(Event.volunteers),
            joinedload(Event.teachers),
        )
        # Apply order_by for the selected sort column
        if sort_param == "date":
            if dir_param == "desc":
                query = query.order_by(Event.start_date.desc())
            else:
                query = query.order_by(Event.start_date.asc())
        elif sort_param == "title":
            col = db.func.coalesce(Event.title, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "district":
            col = db.func.coalesce(Event.district_partner, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "school":
            query = query.outerjoin(School, Event.school == School.id)
            col = db.func.coalesce(School.name, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "educators":
            col = db.func.coalesce(Event.educators, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "presenters":
            col = db.func.coalesce(Event.professionals, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "cluster":
            col = db.func.coalesce(Event.career_cluster, "")
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "students":
            col = db.func.coalesce(Event.registered_student_count, 0)
            query = query.order_by(col.desc() if dir_param == "desc" else col.asc())
        elif sort_param == "status":
            query = query.order_by(
                Event.status.desc() if dir_param == "desc" else Event.status.asc()
            )
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Get unique career clusters for filter dropdown
        career_clusters = (
            db.session.query(Event.career_cluster)
            .filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.career_cluster.isnot(None),
                Event.career_cluster != "",
            )
            .distinct()
            .order_by(Event.career_cluster)
            .all()
        )
        career_clusters = [c[0] for c in career_clusters]

        # Get summary stats (scoped for tenant users)
        stats_query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        )
        stats_query = scope_events_query(stats_query, current_user)
        total_sessions = stats_query.count()

        total_students = (
            scope_events_query(
                db.session.query(func.sum(Event.registered_student_count)).filter(
                    Event.type == EventType.VIRTUAL_SESSION,
                    Event.start_date >= date_from,
                    Event.start_date <= date_to,
                ),
                current_user,
            ).scalar()
            or 0
        )

        # Get unique districts for filter dropdown
        districts = (
            db.session.query(Event.district_partner)
            .filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.district_partner.isnot(None),
                Event.district_partner != "",
            )
            .distinct()
            .order_by(Event.district_partner)
            .all()
        )
        districts = [d[0] for d in districts]

        # Get unique schools for filter dropdown (restricted by district when set)
        schools_base = (
            db.session.query(Event.school, School.name)
            .join(School, Event.school == School.id)
            .filter(
                Event.type == EventType.VIRTUAL_SESSION,
                Event.start_date >= date_from,
                Event.start_date <= date_to,
                Event.school.isnot(None),
                Event.school != "",
            )
        )
        schools_base = scope_events_query(schools_base, current_user)
        if district:
            schools_base = schools_base.filter(Event.district_partner == district)
        schools_rows = schools_base.distinct().order_by(School.name).all()
        schools = [{"id": row[0], "name": row[1] or row[0]} for row in schools_rows]

        # Per-district stats for the district strip (admin only)
        district_stats = []
        if current_user.is_admin:
            district_stats_raw = (
                db.session.query(
                    Event.district_partner,
                    func.count(Event.id),
                    func.coalesce(func.sum(Event.registered_student_count), 0),
                )
                .filter(
                    Event.type == EventType.VIRTUAL_SESSION,
                    Event.district_partner.isnot(None),
                    Event.district_partner != "",
                    Event.start_date >= date_from,
                    Event.start_date <= date_to,
                )
                .group_by(Event.district_partner)
                .order_by(func.count(Event.id).desc())
                .all()
            )
            district_stats = [
                {"name": row[0], "sessions": row[1], "students": int(row[2])}
                for row in district_stats_raw
            ]

        # Pass active tenants for admin Teacher Progress dropdown
        tenants = []
        if current_user.is_admin:
            tenants = Tenant.query.filter_by(is_active=True).order_by(Tenant.name).all()

        return render_template(
            "virtual/sessions.html",
            sessions=pagination,
            career_clusters=career_clusters,
            districts=districts,
            schools=schools,
            district_stats=district_stats,
            total_sessions=total_sessions,
            total_students=total_students,
            tenants=tenants,
            filters={
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "career_cluster": career_cluster,
                "district": district
                or user_district
                or "",  # Pre-select for tenant users
                "school": school,
                "status": status,
                "search": search,
                "sort": sort_param,
                "dir": dir_param,
            },
            # Phase D-3: Tenant context for UI adjustments
            is_tenant_user=is_tenant,
            user_district=user_district,
        )

    # =========================================================================
    # District Detail View
    # =========================================================================

    @virtual_bp.route("/sessions/district/<path:district_name>")
    @login_required
    @admin_required
    def virtual_sessions_district_detail(district_name):
        """
        District detail view showing sessions, teachers, and schools
        for a specific district.
        """
        from urllib.parse import unquote

        district_name = unquote(district_name)

        # Date range (same logic as main sessions view)
        today = datetime.now()
        if today.month >= 8:
            default_start = datetime(today.year, 8, 1)
            default_end = datetime(today.year + 1, 7, 31, 23, 59, 59)
        else:
            default_start = datetime(today.year - 1, 8, 1)
            default_end = datetime(today.year, 7, 31, 23, 59, 59)

        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")

        try:
            date_from = (
                datetime.strptime(date_from_str, "%Y-%m-%d")
                if date_from_str
                else default_start
            )
        except ValueError:
            date_from = default_start

        try:
            date_to = (
                datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                if date_to_str
                else default_end
            )
        except ValueError:
            date_to = default_end

        # Base filter for this district
        base_filter = [
            Event.type == EventType.VIRTUAL_SESSION,
            Event.district_partner == district_name,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        ]

        # Summary stats
        total_sessions = Event.query.filter(*base_filter).count()
        # Count experiences (total educator-session participations)
        educator_rows = (
            db.session.query(Event.educators)
            .filter(*base_filter, Event.educators.isnot(None), Event.educators != "")
            .all()
        )
        total_experiences = 0
        unique_educator_names = set()
        for (educators_str,) in educator_rows:
            for name in educators_str.split("; "):
                name = name.strip()
                if name:
                    total_experiences += 1
                    unique_educator_names.add(name)
        unique_classes = len(unique_educator_names)
        total_students = (
            db.session.query(func.coalesce(func.sum(Event.registered_student_count), 0))
            .filter(*base_filter)
            .scalar()
        )

        # Unique schools
        from models.school_model import School

        schools_query = (
            db.session.query(
                School.name,
                func.count(Event.id).label("session_count"),
                func.coalesce(func.sum(Event.registered_student_count), 0).label(
                    "student_count"
                ),
            )
            .join(Event, Event.school == School.id)
            .filter(*base_filter)
            .group_by(School.name)
            .order_by(func.count(Event.id).desc())
            .all()
        )
        schools = [
            {"name": s[0], "sessions": s[1], "students": int(s[2])}
            for s in schools_query
        ]

        # Also count schools from location field (fallback for unlinked)
        location_schools = (
            db.session.query(
                Event.location,
                func.count(Event.id),
                func.coalesce(func.sum(Event.registered_student_count), 0),
            )
            .filter(
                *base_filter,
                Event.school.is_(None),
                Event.location.isnot(None),
                Event.location != "",
            )
            .group_by(Event.location)
            .order_by(func.count(Event.id).desc())
            .all()
        )
        for s in location_schools:
            schools.append({"name": s[0], "sessions": s[1], "students": int(s[2])})

        # Unique teachers (from educators text field, semicolon-separated)
        educator_events = (
            db.session.query(Event.educators)
            .filter(*base_filter, Event.educators.isnot(None), Event.educators != "")
            .all()
        )
        teacher_counts = {}
        for (educators_str,) in educator_events:
            for name in educators_str.split("; "):
                name = name.strip()
                if name:
                    teacher_counts[name] = teacher_counts.get(name, 0) + 1
        teachers = sorted(
            [
                {"name": name, "sessions": count}
                for name, count in teacher_counts.items()
            ],
            key=lambda t: t["sessions"],
            reverse=True,
        )

        # Status breakdown
        status_breakdown = (
            db.session.query(
                Event.status,
                func.count(Event.id),
            )
            .filter(*base_filter)
            .group_by(Event.status)
            .all()
        )
        statuses = {(s[0].value if s[0] else "Unknown"): s[1] for s in status_breakdown}

        # Unique volunteers who participated in this district's sessions
        from models.contact import LocalStatusEnum
        from models.event import event_volunteers
        from models.volunteer import Volunteer

        volunteer_query = (
            db.session.query(Volunteer)
            .join(event_volunteers, event_volunteers.c.volunteer_id == Volunteer.id)
            .join(Event, Event.id == event_volunteers.c.event_id)
            .filter(*base_filter)
            .distinct()
            .all()
        )

        total_volunteers = len(volunteer_query)
        local_volunteers = sum(
            1 for v in volunteer_query if v.local_status == LocalStatusEnum.local
        )
        poc_volunteers = sum(1 for v in volunteer_query if v.is_people_of_color)
        local_pct = (
            round((local_volunteers / total_volunteers * 100), 1)
            if total_volunteers > 0
            else 0
        )
        poc_pct = (
            round((poc_volunteers / total_volunteers * 100), 1)
            if total_volunteers > 0
            else 0
        )

        # Build volunteers list with org info, and collect unique org names
        org_names = set()
        volunteers_list = []
        for v in volunteer_query:
            # Get org names from the many-to-many relationship
            vol_orgs = [org.name for org in v.organizations if org.name]
            for org_name in vol_orgs:
                org_names.add(org_name)
            volunteers_list.append(
                {
                    "id": v.id,
                    "name": f"{v.first_name or ''} {v.last_name or ''}".strip(),
                    "org": ", ".join(vol_orgs) if vol_orgs else "",
                    "is_local": v.local_status == LocalStatusEnum.local,
                    "is_poc": v.is_people_of_color,
                }
            )
        volunteers_list.sort(key=lambda x: x["name"])
        total_organizations = len(org_names)

        return render_template(
            "virtual/district_detail.html",
            district_name=district_name,
            total_sessions=total_sessions,
            unique_classes=unique_classes,
            total_experiences=total_experiences,
            total_students=int(total_students),
            total_schools=len(schools),
            total_teachers=len(teachers),
            total_volunteers=total_volunteers,
            local_volunteers=local_volunteers,
            local_pct=local_pct,
            poc_volunteers=poc_volunteers,
            poc_pct=poc_pct,
            total_organizations=total_organizations,
            volunteers_list=volunteers_list,
            schools=schools,
            teachers=teachers,
            statuses=statuses,
            date_from=date_from.strftime("%Y-%m-%d"),
            date_to=date_to.strftime("%Y-%m-%d"),
        )

    # =========================================================================
    # Flag Queue Routes (Phase D-1)
    # =========================================================================

    @virtual_bp.route("/flags")
    @login_required
    @admin_or_tenant_required
    def flag_queue():
        """
        Display the flag queue for reviewing event issues.

        Supports filtering by flag type, district, and resolution status.

        Phase D-3: District Admin Access (DEC-009)
        - Staff/admin users see all flags
        - Tenant users see only their district's flags
        """
        from models.event_flag import EventFlag, FlagType
        from services.flag_scanner import get_flag_summary

        # Determine user's district for scoping (Phase D-3)
        user_district = get_user_district_name(current_user)
        is_tenant = is_tenant_user(current_user)

        # Get filter parameters
        flag_type = request.args.get("type", "")
        district = request.args.get("district", "")
        show_resolved = request.args.get("resolved", "false") == "true"
        page = request.args.get("page", 1, type=int)
        per_page = 50

        # Build query
        query = db.session.query(EventFlag).join(Event)

        # Phase D-3: Apply tenant scoping for district admins
        if is_tenant and user_district:
            query = query.filter(Event.district_partner == user_district)

        if not show_resolved:
            query = query.filter(EventFlag.is_resolved == False)

        if flag_type:
            query = query.filter(EventFlag.flag_type == flag_type)

        if district:
            query = query.filter(Event.district_partner == district)

        # Order by created date, newest first
        query = query.order_by(EventFlag.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Get summary for sidebar (scoped for tenant users)
        summary = get_flag_summary(district_id=user_district if is_tenant else None)

        # Get unique districts for filter dropdown
        # For tenant users, only show their district
        if is_tenant and user_district:
            districts = [user_district]
        else:
            districts = (
                db.session.query(Event.district_partner)
                .filter(
                    Event.type == EventType.VIRTUAL_SESSION,
                    Event.district_partner.isnot(None),
                    Event.district_partner != "",
                )
                .distinct()
                .order_by(Event.district_partner)
                .all()
            )
            districts = [d[0] for d in districts]

        return render_template(
            "virtual/pathful/flags.html",
            flags=pagination,
            flag_types=FlagType.all_types(),
            summary=summary,
            districts=districts,
            filters={
                "type": flag_type,
                "district": district
                or user_district
                or "",  # Pre-select for tenant users
                "resolved": show_resolved,
            },
            # Phase D-3: Tenant context for UI adjustments
            is_tenant_user=is_tenant,
            user_district=user_district,
        )

    @virtual_bp.route("/flags/<int:flag_id>/resolve", methods=["POST"])
    @login_required
    @admin_required
    def resolve_flag(flag_id):
        """Resolve a single flag with optional notes."""
        from models.event_flag import EventFlag

        flag = EventFlag.query.get_or_404(flag_id)

        notes = request.form.get("notes", "")
        flag.resolve(notes=notes, resolved_by=current_user.id)
        db.session.commit()

        # Phase D-4: Log flag resolution
        from services.audit_service import log_flag_resolved

        log_flag_resolved(flag.event, flag.flag_type_display, resolution_notes=notes)

        flash(f"Flag resolved: {flag.flag_type_display}", "success")
        return redirect(url_for("virtual.flag_queue"))

    @virtual_bp.route("/flags/scan", methods=["POST"])
    @login_required
    @admin_required
    def run_flag_scan():
        """Manually trigger a flag scan on all virtual events."""
        from services.flag_scanner import scan_and_create_flags

        result = scan_and_create_flags(
            created_by=current_user.id,
            created_source="manual",
        )

        flash(
            f"Scan complete: {result['created_count']} new flags created "
            f"after scanning {result['scanned_count']} events.",
            "success",
        )
        return redirect(url_for("virtual.flag_queue"))
