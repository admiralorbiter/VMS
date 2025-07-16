from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from datetime import datetime
from sqlalchemy import extract
import io
import pandas as pd
import xlsxwriter

from models.organization import Organization, VolunteerOrganization
from models.volunteer import Volunteer, EventParticipation
from models.event import Event, EventTeacher, EventType, EventStatus
from models.teacher import Teacher
from models import db
from routes.reports.common import get_current_school_year, get_school_year_date_range

# Create blueprint
organization_report_bp = Blueprint('organization_report', __name__)

def load_routes(bp):
    @bp.route('/reports/organization/report')
    @login_required
    def organization_report():
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
            'reports/organization_report.html',
            organizations=org_data,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            sort=sort,
            order=order,
            host_filter=host_filter
        )

    @bp.route('/reports/organization/report/detail/<int:org_id>')
    @login_required
    def organization_report_detail(org_id):
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed']),
            Volunteer.exclude_from_reports == False
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

        # Get in-person events with student counts and volunteer details
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed']),
            Volunteer.exclude_from_reports == False
        ).group_by(
            Event.id
        ).all()

        # Get detailed in-person events with volunteer names
        detailed_inperson_events = db.session.query(
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
            Event.start_date <= end_date,
            Event.type != EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed']),
            Volunteer.exclude_from_reports == False
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()

        # Group in-person events by event with volunteer names
        inperson_events_by_event = {}
        for event, volunteer, status, hours in detailed_inperson_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in inperson_events_by_event:
                inperson_events_by_event[event_key] = {
                    'event': event,
                    'volunteers': [],
                    'total_hours': 0
                }
            inperson_events_by_event[event_key]['volunteers'].append({
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status,
                'hours': hours or 0
            })
            inperson_events_by_event[event_key]['total_hours'] += hours or 0

        # Format in-person events data with volunteer names
        in_person_events_data = []
        for event_key, event_data in inperson_events_by_event.items():
            event = event_data['event']
            volunteer_names = [v['name'] for v in event_data['volunteers']]
            
            # Calculate student count for this event
            # For in-person events, we'll use participant_count as a fallback
            student_count = event.participant_count or 0
            
            in_person_events_data.append({
                'date': event.start_date.strftime('%m/%d/%y'),
                'date_sort': event.start_date,
                'title': event.title,
                'type': event.type.value if event.type else 'Unknown',
                'volunteers': volunteer_names,
                'volunteer_count': len(volunteer_names),
                'hours': round(event_data['total_hours'], 2),
                'students': student_count
            })

        # Sort in-person events in Python
        def get_inperson_sort_key(evt):
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
            elif sort_evt == 'students':
                return evt['students']
            return evt['date_sort']
        in_person_events_data.sort(key=get_inperson_sort_key, reverse=(order_evt=='desc'))

        # Get virtual events with classroom counts
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast']),
            Volunteer.exclude_from_reports == False
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
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast']),
            Volunteer.exclude_from_reports == False
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
            
            # Check if any participating volunteer is excluded from reports
            excluded_volunteer_participated = db.session.query(
                EventParticipation
            ).join(
                Volunteer, EventParticipation.volunteer_id == Volunteer.id
            ).filter(
                EventParticipation.event_id == event.id,
                Volunteer.exclude_from_reports == True
            ).first()
            
            # If an excluded volunteer participated, don't count classrooms for this event
            if excluded_volunteer_participated:
                event_data['classroom_count'] = 0
            else:
                # Count classrooms (teachers) for this event, excluding teachers marked as excluded
                classroom_count = db.session.query(
                    db.func.count(db.distinct(EventTeacher.teacher_id))
                ).join(
                    Event, EventTeacher.event_id == Event.id
                ).join(
                    Teacher, EventTeacher.teacher_id == Teacher.id
                ).filter(
                    EventTeacher.event_id == event.id,
                    EventTeacher.status.in_(['simulcast', 'successfully completed']),
                    Teacher.exclude_from_reports == False
                ).scalar()
                event_data['classroom_count'] = classroom_count or 0

        # Format virtual events with volunteer names and time
        virtual_events_data = []
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            volunteer_names = [v['name'] for v in event_data['volunteers']]
            virtual_events_data.append({
                'date': event.start_date.strftime('%m/%d/%y'),
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'date_sort': event.start_date,
                'title': event.title,
                'type': event.type.value if event.type else 'Unknown',
                'volunteers': volunteer_names,
                'volunteer_count': len(volunteer_names),
                'classrooms': event_data['classroom_count']
            })

        # Sort virtual events in Python
        def get_virtual_sort_key(evt):
            if sort_evt == 'date':
                return evt['date_sort']
            elif sort_evt == 'title':
                return evt['title'].lower() if evt['title'] else ''
            elif sort_evt == 'type':
                return evt['type'].lower() if evt['type'] else ''
            elif sort_evt == 'volunteers':
                return evt['volunteer_count']
            elif sort_evt == 'classrooms':
                return evt['classrooms']
            return evt['date_sort']
        virtual_events_data.sort(key=get_virtual_sort_key, reverse=(order_evt=='desc'))

        # Get cancelled events - include both event-level cancellations and volunteer participation cancellations
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
            db.or_(
                # Event-level cancellation
                Event.status == EventStatus.CANCELLED,
                # Volunteer participation cancellation statuses
                EventParticipation.status.in_(['Cancelled', 'No Show', 'Did Not Attend', 'Teacher No-Show', 'Volunteer canceling due to snow', 'Weather Cancellation', 'School Closure', 'Emergency Cancellation'])
            ),
            Volunteer.exclude_from_reports == False
        ).group_by(
            Event.id
        ).all()

        cancelled_events_data = [{
            'date': event.start_date.strftime('%m/%d/%y'),
            'title': event.title,
            'type': event.type.value if event.type else 'Unknown',
            'volunteers': vol_count,
            'status': 'Cancelled/No Show'
        } for event, vol_count in cancelled_events]

        # Calculate summary statistics
        total_inperson_sessions = len(in_person_events_data)
        total_virtual_sessions = len(virtual_events_data)
        total_sessions = total_inperson_sessions + total_virtual_sessions
        total_hours = sum(vol['hours'] for vol in volunteers_data)
        total_volunteers = len(volunteers_data)
        total_cancelled = len(cancelled_events_data)
        total_students_reached = sum(evt['students'] for evt in in_person_events_data)
        total_classrooms_reached = sum(evt['classrooms'] for evt in virtual_events_data)

        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first

        return render_template(
            'reports/organization_report_detail.html',
            organization=organization,
            volunteers=volunteers_data,
            in_person_events=in_person_events_data,
            virtual_events=virtual_events_data,
            cancelled_events=cancelled_events_data,
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
            total_cancelled=total_cancelled,
            total_students_reached=total_students_reached,
            total_classrooms_reached=total_classrooms_reached,
            total_inperson_sessions=total_inperson_sessions,
            total_virtual_sessions=total_virtual_sessions
        )

    @bp.route('/reports/organization/report/excel')
    @login_required
    def organization_report_excel():
        """Generate Excel file for organization report"""
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
        df.to_excel(writer, sheet_name='Organization Report', index=False)
        
        # Format worksheet
        worksheet = writer.sheets['Organization Report']
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
        filename = f"Organization_Report_{school_year[:2]}-{school_year[2:]}{filter_suffix}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        ) 