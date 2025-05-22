from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from models.event import Event, EventAttendance, EventType, EventStatus, EventStudentParticipation
from models.volunteer import EventParticipation
from models.district_model import District
from models import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_

# Create blueprint
attendance_bp = Blueprint('reports_attendance', __name__)

def get_school_year_dates(school_year):
    """Convert school year (e.g., '24-25') to start and end dates"""
    start_year = int(school_year.split('-')[0])
    end_year = int(school_year.split('-')[1])
    
    # Convert to full years
    start_year = 2000 + start_year
    end_year = 2000 + end_year
    
    # School year starts June 1st
    start_date = datetime(start_year, 6, 1)
    end_date = datetime(end_year, 5, 31)
    
    return start_date, end_date

def load_routes(bp):
    @bp.route('/reports/attendance')
    @login_required
    def attendance_report():
        # Get all districts for the dropdown
        districts = District.query.order_by(District.name).all()
        
        # Get current school year
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # If we're past June, use current year as start, otherwise use previous year
        if current_month >= 6:
            school_year = f"{str(current_year)[-2:]}-{str(current_year + 1)[-2:]}"
        else:
            school_year = f"{str(current_year - 1)[-2:]}-{str(current_year)[-2:]}"
            
        return render_template('reports/attendance_report.html', 
                             districts=districts,
                             current_school_year=school_year)

    @bp.route('/reports/attendance/data')
    @login_required
    def get_attendance_data():
        district_id = request.args.get('district_id')
        school_year = request.args.get('school_year', '24-25')  # Default to 2024-2025
        
        # Get date range for school year
        start_date, end_date = get_school_year_dates(school_year)
            
        # Base query for events
        query = Event.query.filter(
            Event.status == EventStatus.COMPLETED,
            Event.start_date >= start_date,
            Event.start_date <= end_date
        )
        
        # Apply district filter if provided
        if district_id:
            district = District.query.get(district_id)
            if district:
                query = query.filter(Event.districts.contains(district))
            
        # Get all matching events
        events = query.all()
        
        # Prepare the response data
        event_data = []
        total_volunteers = 0
        total_students = 0
        total_events = len(events)
        
        for event in events:
            # Get volunteer participation
            volunteer_participations = EventParticipation.query.filter(
                EventParticipation.event_id == event.id,
                EventParticipation.status.in_(['Attended', 'Completed', 'Successfully Completed'])
            ).all()
            
            # Get student participation
            student_participations = EventStudentParticipation.query.filter(
                EventStudentParticipation.event_id == event.id,
                EventStudentParticipation.status == 'Attended'
            ).all()
            
            # Calculate attendance metrics
            volunteer_count = len(volunteer_participations)
            student_count = len(student_participations)
            
            # Get district names
            district_names = [d.name for d in event.districts]
            
            event_data.append({
                'date': event.start_date.strftime('%Y-%m-%d'),
                'name': event.title,
                'district': ', '.join(district_names),
                'volunteers': volunteer_count,
                'students': student_count
            })
            
            total_volunteers += volunteer_count
            total_students += student_count
        
        return jsonify({
            'events': event_data,
            'summary': {
                'total_events': total_events,
                'total_volunteers': total_volunteers,
                'total_students': total_students
            }
        })
