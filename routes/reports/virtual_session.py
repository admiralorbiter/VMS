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
from models.google_sheet import GoogleSheet

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
    """Determines the current virtual session year string (August 1st to July 31st)."""
    today = date.today()
    if today.month > 7 or (today.month == 7 and today.day == 31):  # After July 31st
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{start_year + 1}"

def get_virtual_year_dates(virtual_year: str) -> tuple[datetime, datetime]:
    """Calculates the start and end dates for a given virtual session year string (8/1 to 7/31)."""
    try:
        start_year = int(virtual_year.split('-')[0])
        end_year = start_year + 1
        date_from = datetime(start_year, 8, 1, 0, 0, 0)  # August 1st start
        date_to = datetime(end_year, 7, 31, 23, 59, 59)  # July 31st end
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
            'status': request.args.get('status')
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

        # --- Pagination ---
        # (Move pagination AFTER all summary/district aggregation)
        
        # Build district summary statistics and overall summary from ALL session_data (not paginated)
        all_districts = set()
        all_schools = set()
        all_career_clusters = set()
        all_statuses = set()
        
        district_summaries = {}
        overall_stats = {
            'teacher_count': 0,
            'student_count': 0,
            'session_count': set(),
            'experience_count': 0,
            'organization_count': set(),
            'professional_count': set(),
            'professional_of_color_count': set(),
            'school_count': set()
        }
        
        for session in session_data:
            if session['district']:
                all_districts.add(session['district'])
                if session['district'] not in district_summaries:
                    district_summaries[session['district']] = {
                        'teachers': set(),
                        'schools': set(),
                        'sessions': set(),
                        'total_students': 0,
                        'total_experiences': 0,
                        'organizations': set(),
                        'professionals': set(),
                        'professionals_of_color': set()
                    }
                district_summary = district_summaries[session['district']]
                if session['teacher_name']:
                    district_summary['teachers'].add(session['teacher_name'])
                    overall_stats['teacher_count'] += 1
                if session['school_name']:
                    district_summary['schools'].add(session['school_name'])
                    overall_stats['school_count'].add(session['school_name'])
                if session['session_title']:
                    district_summary['sessions'].add(session['session_title'])
                    overall_stats['session_count'].add(session['session_title'])
                student_count = session.get('participant_count', 0)
                if student_count > 0:
                    district_summary['total_students'] += student_count
                    overall_stats['student_count'] += student_count
                else:
                    district_summary['total_students'] += 25
                    overall_stats['student_count'] += 25
                district_summary['total_experiences'] += 1
                overall_stats['experience_count'] += 1
                if session['presenter']:
                    presenters = [p.strip() for p in session['presenter'].split(',')]
                    for presenter in presenters:
                        if presenter:
                            district_summary['professionals'].add(presenter)
                            district_summary['professionals_of_color'].add(presenter)
                            district_summary['organizations'].add(presenter)
                            overall_stats['professional_count'].add(presenter)
                            overall_stats['professional_of_color_count'].add(presenter)
                            overall_stats['organization_count'].add(presenter)
            if session['school_name']:
                all_schools.add(session['school_name'])
            if session['topic_theme']:
                all_career_clusters.add(session['topic_theme'])
            if session['status']:
                all_statuses.add(session['status'])
        for district_name, summary in district_summaries.items():
            summary['teacher_count'] = len(summary['teachers'])
            summary['school_count'] = len(summary['schools'])
            summary['session_count'] = len(summary['sessions'])
            summary['organization_count'] = len(summary['organizations'])
            summary['professional_count'] = len(summary['professionals'])
            summary['professional_of_color_count'] = 0  # Always 0 until we have demographic data
            del summary['teachers']
            del summary['schools']
            del summary['sessions']
            del summary['organizations']
            del summary['professionals']
            del summary['professionals_of_color']
        # Now paginate session_data for table display
        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                page = 1
        except ValueError:
            page = 1
        try:
            per_page = int(request.args.get('per_page', 25))
            if per_page < 1:
                per_page = 25
        except ValueError:
            per_page = 25
        total_records = len(session_data)
        total_pages = (total_records + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = session_data[start_idx:end_idx]
        virtual_year_options = generate_school_year_options()
        filter_options = {
            'school_years': virtual_year_options,
            'career_clusters': sorted(list(all_career_clusters)),
            'schools': sorted(list(all_schools)),
            'districts': sorted(list(all_districts)),
            'statuses': sorted(list(all_statuses))
        }
        google_sheet = GoogleSheet.query.filter_by(academic_year=selected_virtual_year).first()
        google_sheet_url = None
        if google_sheet and google_sheet.decrypted_sheet_id:
            google_sheet_url = f"https://docs.google.com/spreadsheets/d/{google_sheet.decrypted_sheet_id}"
        allowed_districts = {
            "Hickman Mills School District",
            "Grandview School District",
            "Kansas City Kansas Public Schools"
        }
        district_summaries = {k: v for k, v in district_summaries.items() if k in allowed_districts}
        # Prepare overall summary stats for template
        overall_summary = {
            'teacher_count': overall_stats['teacher_count'],
            'student_count': overall_stats['student_count'],
            'session_count': len(overall_stats['session_count']),
            'experience_count': overall_stats['experience_count'],
            'organization_count': len(overall_stats['organization_count']),
            'professional_count': len(overall_stats['professional_count']),
            'professional_of_color_count': 0,  # Always 0 until we have demographic data
            'school_count': len(overall_stats['school_count'])
        }
        return render_template(
            'reports/virtual_usage.html',
            session_data=paginated_data,
            filter_options=filter_options,
            current_filters=current_filters,
            pagination={
                'current_page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_records': total_records
            },
            google_sheet_url=google_sheet_url,
            district_summaries=district_summaries,
            overall_summary=overall_summary
        )

    @bp.route('/reports/virtual/usage/district/<district_name>')
    @login_required
    def virtual_usage_district(district_name):
        # Get filter parameters: Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)
        default_date_from, default_date_to = get_virtual_year_dates(selected_virtual_year)
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
            'date_to': date_to
        }
        virtual_year_options = generate_school_year_options()
        # --- Aggregate session_data by event/session ---
        base_query = Event.query.options(
            joinedload(Event.districts),
            joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher).joinedload(Teacher.school)
        ).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        events = base_query.order_by(Event.start_date.desc()).all()
        session_dict = {}
        for event in events:
            # Determine district for this event
            district_name_val = None
            if event.districts:
                district_name_val = event.districts[0].name
            elif event.district_partner:
                district_name_val = event.district_partner
            else:
                district_name_val = 'Unknown District'
            if district_name_val != district_name:
                continue
            # Aggregate teachers and schools for this event
            teachers = set()
            schools = set()
            for teacher_reg in event.teacher_registrations:
                teacher = teacher_reg.teacher
                if teacher:
                    teachers.add(f"{teacher.first_name} {teacher.last_name}")
                    # School
                    school_name = ''
                    if hasattr(teacher, 'school_obj') and teacher.school_obj:
                        school_name = teacher.school_obj.name
                    elif teacher.school_id:
                        school_obj = School.query.get(teacher.school_id)
                        if school_obj:
                            school_name = school_obj.name
                    if school_name:
                        schools.add(school_name)
            # If no teacher registrations, leave teachers/schools empty
            session_dict[event.id] = {
                'event_id': event.id,
                'status': event.status.value if event.status else '',
                'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'session_type': event.additional_information or '',
                'teachers': sorted(teachers) if teachers else [],
                'schools': sorted(schools) if schools else [],
                'district': district_name_val,
                'session_title': event.title,
                'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                'topic_theme': event.series or '',
                'session_link': event.registration_link or '',
                'session_id': event.session_id or '',
                'participant_count': event.participant_count or 0,
                'duration': event.duration or 0,
                'is_simulcast': any([tr.is_simulcast for tr in event.teacher_registrations]) if event.teacher_registrations else False
            }
        # Convert to list and sort by date descending
        session_data = list(session_dict.values())
        session_data.sort(key=lambda s: s['date'], reverse=True)
        # --- End aggregation ---

        # Now aggregate stats from session_data (same as main page logic, but updated for new structure)
        total_teachers = set()
        total_students = 0
        total_unique_sessions = set()
        total_experiences = 0
        total_organizations = set()
        total_professionals = set()
        total_professionals_of_color = set()
        total_schools = set()
        school_breakdown = {}
        teacher_breakdown = {}
        for session in session_data:
            # Teachers
            for teacher_name in session['teachers']:
                total_teachers.add(teacher_name)
                # Teacher breakdown
                if teacher_name not in teacher_breakdown:
                    # Use first school if available, else N/A
                    school_val = session['schools'][0] if session['schools'] else 'N/A'
                    teacher_breakdown[teacher_name] = {
                        'name': teacher_name,
                        'school': school_val,
                        'sessions': 0
                    }
                teacher_breakdown[teacher_name]['sessions'] += 1
            # Schools
            for school_name in session['schools']:
                total_schools.add(school_name)
                # School breakdown
                if school_name not in school_breakdown:
                    school_breakdown[school_name] = {
                        'name': school_name,
                        'sessions': 0
                    }
                school_breakdown[school_name]['sessions'] += 1
            # Sessions
            if session['session_title']:
                total_unique_sessions.add(session['session_title'])
            # Students
            if session.get('participant_count', 0) > 0:
                total_students += session['participant_count']
            else:
                total_students += 25
            total_experiences += 1
            # Presenters/Organizations
            if session['presenter']:
                presenters = [p.strip() for p in session['presenter'].split(',')]
                for presenter in presenters:
                    if presenter:
                        total_professionals.add(presenter)
                        total_professionals_of_color.add(presenter)
                        total_organizations.add(presenter)
        total_unique_sessions_count = len(total_unique_sessions)
        total_organizations_count = len(total_organizations)
        total_professionals_count = len(total_professionals)
        total_professionals_of_color_count = 0  # Always 0 until we have demographic data
        total_schools_count = len(total_schools)
        total_teachers_count = len(total_teachers)
        school_breakdown_list = sorted(school_breakdown.values(), key=lambda x: x['sessions'], reverse=True)
        teacher_breakdown_list = sorted(teacher_breakdown.values(), key=lambda x: x['sessions'], reverse=True)
        # Monthly stats (reuse previous logic, but from session_data)
        monthly_stats = {}
        for session in session_data:
            # Parse month from date
            try:
                date_obj = datetime.strptime(session['date'], '%m/%d/%y')
                month_key = date_obj.strftime('%Y-%m')
                month_name = date_obj.strftime('%B %Y')
            except Exception:
                continue
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month_name': month_name,
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
            stats['total_registered'] += session.get('participant_count', 0)
            stats['total_attended'] += session.get('participant_count', 0)
            stats['total_duration'] += session.get('duration', 0)
            for school_name in session['schools']:
                stats['schools'].add(school_name)
            for teacher_name in session['teachers']:
                stats['educators'].add(teacher_name)
            if session['topic_theme']:
                stats['career_clusters'].add(session['topic_theme'])
            stats['events'].append({
                'title': session['session_title'],
                'date': session['date'],
                'time': session['time'],
                'duration': session['duration'],
                'registered': session.get('participant_count', 0),
                'attended': session.get('participant_count', 0),
                'schools': ', '.join(session['schools']) if session['schools'] else 'N/A',
                'educators': ', '.join(session['teachers']) if session['teachers'] else 'N/A',
                'career_cluster': session['topic_theme'],
                'session_id': session['session_id']
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
            school_year_options=virtual_year_options,
            total_teachers=total_teachers_count,
            total_students=total_students,
            total_unique_sessions=total_unique_sessions_count,
            total_experiences=total_experiences,
            total_organizations=total_organizations_count,
            total_professionals=total_professionals_count,
            total_professionals_of_color=total_professionals_of_color_count,
            total_schools=total_schools_count,
            school_breakdown=school_breakdown_list,
            teacher_breakdown=teacher_breakdown_list,
            session_data=session_data
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
            'status': request.args.get('status')
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
