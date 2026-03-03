"""
Bug report management route handlers.

Contains bug report listing, resolution, and deletion routes.
"""

from datetime import datetime, timezone

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import db
from models.bug_report import BugReport, BugReportType
from routes.utils import log_audit_action


def register_bug_report_routes(bp):
    """Register bug report routes on the management blueprint."""

    @bp.route("/bug-reports")
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

    @bp.route("/bug-reports/<int:report_id>/resolve", methods=["POST"])
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

    @bp.route("/bug-reports/<int:report_id>", methods=["DELETE"])
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

    @bp.route("/bug-reports/<int:report_id>/resolve-form")
    @login_required
    def get_resolve_form(report_id):
        if not current_user.is_admin:
            return jsonify({"error": "Unauthorized"}), 403

        report = BugReport.query.get_or_404(report_id)
        return render_template(
            "management/resolve_form.html", report_id=report_id, report=report
        )
