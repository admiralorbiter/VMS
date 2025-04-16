from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract

from models.event import Event, EventType, EventStatus
from models import db

# Create blueprint
virtual_bp = Blueprint('virtual', __name__)

def load_routes(bp):
    @bp.route('/reports/virtual/usage')
    @login_required
    def virtual_usage():
        # Get filter parameters with explicit year handling
        year = int(request.args.get('year', '2024'))  # Default to 2024
        
        # Handle date range
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        if date_from_str and date_to_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                if date_from.year != year or date_to.year != year:
                    date_from = datetime(year, 1, 1)
                    date_to = datetime(year, 12, 31)
            except ValueError:
                date_from = datetime(year, 1, 1)
                date_to = datetime(year, 12, 31)
        else:
            date_from = datetime(year, 1, 1)
            date_to = datetime(year, 12, 31)

        current_filters = {
            'year': year,
            'date_from': date_from,
            'date_to': date_to,
            'career_cluster': request.args.get('career_cluster'),
            'school': request.args.get('school'),
            'district': request.args.get('district')
        }
        
        # Base query with date range filter
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        
        # Apply additional filters
        if current_filters['career_cluster']:
            query = query.filter(Event.series.ilike(f'%{current_filters["career_cluster"]}%'))
        if current_filters['school']:
            query = query.filter(Event.school.ilike(f'%{current_filters["school"]}%'))
        if current_filters['district']:
            query = query.filter(Event.district_partner.ilike(f'%{current_filters["district"]}%'))
        
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
        
        # Create district stats
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
            if event.educators:
                stats['educators'].add(event.educators)
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
            current_filters=current_filters
        )

    @bp.route('/reports/virtual/usage/district/<district_name>')
    @login_required
    def virtual_usage_district(district_name):
        # Get filter parameters with explicit year handling
        year = int(request.args.get('year', '2024'))  # Default to 2024
        
        # Check if date_from and date_to are provided and match the selected year
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        # If dates are provided, check if they match the selected year
        if date_from_str and date_to_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                # If the dates don't match the selected year, use the year's full range
                if date_from.year != year or date_to.year != year:
                    date_from = datetime(year, 1, 1)
                    date_to = datetime(year, 12, 31)
            except ValueError:
                date_from = datetime(year, 1, 1)
                date_to = datetime(year, 12, 31)
        else:
            # If no dates provided, use the full year range
            date_from = datetime(year, 1, 1)
            date_to = datetime(year, 12, 31)

        current_filters = {
            'year': year,
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Base query for this district with date filtering
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
            Event.district_partner == district_name,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        ).order_by(Event.start_date)
        
        # Get all events for this district
        district_events = query.all()
        
        # Group events by month
        monthly_stats = {}
        
        for event in district_events:
            month_key = event.start_date.strftime('%Y-%m')
            
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month_name': event.start_date.strftime('%B %Y'),
                    'total_sessions': 0,
                    'total_registered': 0,
                    'total_attended': 0,
                    'total_duration': 0,
                    'schools': set(),
                    'educators': set(),
                    'career_clusters': set(),
                    'events': []
                }
            
            stats = monthly_stats[month_key]
            stats['total_sessions'] += 1
            stats['total_registered'] += event.registered_count or 0
            stats['total_attended'] += event.attended_count or 0
            stats['total_duration'] += event.duration or 0
            
            if event.school:
                stats['schools'].add(event.school)
            if event.educators:
                stats['educators'].add(event.educators)
            if event.series:
                stats['career_clusters'].add(event.series)
                
            # Add event details
            stats['events'].append({
                'title': event.title,
                'date': event.start_date.strftime('%Y-%m-%d'),
                'duration': event.duration,
                'registered': event.registered_count,
                'attended': event.attended_count,
                'school': event.school,
                'educator': event.educators,
                'career_cluster': event.series
            })
        
        # Calculate averages and convert sets to counts
        for stats in monthly_stats.values():
            if stats['total_registered'] > 0:
                stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
            stats['avg_duration'] = stats['total_duration'] / stats['total_sessions'] if stats['total_sessions'] > 0 else 0
            stats['school_count'] = len(stats['schools'])
            stats['educator_count'] = len(stats['educators'])
            stats['career_cluster_count'] = len(stats['career_clusters'])
            
            # Clean up sets
            del stats['schools']
            del stats['educators']
            del stats['career_clusters']
        
        # Sort months chronologically
        sorted_stats = dict(sorted(monthly_stats.items()))
        
        return render_template(
            'reports/virtual_usage_district.html',
            district_name=district_name,
            monthly_stats=sorted_stats,
            current_filters=current_filters
        )
