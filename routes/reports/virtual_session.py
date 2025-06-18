from flask import Blueprint, render_template, request, make_response, send_file
from flask_login import login_required
from datetime import datetime, date
from sqlalchemy import extract, or_, func
from sqlalchemy.orm import joinedload
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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

def get_current_virtual_year() -> str:
    """Determines the current virtual session year string (July 1st to July 1st)."""
    today = date.today()
    if today.month >= 7:  # Virtual year starts in July
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{start_year + 1}"

def get_virtual_year_dates(virtual_year: str) -> tuple[datetime, datetime]:
    """Calculates the start and end dates for a given virtual session year string."""
    try:
        start_year = int(virtual_year.split('-')[0])
        end_year = start_year + 1
        date_from = datetime(start_year, 7, 1, 0, 0, 0)  # July 1st start
        date_to = datetime(end_year, 6, 30, 23, 59, 59)  # June 30th end
        return date_from, date_to
    except (ValueError, IndexError):
        current_vy = get_current_virtual_year()
        return get_virtual_year_dates(current_vy)

# --- End Helper Functions ---


def load_routes(bp):
    @bp.route('/reports/virtual/usage')
    @login_required
    def virtual_usage():
        # Get filter parameters - Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()  # Changed from get_current_school_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)  # Changed variable name
        
        # Calculate default date range based on virtual session year
        default_date_from, default_date_to = get_virtual_year_dates(selected_virtual_year)  # Changed from get_school_year_dates()
        
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
            'year': selected_virtual_year,  # Updated variable name
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
                        'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
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
                    'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
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
        # Apply sorting before building filter options
        sort_column = request.args.get('sort', 'date')  # Default sort by date
        sort_order = request.args.get('order', 'desc')  # Default descending
        
        # Define sortable columns mapping
        sortable_columns = {
            'status': 'status',
            'date': 'date',
            'time': 'time', 
            'session_type': 'session_type',
            'teacher_name': 'teacher_name',
            'school_name': 'school_name',
            'school_level': 'school_level',
            'district': 'district',
            'session_title': 'session_title',
            'presenter': 'presenter',
            'topic_theme': 'topic_theme'
        }
        
        # Apply sorting if valid column
        if sort_column in sortable_columns:
            reverse_order = (sort_order == 'desc')
            
            # Handle special sorting for date/time columns
            if sort_column == 'date':
                def date_sort_key(session):
                    try:
                        # Convert MM/DD/YY format back to date for proper sorting
                        if session['date']:
                            # Handle both MM/DD/YY and MM/DD formats for backward compatibility
                            date_parts = session['date'].split('/')
                            if len(date_parts) == 3:  # MM/DD/YY format
                                month = int(date_parts[0])
                                day = int(date_parts[1])
                                year = int(date_parts[2])
                                # Convert 2-digit year to 4-digit year
                                if year < 50:  # Assume 00-49 means 2000-2049
                                    year += 2000
                                else:  # Assume 50-99 means 1950-1999
                                    year += 1900
                                return datetime(year, month, day)
                            elif len(date_parts) == 2:  # MM/DD format (fallback)
                                month = int(date_parts[0])
                                day = int(date_parts[1])
                                # Determine the correct year based on virtual session year context
                                # Virtual year runs July-June, so:
                                # July-December = first year of virtual year
                                # January-June = second year of virtual year
                                virtual_year_start = int(selected_virtual_year.split('-')[0])  # Changed from school_year_start
                                
                                if month >= 7:  # July-December
                                    year = virtual_year_start
                                else:  # January-June
                                    year = virtual_year_start + 1
                                return datetime(year, month, day)
                        return datetime.min
                    except (ValueError, IndexError):
                        return datetime.min
                session_data.sort(key=date_sort_key, reverse=reverse_order)
            
            elif sort_column == 'time':
                def time_sort_key(session):
                    try:
                        if session['time']:
                            return datetime.strptime(session['time'], '%I:%M %p').time()
                        return datetime.min.time()
                    except ValueError:
                        return datetime.min.time()
                session_data.sort(key=time_sort_key, reverse=reverse_order)
            
            else:
                # For other columns, sort by string value (case-insensitive)
                def string_sort_key(session):
                    value = session.get(sortable_columns[sort_column], '') or ''
                    return str(value).lower()
                session_data.sort(key=string_sort_key, reverse=reverse_order)
        
        # Add sorting info to current_filters for template
        current_filters['sort'] = sort_column
        current_filters['order'] = sort_order

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
        
        virtual_year_options = generate_school_year_options()  # This function name is misleading but works for both school and virtual years

        filter_options = {
            'school_years': virtual_year_options,  # Keep the key name for template compatibility
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
        # Get filter parameters: Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()  # Changed from get_current_school_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)  # Changed variable name

        # Calculate default date range based on virtual session year
        default_date_from, default_date_to = get_virtual_year_dates(selected_virtual_year)  # Changed from get_school_year_dates()

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
            'year': selected_virtual_year,  # Updated variable name
            'date_from': date_from,
            'date_to': date_to
        }
        
        virtual_year_options = generate_school_year_options()  # Keep same function
        
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
            school_year_options=virtual_year_options  # Keep same key name for template compatibility
        )

    @bp.route('/reports/virtual/usage/export')
    @login_required
    def virtual_usage_export():
        # Get filter parameters - Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)
        
        # Calculate default date range based on virtual session year
        default_date_from, default_date_to = get_virtual_year_dates(selected_virtual_year)
        
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
            'year': selected_virtual_year,
            'date_from': date_from,
            'date_to': date_to,
            'career_cluster': request.args.get('career_cluster'),
            'school': request.args.get('school'),
            'district': request.args.get('district'),
            'status': request.args.get('status'),
            'session_title': request.args.get('session_title')
        }
        
        # Base query for virtual session events (same as main route)
        base_query = Event.query.options(
            joinedload(Event.districts),
            joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher).joinedload(Teacher.school)
        ).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        
        # Apply filters (same as main route)
        if current_filters['career_cluster']:
            base_query = base_query.filter(Event.series.ilike(f'%{current_filters["career_cluster"]}%'))
        
        if current_filters['session_title']:
            base_query = base_query.filter(Event.title.ilike(f'%{current_filters["session_title"]}%'))
        
        if current_filters['status']:
            base_query = base_query.filter(Event.status == current_filters['status'])

        # Get all events
        events = base_query.order_by(Event.start_date.desc()).all()
        
        # Build session data (same logic as main route)
        session_data = []
        
        for event in events:
            teacher_registrations = event.teacher_registrations
            
            if teacher_registrations:
                for teacher_reg in teacher_registrations:
                    teacher = teacher_reg.teacher
                    
                    school = None
                    school_name = ''
                    school_level = ''
                    
                    if teacher:
                        if hasattr(teacher, 'school_obj') and teacher.school_obj:
                            school = teacher.school_obj
                            school_name = school.name
                            school_level = getattr(school, 'level', '')
                        elif teacher.school_id:
                            school = School.query.get(teacher.school_id)
                            if school:
                                school_name = school.name
                                school_level = getattr(school, 'level', '')
                    
                    district_name = None
                    if event.districts:
                        district_name = event.districts[0].name
                    elif event.district_partner:
                        district_name = event.district_partner
                    elif school and hasattr(school, 'district') and school.district:
                        district_name = school.district.name
                    else:
                        district_name = 'Unknown District'
                    
                    # Apply filters
                    if current_filters['district'] and district_name != current_filters['district']:
                        continue
                    
                    if current_filters['school'] and school_name and current_filters['school'].lower() not in school_name.lower():
                        continue
                    
                    session_data.append({
                        'status': teacher_reg.status or 'registered',
                        'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
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
                        'participant_count': event.participant_count or 0,
                        'duration': event.duration or 0
                    })
            else:
                district_name = None
                if event.districts:
                    district_name = event.districts[0].name
                elif event.district_partner:
                    district_name = event.district_partner
                else:
                    district_name = 'Unknown District'
                
                if current_filters['district'] and district_name != current_filters['district']:
                    continue
                
                session_data.append({
                    'status': event.status.value if event.status else '',
                    'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
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
                    'participant_count': event.participant_count or 0,
                    'duration': event.duration or 0
                })

        # Apply sorting (same logic as main route)
        sort_column = request.args.get('sort', 'date')
        sort_order = request.args.get('order', 'desc')
        
        sortable_columns = {
            'status': 'status', 'date': 'date', 'time': 'time', 
            'session_type': 'session_type', 'teacher_name': 'teacher_name',
            'school_name': 'school_name', 'school_level': 'school_level',
            'district': 'district', 'session_title': 'session_title',
            'presenter': 'presenter', 'topic_theme': 'topic_theme'
        }
        
        if sort_column in sortable_columns:
            reverse_order = (sort_order == 'desc')
            
            if sort_column == 'date':
                def date_sort_key(session):
                    try:
                        if session['date']:
                            date_parts = session['date'].split('/')
                            if len(date_parts) == 3:
                                month, day, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                                if year < 50:
                                    year += 2000
                                else:
                                    year += 1900
                                return datetime(year, month, day)
                            elif len(date_parts) == 2:
                                month, day = int(date_parts[0]), int(date_parts[1])
                                virtual_year_start = int(selected_virtual_year.split('-')[0])
                                year = virtual_year_start if month >= 7 else virtual_year_start + 1
                                return datetime(year, month, day)
                        return datetime.min
                    except (ValueError, IndexError):
                        return datetime.min
                session_data.sort(key=date_sort_key, reverse=reverse_order)
            
            elif sort_column == 'time':
                def time_sort_key(session):
                    try:
                        if session['time']:
                            return datetime.strptime(session['time'], '%I:%M %p').time()
                        return datetime.min.time()
                    except ValueError:
                        return datetime.min.time()
                session_data.sort(key=time_sort_key, reverse=reverse_order)
            
            else:
                def string_sort_key(session):
                    value = session.get(sortable_columns[sort_column], '') or ''
                    return str(value).lower()
                session_data.sort(key=string_sort_key, reverse=reverse_order)

        # Create Excel workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Virtual Session Usage"
        
        # Define headers
        headers = [
            'Status', 'Date', 'Time', 'Session Type', 'Teacher Name',
            'School Name', 'School Level', 'District', 'Session Title',
            'Presenter', 'Topic/Theme', 'Session Link', 'Participant Count', 'Duration (min)'
        ]
        
        # Style definitions
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="495057", end_color="495057", fill_type="solid")
        header_alignment = Alignment(horizontal="left", vertical="center")
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        # Add headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Add data
        for row_idx, session in enumerate(session_data, 2):
            data_row = [
                session['status'],
                session['date'],
                session['time'],
                session['session_type'],
                session['teacher_name'],
                session['school_name'],
                session['school_level'],
                session['district'],
                session['session_title'],
                session['presenter'],
                session['topic_theme'],
                session['session_link'],
                session['participant_count'],
                session['duration']
            ]
            
            for col_idx, value in enumerate(data_row, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50
            ws.column_dimensions[column].width = adjusted_width
        
        # Add summary info at the top
        ws.insert_rows(1, 4)
        
        # Report title
        title_cell = ws.cell(row=1, column=1, value="Virtual Session Usage Report")
        title_cell.font = Font(bold=True, size=16)
        
        # Export date
        export_date_cell = ws.cell(row=2, column=1, value=f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        export_date_cell.font = Font(italic=True)
        
        # Filters applied
        filter_info = f"Virtual Year: {selected_virtual_year}"
        if current_filters['date_from'] and current_filters['date_to']:
            filter_info += f" | Date Range: {current_filters['date_from'].strftime('%Y-%m-%d')} to {current_filters['date_to'].strftime('%Y-%m-%d')}"
        if current_filters['district']:
            filter_info += f" | District: {current_filters['district']}"
        if current_filters['session_title']:
            filter_info += f" | Session: {current_filters['session_title']}"
        if current_filters['career_cluster']:
            filter_info += f" | Career Cluster: {current_filters['career_cluster']}"
        if current_filters['status']:
            filter_info += f" | Status: {current_filters['status']}"
        
        filter_cell = ws.cell(row=3, column=1, value=f"Filters: {filter_info}")
        filter_cell.font = Font(italic=True, size=10)
        
        # Total records
        total_cell = ws.cell(row=4, column=1, value=f"Total Records: {len(session_data)}")
        total_cell.font = Font(bold=True)
        
        # Create file in memory
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"virtual_session_usage_{selected_virtual_year}_{timestamp}.xlsx"
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
