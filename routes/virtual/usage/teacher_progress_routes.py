"""
Teacher progress tracking and recruitment routes.

Contains routes for district teacher progress views, semester archiving,
Google Sheets management, progress export, recruitment, and teacher
matching. Registered on virtual_bp.
"""

from datetime import datetime, timedelta, timezone

from flask import (
    Response,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models import db
from models.contact import LocalStatusEnum
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventTeacher, EventType
from models.google_sheet import GoogleSheet
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.teacher import Teacher
from models.teacher_progress import TeacherProgress
from models.teacher_progress_archive import TeacherProgressArchive
from models.volunteer import EventParticipation, Volunteer
from routes.decorators import admin_required, district_scoped_required
from routes.reports.common import (
    generate_school_year_options,
    get_current_virtual_year,
    get_school_year_date_range,
    get_semester_dates,
    get_virtual_year_dates,
    is_cache_valid,
)
from routes.virtual.routes import virtual_bp

from .computation import _district_name_matches
from .exports import generate_teacher_progress_excel
from .teacher_progress import (
    compute_teacher_progress_tracking,
    compute_teacher_school_breakdown,
    match_teacher_progress_to_teachers,
    snapshot_semester_progress,
)


def load_teacher_progress_routes():
    @virtual_bp.route("/usage/usage/district/<district_name>/teacher-progress")
    @login_required
    @district_scoped_required
    def virtual_district_teacher_progress(district_name):
        """
        Show teacher progress tracking for specific teachers in Kansas City Kansas Public Schools.
        This view tracks progress for a predefined set of teachers to ensure district goals are met.

        Args:
            district_name: Name of the district (restricted to Kansas City Kansas Public Schools)

        Returns:
            Rendered template with teacher progress data
        """
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Get filter parameters
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get("year", default_virtual_year)

        # Calculate default date range
        # DEFAULT TO CURRENT SEMESTER if current virtual year is selected
        today = datetime.now()
        current_vy = get_current_virtual_year()

        # Defensive stripping to ensure match
        selected_vy_clean = str(selected_virtual_year).strip()
        current_vy_clean = str(current_vy).strip()

        if selected_vy_clean == current_vy_clean:
            # Check which semester we are in
            # Spring: Jan - Jun
            if 1 <= today.month <= 6:
                semester_type = "Spring"
            else:
                semester_type = "Fall"

            sem_start, sem_end = get_semester_dates(
                selected_virtual_year, semester_type
            )
            default_date_from = sem_start
            default_date_to = sem_end
        else:
            default_date_from, default_date_to = get_virtual_year_dates(
                selected_virtual_year
            )

        # Handle date parameters
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")
        view_mode_param = request.args.get("view", "live")

        # Start with calculated defaults (which are semester-based for current year)
        date_from = default_date_from
        date_to = default_date_to

        # Only override with URL params if they are explicitly provided AND valid
        user_provided_dates = date_from_str is not None or date_to_str is not None

        if user_provided_dates:
            if date_from_str:
                try:
                    parsed_date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
                    date_from = parsed_date_from.replace(hour=0, minute=0, second=0)
                except ValueError:
                    pass

            if date_to_str:
                try:
                    parsed_date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass

            # CRITICAL FIX: If viewing current year live data and the URL params
            # represent a FULL YEAR range (not semester), reset to semester defaults.
            # This handles the case where user navigates away and back with stale params.
            if view_mode_param == "live" and selected_vy_clean == current_vy_clean:
                # Check if the provided dates are the full virtual year (Aug 1 - Jul 31)
                vy_start, vy_end = get_virtual_year_dates(selected_virtual_year)
                is_full_year = (
                    date_from.month == vy_start.month
                    and date_from.day == vy_start.day
                    and date_to.month == vy_end.month
                    and date_to.day == vy_end.day
                )
                if is_full_year:
                    date_from = default_date_from
                    date_to = default_date_to

        if date_from > date_to:
            date_from = default_date_from
            date_to = default_date_to

        current_filters = {
            "year": selected_virtual_year,
            "date_from": date_from,
            "date_to": date_to,
        }

        # Get teacher progress tracking data
        teacher_progress_data = compute_teacher_progress_tracking(
            district_name, selected_virtual_year, date_from, date_to
        )

        # --- Semester Reset Logic ---
        # Automate the process:
        # 1. Determine "Previous Semester" relative to today
        # 2. Check if we have archived it
        # 3. If not, archive it

        today = datetime.now()
        current_vy = get_current_virtual_year()

        # Only trigger logic if we are viewing the current virtual year
        if selected_virtual_year == current_vy:
            prev_semester = None
            prev_sem_dates = None

            # If today is Jan (start of Spring), we just finished Fall
            if today.month == 1:
                prev_semester = f"Fall {selected_virtual_year.split('-')[0]}"
                prev_sem_dates = get_semester_dates(selected_virtual_year, "Fall")
            # If today is July (start of Fall), we just finished Spring
            elif today.month == 7:
                prev_semester = f"Spring {selected_virtual_year.split('-')[1]}"
                prev_sem_dates = get_semester_dates(selected_virtual_year, "Spring")

            if prev_semester and prev_sem_dates:
                # Check for existence of ANY archive for this semester/district to avoid redundant queries
                # We check one random record or just check logic.
                # Efficient check: query one archive record for this district's year/semester
                # Complex because Archive links to TeacherProgress.

                # Check if we have ANY archives for this semester
                # We can optimize by checking a dedicated log or just querying one.
                # Let's simple query: Check if archives exist for this virtual year + semester
                # AND linked to a teacher in this district (approximated by checking valid TeacherProgress)

                # Simplified: Just try to snapshot. The snapshot function checks for duplicates per teacher.
                # Rate limit: Only check/run this occasionally? Or rely on duplicate check.
                # To avoid performance hit on every page load, maybe only run if today.day <= 15?
                if today.day <= 15:
                    # Run generic check first to see if we should bother
                    exists = TeacherProgressArchive.query.filter_by(
                        semester_name=prev_semester, virtual_year=selected_virtual_year
                    ).first()

                    if not exists:
                        # Trigger snapshot
                        success, count = snapshot_semester_progress(
                            district_name,
                            selected_virtual_year,
                            prev_semester,
                            prev_sem_dates[0],
                            prev_sem_dates[1],
                        )
                        if success and count > 0:
                            flash(
                                f"Automatically archived {count} records for {prev_semester}.",
                                "info",
                            )

        # --- View Historical Data Logic ---
        # Allow user to select a semester view
        view_mode = request.args.get(
            "view", "live"
        )  # 'live', 'Fall 2024', 'Spring 2025'

        available_archives = (
            db.session.query(TeacherProgressArchive.semester_name)
            .filter_by(virtual_year=selected_virtual_year)
            .distinct()
            .all()
        )
        archive_options = sorted([r[0] for r in available_archives])

        if view_mode != "live" and view_mode in archive_options:
            # Overwrite teacher_progress_data with archived data
            # We need to reconstruct the nested dictionary structure from flat archive records
            # {School: {teachers: [data]}}

            archives = (
                TeacherProgressArchive.query.join(TeacherProgress)
                .filter(
                    TeacherProgressArchive.semester_name == view_mode,
                    TeacherProgressArchive.virtual_year == selected_virtual_year,
                    # Filter by district if needed (TeacherProgress handles scoping implicitly if we join?
                    # No, need to ensure the TP belongs to this district context.
                    # But compute_teacher_progress_tracking filtered by district implicitly via roster)
                )
                .all()
            )

            # Rebuild structure
            archived_data_map = {}  # School -> Data

            for arc in archives:
                tp = arc.teacher_progress
                school_name = tp.building

                if school_name not in archived_data_map:
                    archived_data_map[school_name] = {
                        "total_teachers": 0,
                        "goals_achieved": 0,
                        "goals_in_progress": 0,
                        "goals_not_started": 0,
                        "teachers": [],
                    }

                school_data = archived_data_map[school_name]
                school_data["total_teachers"] += 1

                if arc.status == "achieved":
                    school_data["goals_achieved"] += 1
                elif arc.status == "in_progress":
                    school_data["goals_in_progress"] += 1
                else:
                    school_data["goals_not_started"] += 1

                # Map archive to teacher dict format expected by template
                t_dict = {
                    "id": tp.id,
                    "name": tp.name,
                    "email": tp.email,
                    "grade": tp.grade,
                    "target_sessions": arc.target_sessions,
                    "completed_sessions": arc.completed_sessions,
                    "planned_sessions": arc.planned_sessions,
                    "progress_percentage": arc.progress_percentage,
                    "goal_status_class": arc.status,
                    "goal_status_text": arc.status_text,
                    "progress_class": arc.status,  # reuse status as class
                    "matched_teacher_id": tp.teacher_id,
                }
                school_data["teachers"].append(t_dict)

            teacher_progress_data = archived_data_map
            current_filters["view_mode"] = view_mode
        else:
            current_filters["view_mode"] = "live"

        virtual_year_options = generate_school_year_options()

        # Compute the last time virtual session data was updated (any event update)
        from sqlalchemy.sql import func as _sql_func

        from models.event import Event, EventType

        last_virtual_update = (
            db.session.query(_sql_func.max(Event.updated_at))
            .filter(Event.type == EventType.VIRTUAL_SESSION)
            .scalar()
        )

        return render_template(
            "virtual/teacher_progress/index.html",
            district_name=district_name,
            teacher_progress_data=teacher_progress_data,
            current_filters=current_filters,
            virtual_year_options=virtual_year_options,
            last_virtual_update=last_virtual_update,
            archive_options=archive_options,
        )

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/manual-archive",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def virtual_district_teacher_progress_manual_archive(district_name):
        """
        Manually trigger semester archive for a district.
        Useful if the automatic trigger was missed or feature was deployed mid-semester.
        """
        today = datetime.now()
        virtual_year = get_current_virtual_year()

        semester_name = None
        sem_dates = None

        if today.month == 1:  # Jan -> Archive Fall
            semester_name = f"Fall {virtual_year.split('-')[0]}"
            sem_dates = get_semester_dates(virtual_year, "Fall")
        elif today.month == 7:  # July -> Archive Spring
            semester_name = f"Spring {virtual_year.split('-')[1]}"
            sem_dates = get_semester_dates(virtual_year, "Spring")
        else:
            # Fall season (Aug-Dec) -> Archive previous Spring?
            # Spring season (Feb-Jun) -> Archive Fall?
            # For manual trigger, assume user wants to archive the *most recently completed* semester relative to today.
            if 8 <= today.month <= 12:
                # In Fall 2025. Previous complete was Spring 2025 (Part of 2024-2025 VY).
                prev_vy_start = int(virtual_year.split("-")[0]) - 1
                prev_vy = f"{prev_vy_start}-{prev_vy_start + 1}"
                semester_name = f"Spring {prev_vy.split('-')[1]}"
                sem_dates = get_semester_dates(prev_vy, "Spring")

            elif 2 <= today.month <= 6:
                # In Spring 2026. Previous complete was Fall 2025.
                semester_name = f"Fall {virtual_year.split('-')[0]}"
                sem_dates = get_semester_dates(virtual_year, "Fall")

        if not semester_name or not sem_dates:
            flash(
                "Could not determine a valid previous semester to archive at this time.",
                "error",
            )
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        success, count = snapshot_semester_progress(
            district_name,
            (
                virtual_year if "Fall" in semester_name else get_current_virtual_year()
            ),  # simplistic
            semester_name,
            sem_dates[0],
            sem_dates[1],
        )
        # Note: Virtual Year argument to snapshot needs to match the semester's VY.
        # Fixed logic below helper

        if success:
            flash(
                f"Successfully archived {count} records for {semester_name}.", "success"
            )
        else:
            flash("Failed to archive semester. Check system logs.", "error")

        return redirect(
            url_for(
                "virtual.virtual_district_teacher_progress", district_name=district_name
            )
        )

    def snapshot_semester_progress(
        district_name, virtual_year, semester_name, date_from, date_to
    ):
        """
        Snapshot teacher progress for a specific semester and archive it.
        """
        try:
            # 1. Compute stats for the semester
            print(
                f"INFO: Snapshotting {semester_name} for {district_name} ({date_from} - {date_to})"
            )
            progress_data = compute_teacher_progress_tracking(
                district_name, virtual_year, date_from, date_to
            )

            count = 0
            # 2. Iterate and save to archive
            for school_name, school_data in progress_data.items():
                for teacher_data in school_data.get("teachers", []):
                    # Find original TeacherProgress record
                    tp_id = teacher_data.get("id")
                    if not tp_id:
                        continue

                    # Check if already archived
                    existing = TeacherProgressArchive.query.filter_by(
                        teacher_progress_id=tp_id, semester_name=semester_name
                    ).first()

                    if existing:
                        continue

                    # Create archive
                    archive = TeacherProgressArchive(
                        teacher_progress_id=tp_id,
                        semester_name=semester_name,
                        academic_year=virtual_year,
                        virtual_year=virtual_year,
                        date_from=date_from,
                        date_to=date_to,
                        completed_sessions=teacher_data.get("completed_sessions", 0),
                        planned_sessions=teacher_data.get("planned_sessions", 0),
                        target_sessions=teacher_data.get("target_sessions", 1),
                        status=teacher_data.get(
                            "goal_status_class"
                        ),  # "achieved", "in_progress", "not_started"
                        status_text=teacher_data.get("goal_status_text"),
                        progress_percentage=teacher_data.get("progress_percentage", 0),
                        created_by=current_user.id if current_user else None,
                    )
                    db.session.add(archive)
                    count += 1

            db.session.commit()
            print(f"INFO: Successfully archived {count} records for {semester_name}")
            return True, count
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Failed to snapshot semester: {str(e)}")
            return False, 0

    @virtual_bp.route("/usage/district/<district_name>/teacher-progress/google-sheets")
    @login_required
    @admin_required
    def virtual_teacher_progress_google_sheets(district_name):
        """Manage Google Sheets for teacher progress tracking"""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Prevent district-scoped users from accessing management UI
        if current_user.scope_type == "district":
            flash("Access denied for district-scoped accounts.", "error")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        from models.district_model import District

        virtual_year = request.args.get("year", get_current_virtual_year())

        # Get all available districts for the dropdown
        districts = District.query.order_by(District.name).all()

        # Get Google Sheets for teacher progress tracking for this year
        # Filter by current district or global (None)
        # Assuming we want to show sheets created for this district specifically
        sheets_query = GoogleSheet.query.filter_by(
            academic_year=virtual_year, purpose="teacher_progress_tracking"
        )

        # If we are in a specific district context, filter for that district or global
        # (For now, matching exact name. In future, might want complex logic)
        # Note: We check if district_name matches.

        sheets = sheets_query.order_by(GoogleSheet.sheet_name).all()
        # Filter in python to support legacy None/Global sheets + specific district sheets
        # or update query to use OR condition if supported easily,
        # but filter_by doesn't support OR. Using simple list comprehension for safety or just showing all for now if safe.
        # Strict scoping: Show sheets matching district_name OR district_name is None

        filtered_sheets = [
            s
            for s in sheets
            if s.district_name == district_name or s.district_name is None
        ]

        return render_template(
            "virtual/deprecated/teacher_progress_google_sheets.html",
            sheets=filtered_sheets,
            district_name=district_name,
            districts=districts,  # Pass districts to template
            virtual_year=virtual_year,
            virtual_year_options=generate_school_year_options(),
        )

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/google-sheets/create",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def create_teacher_progress_google_sheet(district_name):
        """Create a new Google Sheet for teacher progress tracking"""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Block district-scoped users
        if current_user.scope_type == "district":
            flash("Access denied for district-scoped accounts.", "error")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        try:
            virtual_year = request.form.get("virtual_year")
            sheet_id = request.form.get("sheet_id")
            sheet_name = request.form.get("sheet_name")

            if not all([virtual_year, sheet_id, sheet_name]):
                flash("All fields are required.", "error")
                return redirect(
                    url_for(
                        "virtual.virtual_teacher_progress_google_sheets",
                        district_name=district_name,
                        year=virtual_year,
                    )
                )

            # Check if sheet already exists for this year
            existing_sheet = GoogleSheet.query.filter_by(
                academic_year=virtual_year,
                purpose="teacher_progress_tracking",
            ).first()

            if existing_sheet:
                flash(
                    f"A Google Sheet already exists for teacher progress tracking in {virtual_year}.",
                    "error",
                )
                return redirect(
                    url_for(
                        "virtual.virtual_teacher_progress_google_sheets",
                        district_name=district_name,
                        year=virtual_year,
                    )
                )

            district_name_form = request.form.get("district_name")  # Get from dropdown

            # Create new Google Sheet record
            new_sheet = GoogleSheet(
                academic_year=virtual_year,
                purpose="teacher_progress_tracking",
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                created_by=current_user.id,
                district_name=district_name_form if district_name_form else None,
            )

            db.session.add(new_sheet)
            db.session.commit()

            flash(
                f'Google Sheet "{sheet_name}" created successfully for teacher progress tracking.',
                "success",
            )
            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=virtual_year,
                )
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Error creating Google Sheet: {str(e)}", "error")
            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=virtual_year,
                )
            )

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/google-sheets/<int:sheet_id>/import",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def import_teacher_progress_data(district_name, sheet_id):
        """Import teacher progress data from Google Sheet"""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Block district-scoped users
        if current_user.scope_type == "district":
            flash("Access denied for district-scoped accounts.", "error")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        try:
            sheet = GoogleSheet.query.get_or_404(sheet_id)

            if sheet.purpose != "teacher_progress_tracking":
                flash("Invalid sheet type for teacher progress tracking.", "error")
                return redirect(
                    url_for(
                        "virtual.virtual_teacher_progress_google_sheets",
                        district_name=district_name,
                        year=sheet.academic_year,
                    )
                )

            # Import teacher progress data from Google Sheet
            import pandas as pd

            # Get the sheet ID from the GoogleSheet record
            sheet_id = sheet.sheet_id
            if not sheet_id:
                flash("No sheet ID found for this Google Sheet.", "error")
                return redirect(
                    url_for(
                        "virtual.virtual_teacher_progress_google_sheets",
                        district_name=district_name,
                        year=sheet.academic_year,
                    )
                )

            # Create CSV URL for Google Sheets - use export format which works better
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            )

            try:
                # Read data from Google Sheet
                df = pd.read_csv(csv_url)
            except Exception as e:
                # Try alternative URL format if the first one fails
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                try:
                    df = pd.read_csv(csv_url)
                except Exception as e2:
                    flash(f"Error reading Google Sheet: {str(e2)}", "error")
                    return redirect(
                        url_for(
                            "virtual.virtual_teacher_progress_google_sheets",
                            district_name=district_name,
                            year=sheet.academic_year,
                        )
                    )

            # Convert DataFrame to list of dictionaries
            # Expected columns: Building, Name, Email, Grade
            sample_teachers = []
            for _, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row.get("Building")) or pd.isna(row.get("Name")):
                    continue

                teacher_data = {
                    "building": str(row.get("Building", "")).strip(),
                    "name": str(row.get("Name", "")).strip(),
                    "email": str(row.get("Email", "")).strip(),
                    "grade": str(row.get("Grade", "")).strip(),
                }

                # Only add if we have required fields
                if (
                    teacher_data["building"]
                    and teacher_data["name"]
                    and teacher_data["email"]
                ):
                    sample_teachers.append(teacher_data)

            # Validate Import Data
            from utils.roster_import import import_roster, validate_import_data

            # Convert list of dicts to DataFrame for validation function compatibility
            # (or refactor validation to accept list of dicts - for now, reusing the logic)
            validation_df = pd.DataFrame(sample_teachers)
            validated_data, errors = validate_import_data(validation_df)

            if errors:
                flash(
                    f"Data Validation Errors found ({len(errors)}). Import cancelled.",
                    "error",
                )
                # In real UI, we might show the list of errors
                return redirect(
                    url_for(
                        "virtual.virtual_teacher_progress_google_sheets",
                        district_name=district_name,
                        year=sheet.academic_year,
                    )
                )

            # Perform Safe Import
            try:
                # Look up tenant by district name for multi-tenant support
                from models import Tenant

                tenant = Tenant.query.filter(
                    Tenant.district.has(name=district_name)
                ).first()
                tenant_id = tenant.id if tenant else None

                import_log = import_roster(
                    district_name=district_name,
                    academic_year=sheet.academic_year,
                    teacher_data=validated_data,
                    user_id=current_user.id,
                    sheet_id=str(sheet_id),
                    tenant_id=tenant_id,
                )

                flash(
                    f"Import successful! Added: {import_log.records_added}, "
                    f"Updated: {import_log.records_updated}, "
                    f"Deactivated: {import_log.records_deactivated}",
                    "success",
                )
            except Exception as e:
                flash(f"System Error during import: {str(e)}", "error")
                return redirect(url_for("virtual.virtual_usage"))

            # Logic below (db.session.commit) is now handled by import_roster logic
            # db.session.commit()

            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=sheet.academic_year,
                )
            )

        except Exception as e:
            flash(f"Error importing teacher progress data: {str(e)}", "error")
            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=sheet.academic_year,
                )
            )

    @virtual_bp.route("/usage/usage/district/<district_name>/teacher-progress/export")
    @login_required
    @district_scoped_required
    def virtual_district_teacher_progress_export(district_name):
        """
        Export teacher progress tracking data to Excel for Kansas City Kansas Public Schools.
        This exports both summary data and detailed teacher breakdown.

        Args:
            district_name: Name of the district (restricted to Kansas City Kansas Public Schools)

        Returns:
            Excel file with teacher progress data
        """
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Get filter parameters
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get("year", default_virtual_year)

        # Calculate default date range
        default_date_from, default_date_to = get_virtual_year_dates(
            selected_virtual_year
        )

        # Handle date parameters
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            except ValueError:
                date_from = default_date_from
        else:
            date_from = default_date_from

        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
            except ValueError:
                date_to = default_date_to
        else:
            date_to = default_date_to

        # Get teacher progress data
        teacher_progress_data = compute_teacher_progress_tracking(
            district_name, selected_virtual_year, date_from, date_to
        )

        if not teacher_progress_data:
            flash("No teacher progress data available for export.", "warning")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        # Generate Excel file
        excel_data = generate_teacher_progress_excel(
            teacher_progress_data,
            district_name,
            selected_virtual_year,
            date_from,
            date_to,
        )

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Teacher_Progress_Report_{timestamp}.xlsx"

        # Return Excel file
        return Response(
            excel_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/google-sheets/<int:sheet_id>/delete",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def delete_teacher_progress_google_sheet(district_name, sheet_id):
        """Delete a Google Sheet for teacher progress tracking"""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Block district-scoped users
        if current_user.scope_type == "district":
            flash("Access denied for district-scoped accounts.", "error")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        try:
            sheet = GoogleSheet.query.get_or_404(sheet_id)
            virtual_year = sheet.academic_year
            sheet_name = sheet.sheet_name

            db.session.delete(sheet)
            db.session.commit()

            flash(f'Google Sheet "{sheet_name}" deleted successfully.', "success")
            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=virtual_year,
                )
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting Google Sheet: {str(e)}", "error")
            return redirect(
                url_for(
                    "virtual.virtual_teacher_progress_google_sheets",
                    district_name=district_name,
                    year=virtual_year,
                )
            )

    @virtual_bp.route("/usage/recruitment")
    @login_required
    def virtual_recruitment():
        """
        Virtual Sessions Presenter Recruitment View

        Displays upcoming virtual events without assigned presenters to enable
        proactive recruitment of volunteers. Only accessible to Admin users and
        global-scoped regular users (not district or school-scoped users).

        Returns:
            Rendered template with filtered list of events needing presenters
        """
        # Access Control: Allow Admin (any scope) OR User with global scope
        # Deny: District-scoped or School-scoped users
        if not (current_user.is_admin or current_user.scope_type == "global"):
            flash(
                "Access denied. This feature is only available to administrators and global users.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Get filter parameters - Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get("year", default_virtual_year)

        # Calculate default date range based on virtual session year (Aug 1 - Jul 31)
        default_date_from, default_date_to = get_virtual_year_dates(
            selected_virtual_year
        )

        # Handle explicit date range parameters
        date_from_str = request.args.get("date_from")
        date_to_str = request.args.get("date_to")

        date_from = default_date_from
        date_to = default_date_to

        if date_from_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
                if (
                    default_date_from.date()
                    <= parsed_date_from.date()
                    <= default_date_to.date()
                ):
                    date_from = parsed_date_from.replace(hour=0, minute=0, second=0)
            except ValueError:
                pass

        if date_to_str:
            try:
                parsed_date_to = datetime.strptime(date_to_str, "%Y-%m-%d")
                if (
                    default_date_from.date()
                    <= parsed_date_to.date()
                    <= default_date_to.date()
                ):
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass

        if date_from > date_to:
            date_from = default_date_from
            date_to = default_date_to

        # Current timestamp for filtering future events
        # Use both timezone-aware and naive versions for compatibility
        now = datetime.now(timezone.utc)
        now_naive = datetime.now()  # For databases with naive datetime storage

        # Build query for virtual events without presenter assignments
        # Subquery to check for presenter assignments
        from sqlalchemy import and_
        from sqlalchemy import exists as sql_exists

        presenter_exists = sql_exists().where(
            and_(
                EventParticipation.event_id == Event.id,
                EventParticipation.participant_type == "Presenter",
            )
        )

        # Main query: Virtual events, future only, without presenters
        # Use OR condition to handle both timezone-aware and naive datetimes
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            or_(Event.start_date > now, Event.start_date > now_naive),
            ~presenter_exists,  # NOT EXISTS
        )

        # Apply date range filter
        query = query.filter(Event.start_date >= date_from, Event.start_date <= date_to)

        # Apply school filter
        school_id = request.args.get("school")
        if school_id:
            query = query.filter(Event.school == school_id)

        # Apply district filter (via school relationship)
        district_name = request.args.get("district")
        if district_name:
            query = query.join(School).filter(School.district_id == district_name)

        # Apply event type filter (allows filtering to specific virtual event subtypes if needed)
        event_type = request.args.get("event_type")
        if event_type:
            try:
                query = query.filter(Event.type == EventType(event_type))
            except (ValueError, KeyError):
                pass  # Invalid event type, ignore filter

        # Apply search filter across title and teacher names
        search_term = request.args.get("search", "").strip()
        if search_term:
            query = query.filter(
                or_(
                    Event.title.ilike(f"%{search_term}%"),
                    Event.educators.ilike(f"%{search_term}%"),
                )
            )

        # Sort by start date ascending (earliest events first = highest priority)
        query = query.order_by(Event.start_date.asc())

        # Execute query
        events = query.all()

        # Prepare event data with calculated fields
        event_data = []
        for event in events:
            # Ensure event.start_date is timezone-aware for comparison
            event_start = event.start_date
            if event_start.tzinfo is None:
                # If naive, assume UTC
                event_start = event_start.replace(tzinfo=timezone.utc)

            # Calculate days until event
            days_until = (event_start - now).days

            # Count tagged teachers
            teacher_count = EventTeacher.query.filter_by(event_id=event.id).count()

            # Get school and district info
            school = School.query.get(event.school) if event.school else None
            district_display = (
                school.district.name if school and school.district else "N/A"
            )
            school_name = school.name if school else "N/A"

            # Format date for display (use original event.start_date for formatting)
            try:
                formatted_date = event.start_date.strftime("%b %d, %Y %I:%M %p")
            except:
                formatted_date = str(event.start_date)

            event_data.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "start_date": event.start_date,
                    "school_name": school_name,
                    "district_name": district_display,
                    "teacher_count": teacher_count,
                    "days_until": days_until,
                    "formatted_date": formatted_date,
                    "status": (
                        event.status.value
                        if hasattr(event.status, "value")
                        else str(event.status)
                    ),
                }
            )

        # Prepare filter options for dropdowns
        # Get all schools with virtual events
        schools_query = (
            db.session.query(School)
            .join(Event)
            .filter(Event.type == EventType.VIRTUAL_SESSION)
            .distinct()
            .order_by(School.name)
        )
        schools = schools_query.all()

        # Get all districts with virtual events
        districts_query = (
            db.session.query(District)
            .join(School)
            .join(Event)
            .filter(Event.type == EventType.VIRTUAL_SESSION)
            .distinct()
            .order_by(District.name)
        )
        districts = districts_query.all()

        # Generate school year options
        school_years = generate_school_year_options()

        # Build filter options
        filter_options = {
            "schools": schools,
            "districts": districts,
            "school_years": school_years,
            "event_types": [et for et in EventType],  # All event types
        }

        # Current filters for template
        current_filters = {
            "year": selected_virtual_year,
            "date_from": date_from,
            "date_to": date_to,
            "school": school_id,
            "district": district_name,
            "event_type": event_type,
            "search": search_term,
        }

        return render_template(
            "virtual/recruitment.html",
            events=event_data,
            filter_options=filter_options,
            current_filters=current_filters,
            event_count=len(event_data),
        )

    @virtual_bp.route("/usage/district/<district_name>/teacher-progress/matching")
    @login_required
    @admin_required
    def virtual_teacher_progress_matching(district_name):
        """
        Admin interface for matching TeacherProgress entries to Teacher records.

        Args:
            district_name: Name of the district (restricted to Kansas City Kansas Public Schools)

        Returns:
            Rendered template with matching interface
        """
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            flash(
                "This view is only available for Kansas City Kansas Public Schools.",
                "error",
            )
            return redirect(url_for("virtual.virtual_usage"))

        # Block district-scoped users
        if current_user.scope_type == "district":
            flash("Access denied for district-scoped accounts.", "error")
            return redirect(
                url_for(
                    "virtual.virtual_district_teacher_progress",
                    district_name=district_name,
                )
            )

        virtual_year = request.args.get("year", get_current_virtual_year())
        show_unmatched_only = (
            request.args.get("unmatched_only", "false").lower() == "true"
        )
        search_query = request.args.get("search", "").strip()

        # Get all TeacherProgress entries for this virtual year
        query = TeacherProgress.query.filter_by(virtual_year=virtual_year)

        # Filter by unmatched only if requested
        if show_unmatched_only:
            query = query.filter_by(teacher_id=None)

        # Apply search filter if provided
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    TeacherProgress.name.ilike(search_pattern),
                    TeacherProgress.email.ilike(search_pattern),
                    TeacherProgress.building.ilike(search_pattern),
                )
            )

        teacher_progress_entries = query.order_by(
            TeacherProgress.building, TeacherProgress.name
        ).all()

        # Get all teachers for manual matching dropdown
        teachers = Teacher.query.order_by(Teacher.last_name, Teacher.first_name).all()

        # Get match statistics
        total_entries = TeacherProgress.query.filter_by(
            virtual_year=virtual_year
        ).count()
        matched_entries = (
            TeacherProgress.query.filter_by(virtual_year=virtual_year)
            .filter(TeacherProgress.teacher_id.isnot(None))
            .count()
        )
        unmatched_entries = total_entries - matched_entries

        return render_template(
            "virtual/teacher_progress/matching.html",
            district_name=district_name,
            teacher_progress_entries=teacher_progress_entries,
            teachers=teachers,
            virtual_year=virtual_year,
            virtual_year_options=generate_school_year_options(),
            show_unmatched_only=show_unmatched_only,
            search_query=search_query,
            total_entries=total_entries,
            matched_entries=matched_entries,
            unmatched_entries=unmatched_entries,
        )

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/matching/match",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def match_teacher_progress(district_name):
        """Manually match a TeacherProgress entry to a Teacher record."""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            return jsonify({"success": False, "message": "Invalid district"}), 400

        # Block district-scoped users
        if current_user.scope_type == "district":
            return jsonify({"success": False, "message": "Access denied"}), 403

        try:
            teacher_progress_id = request.json.get("teacher_progress_id")
            teacher_id = request.json.get("teacher_id")

            if not teacher_progress_id:
                return (
                    jsonify(
                        {"success": False, "message": "Missing teacher_progress_id"}
                    ),
                    400,
                )

            teacher_progress = TeacherProgress.query.get_or_404(teacher_progress_id)

            if teacher_id:
                # Match to teacher
                teacher = Teacher.query.get_or_404(teacher_id)
                teacher_progress.teacher_id = teacher.id
                message = f'Matched "{teacher_progress.name}" to "{teacher.first_name} {teacher.last_name}"'
            else:
                # Unmatch (set to None)
                teacher_progress.teacher_id = None
                message = f'Removed match for "{teacher_progress.name}"'

            db.session.commit()
            return jsonify({"success": True, "message": message})

        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 500

    @virtual_bp.route(
        "/usage/district/<district_name>/teacher-progress/matching/auto-match",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def auto_match_teacher_progress(district_name):
        """Run automatic matching for TeacherProgress entries."""
        # Restrict access to Kansas City Kansas Public Schools only
        if district_name != "Kansas City Kansas Public Schools":
            return jsonify({"success": False, "message": "Invalid district"}), 400

        # Block district-scoped users
        if current_user.scope_type == "district":
            return jsonify({"success": False, "message": "Access denied"}), 403

        try:
            virtual_year = request.json.get("virtual_year", get_current_virtual_year())
            stats = match_teacher_progress_to_teachers(virtual_year=virtual_year)

            return jsonify(
                {
                    "success": True,
                    "message": f"Auto-matching completed: {stats['matched_by_email']} by email, {stats['matched_by_name']} by name, {stats['unmatched']} unmatched",
                    "stats": stats,
                }
            )

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
