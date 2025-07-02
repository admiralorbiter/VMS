from flask import render_template, request, jsonify, make_response, send_file
from flask_login import login_required
from sqlalchemy import any_, extract
from models.event import Event, EventAttendance, EventType, EventStatus, EventStudentParticipation
from datetime import datetime, timedelta
from models.school_model import School
from models.student import Student
from models.teacher import Teacher
# from models.upcoming_events import UpcomingEvent  # Moved to microservice
from models.volunteer import Volunteer, EventParticipation, Skill, VolunteerSkill
from models.organization import Organization, VolunteerOrganization
from models.event import event_districts
from models.district_model import District
from models.reports import DistrictYearEndReport
from models import db
import json
import pytz
import pandas as pd
import io
import xlsxwriter

# District mapping configuration
DISTRICT_MAPPING = {
    # Districts to show
    '0015f00000JU4opAAD': {  # Grandview School District
        'name': 'Grandview School District',
        'district_code': '48074',
        'merge_with': None,
        'show': True,
        'aliases': [
            'Grandview',
        ]
    },
    '0015f00000JU4pVAAT': {  # Kansas City Kansas Public Schools
        'name': 'Kansas City Kansas Public Schools',
        'district_code': '48078',
        'merge_with': None,
        'show': True,
        'aliases': [
            'Kansas City Kansas School District',
            'KANSAS CITY USD 500',
            'KCKPS (KS)'
        ]
    },
    '0015f00000JU9ZEAA1': {  # Allen Village - District
        'name': 'Allen Village - District',
        'district_code': '48909',
        'merge_with': None,
        'show': True
    },
    '0015f00000JU9ZFAA1': {  # Hickman Mills School District
        'name': 'Hickman Mills School District',
        'district_code': '48072',
        'merge_with': None,
        'show': True,
        'aliases': ['Hickman Mills']
    },
    '0015f00000JVaPKAA1': {  # GUADALUPE CENTERS SCHOOLS
        'name': 'GUADALUPE CENTERS SCHOOLS',
        'district_code': '48902',
        'merge_with': None,
        'show': True
    },
    '0015f00000KvuZTAAZ': {  # Center School District
        'name': 'Center School District',
        'district_code': '48080',
        'merge_with': None,
        'show': True
    },
    '0015f00000KxHwVAAV': {  # Kansas City Public Schools (MO)
        'name': 'Kansas City Public Schools (MO)',
        'district_code': None,
        'merge_with': None,
        'show': True,
        'aliases': ['KCPS (MO)']
    }
}

def get_district_student_count_for_event(event, target_district_id):
    """
    Count students for an event that belong to the specified district.
    
    Args:
        event: Event object
        target_district_id: The district ID to filter students by
        
    Returns:
        int: Count of students from the specified district who attended the event
    """
    if event.type == EventType.VIRTUAL_SESSION:
        # For virtual sessions, count teachers from the district and multiply by 25
        district_teachers_count = 0
        for teacher_registration in event.teacher_registrations:
            teacher = teacher_registration.teacher
            if teacher.school_id:
                school = School.query.filter_by(id=teacher.school_id).first()
                if school and hasattr(school, 'district_id') and school.district_id == target_district_id:
                    district_teachers_count += 1
        return district_teachers_count * 25
    else:
        # For non-virtual events, count actual student participations from the district
        from models.student import Student
        
        district_student_count = (
            db.session.query(EventStudentParticipation)
            .join(Student, EventStudentParticipation.student_id == Student.id)
            .join(School, Student.school_id == School.id)
            .filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status == 'Attended',  # Only count attended students
                School.district_id == target_district_id
            )
            .count()
        )
        return district_student_count

def get_current_school_year():
    """
    Returns the current school year in 'YYZZ' format (e.g., '2324' for 2023-24).
    If before June 1st, returns current academic year.
    If after June 1st, returns next academic year.
    """
    today = datetime.now()
    if today.month < 6:  # Before June
        return f"{str(today.year-1)[-2:]}{str(today.year)[-2:]}"
    return f"{str(today.year)[-2:]}{str(today.year+1)[-2:]}"

def get_school_year_date_range(school_year):
    """
    Returns start and end dates for a school year.
    school_year format: '2324' for 2023-2024 school year
    """
    year = int(school_year[:2]) + 2000
    start_date = datetime(year, 6, 1)  # June 1st of start year
    end_date = datetime(year + 1, 5, 31)  # May 31st of end year
    return start_date, end_date

def generate_district_stats(school_year, host_filter='all'):
    """Generate district statistics for a school year"""
    district_stats = {}
    start_date, end_date = get_school_year_date_range(school_year)
    print(f"Date range: {start_date} to {end_date}")  # Debug log
    
    # Only exclude connector sessions
    excluded_event_types = ['connector_session']
    print(f"Excluded event types: {excluded_event_types}")  # Debug log
    
    # Get all districts from the database
    all_districts = District.query.order_by(District.name).all()
    
    # Process each district in our mapping
    for salesforce_id, mapping in DISTRICT_MAPPING.items():
        if not mapping['show']:
            continue
            
        print(f"\nProcessing district: {mapping['name']}")  # Debug log
        
        # Find the primary district record
        primary_district = next((d for d in all_districts if d.salesforce_id == salesforce_id), None)
        if not primary_district:
            print(f"Warning: Primary district {mapping['name']} not found in database")
            continue
            
        # Get all schools for this district
        schools = School.query.filter_by(district_id=primary_district.id).all()
        print(f"Found {len(schools)} schools for district")  # Debug log
        
        # Build the query conditions for this district
        district_partner_conditions = [
            Event.district_partner.ilike(f"%{school.name}%") for school in schools
        ]
        district_partner_conditions.append(Event.district_partner.ilike(f"%{primary_district.name}%"))

        # Add conditions for aliases - MODIFIED to handle both directions
        if 'aliases' in mapping:
            for alias in mapping['aliases']:
                district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                # Also check the districts relationship for aliases
                district_partner_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Combine all conditions with OR instead of AND
        events_query = Event.query.filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            ~Event.type.in_([EventType(t) for t in excluded_event_types]),
            # Use OR between all district-related conditions
            db.or_(
                Event.districts.contains(primary_district),
                Event.school.in_([school.id for school in schools]),
                *district_partner_conditions
            )
        ).distinct()
        if host_filter == 'prepkc':
            print('Applying PREPKC filter to events_query...')
            events_query = events_query.filter(Event.session_host.ilike('%prepkc%'))
            print('PREPKC filter applied. SQL:', str(events_query))
        
        events = events_query.all()
        if host_filter == 'prepkc':
            print('PREPKC filter active. session_host values:')
            for event in events:
                print(f"  Event ID {event.id}: session_host='{event.session_host}' title='{event.title}'")
        event_ids = [event.id for event in events]
        print(f"Found {len(events)} total events")  # Debug log
        
        # Debug log event types
        event_types_found = {}
        for event in events:
            event_type = event.type.value if event.type else 'unknown'
            event_types_found[event_type] = event_types_found.get(event_type, 0) + 1
        print(f"Event types found: {event_types_found}")  # Debug log
        
        # Query student participations for these events
        student_participations = EventStudentParticipation.query.filter(
            EventStudentParticipation.event_id.in_(event_ids)
        ).all()
        
        # Initialize stats dictionary
        stats = {
            'name': mapping['name'],
            'district_code': mapping['district_code'],
            'total_events': len(events),
            'total_students': 0,
            'total_in_person_students': 0,
            'total_virtual_students': 0,
            'unique_students': set(), # Track unique student IDs
            'total_volunteers': 0,
            'unique_volunteers': set(),  # Track unique volunteer IDs
            'total_volunteer_hours': 0,
            'event_types': event_types_found,
            'schools_reached': set(),
            'monthly_breakdown': {},
            'career_clusters': set()
        }
        
        # Monthly unique volunteer and student tracking
        monthly_unique_volunteers = {}
        monthly_unique_students = {} # Track unique students per month
        
        # Calculate statistics
        for event in events:
            # Get student count filtered by district
            student_count = get_district_student_count_for_event(event, primary_district.id)
            
            is_virtual = event.type == EventType.VIRTUAL_SESSION
            
            if is_virtual:
                stats['total_virtual_students'] += student_count
                print(f"  [DEBUG] Common - Virtual event {event.id} in District {primary_district.name}: {student_count} students")
            else:
                stats['total_in_person_students'] += student_count

            # Keep track of the overall total as well
            stats['total_students'] += student_count
            
            # Track volunteer participation with improved counting for virtual events
            # Fetch participations once outside the loop if possible, or adjust logic
            volunteer_participations = [p for p in event.volunteer_participations
                                        if p.status in ['Attended', 'Completed', 'Successfully Completed']]
            volunteer_count = len(volunteer_participations)
            volunteer_hours = sum(p.delivery_hours or 0 for p in volunteer_participations)

            # Track unique volunteers
            for p in volunteer_participations:
                stats['unique_volunteers'].add(p.volunteer_id)

            # Add debug info for virtual events
            if event.type == EventType.VIRTUAL_SESSION:
                print(f"Virtual event: '{event.title}', Volunteers: {volunteer_count}, Hours: {volunteer_hours}")
            
            stats['total_volunteers'] += volunteer_count
            stats['total_volunteer_hours'] += volunteer_hours
            
            # Track schools and career clusters
            if event.school:
                stats['schools_reached'].add(event.school)
            if event.series:
                stats['career_clusters'].add(event.series)
            
            # Monthly breakdown
            month = event.start_date.strftime('%B %Y')
            if month not in stats['monthly_breakdown']:
                stats['monthly_breakdown'][month] = {
                    'events': 0,
                    'students': 0,
                    'volunteers': 0,
                    'volunteer_hours': 0,
                    'unique_volunteers': set(),  # Track unique volunteers by month
                    'unique_students': set() # Track unique students by month
                }
            
            # Update monthly stats
            stats['monthly_breakdown'][month]['events'] += 1
            stats['monthly_breakdown'][month]['students'] += student_count
            stats['monthly_breakdown'][month]['volunteers'] += volunteer_count
            stats['monthly_breakdown'][month]['volunteer_hours'] += volunteer_hours
            
            # Track unique volunteers by month
            for p in volunteer_participations:
                stats['monthly_breakdown'][month]['unique_volunteers'].add(p.volunteer_id)

            # Track unique students by month for this event - filter by district
            if event.type == EventType.VIRTUAL_SESSION:
                # For virtual events, we can't track individual unique students
                # since the count is calculated from teachers
                pass
            else:
                # Get student IDs for this specific district and event
                district_student_ids = (
                    db.session.query(EventStudentParticipation.student_id)
                    .join(Student, EventStudentParticipation.student_id == Student.id)
                    .join(School, Student.school_id == School.id)
                    .filter(
                        EventStudentParticipation.event_id == event.id,
                        EventStudentParticipation.status == 'Attended',
                        School.district_id == primary_district.id
                    )
                    .all()
                )
                event_student_ids = {student_id[0] for student_id in district_student_ids}
                stats['unique_students'].update(event_student_ids)
                stats['monthly_breakdown'][month]['unique_students'].update(event_student_ids)

        # Convert sets to counts and round hours
        stats['unique_student_count'] = len(stats['unique_students']) # Add unique student count
        del stats['unique_students'] # Remove the set
        
        stats['unique_volunteer_count'] = len(stats['unique_volunteers'])
        del stats['unique_volunteers']  # Remove the set to avoid JSON serialization issues
        
        stats['schools_reached'] = len(stats['schools_reached'])
        stats['career_clusters'] = len(stats['career_clusters'])
        stats['total_volunteer_hours'] = round(stats['total_volunteer_hours'], 1)
        
        # Process monthly data
        for month in stats['monthly_breakdown']:
            # Convert unique volunteer sets to counts
            stats['monthly_breakdown'][month]['unique_volunteer_count'] = len(stats['monthly_breakdown'][month]['unique_volunteers'])
            del stats['monthly_breakdown'][month]['unique_volunteers']  # Remove the set
            
            # Convert unique student sets to counts
            stats['monthly_breakdown'][month]['unique_student_count'] = len(stats['monthly_breakdown'][month]['unique_students'])
            del stats['monthly_breakdown'][month]['unique_students'] # Remove the set
            
            # Round volunteer hours
            stats['monthly_breakdown'][month]['volunteer_hours'] = round(
                stats['monthly_breakdown'][month]['volunteer_hours'], 1
            )
        
        district_stats[mapping['name']] = stats
    
    return district_stats

def cache_district_stats(school_year, district_stats):
    """Save district statistics to the cache table"""
    for district_name, stats in district_stats.items():
        district = District.query.filter_by(name=district_name).first()
        if district:
            # Update or create cache entry
            report = DistrictYearEndReport.query.filter_by(
                district_id=district.id,
                school_year=school_year
            ).first() or DistrictYearEndReport(
                district_id=district.id,
                school_year=school_year
            )
            report.report_data = stats
            report.last_updated = datetime.utcnow()
            db.session.add(report)
    
    db.session.commit()

def update_event_districts(event, district_names):
    """Helper function to update event district relationships"""
    # Clear existing relationships
    event.districts = []
    
    for name in district_names:
        # Try exact match first
        district = District.query.filter(District.name.ilike(name)).first()
        if district and district not in event.districts:
            event.districts.append(district)
            
        # Update text field for backward compatibility
        if event.district_partner:
            current_districts = set(d.strip() for d in event.district_partner.split(','))
            current_districts.add(name)
            event.district_partner = ', '.join(current_districts)
        else:
            event.district_partner = name
