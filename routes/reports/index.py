from flask import Blueprint, render_template
from flask_login import login_required

# Create blueprint
index_bp = Blueprint('reports_index', __name__)

def load_routes(bp):
    @bp.route('/reports')
    @login_required
    def reports():
        # Define available reports
        available_reports = [
            {
                'title': 'Virtual Session Usage',
                'description': 'View virtual session statistics by district, including attendance rates and total participation.',
                'icon': 'fa-solid fa-video',
                'url': '/reports/virtual/usage',
                'category': 'Virtual Events'
            },
            {
                'title': 'Volunteer Thank You Report',
                'description': 'View top volunteers by hours and events for end of year thank you notes.',
                'icon': 'fa-solid fa-heart',
                'url': '/reports/volunteer/thankyou',
                'category': 'Volunteer Recognition'
            },
            {
                'title': 'Organization Thank You Report',
                'description': 'View organization contributions by sessions, hours, and volunteer participation.',
                'icon': 'fa-solid fa-building',
                'url': '/reports/organization/thankyou',
                'category': 'Organization Recognition'
            },
            {
                'title': 'District Year-End Report',
                'description': 'View comprehensive year-end statistics for each district.',
                'icon': 'fa-solid fa-chart-pie',
                'url': '/reports/district/year-end',
                'category': 'District Reports'
            },
            {
                'title': 'Recruitment Tools',
                'description': 'Access various tools for volunteer recruitment and event matching.',
                'icon': 'fa-solid fa-users',
                'url': '/reports/recruitment',
                'category': 'Recruitment'
            },
            {
                'title': 'Event Contact Report',
                'description': 'View upcoming events and volunteer contact information.',
                'icon': 'fa-solid fa-address-book',
                'url': '/reports/contact',
                'category': 'Event Management'
            },
            {
                'title': 'Pathway Report',
                'description': 'View pathway statistics including student participation, events, and contact engagement.',
                'icon': 'fa-solid fa-road',
                'url': '/reports/pathways',
                'category': 'Program Reports'
            }
        ]
        
        return render_template('reports/reports.html', reports=available_reports)
