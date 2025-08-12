from flask import Blueprint

# Create main reports blueprint
report_bp = Blueprint("report", __name__)

from routes.reports.attendance import load_routes as load_attendance_routes
from routes.reports.contact import load_routes as load_contact_routes
from routes.reports.district_year_end import load_routes as load_district_routes
from routes.reports.first_time_volunteer import (
    load_routes as load_first_time_volunteer_routes,
)

# Import all report module functions
from routes.reports.index import load_routes
from routes.reports.organization_report import (
    load_routes as load_organization_report_routes,
)
from routes.reports.pathways import load_routes as load_pathways_routes
from routes.reports.recent_volunteers import (
    load_routes as load_recent_volunteers_routes,
)
from routes.reports.recruitment import load_routes as load_recruitment_routes
from routes.reports.virtual_session import load_routes as load_virtual_routes
from routes.reports.volunteer_thankyou import load_routes as load_volunteer_routes
from routes.reports.volunteers_by_event import (
    load_routes as load_volunteers_by_event_routes,
)

# Register all routes with the main blueprint
load_routes(report_bp)  # This registers the main /reports route
load_virtual_routes(report_bp)
load_volunteer_routes(report_bp)
load_organization_report_routes(report_bp)
load_district_routes(report_bp)

load_recruitment_routes(report_bp)
load_contact_routes(report_bp)
load_pathways_routes(report_bp)
load_attendance_routes(report_bp)
load_first_time_volunteer_routes(report_bp)
load_volunteers_by_event_routes(report_bp)
load_recent_volunteers_routes(report_bp)
