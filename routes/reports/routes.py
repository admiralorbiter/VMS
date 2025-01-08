from flask import Blueprint, render_template
from flask_login import login_required
from models.event import Event, EventType

report_bp = Blueprint('report', __name__)

@report_bp.route('/reports')
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
        # Add more reports here as they become available
    ]
    
    return render_template('reports/reports.html', reports=available_reports)

@report_bp.route('/reports/virtual/usage')
@login_required
def virtual_usage():
    # Get all virtual events
    virtual_events = Event.query.filter_by(type=EventType.VIRTUAL_SESSION).all()
    
    # Create a dictionary to store district stats
    district_stats = {}
    
    for event in virtual_events:
        for district in event.districts:
            if district.name not in district_stats:
                district_stats[district.name] = {
                    'total_sessions': 0,
                    'total_registered': 0,
                    'total_attended': 0,
                    'avg_attendance_rate': 0
                }
            
            stats = district_stats[district.name]
            stats['total_sessions'] += 1
            stats['total_registered'] += event.registered_count or 0
            stats['total_attended'] += event.attended_count or 0
    
    # Calculate average attendance rates
    for stats in district_stats.values():
        if stats['total_registered'] > 0:
            stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
    
    # Sort districts by total sessions
    sorted_districts = dict(sorted(
        district_stats.items(), 
        key=lambda x: x[1]['total_sessions'], 
        reverse=True
    ))
    
    return render_template('reports/virtual_usage.html', district_stats=sorted_districts)

