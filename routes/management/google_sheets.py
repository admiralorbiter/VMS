"""
Google Sheets management route handlers.

Contains CRUD operations for Google Sheet configurations.
"""

import os

from flask import current_app, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from models.google_sheet import GoogleSheet
from routes.decorators import admin_required, handle_route_errors
from routes.utils import log_audit_action
from utils.academic_year import get_academic_year_range


def register_google_sheets_routes(bp):
    """Register Google Sheets management routes on the management blueprint."""

    @bp.route("/google-sheets")
    @login_required
    @admin_required
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

    @bp.route("/google-sheets", methods=["POST"])
    @login_required
    @admin_required
    @handle_route_errors
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
        from utils.errors import ValidationError as AppValidationError

        data = request.get_json()
        academic_year = data.get("academic_year")
        sheet_id = data.get("sheet_id")

        if not all([academic_year, sheet_id]):
            raise AppValidationError("Academic year and sheet ID are required")

        existing = GoogleSheet.query.filter_by(
            academic_year=academic_year, purpose="virtual_sessions"
        ).first()
        if existing:
            raise AppValidationError(
                f"Virtual sessions sheet for academic year {academic_year} already exists"
            )

        new_sheet = GoogleSheet(
            academic_year=academic_year,
            sheet_id=sheet_id,
            created_by=current_user.id,
            purpose="virtual_sessions",
        )

        db.session.add(new_sheet)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Google Sheet for {academic_year} created successfully",
                "sheet": new_sheet.to_dict(),
            }
        )

    @bp.route("/google-sheets/<int:sheet_id>", methods=["PUT"])
    @login_required
    @admin_required
    @handle_route_errors
    def update_google_sheet(sheet_id):
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        data = request.get_json()
        if "sheet_id" in data:
            sheet.update_sheet_id(data["sheet_id"])
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": "Google Sheet updated successfully",
                "sheet": sheet.to_dict(),
            }
        )

    @bp.route("/google-sheets/<int:sheet_id>", methods=["DELETE"])
    @login_required
    @admin_required
    @handle_route_errors
    def delete_google_sheet(sheet_id):
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

    @bp.route("/google-sheets/<int:sheet_id>", methods=["GET"])
    @login_required
    @admin_required
    @handle_route_errors
    def get_google_sheet(sheet_id):
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        return jsonify({"success": True, "sheet": sheet.to_dict()})
