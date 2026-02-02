"""
Main Routes Configuration Module
==============================

This module serves as the central configuration point for all Flask blueprints
in the Volunteer Management System (VMS). It registers all application routes
and provides core template filters.

Key Features:
- Blueprint registration for all application modules
- Main index route handling
- Template filter configuration
- Centralized route management

Blueprint Modules:
- auth: Authentication and user management
- history: Activity history tracking
- volunteers: Volunteer management and operations
- organizations: Organization management
- events: Event management and scheduling
- virtual: Virtual session management
- reports: Reporting and analytics
- attendance: Attendance tracking and management
- management: Administrative functions
- calendar: Calendar functionality
- bug_reports: Bug reporting system
- client_projects: Client project management
- pathways: Educational pathways
- api: API endpoints for AJAX operations

Template Filters:
- format_date: Date formatting utility

Dependencies:
- Flask application instance
- All blueprint modules
- Template rendering system

Usage:
- Called during application initialization
- Registers all blueprints with the Flask app
- Sets up template filters for global use
"""

from flask import render_template

# District Suite Phase 2 - Public Event API (FR-API-101 to FR-API-108)
from routes.api.public_events import public_api_bp
from routes.attendance.routes import attendance
from routes.auth.api import api_bp
from routes.auth.routes import auth_bp
from routes.bug_reports.routes import bug_reports_bp
from routes.calendar.routes import calendar_bp
from routes.client_projects.routes import client_projects_bp

# District Suite Phase 2 - District Event Management
from routes.district import district_bp
from routes.district.tenant_teacher_import import teacher_import_bp
from routes.district.tenant_teacher_usage import teacher_usage_bp
from routes.email.routes import email_bp
from routes.events.pathway_events import pathway_events_bp
from routes.events.routes import events_bp
from routes.history.routes import history_bp
from routes.management.cache_management import cache_management_bp
from routes.management.management import management_bp
from routes.organizations.routes import organizations_bp
from routes.reports import report_bp
from routes.students.routes import students_bp
from routes.teachers.routes import teachers_bp
from routes.tenants import tenant_users_bp, tenants_bp

# Import virtual __init__ to register usage routes
from routes.virtual.routes import virtual_bp
from routes.volunteers.routes import volunteers_bp


def init_routes(app):
    """
    Initialize and register all application blueprints.

    This function registers all Flask blueprints with the main application,
    setting up the complete routing structure for the VMS system.

    Args:
        app: Flask application instance to register blueprints with

    Blueprints Registered:
        - auth_bp: Authentication routes (/login, /logout, /admin)
        - history_bp: History tracking routes (/history)
        - volunteers_bp: Volunteer management routes (/volunteers/*)
        - organizations_bp: Organization management routes (/organizations/*)
        - events_bp: Event management routes (/events/*)
        - virtual_bp: Virtual session routes (/virtual/*)
        - report_bp: Reporting routes (/reports/*)
        - attendance: Attendance tracking routes (/attendance/*)
        - management_bp: Administrative routes (/management/*)
        - calendar_bp: Calendar functionality routes (/calendar/*)
        - bug_reports_bp: Bug reporting routes (/bug_reports/*)
        - client_projects_bp: Client project routes (/client_projects/*)

        - pathway_events_bp: Pathway event routes (/pathway_events/*)
        - api_bp: API endpoints (/api/v1/*)
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(events_bp)

    app.register_blueprint(virtual_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(attendance)
    app.register_blueprint(management_bp)
    app.register_blueprint(cache_management_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(tenants_bp)
    app.register_blueprint(tenant_users_bp)  # Tenant user management
    app.register_blueprint(district_bp)  # District Suite Phase 2
    app.register_blueprint(teacher_import_bp)  # Tenant teacher imports
    app.register_blueprint(teacher_usage_bp)  # Tenant teacher usage dashboard
    app.register_blueprint(bug_reports_bp)
    app.register_blueprint(client_projects_bp)
    app.register_blueprint(email_bp)

    app.register_blueprint(pathway_events_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(public_api_bp)  # District Suite Public API

    @app.route("/")
    def index():
        """
        Main application index route.

        Redirects tenant users to their district dashboard.
        Returns Polaris homepage for non-tenant users.
        """
        from flask import redirect, url_for
        from flask_login import current_user

        from models import TenantRole

        # Redirect tenant users to their district dashboard (FR-TENANT-112)
        if current_user.is_authenticated and current_user.tenant_id:
            # Virtual Admin users default to virtual sessions page
            if current_user.tenant_role == TenantRole.VIRTUAL_ADMIN:
                return redirect(url_for("district.virtual_sessions"))
            return redirect(url_for("district.list_events"))

        return render_template("index.html")

    @app.template_filter("format_date")
    def format_date(date):
        """
        Template filter for formatting dates.

        Converts date objects to a human-readable format for display
        in templates. Returns empty string for None values.

        Args:
            date: Date object to format

        Returns:
            Formatted date string (e.g., "January 15, 2024") or empty string
        """
        if date:
            return date.strftime("%B %d, %Y")
        return ""
