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
from models.reports import DistrictYearEndReport
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
        
        # Generate engagement stats for all districts
        district_stats = generate_district_engagement_stats(school_year)
        
        # Generate list of school years (from 2020-21 to current+1)
        current_year = int(get_current_school_year()[:2])
        school_years = [f"{y}{y+1}" for y in range(20, current_year + 2)]
        school_years.reverse()  # Most recent first
        
        return render_template(
            'reports/district_engagement.html',
            districts=district_stats,
            school_year=school_year,
            school_years=school_years,
            now=datetime.now()
        )

    @bp.route('/reports/district/engagement/detail/<district_name>')
    @login_required
    def district_engagement_detail(district_name):
        """Show detailed engagement report for a specific district"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Generate detailed engagement data
        engagement_data = generate_detailed_engagement_data(district, school_year)
        
        return render_template(
            'reports/district_engagement_detail.html',
            district=district,
            school_year=school_year,
            **engagement_data
        )

    @bp.route('/reports/district/engagement/<district_name>/excel')
    @login_required
    def district_engagement_excel(district_name):
        """Generate Excel file for district engagement report"""
        school_year = request.args.get('school_year', get_current_school_year())
        
        # Get district
        district = District.query.filter_by(name=district_name).first_or_404()
        
        # Generate detailed engagement data
        engagement_data = generate_detailed_engagement_data(district, school_year)
        
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
    
    return {
        'summary_stats': summary_stats,
        'volunteers': volunteers_data,
        'students': students_data,
        'events': events_data
    } 