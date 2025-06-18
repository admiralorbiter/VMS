from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime, date
from sqlalchemy import extract, or_, func
from sqlalchemy.orm import joinedload

from models.event import Event, EventType, EventStatus, EventTeacher
from models.district_model import District
from models.teacher import Teacher
from models.school_model import School
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
        # Get filter parameters
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
            'district': request.args.get('district'),
            'status': request.args.get('status'),
            'session_title': request.args.get('session_title')
        }
        
        # Base query for virtual session events
        base_query = Event.query.options(
            joinedload(Event.districts),
            joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher).joinedload(Teacher.school)
        ).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        
        # Apply filters
        if current_filters['career_cluster']:
            base_query = base_query.filter(Event.series.ilike(f'%{current_filters["career_cluster"]}%'))
        
        if current_filters['session_title']:
            base_query = base_query.filter(Event.title.ilike(f'%{current_filters["session_title"]}%'))
        
        if current_filters['status']:
            base_query = base_query.filter(Event.status == current_filters['status'])

        # Get all events
        events = base_query.order_by(Event.start_date.desc()).all()
        
        # Build session data similar to Google Sheet format
        session_data = []
        
        for event in events:
            # Get all teacher registrations for this event
            teacher_registrations = event.teacher_registrations
            
            if teacher_registrations:
                # Create a row for each teacher registration
                for teacher_reg in teacher_registrations:
                    teacher = teacher_reg.teacher
                    
                    # Get school information - handle both relationship and direct query
                    school = None
                    school_name = ''
                    school_level = ''
                    
                    if teacher:
                        if hasattr(teacher, 'school_obj') and teacher.school_obj:
                            # Use relationship if available
                            school = teacher.school_obj
                            school_name = school.name
                            school_level = getattr(school, 'level', '')
                        elif teacher.school_id:
                            # Fallback to direct query
                            school = School.query.get(teacher.school_id)
                            if school:
                                school_name = school.name
                                school_level = getattr(school, 'level', '')
                    
                    # Determine district from multiple sources
                    district_name = None
                    if event.districts:
                        district_name = event.districts[0].name
                    elif event.district_partner:
                        district_name = event.district_partner
                    elif school and hasattr(school, 'district') and school.district:
                        district_name = school.district.name
                    else:
                        district_name = 'Unknown District'
                    
                    # Apply district filter if specified
                    if current_filters['district'] and district_name != current_filters['district']:
                        continue
                    
                    # Apply school filter if specified
                    if current_filters['school'] and school_name and current_filters['school'].lower() not in school_name.lower():
                        continue
                    
                    session_data.append({
                        'event_id': event.id,
                        'status': teacher_reg.status or 'registered',
                        'date': event.start_date.strftime('%m/%d') if event.start_date else '',
                        'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                        'session_type': event.additional_information or '',
                        'teacher_name': f"{teacher.first_name} {teacher.last_name}" if teacher else '',
                        'school_name': school_name,
                        'school_level': school_level,
                        'district': district_name,
                        'session_title': event.title,
                        'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                        'topic_theme': event.series or '',
                        'session_link': event.registration_link or '',
                        'session_id': event.session_id or '',
                        'participant_count': event.participant_count or 0,
                        'duration': event.duration or 0,
                        'is_simulcast': teacher_reg.is_simulcast
                    })
            else:
                # Event with no teacher registrations - show the event itself
                district_name = None
                if event.districts:
                    district_name = event.districts[0].name
                elif event.district_partner:
                    district_name = event.district_partner
                else:
                    district_name = 'Unknown District'
                
                # Apply district filter if specified
                if current_filters['district'] and district_name != current_filters['district']:
                    continue
                
                session_data.append({
                    'event_id': event.id,
                    'status': event.status.value if event.status else '',
                    'date': event.start_date.strftime('%m/%d') if event.start_date else '',
                    'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                    'session_type': event.additional_information or '',
                    'teacher_name': '',
                    'school_name': '',
                    'school_level': '',
                    'district': district_name,
                    'session_title': event.title,
                    'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                    'topic_theme': event.series or '',
                    'session_link': event.registration_link or '',
                    'session_id': event.session_id or '',
                    'participant_count': event.participant_count or 0,
                    'duration': event.duration or 0,
                    'is_simulcast': False
                })
        
        # Get filter options
        all_districts = set()
        all_schools = set()
        all_career_clusters = set()
        all_statuses = set()
        all_session_titles = set()
        
        for session in session_data:
            if session['district']:
                all_districts.add(session['district'])
            if session['school_name']:
                all_schools.add(session['school_name'])
            if session['topic_theme']:
                all_career_clusters.add(session['topic_theme'])
            if session['status']:
                all_statuses.add(session['status'])
            if session['session_title']:
                all_session_titles.add(session['session_title'])
        
        school_year_options = generate_school_year_options()

        filter_options = {
            'school_years': school_year_options,
            'career_clusters': sorted(list(all_career_clusters)),
            'schools': sorted(list(all_schools)),
            'districts': sorted(list(all_districts)),
            'statuses': sorted(list(all_statuses)),
            'session_titles': sorted(list(all_session_titles))
        }
        
        return render_template(
            'reports/virtual_usage.html',
            session_data=session_data,
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
        
        query = Event.query.options(
            joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher).joinedload(Teacher.school)
        ).join(Event.districts).filter(
            Event.type == EventType.VIRTUAL_SESSION,
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
            stats['total_registered'] += event.participant_count or 0
            stats['total_attended'] += event.participant_count or 0
            stats['total_duration'] += event.duration or 0
            
            # Collect schools and educators from teacher registrations
            event_schools = []
            event_educators = []
            for teacher_reg in event.teacher_registrations:
                if teacher_reg.teacher:
                    educator_name = f"{teacher_reg.teacher.first_name} {teacher_reg.teacher.last_name}"
                    event_educators.append(educator_name)
                    stats['educators'].add(educator_name)
                    
                    if teacher_reg.teacher.school:
                        school_name = teacher_reg.teacher.school.name
                        event_schools.append(school_name)
                        stats['schools'].add(school_name)
            
            if event.series:
                stats['career_clusters'].add(event.series)
            
            stats['events'].append({
                'title': event.title,
                'date': event.start_date.strftime('%Y-%m-%d'),
                'time': event.start_date.strftime('%I:%M %p'),
                'duration': event.duration,
                'registered': event.participant_count,
                'attended': event.participant_count,
                'schools': ', '.join(event_schools),
                'educators': ', '.join(event_educators),
                'career_cluster': event.series,
                'session_id': event.session_id
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
