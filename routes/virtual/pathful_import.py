"""
Pathful Import Routes Module
============================

This module provides routes and functions for importing Pathful export data
into the Polaris system, supporting US-304 (Pathful Import) and US-306 (Historical Data).

Key Features:
- Excel file upload and parsing
- Session/event matching and creation
- Teacher/volunteer matching
- Unmatched record tracking
- Idempotent import operations

Routes:
- POST /virtual/pathful/import - Upload and process Pathful export
- GET /virtual/pathful/import-history - View past imports
- GET /virtual/pathful/unmatched - View and manage unmatched records

Related Documentation:
- documentation/content/dev/pathful_import_deployment.md
- documentation/content/dev/pathful_import_recommendations.md
"""

from datetime import datetime, timedelta
from functools import wraps

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
from models.district_model import District
from models.event import Event, EventFormat, EventStatus, EventType
from models.pathful_import import (
    PathfulImportLog,
    PathfulImportType,
    PathfulUnmatchedRecord,
    PathfulUserProfile,
    ResolutionStatus,
    UnmatchedType,
)
from models.school_model import School
from models.teacher_progress import TeacherProgress
from models.user import TenantRole
from models.volunteer import Volunteer
from services.scoping import (
    get_user_district_name,
    is_staff_user,
    is_tenant_user,
    scope_events_query,
)

# Constants
REQUIRED_SESSION_COLUMNS = [
    "Session ID",
    "Title",
    "Date",
    "Status",
    "SignUp Role",
    "Name",
]

OPTIONAL_SESSION_COLUMNS = [
    "Duration",
    "User Auth Id",
    "School",
    "District or Company",
    "Partner",
    "Registered Student Count",
    "Attended Student Count",
    "Career Cluster",
    "Work Based Learning",
    "Series or Event Title",
    "State",
]

PARTNER_FILTER = "PREP-KC"  # Only import rows with this partner


def admin_required(f):
    """Decorator to require admin access for pathful import routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            flash("Admin access required for Pathful imports.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def admin_or_tenant_required(f):
    """
    Decorator to allow access for admins OR tenant admins/coordinators.

    Phase D-3: District Admin Access (DEC-009)
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        # Allow staff/admin users
        if is_staff_user(current_user):
            return f(*args, **kwargs)

        # Allow tenant admin/coordinator
        if is_tenant_user(current_user):
            if current_user.tenant_role in [
                TenantRole.ADMIN,
                TenantRole.COORDINATOR,
                TenantRole.VIRTUAL_ADMIN,
            ]:
                return f(*args, **kwargs)

        flash("You do not have permission to access this page.", "error")
        return redirect(url_for("index"))

    return decorated_function


def parse_pathful_date(date_value):
    """
    Parse date from Pathful export.

    Handles formats like:
    - '2018-05-17 00:00:00'
    - '2018-05-17'
    - datetime objects

    Args:
        date_value: Date value from Pathful export

    Returns:
        datetime or None
    """
    if pd.isna(date_value) or date_value is None:
        return None

    # Handle pandas Timestamp
    if hasattr(date_value, "to_pydatetime"):
        try:
            return date_value.to_pydatetime()
        except Exception:
            return None

    if isinstance(date_value, datetime):
        return date_value

    date_str = str(date_value).strip()

    # Handle NaT (Not a Time) string representation
    if date_str.lower() in ("nat", "nan", "none", ""):
        return None

    formats_to_try = [
        "%Y-%m-%d %H:%M:%S",  # 2018-05-17 00:00:00
        "%Y-%m-%d",  # 2018-05-17
        "%m/%d/%Y %H:%M:%S",  # 05/17/2018 00:00:00
        "%m/%d/%Y",  # 05/17/2018
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    current_app.logger.warning(f"Could not parse date: {date_value}")
    return None


def parse_name(full_name):
    """
    Parse full name into first and last name components.

    Handles common name patterns and prefixes (Dr., Mr., Mrs., etc.)

    Args:
        full_name: Full name string

    Returns:
        tuple: (first_name, last_name)
    """
    if not full_name or pd.isna(full_name):
        return "", ""

    name = str(full_name).strip()

    # Remove common prefixes
    prefixes = [
        "dr.",
        "dr ",
        "mr.",
        "mr ",
        "mrs.",
        "mrs ",
        "ms.",
        "ms ",
        "prof.",
        "prof ",
    ]
    name_lower = name.lower()
    for prefix in prefixes:
        if name_lower.startswith(prefix):
            name = name[len(prefix) :].strip()
            break

    parts = name.split()

    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return "", parts[0]  # Single name becomes last name
    else:
        first_name = " ".join(parts[:-1])
        last_name = parts[-1]
        return first_name, last_name


def safe_int(value, default=0):
    """Safely convert a value to int, handling NaN and None."""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_str(value):
    """Safely convert a value to string, handling NaN and None."""
    if pd.isna(value) or value is None:
        return ""
    return str(value).strip()


def upsert_district(district_name):
    """
    Find or create a District record by name.

    This ensures the District table is populated automatically during
    Pathful imports, providing normalized district data.

    Args:
        district_name: Name of the district from Pathful data

    Returns:
        District: Found or created District instance
    """
    if not district_name:
        return None

    # Look for existing district by name (case-insensitive)
    district = District.query.filter(
        func.lower(District.name) == func.lower(district_name)
    ).first()

    if district:
        return district

    # Create new district
    import re

    # Generate district code from name
    # Look for acronym in parentheses first
    acronym_match = re.search(r"\(([A-Z]+)\)", district_name)
    if acronym_match:
        code = acronym_match.group(1)
    else:
        # Create code from first word
        simplified = re.sub(
            r"\s*(School District|Public Schools|Schools)$",
            "",
            district_name,
            flags=re.IGNORECASE,
        )
        first_part = simplified.split(",")[0].strip()
        code = re.sub(r"[^A-Z0-9-]", "", first_part.upper().replace(" ", "-"))[:20]

    # Ensure code uniqueness
    base_code = code
    suffix = 1
    while District.query.filter(District.district_code == code).first():
        code = f"{base_code}-{suffix}"
        suffix += 1

    district = District(
        name=district_name,
        district_code=code,
        salesforce_id=None,  # Virtual imports don't have Salesforce IDs
    )
    db.session.add(district)
    db.session.flush()  # Get the ID

    current_app.logger.info(f"Created new District: {district_name} (code={code})")
    return district


def serialize_row_for_json(row):
    """
    Convert a pandas DataFrame row to a JSON-serializable dict.

    Handles pandas Timestamp, NaT, and other non-serializable types.

    Args:
        row: DataFrame row (Series or dict-like)

    Returns:
        dict: JSON-serializable dictionary
    """
    data = row.to_dict() if hasattr(row, "to_dict") else dict(row)

    result = {}
    for key, value in data.items():
        # Handle NaN/NaT/None
        if pd.isna(value) or value is None:
            result[key] = None
        # Handle pandas Timestamp
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        # Handle numpy types
        elif hasattr(value, "item"):
            result[key] = value.item()
        else:
            # Try to convert to string if not a basic type
            if not isinstance(value, (str, int, float, bool, list, dict)):
                result[key] = str(value)
            else:
                result[key] = value

    return result


def match_or_create_event(
    session_id, title, session_date, status_str, duration, career_cluster, import_log
):
    """
    Find existing event or create new one (idempotent).

    Matching priority:
    1. pathful_session_id (exact match)
    2. title + date (flexible match)

    When matched, the event status is updated if the incoming status
    represents a forward progression in the lifecycle:
        DRAFT -> REQUESTED -> CONFIRMED -> PUBLISHED -> COMPLETED
    Cancelled/No-Show are treated as terminal and always accepted.

    Args:
        session_id: Pathful Session ID
        title: Session title
        session_date: Session date
        status_str: Status string
        duration: Duration in minutes
        career_cluster: Career cluster category
        import_log: PathfulImportLog instance for tracking

    Returns:
        tuple: (Event, match_type) where match_type is 'matched' or 'created'
    """
    # Status progression order (higher index = further along in lifecycle)
    STATUS_ORDER = {
        EventStatus.DRAFT: 0,
        EventStatus.REQUESTED: 1,
        EventStatus.CONFIRMED: 2,
        EventStatus.PUBLISHED: 3,
        EventStatus.COMPLETED: 4,
    }

    def _should_update_status(current_status, new_status):
        """Return True if new_status is a forward progression from current_status."""
        # Terminal statuses (Cancelled, No Show, etc.) always accepted
        if new_status in (
            EventStatus.CANCELLED,
            EventStatus.NO_SHOW,
            EventStatus.SIMULCAST,
        ):
            return True
        cur_order = STATUS_ORDER.get(current_status, -1)
        new_order = STATUS_ORDER.get(new_status, -1)
        return new_order > cur_order

    def _update_matched_event(event, status_str, career_cluster):
        """Update fields on a matched event that may have changed since last import."""
        if career_cluster and not event.career_cluster:
            event.career_cluster = career_cluster

        # Update status if it has progressed
        if status_str:
            new_status = EventStatus.map_status(status_str)
            if _should_update_status(event.status, new_status):
                event.status = new_status
                event.original_status_string = status_str

    session_id_str = str(session_id) if session_id and not pd.isna(session_id) else None

    # Priority 1: Match by pathful_session_id
    if session_id_str:
        event = Event.query.filter(Event.pathful_session_id == session_id_str).first()
        if event:
            _update_matched_event(event, status_str, career_cluster)
            return event, "matched_by_session_id"

    # Priority 2: Match by title + date
    if title and session_date:
        event = Event.query.filter(
            func.lower(Event.title) == func.lower(title.strip()),
            func.date(Event.start_date) == session_date.date(),
            Event.type == EventType.VIRTUAL_SESSION,
        ).first()

        if event:
            # Update pathful_session_id if not set
            if session_id_str and not event.pathful_session_id:
                event.pathful_session_id = session_id_str
            _update_matched_event(event, status_str, career_cluster)
            return event, "matched_by_title_date"

    # No match: Create new event
    mapped_status = EventStatus.map_status(status_str)

    event = Event(
        title=title,
        start_date=session_date,
        end_date=session_date,  # Will be updated if duration is known
        duration=safe_int(duration, 60),
        type=EventType.VIRTUAL_SESSION,
        format=EventFormat.VIRTUAL,
        status=mapped_status,
        original_status_string=status_str,
        pathful_session_id=session_id_str,
        career_cluster=career_cluster,
        import_source="pathful_direct",
        session_host="PREPKC",
    )

    # Calculate end_date from duration
    if duration and session_date:
        event.end_date = session_date + timedelta(minutes=safe_int(duration, 60))

    db.session.add(event)
    db.session.flush()  # Get the event.id

    import_log.created_events += 1
    return event, "created"


def match_teacher(
    name, email, school_name, pathful_user_id, import_log, row_number, raw_data
):
    """
    Match a teacher from Pathful data to existing TeacherProgress records.

    Matching priority:
    1. pathful_user_id (exact match)
    2. email (normalized, case-insensitive)
    3. name + school (fuzzy match)

    Args:
        name: Teacher name
        email: Teacher email (may be empty)
        school_name: School name
        pathful_user_id: Pathful User Auth Id
        import_log: PathfulImportLog instance
        row_number: Row number for unmatched tracking
        raw_data: Full row data for unmatched record

    Returns:
        TeacherProgress or None
    """
    pathful_id_str = safe_str(pathful_user_id)
    email_normalized = safe_str(email).lower()
    name_str = safe_str(name)

    # Priority 1: Match by pathful_user_id
    if pathful_id_str:
        teacher_progress = TeacherProgress.query.filter(
            TeacherProgress.pathful_user_id == pathful_id_str
        ).first()
        if teacher_progress:
            import_log.matched_teachers += 1
            return teacher_progress

    # Priority 2: Match by email
    if email_normalized:
        teacher_progress = TeacherProgress.query.filter(
            func.lower(TeacherProgress.email) == email_normalized
        ).first()
        if teacher_progress:
            # Update pathful_user_id if not set
            if pathful_id_str and not teacher_progress.pathful_user_id:
                teacher_progress.pathful_user_id = pathful_id_str
            import_log.matched_teachers += 1
            return teacher_progress

    # Priority 3: Match by name (case-insensitive)
    if name_str:
        teacher_progress = TeacherProgress.query.filter(
            func.lower(TeacherProgress.name) == func.lower(name_str)
        ).first()
        if teacher_progress:
            if pathful_id_str and not teacher_progress.pathful_user_id:
                teacher_progress.pathful_user_id = pathful_id_str
            import_log.matched_teachers += 1
            return teacher_progress

    # No match - create unmatched record
    unmatched = PathfulUnmatchedRecord(
        import_log_id=import_log.id,
        row_number=row_number,
        raw_data=raw_data,
        unmatched_type=UnmatchedType.TEACHER,
        attempted_match_name=name_str,
        attempted_match_email=email_normalized,
        attempted_match_school=school_name,
    )
    if pathful_id_str:
        unmatched.attempted_match_session_id = pathful_id_str

    db.session.add(unmatched)
    import_log.unmatched_count += 1

    return None


def match_volunteer(
    name, email, organization_name, pathful_user_id, import_log, row_number, raw_data
):
    """
    Match a volunteer/professional from Pathful data.

    Matching priority:
    1. pathful_user_id (exact match)
    2. email (normalized, case-insensitive)
    3. name (fuzzy match by first + last)

    Args:
        name: Professional name
        email: Professional email (may be empty)
        organization_name: Organization/company name
        pathful_user_id: Pathful User Auth Id
        import_log: PathfulImportLog instance
        row_number: Row number for unmatched tracking
        raw_data: Full row data for unmatched record

    Returns:
        Volunteer or None
    """
    pathful_id_str = safe_str(pathful_user_id)
    email_normalized = safe_str(email).lower()
    name_str = safe_str(name)
    first_name, last_name = parse_name(name_str)

    # Priority 1: Match by pathful_user_id
    if pathful_id_str:
        volunteer = Volunteer.query.filter(
            Volunteer.pathful_user_id == pathful_id_str
        ).first()
        if volunteer:
            import_log.matched_volunteers += 1
            return volunteer

    # Priority 2: Match by email (using Email model)
    if email_normalized:
        from models.contact import Email

        email_record = Email.query.filter(
            func.lower(Email.email) == email_normalized
        ).first()
        if email_record and email_record.contact:
            volunteer = Volunteer.query.filter(
                Volunteer.id == email_record.contact_id
            ).first()
            if volunteer:
                # Update pathful_user_id if not set
                if pathful_id_str and not volunteer.pathful_user_id:
                    volunteer.pathful_user_id = pathful_id_str
                import_log.matched_volunteers += 1
                return volunteer

    # Priority 3: Match by name
    if first_name and last_name:
        volunteer = Volunteer.query.filter(
            func.lower(Volunteer.first_name) == func.lower(first_name),
            func.lower(Volunteer.last_name) == func.lower(last_name),
        ).first()
        if volunteer:
            if pathful_id_str and not volunteer.pathful_user_id:
                volunteer.pathful_user_id = pathful_id_str
            import_log.matched_volunteers += 1
            return volunteer

    # No match - create unmatched record
    unmatched = PathfulUnmatchedRecord(
        import_log_id=import_log.id,
        row_number=row_number,
        raw_data=raw_data,
        unmatched_type=UnmatchedType.VOLUNTEER,
        attempted_match_name=name_str,
        attempted_match_email=email_normalized,
        attempted_match_organization=organization_name,
    )
    if pathful_id_str:
        unmatched.attempted_match_session_id = pathful_id_str

    db.session.add(unmatched)
    import_log.unmatched_count += 1

    return None


def process_session_report_row(row, row_index, import_log, processed_events):
    """
    Process a single row from the Pathful Session Report.

    Args:
        row: DataFrame row
        row_index: Row index (1-based)
        import_log: PathfulImportLog instance
        processed_events: Dict to track processed events by session_id

    Returns:
        bool: True if row was processed successfully
    """
    try:
        # Extract key fields
        partner = safe_str(row.get("Partner", ""))
        signup_role = safe_str(row.get("SignUp Role", "")).lower()

        # Filter: Only PREP-KC partner
        if partner.upper() != PARTNER_FILTER:
            import_log.skipped_rows += 1
            return True

        # Filter: Skip students and parents
        if signup_role in ["student", "parent"]:
            import_log.skipped_rows += 1
            return True

        # Extract session data
        session_id = row.get("Session ID")
        title = safe_str(row.get("Title"))
        date_value = row.get("Date")
        status = safe_str(row.get("Status"))
        duration = row.get("Duration")
        career_cluster = safe_str(row.get("Career Cluster"))

        # Parse date
        session_date = parse_pathful_date(date_value)
        if not session_date:
            current_app.logger.warning(
                f"Row {row_index}: Could not parse date '{date_value}'"
            )
            import_log.error_count += 1
            return False

        if not title:
            current_app.logger.warning(f"Row {row_index}: Missing title")
            import_log.error_count += 1
            return False

        # Get or create event (idempotent)
        session_id_str = (
            str(session_id)
            if session_id and not pd.isna(session_id)
            else f"{title}_{session_date.date()}"
        )

        if session_id_str in processed_events:
            event = processed_events[session_id_str]
            match_type = "cached"
        else:
            event, match_type = match_or_create_event(
                session_id,
                title,
                session_date,
                status,
                duration,
                career_cluster,
                import_log,
            )
            processed_events[session_id_str] = event

            if (
                match_type == "matched_by_session_id"
                or match_type == "matched_by_title_date"
            ):
                import_log.updated_events += 1

        # Update student counts on event
        registered_students = safe_int(row.get("Registered Student Count"))
        attended_students = safe_int(row.get("Attended Student Count"))

        if registered_students > 0:
            event.registered_student_count = max(
                event.registered_student_count or 0, registered_students
            )
        if attended_students > 0:
            event.attended_student_count = max(
                event.attended_student_count or 0, attended_students
            )

        # Extract participant data
        name = safe_str(row.get("Name"))
        user_auth_id = row.get("User Auth Id")
        school = safe_str(row.get("School"))
        district_or_company = safe_str(row.get("District or Company"))

        # Convert row to dict for unmatched record storage
        raw_data = serialize_row_for_json(row)

        # Process based on role
        if signup_role == "educator":
            # Match teacher
            teacher = match_teacher(
                name=name,
                email="",  # Session report doesn't have email, only User Auth Id
                school_name=school,
                pathful_user_id=user_auth_id,
                import_log=import_log,
                row_number=row_index,
                raw_data=raw_data,
            )
            # If matched, we could link to event via EventTeacher here

            # Store educator name on event (accumulate if multiple)
            if name:
                current_educators = set(
                    filter(None, (event.educators or "").split("; "))
                )
                current_educators.add(name)
                event.educators = "; ".join(sorted(current_educators))

            # ONLY store district from Educator rows (Professional rows have company, not district)
            if district_or_company and not event.district_partner:
                event.district_partner = district_or_company
                # Also upsert and link to District model for proper FK relationship
                district_record = upsert_district(district_or_company)
                if district_record and district_record not in event.districts:
                    event.districts.append(district_record)

            # Store school info from Educator rows
            if school and school.upper() != "PREP-KC":  # Skip "PREP-KC" as school name
                if not event.school:
                    # Try to match school to existing School record
                    school_record = School.query.filter(
                        func.lower(School.name) == func.lower(school)
                    ).first()
                    if school_record:
                        event.school = school_record.id
                # Always store school name in location as fallback display
                if not event.location:
                    event.location = school

        elif signup_role == "professional":
            # Match volunteer
            volunteer = match_volunteer(
                name=name,
                email="",  # Session report doesn't have email
                organization_name=district_or_company,  # This is their company/employer
                pathful_user_id=user_auth_id,
                import_log=import_log,
                row_number=row_index,
                raw_data=raw_data,
            )
            # If matched, link volunteer to event
            if volunteer and volunteer not in event.volunteers:
                event.volunteers.append(volunteer)

            # Store professional name on event (accumulate if multiple)
            if name:
                current_professionals = set(
                    filter(None, (event.professionals or "").split("; "))
                )
                current_professionals.add(name)
                event.professionals = "; ".join(sorted(current_professionals))

        import_log.processed_rows += 1
        return True

    except Exception as e:
        current_app.logger.error(f"Row {row_index}: Error processing - {str(e)}")
        import_log.error_count += 1
        return False


def validate_session_report_columns(df):
    """
    Validate that required columns exist in the DataFrame.

    Args:
        df: pandas DataFrame

    Returns:
        tuple: (is_valid, missing_columns)
    """
    missing = []
    for col in REQUIRED_SESSION_COLUMNS:
        if col not in df.columns:
            missing.append(col)

    return len(missing) == 0, missing


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

            # Process rows
            processed_events = {}  # Cache events by session_id

            for index, row in df.iterrows():
                process_session_report_row(
                    row=row,
                    row_index=index + 1,  # 1-based row number
                    import_log=import_log,
                    processed_events=processed_events,
                )

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
            current_app.logger.error(f"Pathful import error: {str(e)}")
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
                current_app.logger.error(f"Error resolving record {record_id}: {e}")
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

                    # Auto-link to existing pathful_user_id records
                    if not profile.is_linked:
                        if signup_role == "Educator":
                            # Try to find TeacherProgress with this pathful_user_id
                            teacher_progress = TeacherProgress.query.filter_by(
                                pathful_user_id=pathful_user_id
                            ).first()
                            if teacher_progress:
                                profile.link_to_teacher_progress(teacher_progress.id)
                                linked_count += 1
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

            current_app.logger.error(f"User Report import failed: {str(e)}")
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
        status = request.args.get("status", "")
        search = request.args.get("search", "")

        # Base query - all virtual sessions
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to,
        )

        # Phase D-3: Apply tenant scoping for district admins
        query = scope_events_query(query, current_user)

        # Apply filters
        if career_cluster:
            query = query.filter(Event.career_cluster == career_cluster)

        if district:
            query = query.filter(Event.district_partner == district)

        if status:
            try:
                status_enum = EventStatus(status)
                query = query.filter(Event.status == status_enum)
            except ValueError:
                pass

        if search:
            # Search across multiple columns
            query = query.filter(
                db.or_(
                    Event.title.ilike(f"%{search}%"),
                    Event.career_cluster.ilike(f"%{search}%"),
                    Event.district_partner.ilike(f"%{search}%"),
                    Event.location.ilike(f"%{search}%"),  # School name fallback
                    Event.educators.ilike(f"%{search}%"),
                    Event.professionals.ilike(f"%{search}%"),
                    Event.pathful_session_id.ilike(f"%{search}%"),
                )
            )

        # Order and paginate with eager loading for related data
        from sqlalchemy.orm import joinedload

        query = query.options(
            joinedload(Event.school_obj),
            joinedload(Event.volunteers),
            joinedload(Event.teachers),
        ).order_by(Event.start_date.desc())
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

        return render_template(
            "virtual/sessions.html",
            sessions=pagination,
            career_clusters=career_clusters,
            districts=districts,
            total_sessions=total_sessions,
            total_students=total_students,
            filters={
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "career_cluster": career_cluster,
                "district": district
                or user_district
                or "",  # Pre-select for tenant users
                "status": status,
                "search": search,
            },
            # Phase D-3: Tenant context for UI adjustments
            is_tenant_user=is_tenant,
            user_district=user_district,
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
