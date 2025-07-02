from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract

from models.organization import Organization, VolunteerOrganization
from models.volunteer import Volunteer, EventParticipation
from models.event import Event
from models import db
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
organization_thankyou_bp = Blueprint('organization_thankyou', __name__)

def load_routes(bp):
    @bp.route('/reports/organization/thankyou')
    @login_required
    def organization_thankyou():
        # Get filter parameters - use school year format (e.g., '2425' for 2024-25)
        school_year = request.args.get('school_year', get_current_school_year())
        sort = request.args.get('sort', 'total_hours')
        order = request.args.get('order', 'desc')
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
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
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            EventParticipation.status == 'Attended'
        ).group_by(
            Organization.id
        ).all()

        # Format the data for the template
        org_data = [{
            'id': org.id,
            'name': org.name,
            'unique_sessions': sessions,
            'total_hours': round(hours or 0, 2),
            'unique_volunteers': volunteers
        } for org, sessions, hours, volunteers in org_stats]

        # Sort in Python
        def get_sort_key(org):
            if sort == 'name':
                return org['name'].lower() if org['name'] else ''
            elif sort == 'unique_sessions':
                return org['unique_sessions']
            elif sort == 'total_hours':
                return org['total_hours']
            elif sort == 'unique_volunteers':
                return org['unique_volunteers']
            return org['total_hours']
        org_data.sort(key=get_sort_key, reverse=(order=='desc'))

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            'reports/organization_thankyou.html',
            organizations=org_data,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort=sort,
            order=order
        )

    @bp.route('/reports/organization/thankyou/detail/<int:org_id>')
    @login_required
    def organization_thankyou_detail(org_id):
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        sort_vol = request.args.get('sort_vol', 'hours')
        order_vol = request.args.get('order_vol', 'desc')
        sort_evt = request.args.get('sort_evt', 'date')
        order_evt = request.args.get('order_evt', 'asc')
        
        # Get date range for the school year
        start_date, end_date = get_school_year_date_range(school_year)
        
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
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            EventParticipation.status == 'Attended'
        ).group_by(
            Volunteer.id
        ).all()

        # Format volunteer data
        volunteers_data = [{
            'id': v.id,
            'name': f"{v.first_name} {v.last_name}",
            'events': events,
            'hours': round(hours or 0, 2)
        } for v, events, hours in volunteer_stats]

        # Sort volunteers in Python
        def get_vol_sort_key(vol):
            if sort_vol == 'name':
                return vol['name'].lower() if vol['name'] else ''
            elif sort_vol == 'events':
                return vol['events']
            elif sort_vol == 'hours':
                return vol['hours']
            return vol['hours']
        volunteers_data.sort(key=get_vol_sort_key, reverse=(order_vol=='desc'))

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
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            EventParticipation.status == 'Attended'
        ).group_by(
            Event.id
        ).all()

        # Format event data
        events_data = [{
            'date': event.start_date.strftime('%B %d, %Y'),
            'date_sort': event.start_date,
            'title': event.title,
            'type': event.type.value if event.type else 'Unknown',
            'volunteers': vol_count,
            'hours': round(hours or 0, 2)
        } for event, vol_count, hours in events]

        # Sort events in Python
        def get_evt_sort_key(evt):
            if sort_evt == 'date':
                return evt['date_sort']
            elif sort_evt == 'title':
                return evt['title'].lower() if evt['title'] else ''
            elif sort_evt == 'type':
                return evt['type'].lower() if evt['type'] else ''
            elif sort_evt == 'volunteers':
                return evt['volunteers']
            elif sort_evt == 'hours':
                return evt['hours']
            return evt['date_sort']
        events_data.sort(key=get_evt_sort_key, reverse=(order_evt=='desc'))

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            'reports/organization_thankyou_detail.html',
            organization=organization,
            volunteers=volunteers_data,
            events=events_data,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort_vol=sort_vol,
            order_vol=order_vol,
            sort_evt=sort_evt,
            order_evt=order_evt
        )
