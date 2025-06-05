from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required
from datetime import datetime
import pytz
import io
import pandas as pd
import xlsxwriter
from sqlalchemy import func, distinct

from models.event import Event, EventAttendance, EventStatus, EventType, EventStudentParticipation
from models.district_model import District
from models.school_model import School
from models.reports import DistrictEngagementReport
from models.volunteer import EventParticipation, Skill, Volunteer, VolunteerSkill
from models import db
from models.organization import Organization, VolunteerOrganization
from models.student import Student
from models.teacher import Teacher

from routes.reports.common import (
    DISTRICT_MAPPING, 
    get_current_school_year, 
    get_school_year_date_range,
    get_district_student_count_for_event
)

# Create blueprint
district_engagement_bp = Blueprint('district_engagement', __name__)

def load_routes(bp):
    @bp.route('/reports/district/engagement')
    @login_required
    def district_engagement():
        # Get school year from query params or default to current
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get cached reports for the school year
        cached_reports = DistrictEngagementReport.query.filter_by(school_year=school_year).all()
        
        district_stats = {report.district.name: report.summary_stats for report in cached_reports}
        
        if not district_stats:
            # Generate new stats if no cache exists
            district_stats = generate_district_engagement_stats(school_year)
            # Use the detailed caching function to ensure all data is cached
            cache_district_engagement_stats_with_details(school_year, district_stats)
            
            # Reload cached reports to get the updated data
            cached_reports = DistrictEngagementReport.query.filter_by(school_year=school_year).all()
            district_stats = {report.district.name: report.summary_stats for report in cached_reports}
        
        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first
        
        # Convert UTC time to Central time for display
        last_updated = None
        if cached_reports:
            utc_time = min(report.last_updated for report in cached_reports)
            central = pytz.timezone('America/Chicago')
            last_updated = utc_time.replace(tzinfo=pytz.UTC).astimezone(central)
        
        return render_template(
            'reports/district_engagement.html',
            districts=district_stats,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now(),
            last_updated=last_updated
        )

    @bp.route('/reports/district/engagement/refresh', methods=['POST'])
    @login_required
    def refresh_district_engagement():
        """Refresh the cached district engagement report data"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        try:
            # Delete existing cached reports for this school year
            deleted_count = DistrictEngagementReport.query.filter_by(school_year=school_year).delete()
            db.session.commit()
            
            # Generate new stats
            district_stats = generate_district_engagement_stats(school_year)
            
            # Cache the stats and detailed data
            cache_district_engagement_stats_with_details(school_year, district_stats)
            
            return jsonify({
                'success': True, 
                'message': f'Successfully refreshed engagement data for {school_year[:2]}-{school_year[2:]} school year'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/reports/district/engagement/detail/<district_name>')
    @login_required
    def district_engagement_detail(district_name):
        """Show detailed engagement report for a specific district"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Try to get cached data first
        cached_report = DistrictEngagementReport.query.filter_by(
            district_id=district.id,
            school_year=school_year
        ).first()
        
        if cached_report and is_cache_complete(cached_report):
            # Use cached detailed data
            engagement_data = {
                'summary_stats': cached_report.summary_stats,
                'volunteers': cached_report.volunteers_data,
                'students': cached_report.students_data,
                'events': cached_report.events_data
            }
            # Get event types from cached events data
            event_types = {}
            for event in cached_report.events_data:
                event_type = event.get('type', 'Unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
        else:
            # Generate detailed engagement data if not cached or incomplete
            engagement_data = generate_detailed_engagement_data(district, school_year)
            
            # Update or create the cache with detailed data
            if not cached_report:
                cached_report = DistrictEngagementReport(
                    district_id=district.id,
                    school_year=school_year
                )
                db.session.add(cached_report)
            
            # Update cache with all data
            cached_report.summary_stats = engagement_data['summary_stats']
            cached_report.volunteers_data = engagement_data['volunteers']
            cached_report.students_data = engagement_data['students']
            cached_report.events_data = engagement_data['events']
            cached_report.last_updated = datetime.utcnow()
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Log error but continue with generated data
                print(f"Error caching data: {e}")
            
            # Get event types from generated data
            event_types = engagement_data.get('event_types', {})
        
        return render_template(
            'reports/district_engagement_detail.html',
            district=district,
            school_year=school_year,
            event_types=event_types,
            **engagement_data
        )

    @bp.route('/reports/district/engagement/<district_name>/excel')
    @login_required
    def district_engagement_excel(district_name):
        """Generate Excel file for district engagement report"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Try to get cached data first
        cached_report = DistrictEngagementReport.query.filter_by(
            district_id=district.id,
            school_year=school_year
        ).first()
        
        if cached_report and is_cache_complete(cached_report):
            # Use cached detailed data
            engagement_data = {
                'summary_stats': cached_report.summary_stats,
                'volunteers': cached_report.volunteers_data,
                'students': cached_report.students_data,
                'events': cached_report.events_data
            }
        else:
            # Generate detailed engagement data if not cached
            engagement_data = generate_detailed_engagement_data(district, school_year)
        
        # Cache the data if we don't have a complete cache
        if cached_report:
            cached_report.volunteers_data = engagement_data['volunteers']
            cached_report.students_data = engagement_data['students']
            cached_report.events_data = engagement_data['events']
            cached_report.last_updated = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        
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
                'Unique Volunteers',
                'Total Volunteer Engagements',
                'Total Volunteer Hours',
                'Unique Students',
                'Total Student Participations',
                'Unique Events',
                'Unique Organizations',
                'Schools Engaged'
            ],
            'Value': [
                engagement_data['summary_stats']['unique_volunteers'],
                engagement_data['summary_stats']['total_volunteer_engagements'],
                engagement_data['summary_stats']['total_volunteer_hours'],
                engagement_data['summary_stats']['unique_students'],
                engagement_data['summary_stats']['total_student_participations'],
                engagement_data['summary_stats']['unique_events'],
                engagement_data['summary_stats']['unique_organizations'],
                engagement_data['summary_stats']['schools_engaged']
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format summary sheet
        worksheet = writer.sheets['Summary']
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.conditional_format('A1:B9', {'type': 'no_blanks', 'format': header_format})
        
        # Volunteers Sheet
        if engagement_data['volunteers']:
            volunteers_data = []
            for volunteer in engagement_data['volunteers']:
                volunteers_data.append({
                    'Name': f"{volunteer['first_name']} {volunteer['last_name']}",
                    'Email': volunteer['email'],
                    'Organization': volunteer['organization'],
                    'Events Participated': volunteer['events_count'],
                    'Total Hours': volunteer['total_hours'],
                    'Skills': ', '.join(volunteer['skills'])
                })
            
            volunteers_df = pd.DataFrame(volunteers_data)
            volunteers_df.to_excel(writer, sheet_name='Volunteers', index=False)
            
            # Format volunteers sheet
            worksheet = writer.sheets['Volunteers']
            worksheet.set_column('A:A', 20)  # Name
            worksheet.set_column('B:B', 30)  # Email
            worksheet.set_column('C:C', 25)  # Organization
            worksheet.set_column('D:D', 15)  # Events
            worksheet.set_column('E:E', 15)  # Hours
            worksheet.set_column('F:F', 40)  # Skills
            worksheet.conditional_format('A1:F1', {'type': 'no_blanks', 'format': header_format})
        
        # Students Sheet
        if engagement_data['students']:
            students_data = []
            for student in engagement_data['students']:
                students_data.append({
                    'Name': f"{student['first_name']} {student['last_name']}",
                    'Email': student['email'],
                    'School': student['school'],
                    'Grade': student['grade'],
                    'Events Attended': student['events_count']
                })
            
            students_df = pd.DataFrame(students_data)
            students_df.to_excel(writer, sheet_name='Students', index=False)
            
            # Format students sheet
            worksheet = writer.sheets['Students']
            worksheet.set_column('A:A', 20)  # Name
            worksheet.set_column('B:B', 30)  # Email
            worksheet.set_column('C:C', 25)  # School
            worksheet.set_column('D:D', 10)  # Grade
            worksheet.set_column('E:E', 15)  # Events
            worksheet.conditional_format('A1:E1', {'type': 'no_blanks', 'format': header_format})
        
        # Events Sheet
        if engagement_data['events']:
            events_data = []
            for event in engagement_data['events']:
                events_data.append({
                    'Date': event['date'],
                    'Title': event['title'],
                    'Type': event['type'],
                    'Location': event['location'],
                    'Volunteers': event['volunteer_count'],
                    'Students': event['student_count'],
                    'Volunteer Hours': event['volunteer_hours']
                })
            
            events_df = pd.DataFrame(events_data)
            events_df.to_excel(writer, sheet_name='Events', index=False)
            
            # Format events sheet
            worksheet = writer.sheets['Events']
            worksheet.set_column('A:A', 12)  # Date
            worksheet.set_column('B:B', 40)  # Title
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 30)  # Location
            worksheet.set_column('E:G', 15)  # Numbers
            worksheet.conditional_format('A1:G1', {'type': 'no_blanks', 'format': header_format})
        
        writer.close()
        output.seek(0)
        
        # Create filename
        filename = f"{district_name.replace(' ', '_')}_{school_year}_Engagement_Report.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        )

    @bp.route('/reports/district/engagement/detail/<district_name>/filtered-stats')
    @login_required
    def get_filtered_engagement_stats(district_name):
        """Get precise filtered engagement stats for selected event types"""
        school_year = request.args.get('school_year', get_current_school_year())
        event_types = request.args.getlist('event_types[]')
        
        if not event_types:
            return jsonify({'error': 'No event types specified'}), 400
        
        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({'error': 'District not found'}), 404
        
        # Generate filtered engagement data
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']
        
        # Get district mapping
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                                if mapping['name'] == district.name), None)
        
        # Get all schools for this district
        schools = School.query.filter_by(district_id=district.id).all()
        
        # Build query conditions
        district_partner_conditions = [
            Event.district_partner.ilike(f"%{school.name}%") for school in schools
        ]
        district_partner_conditions.append(Event.district_partner.ilike(f"%{district.name}%"))

        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                district_partner_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Get events of specified types for this district
        events = Event.query.filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            Event.type.in_([EventType(t) for t in event_types]),
            db.or_(
                Event.districts.contains(district),
                Event.school.in_([school.id for school in schools]),
                *district_partner_conditions
            )
        ).distinct().all()
        
        event_ids = [event.id for event in events]
        
        # Calculate volunteer stats
        unique_volunteers = set()
        total_volunteer_engagements = 0
        total_volunteer_hours = 0
        
        volunteer_participations = EventParticipation.query.filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).all()
        
        for participation in volunteer_participations:
            unique_volunteers.add(participation.volunteer_id)
            total_volunteer_engagements += 1
            total_volunteer_hours += participation.delivery_hours or 0
        
        # Calculate student stats (excluding virtual sessions for unique count)
        non_virtual_event_ids = [e.id for e in events if e.type != EventType.VIRTUAL_SESSION]
        unique_students = set()
        total_student_participations = 0
        
        if non_virtual_event_ids:
            student_participations = EventStudentParticipation.query.join(
                Student, EventStudentParticipation.student_id == Student.id
            ).join(
                School, Student.school_id == School.id
            ).filter(
                EventStudentParticipation.event_id.in_(non_virtual_event_ids),
                EventStudentParticipation.status == 'Attended',
                School.district_id == district.id
            ).all()
            
            for participation in student_participations:
                unique_students.add(participation.student_id)
                total_student_participations += 1
        
        # Calculate total students including virtual estimates
        total_students_with_virtual = 0
        for event in events:
            total_students_with_virtual += get_district_student_count_for_event(event, district.id)
        
        # Get unique organizations
        unique_organizations = 0
        if unique_volunteers:
            volunteer_id_list = list(unique_volunteers)
            unique_organizations = db.session.query(distinct(VolunteerOrganization.organization_id)).filter(
                VolunteerOrganization.volunteer_id.in_(volunteer_id_list)
            ).count()
        
        # Get schools engaged
        schools_engaged = len(set([event.school for event in events if event.school]))
        
        return jsonify({
            'unique_volunteers': len(unique_volunteers),
            'total_volunteer_engagements': total_volunteer_engagements,
            'total_volunteer_hours': round(total_volunteer_hours, 1),
            'unique_students': len(unique_students),
            'total_student_participations': total_student_participations,
            'total_students_with_virtual': total_students_with_virtual,
            'unique_events': len(events),
            'unique_organizations': unique_organizations,
            'schools_engaged': schools_engaged
        })

    @bp.route('/reports/district/engagement/detail/<district_name>/filtered-participants')
    @login_required
    def get_filtered_participants(district_name):
        """Get filtered volunteers and students for selected event types"""
        school_year = request.args.get('school_year', get_current_school_year())
        event_types = request.args.getlist('event_types[]')
        
        if not event_types:
            return jsonify({'error': 'No event types specified'}), 400
        
        # Get district
        district = District.query.filter_by(name=district_name).first()
        if not district:
            return jsonify({'error': 'District not found'}), 404
        
        # Get events of specified types for this district (same logic as before)
        start_date, end_date = get_school_year_date_range(school_year)
        excluded_event_types = ['connector_session']
        
        # Get district mapping
        district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                                if mapping['name'] == district.name), None)
        
        # Get all schools for this district
        schools = School.query.filter_by(district_id=district.id).all()
        
        # Build query conditions
        district_partner_conditions = [
            Event.district_partner.ilike(f"%{school.name}%") for school in schools
        ]
        district_partner_conditions.append(Event.district_partner.ilike(f"%{district.name}%"))

        if district_mapping and 'aliases' in district_mapping:
            for alias in district_mapping['aliases']:
                district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                district_partner_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Get events of specified types for this district
        events = Event.query.filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            Event.type.in_([EventType(t) for t in event_types]),
            db.or_(
                Event.districts.contains(district),
                Event.school.in_([school.id for school in schools]),
                *district_partner_conditions
            )
        ).distinct().all()
        
        event_ids = [event.id for event in events]
        
        # Get filtered volunteers
        filtered_volunteer_ids = set()
        volunteer_participations = EventParticipation.query.filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).all()
        
        for participation in volunteer_participations:
            filtered_volunteer_ids.add(participation.volunteer_id)
        
        # Get filtered students (excluding virtual sessions)
        filtered_student_ids = set()
        non_virtual_event_ids = [e.id for e in events if e.type != EventType.VIRTUAL_SESSION]
        
        if non_virtual_event_ids:
            student_participations = EventStudentParticipation.query.join(
                Student, EventStudentParticipation.student_id == Student.id
            ).join(
                School, Student.school_id == School.id
            ).filter(
                EventStudentParticipation.event_id.in_(non_virtual_event_ids),
                EventStudentParticipation.status == 'Attended',
                School.district_id == district.id
            ).all()
            
            for participation in student_participations:
                filtered_student_ids.add(participation.student_id)
        
        return jsonify({
            'volunteer_ids': list(filtered_volunteer_ids),
            'student_ids': list(filtered_student_ids),
            'event_ids': event_ids
        })

    @bp.route('/reports/district/engagement/full-breakdown/<district_name>')
    @login_required
    def district_engagement_full_breakdown(district_name):
        """Show comprehensive full breakdown report for a specific district organized by event"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Try to get cached breakdown data first
        cached_report = DistrictEngagementReport.query.filter_by(
            district_id=district.id,
            school_year=school_year
        ).first()
        
        if cached_report and cached_report.breakdown_data:
            # Use cached breakdown data
            breakdown_data = cached_report.breakdown_data
        else:
            # Generate event-centric breakdown data
            breakdown_data = generate_event_breakdown_data(district, school_year)
            
            # Cache the breakdown data
            if not cached_report:
                cached_report = DistrictEngagementReport(
                    district_id=district.id,
                    school_year=school_year,
                    summary_stats={}  # Will be filled later if needed
                )
                db.session.add(cached_report)
            
            cached_report.breakdown_data = breakdown_data
            cached_report.last_updated = datetime.utcnow()
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Log error but continue with generated data
                print(f"Error caching breakdown data: {e}")
        
        return render_template(
            'reports/district_engagement_full_breakdown.html',
            district=district,
            school_year=school_year,
            **breakdown_data
        )

    @bp.route('/reports/district/engagement/full-breakdown/<district_name>/excel')
    @login_required
    def district_engagement_full_breakdown_excel(district_name):
        """Generate Excel file for district engagement full breakdown report"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Try to get cached breakdown data first
        cached_report = DistrictEngagementReport.query.filter_by(
            district_id=district.id,
            school_year=school_year
        ).first()
        
        if cached_report and cached_report.breakdown_data:
            # Use cached breakdown data
            breakdown_data = cached_report.breakdown_data
        else:
            # Generate event-centric breakdown data
            breakdown_data = generate_event_breakdown_data(district, school_year)
        
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
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#f0f0f0',
            'border': 1
        })
        
        # Events Overview Sheet
        events_data = []
        all_volunteers = []
        all_students = []
        
        for event in breakdown_data['events_breakdown']:
            events_data.append({
                'Date': event['date'],
                'Event Title': event['title'],
                'Type': event['type'],
                'Location': event['location'],
                'Volunteer Count': event['volunteer_count'],
                'Student Count': event['student_count'],
                'Volunteer Hours': event['total_volunteer_hours'],
                'Is Virtual': 'Yes' if event['is_virtual'] else 'No'
            })
            
            # Collect all volunteers
            for volunteer in event['volunteers']:
                volunteer_record = volunteer.copy()
                volunteer_record['Event Title'] = event['title']
                volunteer_record['Event Date'] = event['date']
                all_volunteers.append(volunteer_record)
            
            # Collect all students (if not virtual)
            if not event['is_virtual']:
                for student in event['students']:
                    student_record = student.copy()
                    student_record['Event Title'] = event['title']
                    student_record['Event Date'] = event['date']
                    all_students.append(student_record)
        
        # Events Overview Sheet
        if events_data:
            events_df = pd.DataFrame(events_data)
            events_df.to_excel(writer, sheet_name='Events Overview', index=False)
            
            # Format events sheet
            worksheet = writer.sheets['Events Overview']
            worksheet.set_column('A:A', 15)  # Date
            worksheet.set_column('B:B', 40)  # Event Title
            worksheet.set_column('C:C', 20)  # Type
            worksheet.set_column('D:D', 30)  # Location
            worksheet.set_column('E:H', 12)  # Counts and Hours
            worksheet.conditional_format('A1:H1', {'type': 'no_blanks', 'format': header_format})
        
        # All Volunteers Sheet
        if all_volunteers:
            volunteers_data = []
            for volunteer in all_volunteers:
                skills_str = ', '.join(volunteer.get('skills', []))
                volunteers_data.append({
                    'Event Date': volunteer['Event Date'],
                    'Event Title': volunteer['Event Title'],
                    'Volunteer Name': f"{volunteer['first_name']} {volunteer['last_name']}",
                    'Email': volunteer['email'],
                    'Organization': volunteer['organization'],
                    'Hours': volunteer['hours'],
                    'Skills': skills_str
                })
            
            volunteers_df = pd.DataFrame(volunteers_data)
            volunteers_df.to_excel(writer, sheet_name='All Volunteers', index=False)
            
            # Format volunteers sheet
            worksheet = writer.sheets['All Volunteers']
            worksheet.set_column('A:A', 15)  # Event Date
            worksheet.set_column('B:B', 40)  # Event Title
            worksheet.set_column('C:C', 25)  # Volunteer Name
            worksheet.set_column('D:D', 30)  # Email
            worksheet.set_column('E:E', 25)  # Organization
            worksheet.set_column('F:F', 10)  # Hours
            worksheet.set_column('G:G', 50)  # Skills
            worksheet.conditional_format('A1:G1', {'type': 'no_blanks', 'format': header_format})
        
        # All Students Sheet
        if all_students:
            students_data = []
            for student in all_students:
                students_data.append({
                    'Event Date': student['Event Date'],
                    'Event Title': student['Event Title'],
                    'Student Name': f"{student['first_name']} {student['last_name']}",
                    'Email': student['email'],
                    'School': student['school'],
                    'Grade': student['grade']
                })
            
            students_df = pd.DataFrame(students_data)
            students_df.to_excel(writer, sheet_name='All Students', index=False)
            
            # Format students sheet
            worksheet = writer.sheets['All Students']
            worksheet.set_column('A:A', 15)  # Event Date
            worksheet.set_column('B:B', 40)  # Event Title
            worksheet.set_column('C:C', 25)  # Student Name
            worksheet.set_column('D:D', 30)  # Email
            worksheet.set_column('E:E', 25)  # School
            worksheet.set_column('F:F', 10)  # Grade
            worksheet.conditional_format('A1:F1', {'type': 'no_blanks', 'format': header_format})
        
        # Individual Event Sheets (limit to first 20 events to avoid too many sheets)
        for i, event in enumerate(breakdown_data['events_breakdown'][:20]):
            sheet_name = f"Event_{i+1}_{event['date'][:5]}"  # Sheet name with event number and month/day
            
            # Create event info at the top
            event_info = pd.DataFrame([
                ['Event Title', event['title']],
                ['Date', event['date']],
                ['Type', event['type']],
                ['Location', event['location']],
                ['Volunteer Count', event['volunteer_count']],
                ['Student Count', event['student_count']],
                ['Volunteer Hours', event['total_volunteer_hours']],
                ['', ''],  # Empty row
                ['VOLUNTEERS', ''],
            ])
            
            startrow = 0
            event_info.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=startrow)
            startrow += len(event_info) + 1
            
            # Add volunteers for this event
            if event['volunteers']:
                event_volunteers_data = []
                for volunteer in event['volunteers']:
                    skills_str = ', '.join(volunteer.get('skills', []))
                    event_volunteers_data.append({
                        'Name': f"{volunteer['first_name']} {volunteer['last_name']}",
                        'Email': volunteer['email'],
                        'Organization': volunteer['organization'],
                        'Hours': volunteer['hours'],
                        'Skills': skills_str
                    })
                
                volunteers_df = pd.DataFrame(event_volunteers_data)
                volunteers_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=startrow)
                startrow += len(volunteers_df) + 3
            
            # Add students for this event (if not virtual)
            if not event['is_virtual'] and event['students']:
                # Add students header
                students_header = pd.DataFrame([['STUDENTS', '', '', '', '']])
                students_header.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=startrow)
                startrow += 2
                
                event_students_data = []
                for student in event['students']:
                    event_students_data.append({
                        'Name': f"{student['first_name']} {student['last_name']}",
                        'Email': student['email'],
                        'School': student['school'],
                        'Grade': student['grade']
                    })
                
                students_df = pd.DataFrame(event_students_data)
                students_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=startrow)
            elif event['is_virtual']:
                # Add virtual note
                virtual_note = pd.DataFrame([['STUDENTS', ''], [event['students'][0]['note'], '']])
                virtual_note.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=startrow)
            
            # Format the individual event sheet
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:E', 20)
        
        writer.close()
        output.seek(0)
        
        # Create filename
        filename = f"{district_name.replace(' ', '_')}_{school_year}_Full_Breakdown.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=filename,
            as_attachment=True
        )

def is_cache_complete(cached_report):
    """Check if the cached report has all necessary data"""
    return (cached_report and 
            cached_report.summary_stats and 
            cached_report.volunteers_data is not None and 
            cached_report.students_data is not None and 
            cached_report.events_data is not None)

def cache_district_engagement_stats_with_details(school_year, district_stats):
    """Cache district engagement stats and generate detailed data for all districts"""
    for district_name, stats in district_stats.items():
        district = District.query.filter_by(name=district_name).first()
        if not district:
            continue

        # Get or create report
        report = DistrictEngagementReport.query.filter_by(
            district_id=district.id,
            school_year=school_year
        ).first()
        
        if not report:
            report = DistrictEngagementReport(
                district_id=district.id,
                school_year=school_year
            )
            db.session.add(report)
        
        report.summary_stats = stats
        
        # Only generate detailed data if not already cached or if forced refresh
        if not is_cache_complete(report):
            try:
                # Generate detailed engagement data
                detailed_data = generate_detailed_engagement_data(district, school_year)
                
                report.volunteers_data = detailed_data['volunteers']
                report.students_data = detailed_data['students']
                report.events_data = detailed_data['events']
                
                # Also generate and cache breakdown data
                breakdown_data = generate_event_breakdown_data(district, school_year)
                report.breakdown_data = breakdown_data
                
            except Exception as e:
                print(f"Error generating detailed data for {district_name}: {e}")
                # Set empty arrays if generation fails
                report.volunteers_data = []
                report.students_data = []
                report.events_data = []
                report.breakdown_data = {'events_breakdown': [], 'total_events': 0}
        
        report.last_updated = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error committing cache data: {e}")

def generate_district_engagement_stats(school_year):
    """Generate engagement statistics for all districts"""
    district_stats = {}
    start_date, end_date = get_school_year_date_range(school_year)
    
    # Only exclude connector sessions
    excluded_event_types = ['connector_session']
    
    # Get all districts from the database
    all_districts = District.query.order_by(District.name).all()
    
    # Process each district in our mapping
    for salesforce_id, mapping in DISTRICT_MAPPING.items():
        if not mapping['show']:
            continue
            
        # Find the primary district record
        primary_district = next((d for d in all_districts if d.salesforce_id == salesforce_id), None)
        if not primary_district:
            continue
            
        # Get all schools for this district
        schools = School.query.filter_by(district_id=primary_district.id).all()
        
        # Build the query conditions for this district
        district_partner_conditions = [
            Event.district_partner.ilike(f"%{school.name}%") for school in schools
        ]
        district_partner_conditions.append(Event.district_partner.ilike(f"%{primary_district.name}%"))

        # Add conditions for aliases
        if 'aliases' in mapping:
            for alias in mapping['aliases']:
                district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
                district_partner_conditions.append(
                    Event.districts.any(District.name.ilike(f"%{alias}%"))
                )

        # Get events for this district
        events = Event.query.filter(
            Event.start_date >= start_date,
            Event.start_date <= end_date,
            Event.status == EventStatus.COMPLETED,
            ~Event.type.in_([EventType(t) for t in excluded_event_types]),
            db.or_(
                Event.districts.contains(primary_district),
                Event.school.in_([school.id for school in schools]),
                *district_partner_conditions
            )
        ).distinct().all()
        
        event_ids = [event.id for event in events]
        
        # Get unique volunteers for these events
        unique_volunteers = db.session.query(distinct(EventParticipation.volunteer_id)).filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).count()
        
        # Get total volunteer engagements
        total_volunteer_engagements = EventParticipation.query.filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).count()
        
        # Get total volunteer hours
        total_volunteer_hours = db.session.query(func.sum(EventParticipation.delivery_hours)).filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).scalar() or 0
        
        # Get unique students for these events (excluding virtual sessions)
        non_virtual_event_ids = [e.id for e in events if e.type != EventType.VIRTUAL_SESSION]
        unique_students = 0
        total_student_participations = 0
        
        if non_virtual_event_ids:
            unique_students = db.session.query(distinct(EventStudentParticipation.student_id)).join(
                Student, EventStudentParticipation.student_id == Student.id
            ).join(
                School, Student.school_id == School.id
            ).filter(
                EventStudentParticipation.event_id.in_(non_virtual_event_ids),
                EventStudentParticipation.status == 'Attended',
                School.district_id == primary_district.id
            ).count()
            
            total_student_participations = EventStudentParticipation.query.join(
                Student, EventStudentParticipation.student_id == Student.id
            ).join(
                School, Student.school_id == School.id
            ).filter(
                EventStudentParticipation.event_id.in_(non_virtual_event_ids),
                EventStudentParticipation.status == 'Attended',
                School.district_id == primary_district.id
            ).count()
        
        # Calculate total students including virtual estimates
        total_students = 0
        for event in events:
            total_students += get_district_student_count_for_event(event, primary_district.id)
        
        # Get unique organizations
        volunteer_ids = db.session.query(EventParticipation.volunteer_id).filter(
            EventParticipation.event_id.in_(event_ids),
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).distinct().all()
        
        unique_organizations = 0
        if volunteer_ids:
            volunteer_id_list = [v[0] for v in volunteer_ids]
            unique_organizations = db.session.query(distinct(VolunteerOrganization.organization_id)).filter(
                VolunteerOrganization.volunteer_id.in_(volunteer_id_list)
            ).count()
        
        # Get schools engaged
        schools_engaged = len(set([event.school for event in events if event.school]))
        
        stats = {
            'name': mapping['name'],
            'unique_volunteers': unique_volunteers,
            'total_volunteer_engagements': total_volunteer_engagements,
            'total_volunteer_hours': round(total_volunteer_hours, 1),
            'unique_students': unique_students,
            'total_student_participations': total_student_participations,
            'total_students_with_virtual': total_students,
            'unique_events': len(events),
            'unique_organizations': unique_organizations,
            'schools_engaged': schools_engaged
        }
        
        district_stats[mapping['name']] = stats
    
    return district_stats

def generate_detailed_engagement_data(district, school_year):
    """Generate detailed engagement data for a specific district"""
    start_date, end_date = get_school_year_date_range(school_year)
    excluded_event_types = ['connector_session']
    
    # Get district mapping
    district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                            if mapping['name'] == district.name), None)
    
    # Get all schools for this district
    schools = School.query.filter_by(district_id=district.id).all()
    
    # Build query conditions
    district_partner_conditions = [
        Event.district_partner.ilike(f"%{school.name}%") for school in schools
    ]
    district_partner_conditions.append(Event.district_partner.ilike(f"%{district.name}%"))

    if district_mapping and 'aliases' in district_mapping:
        for alias in district_mapping['aliases']:
            district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
            district_partner_conditions.append(
                Event.districts.any(District.name.ilike(f"%{alias}%"))
            )

    # Get events for this district
    events = Event.query.filter(
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
        ~Event.type.in_([EventType(t) for t in excluded_event_types]),
        db.or_(
            Event.districts.contains(district),
            Event.school.in_([school.id for school in schools]),
            *district_partner_conditions
        )
    ).distinct().order_by(Event.start_date).all()
    
    event_ids = [event.id for event in events]
    
    # Get detailed volunteer data
    volunteers_data = []
    volunteer_participations = EventParticipation.query.filter(
        EventParticipation.event_id.in_(event_ids),
        EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
    ).all()
    
    # Group by volunteer
    volunteer_stats = {}
    for participation in volunteer_participations:
        vol_id = participation.volunteer_id
        if vol_id not in volunteer_stats:
            volunteer_stats[vol_id] = {
                'events': set(),
                'total_hours': 0
            }
        volunteer_stats[vol_id]['events'].add(participation.event_id)
        volunteer_stats[vol_id]['total_hours'] += participation.delivery_hours or 0
    
    # Get volunteer details
    for vol_id, stats in volunteer_stats.items():
        volunteer = Volunteer.query.get(vol_id)
        if volunteer:
            # Get organization
            org_relationship = VolunteerOrganization.query.filter_by(volunteer_id=vol_id).first()
            organization = Organization.query.get(org_relationship.organization_id).name if org_relationship else 'N/A'
            
            # Get skills
            skills = db.session.query(Skill.name).join(VolunteerSkill).filter(
                VolunteerSkill.volunteer_id == vol_id
            ).all()
            skill_names = [skill[0] for skill in skills]
            
            volunteers_data.append({
                'id': vol_id,
                'first_name': volunteer.first_name or '',
                'last_name': volunteer.last_name or '',
                'email': volunteer.primary_email or '',
                'organization': organization,
                'events_count': len(stats['events']),
                'total_hours': round(stats['total_hours'], 1),
                'skills': skill_names
            })
    
    # Sort volunteers by engagement (events count, then hours)
    volunteers_data.sort(key=lambda x: (-x['events_count'], -x['total_hours']))
    
    # Get detailed student data (excluding virtual sessions)
    students_data = []
    non_virtual_events = [e for e in events if e.type != EventType.VIRTUAL_SESSION]
    non_virtual_event_ids = [e.id for e in non_virtual_events]
    
    if non_virtual_event_ids:
        student_participations = EventStudentParticipation.query.join(
            Student, EventStudentParticipation.student_id == Student.id
        ).join(
            School, Student.school_id == School.id
        ).filter(
            EventStudentParticipation.event_id.in_(non_virtual_event_ids),
            EventStudentParticipation.status == 'Attended',
            School.district_id == district.id
        ).all()
        
        # Group by student
        student_stats = {}
        for participation in student_participations:
            student_id = participation.student_id
            if student_id not in student_stats:
                student_stats[student_id] = set()
            student_stats[student_id].add(participation.event_id)
        
        # Get student details
        for student_id, event_set in student_stats.items():
            student = Student.query.get(student_id)
            if student:
                school = School.query.get(student.school_id)
                students_data.append({
                    'id': student_id,
                    'first_name': student.first_name or '',
                    'last_name': student.last_name or '',
                    'email': student.primary_email or '',
                    'school': school.name if school else 'N/A',
                    'grade': student.current_grade or 'N/A',
                    'events_count': len(event_set)
                })
        
        # Sort students by engagement
        students_data.sort(key=lambda x: (-x['events_count'], x['last_name']))
    
    # Get events data
    events_data = []
    for event in events:
        volunteer_count = len([p for p in event.volunteer_participations 
                              if p.status in ['Attended', 'Completed', 'Successfully Completed']])
        volunteer_hours = sum(p.delivery_hours or 0 for p in event.volunteer_participations 
                             if p.status in ['Attended', 'Completed', 'Successfully Completed'])
        student_count = get_district_student_count_for_event(event, district.id)
        
        events_data.append({
            'id': event.id,
            'date': event.start_date.strftime('%m/%d/%Y'),
            'title': event.title,
            'type': event.type.value if event.type else 'N/A',
            'location': event.location or 'N/A',
            'volunteer_count': volunteer_count,
            'student_count': student_count,
            'volunteer_hours': round(volunteer_hours, 1)
        })
    
    # Calculate summary stats
    summary_stats = {
        'unique_volunteers': len(volunteers_data),
        'total_volunteer_engagements': sum(v['events_count'] for v in volunteers_data),
        'total_volunteer_hours': sum(v['total_hours'] for v in volunteers_data),
        'unique_students': len(students_data),
        'total_student_participations': sum(s['events_count'] for s in students_data),
        'unique_events': len(events_data),
        'unique_organizations': len(set(v['organization'] for v in volunteers_data if v['organization'] != 'N/A')),
        'schools_engaged': len(set(s['school'] for s in students_data if s['school'] != 'N/A'))
    }
    
    # After getting events, add event type breakdown
    event_type_breakdown = {}
    for event in events:
        event_type = event.type.value if event.type else 'Unknown'
        event_type_breakdown[event_type] = event_type_breakdown.get(event_type, 0) + 1
    
    return {
        'summary_stats': summary_stats,
        'volunteers': volunteers_data,
        'students': students_data,
        'events': events_data,
        'event_types': event_type_breakdown
    }

def generate_event_breakdown_data(district, school_year):
    """Generate event-centric breakdown data showing volunteers and students for each event"""
    start_date, end_date = get_school_year_date_range(school_year)
    excluded_event_types = ['connector_session']
    
    # Get district mapping
    district_mapping = next((mapping for salesforce_id, mapping in DISTRICT_MAPPING.items() 
                            if mapping['name'] == district.name), None)
    
    # Get all schools for this district
    schools = School.query.filter_by(district_id=district.id).all()
    
    # Build query conditions
    district_partner_conditions = [
        Event.district_partner.ilike(f"%{school.name}%") for school in schools
    ]
    district_partner_conditions.append(Event.district_partner.ilike(f"%{district.name}%"))

    if district_mapping and 'aliases' in district_mapping:
        for alias in district_mapping['aliases']:
            district_partner_conditions.append(Event.district_partner.ilike(f"%{alias}%"))
            district_partner_conditions.append(
                Event.districts.any(District.name.ilike(f"%{alias}%"))
            )

    # Get events for this district
    events = Event.query.filter(
        Event.start_date >= start_date,
        Event.start_date <= end_date,
        Event.status == EventStatus.COMPLETED,
        ~Event.type.in_([EventType(t) for t in excluded_event_types]),
        db.or_(
            Event.districts.contains(district),
            Event.school.in_([school.id for school in schools]),
            *district_partner_conditions
        )
    ).distinct().order_by(Event.start_date.desc()).all()
    
    # Generate event-centric data
    events_breakdown = []
    
    for event in events:
        # Get volunteers for this event
        volunteer_participations = EventParticipation.query.filter(
            EventParticipation.event_id == event.id,
            EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
        ).all()
        
        event_volunteers = []
        total_volunteer_hours = 0
        
        for participation in volunteer_participations:
            volunteer = Volunteer.query.get(participation.volunteer_id)
            if volunteer:
                # Get organization
                org_relationship = VolunteerOrganization.query.filter_by(volunteer_id=volunteer.id).first()
                organization = Organization.query.get(org_relationship.organization_id).name if org_relationship else 'N/A'
                
                # Get skills
                skills = db.session.query(Skill.name).join(VolunteerSkill).filter(
                    VolunteerSkill.volunteer_id == volunteer.id
                ).all()
                skill_names = [skill[0] for skill in skills]
                
                hours = participation.delivery_hours or 0
                total_volunteer_hours += hours
                
                event_volunteers.append({
                    'id': volunteer.id,
                    'first_name': volunteer.first_name or '',
                    'last_name': volunteer.last_name or '',
                    'email': volunteer.primary_email or '',
                    'organization': organization,
                    'hours': round(hours, 1),
                    'skills': skill_names
                })
        
        # Sort volunteers by hours (descending), then by last name
        event_volunteers.sort(key=lambda x: (-x['hours'], x['last_name']))
        
        # Get students for this event (excluding virtual sessions for detailed attendance)
        event_students = []
        if event.type != EventType.VIRTUAL_SESSION:
            student_participations = EventStudentParticipation.query.join(
                Student, EventStudentParticipation.student_id == Student.id
            ).join(
                School, Student.school_id == School.id
            ).filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status == 'Attended',
                School.district_id == district.id
            ).all()
            
            for participation in student_participations:
                student = Student.query.get(participation.student_id)
                if student:
                    school = School.query.get(student.school_id)
                    event_students.append({
                        'id': student.id,
                        'first_name': student.first_name or '',
                        'last_name': student.last_name or '',
                        'email': student.primary_email or '',
                        'school': school.name if school else 'N/A',
                        'grade': student.current_grade or 'N/A'
                    })
            
            # Sort students by school, then by grade, then by last name
            event_students.sort(key=lambda x: (x['school'], str(x['grade']), x['last_name']))
        else:
            # For virtual sessions, use estimated count
            estimated_students = get_district_student_count_for_event(event, district.id)
            event_students = [{
                'note': f'Virtual session - estimated {estimated_students} students participated'
            }]
        
        events_breakdown.append({
            'id': event.id,
            'date': event.start_date.strftime('%B %d, %Y'),
            'title': event.title,
            'type': event.type.value if event.type else 'N/A',
            'location': event.location or 'N/A',
            'volunteers': event_volunteers,
            'students': event_students,
            'volunteer_count': len(event_volunteers),
            'student_count': len(event_students) if event.type != EventType.VIRTUAL_SESSION else estimated_students,
            'total_volunteer_hours': round(total_volunteer_hours, 1),
            'is_virtual': event.type == EventType.VIRTUAL_SESSION
        })
    
    return {
        'events_breakdown': events_breakdown,
        'total_events': len(events_breakdown)
    } 