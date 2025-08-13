"""
Bug Reports Routes Module
=========================

This module provides functionality for bug reporting and management
in the Volunteer Management System (VMS). It handles bug report submission,
form display, and administrative review of reports.

Key Features:
- Bug report form display
- Report submission with validation
- Administrative report listing
- Error handling and user feedback
- Report categorization and tracking

Main Endpoints:
- /bug-report/form: Display bug report form
- /bug-report/submit: Submit new bug report (POST)
- /bug-reports: Admin view of all reports

Report Types:
- Bug: General bug reports
- Feature Request: Feature enhancement requests
- UI/UX: User interface issues
- Performance: System performance issues
- Other: Miscellaneous reports

Security Features:
- Login required for all operations
- Admin-only access to report listing
- Form validation and sanitization
- Error handling with user feedback

Dependencies:
- Flask Blueprint for routing
- BugReport model for data persistence
- Database session for operations
- User authentication system

Models Used:
- BugReport: Bug report data and metadata
- BugReportType: Enumeration of report types
- User: Submitter information

Template Dependencies:
- bug_reports/form.html: Bug report submission form
- bug_reports/list.html: Admin report listing template
"""

from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import current_user, login_required

from models import db
from models.bug_report import BugReport, BugReportType

bug_reports_bp = Blueprint("bug_reports", __name__)


@bug_reports_bp.route("/bug-report/form")
@login_required
def get_form():
    """
    Display the bug report submission form.

    Returns the HTML template for users to submit bug reports,
    feature requests, or other feedback.

    Returns:
        Rendered bug report form template
    """
    return render_template("bug_reports/form.html")


@bug_reports_bp.route("/bug-report/submit", methods=["POST"])
@login_required
def submit_report():
    """
    Handle bug report submission.

    Processes form data and creates a new bug report in the database.
    Validates required fields and provides user feedback.

    Form Parameters:
        type: Report type (default: BUG)
        description: Detailed description of the issue
        page_url: URL where the issue occurred (optional)
        page_title: Title of the page where issue occurred (optional)

    Validation:
        - Description is required
        - User must be logged in
        - Report type must be valid

    Returns:
        JSON response with success/error status and message

    Raises:
        400: Missing required description
        500: Database or server error
    """
    try:
        # Get form data with defaults
        report_type = request.form.get("type", BugReportType.BUG)
        description = request.form.get("description")
        page_url = request.form.get("page_url", "")
        page_title = request.form.get("page_title", "")

        if not description:
            return (
                jsonify({"success": False, "message": "Description is required"}),
                400,
            )

        # Create new bug report
        report = BugReport(
            type=int(report_type),
            description=description,
            page_url=page_url,
            page_title=page_title,
            submitted_by_id=current_user.id,
        )

        db.session.add(report)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Thank you for your report. We will look into this.",
            }
        )

    except Exception as e:
        db.session.rollback()
        # Log the error for debugging (you should have proper logging set up)
        print(f"Error submitting bug report: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while submitting your report. Please try again.",
                }
            ),
            500,
        )


@bug_reports_bp.route("/bug-reports")
@login_required
def list_reports():
    """
    Admin view to list all bug reports.

    Provides administrative access to view all submitted bug reports
    in chronological order (newest first). Only accessible to admin users.

    Permission Requirements:
        - Admin access required

    Returns:
        Rendered template with all bug reports

    Raises:
        403: Unauthorized access attempt
    """
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    return render_template("bug_reports/list.html", reports=reports)
