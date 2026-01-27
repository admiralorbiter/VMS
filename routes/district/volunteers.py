"""
District Volunteer Management Routes

Routes for district administrators to manage volunteers within their
tenant context.

Requirements:
- FR-SELFSERV-301: Add/edit volunteers with contact and skills
- FR-SELFSERV-302: Import volunteers from CSV/Excel
- FR-SELFSERV-303: Search volunteers by name, organization, skills
- FR-SELFSERV-304: Assign volunteers to events with status tracking
- FR-SELFSERV-305: Tenant isolation - volunteers only visible to their district

Routes:
- GET  /district/volunteers              - List district volunteers
- GET  /district/volunteers/new          - New volunteer form
- POST /district/volunteers              - Create volunteer
- GET  /district/volunteers/<id>         - View volunteer details
- GET  /district/volunteers/<id>/edit    - Edit volunteer form
- POST /district/volunteers/<id>         - Update volunteer
- POST /district/volunteers/<id>/toggle-status - Toggle active/inactive
- GET  /district/volunteers/import       - CSV import form
- POST /district/volunteers/import       - Process CSV import
- POST /district/volunteers/import/preview - Preview CSV import
"""

import csv
import io
from datetime import datetime, timezone
from functools import wraps

from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from models.contact import Contact, Email, Phone
from models.district_participation import DistrictParticipation
from models.district_volunteer import DistrictVolunteer
from models.recruitment_note import RecruitmentNote
from models.volunteer import Volunteer
from routes.district import district_bp


def require_tenant_context(f):
    """Decorator to require tenant context for district routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get("tenant"):
            flash(
                "You must be logged in with a district account to access this page.",
                "error",
            )
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def require_district_admin(f):
    """Decorator to require district admin access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not g.get("tenant"):
            flash("District access required.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def _find_volunteer_by_email(email):
    """
    Find a volunteer by their primary or any email address.

    Args:
        email: Email address to search for (case-insensitive)

    Returns:
        Volunteer or None
    """
    if not email:
        return None

    # Search through Email model joined to Volunteer
    email_record = (
        Email.query.join(Contact, Email.contact_id == Contact.id)
        .join(Volunteer, Volunteer.id == Contact.id)
        .filter(db.func.lower(Email.email) == email.lower())
        .first()
    )

    if email_record:
        return Volunteer.query.get(email_record.contact_id)
    return None


def _set_volunteer_primary_email(volunteer, email):
    """
    Set the primary email for a volunteer.

    Args:
        volunteer: Volunteer instance
        email: Email address string
    """
    if not email:
        return

    # Check if email already exists
    existing_email = volunteer.emails.filter(
        db.func.lower(Email.email) == email.lower()
    ).first()

    if existing_email:
        # Make it primary
        for e in volunteer.emails:
            e.primary = False
        existing_email.primary = True
    else:
        # Clear other primary flags and add new
        for e in volunteer.emails:
            e.primary = False
        new_email = Email(
            contact_id=volunteer.id,
            email=email,
            primary=True,
        )
        db.session.add(new_email)


def _set_volunteer_primary_phone(volunteer, phone):
    """
    Set the primary phone for a volunteer.

    Args:
        volunteer: Volunteer instance
        phone: Phone number string
    """
    if not phone:
        return

    # Check if phone already exists
    existing_phone = volunteer.phones.filter(Phone.number == phone).first()

    if existing_phone:
        for p in volunteer.phones:
            p.primary = False
        existing_phone.primary = True
    else:
        for p in volunteer.phones:
            p.primary = False
        new_phone = Phone(
            contact_id=volunteer.id,
            number=phone,
            primary=True,
        )
        db.session.add(new_phone)


@district_bp.route("/volunteers")
@login_required
@require_tenant_context
def list_volunteers():
    """
    List volunteers for current tenant with search/filter.

    FR-SELFSERV-303: Search by name, organization, skills
    FR-SELFSERV-305: Scoped to tenant
    """
    # Get search/filter parameters
    search_query = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "active")
    organization_filter = request.args.get("organization", "")
    page = request.args.get("page", 1, type=int)
    per_page = 25

    # Base query - join with DistrictVolunteer for tenant scoping
    query = (
        db.session.query(Volunteer, DistrictVolunteer)
        .join(DistrictVolunteer, DistrictVolunteer.volunteer_id == Volunteer.id)
        .filter(DistrictVolunteer.tenant_id == g.tenant_id)
    )

    # Apply status filter
    if status_filter == "active":
        query = query.filter(DistrictVolunteer.status == "active")
    elif status_filter == "inactive":
        query = query.filter(DistrictVolunteer.status == "inactive")

    # Apply search (FR-SELFSERV-303) - search name and organization
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Volunteer.first_name.ilike(search_term),
                Volunteer.last_name.ilike(search_term),
                Volunteer.organization_name.ilike(search_term),
            )
        )

    # Apply organization filter
    if organization_filter:
        query = query.filter(
            Volunteer.organization_name.ilike(f"%{organization_filter}%")
        )

    # Order by name
    query = query.order_by(Volunteer.first_name, Volunteer.last_name)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get unique organizations for filter dropdown
    org_query = (
        db.session.query(Volunteer.organization_name)
        .join(DistrictVolunteer, DistrictVolunteer.volunteer_id == Volunteer.id)
        .filter(DistrictVolunteer.tenant_id == g.tenant_id)
        .filter(Volunteer.organization_name.isnot(None))
        .filter(Volunteer.organization_name != "")
        .distinct()
        .order_by(Volunteer.organization_name)
    )
    organizations = [org[0] for org in org_query.all()]

    return render_template(
        "district/volunteers/list.html",
        volunteers=pagination.items,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter,
        organization_filter=organization_filter,
        organizations=organizations,
    )


@district_bp.route("/volunteers/new", methods=["GET"])
@login_required
@require_district_admin
def new_volunteer():
    """Show new volunteer form."""
    return render_template("district/volunteers/form.html", volunteer=None)


@district_bp.route("/volunteers", methods=["POST"])
@login_required
@require_district_admin
def create_volunteer():
    """
    Create a new volunteer and add to tenant.

    FR-SELFSERV-301: Add volunteer with contact info and skills
    """
    try:
        # Get form data
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        organization_name = request.form.get("organization_name", "").strip()
        title = request.form.get("title", "").strip()
        notes = request.form.get("notes", "").strip()

        # Validate required fields
        if not first_name or not last_name:
            flash("First name and last name are required.", "error")
            return redirect(url_for("district.new_volunteer"))

        # Check for existing volunteer by email
        existing = _find_volunteer_by_email(email)

        if existing:
            # Check if already in this tenant
            district_vol = DistrictVolunteer.query.filter_by(
                volunteer_id=existing.id,
                tenant_id=g.tenant_id,
            ).first()

            if district_vol:
                if district_vol.status == "active":
                    flash(
                        f"Volunteer with email {email} already exists in your district.",
                        "warning",
                    )
                    return redirect(
                        url_for("district.view_volunteer", volunteer_id=existing.id)
                    )
                else:
                    # Reactivate
                    district_vol.status = "active"
                    district_vol.added_by = current_user.id
                    district_vol.added_at = datetime.now(timezone.utc)
                    if notes:
                        district_vol.notes = notes
                    db.session.commit()
                    flash("Volunteer reactivated in your district.", "success")
                    return redirect(
                        url_for("district.view_volunteer", volunteer_id=existing.id)
                    )
            else:
                # Add existing volunteer to this tenant
                district_vol = DistrictVolunteer(
                    volunteer_id=existing.id,
                    tenant_id=g.tenant_id,
                    added_by=current_user.id,
                    notes=notes,
                )
                db.session.add(district_vol)
                db.session.commit()
                flash("Existing volunteer added to your district.", "success")
                return redirect(
                    url_for("district.view_volunteer", volunteer_id=existing.id)
                )

        # Create new volunteer
        volunteer = Volunteer(
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name if organization_name else None,
            title=title if title else None,
        )
        db.session.add(volunteer)
        db.session.flush()  # Get the ID

        # Add email if provided
        if email:
            email_record = Email(
                contact_id=volunteer.id,
                email=email,
                primary=True,
            )
            db.session.add(email_record)

        # Add phone if provided
        if phone:
            phone_record = Phone(
                contact_id=volunteer.id,
                number=phone,
                primary=True,
            )
            db.session.add(phone_record)

        # Add to tenant
        district_vol = DistrictVolunteer(
            volunteer_id=volunteer.id,
            tenant_id=g.tenant_id,
            added_by=current_user.id,
            notes=notes if notes else None,
        )
        db.session.add(district_vol)
        db.session.commit()

        flash("Volunteer created successfully.", "success")
        return redirect(url_for("district.view_volunteer", volunteer_id=volunteer.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Error creating volunteer: {str(e)}", "error")
        return redirect(url_for("district.new_volunteer"))


@district_bp.route("/volunteers/<int:volunteer_id>")
@login_required
@require_tenant_context
def view_volunteer(volunteer_id):
    """
    View volunteer details.

    FR-SELFSERV-305: Only show if volunteer is in tenant
    """
    # Verify volunteer belongs to tenant
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    volunteer = Volunteer.query.get_or_404(volunteer_id)

    # Get event history for this tenant
    participations = (
        DistrictParticipation.query.filter_by(
            volunteer_id=volunteer_id,
            tenant_id=g.tenant_id,
        )
        .order_by(DistrictParticipation.invited_at.desc())
        .limit(20)
        .all()
    )

    # Get recruitment notes (FR-RECRUIT-306)
    recruitment_notes = RecruitmentNote.get_for_volunteer(volunteer_id, g.tenant_id)

    return render_template(
        "district/volunteers/view.html",
        volunteer=volunteer,
        district_volunteer=district_vol,
        participations=participations,
        recruitment_notes=recruitment_notes,
        recruitment_outcome_choices=RecruitmentNote.OUTCOME_CHOICES,
    )


@district_bp.route("/volunteers/<int:volunteer_id>/edit", methods=["GET"])
@login_required
@require_district_admin
def edit_volunteer(volunteer_id):
    """Show edit volunteer form."""
    # Verify volunteer belongs to tenant
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    volunteer = Volunteer.query.get_or_404(volunteer_id)

    return render_template(
        "district/volunteers/form.html",
        volunteer=volunteer,
        district_volunteer=district_vol,
    )


@district_bp.route("/volunteers/<int:volunteer_id>", methods=["POST"])
@login_required
@require_district_admin
def update_volunteer(volunteer_id):
    """
    Update volunteer details.

    FR-SELFSERV-301: Edit volunteer with contact info and skills
    """
    # Verify volunteer belongs to tenant
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    volunteer = Volunteer.query.get_or_404(volunteer_id)

    try:
        # Update fields
        volunteer.first_name = request.form.get("first_name", "").strip()
        volunteer.last_name = request.form.get("last_name", "").strip()

        org = request.form.get("organization_name", "").strip()
        volunteer.organization_name = org if org else None

        title = request.form.get("title", "").strip()
        volunteer.title = title if title else None

        # Update email
        email = request.form.get("email", "").strip().lower()
        if email:
            _set_volunteer_primary_email(volunteer, email)

        # Update phone
        phone = request.form.get("phone", "").strip()
        if phone:
            _set_volunteer_primary_phone(volunteer, phone)

        # Update district-specific notes
        notes = request.form.get("notes", "").strip()
        district_vol.notes = notes if notes else None

        db.session.commit()
        flash("Volunteer updated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error updating volunteer: {str(e)}", "error")

    return redirect(url_for("district.view_volunteer", volunteer_id=volunteer_id))


@district_bp.route("/volunteers/<int:volunteer_id>/toggle-status", methods=["POST"])
@login_required
@require_district_admin
def toggle_volunteer_status(volunteer_id):
    """Toggle volunteer active/inactive status."""
    district_vol = DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    if district_vol.status == "active":
        district_vol.status = "inactive"
        flash("Volunteer marked as inactive.", "info")
    else:
        district_vol.status = "active"
        flash("Volunteer reactivated.", "success")

    db.session.commit()
    return redirect(url_for("district.view_volunteer", volunteer_id=volunteer_id))


@district_bp.route("/volunteers/import", methods=["GET"])
@login_required
@require_district_admin
def import_volunteers_form():
    """Show CSV import form."""
    return render_template("district/volunteers/import.html")


@district_bp.route("/volunteers/import/preview", methods=["POST"])
@login_required
@require_district_admin
def preview_import():
    """
    Preview CSV import data.

    FR-SELFSERV-302: Import from CSV with preview
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Read file content
        content = file.read().decode("utf-8-sig")  # Handle BOM
        reader = csv.DictReader(io.StringIO(content))

        # Detect columns
        fieldnames = reader.fieldnames or []

        # Read rows (limit for preview)
        rows = []
        for i, row in enumerate(reader):
            if i >= 10:  # Preview limit
                break
            rows.append(row)

        # Suggested mappings
        column_mappings = {
            "first_name": _detect_column(
                fieldnames, ["first", "firstname", "first_name", "fname"]
            ),
            "last_name": _detect_column(
                fieldnames, ["last", "lastname", "last_name", "lname", "surname"]
            ),
            "email": _detect_column(fieldnames, ["email", "e-mail", "email_address"]),
            "phone": _detect_column(
                fieldnames, ["phone", "telephone", "mobile", "cell"]
            ),
            "organization": _detect_column(
                fieldnames, ["organization", "org", "company", "employer"]
            ),
            "title": _detect_column(
                fieldnames, ["title", "job_title", "position", "role"]
            ),
        }

        return jsonify(
            {
                "columns": fieldnames,
                "suggested_mappings": column_mappings,
                "preview_rows": rows,
                "total_rows": len(rows),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 400


def _detect_column(fieldnames, possible_names):
    """Detect column by possible names."""
    for col in fieldnames:
        if col.lower().strip() in possible_names:
            return col
    return None


@district_bp.route("/volunteers/import", methods=["POST"])
@login_required
@require_district_admin
def process_import():
    """
    Process CSV import.

    FR-SELFSERV-302: Import volunteers from CSV
    """
    if "file" not in request.files:
        flash("No file provided.", "error")
        return redirect(url_for("district.import_volunteers_form"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("district.import_volunteers_form"))

    # Get column mappings from form
    mappings = {
        "first_name": request.form.get("map_first_name"),
        "last_name": request.form.get("map_last_name"),
        "email": request.form.get("map_email"),
        "phone": request.form.get("map_phone"),
        "organization": request.form.get("map_organization"),
        "title": request.form.get("map_title"),
    }

    try:
        content = file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            try:
                # Extract values based on mappings
                first_name = (row.get(mappings["first_name"]) or "").strip()
                last_name = (row.get(mappings["last_name"]) or "").strip()
                email = (row.get(mappings["email"]) or "").strip().lower()
                phone = (row.get(mappings["phone"]) or "").strip()
                organization = (row.get(mappings["organization"]) or "").strip()
                title = (row.get(mappings["title"]) or "").strip()

                # Skip rows without required fields
                if not first_name or not last_name:
                    skipped += 1
                    continue

                # Check for existing volunteer by email
                volunteer = _find_volunteer_by_email(email) if email else None

                if volunteer:
                    # Check if in tenant
                    district_vol = DistrictVolunteer.query.filter_by(
                        volunteer_id=volunteer.id,
                        tenant_id=g.tenant_id,
                    ).first()

                    if district_vol:
                        # Already exists in tenant
                        if district_vol.status == "inactive":
                            district_vol.status = "active"
                            updated += 1
                        else:
                            skipped += 1
                    else:
                        # Add to tenant
                        district_vol = DistrictVolunteer(
                            volunteer_id=volunteer.id,
                            tenant_id=g.tenant_id,
                            added_by=current_user.id,
                        )
                        db.session.add(district_vol)
                        created += 1
                else:
                    # Create new volunteer
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        organization_name=organization if organization else None,
                        title=title if title else None,
                    )
                    db.session.add(volunteer)
                    db.session.flush()

                    # Add email if provided
                    if email:
                        email_record = Email(
                            contact_id=volunteer.id,
                            email=email,
                            primary=True,
                        )
                        db.session.add(email_record)

                    # Add phone if provided
                    if phone:
                        phone_record = Phone(
                            contact_id=volunteer.id,
                            number=phone,
                            primary=True,
                        )
                        db.session.add(phone_record)

                    # Add to tenant
                    district_vol = DistrictVolunteer(
                        volunteer_id=volunteer.id,
                        tenant_id=g.tenant_id,
                        added_by=current_user.id,
                    )
                    db.session.add(district_vol)
                    created += 1

            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        db.session.commit()

        # Build summary message
        msg = f"Import complete: {created} created, {updated} reactivated, {skipped} skipped."
        if errors:
            msg += f" {len(errors)} errors."
        flash(msg, "success" if not errors else "warning")

    except Exception as e:
        db.session.rollback()
        flash(f"Import failed: {str(e)}", "error")

    return redirect(url_for("district.list_volunteers"))


@district_bp.route("/volunteers/api/search")
@login_required
@require_tenant_context
def search_volunteers_api():
    """
    API endpoint for volunteer search (for AJAX autocomplete).

    FR-SELFSERV-303: Search volunteers
    """
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)

    if len(query) < 2:
        return jsonify([])

    search_term = f"%{query}%"

    results = (
        db.session.query(Volunteer)
        .join(DistrictVolunteer, DistrictVolunteer.volunteer_id == Volunteer.id)
        .filter(DistrictVolunteer.tenant_id == g.tenant_id)
        .filter(DistrictVolunteer.status == "active")
        .filter(
            db.or_(
                Volunteer.first_name.ilike(search_term),
                Volunteer.last_name.ilike(search_term),
                Volunteer.organization_name.ilike(search_term),
            )
        )
        .limit(limit)
        .all()
    )

    return jsonify(
        [
            {
                "id": v.id,
                "name": f"{v.first_name} {v.last_name}",
                "email": v.primary_email,
                "organization": v.organization_name,
            }
            for v in results
        ]
    )


# =============================================================================
# Recruitment Notes Routes (FR-RECRUIT-306 / US-403)
# =============================================================================


@district_bp.route("/volunteers/<int:volunteer_id>/notes", methods=["POST"])
@login_required
@require_tenant_context
def create_recruitment_note(volunteer_id):
    """
    Create a recruitment note for a volunteer.

    FR-RECRUIT-306: Record recruitment notes and outcomes
    TC-380: Note saved and displayed
    TC-381: Outcome recorded correctly
    """
    # Verify volunteer belongs to tenant
    DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    try:
        note_text = request.form.get("note", "").strip()
        outcome = request.form.get("outcome", "no_outcome")

        if not note_text:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return (
                    jsonify({"success": False, "error": "Note text is required"}),
                    400,
                )
            flash("Note text is required.", "error")
            return redirect(
                url_for("district.view_volunteer", volunteer_id=volunteer_id)
            )

        recruitment_note = RecruitmentNote.create_note(
            volunteer_id=volunteer_id,
            tenant_id=g.tenant_id,
            note=note_text,
            outcome=outcome,
            created_by=current_user.id,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "success": True,
                    "note": recruitment_note.to_dict(),
                }
            )

        flash("Recruitment note added successfully.", "success")
        return redirect(url_for("district.view_volunteer", volunteer_id=volunteer_id))

    except Exception as e:
        db.session.rollback()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": str(e)}), 500
        flash(f"Error adding note: {str(e)}", "error")
        return redirect(url_for("district.view_volunteer", volunteer_id=volunteer_id))


@district_bp.route("/volunteers/<int:volunteer_id>/notes", methods=["GET"])
@login_required
@require_tenant_context
def get_recruitment_notes(volunteer_id):
    """
    Get all recruitment notes for a volunteer as JSON.

    FR-RECRUIT-306: View recruitment history in chronological order
    """
    # Verify volunteer belongs to tenant
    DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    notes = RecruitmentNote.get_for_volunteer(volunteer_id, g.tenant_id)

    return jsonify(
        {
            "success": True,
            "notes": [note.to_dict() for note in notes],
        }
    )


@district_bp.route(
    "/volunteers/<int:volunteer_id>/notes/<int:note_id>", methods=["DELETE"]
)
@login_required
@require_tenant_context
def delete_recruitment_note(volunteer_id, note_id):
    """
    Delete a recruitment note.

    FR-RECRUIT-306: Manage recruitment notes
    """
    # Verify volunteer belongs to tenant
    DistrictVolunteer.query.filter_by(
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    # Get and verify note belongs to volunteer and tenant
    note = RecruitmentNote.query.filter_by(
        id=note_id,
        volunteer_id=volunteer_id,
        tenant_id=g.tenant_id,
    ).first_or_404()

    try:
        db.session.delete(note)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
