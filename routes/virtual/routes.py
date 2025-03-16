import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime, timezone
from flask import current_app
from models.district_model import District
from models.event import db, Event, EventType, EventStatus
from models.organization import Organization, VolunteerOrganization
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import Volunteer, EventParticipation
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs
from os import getenv
from sqlalchemy import func
import re
from models.history import History
import hashlib
from models.contact import Contact
from models.event import EventTeacher
from models.contact import ContactTypeEnum

virtual_bp = Blueprint('virtual', __name__, url_prefix='/virtual')

@virtual_bp.route('/virtual')
def virtual():
    return render_template('virtual/virtual.html')

def process_csv_row(row, success_count, warning_count, error_count, errors):
    try:
        db.session.rollback()
        
        # Debug logging
        current_app.logger.debug(f"Processing row: {row}")
        
        # Skip empty rows
        if not any(row.values()):
            warning_count += 1
            errors.append(f"Row {success_count + warning_count + error_count}: Skipped - Empty row")
            return success_count, warning_count, error_count

        # Handle simulcast entries
        is_simulcast = row.get('Status', '').lower() == 'simulcast'
        
        # Extract session ID and find/create event
        session_id = None
        if row.get('Session Link'):
            try:
                session_id = row['Session Link'].split('/')[-1]
            except Exception as e:
                current_app.logger.error(f"Error extracting session ID: {e}")

        # Find existing event or create new one
        event = Event.query.filter_by(session_id=session_id).first() if session_id else None
        
        if not event:
            event = Event()
            event.session_id = session_id
            event.title = row.get('Session Title')
            event.type = EventType.VIRTUAL_SESSION
            event.status = EventStatus.map_status(row.get('Status', ''))
            event.topic = row.get('Topic/Theme')
            event.session_type = row.get('Session Type')
            event.session_link = row.get('Session Link')
            
            # Set date/time for new events
            if not is_simulcast and row.get('Date'):
                try:
                    date_str = row.get('Date')
                    time_str = row.get('Time', '')
                    date_parts = date_str.split('/')
                    current_year = datetime.now(timezone.utc).year
                    event.date = datetime.strptime(f"{date_parts[0]}/{date_parts[1]}/{current_year}", '%m/%d/%Y').date()
                    if time_str:
                        event.start_time = datetime.strptime(time_str, '%I:%M %p').time()
                except ValueError as e:
                    current_app.logger.error(f"Date/time parsing error: {e}")

        # Handle presenter information
        volunteer_id = None
        if row.get('Presenter'):
            presenter_name = row.get('Presenter').strip()
            name_parts = presenter_name.split(' ', 1)
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[1]
                
                # Find or create volunteer for presenter
                volunteer = Volunteer.query.filter(
                    func.lower(Volunteer.first_name) == func.lower(first_name),
                    func.lower(Volunteer.last_name) == func.lower(last_name)
                ).first()
                
                if not volunteer:
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        organization_name=row.get('Organization'),
                        contact_type=ContactTypeEnum.PRESENTER
                    )
                    db.session.add(volunteer)
                    db.session.flush()
                
                volunteer_id = volunteer.id
                
                # Create event participation record
                participation = EventParticipation(
                    volunteer_id=volunteer_id,
                    event_id=event.id,
                    participant_type='Presenter',
                    status='Confirmed',
                    title=row.get('Session Title')
                )
                db.session.add(participation)

        # Handle teacher information
        if row.get('Teacher Name'):
            teacher_name = row.get('Teacher Name').strip()
            name_parts = teacher_name.split(' ', 1)
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[1]
                
                # Find or create teacher
                teacher = Teacher.query.filter(
                    func.lower(Teacher.first_name) == func.lower(first_name),
                    func.lower(Teacher.last_name) == func.lower(last_name)
                ).first()
                
                if not teacher:
                    teacher = Teacher(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=''
                    )
                    
                    # Handle school association
                    school_name = row.get('School Name')
                    district_name = row.get('District')
                    if school_name:
                        school = get_or_create_school(school_name, get_or_create_district(district_name))
                        teacher.school_id = school.id
                    
                    db.session.add(teacher)
                    db.session.flush()

                # Create teacher participation record
                event_teacher = EventTeacher.query.filter_by(
                    event_id=event.id,
                    teacher_id=teacher.id
                ).first()
                
                if not event_teacher:
                    event_teacher = EventTeacher(
                        event_id=event.id,
                        teacher_id=teacher.id,
                        status=row.get('Status'),
                        is_simulcast=is_simulcast
                    )
                    db.session.add(event_teacher)

        # Set volunteer_id for history creation (only if we have a presenter)
        if volunteer_id:
            event._volunteer_id = volunteer_id

        # Add district association here
        district_name = row.get('District')  # Get district name from the CSV row
        if district_name:
            district = get_or_create_district(district_name)  # This function either finds existing district or creates new one
            event.district_partner = district_name  # Set the text field
            if district not in event.districts:  # Add to the relationship if not already there
                event.districts.append(district)

        db.session.add(event)
        db.session.commit()
        success_count += 1
        
    except Exception as e:
        error_count += 1
        errors.append(f"Error processing row: {str(e)}")
        db.session.rollback()
        current_app.logger.error(f"Import error: {e}", exc_info=True)
    
    return success_count, warning_count, error_count

@virtual_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_virtual():
    if request.method == 'GET':
        return render_template('virtual/import.html')
    
    try:
        success_count = warning_count = error_count = 0
        errors = []

        if 'file' in request.files:
            file = request.files['file']
            if not file.filename.endswith('.csv'):
                raise ValueError("Please upload a CSV file")
            
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_data = csv.DictReader(stream)
            
            for row in csv_data:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors
                )

        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Import failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/quick-sync', methods=['POST'])
@login_required
def quick_sync():
    """Synchronize virtual sessions from a predefined CSV file"""
    try:
        csv_path = os.path.join('data', 'virtual.csv')
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Virtual data file not found at {csv_path}")

        success_count = warning_count = error_count = 0
        errors = []

        with open(csv_path, 'r', encoding='UTF8') as file:
            csv_data = csv.DictReader(file)
            
            for row in csv_data:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors
                )

        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Quick sync failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/purge', methods=['POST'])
@login_required
def purge_virtual():
    """Remove all virtual session records"""
    try:
        # First delete all event-teacher associations
        EventTeacher.query.join(Event).filter(
            Event.type == EventType.VIRTUAL_SESSION
        ).delete(synchronize_session=False)
        
        # Then delete the events
        deleted_count = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).delete(synchronize_session=False)
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully purged {deleted_count} virtual sessions',
            'count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Purge failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/events', methods=['GET'])
@login_required
def list_events():
    """List all virtual events with their associated teachers and presenters"""
    try:
        events = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).order_by(Event.date.desc()).all()
        
        events_data = []
        for event in events:
            # Get all teacher participants
            teacher_data = [{
                'id': et.teacher_id,
                'name': f"{et.teacher.first_name} {et.teacher.last_name}",
                'school': et.teacher.school.name if et.teacher.school else None,
                'status': et.status,
                'is_simulcast': et.is_simulcast
            } for et in event.teacher_participants]
            
            events_data.append({
                'id': event.id,
                'title': event.title,
                'date': event.date.strftime('%Y-%m-%d') if event.date else None,
                'time': event.start_time.strftime('%I:%M %p') if event.start_time else None,
                'status': event.status,
                'session_type': event.session_type,
                'topic': event.topic,
                'session_link': event.session_link,
                'presenter_name': event.presenter_name,
                'presenter_organization': event.presenter_organization,
                'presenter_location_type': event.presenter_location_type,
                'teachers': teacher_data
            })
        
        return jsonify({
            'success': True,
            'events': events_data
        })
        
    except Exception as e:
        current_app.logger.error("Error fetching events", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/event/<int:event_id>', methods=['GET'])
@login_required
def get_event(event_id):
    """Get detailed information about a specific virtual event"""
    try:
        event = Event.query.filter_by(
            id=event_id,
            type=EventType.VIRTUAL_SESSION
        ).first_or_404()
        
        # Get teacher participation details
        teacher_data = [{
            'id': et.teacher_id,
            'name': f"{et.teacher.first_name} {et.teacher.last_name}",
            'school': et.teacher.school.name if et.teacher.school else None,
            'status': et.status,
            'is_simulcast': et.is_simulcast
        } for et in event.teacher_participants]
        
        return jsonify({
            'success': True,
            'event': {
                'id': event.id,
                'title': event.title,
                'date': event.date.strftime('%Y-%m-%d') if event.date else None,
                'time': event.start_time.strftime('%I:%M %p') if event.start_time else None,
                'status': event.status,
                'session_type': event.session_type,
                'topic': event.topic,
                'session_link': event.session_link,
                'presenter_name': event.presenter_name,
                'presenter_organization': event.presenter_organization,
                'presenter_location_type': event.presenter_location_type,
                'teachers': teacher_data
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching event {event_id}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def clean_name(name):
    """Enhanced name cleaning function"""
    if not name:
        return '', ''
    
    # Split name into parts
    parts = name.strip().split()
    
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return parts[0], ''
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        # For names with more than 2 parts, treat first part as first name
        # and remaining parts as last name
        return parts[0], ' '.join(parts[1:])

def standardize_organization(org_name):
    """Standardize organization names"""
    if not org_name or pd.isna(org_name):
        return None
    
    org_name = str(org_name).strip()
    # Add common replacements
    replacements = {
        "IBM CORPORATION": "IBM",
        "HILL'S PET NUTRITION INC": "Hill's Pet Nutrition",
        # Add more as needed
    }
    return replacements.get(org_name.upper(), org_name)

def parse_datetime(date_str, time_str):
    """Parse date and time strings into datetime object"""
    try:
        if pd.isna(date_str) or pd.isna(time_str):
            return None
            
        # Convert to string if numeric
        if isinstance(date_str, (int, float)):
            date_str = str(int(date_str))
        if isinstance(time_str, (int, float)):
            time_str = str(int(time_str))
            
        # Parse date
        date_parts = date_str.split('/')
        
        if len(date_parts) == 2:
            month, day = map(int, date_parts)
            # Simplified year logic:
            # Months 1-6 -> 2025
            # Months 7-12 -> 2024
            year = 2024 if month >= 7 else 2025
        elif len(date_parts) == 3:
            month, day, year = map(int, date_parts)
            if year < 100:
                year += 2000
        else:
            return None
            
        # Parse time
        time_str = time_str.strip().upper()
        try:
            # Try 24-hour format
            time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            try:
                # Try 12-hour format with AM/PM
                time = datetime.strptime(time_str, '%I:%M %p').time()
            except ValueError:
                # Try adding AM/PM based on hour
                hour = int(time_str.split(':')[0])
                if hour < 8:  # Assume PM for early hours
                    time_str += ' PM'
                else:
                    time_str += ' AM'
                time = datetime.strptime(time_str, '%I:%M %p').time()
                
        return datetime.combine(datetime(year, month, day).date(), time)
    except Exception as e:
        current_app.logger.error(f"DateTime parsing error: {e}")
        return None

def clean_string_value(value):
    """Convert any value to string safely"""
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()

def clean_status(status):
    """Clean status value"""
    if pd.isna(status) or status is None:
        return ''
    return str(status).strip()

def get_or_create_district(name):
    """Get or create district by name"""
    if not name:
        # Get or create a default district for schools without one
        district = District.query.filter_by(name='Unknown District').first()
        if not district:
            district = District(
                name='Unknown District'
            )
            db.session.add(district)
            db.session.flush()
        return district
    
    district = District.query.filter(
        func.lower(District.name) == func.lower(name)
    ).first()
    
    if not district:
        district = District(
            name=name
        )
        db.session.add(district)
        db.session.flush()
    
    return district

def safe_str(value):
    """Safely convert a value to string, handling NaN and None"""
    if pd.isna(value):
        return ''
    return str(value)

def map_status(status_str):
    """Enhanced status mapping"""
    status_str = safe_str(status_str).strip().lower()
    
    # Add mappings for additional status values
    status_mapping = {
        'simulcast': EventStatus.SIMULCAST,
        'technical difficulties': EventStatus.NO_SHOW,
        'count': EventStatus.CONFIRMED,
        'local professional no-show': EventStatus.NO_SHOW,
        'pathful professional no-show': EventStatus.NO_SHOW,
        'teacher no-show': EventStatus.NO_SHOW,
        'teacher cancelation': EventStatus.CANCELLED,
        'successfully completed': EventStatus.COMPLETED
    }
    
    return status_mapping.get(status_str, EventStatus.DRAFT)

@virtual_bp.route('/import-sheet', methods=['POST'])
@login_required
def import_sheet():
    try:
        sheet_id = getenv('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("Google Sheet ID not configured")
        
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url, skiprows=5)
        
        # First, create a mapping of session titles to their datetime
        session_datetimes = {}
        for _, row in df.iterrows():
            title = clean_string_value(row.get('Session Title'))
            date_str = row.get('Date')
            time_str = row.get('Time')
            
            if title and not pd.isna(date_str) and not pd.isna(time_str):
                event_datetime = parse_datetime(date_str, time_str)
                if event_datetime:
                    session_datetimes[title] = event_datetime
        
        # Now process all rows, using the stored datetime for simulcast entries
        success_count = warning_count = error_count = 0
        errors = []
        processed_events = {}  # Keep track of created events
        
        for _, row in df.iterrows():
            try:
                title = clean_string_value(row.get('Session Title'))
                if not title:
                    continue
                
                # Get the datetime for this session
                event_datetime = session_datetimes.get(title)
                if not event_datetime:
                    warning_count += 1
                    errors.append(f"Skipped: No valid datetime found for {title}")
                    continue
                
                # Get or create event
                event_key = (title, event_datetime.date())
                if event_key in processed_events:
                    event = processed_events[event_key]
                else:
                    event = Event.query.filter(
                        func.lower(Event.title) == func.lower(title.strip()),
                        func.date(Event.start_date) == event_datetime.date(),
                        Event.type == EventType.VIRTUAL_SESSION
                    ).first()
                    
                    if not event:
                        event = Event(
                            title=title,
                            start_date=event_datetime,
                            type=EventType.VIRTUAL_SESSION,
                            status=EventStatus.map_status(clean_status(row.get('Status')))
                        )
                        db.session.add(event)
                        db.session.flush()
                    
                    processed_events[event_key] = event
                
                # Process teacher if present
                teacher_name = row.get('Teacher Name')
                if not pd.isna(teacher_name) and str(teacher_name).strip():
                    # Get or create teacher
                    first_name, last_name = clean_name(teacher_name)
                    teacher = Teacher.query.filter(
                        func.lower(Teacher.first_name) == func.lower(first_name),
                        func.lower(Teacher.last_name) == func.lower(last_name)
                    ).first()
                    
                    if not teacher:
                        school_name = safe_str(row.get('School Name'))
                        district_name = safe_str(row.get('District'))
                        
                        # Get or create district and school
                        district = get_or_create_district(district_name)
                        school = get_or_create_school(school_name, district)
                        
                        teacher = Teacher(
                            first_name=first_name,
                            last_name=last_name,
                            school_id=school.id if school else None
                        )
                        db.session.add(teacher)
                        db.session.flush()
                    
                    # Create or update EventTeacher registration
                    status_str = safe_str(row.get('Status')).lower()
                    is_simulcast = status_str == 'simulcast'
                    status = EventStatus.map_status(status_str)
                    
                    event_teacher = EventTeacher.query.filter_by(
                        event_id=event.id,
                        teacher_id=teacher.id
                    ).first()
                    
                    if not event_teacher:
                        event_teacher = EventTeacher(
                            event_id=event.id,
                            teacher_id=teacher.id,
                            status=status,
                            is_simulcast=is_simulcast,
                            attendance_confirmed_at=datetime.now(timezone.utc) if status == EventStatus.COMPLETED else None
                        )
                        db.session.add(event_teacher)
                
                # Add district association here
                district_name = row.get('District')  # Get district name from the CSV row
                if district_name:
                    district = get_or_create_district(district_name)  # This function either finds existing district or creates new one
                    event.district_partner = district_name  # Set the text field
                    if district not in event.districts:  # Add to the relationship if not already there
                        event.districts.append(district)
                
                db.session.commit()
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing row: {str(e)}")
                db.session.rollback()
                current_app.logger.error(f"Import error: {e}", exc_info=True)
        
        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Sheet import failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def clean_time_string(time_str):
    """Clean and validate time string"""
    if not time_str:
        return None
    # Remove duplicate AM/PM
    time_str = time_str.replace(' PM PM', ' PM').replace(' AM AM', ' AM')
    try:
        return datetime.strptime(time_str, '%I:%M %p')
    except ValueError:
        current_app.logger.warning(f"Invalid time format: {time_str}")
        return None

def generate_school_id(name):
    """Generate a unique ID for virtual schools that matches Salesforce length"""
    timestamp = datetime.now(timezone.utc).strftime('%y%m%d')
    name_hash = hashlib.sha256(name.lower().encode()).hexdigest()[:8]  # Increased to 8 chars
    base_id = f"VRT{timestamp}{name_hash}"  # Removed underscores to save space
    
    # Ensure exactly 18 characters
    base_id = base_id[:18].ljust(18, '0')
    
    # Check if ID exists and append counter if needed
    counter = 1
    new_id = base_id
    while School.query.filter_by(id=new_id).first():
        counter_str = str(counter).zfill(2)
        new_id = (base_id[:-2] + counter_str)  # Replace last 2 chars with counter
        counter += 1
    
    return new_id

def get_or_create_school(name, district=None):
    """Get or create school by name with improved district handling"""
    if not name:
        return None
    
    school = School.query.filter(
        func.lower(School.name) == func.lower(name)
    ).first()
    
    if not school:
        school = School(
            id=generate_school_id(name),
            name=name,
            district_id=district.id if district else None,
            normalized_name=name.lower(),
            salesforce_district_id=district.salesforce_id if district and district.salesforce_id else None
        )
        db.session.add(school)
        db.session.flush()
    
    return school
