"""
Bug Report Models Module
========================

This module defines the BugReport model and related enums for managing
bug reports and issue tracking in the VMS system.

Key Features:
- Bug report submission and tracking
- Issue categorization and classification
- User submission tracking
- Admin resolution management
- Page context preservation
- Resolution notes and tracking
- Automatic timestamp tracking

Database Table:
- bug_reports: Stores bug reports and issue tracking data

Bug Report Types:
- BUG: Something not working correctly
- DATA_ERROR: Incorrect information displayed
- OTHER: Other issues not fitting other categories

Report Management:
- User submission tracking
- Admin resolution workflow
- Page context preservation
- Resolution notes and documentation
- Timestamp tracking for audit trails

User Tracking:
- Submitted by user identification
- Resolved by admin tracking
- User relationship management
- Submission history tracking

Resolution Workflow:
- Bug report submission
- Admin review and classification
- Resolution assignment
- Resolution notes and documentation
- Resolution timestamp tracking

Usage Examples:
    # Create a new bug report
    bug_report = BugReport(
        type=BugReportType.BUG,
        description="Login page not loading properly",
        page_url="/login",
        page_title="Login",
        submitted_by_id=user.id
    )

    # Resolve a bug report
    bug_report.resolved = True
    bug_report.resolved_by_id = admin_user.id
    bug_report.resolution_notes = "Fixed CSS issue"
    bug_report.resolved_at = datetime.now(timezone.utc)

    # Get user's bug reports
    user_reports = user.bug_reports
"""

from datetime import datetime, timezone
from enum import IntEnum

from . import db


class BugReportType(IntEnum):
    """
    Enum for categorizing different types of bug reports.

    Provides standardized categories for organizing and prioritizing
    bug reports based on their nature and impact.

    Categories:
        - BUG: Something not working correctly (functional issues)
        - DATA_ERROR: Incorrect information displayed (data accuracy issues)
        - OTHER: Other issues not fitting other categories (miscellaneous)
    """

    BUG = 0  # Something not working correctly
    DATA_ERROR = 1  # Incorrect information displayed
    OTHER = 2  # Other issues


class BugReport(db.Model):
    """
    Model for tracking bug reports and issues in the VMS system.

    This model provides comprehensive bug tracking functionality including
    submission, categorization, resolution workflow, and audit trails.

    Database Table:
        bug_reports - Stores bug reports and issue tracking data

    Key Features:
        - Bug report submission and tracking
        - Issue categorization and classification
        - User submission tracking
        - Admin resolution management
        - Page context preservation
        - Resolution notes and tracking
        - Automatic timestamp tracking

    Report Types:
        - BUG: Functional issues and broken features
        - DATA_ERROR: Data accuracy and display issues
        - OTHER: Miscellaneous issues and requests

    Workflow Management:
        - User submission with context
        - Admin review and classification
        - Resolution assignment and tracking
        - Resolution documentation
        - Timestamp tracking for audit trails

    User Tracking:
        - submitted_by: User who submitted the report
        - resolved_by: Admin who resolved the issue
        - User relationship management
        - Submission and resolution history

    Context Preservation:
        - page_url: URL where issue was encountered
        - page_title: Page title for better context
        - description: Detailed issue description
        - resolution_notes: Admin resolution documentation

    Data Management:
        - Type categorization for prioritization
        - Resolution status tracking
        - Timestamp tracking for all actions
        - Notes and documentation storage
        - User relationship management
    """

    __tablename__ = "bug_reports"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, default=BugReportType.BUG)
    description = db.Column(db.Text, nullable=False)
    page_url = db.Column(
        db.String(500), nullable=False
    )  # Store which page it was reported from
    page_title = db.Column(db.String(200))  # Store the page title for better context

    # User who submitted the report
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submitted_by = db.relationship(
        "User",
        foreign_keys=[submitted_by_id],
        backref=db.backref("bug_reports", lazy=True),
    )

    # Admin fields
    resolved = db.Column(db.Boolean, default=False)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolved_by = db.relationship(
        "User",
        foreign_keys=[resolved_by_id],
        backref=db.backref("resolved_bug_reports", lazy=True),
    )
    resolution_notes = db.Column(db.Text)

    # Automatic timestamps for audit trail (timezone-aware, Python-side defaults)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
