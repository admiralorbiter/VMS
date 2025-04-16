from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract

from models.volunteer import Volunteer, EventParticipation
from models.organization import Organization, VolunteerOrganization
from models.event import Event
from models import db

# Create blueprint
volunteer_thankyou_bp = Blueprint('volunteer_thankyou', __name__)

def load_routes(bp):
    @bp.route('/reports/volunteer/thankyou')
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

    @bp.route('/reports/volunteer/thankyou/detail/<int:volunteer_id>')
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
