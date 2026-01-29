"""
District Settings Routes

Routes for district administrators to manage tenant settings,
including API key rotation.

Requirements:
- FR-API-106: District administrators can rotate their API key
"""

from flask import current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from routes.district import district_bp
from routes.district.events import require_district_admin, require_tenant_context


@district_bp.route("/settings")
@login_required
@require_tenant_context
def settings():
    """Display tenant settings page."""
    return render_template(
        "district/settings.html",
        tenant=g.tenant,
        page_title=f"Settings - {g.tenant.name}",
    )


@district_bp.route("/settings/api-key", methods=["POST"])
@login_required
@require_district_admin
def rotate_api_key():
    """
    Generate a new API key (FR-API-106).

    The old key is immediately invalidated.
    The new key is displayed once and cannot be retrieved again.
    """
    tenant = g.tenant

    try:
        # Generate new key (this revokes the old one)
        new_key = tenant.generate_api_key()
        db.session.commit()

        current_app.logger.info(
            f"API key rotated for tenant {tenant.slug} by user {current_user.id}"
        )

        # Flash the new key - user must copy it now
        flash(
            f"New API key generated! Copy it now, it won't be shown again: {new_key}",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rotating API key: {e}")
        flash("An error occurred while generating the API key.", "error")

    return redirect(url_for("district.settings"))


@district_bp.route("/settings/cors", methods=["POST"])
@login_required
@require_district_admin
def update_cors_origins():
    """Update allowed CORS origins for API."""
    tenant = g.tenant

    try:
        # Get origins from form (one per line)
        origins_text = request.form.get("origins", "").strip()
        origins = [
            origin.strip() for origin in origins_text.split("\n") if origin.strip()
        ]

        tenant.set_allowed_origins_list(origins)
        db.session.commit()

        current_app.logger.info(
            f"CORS origins updated for tenant {tenant.slug}: {origins}"
        )

        flash("Allowed origins updated successfully!", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating CORS origins: {e}")
        flash("An error occurred while updating origins.", "error")

    return redirect(url_for("district.settings"))
