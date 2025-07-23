# Attendance management routes for VMS (Volunteer Management System)
# This module handles all attendance-related functionality including:
# - Viewing student and teacher lists with pagination
# - Importing data from Salesforce
# - Managing event attendance details
# - Data purging operations

from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import login_required, current_user
import pandas as pd
import os
from models import db
from models.student import Student
from models.teacher import Teacher, TeacherStatus
from models.contact import Email, Phone, GenderEnum, RaceEthnicityEnum
from models.class_model import Class
from models.school_model import School
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from config import Config
from routes.utils import parse_date
from models.event import Event, EventType, EventTeacher
from models.attendance import EventAttendanceDetail
from datetime import datetime, date, timedelta
from sqlalchemy import func

# Create Blueprint for attendance routes
attendance = Blueprint('attendance', __name__)

@attendance.route('/attendance')
@login_required
def view_attendance():
    """
    Main attendance management page showing paginated lists of students and teachers.
    
    Returns:
        Rendered template with paginated student and teacher data
    """
    # Get pagination parameters from request
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query students with pagination
    students = Student.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Query teachers with pagination - include teachers who participate in events
    teachers_query = db.session.query(Teacher).distinct()
    
    # Add teachers who participate in events (including virtual sessions)
    teachers_with_events = db.session.query(Teacher).join(EventTeacher).distinct()
    
    # Combine both queries and remove duplicates
    all_teachers = teachers_query.union(teachers_with_events).order_by(Teacher.last_name, Teacher.first_name)
    
    # Apply pagination manually since union doesn't work well with paginate
    total_teachers = all_teachers.count()
    offset = (page - 1) * per_page
    teachers_list = all_teachers.offset(offset).limit(per_page).all()
    
    # Create a pagination-like object
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if page > 1 else None
            self.next_num = page + 1 if page < self.pages else None
            
        def iter_pages(self, left_edge=2, left_current=2, right_current=2, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if (num <= left_edge or 
                    (num > self.page - left_current - 1 and num < self.page + right_current) or 
                    num > self.pages - right_edge):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    
    teachers = Pagination(teachers_list, page, per_page, total_teachers)
    
    # Calculate total counts for pagination info
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    
    return render_template(
        'attendance/attendance.html',
        students=students,
        teachers=teachers,
        current_page=page,
        per_page=per_page,
        total_students=total_students,
        total_teachers=total_teachers,
        per_page_options=[10, 25, 50, 100]
    )

def map_racial_ethnic_value(value):
    """
    Clean and standardize racial/ethnic values from Salesforce.
    
    Args:
        value: Raw racial/ethnic value from Salesforce
        
    Returns:
        Cleaned and standardized value or None if empty
    """
    if not value:
        return None
        
    # Clean the input by stripping whitespace
    value = value.strip()
    
    # Return the cleaned value directly
    return value

@attendance.route('/attendance/purge', methods=['POST'])
@login_required
def purge_attendance():
    """
    Purge attendance data (students, teachers, or all).
    
    This is a destructive operation that permanently deletes data.
    Use with extreme caution.
    
    Returns:
        JSON response with success/error status
    """
    try:
        # Get the type from request, default to 'all'
        purge_type = request.json.get('type', 'all')
        
        # Purge students if requested
        if purge_type == 'students' or purge_type == 'all':
            Student.query.delete()
            db.session.commit()
            
        # Purge teachers if requested
        if purge_type == 'teachers' or purge_type == 'all':
            Teacher.query.delete()
            db.session.commit()
            
        return jsonify({
            'status': 'success', 
            'message': f'Successfully purged {purge_type} data'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@attendance.route('/attendance/toggle-teacher-exclude-reports/<int:id>', methods=['POST'])
@login_required
def toggle_teacher_exclude_reports(id):
    """Toggle the exclude_from_reports field for a teacher - Admin only"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
    try:
        teacher = db.session.get(Teacher, id)
        if not teacher:
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        # Get the new value from the request
        data = request.get_json()
        exclude_from_reports = data.get('exclude_from_reports', False)
        
        # Update the field
        teacher.exclude_from_reports = exclude_from_reports
        db.session.commit()
        
        status = 'excluded' if exclude_from_reports else 'included'
        return jsonify({
            'success': True, 
            'message': f'Teacher {status} from reports successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance.route('/attendance/view/<type>/<int:id>')
@login_required
def view_details(type, id):
    """
    View detailed information for a specific student or teacher.
    
    Args:
        type: 'student' or 'teacher'
        id: Database ID of the contact
        
    Returns:
        Rendered template with detailed contact information
    """
    try:
        # Query the appropriate model based on type
        if type == 'student':
            contact = Student.query.get_or_404(id)
        elif type == 'teacher':
            contact = Teacher.query.get_or_404(id)
        else:
            return jsonify({'status': 'error', 'message': 'Invalid type'})
        
        # Get related contact information
        primary_email = contact.emails.filter_by(primary=True).first()
        primary_phone = contact.phones.filter_by(primary=True).first()
        primary_address = contact.addresses.filter_by(primary=True).first()
        
        return render_template(
            'attendance/view_details.html',
            contact=contact,
            type=type,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address
        )
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# Teacher and student import functionality has been moved to dedicated route files:
# - Teacher imports: routes/teachers/routes.py
# - Student imports: routes/students/routes.py

def get_academic_year_range(today=None):
    """
    Calculate academic year start and end dates.
    
    Academic year runs from August 1 to July 31 of the following year.
    
    Args:
        today: Date to calculate from (defaults to current date)
        
    Returns:
        Tuple of (start_date, end_date) for the academic year
    """
    today = today or date.today()
    year = today.year
    if today.month < 8:
        start = date(year-1, 8, 1)
        end = date(year, 7, 31)
    else:
        start = date(year, 8, 1)
        end = date(year+1, 7, 31)
    return start, end

@attendance.route('/attendance/details')
@login_required
def attendance_details():
    """
    Display event attendance details for a specific academic year.
    
    This page shows detailed attendance information for events including
    classroom counts, student-volunteer ratios, and pathway information.
    
    Returns:
        Rendered template with event attendance data
    """
    year_param = request.args.get('year', type=int)
    today = date.today()
    current_year = today.year if today.month >= 8 else today.year - 1
    academic_years = [current_year - i for i in range(5)]
    academic_years.sort(reverse=True)
    selected_year = year_param or current_year
    start = date(selected_year, 8, 1)
    end = date(selected_year + 1, 7, 31)
    
    # Query events for the selected academic year
    events = Event.query.filter(Event.start_date >= start, Event.start_date <= end).order_by(Event.start_date).all()
    
    # Get unique event types for this year, as value/label dicts
    event_types = (
        db.session.query(Event.type)
        .filter(Event.start_date >= start, Event.start_date <= end)
        .distinct()
        .all()
    )
    event_types = [et[0] for et in event_types if et[0]]
    event_types = [
        {'value': et.value, 'label': et.value.replace('_', ' ').title()} for et in event_types
    ]
    event_types = sorted(event_types, key=lambda x: x['label'])
    
    return render_template('attendance/details.html', 
                         events=events, 
                         academic_years=academic_years, 
                         selected_year=selected_year, 
                         event_types=event_types)

@attendance.route('/attendance/details/events_json')
@login_required
def attendance_details_events_json():
    """
    AJAX endpoint for filtered event data.
    
    Returns JSON data for events filtered by year and event types.
    Used by the frontend for dynamic filtering without page reload.
    
    Returns:
        JSON array of event data with attendance details
    """
    year = request.args.get('year', type=int)
    types = request.args.getlist('types[]')
    start = date(year, 8, 1)
    end = date(year + 1, 7, 31)
    
    # Build query with filters
    q = Event.query.filter(Event.start_date >= start, Event.start_date <= end)
    if types:
        # Convert string values to Enum
        enum_types = [EventType(t) for t in types if t in EventType.__members__.values() or t in [e.value for e in EventType]]
        q = q.filter(Event.type.in_(enum_types))
    events = q.order_by(Event.start_date).all()
    
    def event_to_dict(event):
        """Convert event object to dictionary for JSON serialization."""
        d = {
            'id': event.id,
            'title': event.title,
            'start_date': event.start_date.strftime('%Y-%m-%d') if event.start_date else '',
            'type': event.type.value if event.type else '',
            'attendance_detail': None
        }
        if event.attendance_detail:
            ad = event.attendance_detail
            d['attendance_detail'] = {
                'num_classrooms': ad.num_classrooms,
                'rotations': ad.rotations,
                'students_per_volunteer': ad.students_per_volunteer,
                'total_students': ad.total_students,
                'attendance_in_sf': ad.attendance_in_sf,
                'pathway': ad.pathway,
                'groups_rotations': ad.groups_rotations,
                'is_stem': ad.is_stem,
                'attendance_link': ad.attendance_link
            }
        return d
    
    return jsonify([event_to_dict(e) for e in events])

@attendance.route('/attendance/details/<int:event_id>/detail', methods=['GET'])
@login_required
def get_attendance_detail(event_id):
    """
    Get attendance detail for a specific event.
    
    Args:
        event_id: Database ID of the event
        
    Returns:
        JSON object with attendance detail data or default values
    """
    event = Event.query.get_or_404(event_id)
    detail = event.attendance_detail
    if not detail:
        # Return empty/default values if not set
        return jsonify({
            'num_classrooms': '',
            'rotations': '',
            'students_per_volunteer': '',
            'total_students': '',
            'attendance_in_sf': False,
            'pathway': '',
            'groups_rotations': '',
            'is_stem': False,
            'attendance_link': ''
        })
    return jsonify({
        'num_classrooms': detail.num_classrooms,
        'rotations': detail.rotations,
        'students_per_volunteer': detail.students_per_volunteer,
        'total_students': detail.total_students,
        'attendance_in_sf': detail.attendance_in_sf,
        'pathway': detail.pathway,
        'groups_rotations': detail.groups_rotations,
        'is_stem': detail.is_stem,
        'attendance_link': detail.attendance_link
    })

@attendance.route('/attendance/details/<int:event_id>/detail', methods=['POST'])
@login_required
def update_attendance_detail(event_id):
    """
    Update attendance detail for a specific event.
    
    Args:
        event_id: Database ID of the event
        
    Returns:
        JSON response indicating success
    """
    event = Event.query.get_or_404(event_id)
    data = request.json
    detail = event.attendance_detail
    if not detail:
        detail = EventAttendanceDetail(event_id=event.id)
        db.session.add(detail)
    
    # Convert string values to integers for numeric fields
    total_students = data.get('total_students')
    num_classrooms = data.get('num_classrooms')
    rotations = data.get('rotations')
    
    # Convert to integers if they're not empty
    if total_students:
        try:
            total_students = int(total_students)
        except (ValueError, TypeError):
            total_students = None
    
    if num_classrooms:
        try:
            num_classrooms = int(num_classrooms)
        except (ValueError, TypeError):
            num_classrooms = None
                
    if rotations:
        try:
            rotations = int(rotations)
        except (ValueError, TypeError):
            rotations = None
    
    # Update attendance detail fields
    detail.num_classrooms = num_classrooms
    detail.rotations = rotations
    detail.total_students = total_students
    detail.attendance_in_sf = data.get('attendance_in_sf', False)
    detail.pathway = data.get('pathway')
    detail.groups_rotations = data.get('groups_rotations')
    detail.is_stem = data.get('is_stem', False)
    detail.attendance_link = data.get('attendance_link')
    
    # Calculate students per volunteer if we have the required data
    if detail.total_students and detail.num_classrooms and detail.rotations:
        if detail.num_classrooms > 0 and detail.rotations > 0:
            detail.students_per_volunteer = detail.calculate_students_per_volunteer()
    
    db.session.commit()
    return jsonify({'success': True})