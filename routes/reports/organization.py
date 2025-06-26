from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import distinct, func, or_

from models.organization import Organization, VolunteerOrganization
from models.volunteer import Volunteer, EventParticipation
from models.event import Event, EventType, EventFormat
from models import db
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
organization_bp = Blueprint('organization_reports', __name__)

def load_routes(bp):
    @bp.route('/reports/organization')
    @login_required
    def organization_reports():
        """Display all organizations with their engagement statistics"""
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
        # Query organization engagement statistics
        org_stats = db.session.query(
            Organization,
            func.count(distinct(Event.id)).label('total_events'),
            func.count(distinct(Volunteer.id)).label('unique_volunteers'),
            func.sum(EventParticipation.delivery_hours).label('total_hours')
        ).join(
            VolunteerOrganization, Organization.id == VolunteerOrganization.organization_id
        ).join(
            Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id
        ).join(
            EventParticipation, Volunteer.id == EventParticipation.volunteer_id
        ).join(
            Event, EventParticipation.event_id == Event.id
        ).filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            EventParticipation.status == 'Attended'
        ).group_by(
            Organization.id
        ).order_by(
            db.desc('total_events')
        ).all()

        # Get cancelled events count for each organization
        cancelled_stats = db.session.query(
            Organization.id,
            func.count(distinct(Event.id)).label('cancelled_events')
        ).join(
            VolunteerOrganization, Organization.id == VolunteerOrganization.organization_id
        ).join(
            Volunteer, VolunteerOrganization.volunteer_id == Volunteer.id
        ).join(
            EventParticipation, Volunteer.id == EventParticipation.volunteer_id
        ).join(
            Event, EventParticipation.event_id == Event.id
        ).filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == 'Cancelled'
        ).group_by(
            Organization.id
        ).all()

        # Create a dictionary for quick lookup of cancelled events
        cancelled_dict = {org_id: count for org_id, count in cancelled_stats}

        # Format the data for the template
        org_data = [{
            'id': org.id,
            'name': org.name,
            'total_events': total_events or 0,
            'unique_volunteers': unique_volunteers or 0,
            'total_hours': round(float(total_hours or 0), 2),
            'cancelled_events': cancelled_dict.get(org.id, 0)
        } for org, total_events, unique_volunteers, total_hours in org_stats]

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            'reports/organization.html',
            organizations=org_data,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now()
        )

    @bp.route('/reports/organization/detail/<int:org_id>')
    @login_required
    def organization_detail(org_id):
        """Display detailed report for a specific organization"""
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
        # Get organization details
        organization = Organization.query.get_or_404(org_id)
        
        # Get attended events for this organization
        # Include both 'Attended' participation and 'Completed' events (for virtual sessions where professional delivered but may have had teacher no-show)
        attended_events = db.session.query(
            Event,
            EventParticipation.delivery_hours,
            Volunteer.first_name,
            Volunteer.last_name
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            db.or_(
                EventParticipation.status == 'Attended',
                EventParticipation.status == 'Completed', 
                EventParticipation.status == 'Successfully Completed',
                EventParticipation.status == 'Confirmed'
            )
        ).order_by(
            Event.start_date.desc()
        ).all()

        # Get cancelled events for this organization
        cancelled_events = db.session.query(
            Event,
            Volunteer.first_name,
            Volunteer.last_name
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == 'Cancelled'
        ).order_by(
            Event.start_date.desc()
        ).all()

        # Get organization volunteers with their engagement stats
        volunteer_stats = db.session.query(
            Volunteer,
            func.count(distinct(Event.id)).label('event_count'),
            func.sum(EventParticipation.delivery_hours).label('total_hours')
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).join(
            EventParticipation, Volunteer.id == EventParticipation.volunteer_id
        ).join(
            Event, EventParticipation.event_id == Event.id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            db.or_(
                EventParticipation.status == 'Attended',
                EventParticipation.status == 'Completed', 
                EventParticipation.status == 'Successfully Completed',
                EventParticipation.status == 'Confirmed'
            )
        ).group_by(
            Volunteer.id
        ).order_by(
            db.desc('total_hours')
        ).all()

        # Separate in-person and virtual events from attended events
        in_person_events = []
        virtual_events = []
        
        # Define which event types are considered in-person vs virtual
        in_person_types = {
            EventType.IN_PERSON,
            EventType.CAREER_JUMPING,
            EventType.CAREER_SPEAKER,
            EventType.EMPLOYABILITY_SKILLS,
            EventType.IGNITE,
            EventType.CAREER_FAIR,
            EventType.PATHWAY_CAMPUS_VISITS,
            EventType.WORKPLACE_VISIT,
            EventType.PATHWAY_WORKPLACE_VISITS,
            EventType.COLLEGE_OPTIONS,
            EventType.DIA_CLASSROOM_SPEAKER,
            EventType.DIA,
            EventType.CAMPUS_VISIT,
            EventType.ADVISORY_SESSIONS,
            EventType.MENTORING,
            EventType.FINANCIAL_LITERACY,
            EventType.MATH_RELAYS,
            EventType.CLASSROOM_SPEAKER,
            EventType.INTERNSHIP,
            EventType.COLLEGE_APPLICATION_FAIR,
            EventType.FAFSA,
            EventType.CLASSROOM_ACTIVITY,
            EventType.VOLUNTEER_ORIENTATION,
            EventType.VOLUNTEER_ENGAGEMENT,
            EventType.CLIENT_CONNECTED_PROJECT
        }
        
        virtual_types = {
            EventType.VIRTUAL_SESSION,
            EventType.CONNECTOR_SESSION,
            EventType.DATA_VIZ,  # Data visualization sessions are often virtual
            EventType.P2GD,      # Prep to Goal Directed 
            EventType.SLA,       # Student Learning Activities
            EventType.HEALTHSTART,
            EventType.P2T,       # Prep to Trade
            EventType.BFI,       # Business and Finance Institute
            EventType.HISTORICAL
        }
        
        for event, hours, first_name, last_name in attended_events:
            event_data = {
                'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
                'volunteer': f"{first_name} {last_name}",
                'session': event.title,
                'hours': round(float(hours or 0), 2),
                'students_reached': event.participant_count or 0,
                'event_type': event.type.value if event.type else 'Unknown'
            }
            
            # Check both event type and format to determine if virtual
            is_virtual = (event.type in virtual_types or 
                         event.format == EventFormat.VIRTUAL)
            
            if is_virtual:
                event_data['time'] = event.start_date.strftime('%I:%M %p') if event.start_date else ''
                # For virtual events, show estimated student participation or registered count
                event_data['classrooms'] = event.participant_count or event.registered_count or 0
                # Add additional virtual session details
                event_data['session_id'] = event.session_id or ''
                event_data['series'] = event.series or ''
                virtual_events.append(event_data)
            elif event.type in in_person_types or event.format == EventFormat.IN_PERSON:
                in_person_events.append(event_data)
            else:
                # For unknown types, default to in-person but log the type
                event_data['note'] = f"Unknown event type: {event.type}"
                in_person_events.append(event_data)

        # Process cancelled events
        cancelled_events_data = []
        for event, first_name, last_name in cancelled_events:
            cancelled_events_data.append({
                'event': event.title,
                'volunteer': f"{first_name} {last_name}",
                'date': event.start_date.strftime('%m/%d/%y') if event.start_date else '',
                'cancellation_reason': event.cancellation_reason.value if event.cancellation_reason else 'Unknown'
            })

        # Format volunteer data
        volunteers_data = [{
            'name': f"{v.first_name} {v.last_name}",
            'events': events,
            'hours': round(float(hours or 0), 2)
        } for v, events, hours in volunteer_stats]

        # Calculate summary statistics
        total_in_person_students = sum(item['students_reached'] for item in in_person_events)
        total_virtual_classrooms = sum(item.get('classrooms', 0) for item in virtual_events)
        total_volunteers = len(volunteers_data)
        total_in_person_events = len(in_person_events)
        total_virtual_events = len(virtual_events)

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first
        
        return render_template(
            'reports/organization_detail.html',
            organization=organization,
            in_person_events=in_person_events,
            virtual_events=virtual_events,
            cancelled_events=cancelled_events_data,
            volunteers=volunteers_data,
            summary={
                'total_volunteers': total_volunteers,
                'total_in_person_events': total_in_person_events,
                'total_virtual_events': total_virtual_events,
                'total_in_person_students': total_in_person_students,
                'total_virtual_classrooms': total_virtual_classrooms,
                'total_cancelled_events': len(cancelled_events_data)
            },
            school_year=school_year,
            school_years=school_years,
            now=datetime.now()
        )
