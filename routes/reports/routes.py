from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from sqlalchemy import extract
from models.event import Event, EventType, EventStatus
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models.event import db
from models.teacher import Teacher
from models.volunteer import Volunteer, EventParticipation
from models.organization import Organization, VolunteerOrganization
from models.event import event_districts
from models.district_model import District
import json

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
        {
            'title': 'Volunteer Thank You Report',
            'description': 'View top volunteers by hours and events for end of year thank you notes.',
            'icon': 'fa-solid fa-heart',
            'url': '/reports/volunteer/thankyou',
            'category': 'Volunteer Recognition'
        },
        {
            'title': 'Organization Thank You Report',
            'description': 'View organization contributions by sessions, hours, and volunteer participation.',
            'icon': 'fa-solid fa-building',
            'url': '/reports/organization/thankyou',
            'category': 'Organization Recognition'
        },
        {
            'title': 'District Year-End Report',
            'description': 'View comprehensive year-end statistics for each district.',
            'icon': 'fa-solid fa-chart-pie',
            'url': '/reports/district/year-end',
            'category': 'District Reports'
        }
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
        if event.educator_ids:
            # Convert string of IDs to list of integers
            try:
                # Handle different possible formats
                if isinstance(event.educator_ids, str):
                    # Remove any brackets and split by commas
                    educator_id_list = [int(id.strip()) for id in event.educator_ids.strip('[]').split(',') if id.strip()]
                else:
                    educator_id_list = event.educator_ids

                educators = Teacher.query.filter(Teacher.id.in_(educator_id_list)).all()
                educator_names = [f"{educator.first_name} {educator.last_name}" for educator in educators]
                educator_name = ", ".join(educator_names) if educator_names else "Unknown"
                stats['educators'].add(educator_name)
            except (ValueError, AttributeError):
                stats['educators'].add("Unknown")
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

@report_bp.route('/reports/virtual/usage/district/<district_name>')
@login_required
def virtual_usage_district(district_name):
    # Get filter parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Base query for this district
    query = Event.query.filter_by(
        type=EventType.VIRTUAL_SESSION,
        status=EventStatus.COMPLETED,
        district_partner=district_name
    )
    
    # Apply date filters
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
    
    # Get all events for this district
    district_events = query.order_by(Event.start_date).all()
    
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
                'events': []  # List to store individual event details
            }
        
        stats = monthly_stats[month_key]
        stats['total_sessions'] += 1
        stats['total_registered'] += event.registered_count or 0
        stats['total_attended'] += event.attended_count or 0
        stats['total_duration'] += event.duration or 0
        
        if event.school:
            stats['schools'].add(event.school)
        if event.educator_ids:
            educators = Teacher.query.filter(Teacher.id.in_(event.educator_ids)).all()
            educator_names = [f"{educator.first_name} {educator.last_name}" for educator in educators]
            educator_name = ", ".join(educator_names) if educator_names else "Unknown"
            stats['educators'].add(educator_name)
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
            'educator': event.educator_name,
            'career_cluster': event.series
        })
    
    # Calculate averages and convert sets to counts
    for stats in monthly_stats.values():
        if stats['total_registered'] > 0:
            stats['avg_attendance_rate'] = (stats['total_attended'] / stats['total_registered']) * 100
        stats['avg_duration'] = stats['total_duration'] / stats['total_sessions']
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
        current_filters={
            'date_from': date_from,
            'date_to': date_to
        }
    )

@report_bp.route('/reports/volunteer/thankyou')
@login_required
def volunteer_thankyou():
    # Get filter parameters
    year = request.args.get('year', datetime.now().year)
    
    # Query volunteer participation through EventParticipation
    volunteer_stats = db.session.query(
        Volunteer,
        db.func.sum(EventParticipation.delivery_hours).label('total_hours'),
        db.func.count(EventParticipation.id).label('total_events'),
        Organization.name.label('organization_name')
    ).join(
        EventParticipation, Volunteer.id == EventParticipation.volunteer_id
    ).join(
        Event, EventParticipation.event_id == Event.id
    ).outerjoin(
        VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
    ).outerjoin(
        Organization, VolunteerOrganization.organization_id == Organization.id
    ).filter(
        extract('year', Event.start_date) == year,
        EventParticipation.status == 'Attended'
    ).group_by(
        Volunteer.id,
        Organization.name
    ).order_by(
        db.desc('total_hours')
    ).all()

    # Format the data for the template
    volunteer_data = [{
        'id': v.id,
        'name': f"{v.first_name} {v.last_name}",
        'total_hours': round(float(hours or 0), 2) if hours is not None else 0,
        'total_events': events,
        'organization': org or 'Independent'
    } for v, hours, events, org in volunteer_stats]

    return render_template(
        'reports/volunteer_thankyou.html',
        volunteers=volunteer_data,
        year=year,
        now=datetime.now()
    )

@report_bp.route('/reports/volunteer/thankyou/detail/<int:volunteer_id>')
@login_required
def volunteer_thankyou_detail(volunteer_id):
    # Get filter parameters
    year = request.args.get('year', datetime.now().year)
    
    # Get volunteer details
    volunteer = Volunteer.query.get_or_404(volunteer_id)
    
    # Query all events for this volunteer in the specified year
    events = db.session.query(
        Event,
        EventParticipation.delivery_hours
    ).join(
        EventParticipation, Event.id == EventParticipation.event_id
    ).filter(
        EventParticipation.volunteer_id == volunteer_id,
        extract('year', Event.start_date) == year,
        EventParticipation.status == 'Attended'
    ).order_by(
        Event.start_date
    ).all()
    
    # Format the events data
    events_data = [{
        'date': event.start_date.strftime('%B %d, %Y'),
        'title': event.title,
        'type': event.type.value if event.type else 'Unknown',
        'hours': round(hours or 0, 2),
        'school': event.school or 'N/A',
        'district': event.district_partner or 'N/A'
    } for event, hours in events]
    
    # Calculate totals
    total_hours = sum(event['hours'] for event in events_data)
    total_events = len(events_data)
    
    return render_template(
        'reports/volunteer_thankyou_detail.html',
        volunteer=volunteer,
        events=events_data,
        total_hours=total_hours,
        total_events=total_events,
        year=year,
        now=datetime.now()
    )

@report_bp.route('/reports/organization/thankyou')
@login_required
def organization_thankyou():
    # Get filter parameters
    year = request.args.get('year', datetime.now().year)
    
    # Query organization participation through EventParticipation
    org_stats = db.session.query(
        Organization,
        db.func.count(db.distinct(Event.id)).label('unique_sessions'),
        db.func.sum(EventParticipation.delivery_hours).label('total_hours'),
        db.func.count(db.distinct(Volunteer.id)).label('unique_volunteers')
    ).join(
        VolunteerOrganization, Organization.id == VolunteerOrganization.organization_id
    ).join(
        Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id
    ).join(
        EventParticipation, Volunteer.id == EventParticipation.volunteer_id
    ).join(
        Event, EventParticipation.event_id == Event.id
    ).filter(
        extract('year', Event.start_date) == year,
        EventParticipation.status == 'Attended'
    ).group_by(
        Organization.id
    ).order_by(
        db.desc('total_hours')
    ).all()

    # Format the data for the template
    org_data = [{
        'id': org.id,
        'name': org.name,
        'unique_sessions': sessions,
        'total_hours': round(hours or 0, 2),
        'unique_volunteers': volunteers
    } for org, sessions, hours, volunteers in org_stats]

    return render_template(
        'reports/organization_thankyou.html',
        organizations=org_data,
        year=year,
        now=datetime.now()
    )

@report_bp.route('/reports/organization/thankyou/detail/<int:org_id>')
@login_required
def organization_thankyou_detail(org_id):
    # Get filter parameters
    year = request.args.get('year', datetime.now().year)
    
    # Get organization details
    organization = Organization.query.get_or_404(org_id)
    
    # Query volunteers and their participation for this organization
    volunteer_stats = db.session.query(
        Volunteer,
        db.func.count(db.distinct(Event.id)).label('event_count'),
        db.func.sum(EventParticipation.delivery_hours).label('total_hours')
    ).join(
        VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
    ).join(
        EventParticipation, Volunteer.id == EventParticipation.volunteer_id
    ).join(
        Event, EventParticipation.event_id == Event.id
    ).filter(
        VolunteerOrganization.organization_id == org_id,
        extract('year', Event.start_date) == year,
        EventParticipation.status == 'Attended'
    ).group_by(
        Volunteer.id
    ).order_by(
        db.desc('total_hours')
    ).all()

    # Format volunteer data
    volunteers_data = [{
        'id': v.id,
        'name': f"{v.first_name} {v.last_name}",
        'events': events,
        'hours': round(hours or 0, 2)
    } for v, events, hours in volunteer_stats]

    # Get event details
    events = db.session.query(
        Event,
        db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count'),
        db.func.sum(EventParticipation.delivery_hours).label('total_hours')
    ).join(
        EventParticipation, Event.id == EventParticipation.event_id
    ).join(
        Volunteer, EventParticipation.volunteer_id == Volunteer.id
    ).join(
        VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
    ).filter(
        VolunteerOrganization.organization_id == org_id,
        extract('year', Event.start_date) == year,
        EventParticipation.status == 'Attended'
    ).group_by(
        Event.id
    ).order_by(
        Event.start_date
    ).all()

    # Format event data
    events_data = [{
        'date': event.start_date.strftime('%B %d, %Y'),
        'title': event.title,
        'type': event.type.value if event.type else 'Unknown',
        'volunteers': vol_count,
        'hours': round(hours or 0, 2)
    } for event, vol_count, hours in events]

    return render_template(
        'reports/organization_thankyou_detail.html',
        organization=organization,
        volunteers=volunteers_data,
        events=events_data,
        year=year,
        now=datetime.now()
    )

@report_bp.route('/reports/district/year-end')
@login_required
def district_year_end():
    year = request.args.get('year', datetime.now().year)
    
    # Get all districts from District model
    districts = District.query.order_by(District.name).all()
    district_stats = {}
    
    # Create a mapping of variations to standardized names
    district_name_variations = {
        'GRANDVIEW C-4': ['Grandview C-4 School District', 'Grandview C-4', 'Grandview C4'],
        'KANSAS CITY USD 500': ['Kansas City USD 500', 'Kansas City, Kansas Public Schools', 'KCK Public Schools'],
        'HICKMAN MILLS C-1': ['Hickman Mills C-1', 'Hickman Mills', 'Hickman Mills School District'],
        # Add more variations as needed
    }
    
    for district in districts:
        print(f"Processing district: {district.name}")  # Debug log
        
        # Get all possible name variations for this district
        name_variations = district_name_variations.get(district.name, [district.name])
        name_variations = [name.upper() for name in name_variations]  # Convert all to uppercase
        
        # Count all events for this district using name variations
        total_events = Event.query.filter(
            Event.district_partner.in_(name_variations),
            extract('year', Event.start_date) == year
        ).count()

        print(f"Checking variations for {district.name}: {name_variations}")
        print(f"Found {total_events} events")

        district_stats[district.name] = {
            'name': district.name,
            'total_events': total_events
        }

    return render_template(
        'reports/district_year_end.html',
        districts=district_stats,
        year=year,
        now=datetime.now()
    )

