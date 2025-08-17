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

from routes.attendance.routes import attendance
from routes.auth.api import api_bp
from routes.auth.routes import auth_bp
from routes.bug_reports.routes import bug_reports_bp
from routes.calendar.routes import calendar_bp
from routes.client_projects.routes import client_projects_bp
from routes.events.pathway_events import pathway_events_bp
from routes.events.routes import events_bp
from routes.history.routes import history_bp
from routes.management.management import management_bp
from routes.organizations.routes import organizations_bp
from routes.reports import report_bp
from routes.students.routes import students_bp
from routes.teachers.routes import teachers_bp
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
    app.register_blueprint(calendar_bp)
    app.register_blueprint(bug_reports_bp)
    app.register_blueprint(client_projects_bp)

    app.register_blueprint(pathway_events_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.route("/")
    def index():
        """
        Main application index route.

        Returns:
            Rendered index template for the application homepage
        """
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
