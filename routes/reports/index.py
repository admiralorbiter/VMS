"""
Reports Index Module
===================

This module provides the main reports landing page functionality for the
Volunteer Management System (VMS). It defines and displays all available
reports with their descriptions, categories, and navigation links.

Key Features:
- Centralized report catalog
- Categorized report organization
- Icon-based visual navigation
- Detailed report descriptions
- URL routing for report access

Report Categories:
- Virtual Events: Virtual session usage and statistics
- Volunteer Recognition: Thank you reports and volunteer metrics
- Organization Recognition: Organization contribution reports
- District Reports: Comprehensive district-level analytics
- Volunteer Reports: First-time volunteer and engagement metrics
- Recruitment: Volunteer recruitment tools and matching
- Event Management: Contact reports and event coordination
- Attendance: Attendance tracking and statistics

Available Reports:
1. Virtual Session Usage: District-based virtual session statistics
2. Volunteer Thank You Report: Top volunteers by hours and events
3. Organization Thank You Report: Organization contribution metrics
4. District Year-End Report: Comprehensive district analytics
5. First Time Volunteer Report: New volunteer engagement metrics
6. Recruitment Tools: Volunteer recruitment and matching tools
7. Event Contact Report: Upcoming events and volunteer contacts
8. Attendance Report: Event and district attendance statistics

Navigation Features:
- Icon-based visual identification
- Categorized report grouping
- Descriptive summaries for each report
- Direct URL routing to report pages

Dependencies:
- Flask Blueprint for routing
- Login required for all report access
- Template system for report display

Template Dependencies:
- reports/reports.html: Main reports landing page template

Security Features:
- Login required for all report access
- Centralized access control
- Consistent authentication requirements
"""

from flask import Blueprint, render_template
from flask_login import login_required

# Create blueprint
index_bp = Blueprint("reports_index", __name__)


def load_routes(bp):
    """
    Load report routes into the provided blueprint.

    This function defines the main reports landing page route and
    populates it with all available reports in the system.

    Args:
        bp: Flask Blueprint to register routes with

    Route:
        /reports: Main reports landing page with report catalog
    """

    @bp.route("/reports")
    @login_required
    def reports():
        """
        Display the main reports landing page.

        Shows all available reports organized by category with
        descriptions, icons, and navigation links. Provides a
        centralized hub for accessing all system reports.

        Report Structure:
            - title: Report display name
            - description: Detailed report description
            - icon: FontAwesome icon class for visual identification
            - url: Route to the specific report
            - category: Report category for organization

        Categories:
            - Virtual Events: Virtual session and online engagement
            - Volunteer Recognition: Thank you and appreciation reports
            - Organization Recognition: Organization contribution metrics
            - District Reports: District-level comprehensive analytics
            - Volunteer Reports: Volunteer engagement and participation
            - Recruitment: Volunteer recruitment and matching tools
            - Event Management: Event coordination and contact reports
            - Attendance: Attendance tracking and statistics

        Returns:
            Rendered reports template with available report catalog
        """
        # Define available reports
        available_reports = [
            {
                "title": "Virtual Session Usage",
                "description": "View virtual session statistics by district, including attendance rates and total participation.",
                "icon": "fa-solid fa-video",
                "url": "/reports/virtual/usage",
                "category": "Virtual Events",
            },
            {
                "title": "Volunteer Thank You Report",
                "description": "View top volunteers by hours and events for end of year thank you notes.",
                "icon": "fa-solid fa-heart",
                "url": "/reports/volunteer/thankyou",
                "category": "Volunteer Recognition",
            },
            {
                "title": "Organization Thank You Report",
                "description": "View organization contributions by sessions, hours, and volunteer participation.",
                "icon": "fa-solid fa-building",
                "url": "/reports/organization/thankyou",
                "category": "Organization Recognition",
            },
            {
                "title": "Organization Report",
                "description": "View detailed organization engagement with in-person and virtual experiences, student counts, and classroom breakdowns.",
                "icon": "fa-solid fa-chart-line",
                "url": "/reports/organization/report",
                "category": "Organization Recognition",
            },
            {
                "title": "District Year-End Report",
                "description": "View comprehensive year-end statistics for each district with event type filtering and detailed engagement data.",
                "icon": "fa-solid fa-chart-pie",
                "url": "/reports/district/year-end",
                "category": "District Reports",
            },
            {
                "title": "First Time Volunteer Report",
                "description": "View statistics on first-time volunteers, including participation and engagement metrics.",
                "icon": "fa-solid fa-user-plus",
                "url": "/reports/first-time-volunteer",
                "category": "Volunteer Reports",
            },
            {
                "title": "Recruitment Tools",
                "description": "Access various tools for volunteer recruitment and event matching.",
                "icon": "fa-solid fa-users",
                "url": "/reports/recruitment",
                "category": "Recruitment",
            },
            {
                "title": "Event Contact Report",
                "description": "View upcoming events and volunteer contact information.",
                "icon": "fa-solid fa-address-book",
                "url": "/reports/contact",
                "category": "Event Management",
            },
            {
                "title": "Volunteers by Event",
                "description": "Find volunteers who participated in selected event types (e.g., Career Fair, Data Viz) in a date range or school year; export to Excel.",
                "icon": "fa-solid fa-users",
                "url": "/reports/volunteers/by-event",
                "category": "Volunteer Reports",
            },
            # {
            #     'title': 'Pathway Report',
            #     'description': 'View pathway statistics including student participation, events, and contact engagement.',
            #     'icon': 'fa-solid fa-road',
            #     'url': '/reports/pathways',
            #     'category': 'Program Reports'
            # },
            {
                "title": "Attendance Report",
                "description": "View attendance statistics by event and district.",
                "icon": "fa-solid fa-calendar-check",
                "url": "/attendance/details",
                "category": "Attendance",
            },
        ]

        return render_template("reports/reports.html", reports=available_reports)
