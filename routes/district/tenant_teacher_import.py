"""
Tenant Teacher Import Routes
===========================

Routes for tenant-scoped teacher roster imports.
Allows Virtual Admins to import teacher data via Google Sheets or CSV.

Access Control:
- Requires authenticated user with tenant_id
- Requires VIRTUAL_ADMIN or ADMIN tenant role
"""

from datetime import datetime
from functools import wraps

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
from models.teacher_progress import TeacherProgress
from models.user import TenantRole
from services.teacher_import_service import TeacherImportService

teacher_import_bp = Blueprint(
    "teacher_import", __name__, url_prefix="/district/teacher-import"
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
    """Get the current academic year string (e.g., '2024-2025')."""
    today = datetime.now()
    if today.month >= 8:
        return f"{today.year}-{today.year + 1}"
    else:
        return f"{today.year - 1}-{today.year}"


def get_tenant_district_name():
    """Get the district name for the current user's tenant."""
    if not current_user.tenant_id:
        return None

    from models.tenant import Tenant

    tenant = Tenant.query.get(current_user.tenant_id)
    if not tenant:
        return None

    if tenant.district:
        return tenant.district.name

    return tenant.get_setting("linked_district_name") or tenant.name


@teacher_import_bp.route("/")
@login_required
@virtual_admin_required
def index():
    """Main teacher import page."""
    academic_year = request.args.get("year", get_current_academic_year())
    tenant_id = current_user.tenant_id
    district_name = get_tenant_district_name()

    # Get available years (current and next)
    current_year = get_current_academic_year()
    today = datetime.now()
    if today.month >= 8:
        next_year = f"{today.year + 1}-{today.year + 2}"
        prev_year = f"{today.year - 1}-{today.year}"
    else:
        next_year = f"{today.year}-{today.year + 1}"
        prev_year = f"{today.year - 2}-{today.year - 1}"

    available_years = [prev_year, current_year, next_year]

    # Get current teacher counts
    counts = TeacherImportService.get_teacher_count(tenant_id, academic_year)

    # Get existing teachers for this year
    teachers = (
        TeacherProgress.query.filter_by(
            tenant_id=tenant_id, academic_year=academic_year, is_active=True
        )
        .order_by(TeacherProgress.building, TeacherProgress.name)
        .all()
    )

    # Get schools for the tenant's district (for dropdown)
    schools = []
    if current_user.tenant_id:
        from models.tenant import Tenant

        tenant = Tenant.query.get(current_user.tenant_id)
        if tenant and tenant.district:
            schools = [s.name for s in tenant.district.schools.order_by("name").all()]

    # Common grade options
    grade_options = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

    return render_template(
        "district/teacher_import/index.html",
        academic_year=academic_year,
        available_years=available_years,
        district_name=district_name,
        counts=counts,
        teachers=teachers,
        schools=schools,
        grade_options=grade_options,
    )


@teacher_import_bp.route("/validate", methods=["POST"])
@login_required
@virtual_admin_required
def validate_data():
    """
    Validate import data before committing.
    Returns preview data or validation errors.
    """
    import_type = request.form.get("import_type", "csv")
    academic_year = request.form.get("academic_year", get_current_academic_year())

    if import_type == "google_sheet":
        sheet_url = request.form.get("sheet_url", "").strip()
        if not sheet_url:
            return jsonify(
                {"success": False, "errors": ["Please provide a Google Sheet URL."]}
            )

        # Extract sheet ID
        sheet_id = TeacherImportService.extract_sheet_id(sheet_url)
        if not sheet_id:
            return jsonify(
                {
                    "success": False,
                    "errors": [
                        "Invalid Google Sheet URL. Please provide a valid Google Sheets link."
                    ],
                }
            )

        # Read and validate
        df, error = TeacherImportService.read_google_sheet(sheet_id)
        if error:
            return jsonify({"success": False, "errors": [error]})

        validation = TeacherImportService.validate_dataframe(df)

    elif import_type == "csv":
        if "csv_file" not in request.files:
            return jsonify({"success": False, "errors": ["Please upload a CSV file."]})

        file = request.files["csv_file"]
        if file.filename == "":
            return jsonify({"success": False, "errors": ["No file selected."]})

        # Read and validate
        file_content = file.read()
        df, error = TeacherImportService.read_csv_file(file_content, file.filename)
        if error:
            return jsonify({"success": False, "errors": [error]})

        validation = TeacherImportService.validate_dataframe(df)
    else:
        return jsonify({"success": False, "errors": ["Invalid import type."]})

    if not validation.is_valid:
        return jsonify({"success": False, "errors": validation.errors})

    return jsonify(
        {
            "success": True,
            "row_count": validation.row_count,
            "preview": validation.preview_data,
            "warnings": validation.warnings,
        }
    )


@teacher_import_bp.route("/import", methods=["POST"])
@login_required
@virtual_admin_required
def do_import():
    """
    Perform the actual import after validation.
    """
    import_type = request.form.get("import_type", "csv")
    academic_year = request.form.get("academic_year", get_current_academic_year())
    tenant_id = current_user.tenant_id
    district_name = get_tenant_district_name()

    # Debug logging
    current_app.logger.info(
        f"Import attempt: type={import_type}, year={academic_year}, tenant_id={tenant_id}, district={district_name}"
    )

    # Handle global admins without tenant
    if not district_name:
        if current_user.is_admin:
            # For global admins, use a placeholder district name
            district_name = "Global Admin Import"
            current_app.logger.warning(
                f"Global admin {current_user.email} importing without tenant context"
            )
        else:
            flash("Could not determine district name. Please contact support.", "error")
            return redirect(url_for("teacher_import.index", year=academic_year))

    if import_type == "google_sheet":
        sheet_url = request.form.get("sheet_url", "").strip()
        current_app.logger.info(f"Google Sheet URL: {sheet_url}")
        if not sheet_url:
            flash("Please provide a Google Sheet URL.", "error")
            return redirect(url_for("teacher_import.index", year=academic_year))

        result = TeacherImportService.import_from_google_sheet(
            sheet_url=sheet_url,
            tenant_id=tenant_id,
            academic_year=academic_year,
            user_id=current_user.id,
            district_name=district_name,
        )

    elif import_type == "csv":
        if "csv_file" not in request.files:
            flash("Please upload a CSV file.", "error")
            return redirect(url_for("teacher_import.index", year=academic_year))

        file = request.files["csv_file"]
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("teacher_import.index", year=academic_year))

        file_content = file.read()
        result = TeacherImportService.import_from_csv(
            file_content=file_content,
            tenant_id=tenant_id,
            academic_year=academic_year,
            user_id=current_user.id,
            district_name=district_name,
        )
    else:
        flash("Invalid import type.", "error")
        return redirect(url_for("teacher_import.index", year=academic_year))

    if result.success:
        msg = (
            f"Import successful! Added: {result.records_added}, "
            f"Updated: {result.records_updated}, "
            f"Deactivated: {result.records_deactivated}"
        )
        if result.records_skipped > 0:
            msg += f", Skipped duplicates: {result.records_skipped}"
        flash(msg, "success")

        # Show warnings for skipped duplicates (limit to first 5 to avoid flooding)
        if result.warnings:
            warning_count = len(result.warnings)
            if warning_count <= 5:
                for warning in result.warnings:
                    flash(warning, "warning")
            else:
                for warning in result.warnings[:3]:
                    flash(warning, "warning")
                flash(
                    f"... and {warning_count - 3} more duplicate rows skipped.",
                    "warning",
                )
    else:
        flash(f"Import failed: {result.error_message}", "error")

    return redirect(url_for("teacher_import.index", year=academic_year))


@teacher_import_bp.route("/teachers")
@login_required
@virtual_admin_required
def list_teachers():
    """List all imported teachers for the tenant."""
    academic_year = request.args.get("year", get_current_academic_year())
    tenant_id = current_user.tenant_id
    show_inactive = request.args.get("show_inactive", "false") == "true"

    query = TeacherProgress.query.filter_by(
        tenant_id=tenant_id, academic_year=academic_year
    )

    if not show_inactive:
        query = query.filter_by(is_active=True)

    teachers = query.order_by(TeacherProgress.building, TeacherProgress.name).all()

    # Group by building
    buildings = {}
    for teacher in teachers:
        if teacher.building not in buildings:
            buildings[teacher.building] = []
        buildings[teacher.building].append(teacher)

    return render_template(
        "district/teacher_import/teachers.html",
        teachers=teachers,
        buildings=buildings,
        academic_year=academic_year,
        show_inactive=show_inactive,
        district_name=get_tenant_district_name(),
    )


@teacher_import_bp.route("/template")
@login_required
@virtual_admin_required
def download_template():
    """Download a CSV template for teacher imports."""
    import io

    from flask import Response

    # Create template CSV
    template = "Building,Name,Email,Grade\n"
    template += "Example Elementary,John Smith,john.smith@district.org,3\n"
    template += "Example Middle,Jane Doe,jane.doe@district.org,7\n"

    output = io.BytesIO()
    output.write(template.encode("utf-8"))
    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment;filename=teacher_import_template.csv"
        },
    )


@teacher_import_bp.route("/add", methods=["POST"])
@login_required
@virtual_admin_required
def add_single_teacher():
    """Add a single teacher via manual form entry."""
    academic_year = request.form.get("academic_year", get_current_academic_year())
    tenant_id = current_user.tenant_id
    district_name = get_tenant_district_name()

    # Get form fields
    building = request.form.get("building", "").strip()
    # Handle 'Other' option from dropdown
    if building == "__other__":
        building = request.form.get("building_other", "").strip()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    grade = request.form.get("grade", "").strip() or None

    # Validate required fields
    errors = []
    if not building:
        errors.append("Building is required.")
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    elif "@" not in email:
        errors.append("Please enter a valid email address.")

    if errors:
        for error in errors:
            flash(error, "error")
        return redirect(url_for("teacher_import.index", year=academic_year))

    # Check for existing teacher with same email in this academic year
    existing = TeacherProgress.query.filter_by(
        email=email,
        academic_year=academic_year,
        tenant_id=tenant_id,
    ).first()

    if existing:
        # Update existing teacher
        existing.building = building
        existing.name = name
        existing.grade = grade
        existing.is_active = True
        db.session.commit()
        flash(f"Updated existing teacher: {name}", "success")
    else:
        # Create new teacher
        teacher = TeacherProgress(
            academic_year=academic_year,
            virtual_year=academic_year,
            building=building,
            name=name,
            email=email,
            grade=grade,
            created_by=current_user.id,
        )
        teacher.tenant_id = tenant_id
        teacher.district_name = district_name
        teacher.is_active = True
        db.session.add(teacher)
        db.session.commit()
        flash(f"Successfully added teacher: {name}", "success")

    return redirect(url_for("teacher_import.index", year=academic_year))
