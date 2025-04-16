from flask import render_template, request, jsonify, make_response, send_file
from flask_login import login_required
from sqlalchemy import any_, extract
from models.event import Event, EventAttendance, EventType, EventStatus
from datetime import datetime, timedelta
from models.school_model import School
from models.teacher import Teacher
from models.upcoming_events import UpcomingEvent
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

def generate_district_stats(school_year):
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
        
        events = events_query.all()
        print(f"Found {len(events)} total events")  # Debug log
        
        # Debug log event types
        event_types_found = {}
        for event in events:
            event_type = event.type.value if event.type else 'unknown'
            event_types_found[event_type] = event_types_found.get(event_type, 0) + 1
        print(f"Event types found: {event_types_found}")  # Debug log
        
        # Initialize stats dictionary
        stats = {
            'name': mapping['name'],
            'district_code': mapping['district_code'],
            'total_events': len(events),
            'total_students': 0,
            'total_volunteers': 0,
            'unique_volunteers': set(),  # Track unique volunteer IDs
            'total_volunteer_hours': 0,
            'event_types': event_types_found,
            'schools_reached': set(),
            'monthly_breakdown': {},
            'career_clusters': set()
        }
        
        # Monthly unique volunteer tracking
        monthly_unique_volunteers = {}
        
        # Calculate statistics
        for event in events:
            # Get student count based on event type
            student_count = 0
            if event.type == EventType.VIRTUAL_SESSION:
                student_count = event.attended_count or 0
            elif hasattr(event, 'attendance') and event.attendance:
                student_count = event.attendance.total_attendance
            else:
                student_count = event.participant_count or 0
            
            stats['total_students'] += student_count
            
            # Track volunteer participation with improved counting for virtual events
            if event.type == EventType.VIRTUAL_SESSION:
                # For virtual sessions, count all volunteers with Completed or Successfully Completed status
                volunteer_participations = EventParticipation.query.filter(
                    EventParticipation.event_id == event.id,
                    EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
                ).all()
                
                # If we found participations, use them
                if volunteer_participations:
                    volunteer_count = len(volunteer_participations)
                    volunteer_hours = sum(p.delivery_hours or 0 for p in volunteer_participations)
                    
                    # Track unique volunteers
                    for p in volunteer_participations:
                        stats['unique_volunteers'].add(p.volunteer_id)
                else:
                    # If no participations but the event is completed, assume 1 volunteer and 1 hour
                    volunteer_count = 1
                    volunteer_hours = 1.0
                    # We can't track unique volunteers in this case
            else:
                # For non-virtual events, use the standard attendance counting
                volunteer_participations = EventParticipation.query.filter(
                    EventParticipation.event_id == event.id,
                    EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
                ).all()
                
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
                    'unique_volunteers': set()  # Track unique volunteers by month
                }
            
            # Update monthly stats
            stats['monthly_breakdown'][month]['events'] += 1
            stats['monthly_breakdown'][month]['students'] += student_count
            stats['monthly_breakdown'][month]['volunteers'] += volunteer_count
            stats['monthly_breakdown'][month]['volunteer_hours'] += volunteer_hours
            
            # Track unique volunteers by month
            for p in volunteer_participations:
                stats['monthly_breakdown'][month]['unique_volunteers'].add(p.volunteer_id)
        
        # Convert sets to counts and round hours
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
