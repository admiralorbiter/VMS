import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime, timezone
from flask import current_app
from models.district_model import District
from models.event import db, Event, EventType, EventStatus, EventFormat
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
        presenter_name = row.get('Presenter')
        presenter_org = standardize_organization(row.get('Organization', ''))
        
        if presenter_name and not pd.isna(presenter_name):
            presenter_name = str(presenter_name).strip()
            first_name, last_name = clean_name(presenter_name)
            
            # Only proceed if we have at least a first name
            if first_name:
                # First try exact match on first and last name (case-insensitive)
                volunteer = Volunteer.query.filter(
                    func.lower(Volunteer.first_name) == func.lower(first_name),
                    func.lower(Volunteer.last_name) == func.lower(last_name)
                ).first()
                
                # If no exact match and we have a last name, try partial matching
                if not volunteer and last_name:
                    volunteer = Volunteer.query.filter(
                        Volunteer.first_name.ilike(f"{first_name}%"),
                        Volunteer.last_name.ilike(f"{last_name}%")
                    ).first()
                
                # Create new volunteer if not found
                if not volunteer:
                    current_app.logger.info(f"Creating new volunteer: {first_name} {last_name}")
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name='',
                        organization_name=presenter_org if not pd.isna(presenter_org) else None
                    )
                    db.session.add(volunteer)
                    db.session.flush()
                
                # Create or update participation record
                participation = EventParticipation.query.filter_by(
                    event_id=event.id,
                    volunteer_id=volunteer.id
                ).first()
                
                if not participation:
                    # Define participation data
                    participation_data = {
                        'event_id': event.id,
                        'volunteer_id': volunteer.id,
                        'participant_type': 'Presenter',
                        'status': 'Completed' if status == EventStatus.COMPLETED else 'Confirmed'
                    }
                    
                    # Try to set delivery_hours if that field exists
                    try:
                        participation = EventParticipation(**participation_data)
                        if hasattr(EventParticipation, 'delivery_hours'):
                            participation.delivery_hours = event.duration / 60 if event.duration else 1
                    except Exception as e:
                        current_app.logger.warning(f"Could not set hours on EventParticipation: {e}")
                        participation = EventParticipation(**participation_data)
                    
                    db.session.add(participation)
                
                # Before adding new volunteer to event's volunteers list, clear existing ones
                if not is_simulcast:  # Only clear for non-simulcast events
                    event.volunteers = []  # Clear existing volunteer associations
                    if hasattr(event, 'professionals'):
                        event.professionals = ''  # Clear text-based professionals field
                    if hasattr(event, 'professional_ids'):
                        event.professional_ids = ''  # Clear professional IDs field
                
                # Add volunteer to event's volunteers list if not already there
                if volunteer not in event.volunteers:
                    event.volunteers.append(volunteer)
                
                # Also update text-based fields for backwards compatibility
                if hasattr(event, 'professionals'):
                    current_profs = []
                    if event.professionals:
                        current_profs = [p.strip() for p in event.professionals.split(';') if p.strip()]
                    prof_name = f"{volunteer.first_name} {volunteer.last_name}"
                    if prof_name not in current_profs:
                        current_profs.append(prof_name)
                        event.professionals = '; '.join(current_profs)
                
                if hasattr(event, 'professional_ids'):
                    current_ids = []
                    if event.professional_ids:
                        current_ids = [id.strip() for id in event.professional_ids.split(';') if id.strip()]
                    if str(volunteer.id) not in current_ids:
                        current_ids.append(str(volunteer.id))
                        event.professional_ids = '; '.join(current_ids)

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
                        is_simulcast=row.get('Status', '').lower() == 'simulcast'
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
    """More robust name cleaning function"""
    if not name or pd.isna(name):
        return '', ''
    
    name = str(name).strip()
    
    # Handle common prefixes
    prefixes = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.']
    for prefix in prefixes:
        if name.lower().startswith(prefix):
            name = name[len(prefix):].strip()
    
    # Split name into parts
    parts = [p for p in name.split() if p]
    
    if len(parts) == 0:
        return '', ''
    elif len(parts) == 1:
        return parts[0], ''
    else:
        # For simplicity in matching, use first part as first name
        # and last part as last name (helps match with database)
        return parts[0], parts[-1]

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
    """More robust date/time parsing function"""
    try:
        # Handle missing or NaN values
        if pd.isna(date_str) or pd.isna(time_str):
            return None
            
        # Convert numeric values to strings
        if isinstance(date_str, (int, float)):
            date_str = str(int(date_str))
        if isinstance(time_str, (int, float)):
            time_str = str(int(time_str))
            
        # Clean up the date and time strings
        date_str = str(date_str).strip()
        time_str = str(time_str).strip()
        
        # Parse date - try multiple formats
        date_obj = None
        
        # Try different date formats
        date_formats = ['%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y', '%Y-%m-%d']
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        
        # If all formats failed, try parsing MM/DD format with current year
        if not date_obj and '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 2:
                try:
                    month, day = map(int, parts)
                    current_year = datetime.now().year
                    date_obj = datetime(current_year, month, day).date()
                except (ValueError, IndexError):
                    pass
        
        # If still no date, return None
        if not date_obj:
            return None
            
        # Parse time - try multiple formats
        time_obj = None
        time_formats = ['%I:%M %p', '%H:%M', '%I:%M%p', '%I%p']
        
        # Standardize AM/PM notation
        time_str = (time_str.replace('am', ' AM')
                   .replace('pm', ' PM')
                   .replace('AM', ' AM')
                   .replace('PM', ' PM')
                   .replace('  ', ' '))
        
        for fmt in time_formats:
            try:
                time_obj = datetime.strptime(time_str, fmt).time()
                break
            except ValueError:
                continue
        
        # If time parsing failed, use default time (9:00 AM)
        if not time_obj:
            time_obj = datetime.strptime('9:00 AM', '%I:%M %p').time()
        
        # Combine date and time
        return datetime.combine(date_obj, time_obj)
    except Exception as e:
        current_app.logger.warning(f"DateTime parsing error: {e} for date: '{date_str}', time: '{time_str}'")
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
    # Handle null/empty/nan values
    if pd.isna(name) or not name or name.strip() == '':
        name = 'Unknown District'
    else:
        name = str(name).strip()
    
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
    if pd.isna(value) or value is None:
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
        
        # Modify the session_datetimes creation to handle multiple dates per title
        session_datetimes = {}
        for _, row in df.iterrows():
            title = clean_string_value(row.get('Session Title'))
            date_str = row.get('Date')
            time_str = row.get('Time')
            
            if title and not pd.isna(date_str) and not pd.isna(time_str):
                event_datetime = parse_datetime(date_str, time_str)
                if event_datetime:
                    # Store as a list of dates for each title
                    if title not in session_datetimes:
                        session_datetimes[title] = {}
                    # Use date as key to handle multiple dates for same title
                    date_key = event_datetime.date().isoformat()
                    session_datetimes[title][date_key] = event_datetime
        
        # Now process all rows, using the stored datetime for simulcast entries
        success_count = warning_count = error_count = 0
        errors = []
        processed_events = {}  # Keep track of created events
        
        for _, row in df.iterrows():
            try:
                title = clean_string_value(row.get('Session Title'))
                if not title:
                    continue
                
                # Get the date string from the current row
                date_str = row.get('Date')
                if pd.isna(date_str):
                    warning_count += 1
                    errors.append(f"Skipped: No date for {title}")
                    continue
                
                # Parse the date to match the format used as key
                parsed_date = parse_datetime(date_str, row.get('Time'))
                if not parsed_date:
                    warning_count += 1
                    errors.append(f"Skipped: Invalid date/time for {title}")
                    continue
                
                date_key = parsed_date.date().isoformat()
                
                # Get the datetime specific to this title and date
                if title in session_datetimes and date_key in session_datetimes[title]:
                    event_datetime = session_datetimes[title][date_key]
                else:
                    warning_count += 1
                    errors.append(f"Skipped: No valid datetime found for {title} on {date_key}")
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
                            end_date=event_datetime.replace(hour=event_datetime.hour+1) if event_datetime else None,
                            duration=60,  # Set default duration to 60 minutes
                            type=EventType.VIRTUAL_SESSION,
                            format=EventFormat.VIRTUAL,
                            status=EventStatus.map_status(clean_status(row.get('Status'))),
                            session_id=extract_session_id(row.get('Session Link'))  # Use the safer function
                        )
                        db.session.add(event)
                        db.session.flush()
                    
                    processed_events[event_key] = event
                
                # Update completed session metrics
                status_str = safe_str(row.get('Status')).lower()
                status = EventStatus.map_status(status_str)
                
                # Set default metrics for completed events
                if status == EventStatus.COMPLETED:
                    # Update event metrics
                    event.participant_count = 20  # Set student count to 20
                    event.registered_count = 20  # Set registered count to match
                    event.attended_count = 20  # Set attended count to match
                    event.volunteers_needed = 1  # Set volunteers needed to 1
                    
                    # Make sure duration is set
                    if not event.duration:
                        event.duration = 60  # Default to 60 minutes
                
                # Handle presenter/volunteer - MOVED OUTSIDE THE STATUS CONDITION
                presenter_name = row.get('Presenter')
                presenter_org = row.get('Organization', '')
                if presenter_name and not pd.isna(presenter_name):
                    presenter_name = str(presenter_name).strip()
                    first_name, last_name = clean_name(presenter_name)
                    
                    # Only proceed if we have at least a first name
                    if first_name:
                        # First try exact match on first and last name (case-insensitive)
                        volunteer = Volunteer.query.filter(
                            func.lower(Volunteer.first_name) == func.lower(first_name),
                            func.lower(Volunteer.last_name) == func.lower(last_name)
                        ).first()
                        
                        # If no exact match and we have a last name, try partial matching
                        if not volunteer and last_name:
                            volunteer = Volunteer.query.filter(
                                Volunteer.first_name.ilike(f"{first_name}%"),
                                Volunteer.last_name.ilike(f"{last_name}%")
                            ).first()
                        
                        # Create new volunteer if not found
                        if not volunteer:
                            current_app.logger.info(f"Creating new volunteer: {first_name} {last_name}")
                            volunteer = Volunteer(
                                first_name=first_name,
                                last_name=last_name,
                                middle_name='',
                                organization_name=presenter_org if not pd.isna(presenter_org) else None
                            )
                            db.session.add(volunteer)
                            db.session.flush()
                        
                        # Create or update participation record
                        participation = EventParticipation.query.filter_by(
                            event_id=event.id,
                            volunteer_id=volunteer.id
                        ).first()
                        
                        if not participation:
                            # Define participation data
                            participation_data = {
                                'event_id': event.id,
                                'volunteer_id': volunteer.id,
                                'participant_type': 'Presenter',
                                'status': 'Completed' if status == EventStatus.COMPLETED else 'Confirmed'
                            }
                            
                            # Try to set delivery_hours if that field exists
                            try:
                                participation = EventParticipation(**participation_data)
                                if hasattr(EventParticipation, 'delivery_hours'):
                                    participation.delivery_hours = event.duration / 60 if event.duration else 1
                            except Exception as e:
                                current_app.logger.warning(f"Could not set hours on EventParticipation: {e}")
                                participation = EventParticipation(**participation_data)
                            
                            db.session.add(participation)
                        
                        # Before adding new volunteer to event's volunteers list, clear existing ones
                        if not is_simulcast:  # Only clear for non-simulcast events
                            event.volunteers = []  # Clear existing volunteer associations
                            if hasattr(event, 'professionals'):
                                event.professionals = ''  # Clear text-based professionals field
                            if hasattr(event, 'professional_ids'):
                                event.professional_ids = ''  # Clear professional IDs field
                        
                        # Add volunteer to event's volunteers list if not already there
                        if volunteer not in event.volunteers:
                            event.volunteers.append(volunteer)
                        
                        # Also update text-based fields for backwards compatibility
                        if hasattr(event, 'professionals'):
                            current_profs = []
                            if event.professionals:
                                current_profs = [p.strip() for p in event.professionals.split(';') if p.strip()]
                            prof_name = f"{volunteer.first_name} {volunteer.last_name}"
                            if prof_name not in current_profs:
                                current_profs.append(prof_name)
                                event.professionals = '; '.join(current_profs)
                        
                        if hasattr(event, 'professional_ids'):
                            current_ids = []
                            if event.professional_ids:
                                current_ids = [id.strip() for id in event.professional_ids.split(';') if id.strip()]
                            if str(volunteer.id) not in current_ids:
                                current_ids.append(str(volunteer.id))
                                event.professional_ids = '; '.join(current_ids)
                
                # Process teacher if present
                teacher_name = row.get('Teacher Name')
                if not pd.isna(teacher_name) and str(teacher_name).strip():
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
                    is_simulcast = status_str == 'simulcast'
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
                
                # Add district association
                district_name = row.get('District')
                if district_name and not pd.isna(district_name):
                    district = get_or_create_district(district_name)
                    event.district_partner = district_name
                    if district not in event.districts:
                        event.districts.append(district)
                
                db.session.commit()
                success_count += 1

                # Add this right after assigning a presenter to an event
                # DEBUGGING
                current_app.logger.info(
                    f"Added presenter '{presenter_name}' to event '{event.title}' (date: {event_datetime.date().isoformat()})"
                )

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

def extract_session_id(session_link):
    """Safely extract session ID from link with type checking"""
    try:
        if pd.isna(session_link) or session_link is None:
            return None
            
        # Convert float to string if needed
        if isinstance(session_link, (int, float)):
            return str(int(session_link))
            
        # If it's a URL, extract the last part
        link_str = str(session_link).strip()
        if '/' in link_str:
            return link_str.split('/')[-1]
        return link_str
    except Exception as e:
        current_app.logger.warning(f"Error extracting session ID: {e} from {session_link}")
        return None
