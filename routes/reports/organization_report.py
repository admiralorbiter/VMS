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
from models.school_model import School
from models.district_model import District
from sqlalchemy.orm import aliased

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
            'email': v.primary_email,
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
                'id': event.id,
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

        # Get detailed virtual events with volunteer names and teacher details
        TeacherAlias = aliased(Teacher, flat=True)
        SchoolAlias = aliased(School, flat=True)
        DistrictAlias = aliased(District, flat=True)
        
        detailed_virtual_events = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status,
            EventTeacher,
            TeacherAlias,
            SchoolAlias,
            DistrictAlias
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).outerjoin(
            EventTeacher, Event.id == EventTeacher.event_id
        ).outerjoin(
            TeacherAlias, EventTeacher.teacher_id == TeacherAlias.id
        ).outerjoin(
            SchoolAlias, TeacherAlias.salesforce_school_id == SchoolAlias.id
        ).outerjoin(
            DistrictAlias, SchoolAlias.district_id == DistrictAlias.id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast']),
            Volunteer.exclude_from_reports == False,
            db.or_(
                TeacherAlias.id == None,  # No teacher associated with event
                TeacherAlias.exclude_from_reports == False  # Teacher is not excluded
            )
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()

        # Group virtual events by event with volunteer names and teacher details
        virtual_events_by_event = {}
        for event, volunteer, status, event_teacher, teacher, school, district in detailed_virtual_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in virtual_events_by_event:
                virtual_events_by_event[event_key] = {
                    'event': event,
                    'volunteers': [],
                    'classrooms': [],
                    'unique_classroom_count': 0
                }
            virtual_events_by_event[event_key]['volunteers'].append({
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status
            })
            
            # Add teacher/classroom information if available
            if teacher and event_teacher and event_teacher.status in ['simulcast', 'successfully completed']:
                classroom_info = {
                    'teacher_id': teacher.id,
                    'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                    'school_name': school.name if school else 'Unknown School',
                    'district_name': district.name if district else 'Unknown District',
                    'status': event_teacher.status
                }
                virtual_events_by_event[event_key]['classrooms'].append(classroom_info)

        # Calculate unique classroom count for each event
        for event_key, event_data in virtual_events_by_event.items():
            # Get unique teachers for this event
            unique_teachers = set()
            for classroom in event_data['classrooms']:
                unique_teachers.add(classroom['teacher_name'])
            event_data['unique_classroom_count'] = len(unique_teachers)

        # Format virtual events with volunteer names, time, and classroom details
        virtual_events_data = []
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            # Get unique volunteer names (remove duplicates)
            unique_volunteer_names = list(set([v['name'] for v in event_data['volunteers']]))
            virtual_events_data.append({
                'id': event.id,
                'date': event.start_date.strftime('%m/%d/%y'),
                'time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'date_sort': event.start_date,
                'title': event.title,
                'type': event.type.value if event.type else 'Unknown',
                'volunteers': unique_volunteer_names,
                'volunteer_count': len(unique_volunteer_names),
                'classrooms': event_data['unique_classroom_count'],
                'classroom_details': event_data['classrooms']
            })

        # Calculate total unique classrooms across all virtual events and track session counts
        teacher_session_counts = {}
        for event_data in virtual_events_by_event.values():
            for classroom in event_data['classrooms']:
                teacher_name = classroom['teacher_name']
                if teacher_name not in teacher_session_counts:
                    teacher_session_counts[teacher_name] = 0
                teacher_session_counts[teacher_name] += 1
        
        total_unique_classrooms = len(teacher_session_counts)

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
        total_classrooms_reached = total_unique_classrooms

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

    @bp.route('/reports/organization/report/detail/<int:org_id>/excel')
    @login_required
    def organization_report_detail_excel(org_id):
        """Generate comprehensive Excel file for organization report detail with all granular data"""
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
            'Name': f"{v.first_name} {v.last_name}",
            'Email': v.primary_email,
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
            student_count = event.participant_count or 0
            
            in_person_events_data.append({
                'Date': event.start_date.strftime('%m/%d/%y'),
                'Title': event.title,
                'Type': event.type.value if event.type else 'Unknown',
                'Volunteers': ', '.join(volunteer_names) if volunteer_names else 'None',
                'Volunteer Count': len(volunteer_names),
                'Hours': round(event_data['total_hours'], 2),
                'Students': student_count
            })

        # Sort in-person events in Python
        def get_inperson_sort_key(evt):
            if sort_evt == 'date':
                return datetime.strptime(evt['Date'], '%m/%d/%y')
            elif sort_evt == 'title':
                return evt['Title'].lower() if evt['Title'] else ''
            elif sort_evt == 'type':
                return evt['Type'].lower() if evt['Type'] else ''
            elif sort_evt == 'volunteers':
                return evt['Volunteer Count']
            elif sort_evt == 'hours':
                return evt['Hours']
            elif sort_evt == 'students':
                return evt['Students']
            return datetime.strptime(evt['Date'], '%m/%d/%y')
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

        # Get detailed virtual events with volunteer names and teacher details
        TeacherAlias = aliased(Teacher, flat=True)
        SchoolAlias = aliased(School, flat=True)
        DistrictAlias = aliased(District, flat=True)
        
        detailed_virtual_events = db.session.query(
            Event,
            Volunteer,
            EventParticipation.status,
            EventTeacher,
            TeacherAlias,
            SchoolAlias,
            DistrictAlias
        ).join(
            EventParticipation, Event.id == EventParticipation.event_id
        ).join(
            Volunteer, EventParticipation.volunteer_id == Volunteer.id
        ).join(
            VolunteerOrganization, Volunteer.id == VolunteerOrganization.volunteer_id
        ).outerjoin(
            EventTeacher, Event.id == EventTeacher.event_id
        ).outerjoin(
            TeacherAlias, EventTeacher.teacher_id == TeacherAlias.id
        ).outerjoin(
            SchoolAlias, TeacherAlias.salesforce_school_id == SchoolAlias.id
        ).outerjoin(
            DistrictAlias, SchoolAlias.district_id == DistrictAlias.id
        ).filter(
            VolunteerOrganization.organization_id == org_id,
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.type == EventType.VIRTUAL_SESSION,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed', 'Simulcast']),
            Volunteer.exclude_from_reports == False,
            db.or_(
                TeacherAlias.id == None,  # No teacher associated with event
                TeacherAlias.exclude_from_reports == False  # Teacher is not excluded
            )
        ).order_by(
            Event.start_date, Event.title, Volunteer.last_name, Volunteer.first_name
        ).all()

        # Group virtual events by event with volunteer names and teacher details
        virtual_events_by_event = {}
        for event, volunteer, status, event_teacher, teacher, school, district in detailed_virtual_events:
            event_key = f"{event.id}_{event.title}"
            if event_key not in virtual_events_by_event:
                virtual_events_by_event[event_key] = {
                    'event': event,
                    'volunteers': [],
                    'classrooms': [],
                    'unique_classroom_count': 0
                }
            virtual_events_by_event[event_key]['volunteers'].append({
                'name': f"{volunteer.first_name} {volunteer.last_name}",
                'status': status
            })
            
            # Add teacher/classroom information if available and not excluded
            if teacher and event_teacher and event_teacher.status in ['simulcast', 'successfully completed'] and not teacher.exclude_from_reports:
                classroom_info = {
                    'teacher_name': f"{teacher.first_name} {teacher.last_name}",
                    'school_name': school.name if school else 'Unknown School',
                    'district_name': district.name if district else 'Unknown District',
                    'status': event_teacher.status
                }
                virtual_events_by_event[event_key]['classrooms'].append(classroom_info)

        # Calculate unique classroom count for each event
        for event_key, event_data in virtual_events_by_event.items():
            unique_teachers = set()
            for classroom in event_data['classrooms']:
                unique_teachers.add(classroom['teacher_name'])
            event_data['unique_classroom_count'] = len(unique_teachers)

        # Format virtual events with volunteer names, time, and classroom details
        virtual_events_data = []
        for event_key, event_data in virtual_events_by_event.items():
            event = event_data['event']
            volunteer_names = [v['name'] for v in event_data['volunteers']]
            virtual_events_data.append({
                'Date': event.start_date.strftime('%m/%d/%y'),
                'Time': event.start_date.strftime('%I:%M %p') if event.start_date else '',
                'Title': event.title,
                'Type': event.type.value if event.type else 'Unknown',
                'Volunteers': ', '.join(volunteer_names) if volunteer_names else 'None',
                'Volunteer Count': len(volunteer_names),
                'Classrooms': event_data['unique_classroom_count'],
                'classroom_details': event_data['classrooms']
            })

        # Sort virtual events in Python
        def get_virtual_sort_key(evt):
            if sort_evt == 'date':
                return datetime.strptime(evt['Date'], '%m/%d/%y')
            elif sort_evt == 'title':
                return evt['Title'].lower() if evt['Title'] else ''
            elif sort_evt == 'type':
                return evt['Type'].lower() if evt['Type'] else ''
            elif sort_evt == 'volunteers':
                return evt['Volunteer Count']
            elif sort_evt == 'classrooms':
                return evt['Classrooms']
            return datetime.strptime(evt['Date'], '%m/%d/%y')
        virtual_events_data.sort(key=get_virtual_sort_key, reverse=(order_evt=='desc'))

        # Get cancelled events
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
            'Date': event.start_date.strftime('%m/%d/%y'),
            'Title': event.title,
            'Type': event.type.value if event.type else 'Unknown',
            'Volunteers': vol_count,
            'Status': 'Cancelled/No Show'
        } for event, vol_count in cancelled_events]

        # Calculate total unique classrooms across all virtual events for Excel and track session counts
        teacher_session_counts_excel = {}
        for event_data in virtual_events_by_event.items():
            for classroom in event_data[1]['classrooms']:
                teacher_name = classroom['teacher_name']
                if teacher_name not in teacher_session_counts_excel:
                    teacher_session_counts_excel[teacher_name] = 0
                teacher_session_counts_excel[teacher_name] += 1
        
        total_unique_classrooms_excel = len(teacher_session_counts_excel)

        # Calculate summary statistics
        total_inperson_sessions = len(in_person_events_data)
        total_virtual_sessions = len(virtual_events_data)
        total_sessions = total_inperson_sessions + total_virtual_sessions
        total_hours = sum(vol['Hours'] for vol in volunteers_data)
        total_volunteers = len(volunteers_data)
        total_cancelled = len(cancelled_events_data)
        total_students_reached = sum(evt['Students'] for evt in in_person_events_data)
        total_classrooms_reached = total_unique_classrooms_excel

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
                'In-Person Sessions',
                'Virtual Sessions',
                'Students Reached (In-Person)',
                'Classrooms Reached (Virtual)'
            ],
            'Value': [
                organization.name,
                f"{school_year[:2]}-{school_year[2:]} School Year",
                total_sessions,
                total_hours,
                total_volunteers,
                total_cancelled,
                total_inperson_sessions,
                total_virtual_sessions,
                total_students_reached,
                total_classrooms_reached
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 40)
        worksheet.conditional_format('A1:B10', {'type': 'no_blanks', 'format': header_format})
        
        # Volunteers Sheet
        if volunteers_data:
            volunteers_df = pd.DataFrame(volunteers_data)
            volunteers_df.to_excel(writer, sheet_name='Volunteers', index=False)
            
            # Format volunteers sheet
            worksheet = writer.sheets['Volunteers']
            worksheet.set_column('A:A', 30)  # Name
            worksheet.set_column('B:B', 35)  # Email
            worksheet.set_column('C:C', 15)  # Events
            worksheet.set_column('D:D', 15)  # Hours
            worksheet.conditional_format('A1:D1', {'type': 'no_blanks', 'format': header_format})
        
        # In-Person Events Sheet
        if in_person_events_data:
            in_person_df = pd.DataFrame(in_person_events_data)
            in_person_df.to_excel(writer, sheet_name='In-Person Events', index=False)
            
            # Format in-person events sheet
            worksheet = writer.sheets['In-Person Events']
            worksheet.set_column('A:A', 15)  # Date
            worksheet.set_column('B:B', 40)  # Title
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 40)  # Volunteers
            worksheet.set_column('E:E', 15)  # Volunteer Count
            worksheet.set_column('F:F', 15)  # Hours
            worksheet.set_column('G:G', 15)  # Students
            worksheet.conditional_format('A1:G1', {'type': 'no_blanks', 'format': header_format})
        
        # Virtual Events Sheet
        if virtual_events_data:
            virtual_df = pd.DataFrame(virtual_events_data)
            virtual_df.to_excel(writer, sheet_name='Virtual Events', index=False)
            
            # Format virtual events sheet
            worksheet = writer.sheets['Virtual Events']
            worksheet.set_column('A:A', 15)  # Date
            worksheet.set_column('B:B', 15)  # Time
            worksheet.set_column('C:C', 40)  # Title
            worksheet.set_column('D:D', 20)  # Type
            worksheet.set_column('E:E', 40)  # Volunteers
            worksheet.set_column('F:F', 15)  # Volunteer Count
            worksheet.set_column('G:G', 15)  # Classrooms
            worksheet.conditional_format('A1:G1', {'type': 'no_blanks', 'format': header_format})
            
            # Classroom Details Sheet (Unique Teachers)
            unique_classroom_details_data = []
            unique_teachers_seen = set()
            
            for event in virtual_events_data:
                if 'classroom_details' in event and event['classroom_details']:
                    for classroom in event['classroom_details']:
                        if classroom['teacher_name'] not in unique_teachers_seen:
                            unique_teachers_seen.add(classroom['teacher_name'])
                            session_count = teacher_session_counts_excel.get(classroom['teacher_name'], 1)
                            unique_classroom_details_data.append({
                                'Teacher Name': classroom['teacher_name'],
                                'School': classroom['school_name'],
                                'District': classroom['district_name']
                            })
            
            if unique_classroom_details_data:
                classroom_df = pd.DataFrame(unique_classroom_details_data)
                classroom_df.to_excel(writer, sheet_name='Unique Teachers', index=False)
                
                # Format classroom details sheet
                worksheet = writer.sheets['Unique Teachers']
                worksheet.set_column('A:A', 30)  # Teacher Name
                worksheet.set_column('B:B', 40)  # School
                worksheet.set_column('C:C', 30)  # District
                worksheet.conditional_format('A1:C1', {'type': 'no_blanks', 'format': header_format})
        
        # Cancelled Events Sheet
        if cancelled_events_data:
            cancelled_df = pd.DataFrame(cancelled_events_data)
            cancelled_df.to_excel(writer, sheet_name='Cancelled Events', index=False)
            
            # Format cancelled events sheet
            worksheet = writer.sheets['Cancelled Events']
            worksheet.set_column('A:A', 15)  # Date
            worksheet.set_column('B:B', 40)  # Title
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 15)  # Volunteers
            worksheet.set_column('E:E', 20)  # Status
            worksheet.conditional_format('A1:E1', {'type': 'no_blanks', 'format': header_format})
        
        writer.close()
        output.seek(0)
        
        # Create filename
        filename = f"Organization_Detail_{organization.name.replace(' ', '_')}_{school_year[:2]}-{school_year[2:]}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        ) 