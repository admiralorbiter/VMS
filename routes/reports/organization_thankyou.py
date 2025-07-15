from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract
import io
import pandas as pd
import xlsxwriter

from models.organization import Organization, VolunteerOrganization
from models.volunteer import Volunteer, EventParticipation
from models.event import Event, EventTeacher
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
        host_filter = request.args.get('host_filter', 'all')  # 'all' or 'prepkc'
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        )
        
        # Apply host filter if specified
        if host_filter == 'prepkc':
            org_stats = org_stats.filter(
                db.or_(
                    Event.session_host.ilike('%PREPKC%'),
                    Event.session_host.ilike('%prepkc%'),
                    Event.session_host.ilike('%PrepKC%')
                )
            )
        
        org_stats = org_stats.group_by(
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
            order=order,
            host_filter=host_filter
        )

    @bp.route('/reports/organization/thankyou/excel')
    @login_required
    def organization_thankyou_excel():
        """Generate Excel file for organization thank you report"""
        # Get filter parameters
        school_year = request.args.get('school_year', get_current_school_year())
        host_filter = request.args.get('host_filter', 'all')  # 'all' or 'prepkc'
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        )
        
        # Apply host filter if specified
        if host_filter == 'prepkc':
            org_stats = org_stats.filter(
                db.or_(
                    Event.session_host.ilike('%PREPKC%'),
                    Event.session_host.ilike('%prepkc%'),
                    Event.session_host.ilike('%PrepKC%')
                )
            )
        
        org_stats = org_stats.group_by(
            Organization.id
        ).all()

        # Format the data for Excel
        org_data = [{
            'Organization': org.name,
            'Unique Sessions': sessions,
            'Total Hours': round(hours or 0, 2),
            'Unique Volunteers': volunteers
        } for org, sessions, hours, volunteers in org_stats]

        # Sort in Python
        def get_sort_key(org):
            if sort == 'name':
                return org['Organization'].lower() if org['Organization'] else ''
            elif sort == 'unique_sessions':
                return org['Unique Sessions']
            elif sort == 'total_hours':
                return org['Total Hours']
            elif sort == 'unique_volunteers':
                return org['Unique Volunteers']
            return org['Total Hours']
        org_data.sort(key=get_sort_key, reverse=(order=='desc'))

        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#467599',
            'font_color': 'white',
            'border': 1
        })
        
        # Create DataFrame and write to Excel
        df = pd.DataFrame(org_data)
        df.to_excel(writer, sheet_name='Organization Thank You Report', index=False)
        
        # Format worksheet
        worksheet = writer.sheets['Organization Thank You Report']
        worksheet.set_column('A:A', 40)  # Organization
        worksheet.set_column('B:B', 20)  # Unique Sessions
        worksheet.set_column('C:C', 15)  # Total Hours
        worksheet.set_column('D:D', 20)  # Unique Volunteers
        
        # Apply header formatting
        worksheet.conditional_format('A1:D1', {'type': 'no_blanks', 'format': header_format})
        
        # Add summary statistics
        total_organizations = len(org_data)
        total_sessions = sum(org['Unique Sessions'] for org in org_data)
        total_hours = sum(org['Total Hours'] for org in org_data)
        total_volunteers = sum(org['Unique Volunteers'] for org in org_data)
        
        # Add summary section
        summary_row = total_organizations + 3
        worksheet.write(summary_row, 0, 'Summary Statistics', header_format)
        worksheet.write(summary_row + 1, 0, 'Total Organizations')
        worksheet.write(summary_row + 1, 1, total_organizations)
        worksheet.write(summary_row + 2, 0, 'Total Sessions')
        worksheet.write(summary_row + 2, 1, total_sessions)
        worksheet.write(summary_row + 3, 0, 'Total Hours')
        worksheet.write(summary_row + 3, 1, total_hours)
        worksheet.write(summary_row + 4, 0, 'Total Volunteers')
        worksheet.write(summary_row + 4, 1, total_volunteers)
        worksheet.write(summary_row + 5, 0, 'School Year')
        worksheet.write(summary_row + 5, 1, f"{school_year[:2]}-{school_year[2:]} School Year")
        worksheet.write(summary_row + 6, 0, 'Filter')
        worksheet.write(summary_row + 6, 1, 'PREPKC Events Only' if host_filter == 'prepkc' else 'All Events')
        
        writer.close()
        output.seek(0)
        
        # Create filename
        filter_suffix = '_PREPKC' if host_filter == 'prepkc' else ''
        filename = f"Organization_Thank_You_Report_{school_year[:2]}-{school_year[2:]}{filter_suffix}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
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

        # Get event details with enhanced breakdown
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
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

        # Enhanced breakdown queries
        from models.event import EventType
        
        # In-person vs Virtual breakdown
        event_type_breakdown = db.session.query(
            Event.type,
            db.func.count(db.distinct(Event.id)).label('event_count'),
            db.func.sum(EventParticipation.delivery_hours).label('total_hours'),
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count')
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Event.type
        ).all()
        
        # Format event type breakdown
        event_type_data = {}
        for event_type, count, hours, volunteers in event_type_breakdown:
            type_name = event_type.value if event_type else 'Unknown'
            event_type_data[type_name] = {
                'count': count,
                'hours': round(hours or 0, 2),
                'volunteers': volunteers
            }
        
        # Cancelled and No-show events
        cancelled_events = db.session.query(
            Event,
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count')
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
            EventParticipation.status.in_(['Cancelled', 'No Show', 'Did Not Attend', 'Teacher No-Show', 'Volunteer canceling due to snow', 'Weather Cancellation', 'School Closure', 'Emergency Cancellation'])
        ).group_by(
            Event.id
        ).all()
        
        cancelled_events_data = [{
            'date': event.start_date.strftime('%B %d, %Y'),
            'title': event.title,
            'type': event.type.value if event.type else 'Unknown',
            'volunteers': vol_count,
            'status': 'Cancelled/No Show'
        } for event, vol_count in cancelled_events]
        
        # Separate in-person and virtual events
        in_person_events = db.session.query(
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
            Event.type != EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Event.id
        ).all()
        
        # Format in-person events
        in_person_events_data = [{
            'date': event.start_date.strftime('%B %d, %Y'),
            'date_sort': event.start_date,
            'title': event.title,
            'type': event.type.value if event.type else 'Unknown',
            'volunteers': vol_count,
            'hours': round(hours or 0, 2)
        } for event, vol_count, hours in in_person_events]
        
        virtual_events = db.session.query(
            Event,
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count'),
            db.func.count(db.distinct(EventTeacher.teacher_id)).label('classroom_count')
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).outerjoin(
            EventTeacher, Event.id == EventTeacher.event_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast'])
        ).group_by(
            Event.id
        ).all()
        
        # Get detailed virtual events with volunteer names
        detailed_virtual_events = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status
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
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast'])
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()
        
        # Group virtual events by event with volunteer names
        virtual_events_by_event = {}
        for event, volunteer, status in detailed_virtual_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in virtual_events_by_event:
                virtual_events_by_event[event_key] = {
                    'event': event,
                    'volunteers': [],
                    'classroom_count': 0
                }
            virtual_events_by_event[event_key]['volunteers'].append({
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status
            })
        
        # Get classroom counts for each virtual event
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            classroom_count = db.session.query(
                db.func.count(db.distinct(EventTeacher.teacher_id))
            ).filter(
                EventTeacher.event_id == event.id,
                EventTeacher.status.in_(['simulcast', 'successfully completed'])
            ).scalar()
            event_data['classroom_count'] = classroom_count or 0
        
        # Format virtual events with volunteer names and time
        virtual_events_data = []
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            volunteer_names = [v['name'] for v in event_data['volunteers']]
            virtual_events_data.append({
                'date': event.start_date.strftime('%B %d, %Y'),
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'date_sort': event.start_date,
                'title': event.title,
                'type': event.type.value if event.type else 'Unknown',
                'volunteers': volunteer_names,
                'volunteer_count': len(volunteer_names),
                'classrooms': event_data['classroom_count']
            })
        
        # Calculate class reach for virtual events (teachers with simulcast or successfully completed)
        virtual_class_reach = db.session.query(
            db.func.count(db.distinct(EventTeacher.teacher_id)).label('teacher_count')
        ).join(
            Event, EventTeacher.event_id == Event.id
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
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Successfully Completed', 'Simulcast']),
            EventTeacher.status.in_(['simulcast', 'successfully completed'])
        ).scalar()
        
        virtual_class_reach = virtual_class_reach or 0
        
        # Detailed volunteer participation per event
        detailed_participation = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status,
            EventParticipation.delivery_hours
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()
        
        # Group detailed participation by event
        event_participation_data = {}
        for event, volunteer, status, hours in detailed_participation:
            event_key = f"{event.id}_{event.title}"
            if event_key not in event_participation_data:
                event_participation_data[event_key] = {
                    'event': {
                        'id': event.id,
                        'title': event.title,
                        'date': event.start_date.strftime('%B %d, %Y'),
                        'type': event.type.value if event.type else 'Unknown'
                    },
                    'participants': []
                }
            
            event_participation_data[event_key]['participants'].append({
                'volunteer_id': volunteer.id,
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status,
                'hours': round(hours or 0, 2) if hours else 0
            })

        # Calculate summary statistics
        total_sessions = len(events_data)
        total_hours = sum(vol['hours'] for vol in volunteers_data)
        total_volunteers = len(volunteers_data)
        total_cancelled = len(cancelled_events_data)

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            'reports/organization_thankyou_detail.html',
            organization=organization,
            volunteers=volunteers_data,
            events=events_data,
            in_person_events=in_person_events_data,
            virtual_events=virtual_events_data,
            virtual_class_reach=virtual_class_reach,
            event_type_breakdown=event_type_data,
            cancelled_events=cancelled_events_data,
            event_participation=event_participation_data,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort_vol=sort_vol,
            order_vol=order_vol,
            sort_evt=sort_evt,
            order_evt=order_evt,
            total_sessions=total_sessions,
            total_hours=total_hours,
            total_volunteers=total_volunteers,
            total_cancelled=total_cancelled
        )

    @bp.route('/reports/organization/thankyou/detail/<int:org_id>/excel')
    @login_required
    def organization_thankyou_detail_excel(org_id):
        """Generate Excel file for organization detail report"""
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Volunteer.id
        ).all()

        # Format volunteer data for Excel
        volunteers_data = [{
            'Name': f"{v.first_name} {v.last_name}",
            'Events': events,
            'Hours': round(hours or 0, 2)
        } for v, events, hours in volunteer_stats]

        # Sort volunteers in Python
        def get_vol_sort_key(vol):
            if sort_vol == 'name':
                return vol['Name'].lower() if vol['Name'] else ''
            elif sort_vol == 'events':
                return vol['Events']
            elif sort_vol == 'hours':
                return vol['Hours']
            return vol['Hours']
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Event.id
        ).all()

        # Format event data for Excel
        events_data = [{
            'Date': event.start_date.strftime('%B %d, %Y'),
            'Event': event.title,
            'Type': event.type.value if event.type else 'Unknown',
            'Volunteers': vol_count,
            'Hours': round(hours or 0, 2)
        } for event, vol_count, hours in events]

        # Sort events in Python
        def get_evt_sort_key(evt):
            if sort_evt == 'date':
                return evt['Date']
            elif sort_evt == 'title':
                return evt['Event'].lower() if evt['Event'] else ''
            elif sort_evt == 'type':
                return evt['Type'].lower() if evt['Type'] else ''
            elif sort_evt == 'volunteers':
                return evt['Volunteers']
            elif sort_evt == 'hours':
                return evt['Hours']
            return evt['Date']
        events_data.sort(key=get_evt_sort_key, reverse=(order_evt=='desc'))

        # Enhanced breakdown queries for Excel
        from models.event import EventType
        
        # In-person vs Virtual breakdown
        event_type_breakdown = db.session.query(
            Event.type,
            db.func.count(db.distinct(Event.id)).label('event_count'),
            db.func.sum(EventParticipation.delivery_hours).label('total_hours'),
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count')
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Event.type
        ).all()
        
        # Format event type breakdown for Excel
        event_type_data = []
        for event_type, count, hours, volunteers in event_type_breakdown:
            type_name = event_type.value if event_type else 'Unknown'
            event_type_data.append({
                'Event Type': type_name,
                'Event Count': count,
                'Total Hours': round(hours or 0, 2),
                'Volunteer Count': volunteers
            })
        
        # Separate in-person and virtual events for Excel
        in_person_events = db.session.query(
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
            Event.type != EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).group_by(
            Event.id
        ).all()
        
        virtual_events = db.session.query(
            Event,
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count'),
            db.func.count(db.distinct(EventTeacher.teacher_id)).label('classroom_count')
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).outerjoin(
            EventTeacher, Event.id == EventTeacher.event_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast'])
        ).group_by(
            Event.id
        ).all()
        
        # Get detailed virtual events with volunteer names for Excel
        detailed_virtual_events = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status
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
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast'])
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()
        
        # Group virtual events by event with volunteer names for Excel
        virtual_events_by_event = {}
        for event, volunteer, status in detailed_virtual_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in virtual_events_by_event:
                virtual_events_by_event[event_key] = {
                    'event': event,
                    'volunteers': [],
                    'classroom_count': 0
                }
            virtual_events_by_event[event_key]['volunteers'].append({
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status
            })
        
        # Get classroom counts for each virtual event for Excel
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            classroom_count = db.session.query(
                db.func.count(db.distinct(EventTeacher.teacher_id))
            ).filter(
                EventTeacher.event_id == event.id,
                EventTeacher.status.in_(['simulcast', 'successfully completed'])
            ).scalar()
            event_data['classroom_count'] = classroom_count or 0
        
        # Calculate virtual class reach for Excel
        virtual_class_reach = db.session.query(
            db.func.count(db.distinct(EventTeacher.teacher_id)).label('teacher_count')
        ).join(
            Event, EventTeacher.event_id == Event.id
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
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Successfully Completed', 'Simulcast']),
            EventTeacher.status.in_(['simulcast', 'successfully completed'])
        ).scalar()
        
        virtual_class_reach = virtual_class_reach or 0
        
        # Format in-person events for Excel
        in_person_events_data = [{
            'Date': event.start_date.strftime('%B %d, %Y'),
            'Event': event.title,
            'Type': event.type.value if event.type else 'Unknown',
            'Volunteers': vol_count,
            'Hours': round(hours or 0, 2)
        } for event, vol_count, hours in in_person_events]
        
        # Format virtual events for Excel
        virtual_events_data = []
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            volunteer_names = [v['name'] for v in event_data['volunteers']]
            virtual_events_data.append({
                'Date': event.start_date.strftime('%B %d, %Y'),
                'Time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'Event': event.title,
                'Type': event.type.value if event.type else 'Unknown',
                'Volunteers': ', '.join(volunteer_names) if volunteer_names else 'None',
                'Classrooms': event_data['classroom_count']
            })
        
        # Cancelled and No-show events
        cancelled_events = db.session.query(
            Event,
            db.func.count(db.distinct(EventParticipation.volunteer_id)).label('volunteer_count')
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
            EventParticipation.status.in_(['Cancelled', 'No Show', 'Did Not Attend', 'Teacher No-Show', 'Volunteer canceling due to snow', 'Weather Cancellation', 'School Closure', 'Emergency Cancellation'])
        ).group_by(
            Event.id
        ).all()
        
        cancelled_events_data = [{
            'Date': event.start_date.strftime('%B %d, %Y'),
            'Event': event.title,
            'Type': event.type.value if event.type else 'Unknown',
            'Volunteers': vol_count,
            'Status': 'Cancelled/No Show'
        } for event, vol_count in cancelled_events]
        
        # Detailed volunteer participation per event
        detailed_participation = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status,
            EventParticipation.delivery_hours
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()
        
        # Format detailed participation for Excel
        detailed_participation_data = []
        for event, volunteer, status, hours in detailed_participation:
            detailed_participation_data.append({
                'Event Date': event.start_date.strftime('%B %d, %Y'),
                'Event Title': event.title,
                'Event Type': event.type.value if event.type else 'Unknown',
                'Volunteer Name': f"{volunteer.first_name} {volunteer.last_name}",
                'Status': status,
                'Hours': round(hours or 0, 2) if hours else 0
            })

        # Calculate summary statistics
        total_sessions = len(events_data)
        total_hours = sum(vol['Hours'] for vol in volunteers_data)
        total_volunteers = len(volunteers_data)
        total_cancelled = len(cancelled_events_data)

        # Create Excel file
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        workbook = writer.book
        
        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#467599',
            'font_color': 'white',
            'border': 1
        })
        
        # Summary Sheet
        summary_data = {
            'Metric': [
                'Organization',
                'School Year',
                'Total Sessions',
                'Total Hours',
                'Total Volunteers',
                'Cancelled/No Show Events',
                'Virtual Sessions',
                'Classes Reached (Virtual)'
            ],
            'Value': [
                organization.name,
                f"{school_year[:2]}-{school_year[2:]} School Year",
                total_sessions,
                total_hours,
                total_volunteers,
                total_cancelled,
                len(virtual_events_data),
                virtual_class_reach
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 40)
        worksheet.conditional_format('A1:B8', {'type': 'no_blanks', 'format': header_format})
        
        # In-Person Events Sheet
        if in_person_events_data:
            in_person_df = pd.DataFrame(in_person_events_data)
            in_person_df.to_excel(writer, sheet_name='In-Person Events', index=False)
            
            # Format in-person events sheet
            worksheet = writer.sheets['In-Person Events']
            worksheet.set_column('A:A', 20)  # Date
            worksheet.set_column('B:B', 40)  # Event
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 15)  # Volunteers
            worksheet.set_column('E:E', 15)  # Hours
            worksheet.conditional_format('A1:E1', {'type': 'no_blanks', 'format': header_format})
        
        # Virtual Events Sheet
        if virtual_events_data:
            virtual_df = pd.DataFrame(virtual_events_data)
            virtual_df.to_excel(writer, sheet_name='Virtual Events', index=False)
            
            # Format virtual events sheet
            worksheet = writer.sheets['Virtual Events']
            worksheet.set_column('A:A', 20)  # Date
            worksheet.set_column('B:B', 15)  # Time
            worksheet.set_column('C:C', 40)  # Event
            worksheet.set_column('D:D', 20)  # Type
            worksheet.set_column('E:E', 40)  # Volunteers
            worksheet.set_column('F:F', 15)  # Classrooms
            worksheet.conditional_format('A1:F1', {'type': 'no_blanks', 'format': header_format})
        
        # Event Type Breakdown Sheet
        if event_type_data:
            event_type_df = pd.DataFrame(event_type_data)
            event_type_df.to_excel(writer, sheet_name='Event Type Breakdown', index=False)
            
            # Format event type breakdown sheet
            worksheet = writer.sheets['Event Type Breakdown']
            worksheet.set_column('A:A', 25)  # Event Type
            worksheet.set_column('B:B', 15)  # Event Count
            worksheet.set_column('C:C', 15)  # Total Hours
            worksheet.set_column('D:D', 20)  # Volunteer Count
            worksheet.conditional_format('A1:D1', {'type': 'no_blanks', 'format': header_format})
        
        # Volunteers Sheet
        if volunteers_data:
            volunteers_df = pd.DataFrame(volunteers_data)
            volunteers_df.to_excel(writer, sheet_name='Volunteers', index=False)
            
            # Format volunteers sheet
            worksheet = writer.sheets['Volunteers']
            worksheet.set_column('A:A', 30)  # Name
            worksheet.set_column('B:B', 15)  # Events
            worksheet.set_column('C:C', 15)  # Hours
            worksheet.conditional_format('A1:C1', {'type': 'no_blanks', 'format': header_format})
        
        # Events Sheet
        if events_data:
            events_df = pd.DataFrame(events_data)
            events_df.to_excel(writer, sheet_name='Events', index=False)
            
            # Format events sheet
            worksheet = writer.sheets['Events']
            worksheet.set_column('A:A', 20)  # Date
            worksheet.set_column('B:B', 40)  # Event
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 15)  # Volunteers
            worksheet.set_column('E:E', 15)  # Hours
            worksheet.conditional_format('A1:E1', {'type': 'no_blanks', 'format': header_format})
        
        # Cancelled Events Sheet
        if cancelled_events_data:
            cancelled_df = pd.DataFrame(cancelled_events_data)
            cancelled_df.to_excel(writer, sheet_name='Cancelled Events', index=False)
            
            # Format cancelled events sheet
            worksheet = writer.sheets['Cancelled Events']
            worksheet.set_column('A:A', 20)  # Date
            worksheet.set_column('B:B', 40)  # Event
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 15)  # Volunteers
            worksheet.set_column('E:E', 20)  # Status
            worksheet.conditional_format('A1:E1', {'type': 'no_blanks', 'format': header_format})
        
        # Detailed Participation Sheet
        if detailed_participation_data:
            detailed_df = pd.DataFrame(detailed_participation_data)
            detailed_df.to_excel(writer, sheet_name='Detailed Participation', index=False)
            
            # Format detailed participation sheet
            worksheet = writer.sheets['Detailed Participation']
            worksheet.set_column('A:A', 20)  # Event Date
            worksheet.set_column('B:B', 40)  # Event Title
            worksheet.set_column('C:C', 20)  # Event Type
            worksheet.set_column('D:D', 30)  # Volunteer Name
            worksheet.set_column('E:E', 20)  # Status
            worksheet.set_column('F:F', 15)  # Hours
            worksheet.conditional_format('A1:F1', {'type': 'no_blanks', 'format': header_format})
        
        writer.close()
        output.seek(0)
        
        # Create filename
        org_name_clean = organization.name.replace('/', '_').replace(' ', '_')
        filename = f"{org_name_clean}_{school_year[:2]}-{school_year[2:]}_Detail_Report.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        )
