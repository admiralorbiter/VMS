from flask import Blueprint, render_template, request, make_response, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timezone, timedelta
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
from models.reports import VirtualSessionReportCache, VirtualSessionDistrictCache

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

# --- Cache Management Functions ---

def is_cache_valid(cache_record, max_age_hours=24):
    """
    Check if a cache record is still valid based on age.
    
    Args:
        cache_record: The cache record to check
        max_age_hours: Maximum age in hours before cache is considered stale
        
    Returns:
        bool: True if cache is valid, False otherwise
    """
    if not cache_record:
        return False
    
    from datetime import datetime, timezone, timedelta
    
    # Convert to timezone-aware datetime if needed
    if cache_record.last_updated.tzinfo is None:
        last_updated = cache_record.last_updated.replace(tzinfo=timezone.utc)
    else:
        last_updated = cache_record.last_updated
    
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    
    return (now - last_updated) < max_age


def get_virtual_session_cache(virtual_year, date_from=None, date_to=None):
    """
    Get cached virtual session report data.
    
    Args:
        virtual_year: The virtual year to get cache for
        date_from: Optional start date filter
        date_to: Optional end date filter
        
    Returns:
        VirtualSessionReportCache or None if not found/expired
    """
    cache_query = VirtualSessionReportCache.query.filter_by(
        virtual_year=virtual_year,
        date_from=date_from.date() if date_from else None,
        date_to=date_to.date() if date_to else None
    )
    
    cache_record = cache_query.first()
    
    if is_cache_valid(cache_record):
        return cache_record
    
    return None


def save_virtual_session_cache(virtual_year, date_from, date_to, session_data, 
                              district_summaries, overall_summary, filter_options):
    """
    Save virtual session report data to cache.
    
    Args:
        virtual_year: The virtual year
        date_from: Start date filter
        date_to: End date filter
        session_data: Session data to cache
        district_summaries: District summary data
        overall_summary: Overall summary data
        filter_options: Filter options data
    """
    try:
        # Check if cache record exists
        cache_record = VirtualSessionReportCache.query.filter_by(
            virtual_year=virtual_year,
            date_from=date_from.date() if date_from else None,
            date_to=date_to.date() if date_to else None
        ).first()
        
        if cache_record:
            # Update existing record
            cache_record.session_data = session_data
            cache_record.district_summaries = district_summaries
            cache_record.overall_summary = overall_summary
            cache_record.filter_options = filter_options
            cache_record.last_updated = datetime.now(timezone.utc)
        else:
            # Create new record
            cache_record = VirtualSessionReportCache(
                virtual_year=virtual_year,
                date_from=date_from.date() if date_from else None,
                date_to=date_to.date() if date_to else None,
                session_data=session_data,
                district_summaries=district_summaries,
                overall_summary=overall_summary,
                filter_options=filter_options
            )
            db.session.add(cache_record)
        
        db.session.commit()
        print(f"Virtual session cache saved for {virtual_year}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving virtual session cache: {str(e)}")


def get_virtual_session_district_cache(district_name, virtual_year, date_from=None, date_to=None):
    """
    Get cached district virtual session report data.
    
    Args:
        district_name: The district name
        virtual_year: The virtual year to get cache for
        date_from: Optional start date filter
        date_to: Optional end date filter
        
    Returns:
        VirtualSessionDistrictCache or None if not found/expired
    """
    cache_query = VirtualSessionDistrictCache.query.filter_by(
        district_name=district_name,
        virtual_year=virtual_year,
        date_from=date_from.date() if date_from else None,
        date_to=date_to.date() if date_to else None
    )
    
    cache_record = cache_query.first()
    
    if is_cache_valid(cache_record):
        return cache_record
    
    return None


def save_virtual_session_district_cache(district_name, virtual_year, date_from, date_to,
                                      session_data, monthly_stats, school_breakdown,
                                      teacher_breakdown, summary_stats):
    """
    Save district virtual session report data to cache.
    
    Args:
        district_name: The district name
        virtual_year: The virtual year
        date_from: Start date filter
        date_to: End date filter
        session_data: Session data to cache
        monthly_stats: Monthly statistics
        school_breakdown: School breakdown data
        teacher_breakdown: Teacher breakdown data
        summary_stats: Summary statistics
    """
    try:
        # Check if cache record exists
        cache_record = VirtualSessionDistrictCache.query.filter_by(
            district_name=district_name,
            virtual_year=virtual_year,
            date_from=date_from.date() if date_from else None,
            date_to=date_to.date() if date_to else None
        ).first()
        
        if cache_record:
            # Update existing record
            cache_record.session_data = session_data
            cache_record.monthly_stats = monthly_stats
            cache_record.school_breakdown = school_breakdown
            cache_record.teacher_breakdown = teacher_breakdown
            cache_record.summary_stats = summary_stats
            cache_record.last_updated = datetime.now(timezone.utc)
        else:
            # Create new record
            cache_record = VirtualSessionDistrictCache(
                district_name=district_name,
                virtual_year=virtual_year,
                date_from=date_from.date() if date_from else None,
                date_to=date_to.date() if date_to else None,
                session_data=session_data,
                monthly_stats=monthly_stats,
                school_breakdown=school_breakdown,
                teacher_breakdown=teacher_breakdown,
                summary_stats=summary_stats
            )
            db.session.add(cache_record)
        
        db.session.commit()
        print(f"Virtual session district cache saved for {district_name} {virtual_year}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving virtual session district cache: {str(e)}")


def invalidate_virtual_session_caches(virtual_year=None):
    """
    Invalidate virtual session caches for a specific year or all years.
    
    Args:
        virtual_year: Specific year to invalidate, or None for all years
    """
    try:
        if virtual_year:
            # Invalidate specific year
            VirtualSessionReportCache.query.filter_by(virtual_year=virtual_year).delete()
            VirtualSessionDistrictCache.query.filter_by(virtual_year=virtual_year).delete()
        else:
            # Invalidate all caches
            VirtualSessionReportCache.query.delete()
            VirtualSessionDistrictCache.query.delete()
        
        db.session.commit()
        print(f"Virtual session caches invalidated for {virtual_year or 'all years'}")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error invalidating virtual session caches: {str(e)}")

# --- End Cache Management Functions ---

# --- Data Processing Helper Functions ---

def apply_runtime_filters(session_data, filters):
    """
    Apply runtime filters to session data.
    
    Args:
        session_data: List of session records
        filters: Dictionary of filter criteria
        
    Returns:
        Filtered session data
    """
    filtered_data = []
    
    for session in session_data:
        # Apply career cluster filter
        if filters.get('career_cluster'):
            if not session.get('topic_theme') or filters['career_cluster'].lower() not in session['topic_theme'].lower():
                continue
        
        # Apply school filter
        if filters.get('school'):
            if not session.get('school_name') or filters['school'].lower() not in session['school_name'].lower():
                continue
        
        # Apply district filter
        if filters.get('district'):
            if session.get('district') != filters['district']:
                continue
        
        # Apply status filter
        if filters.get('status'):
            if session.get('status') != filters['status']:
                continue
        
        filtered_data.append(session)
    
    return filtered_data


def calculate_summaries_from_sessions(session_data):
    """
    Calculate district summaries and overall summary from session data.
    
    Args:
        session_data: List of session records
        
    Returns:
        Tuple of (district_summaries, overall_summary)
    """
    # Filter districts to only show allowed ones
    allowed_districts = {
        "Hickman Mills School District",
        "Grandview School District",
        "Kansas City Kansas Public Schools"
    }
    
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
    
    # Convert sets to counts and filter allowed districts
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
    
    district_summaries = {k: v for k, v in district_summaries.items() if k in allowed_districts}
    
    # Prepare overall summary stats
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
    
    return district_summaries, overall_summary


def apply_sorting_and_pagination(session_data, request_args, current_filters):
    """
    Apply sorting and pagination to session data.
    
    Args:
        session_data: List of session records
        request_args: Request arguments for sorting/pagination
        current_filters: Current filter settings
        
    Returns:
        Dictionary with paginated_data and pagination info
    """
    # Apply sorting
    sort_column = request_args.get('sort', 'date')
    sort_order = request_args.get('order', 'desc')
    
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
                    if session['date']:
                        date_parts = session['date'].split('/')
                        if len(date_parts) == 3:
                            month = int(date_parts[0])
                            day = int(date_parts[1])
                            year = int(date_parts[2])
                            if year < 50:
                                year += 2000
                            else:
                                year += 1900
                            return datetime(year, month, day)
                        elif len(date_parts) == 2:
                            month = int(date_parts[0])
                            day = int(date_parts[1])
                            virtual_year_start = int(current_filters['year'].split('-')[0])
                            if month >= 7:
                                year = virtual_year_start
                            else:
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
            def string_sort_key(session):
                value = session.get(sortable_columns[sort_column], '') or ''
                return str(value).lower()
            session_data.sort(key=string_sort_key, reverse=reverse_order)
    
    # Add sorting info to current_filters for template
    current_filters['sort'] = sort_column
    current_filters['order'] = sort_order
    
    # Apply pagination
    try:
        page = int(request_args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    try:
        per_page = int(request_args.get('per_page', 25))
        if per_page < 1:
            per_page = 25
    except ValueError:
        per_page = 25
    
    total_records = len(session_data)
    total_pages = (total_records + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = session_data[start_idx:end_idx]
    
    pagination = {
        'current_page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_records': total_records
    }
    
    return {
        'paginated_data': paginated_data,
        'pagination': pagination
    }


def get_google_sheet_url(virtual_year):
    """
    Get Google Sheet URL for a virtual year.
    
    Args:
        virtual_year: The virtual year to get sheet for
        
    Returns:
        Google Sheet URL or None
    """
    google_sheet = GoogleSheet.query.filter_by(academic_year=virtual_year, purpose='virtual_sessions').first()
    if google_sheet and google_sheet.decrypted_sheet_id:
        return f"https://docs.google.com/spreadsheets/d/{google_sheet.decrypted_sheet_id}"
    return None


def compute_virtual_session_data(virtual_year, date_from, date_to, filters):
    """
    Compute virtual session data from database.
    
    Args:
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date
        filters: Filter criteria
        
    Returns:
        Tuple of (session_data, district_summaries, overall_summary, filter_options)
    """
    # Base query for virtual session events
    base_query = Event.query.options(
        joinedload(Event.districts),
        joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher).joinedload(Teacher.school)
    ).filter(
        Event.type == EventType.VIRTUAL_SESSION,
        Event.start_date >= date_from,
        Event.start_date <= date_to
    )
    
    # Apply database-level filters
    if filters.get('career_cluster'):
        base_query = base_query.filter(Event.series.ilike(f'%{filters["career_cluster"]}%'))
    
    if filters.get('status'):
        base_query = base_query.filter(Event.status == filters['status'])

    # Get all events
    events = base_query.order_by(Event.start_date.desc()).all()
    
    # Build session data
    session_data = []
    all_districts = set()
    all_schools = set()
    all_career_clusters = set()
    all_statuses = set()
    
    for event in events:
        # Get all teacher registrations for this event
        teacher_registrations = event.teacher_registrations
        
        if teacher_registrations:
            # Create a row for each teacher registration
            for teacher_reg in teacher_registrations:
                teacher = teacher_reg.teacher
                
                # Get school information
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
                if filters.get('district') and district_name != filters['district']:
                    continue
                
                # Apply school filter if specified
                if filters.get('school') and school_name and filters['school'].lower() not in school_name.lower():
                    continue
                
                session_data.append({
                    'event_id': event.id,
                    'status': teacher_reg.status or 'registered',
                    'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
                    'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                    'session_type': event.additional_information or '',
                    'teacher_name': f"{teacher.first_name} {teacher.last_name}" if teacher else '',
                    'teacher_id': teacher.id if teacher else None,
                    'school_name': school_name,
                    'school_level': school_level,
                    'district': district_name,
                    'session_title': event.title,
                    'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                    'presenter_data': [{'id': v.id, 'name': v.full_name} for v in event.volunteers] if event.volunteers else [],
                    'topic_theme': event.series or '',
                    'session_link': event.registration_link or '',
                    'session_id': event.session_id or '',
                    'participant_count': event.participant_count or 0,
                    'duration': event.duration or 0,
                    'is_simulcast': teacher_reg.is_simulcast
                })
                
                # Collect filter options
                if district_name:
                    all_districts.add(district_name)
                if school_name:
                    all_schools.add(school_name)
                if event.series:
                    all_career_clusters.add(event.series)
                if teacher_reg.status:
                    all_statuses.add(teacher_reg.status)
                    
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
            if filters.get('district') and district_name != filters['district']:
                continue
            
            session_data.append({
                'event_id': event.id,
                'status': event.status.value if event.status else '',
                'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'session_type': event.additional_information or '',
                'teacher_name': '',
                'teacher_id': None,
                'school_name': '',
                'school_level': '',
                'district': district_name,
                'session_title': event.title,
                'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                'presenter_data': [{'id': v.id, 'name': v.full_name} for v in event.volunteers] if event.volunteers else [],
                'topic_theme': event.series or '',
                'session_link': event.registration_link or '',
                'session_id': event.session_id or '',
                'participant_count': event.participant_count or 0,
                'duration': event.duration or 0,
                'is_simulcast': False
            })
            
            # Collect filter options
            if district_name:
                all_districts.add(district_name)
            if event.series:
                all_career_clusters.add(event.series)
            if event.status:
                all_statuses.add(event.status.value)
    
    # Calculate summaries
    district_summaries, overall_summary = calculate_summaries_from_sessions(session_data)
    
    # Filter districts to only show allowed ones
    allowed_districts = {
        "Hickman Mills School District",
        "Grandview School District", 
        "Kansas City Kansas Public Schools"
    }
    filtered_districts = [d for d in all_districts if d in allowed_districts]
    
    # Prepare filter options
    virtual_year_options = generate_school_year_options()
    filter_options = {
        'school_years': virtual_year_options,
        'career_clusters': sorted(list(all_career_clusters)),
        'schools': sorted(list(all_schools)),
        'districts': sorted(filtered_districts),
        'statuses': sorted(list(all_statuses))
    }
    
    return session_data, district_summaries, overall_summary, filter_options


def compute_virtual_session_district_data(district_name, virtual_year, date_from, date_to):
    """
    Compute district-specific virtual session data from database.
    
    Args:
        district_name: Name of the district
        virtual_year: The virtual year
        date_from: Start date
        date_to: End date
        
    Returns:
        Tuple of (session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats)
    """
    # Base query for virtual session events
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
        
        # Create aggregated session record
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
    
    # Calculate summary statistics
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
    
    # We need to track teachers by their actual database objects to get IDs
    # Re-query events with teacher data to get proper teacher IDs
    teacher_sessions = {}  # teacher_id -> session_count
    teacher_details = {}   # teacher_id -> {name, school, id}
    
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
            
        # Process teacher registrations to get proper IDs
        for teacher_reg in event.teacher_registrations:
            teacher = teacher_reg.teacher
            if teacher:
                teacher_id = teacher.id
                teacher_name = f"{teacher.first_name} {teacher.last_name}"
                
                # Get school info
                school_name = 'N/A'
                if hasattr(teacher, 'school_obj') and teacher.school_obj:
                    school_name = teacher.school_obj.name
                elif teacher.school_id:
                    school_obj = School.query.get(teacher.school_id)
                    if school_obj:
                        school_name = school_obj.name
                
                # Track teacher sessions
                if teacher_id not in teacher_sessions:
                    teacher_sessions[teacher_id] = 0
                    teacher_details[teacher_id] = {
                        'id': teacher_id,
                        'name': teacher_name,
                        'school': school_name
                    }
                teacher_sessions[teacher_id] += 1
                total_teachers.add(teacher_name)
    
    # Build teacher breakdown from the collected data
    for teacher_id, session_count in teacher_sessions.items():
        teacher_info = teacher_details[teacher_id]
        teacher_breakdown[teacher_id] = {
            'id': teacher_info['id'],
            'name': teacher_info['name'],
            'school': teacher_info['school'],
            'sessions': session_count
        }
    
    for session in session_data:
        
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
    
    # Convert breakdowns to sorted lists
    school_breakdown_list = sorted(school_breakdown.values(), key=lambda x: x['sessions'], reverse=True)
    teacher_breakdown_list = sorted(teacher_breakdown.values(), key=lambda x: x['sessions'], reverse=True)
    
    # Calculate monthly statistics
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
            'session_id': session['session_id'],
            'presenter': session['presenter']
        })
    
    # Finalize monthly stats
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
    
    sorted_monthly_stats = dict(sorted(monthly_stats.items()))
    
    # Prepare summary statistics
    # Calculate estimated students as unique teachers * 25
    estimated_students = len(total_teachers) * 25
    
    summary_stats = {
        'total_teachers': len(total_teachers),
        'total_students': estimated_students,
        'total_unique_sessions': len(total_unique_sessions),
        'total_experiences': total_experiences,
        'total_organizations': len(total_organizations),
        'total_professionals': len(total_professionals),
        'total_professionals_of_color': 0,  # Always 0 until we have demographic data
        'total_schools': len(total_schools)
    }
    
    return session_data, sorted_monthly_stats, school_breakdown_list, teacher_breakdown_list, summary_stats

# --- End Data Processing Helper Functions ---


def load_routes(bp):
    @bp.route('/reports/virtual/usage')
    @login_required
    def virtual_usage():
        # Get filter parameters - Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()  # Changed from get_current_school_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)  # Changed variable name
        
        # Check if refresh is requested
        refresh_requested = request.args.get('refresh', '0') == '1'
        
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
        
        # Check if we're using default full year date range (for caching)
        is_full_year = (date_from == default_date_from and date_to == default_date_to)
        
        # If refresh is requested, invalidate cache for this virtual year
        if refresh_requested and is_full_year:
            invalidate_virtual_session_caches(selected_virtual_year)
            print(f"Cache invalidated for virtual session report {selected_virtual_year}")
        
        # Try to get cached data for full year queries
        cached_data = None
        is_cached = False
        last_refreshed = None
        
        if is_full_year and not refresh_requested:
            cached_data = get_virtual_session_cache(selected_virtual_year, date_from, date_to)
            if cached_data:
                is_cached = True
                last_refreshed = cached_data.last_updated
                print(f"Using cached data for virtual session report {selected_virtual_year}")
                # Use cached data
                session_data = cached_data.session_data
                district_summaries = cached_data.district_summaries
                overall_summary = cached_data.overall_summary
                filter_options = cached_data.filter_options
                
                # Check if cached data has the new fields and invalidate if missing
                if session_data and len(session_data) > 0:
                    sample_session = session_data[0]
                    if 'teacher_id' not in sample_session or 'presenter_data' not in sample_session:
                        # Force fresh data if new fields are missing
                        invalidate_virtual_session_caches(selected_virtual_year)
                        # Recompute
                        session_data, district_summaries, overall_summary, filter_options = compute_virtual_session_data(
                            selected_virtual_year, date_from, date_to, current_filters
                        )
                        is_cached = False
                
                # Apply runtime filters if any
                if any([current_filters['career_cluster'], current_filters['school'], 
                       current_filters['district'], current_filters['status']]):
                    session_data = apply_runtime_filters(session_data, current_filters)
                    # Recalculate summaries based on filtered data
                    district_summaries, overall_summary = calculate_summaries_from_sessions(session_data)
                
                # Apply sorting and pagination as before
                session_data = apply_sorting_and_pagination(session_data, request.args, current_filters)
                
                return render_template(
                    'reports/virtual_usage.html',
                    session_data=session_data['paginated_data'],
                    filter_options=filter_options,
                    current_filters=current_filters,
                    pagination=session_data['pagination'],
                    google_sheet_url=get_google_sheet_url(selected_virtual_year),
                    district_summaries=district_summaries,
                    overall_summary=overall_summary,
                    last_refreshed=last_refreshed,
                    is_cached=is_cached
                )
        
        # If no cache or not full year, compute data fresh
        print(f"Computing fresh data for virtual session report {selected_virtual_year}")
        session_data, district_summaries, overall_summary, filter_options = compute_virtual_session_data(
            selected_virtual_year, date_from, date_to, current_filters
        )
        
        # Cache the data if it's a full year query
        if is_full_year:
            # Cache the unfiltered data
            unfiltered_data, unfiltered_district_summaries, unfiltered_overall_summary, _ = compute_virtual_session_data(
                selected_virtual_year, date_from, date_to, {}  # No filters for cache
            )
            save_virtual_session_cache(
                selected_virtual_year, date_from, date_to,
                unfiltered_data, unfiltered_district_summaries, 
                unfiltered_overall_summary, filter_options
            )
            # Set the last refreshed time for this fresh data
            last_refreshed = datetime.now(timezone.utc)
        
        # Apply sorting and pagination
        session_result = apply_sorting_and_pagination(session_data, request.args, current_filters)
        
        return render_template(
            'reports/virtual_usage.html',
            session_data=session_result['paginated_data'],
            filter_options=filter_options,
            current_filters=current_filters,
            pagination=session_result['pagination'],
            google_sheet_url=get_google_sheet_url(selected_virtual_year),
            district_summaries=district_summaries,
            overall_summary=overall_summary,
            last_refreshed=last_refreshed,
            is_cached=is_cached
        )

    @bp.route('/reports/virtual/usage/district/<district_name>')
    @login_required
    def virtual_usage_district(district_name):
        # Get filter parameters: Use virtual year instead of school year
        default_virtual_year = get_current_virtual_year()
        selected_virtual_year = request.args.get('year', default_virtual_year)
        
        # Check if refresh is requested
        refresh_requested = request.args.get('refresh', '0') == '1'
        
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
        
        # Check if we're using default full year date range (for caching)
        is_full_year = (date_from == default_date_from and date_to == default_date_to)
        
        # If refresh is requested, invalidate cache for this district and virtual year
        if refresh_requested and is_full_year:
            # Invalidate district cache
            cached_data = VirtualSessionDistrictCache.query.filter_by(
                district_name=district_name,
                virtual_year=selected_virtual_year,
                date_from=date_from.date(),
                date_to=date_to.date()
            ).first()
            if cached_data:
                db.session.delete(cached_data)
                db.session.commit()
            print(f"Cache invalidated for district {district_name} virtual session report {selected_virtual_year}")
        
        # Try to get cached data for full year queries
        cached_data = None
        is_cached = False
        last_refreshed = None
        
        if is_full_year and not refresh_requested:
            cached_data = get_virtual_session_district_cache(district_name, selected_virtual_year, date_from, date_to)
            if cached_data:
                is_cached = True
                last_refreshed = cached_data.last_updated
                print(f"Using cached data for district {district_name} virtual session report {selected_virtual_year}")
                
                # Check if cached data has the new teacher ID fields and correct student calculation
                teacher_breakdown = cached_data.teacher_breakdown
                summary_stats = cached_data.summary_stats
                
                needs_refresh = False
                
                # Check for missing teacher ID field
                if teacher_breakdown and len(teacher_breakdown) > 0:
                    sample_teacher = teacher_breakdown[0]
                    if 'id' not in sample_teacher:
                        print(f"DEBUG: Cached data missing teacher ID field, invalidating cache")
                        needs_refresh = True
                
                # Check if student calculation is using old method (not unique teachers * 25)
                if summary_stats and 'total_teachers' in summary_stats and 'total_students' in summary_stats:
                    expected_students = summary_stats['total_teachers'] * 25
                    actual_students = summary_stats['total_students']
                    if actual_students != expected_students:
                        print(f"DEBUG: Cached data using old student calculation ({actual_students} vs expected {expected_students}), invalidating cache")
                        needs_refresh = True
                
                if needs_refresh:
                    db.session.delete(cached_data)
                    db.session.commit()
                    # Force fresh data computation
                    session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats = compute_virtual_session_district_data(
                        district_name, selected_virtual_year, date_from, date_to
                    )
                    is_cached = False
                    last_refreshed = datetime.now(timezone.utc)
                    
                    # Cache the new data
                    save_virtual_session_district_cache(
                        district_name, selected_virtual_year, date_from, date_to,
                        session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats
                    )
                else:
                    # Use cached data
                    session_data = cached_data.session_data
                    monthly_stats = cached_data.monthly_stats
                    school_breakdown = cached_data.school_breakdown
                    summary_stats = cached_data.summary_stats
                
                return render_template(
                    'reports/virtual_usage_district.html',
                    district_name=district_name,
                    monthly_stats=monthly_stats,
                    current_filters=current_filters,
                    school_year_options=virtual_year_options,
                    total_teachers=summary_stats['total_teachers'],
                    total_students=summary_stats['total_students'],
                    total_unique_sessions=summary_stats['total_unique_sessions'],
                    total_experiences=summary_stats['total_experiences'],
                    total_organizations=summary_stats['total_organizations'],
                    total_professionals=summary_stats['total_professionals'],
                    total_professionals_of_color=summary_stats['total_professionals_of_color'],
                    total_schools=summary_stats['total_schools'],
                    school_breakdown=school_breakdown,
                    teacher_breakdown=teacher_breakdown,
                    session_data=session_data,
                    last_refreshed=last_refreshed,
                    is_cached=is_cached
                )
        
        # If no cache or not full year, compute data fresh
        print(f"Computing fresh data for district {district_name} virtual session report {selected_virtual_year}")
        session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats = compute_virtual_session_district_data(
            district_name, selected_virtual_year, date_from, date_to
        )
        
        # Cache the data if it's a full year query
        if is_full_year:
            save_virtual_session_district_cache(
                district_name, selected_virtual_year, date_from, date_to,
                session_data, monthly_stats, school_breakdown, teacher_breakdown, summary_stats
            )
            # Set the last refreshed time for this fresh data
            last_refreshed = datetime.now(timezone.utc)
        
        return render_template(
            'reports/virtual_usage_district.html',
            district_name=district_name,
            monthly_stats=monthly_stats,
            current_filters=current_filters,
            school_year_options=virtual_year_options,
            total_teachers=summary_stats['total_teachers'],
            total_students=summary_stats['total_students'],
            total_unique_sessions=summary_stats['total_unique_sessions'],
            total_experiences=summary_stats['total_experiences'],
            total_organizations=summary_stats['total_organizations'],
            total_professionals=summary_stats['total_professionals'],
            total_professionals_of_color=summary_stats['total_professionals_of_color'],
            total_schools=summary_stats['total_schools'],
            school_breakdown=school_breakdown,
            teacher_breakdown=teacher_breakdown,
            session_data=session_data,
            last_refreshed=last_refreshed,
            is_cached=is_cached
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
                        'teacher_id': teacher.id if teacher else None,
                        'school_name': school_name,
                        'school_level': school_level,
                        'district': district_name,
                        'session_title': event.title,
                        'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                        'presenter_data': [{'id': v.id, 'name': v.full_name} for v in event.volunteers] if event.volunteers else [],
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
                    'teacher_id': None,
                    'school_name': '',
                    'school_level': '',
                    'district': district_name,
                    'session_title': event.title,
                    'presenter': ', '.join([v.full_name for v in event.volunteers]) if event.volunteers else '',
                    'presenter_data': [{'id': v.id, 'name': v.full_name} for v in event.volunteers] if event.volunteers else [],
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

    @bp.route('/reports/virtual/breakdown')
    @login_required
    def virtual_breakdown():
        """
        Detailed breakdown of virtual sessions by month and category.
        
        Categories:
        - Successfully completed sessions
        - Number of simulcast + Sessions
        - Number of teacher canceled sessions
        - Number of teacher no shows
        - Number of pathful professional canceled/no shows sessions
        - Number of local professional canceled/no show sessions
        - Number of unfilled sessions
        """
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
            'date_to': date_to
        }
        
        # Base query for virtual session events
        base_query = Event.query.options(
            joinedload(Event.districts),
            joinedload(Event.teacher_registrations).joinedload(EventTeacher.teacher),
            joinedload(Event.volunteers),
            joinedload(Event.school_obj)  # Add school relationship for grade level analysis
        ).filter(
            Event.type == EventType.VIRTUAL_SESSION,
            Event.start_date >= date_from,
            Event.start_date <= date_to
        )
        
        events = base_query.all()
        
        # Initialize monthly breakdown data
        monthly_breakdown = {}
        
        # Create month entries for the full virtual year (August to July)
        virtual_year_start = int(selected_virtual_year.split('-')[0])
        months = [
            (virtual_year_start, 8, 'August'),
            (virtual_year_start, 9, 'September'),
            (virtual_year_start, 10, 'October'),
            (virtual_year_start, 11, 'November'),
            (virtual_year_start, 12, 'December'),
            (virtual_year_start + 1, 1, 'January'),
            (virtual_year_start + 1, 2, 'February'),
            (virtual_year_start + 1, 3, 'March'),
            (virtual_year_start + 1, 4, 'April'),
            (virtual_year_start + 1, 5, 'May'),
            (virtual_year_start + 1, 6, 'June'),
            (virtual_year_start + 1, 7, 'July')
        ]
        
        for year, month_num, month_name in months:
            month_key = f"{year}-{month_num:02d}"
            monthly_breakdown[month_key] = {
                'month_name': month_name,
                'year': year,
                'month': month_num,
                'successfully_completed': 0,
                'simulcast_sessions': 0,
                'teacher_canceled': 0,
                'teacher_no_shows': 0,
                'pathful_professional_canceled_no_shows': 0,
                'local_professional_canceled_no_shows': 0,
                'unfilled_sessions': 0
            }
        
        # Debug: Collect unique status strings to understand what we're working with
        unique_statuses = set()
        unique_additional_info = set()
        unique_series = set()
        unique_school_levels = set()
        
        # Process each event
        for event in events:
            if not event.start_date:
                continue
                
            month_key = f"{event.start_date.year}-{event.start_date.month:02d}"
            
            # Skip if not in our breakdown range
            if month_key not in monthly_breakdown:
                continue
            
            # Get the original status string for analysis
            original_status_raw = getattr(event, 'original_status_string', None)
            original_status = (original_status_raw or '').lower().strip()
            
            # Collect unique statuses for debugging
            if original_status:
                unique_statuses.add(original_status)
            
            # Collect unique additional info (session types)
            if event.additional_information:
                unique_additional_info.add(event.additional_information)
            
            # Collect unique series (topics)
            if event.series:
                unique_series.add(event.series)
            
            # Collect unique school levels
            if event.school_obj and event.school_obj.level:
                unique_school_levels.add(event.school_obj.level)
            
            # Categorize based on original status string (primary source of truth)
            if 'successfully completed' in original_status:
                monthly_breakdown[month_key]['successfully_completed'] += 1
            
            elif 'simulcast' in original_status:
                monthly_breakdown[month_key]['simulcast_sessions'] += 1
            
            elif 'teacher' in original_status and ('cancelation' in original_status or 'cancellation' in original_status):
                monthly_breakdown[month_key]['teacher_canceled'] += 1
            
            elif 'teacher no-show' in original_status or 'teacher no show' in original_status:
                monthly_breakdown[month_key]['teacher_no_shows'] += 1
            
            elif 'pathful professional' in original_status:
                monthly_breakdown[month_key]['pathful_professional_canceled_no_shows'] += 1
            
            elif 'local professional' in original_status:
                monthly_breakdown[month_key]['local_professional_canceled_no_shows'] += 1
            
            elif 'technical difficulties' in original_status or original_status == 'count':
                monthly_breakdown[month_key]['unfilled_sessions'] += 1
            
            # Fallback to event status if no original status string
            elif not original_status:
                event_status = event.status
                event_status_str = event_status.value.lower() if event_status else ''
                

                
                if event_status == EventStatus.COMPLETED:
                    monthly_breakdown[month_key]['successfully_completed'] += 1
                elif event_status == EventStatus.SIMULCAST:
                    monthly_breakdown[month_key]['simulcast_sessions'] += 1
                elif event_status == EventStatus.NO_SHOW and not event.volunteers:
                    monthly_breakdown[month_key]['unfilled_sessions'] += 1
                elif event_status == EventStatus.CANCELLED and not event.volunteers:
                    monthly_breakdown[month_key]['unfilled_sessions'] += 1
                
                # Check for professional statuses in main event status
                elif 'pathful professional' in event_status_str:
                    monthly_breakdown[month_key]['pathful_professional_canceled_no_shows'] += 1
                elif 'local professional' in event_status_str:
                    monthly_breakdown[month_key]['local_professional_canceled_no_shows'] += 1
            
            # Check teacher registrations for additional status information
            for teacher_reg in event.teacher_registrations:
                tr_status = (teacher_reg.status or '').lower().strip()
                
                # Check for professional statuses FIRST (before teacher-specific logic)
                if 'pathful professional' in tr_status:
                    monthly_breakdown[month_key]['pathful_professional_canceled_no_shows'] += 1
                elif 'local professional' in tr_status:
                    monthly_breakdown[month_key]['local_professional_canceled_no_shows'] += 1
                
                # Count teacher-specific cancellations and no-shows (only if not professional)
                elif 'cancel' in tr_status and 'teacher' not in original_status:
                    monthly_breakdown[month_key]['teacher_canceled'] += 1
                elif ('no-show' in tr_status or 'no show' in tr_status) and 'teacher' not in original_status:
                    monthly_breakdown[month_key]['teacher_no_shows'] += 1
            
            # Check for simulcast from teacher registrations (additional simulcast detection)
            simulcast_teacher_count = sum(1 for tr in event.teacher_registrations if tr.is_simulcast)
            if simulcast_teacher_count > 0 and 'simulcast' not in original_status:
                monthly_breakdown[month_key]['simulcast_sessions'] += 1
        
        # Calculate year-to-date totals
        ytd_totals = {
            'successfully_completed': 0,
            'simulcast_sessions': 0,
            'teacher_canceled': 0,
            'teacher_no_shows': 0,
            'pathful_professional_canceled_no_shows': 0,
            'local_professional_canceled_no_shows': 0,
            'unfilled_sessions': 0
        }
        
        for month_data in monthly_breakdown.values():
            for key in ytd_totals:
                ytd_totals[key] += month_data[key]
        
        # COMPREHENSIVE ANALYTICS SECTIONS
        
        # 1. Current Running Count - detailed status breakdown
        running_count = {
            'unfilled': 0,
            'successfully_completed': 0,
            'teacher_cancelation': 0,
            'formerly_in_person_completed': 0,
            'formerly_in_person_canceled': 0,
            'professional_cancel_no_show': 0,
            'inclement_weather_cancellation': 0,
            'withdrawn_time_constraint': 0,
            'moved_to_in_person_session': 0,
            'teacher_no_show': 0,
            'covid19_cancelation': 0,
            'white_label_completed': 0,
            'white_label_unfilled': 0,
            'technical_difficulties': 0,
            'local_professional_cancellation': 0,
            'pathful_professional_cancellation': 0,
            'local_professional_no_show': 0,
            'pathful_professional_no_show': 0,
            'formerly_in_person_duplicate': 0,
            'white_label_canceled': 0,
            'simulcast': 0,
            'count': 0
        }
        
        # 2. District-wise completed sessions
        district_completed = {}
        
        # 3. Topic-wise session counts
        topic_counts = {}
        
        # 4. Session type breakdown
        session_types = {
            'teacher_requested': {'all': 0, 'completed': 0},
            'industry_chat': {'all': 0, 'completed': 0},
            'formerly_in_person': {'all': 0, 'completed': 0},
            'other': {'all': 0, 'completed': 0},
            'kansas_city_series': {'all': 0, 'completed': 0}
        }
        
        # 5. Grade level breakdown
        grade_levels = {
            'elementary': {'all': 0, 'completed_no_simulcast': 0},
            'middle': {'all': 0, 'completed_no_simulcast': 0},
            'high': {'all': 0, 'completed_no_simulcast': 0},
            'grade_level_not_set': {'all': 0, 'completed_no_simulcast': 0},
            'pre_k': {'all': 0, 'completed_no_simulcast': 0}
        }
        
        # 6. Teacher attendance metrics
        teacher_attendance = {
            'more_than_one_teacher_present': 0,
            'total_number_of_sessions': len(events)
        }
        
        # Process events for comprehensive analytics
        for event in events:
            # Get status information
            original_status_raw = getattr(event, 'original_status_string', None)
            original_status = (original_status_raw or '').lower().strip()
            event_status = event.status
            
            # Running count analysis - check multiple sources like monthly breakdown
            event_categorized = False
            
            # Check original status first
            if 'successfully completed' in original_status:
                running_count['successfully_completed'] += 1
                event_categorized = True
            elif 'simulcast' in original_status:
                running_count['simulcast'] += 1
                event_categorized = True
            elif 'teacher' in original_status and ('cancelation' in original_status or 'cancellation' in original_status):
                running_count['teacher_cancelation'] += 1
                event_categorized = True
            elif 'teacher no-show' in original_status or 'teacher no show' in original_status:
                running_count['teacher_no_show'] += 1
                event_categorized = True
            elif 'pathful professional cancellation' in original_status:
                running_count['pathful_professional_cancellation'] += 1
                event_categorized = True
            elif 'pathful professional no-show' in original_status or 'pathful professional no show' in original_status:
                running_count['pathful_professional_no_show'] += 1
                event_categorized = True
            elif 'local professional cancellation' in original_status:
                running_count['local_professional_cancellation'] += 1
                event_categorized = True
            elif 'local professional no-show' in original_status or 'local professional no show' in original_status:
                running_count['local_professional_no_show'] += 1
                event_categorized = True
            elif 'technical difficulties' in original_status:
                running_count['technical_difficulties'] += 1
                event_categorized = True
            elif 'inclement weather' in original_status:
                running_count['inclement_weather_cancellation'] += 1
                event_categorized = True
            elif 'moved to in-person' in original_status:
                running_count['moved_to_in_person_session'] += 1
                event_categorized = True
            elif 'white label completed' in original_status or 'white lable completed' in original_status:
                running_count['white_label_completed'] += 1
                event_categorized = True
            elif 'white label unfilled' in original_status or 'white lable unfilled' in original_status:
                running_count['white_label_unfilled'] += 1
                event_categorized = True
            elif 'formerly in-person' in original_status and 'completed' in original_status:
                running_count['formerly_in_person_completed'] += 1
                event_categorized = True
            elif 'formerly in-person' in original_status and ('canceled' in original_status or 'cancelled' in original_status):
                running_count['formerly_in_person_canceled'] += 1
                event_categorized = True
            elif 'covid' in original_status:
                running_count['covid19_cancelation'] += 1
                event_categorized = True
            elif original_status == 'count':
                running_count['count'] += 1
                event_categorized = True
            
            # If not categorized by original status, check teacher registrations
            if not event_categorized:
                for teacher_reg in event.teacher_registrations:
                    tr_status = (teacher_reg.status or '').lower().strip()
                    
                    # Check for professional statuses FIRST
                    if 'pathful professional' in tr_status:
                        if 'no-show' in tr_status or 'no show' in tr_status:
                            running_count['pathful_professional_no_show'] += 1
                        else:
                            running_count['pathful_professional_cancellation'] += 1
                        event_categorized = True
                        break
                    elif 'local professional' in tr_status:
                        if 'no-show' in tr_status or 'no show' in tr_status:
                            running_count['local_professional_no_show'] += 1
                        else:
                            running_count['local_professional_cancellation'] += 1
                        event_categorized = True
                        break
                    # Check for teacher-specific statuses
                    elif 'cancel' in tr_status and 'professional' not in tr_status:
                        running_count['teacher_cancelation'] += 1
                        event_categorized = True
                        break
                    elif ('no-show' in tr_status or 'no show' in tr_status) and 'professional' not in tr_status:
                        running_count['teacher_no_show'] += 1
                        event_categorized = True
                        break
                
                # Check for simulcast from teacher registrations
                if not event_categorized:
                    simulcast_teacher_count = sum(1 for tr in event.teacher_registrations if tr.is_simulcast)
                    if simulcast_teacher_count > 0:
                        running_count['simulcast'] += 1
                        event_categorized = True
            
            # If still not categorized, check event status
            if not event_categorized:
                if event_status == EventStatus.COMPLETED:
                    running_count['successfully_completed'] += 1
                    event_categorized = True
                elif event_status == EventStatus.SIMULCAST:
                    running_count['simulcast'] += 1
                    event_categorized = True
                elif event_status == EventStatus.CANCELLED and not event.volunteers:
                    running_count['unfilled'] += 1
                    event_categorized = True
                elif event_status == EventStatus.NO_SHOW and not event.volunteers:
                    running_count['unfilled'] += 1
                    event_categorized = True
            
            # Default to unfilled if still not categorized
            if not event_categorized:
                running_count['unfilled'] += 1
            
            # District-wise completed sessions - check if this event is successfully completed
            event_is_completed = False
            
            # Check multiple sources for "successfully completed" status
            if 'successfully completed' in original_status:
                event_is_completed = True
            elif event_status == EventStatus.COMPLETED:
                event_is_completed = True
            else:
                # Check teacher registrations for completion indicators
                for teacher_reg in event.teacher_registrations:
                    tr_status = (teacher_reg.status or '').lower().strip()
                    if 'successfully completed' in tr_status or 'attended' in tr_status or 'completed' in tr_status:
                        event_is_completed = True
                        break
            
            # Count by district if successfully completed
            if event_is_completed and event.districts:
                for district in event.districts:
                    district_name = district.name
                    if district_name not in district_completed:
                        district_completed[district_name] = 0
                    district_completed[district_name] += 1
            
            # Topic-wise session counts (using series field which contains Topic/Theme)
            if event.series and event.series.strip():
                topic = event.series.strip()
                if topic not in topic_counts:
                    topic_counts[topic] = 0
                topic_counts[topic] += 1
            
            # Session type analysis (using additional_information field)
            session_type = event.additional_information or 'other'
            session_type_clean = session_type.lower().replace(' ', '_').replace('-', '_')
            
            # Map to our predefined session types or use 'other'
            if session_type_clean in session_types:
                session_types[session_type_clean]['all'] += 1
                if 'successfully completed' in original_status:
                    session_types[session_type_clean]['completed'] += 1
            else:
                session_types['other']['all'] += 1
                if 'successfully completed' in original_status:
                    session_types['other']['completed'] += 1
            
            # Grade level analysis (using school level)
            grade_level = None
            if event.school_obj and event.school_obj.level:
                grade_level = event.school_obj.level.lower().strip()
            
            if grade_level:
                # Map school levels to our grade level categories
                if grade_level in ['elementary', 'elem']:
                    grade_key = 'elementary'
                elif grade_level in ['middle', 'mid']:
                    grade_key = 'middle'
                elif grade_level in ['high', 'secondary']:
                    grade_key = 'high'
                elif grade_level in ['pre-k', 'prek', 'pre_k']:
                    grade_key = 'pre_k'
                else:
                    grade_key = 'grade_level_not_set'
                
                grade_levels[grade_key]['all'] += 1
                # Count completed (no simulcast)
                if 'successfully completed' in original_status:
                    grade_levels[grade_key]['completed_no_simulcast'] += 1
            else:
                grade_levels['grade_level_not_set']['all'] += 1
                if 'successfully completed' in original_status:
                    grade_levels['grade_level_not_set']['completed_no_simulcast'] += 1
            
            # Teacher attendance analysis
            teacher_count = len(event.teacher_registrations)
            if teacher_count > 1:
                teacher_attendance['more_than_one_teacher_present'] += 1
        
        # Calculate professional cancel/no-show total for running count
        running_count['professional_cancel_no_show'] = (
            running_count['pathful_professional_cancellation'] +
            running_count['pathful_professional_no_show'] +
            running_count['local_professional_cancellation'] +
            running_count['local_professional_no_show']
        )
        
        # Sort districts and topics for consistent display
        district_completed = dict(sorted(district_completed.items()))
        topic_counts = dict(sorted(topic_counts.items()))
        
        # Debug output to understand the data
        print(f"DEBUG: Found {len(events)} events")
        print(f"DEBUG: Unique statuses: {sorted(unique_statuses)}")
        print(f"DEBUG: Unique additional info: {sorted(unique_additional_info)}")
        print(f"DEBUG: Unique series: {sorted(unique_series)}")
        print(f"DEBUG: Unique school levels: {sorted(unique_school_levels)}")
        print(f"DEBUG: Running count totals: {running_count}")
        print(f"DEBUG: Topic counts: {topic_counts}")
        print(f"DEBUG: District completed: {district_completed}")
        
        # Show overall completion stats
        total_completed = sum(district_completed.values()) if district_completed else 0
        total_successfully_completed = running_count.get('successfully_completed', 0)
        print(f"DEBUG: Total completed by district: {total_completed}")
        print(f"DEBUG: Total successfully completed in running count: {total_successfully_completed}")
        
        # Prepare data for template
        virtual_year_options = generate_school_year_options()
        
        return render_template(
            'reports/virtual_breakdown.html',
            monthly_breakdown=monthly_breakdown,
            ytd_totals=ytd_totals,
            running_count=running_count,
            district_completed=district_completed,
            topic_counts=topic_counts,
            session_types=session_types,
            grade_levels=grade_levels,
            teacher_attendance=teacher_attendance,
            current_filters=current_filters,
            virtual_year_options=virtual_year_options,
            months=months
        )

    @bp.route('/reports/virtual/google-sheets')
    @login_required
    def virtual_google_sheets():
        """Manage Google Sheets for virtual district reports"""
        virtual_year = request.args.get('year', get_current_virtual_year())
        
        # Get all Google Sheets for virtual district reports for this year
        sheets = GoogleSheet.query.filter_by(
            academic_year=virtual_year,
            purpose='virtual_district_reports'
        ).order_by(GoogleSheet.sheet_name).all()
        
        # Get only allowed districts for dropdown
        allowed_district_names = {
            "Hickman Mills School District",
            "Grandview School District",
            "Kansas City Kansas Public Schools"
        }
        districts = District.query.filter(
            District.name.in_(allowed_district_names)
        ).order_by(District.name).all()
        
        return render_template(
            'reports/virtual_google_sheets.html',
            sheets=sheets,
            districts=districts,
            virtual_year=virtual_year,
            virtual_year_options=generate_school_year_options()
        )
    
    @bp.route('/reports/virtual/google-sheets/create', methods=['POST'])
    @login_required
    def create_virtual_google_sheet():
        """Create a new Google Sheet for virtual district reports"""
        try:
            virtual_year = request.form.get('virtual_year')
            district_name = request.form.get('district_name')
            sheet_id = request.form.get('sheet_id')
            sheet_name = request.form.get('sheet_name')
            
            if not all([virtual_year, district_name, sheet_id, sheet_name]):
                flash('All fields are required.', 'error')
                return redirect(url_for('report.virtual_google_sheets', year=virtual_year))
            
            # Check if sheet already exists for this district and year
            existing_sheet = GoogleSheet.query.filter_by(
                academic_year=virtual_year,
                purpose='virtual_district_reports',
                sheet_name=sheet_name
            ).first()
            
            if existing_sheet:
                flash(f'A Google Sheet with this name already exists for {virtual_year}.', 'error')
                return redirect(url_for('report.virtual_google_sheets', year=virtual_year))
            
            # Create new Google Sheet record
            new_sheet = GoogleSheet(
                academic_year=virtual_year,
                purpose='virtual_district_reports',
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                created_by=current_user.id
            )
            
            db.session.add(new_sheet)
            db.session.commit()
            
            flash(f'Google Sheet "{sheet_name}" created successfully for {district_name}.', 'success')
            return redirect(url_for('report.virtual_google_sheets', year=virtual_year))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating Google Sheet: {str(e)}', 'error')
            return redirect(url_for('report.virtual_google_sheets', year=virtual_year))
    
    @bp.route('/reports/virtual/google-sheets/<int:sheet_id>/update', methods=['POST'])
    @login_required
    def update_virtual_google_sheet(sheet_id):
        """Update an existing Google Sheet"""
        try:
            sheet = GoogleSheet.query.get_or_404(sheet_id)
            
            sheet_url = request.form.get('sheet_id')
            sheet_name = request.form.get('sheet_name')
            
            if not all([sheet_url, sheet_name]):
                flash('Sheet URL and name are required.', 'error')
                return redirect(url_for('report.virtual_google_sheets', year=sheet.academic_year))
            
            sheet.update_sheet_id(sheet_url)
            sheet.sheet_name = sheet_name
            
            db.session.commit()
            
            flash(f'Google Sheet "{sheet_name}" updated successfully.', 'success')
            return redirect(url_for('report.virtual_google_sheets', year=sheet.academic_year))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating Google Sheet: {str(e)}', 'error')
            return redirect(url_for('report.virtual_google_sheets'))
    
    @bp.route('/reports/virtual/google-sheets/<int:sheet_id>/delete', methods=['POST'])
    @login_required
    def delete_virtual_google_sheet(sheet_id):
        """Delete a Google Sheet"""
        try:
            sheet = GoogleSheet.query.get_or_404(sheet_id)
            virtual_year = sheet.academic_year
            sheet_name = sheet.sheet_name
            
            db.session.delete(sheet)
            db.session.commit()
            
            flash(f'Google Sheet "{sheet_name}" deleted successfully.', 'success')
            return redirect(url_for('report.virtual_google_sheets', year=virtual_year))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting Google Sheet: {str(e)}', 'error')
            return redirect(url_for('report.virtual_google_sheets'))
    
    @bp.route('/reports/virtual/google-sheets/<int:sheet_id>/view')
    @login_required
    def view_virtual_google_sheet(sheet_id):
        """Redirect to the Google Sheet"""
        sheet = GoogleSheet.query.get_or_404(sheet_id)
        
        if not sheet.decrypted_sheet_id:
            flash('Google Sheet URL not available.', 'error')
            return redirect(url_for('report.virtual_google_sheets', year=sheet.academic_year))
        
        # Create Google Sheets URL
        google_sheets_url = f"https://docs.google.com/spreadsheets/d/{sheet.decrypted_sheet_id}/edit"
        
        return redirect(google_sheets_url)
    
    @bp.route('/reports/virtual/district/<district_name>/google-sheet')
    @login_required
    def get_district_google_sheet(district_name):
        """Get Google Sheet for a specific district and year"""
        virtual_year = request.args.get('year', get_current_virtual_year())
        
        # Look for a sheet that matches this district in the name
        sheet = GoogleSheet.query.filter(
            GoogleSheet.academic_year == virtual_year,
            GoogleSheet.purpose == 'virtual_district_reports',
            GoogleSheet.sheet_name.ilike(f'%{district_name}%')
        ).first()
        
        if sheet:
            return redirect(url_for('report.view_virtual_google_sheet', sheet_id=sheet.id))
        else:
            flash(f'No Google Sheet found for {district_name} in {virtual_year}.', 'warning')
            return redirect(url_for('report.virtual_usage_district', district_name=district_name, year=virtual_year))
