from flask import render_template
from routes.auth.routes import auth_bp
from routes.history.routes import history_bp
from routes.volunteers.routes import volunteers_bp
from routes.organizations.routes import organizations_bp
from routes.job_board.routes import job_board_bp
from routes.upcoming_events.routes import upcoming_events_bp
from routes.events.routes import events_bp
from routes.virtual.routes import virtual_bp
from routes.reports import report_bp
from routes.attendance.routes import attendance
from routes.management.management import management_bp
from routes.job_board.filters import init_filters
from routes.calendar.routes import calendar_bp
from routes.playground.playground_route import playground_bp
from routes.bug_reports.routes import bug_reports_bp
from routes.client_projects.routes import client_projects_bp
from routes.pathways.routes_pathways import pathways_bp
from routes.auth.api import api_bp

def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(job_board_bp)
    app.register_blueprint(upcoming_events_bp)
    app.register_blueprint(virtual_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(attendance)
    app.register_blueprint(management_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(playground_bp)
    app.register_blueprint(bug_reports_bp)
    app.register_blueprint(client_projects_bp)
    app.register_blueprint(pathways_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    init_filters(app)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.template_filter('format_date')
    def format_date(date):
        if date:
            return date.strftime('%B %d, %Y')
        return ''