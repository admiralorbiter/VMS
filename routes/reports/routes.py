from flask import Blueprint, render_template, request
from flask_login import login_required
from models.event import Event, EventType, EventStatus
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models.event import db

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
    # Get filter parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    career_cluster = request.args.get('career_cluster')
    school = request.args.get('school')
    district = request.args.get('district')
    
    # Base query
    query = Event.query.filter_by(
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.COMPLETED
    )
    
    # Apply filters
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Event.start_date >= date_from)
        except ValueError:
            pass
            
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Event.start_date <= date_to)
        except ValueError:
            pass
            
    if career_cluster:
        query = query.filter(Event.series.ilike(f'%{career_cluster}%'))
        
    if school:
        query = query.filter(Event.school.ilike(f'%{school}%'))
        
    if district:
        query = query.filter(Event.district_partner.ilike(f'%{district}%'))
    
    # Get all events after filtering
    virtual_events = query.all()
    
    # Get unique values for filter dropdowns
    all_clusters = db.session.query(Event.series).distinct().all()
    all_schools = db.session.query(Event.school).distinct().all()
    all_districts = db.session.query(Event.district_partner).distinct().all()
    
    filter_options = {
        'career_clusters': sorted([c[0] for c in all_clusters if c[0]]),
        'schools': sorted([s[0] for s in all_schools if s[0]]),
        'districts': sorted([d[0] for d in all_districts if d[0]])
    }
    
    # Create a dictionary to store district stats
    district_stats = {}
    
    for event in virtual_events:
        district_name = event.district_partner or 'Unassigned'
        
        if district_name not in district_stats:
            district_stats[district_name] = {
                'total_sessions': 0,
                'total_registered': 0,
                'total_attended': 0,
                'avg_attendance_rate': 0,
                'total_duration': 0,
                'schools': set(),
                'educators': set(),
                'career_clusters': set()
            }
        
        stats = district_stats[district_name]
        stats['total_sessions'] += 1
        stats['total_registered'] += event.registered_count or 0
        stats['total_attended'] += event.attended_count or 0
        stats['total_duration'] += event.duration or 0
        
        if event.school:
            stats['schools'].add(event.school)
        if event.educator_name:
            stats['educators'].add(event.educator_name)
        if event.series:
            stats['career_clusters'].add(event.series)
    
    # Calculate averages and convert sets to counts
    for stats in district_stats.values():
        if stats['total_registered'] > 0:
            stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
        stats['avg_duration'] = stats['total_duration'] / stats['total_sessions'] if stats['total_sessions'] > 0 else 0
        stats['school_count'] = len(stats['schools'])
        stats['educator_count'] = len(stats['educators'])
        stats['career_cluster_count'] = len(stats['career_clusters'])
        
        # Clean up sets before sending to template
        del stats['schools']
        del stats['educators']
        del stats['career_clusters']
    
    # Sort districts by total sessions
    sorted_districts = dict(sorted(
        district_stats.items(), 
        key=lambda x: x[1]['total_sessions'], 
        reverse=True
    ))
    
    return render_template(
        'reports/virtual_usage.html',
        district_stats=sorted_districts,
        filter_options=filter_options,
        current_filters={
            'date_from': date_from,
            'date_to': date_to,
            'career_cluster': career_cluster,
            'school': school,
            'district': district
        }
    )

