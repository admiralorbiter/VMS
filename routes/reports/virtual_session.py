from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime, date
from sqlalchemy import extract, or_
from sqlalchemy.orm import joinedload

from models.event import Event, EventType, EventStatus
from models.district_model import District
from models import db

# Create blueprint
virtual_bp = Blueprint('virtual', __name__)

# --- Helper Functions for School Year ---

def get_current_school_year() -> str:
    """Determines the current school year string (e.g., '2024-2025')."""
    today = date.today()
    if today.month >= 6:  # School year starts in June
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{start_year + 1}"

def get_school_year_dates(school_year: str) -> tuple[datetime, datetime]:
    """Calculates the start and end dates for a given school year string."""
    try:
        start_year = int(school_year.split('-')[0])
        end_year = start_year + 1
        date_from = datetime(start_year, 6, 1, 0, 0, 0)
        date_to = datetime(end_year, 5, 31, 23, 59, 59)
        return date_from, date_to
    except (ValueError, IndexError):
        current_sy = get_current_school_year()
        return get_school_year_dates(current_sy)

def generate_school_year_options(start_cal_year=2018, end_cal_year=None) -> list[str]:
    """Generates a list of school year strings for dropdowns."""
    if end_cal_year is None:
        end_cal_year = date.today().year + 1
    
    school_years = []
    for year in range(end_cal_year, start_cal_year - 1, -1):
         school_years.append(f"{year}-{year + 1}")
    return school_years

# --- End Helper Functions ---


def load_routes(bp):
    @bp.route('/reports/virtual/usage')
    @login_required
    def virtual_usage():
        # Get filter parameters: Use school year
        default_school_year = get_current_school_year()
        selected_school_year = request.args.get('year', default_school_year)
        
        # Calculate default date range based on school year
        default_date_from, default_date_to = get_school_year_dates(selected_school_year)
        
        # Handle explicit date range parameters
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        
        date_from = default_date_from
        date_to = default_date_to
        
        if date_from_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                if default_date_from.date() <= parsed_date_from.date() <= default_date_to.date():
                    date_from = parsed_date_from.replace(hour=0, minute=0, second=0)
            except ValueError:
                pass

        if date_to_str:
            try:
                parsed_date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                if default_date_from.date() <= parsed_date_to.date() <= default_date_to.date():
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass

        if date_from > date_to:
            date_from = default_date_from
            date_to = default_date_to

        current_filters = {
            'year': selected_school_year,
            'date_from': date_from,
            'date_to': date_to,
            'career_cluster': request.args.get('career_cluster'),
            'school': request.args.get('school'),
            'district': request.args.get('district')
        }
        
        # Base query: Find relevant events first
        base_query = Event.query.options(joinedload(Event.districts)).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        
        # Apply optional non-district filters to the base query
        if current_filters['career_cluster']:
            base_query = base_query.filter(Event.series.ilike(f'%{current_filters["career_cluster"]}%'))
        if current_filters['school']:
            base_query = base_query.filter(Event.school.ilike(f'%{current_filters["school"]}%'))

        # Fetch all potentially relevant events based on date/type/status/other filters
        all_relevant_events = base_query.all()

        # --- Calculate Stats Per District ---
        district_stats = {}
        participating_districts = set()

        for event in all_relevant_events:
            for district in event.districts:
                district_name = district.name
                participating_districts.add(district_name)

                if current_filters['district'] and district_name != current_filters['district']:
                    continue

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
                    for educator in (e.strip() for e in event.educators.split(';') if e.strip()):
                        stats['educators'].add(educator)
                if event.series:
                    stats['career_clusters'].add(event.series)

        # Calculate averages and convert sets to counts
        for district_name in list(district_stats.keys()):
            stats = district_stats[district_name]
            if stats['total_sessions'] == 0:
                del district_stats[district_name]
                continue

            if stats['total_registered'] > 0:
                stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
            stats['avg_duration'] = stats['total_duration'] / stats['total_sessions']
            stats['school_count'] = len(stats['schools'])
            stats['educator_count'] = len(stats['educators'])
            stats['career_cluster_count'] = len(stats['career_clusters'])
            
            del stats['schools']
            del stats['educators']
            del stats['career_clusters']
        
        # Sort districts by total sessions
        sorted_districts = dict(sorted(
            district_stats.items(), 
            key=lambda x: x[1]['total_sessions'], 
            reverse=True
        ))

        # Get unique values for filter dropdowns
        all_clusters_query = base_query.with_entities(Event.series).distinct().all()
        all_schools_query = base_query.with_entities(Event.school).distinct().all()
        
        school_year_options = generate_school_year_options()

        filter_options = {
            'school_years': school_year_options,
            'career_clusters': sorted([c[0] for c in all_clusters_query if c[0]]),
            'schools': sorted([s[0] for s in all_schools_query if s[0]]),
            'districts': sorted(list(participating_districts))
        }
        
        return render_template(
            'reports/virtual_usage.html',
            district_stats=sorted_districts,
            filter_options=filter_options,
            current_filters=current_filters
        )

    @bp.route('/reports/virtual/usage/district/<district_name>')
    @login_required
    def virtual_usage_district(district_name):
        # Get filter parameters: Use school year
        default_school_year = get_current_school_year()
        selected_school_year = request.args.get('year', default_school_year)

        # Calculate default date range based on school year
        default_date_from, default_date_to = get_school_year_dates(selected_school_year)

        # Handle explicit date range parameters
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')

        date_from = default_date_from
        date_to = default_date_to

        if date_from_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                if default_date_from.date() <= parsed_date_from.date() <= default_date_to.date():
                    date_from = parsed_date_from.replace(hour=0, minute=0, second=0)
            except ValueError:
                pass

        if date_to_str:
            try:
                parsed_date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                if default_date_from.date() <= parsed_date_to.date() <= default_date_to.date():
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
            except ValueError:
                pass

        if date_from > date_to:
            date_from = default_date_from
            date_to = default_date_to

        current_filters = {
            'year': selected_school_year,
            'date_from': date_from,
            'date_to': date_to
        }
        
        school_year_options = generate_school_year_options()
        
        query = Event.query.join(Event.districts).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
            District.name == district_name,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        ).order_by(Event.start_date)
        
        district_events = query.all()
        
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
                    'avg_attendance_rate': 0.0,
                    'avg_duration': 0.0,
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
                for educator in (e.strip() for e in event.educators.split(';') if e.strip()):
                    stats['educators'].add(educator)
            if event.series:
                stats['career_clusters'].add(event.series)
            
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
        
        for stats in monthly_stats.values():
            if stats['total_registered'] > 0:
                stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
            if stats['total_sessions'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['total_sessions']

            stats['school_count'] = len(stats['schools'])
            stats['educator_count'] = len(stats['educators'])
            stats['career_cluster_count'] = len(stats['career_clusters'])
            
            del stats['schools']
            del stats['educators']
            del stats['career_clusters']
        
        sorted_stats = dict(sorted(monthly_stats.items()))
        
        return render_template(
            'reports/virtual_usage_district.html',
            district_name=district_name,
            monthly_stats=sorted_stats,
            current_filters=current_filters,
            school_year_options=school_year_options
        )
