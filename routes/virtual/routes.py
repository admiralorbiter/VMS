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
from sqlalchemy.orm import joinedload # Import for potential optimization if needed
from routes.reports.common import DISTRICT_MAPPING

virtual_bp = Blueprint('virtual', __name__, url_prefix='/virtual')

@virtual_bp.route('/virtual')
def virtual():
    return render_template('virtual/virtual.html')

def process_csv_row(row, success_count, warning_count, error_count, errors, all_rows=None):
    try:
        db.session.rollback()
        
        # Skip empty rows
        if not any(row.values()):
            return success_count, warning_count, error_count

        # Get status early to determine processing logic
        status_str = safe_str(row.get('Status', '')).lower()
        is_simulcast = status_str == 'simulcast'
        
        # Parse the date early since we'll need it in multiple places
        date_str = row.get('Date')
        time_str = row.get('Time', '')
        parsed_date = parse_datetime(date_str, time_str) if date_str else None
        
        # For simulcast entries or entries without dates, we only process teacher data
        if is_simulcast or not date_str:
            # Only process teacher information
            if row.get('Teacher Name'):
                process_teacher_data(row, is_simulcast)
                success_count += 1
            return success_count, warning_count, error_count

        # For regular entries, proceed with full processing
        session_id = extract_session_id(row.get('Session Link'))
        event = Event.query.filter_by(session_id=session_id).first() if session_id else None
        
        if not event:
            event = Event()
            event.session_id = session_id
            event.title = row.get('Session Title')
            event.type = EventType.VIRTUAL_SESSION
            event.status = EventStatus.map_status(status_str)
            event.topic = row.get('Topic/Theme')
            event.session_type = row.get('Session Type')
            event.session_link = row.get('Session Link')
            
            # Set date/time for new events
            try:
                date_str = row.get('Date')
                time_str = row.get('Time', '')
                if date_str:
                    date_parts = date_str.split('/')
                    current_year = datetime.now(timezone.utc).year
                    event.date = datetime.strptime(f"{date_parts[0]}/{date_parts[1]}/{current_year}", '%m/%d/%Y').date()
                    if time_str:
                        event.start_time = datetime.strptime(time_str, '%I:%M %p').time()
            except ValueError as e:
                error_count += 1
                errors.append(f"Error parsing date/time for {event.title}: {str(e)}")
                return success_count, warning_count, error_count

        # Handle presenter information
        process_presenter(row, event, is_simulcast)

        # Handle teacher information
        if row.get('Teacher Name') and not pd.isna(row.get('Teacher Name')):
            process_teacher_for_event(row, event, is_simulcast)

        # Collect all districts (main event + simulcast) before adding them
        districts_to_add = set()
        
        # Add the main event's district if it exists
        main_district = row.get('District')
        if main_district and not pd.isna(main_district):
            districts_to_add.add(main_district)
            # Set district_partner to the main event's district if not already set
            if not event.district_partner:
                event.district_partner = main_district

        # For completed sessions, collect all simulcast districts
        if status_str == 'successfully completed' and all_rows and parsed_date:
            session_title = row.get('Session Title')
            date_key = parsed_date.date().isoformat()
            if session_title:
                # Find all simulcast entries with matching title and date
                simulcast_districts = set()
                for sim_row in all_rows:  # Changed from df.iterrows()
                    sim_title = clean_string_value(sim_row.get('Session Title'))
                    sim_status = safe_str(sim_row.get('Status', '')).lower()
                    sim_district = safe_str(sim_row.get('District'))
                    sim_date = parse_datetime(sim_row.get('Date'), sim_row.get('Time'))
                    
                    if (sim_title == session_title and 
                        sim_status == 'simulcast' and 
                        sim_district and not pd.isna(sim_district) and
                        (not sim_date or sim_date.date().isoformat() == date_key)):
                        simulcast_districts.add(sim_district)

        # Now add all collected districts to the event
        for district_name in districts_to_add:
            add_district_to_event(event, district_name)

        db.session.add(event)
        db.session.commit()
        success_count += 1
        
    except Exception as e:
        error_count += 1
        title = row.get('Session Title', 'Unknown session')
        errors.append(f"Error processing {title}: {str(e)}")
        db.session.rollback()
        current_app.logger.error(f"Import error: {e}", exc_info=True)
    
    return success_count, warning_count, error_count

def process_teacher_data(row, is_simulcast=False):
    """Helper function to process just teacher data for simulcast/dateless entries"""
    if not row.get('Teacher Name') or pd.isna(row.get('Teacher Name')):
        return
        
    teacher_name = safe_str(row.get('Teacher Name'))
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
            db.session.commit()

def process_presenter(row, event, is_simulcast):
    """Helper function to process presenter data"""
    volunteer_id = None
    presenter_name = row.get('Presenter')
    presenter_org = standardize_organization(row.get('Organization', ''))
    
    if presenter_name and not pd.isna(presenter_name):
        presenter_name = safe_str(presenter_name)
        first_name, last_name = clean_name(presenter_name)
        
        # Only proceed if we have at least a first name
        if first_name:
            volunteer = find_or_create_volunteer(first_name, last_name, presenter_org)
            
            if volunteer:
                # Create or update participation record
                create_participation(event, volunteer, event.status)
                
                # Handle volunteer association
                update_volunteer_association(event, volunteer, is_simulcast)

def find_or_create_volunteer(first_name, last_name, organization=None):
    """Find an existing volunteer or create a new one"""
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
            organization_name=organization if not pd.isna(organization) else None
        )
        db.session.add(volunteer)
        db.session.flush()
    
    return volunteer

def create_participation(event, volunteer, status):
    """Create or update participation record"""
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

def update_volunteer_association(event, volunteer, is_simulcast):
    """Update volunteer associations for an event"""
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
    update_legacy_fields(event, volunteer)

def update_legacy_fields(event, volunteer):
    """Update legacy text-based fields for backward compatibility"""
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

def process_teacher_for_event(row, event, is_simulcast):
    """Process teacher data for a specific event"""
    # Check if teacher name exists and is not a NaN value
    if not row.get('Teacher Name') or pd.isna(row.get('Teacher Name')):
        return
        
    teacher_name = safe_str(row.get('Teacher Name'))
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
            if school_name and not pd.isna(school_name):
                district = get_or_create_district(district_name) if district_name else None
                school = get_or_create_school(school_name, district)
                if school:  # Only set school_id if school exists
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
                is_simulcast=is_simulcast,
                attendance_confirmed_at=datetime.now(timezone.utc) if event.status == EventStatus.COMPLETED else None
            )
            db.session.add(event_teacher)

def add_district_to_event(event, district_name):
    """Gets or creates the district and adds it to the event's districts list if not already present."""
    district = get_or_create_district(district_name) # Handles None/empty names
    if district:
        # Check if district is already associated by ID
        if not any(d.id == district.id for d in event.districts):
            event.districts.append(district)
            print(f"    Added district '{district.name}' (ID: {district.id}) to event '{event.title}'")
        # else:
        #     print(f"    District '{district.name}' already associated with event '{event.title}'.")
    # else:
    #     print(f"    Skipped adding invalid district name: {district_name}")

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
            
            # Convert to list to allow multiple passes
            all_rows = list(csv_data)
            
            for row in all_rows:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors, all_rows
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
            all_rows = list(csv_data)
            
            for row in all_rows:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors, all_rows
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
    """Parse date and time strings using academic year logic"""
    try:
        # Handle missing or NaN values
        if pd.isna(date_str) or pd.isna(time_str):
            return None
            
        # Convert numeric values to strings and clean them
        date_str = str(date_str).strip() if not pd.isna(date_str) else ''
        time_str = str(time_str).strip() if not pd.isna(time_str) else ''
        
        if not date_str:
            return None
            
        # Parse the month and day
        try:
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) >= 2:
                    month = int(parts[0])
                    day = int(parts[1])
                else:
                    return None
            else:
                return None
                
            # Validate month and day
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                return None
                
            # Get current date for comparison
            current_date = datetime.now(timezone.utc)
            
            # Determine academic year
            # If we're in or after June, use current year for fall semester (months 6-12)
            # and next year for spring semester (months 1-5)
            # If we're before June, use previous year for fall semester and current year for spring
            if current_date.month >= 6:
                year = current_date.year if month >= 6 else current_date.year + 1
            else:
                year = current_date.year - 1 if month >= 6 else current_date.year
                
            # Create the date object with validation
            try:
                date_obj = datetime(year, month, day).date()
            except ValueError:
                # Handle invalid dates like 9/31
                return None
                
            # Parse time with multiple format support
            time_obj = None
            
            # Clean up time string
            time_str = (time_str.replace('am', ' AM')
                       .replace('pm', ' PM')
                       .replace('AM', ' AM')
                       .replace('PM', ' PM')
                       .replace('  ', ' ')
                       .strip())
            
            # Try different time formats
            time_formats = [
                '%I:%M %p',  # 11:30 AM
                '%H:%M',     # 13:30
                '%I:%M%p',   # 11:30AM
                '%I%p',      # 11AM
                '%H:%M:%S'   # 13:30:00
            ]
            
            for fmt in time_formats:
                try:
                    if 'M' in fmt:  # If format expects AM/PM
                        if ' AM' not in time_str.upper() and ' PM' not in time_str.upper():
                            continue
                    time_obj = datetime.strptime(time_str, fmt).time()
                    break
                except ValueError:
                    continue
            
            # If time parsing failed, use default time (9:00 AM)
            if not time_obj:
                time_obj = datetime.strptime('9:00 AM', '%I:%M %p').time()
            
            # Combine date and time
            return datetime.combine(date_obj, time_obj)
            
        except (ValueError, IndexError, TypeError) as e:
            current_app.logger.warning(f"Date parsing error: {e} for date: '{date_str}'")
            return None
            
    except Exception as e:
        current_app.logger.warning(f"DateTime parsing error: {e} for date: '{date_str}', time: '{time_str}'")
        return None

def clean_string_value(value):
    """Convert any value to string safely"""
    if pd.isna(value) or value is None:
        return ''
    # Handle float or numeric values
    if isinstance(value, (float, int)):
        return str(value)
    return str(value).strip()

def clean_status(status):
    """Clean status value"""
    if pd.isna(status) or status is None:
        return ''
    return str(status).strip()

def get_or_create_district(name):
    """
    Get or create district by name, attempting to match aliases and standard names
    from DISTRICT_MAPPING to avoid creating duplicates.
    """
    if pd.isna(name) or not name or str(name).strip() == '':
        effective_name = 'Unknown District'
        target_salesforce_id = None
    else:
        effective_name = str(name).strip()
        target_salesforce_id = None

        # --- Attempt to map the input name to a canonical Salesforce ID ---
        name_lower = effective_name.lower()
        for sf_id, mapping_info in DISTRICT_MAPPING.items():
            # Check exact canonical name
            if mapping_info['name'].lower() == name_lower:
                target_salesforce_id = sf_id
                effective_name = mapping_info['name'] # Use the canonical name
                print(f"    Mapped input '{name}' to canonical name '{effective_name}' via exact match (SFID: {sf_id})")
                break
            # Check aliases
            if 'aliases' in mapping_info:
                for alias in mapping_info['aliases']:
                    if alias.lower() == name_lower:
                        target_salesforce_id = sf_id
                        effective_name = mapping_info['name'] # Use the canonical name
                        print(f"    Mapped input '{name}' to canonical name '{effective_name}' via alias '{alias}' (SFID: {sf_id})")
                        break
            if target_salesforce_id: # Stop searching if mapped
                break
        # --- End Mapping Attempt ---

    district = None
    # If we mapped to a Salesforce ID, prioritize finding the district by that ID
    if target_salesforce_id:
        district = District.query.filter_by(salesforce_id=target_salesforce_id).first()
        if district:
            print(f"    Found existing district by mapped Salesforce ID: '{district.name}' (ID: {district.id})")

    # If not found by Salesforce ID (or no mapping occurred), try finding by the effective name (case-insensitive)
    if not district:
        district = District.query.filter(func.lower(District.name) == func.lower(effective_name)).first()
        if district:
             print(f"    Found existing district by name lookup: '{district.name}' (ID: {district.id})")


    # Only create a new district if absolutely not found and it's not 'Unknown District'
    if not district and effective_name != 'Unknown District':
        print(f"      CREATING NEW district: '{effective_name}' (Salesforce ID will be NULL)")
        # We create it without a Salesforce ID because we couldn't map it
        district = District(name=effective_name)
        db.session.add(district)
        db.session.flush() # Flush to assign an ID

    # Handle 'Unknown District' case - find or create the specific 'Unknown' record
    elif not district and effective_name == 'Unknown District':
         district = District.query.filter(func.lower(District.name) == 'unknown district').first()
         if not district:
              print(f"      CREATING 'Unknown District'")
              district = District(name='Unknown District')
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
        # Consider removing nrows limit for production
        df = pd.read_csv(csv_url, skiprows=5, dtype={'School Name': str})

        print(f"\n=== Starting Import ===")
        print(f"Total rows read from sheet: {len(df)}")
        print("========================\n")

        session_datetimes = {}
        # --- First Pass: Identify potential primary event instances and their datetimes ---
        print("--- First Pass: Identifying event datetimes ---")
        for index, row in df.iterrows():
            title = clean_string_value(row.get('Session Title'))
            date_str = row.get('Date')
            time_str = row.get('Time')
            status_str = safe_str(row.get('Status', '')).lower().strip()

            # Basic check for necessary data
            if title and not pd.isna(date_str) and not pd.isna(time_str):
                event_datetime = parse_datetime(date_str, time_str)
                if event_datetime:
                    date_key = event_datetime.date().isoformat()
                    if title not in session_datetimes:
                        session_datetimes[title] = {}

                    # Store the datetime. Mark if this specific row seems like a "primary" one.
                    # Define "primary" statuses (rows that define the core event)
                    is_primary_status = status_str not in ['simulcast', 'teacher no-show', 'count', 'technical difficulties', ''] # Add other non-primary statuses if necessary
                    if date_key not in session_datetimes[title] or is_primary_status:
                         # Prioritize storing info from a primary row if multiple rows have same date/time
                         session_datetimes[title][date_key] = {'datetime': event_datetime, 'is_primary': is_primary_status, 'status': status_str}
                         print(f"  Stored datetime for '{title}' on {date_key} (Primary: {is_primary_status})")

        print("--- First Pass Complete ---\n")

        success_count = warning_count = error_count = 0
        errors = []
        # Use Event ID cache to handle multiple rows for the same event
        processed_event_ids = {}
        # Convert DataFrame rows to a list of dictionaries for easier lookup
        all_rows_for_lookup = df.to_dict('records')

        # --- Second Pass: Process each row ---
        print("--- Second Pass: Processing Rows ---")
        for row_index, row_data in enumerate(all_rows_for_lookup):
            event_processed_in_this_row = False # Flag to track if event logic ran
            try:
                # Extract key fields safely
                status_str = safe_str(row_data.get('Status', '')).lower().strip()
                is_simulcast = status_str == 'simulcast'
                title = clean_string_value(row_data.get('Session Title'))

                if not title:
                    print(f"Skipping row {row_index + 1}: No Session Title")
                    warning_count += 1
                    errors.append(f"Skipped row {row_index + 1}: Missing Session Title")
                    continue

                # Determine the event context (datetime and date_key) for this row
                current_datetime = None
                date_key = None
                date_str = row_data.get('Date')
                time_str = row_data.get('Time')

                # Try parsing date/time from the current row first
                if not pd.isna(date_str):
                    parsed_date = parse_datetime(date_str, time_str)
                    if parsed_date:
                        current_datetime = parsed_date
                        date_key = current_datetime.date().isoformat()

                # If current row lacks date/time, try finding *any* matching event from pass 1
                if not current_datetime and title in session_datetimes:
                     # Heuristic: Find *a* date_key associated with this title if row lacks its own
                     potential_date_key = next(iter(session_datetimes[title]), None)
                     if potential_date_key:
                         current_datetime = session_datetimes[title][potential_date_key]['datetime']
                         date_key = potential_date_key
                         print(f"Row {row_index + 1} ('{title}'): Using inferred date {date_key} as row lacks specific date/time.")

                # If we still can't determine event context, we can only process teacher data
                if not current_datetime or not date_key:
                    if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                         print(f"Processing row {row_index + 1} ('{title}'): No valid event context found. Processing TEACHER ONLY.")
                         process_teacher_data(row_data, is_simulcast)
                         # Don't count as full success? Maybe just log.
                    else:
                         print(f"Skipping row {row_index + 1} ('{title}'): Cannot determine event context and no teacher name.")
                         warning_count += 1
                         errors.append(f"Skipped row {row_index + 1} ('{title}'): Cannot determine event context.")
                    continue # Cannot process event without context

                # --- Event Handling ---
                event_key = (title, date_key)
                event = None
                event_id = processed_event_ids.get(event_key)

                if event_id:
                    # Fetch fresh event object from session/DB using cached ID
                    event = db.session.get(Event, event_id)
                    if not event:
                         print(f"Warning: Event ID {event_id} found in cache for '{title}'/{date_key}, but not in DB session. Querying DB.")
                         # Fall through to DB query if session.get fails unexpectedly

                if not event:
                    # Query DB if not found via cache or if session.get failed
                    event = Event.query.filter(
                        func.lower(Event.title) == func.lower(title.strip()),
                        func.date(Event.start_date) == current_datetime.date(),
                        Event.type == EventType.VIRTUAL_SESSION
                    ).first()

                    if event:
                        # Found in DB, cache its ID
                        processed_event_ids[event_key] = event.id
                        print(f"Found existing event in DB for '{title}' on {date_key}. ID: {event.id}")
                    else:
                        # Create new event *only if* this row represents a primary instance
                        is_primary_row_status = status_str not in ['simulcast', 'teacher no-show', 'count', 'technical difficulties', '']
                        if is_primary_row_status:
                            print(f"Creating NEW event for '{title}' on {date_key} based on primary status: '{status_str}'")
                            event = Event(
                                title=title,
                                start_date=current_datetime,
                                # Basic duration logic, refine if needed
                                end_date=current_datetime.replace(hour=current_datetime.hour+1) if current_datetime else None,
                                duration=60,
                                type=EventType.VIRTUAL_SESSION,
                                format=EventFormat.VIRTUAL,
                                status=EventStatus.map_status(status_str), # Status from primary row
                                session_id=extract_session_id(row_data.get('Session Link'))
                            )
                            db.session.add(event)
                            db.session.flush() # Flush to get the new event.id
                            processed_event_ids[event_key] = event.id
                            print(f"  New Event ID: {event.id}")
                        else:
                            # This row is secondary, but no existing event found.
                            # We can only process teacher data for this row.
                            print(f"Row {row_index + 1} ('{title}'): Secondary status '{status_str}' but no existing event found. Processing TEACHER ONLY.")
                            if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                                process_teacher_data(row_data, is_simulcast)
                            continue # Skip further event processing for this row


                # If we don't have an event object here, something went wrong or it was skipped above
                if not event:
                    print(f"Skipping row {row_index + 1} ('{title}'): Could not find or create event.")
                    warning_count += 1
                    errors.append(f"Skipped row {row_index + 1} ('{title}'): Could not find or create event.")
                    continue

                # --- Determine if this row dictates the event's core data ---
                # We only update core Event fields, Districts, Partner, Volunteer based on ONE primary row per event instance.
                # Check if *this row* is considered the primary one for this event key.
                is_primary_row_status = status_str not in ['simulcast', 'teacher no-show', 'count', 'technical difficulties', '']
                # We also need to check if we've ALREADY processed the primary logic for this event_key
                primary_logic_run_key = f"{event_key}_primary_done"
                primary_logic_already_run = processed_event_ids.get(primary_logic_run_key, False)


                # --- Primary Logic Block ---
                # Run this block only ONCE per event instance, using the first primary row encountered.
                if is_primary_row_status and not primary_logic_already_run:
                    event_processed_in_this_row = True # Mark that event logic ran
                    print(f"\n=== Processing PRIMARY LOGIC for Event '{title}' ({event.id}) (Row {row_index+1}) ===")
                    print(f"    Primary Event Key: Title='{title}', DateKey='{date_key}'")
                    processed_event_ids[primary_logic_run_key] = True # Mark primary logic as done for this event

                    # Update core event details from this primary row
                    event.status = EventStatus.map_status(status_str)
                    event.session_id = extract_session_id(row_data.get('Session Link'))
                    # Update other fields if needed: topic, session_type, etc.
                    event.topic = row_data.get('Topic/Theme')
                    event.session_type = row_data.get('Session Type')
                    event.session_link = row_data.get('Session Link')

                    # --- District Handling (Reset and Aggregate) ---
                    print("  Clearing existing districts...")
                    event.districts = [] # Reset districts for this event instance
                    db.session.flush()   # Ensure the clear is persisted before adding

                    all_associated_district_names = set()
                    primary_row_district = None

                    print(f"  Searching all {len(all_rows_for_lookup)} rows for districts associated with '{title}' on {date_key}...")
                    # Iterate through ALL rows to find districts related to this title and date
                    for lookup_row_index, lookup_row_data in enumerate(all_rows_for_lookup):
                        lookup_title = clean_string_value(lookup_row_data.get('Session Title'))
                        # Fast skip if title doesn't match
                        if lookup_title != title:
                            continue

                        lookup_date_str = lookup_row_data.get('Date')
                        lookup_time_str = lookup_row_data.get('Time')
                        final_lookup_date_key = None # Initialize

                        # Attempt 1: Parse full datetime
                        lookup_datetime = parse_datetime(lookup_date_str, lookup_time_str)
                        if lookup_datetime:
                            final_lookup_date_key = lookup_datetime.date().isoformat()
                            print(f"    [Row {lookup_row_index+1}] Parsed FULL datetime: LookupDateKey='{final_lookup_date_key}'")
                        else:
                            # Attempt 2: If full parse failed BUT raw date string exists, parse just the date part
                            if not pd.isna(lookup_date_str):
                                try:
                                    date_str_cleaned = str(lookup_date_str).strip()
                                    if '/' in date_str_cleaned:
                                        parts = date_str_cleaned.split('/')
                                        if len(parts) >= 2:
                                            month = int(parts[0])
                                            day = int(parts[1])
                                            if 1 <= month <= 12 and 1 <= day <= 31:
                                                # Determine academic year (same logic as parse_datetime)
                                                current_dt_utc = datetime.now(timezone.utc)
                                                if current_dt_utc.month >= 6:
                                                    year = current_dt_utc.year if month >= 6 else current_dt_utc.year + 1
                                                else:
                                                    year = current_dt_utc.year - 1 if month >= 6 else current_dt_utc.year

                                                # Create date object, handle potential ValueError (e.g., 2/30)
                                                try:
                                                    date_obj_only = datetime(year, month, day).date()
                                                    final_lookup_date_key = date_obj_only.isoformat()
                                                    print(f"    [Row {lookup_row_index+1}] Parsed DATE ONLY: LookupDateKey='{final_lookup_date_key}'")
                                                except ValueError:
                                                    print(f"    [Row {lookup_row_index+1}] Invalid date components from date string: {year}-{month}-{day}")
                                                    final_lookup_date_key = None # Mark as failed
                                            else: # Invalid month/day numbers
                                                print(f"    [Row {lookup_row_index+1}] Invalid month/day from date string: {month}/{day}")
                                                final_lookup_date_key = None
                                        else: # Not enough parts after split
                                           final_lookup_date_key = None
                                    else: # Date string doesn't contain '/' - add other format handling if needed
                                        final_lookup_date_key = None
                                except Exception as e:
                                    print(f"    [Row {lookup_row_index+1}] Error parsing date only from '{lookup_date_str}': {e}")
                                    final_lookup_date_key = None
                            # else: Raw date string is also missing/NaN, final_lookup_date_key remains None

                        print(f"    [Row {lookup_row_index+1}] Checking: Title='{lookup_title}', RawDate='{lookup_date_str}', RawTime='{lookup_time_str}', FinalLookupDateKey='{final_lookup_date_key}'")

                        # Compare using the final derived lookup_date_key
                        # Ensure both keys are valid and match
                        if final_lookup_date_key is not None and final_lookup_date_key == date_key:
                            lookup_district = safe_str(lookup_row_data.get('District'))
                            print(f"      MATCHED on Title and DateKey. Found District: '{lookup_district}'")
                            if lookup_district:
                                all_associated_district_names.add(lookup_district)
                                # Check if this lookup_row_data is the current primary row_data
                                if lookup_row_data is row_data:
                                     primary_row_district = lookup_district
                        else:
                            print(f"      NO MATCH: Title or FinalDateKey mismatch ('{lookup_title}' == '{title}', '{final_lookup_date_key}' == '{date_key}')") # Modified log


                    print(f"  Finished search. Found unique associated district names: {all_associated_district_names}")

                    # Set district partner based ONLY on the primary row's district
                    event.district_partner = primary_row_district # This will be None if primary row had no district
                    print(f"  District Partner set to: {event.district_partner} (from primary row)")

                    # Add all unique districts found to the relationship
                    for district_name in all_associated_district_names:
                        add_district_to_event(event, district_name) # Use helper (modified below)

                    # Fallback for district partner if primary row had none
                    if not event.district_partner and all_associated_district_names:
                        fallback_partner = next(iter(sorted(list(all_associated_district_names))), None) # Pick one consistently
                        event.district_partner = fallback_partner
                        print(f"  Fallback District Partner set to: {event.district_partner}")

                    # Flush to ensure district additions are reflected before logging
                    db.session.flush()
                    print(f"  Final Associated Districts after adding: {[d.name for d in event.districts]}")


                    # --- Volunteer/Presenter Handling (from primary row only) ---
                    print("  Processing presenter/volunteer from primary row...")
                    # Assuming only the primary row defines the presenter.
                    # The is_simulcast=False ensures volunteer list is cleared before adding.
                    process_presenter(row_data, event, is_simulcast=False)
                    print(f"  Event Volunteers after processing: {[v.full_name for v in event.volunteers]}")


                    # --- Update Metrics (if applicable, from primary row) ---
                    if event.status == EventStatus.COMPLETED:
                        print("  Updating metrics for completed event...")
                        # Set default metrics if not already set, or adjust as needed
                        event.participant_count = event.participant_count or 0
                        event.registered_count = event.registered_count or 0
                        event.attended_count = event.attended_count or 0
                        event.volunteers_needed = event.volunteers_needed or 1
                        if not event.duration: event.duration = 60

                    print(f"=== PRIMARY LOGIC Complete for Event '{title}' ({event.id}) ===")


                # --- Teacher Processing (runs for EVERY row with a teacher) ---
                if row_data.get('Teacher Name') and not pd.isna(row_data.get('Teacher Name')):
                     print(f"Processing TEACHER '{row_data.get('Teacher Name')}' for Event '{title}' ({event.id}) (Row {row_index+1}, Simulcast: {is_simulcast})")
                     # Pass the correct 'is_simulcast' flag for the *current row*
                     process_teacher_for_event(row_data, event, is_simulcast=is_simulcast)


                # Commit changes potentially made in this iteration
                db.session.commit()
                if event_processed_in_this_row: # Count success if event logic ran
                     success_count += 1
                # How to count success if only teacher was processed? Add logic if needed.


            except Exception as e:
                 db.session.rollback() # Rollback on error for the specific row
                 error_count += 1
                 title_for_error = clean_string_value(row_data.get('Session Title', 'Unknown'))
                 errors.append(f"Error processing row {row_index + 1} for '{title_for_error}': {str(e)}")
                 current_app.logger.error(f"Import error processing row {row_index + 1} for '{title_for_error}': {e}", exc_info=True)

        print("\n--- Import Process Finished ---")
        return jsonify({
            'success': True,
            'successCount': success_count, # Note: Success count might need adjustment based on definition
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback() # Rollback any remaining transaction on overall failure
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
    if pd.isna(name) or not name:
        name = "Unknown School"
    
    # Ensure name is a string
    name = str(name).strip()
    
    timestamp = datetime.now(timezone.utc).strftime('%y%m%d')
    name_hash = hashlib.sha256(name.lower().encode()).hexdigest()[:8]
    base_id = f"VRT{timestamp}{name_hash}"
    
    # Ensure exactly 18 characters
    base_id = base_id[:18].ljust(18, '0')
    
    # Check if ID exists and append counter if needed
    counter = 1
    new_id = base_id
    while School.query.filter_by(id=new_id).first():
        counter_str = str(counter).zfill(2)
        new_id = (base_id[:-2] + counter_str)
        counter += 1
    
    return new_id

def get_or_create_school(name, district=None):
    """Get or create school by name with improved district handling"""
    try:
        if pd.isna(name) or not name:
            return None
            
        # Clean and standardize the school name
        name = str(name).strip()
        if not name:
            return None
            
        # Try to find existing school
        school = School.query.filter(
            func.lower(School.name) == func.lower(name)
        ).first()
        
        if not school:
            try:
                school = School(
                    id=generate_school_id(name),
                    name=name,
                    district_id=district.id if district else None,
                    normalized_name=name.lower(),
                    salesforce_district_id=district.salesforce_id if district and district.salesforce_id else None
                )
                db.session.add(school)
                db.session.flush()
            except Exception as e:
                current_app.logger.error(f"Error creating school {name}: {str(e)}")
                return None
        
        return school
        
    except Exception as e:
        current_app.logger.error(f"Error in get_or_create_school for {name}: {str(e)}")
        return None

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
