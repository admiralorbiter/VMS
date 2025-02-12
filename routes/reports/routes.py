from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from sqlalchemy import extract
from models.event import Event, EventType, EventStatus
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models.event import db
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import Volunteer, EventParticipation, Skill
from models.organization import Organization, VolunteerOrganization
from models.event import event_districts
from models.district_model import District
from models.upcoming_events import UpcomingEvent
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
        },
        {
            'title': 'Recruitment Report',
            'description': 'Shows upcoming unfilled events, volunteer search, and skill matching to industry/jobs.',
            'icon': 'fa-solid fa-file-alt',
            'url': '/reports/recruitment',
            'category': 'General Reports'
        },
        {
            'title': 'Event Contact Report',
            'description': 'View upcoming events and volunteer contact information.',
            'icon': 'fa-solid fa-address-book',
            'url': '/reports/contact',
            'category': 'Event Management'
        }
    ]
    
    return render_template('reports/reports.html', reports=available_reports)

@report_bp.route('/reports/virtual/usage')
@login_required
def virtual_usage():
    # Get filter parameters with explicit year handling
    year = int(request.args.get('year', '2024'))  # Default to 2024, convert to int
    
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

@report_bp.route('/reports/virtual/usage/district/<district_name>')
@login_required
def virtual_usage_district(district_name):
    # Get filter parameters with explicit year handling
    year = int(request.args.get('year', '2024'))  # Default to 2024, convert to int
    
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
    year = int(request.args.get('year', datetime.now().year))
    
    districts = District.query.order_by(District.name).all()
    district_stats = {}
    
    for district in districts:
        # Get all schools for this district
        schools = School.query.filter_by(district_id=district.id).all()
        school_names = [school.name for school in schools]
        
        # Query events using both relationships and text matching
        events = Event.query.filter(
            db.or_(
                Event.districts.contains(district),  # Check direct district relationship
                Event.school.in_([school.id for school in schools]),  # Check school relationship
                # Check text fields with school names
                *[Event.title.ilike(f"%{school.name}%") for school in schools],
                *[Event.district_partner.ilike(f"%{school.name}%") for school in schools],
                # Also check district name variations
                Event.district_partner.ilike(f"%{district.name}%"),
                Event.district_partner.ilike(f"%{district.name.replace(' School District', '')}%"),
                Event.district_partner.ilike(f"%{district.name.replace(' Public Schools', '')}%")
            ),
            extract('year', Event.start_date) == year,
            Event.status == EventStatus.COMPLETED
        ).distinct().all()

        # Initialize stats dictionary
        stats = {
            'name': district.name,
            'district_code': district.district_code,
            'total_events': len(events),
            'total_students': 0,
            'total_volunteers': 0,
            'total_volunteer_hours': 0,
            'event_types': {},
            'schools_reached': set(),
            'monthly_breakdown': {},
            'career_clusters': set()
        }

        for event in events:
            # Count students
            stats['total_students'] += event.attended_count or 0
            
            # Count volunteers and hours
            for participation in event.volunteer_participations:
                if participation.status == 'Attended':
                    stats['total_volunteers'] += 1
                    stats['total_volunteer_hours'] += participation.delivery_hours or 0
            
            # Track event types
            event_type = event.type.value if event.type else 'unknown'
            stats['event_types'][event_type] = stats['event_types'].get(event_type, 0) + 1
            
            # Track schools
            if event.school:
                stats['schools_reached'].add(event.school)
            
            # Monthly breakdown
            month = event.start_date.strftime('%B %Y')
            if month not in stats['monthly_breakdown']:
                stats['monthly_breakdown'][month] = {
                    'events': 0,
                    'students': 0,
                    'volunteers': 0
                }
            stats['monthly_breakdown'][month]['events'] += 1
            stats['monthly_breakdown'][month]['students'] += event.attended_count or 0
            stats['monthly_breakdown'][month]['volunteers'] += len([p for p in event.volunteer_participations if p.status == 'Attended'])
            
            # Track career clusters
            if event.series:
                stats['career_clusters'].add(event.series)

        # Convert sets to counts
        stats['schools_reached'] = len(stats['schools_reached'])
        stats['career_clusters'] = len(stats['career_clusters'])
        stats['total_volunteer_hours'] = round(stats['total_volunteer_hours'], 1)
        
        district_stats[district.name] = stats
    
    return render_template(
        'reports/district_year_end.html',
        districts=district_stats,
        year=year,
        now=datetime.now()
    )

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

@report_bp.route('/reports/recruitment')
@login_required
def recruitment_report():
    # Get upcoming events that need volunteers from the UpcomingEvent model
    upcoming_events = UpcomingEvent.query.filter(
        UpcomingEvent.start_date >= datetime.now(),
        UpcomingEvent.available_slots > UpcomingEvent.filled_volunteer_jobs
    ).order_by(UpcomingEvent.start_date).all()

    # Get the search query from the request
    search_query = request.args.get('search', '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of volunteers per page

    # Get the event type filter
    event_type_filter = request.args.get('event_type', '').strip()
    
    # Fix: Handle exclude_dia value from both checkbox and hidden input
    exclude_dia = request.args.get('exclude_dia')
    exclude_dia = exclude_dia == '1' or exclude_dia == 'true' or exclude_dia == 'True'

    # Initialize volunteers_data and pagination as None
    volunteers_data = []
    pagination = None

    # Only query volunteers if there is a search query
    if search_query:
        # Split search query into words
        search_terms = search_query.split()
        
        volunteers_query = Volunteer.query.outerjoin(
            Volunteer.volunteer_organizations
        ).outerjoin(
            VolunteerOrganization.organization
        ).outerjoin(
            EventParticipation, EventParticipation.volunteer_id == Volunteer.id
        ).filter(
            db.or_(
                db.and_(*[
                    db.or_(
                        Volunteer.first_name.ilike(f'%{term}%'),
                        Volunteer.last_name.ilike(f'%{term}%')
                    ) for term in search_terms
                ]),
                Volunteer.title.ilike(f'%{search_query}%'),
                Organization.name.ilike(f'%{search_query}%'),
                Volunteer.skills.any(Skill.name.ilike(f'%{search_query}%'))
            )
        )

        # Add pagination to the volunteers query
        paginated_volunteers = volunteers_query.add_columns(
            db.func.count(EventParticipation.id).label('participation_count'),
            db.func.max(EventParticipation.event_id).label('last_event')
        ).group_by(Volunteer.id).paginate(page=page, per_page=per_page, error_out=False)

        # Store pagination object for template
        pagination = paginated_volunteers

        # Populate volunteers_data based on the paginated results
        for volunteer, participation_count, last_event in paginated_volunteers.items:
            volunteers_data.append({
                'id': volunteer.id,
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'email': volunteer.primary_email,
                'title': volunteer.title,
                'organization': {
                    'name': volunteer.volunteer_organizations[0].organization.name if volunteer.volunteer_organizations else None,
                    'id': volunteer.volunteer_organizations[0].organization.id if volunteer.volunteer_organizations else None
                },
                'participation_count': participation_count,
                'skills': [skill.name for skill in volunteer.skills],
                'industry': volunteer.industry,
                'last_mailchimp_date': volunteer.last_mailchimp_activity_date,
                'last_volunteer_date': volunteer.last_volunteer_date,
                'last_email_date': volunteer.last_email_date,
                'salesforce_contact_url': volunteer.salesforce_contact_url
            })

    # Prepare events_data based on UpcomingEvent model
    events_data = []
    for event in upcoming_events:
        # Extract the URL from the HTML anchor tag if it exists
        registration_link = None
        if event.registration_link and 'href=' in event.registration_link:
            start = event.registration_link.find('href="') + 6
            end = event.registration_link.find('"', start)
            if start > 5 and end > start:  # ensure we found both quotes
                registration_link = event.registration_link[start:end]
        
        events_data.append({
            'title': event.name,
            'description': event.event_type,
            'start_date': event.start_date,
            'type': event.event_type,
            'location': event.registration_link,
            'total_slots': event.available_slots,
            'filled_slots': event.filled_volunteer_jobs,
            'remaining_slots': event.available_slots - event.filled_volunteer_jobs,
            'skills_needed': [],
            'status': 'Upcoming',
            'registration_link': registration_link
        })

    return render_template(
        'reports/recruitment_report.html',
        events=events_data,
        volunteers=volunteers_data,
        search_query=search_query,
        event_types=UpcomingEvent.query.with_entities(UpcomingEvent.event_type).distinct().all(),
        exclude_dia=exclude_dia,
        event_type_filter=event_type_filter,
        pagination=pagination,
        page=page
    )

@report_bp.route('/reports/contact')
@login_required
def contact_report():
    # Get search parameters
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'start_date')
    order = request.args.get('order', 'asc')

    # Base query for future events that are confirmed
    query = Event.query.filter(
        Event.start_date >= datetime.utcnow(),  # Only future events
        Event.status == EventStatus.CONFIRMED
    )
    
    # Apply search if provided
    if search:
        query = query.filter(Event.title.ilike(f'%{search}%'))
    
    # Apply sorting
    if sort == 'title':
        query = query.order_by(Event.title.asc() if order == 'asc' else Event.title.desc())
    elif sort == 'location':
        query = query.order_by(Event.location.asc() if order == 'asc' else Event.location.desc())
    else:  # default to date
        query = query.order_by(Event.start_date.asc() if order == 'asc' else Event.start_date.desc())
    
    upcoming_events = query.all()
    
    # Get participant counts for each event
    event_stats = {}
    for event in upcoming_events:
        participations = event.volunteer_participations
        event_stats[event.id] = {
            'volunteer_count': len(participations),
        }
    
    return render_template('reports/contact_report.html', 
                         events=upcoming_events,
                         event_stats=event_stats,
                         search=search,
                         sort=sort,
                         order=order)

@report_bp.route('/reports/contact/<int:event_id>')
@login_required
def contact_report_detail(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Get sort parameters
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    
    # Get all participants for this event
    participations = event.volunteer_participations
    
    # Group participants by status
    participants_by_status = {
        'Scheduled': [],
        'Unscheduled': []
    }
    
    for participation in participations:
        if participation.status == 'Scheduled':
            participants_by_status['Scheduled'].append(participation)
        else:
            participants_by_status['Unscheduled'].append(participation)
    
    # Sort participants in each group
    for status in participants_by_status:
        participants = participants_by_status[status]
        if sort == 'name':
            participants.sort(
                key=lambda p: f"{p.volunteer.first_name} {p.volunteer.last_name}",
                reverse=(order == 'desc')
            )
        elif sort == 'title':
            participants.sort(
                key=lambda p: p.title or p.volunteer.title or '',
                reverse=(order == 'desc')
            )
        elif sort == 'email':
            participants.sort(
                key=lambda p: p.volunteer.primary_email or '',
                reverse=(order == 'desc')
            )
        elif sort == 'organization':
            participants.sort(
                key=lambda p: p.volunteer.organizations[0].name if p.volunteer.organizations else '',
                reverse=(order == 'desc')
            )
    
    return render_template('reports/contact_report_detail.html',
                         event=event,
                         participants_by_status=participants_by_status,
                         sort=sort,
                         order=order)