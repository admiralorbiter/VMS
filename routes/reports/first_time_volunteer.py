from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract, and_, or_

from models.volunteer import Volunteer, EventParticipation
from models.organization import Organization, VolunteerOrganization
from models.event import Event, EventStatus
from models import db
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
first_time_volunteer_bp = Blueprint('first_time_volunteer', __name__)

def load_routes(bp):
    @bp.route('/reports/first-time-volunteer')
    @login_required
    def first_time_volunteer():
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
        # Query for first-time volunteers in the school year
        # A first-time volunteer is someone whose first_volunteer_date falls within the school year
        first_time_volunteers = db.session.query(
            Volunteer,
            db.func.count(EventParticipation.id).label('total_events'),
            db.func.sum(EventParticipation.delivery_hours).label('total_hours'),
            Organization.name.label('organization_name')
        ).outerjoin(
            EventParticipation, Volunteer.id == EventParticipation.volunteer_id
        ).outerjoin(
            Event, and_(
                EventParticipation.event_id == Event.id,
                Event.start_date >= start_date,
                Event.start_date <= end_date,
                Event.status == EventStatus.COMPLETED
            )
        ).outerjoin(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).outerjoin(
            Organization, VolunteerOrganization.organization_id == Organization.id
        ).filter(
            and_(
                Volunteer.first_volunteer_date >= start_date,
                Volunteer.first_volunteer_date <= end_date
            )
        ).filter(
            or_(
                EventParticipation.status == 'Attended',
                EventParticipation.status == 'Completed',
                EventParticipation.status == 'Successfully Completed',
                EventParticipation.status.is_(None)  # Include volunteers with no participations yet
            )
        ).group_by(
            Volunteer.id,
            Organization.name
        ).order_by(
            Volunteer.first_volunteer_date.desc()
        ).all()

        # Format the data for the template
        volunteer_data = []
        for v, events, hours, org in first_time_volunteers:
            volunteer_data.append({
                'id': v.id,
                'name': f"{v.first_name} {v.last_name}",
                'first_volunteer_date': v.first_volunteer_date.strftime('%B %d, %Y') if v.first_volunteer_date else 'Unknown',
                'total_events': events or 0,
                'total_hours': round(float(hours or 0), 2),
                'organization': org or 'Independent',
                'email': v.primary_email,
                'phone': v.primary_phone
            })

        # Calculate summary statistics
        total_first_time_volunteers = len(volunteer_data)
        total_events_by_first_timers = sum(v['total_events'] for v in volunteer_data)
        total_hours_by_first_timers = sum(v['total_hours'] for v in volunteer_data)

        return render_template(
            'reports/first_time_volunteer.html',
            volunteers=volunteer_data,
            school_year=school_year,
            school_year_display=f"20{school_year[:2]}-{school_year[2:]}",
            total_first_time_volunteers=total_first_time_volunteers,
            total_events_by_first_timers=total_events_by_first_timers,
            total_hours_by_first_timers=total_hours_by_first_timers,
            now=datetime.now()
        )

    @bp.route('/reports/first-time-volunteer/detail/<int:volunteer_id>')
    @login_required
    def first_time_volunteer_detail(volunteer_id):
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
        # Get volunteer details
        volunteer = Volunteer.query.get_or_404(volunteer_id)
        
        # Verify this is actually a first-time volunteer for the selected school year
        if not volunteer.first_volunteer_date or not (start_date <= volunteer.first_volunteer_date <= end_date):
            return render_template('404.html'), 404
        
        # Query all events for this volunteer in the specified school year
        events = db.session.query(
            Event,
            EventParticipation.delivery_hours,
            EventParticipation.status
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).filter(
            EventParticipation.volunteer_id == volunteer_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            or_(
                EventParticipation.status == 'Attended',
                EventParticipation.status == 'Completed',
                EventParticipation.status == 'Successfully Completed'
            )
        ).order_by(
            Event.start_date
        ).all()
        
        # Format the events data
        events_data = []
        for event, hours, status in events:
            events_data.append({
                'date': event.start_date.strftime('%B %d, %Y'),
                'title': event.title,
                'type': event.type.value if event.type else 'Unknown',
                'hours': round(hours or 0, 2),
                'status': status,
                'school': event.school or 'N/A',
                'district': event.district_partner or 'N/A'
            })
        
        # Calculate totals
        total_hours = sum(event['hours'] for event in events_data)
        total_events = len(events_data)
        
        # Get organization info
        org_relationship = VolunteerOrganization.query.filter_by(volunteer_id=volunteer_id).first()
        organization_name = 'Independent'
        if org_relationship:
            org = Organization.query.get(org_relationship.organization_id)
            if org:
                organization_name = org.name
        
        return render_template(
            'reports/first_time_volunteer_detail.html',
            volunteer=volunteer,
            events=events_data,
            total_hours=total_hours,
            total_events=total_events,
            organization=organization_name,
            school_year=school_year,
            school_year_display=f"20{school_year[:2]}-{school_year[2:]}",
            now=datetime.now()
        ) 