from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime, date
from sqlalchemy import extract

from models.event import Event, EventType, EventStatus
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
        date_from = datetime(start_year, 6, 1)
        date_to = datetime(end_year, 5, 31, 23, 59, 59) # End of May 31st
        return date_from, date_to
    except (ValueError, IndexError):
        # Handle invalid format, maybe default to current school year
        current_sy = get_current_school_year()
        return get_school_year_dates(current_sy)

def generate_school_year_options(start_cal_year=2018, end_cal_year=None) -> list[str]:
    """Generates a list of school year strings for dropdowns."""
    if end_cal_year is None:
        end_cal_year = date.today().year + 1 # Go one year into the future potentially
    
    school_years = []
    # School year starts June 1st, so calendar year YYYY corresponds to YYYY-YYYY+1 school year start
    for year in range(end_cal_year, start_cal_year - 1, -1):
         # The school year starting in 'year' is 'year'-'year+1'
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
        
        if date_from_str and date_to_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                parsed_date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
                
                # Check if parsed dates fall within the selected school year range
                # If they don't, we stick with the school year's default range
                if default_date_from <= parsed_date_from <= default_date_to and \
                   default_date_from <= parsed_date_to <= default_date_to and \
                   parsed_date_from <= parsed_date_to:
                    date_from = parsed_date_from
                    # Adjust date_to to include the whole day
                    date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
                # else: keep default_date_from/to calculated from school year

            except ValueError:
                # Invalid date format, use the default school year range
                pass 

        current_filters = {
            'year': selected_school_year, # Now stores school year string
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
            Event.start_date <= date_to # Use precise end time
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
        
        # Generate school year options for the dropdown
        school_year_options = generate_school_year_options()

        filter_options = {
            'school_years': school_year_options, # Add school years here
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
            filter_options=filter_options, # Pass updated filter options
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

        if date_from_str and date_to_str:
            try:
                parsed_date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
                parsed_date_to = datetime.strptime(date_to_str, '%Y-%m-%d')

                # Check if parsed dates fall within the selected school year range
                if default_date_from <= parsed_date_from <= default_date_to and \
                   default_date_from <= parsed_date_to <= default_date_to and \
                   parsed_date_from <= parsed_date_to:
                     date_from = parsed_date_from
                     # Adjust date_to to include the whole day
                     date_to = parsed_date_to.replace(hour=23, minute=59, second=59)
                # else: keep default_date_from/to calculated from school year

            except ValueError:
                # Invalid date format, use the default school year range
                 pass

        current_filters = {
            'year': selected_school_year, # Use school year string
            'date_from': date_from,
            'date_to': date_to
        }
        
        # Generate school year options for the dropdown
        school_year_options = generate_school_year_options()
        
        # Base query for this district with date filtering
        query = Event.query.filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.status == EventStatus.COMPLETED,
            Event.district_partner == district_name,
            Event.start_date >= date_from,
            Event.start_date <= date_to # Use precise end time
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
                    'avg_attendance_rate': 0.0, # Initialize here
                    'avg_duration': 0.0,       # Initialize here
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
            # No 'else' needed as it's initialized to 0.0

            if stats['total_sessions'] > 0: # Check division by zero
                stats['avg_duration'] = stats['total_duration'] / stats['total_sessions']
            # No 'else' needed as it's initialized to 0.0

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
            current_filters=current_filters,
            school_year_options=school_year_options # Pass school year options
        )
