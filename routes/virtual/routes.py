import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime
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
        
        # Skip rows without dates or times unless it's a simulcast
        if not is_simulcast and (not row.get('Date') or not row.get('Time')):
            warning_count += 1
            errors.append(f"Row {success_count + warning_count + error_count}: Skipped - No date/time provided")
            return success_count, warning_count, error_count

        # Extract session ID from Session Link if available
        session_id = None
        if row.get('Session Link'):
            try:
                session_id = row['Session Link'].split('/')[-1]
            except Exception as e:
                current_app.logger.error(f"Error extracting session ID: {e}")

        # Check if event already exists by session ID
        existing_event = None
        if session_id:
            existing_event = Event.query.filter_by(session_id=session_id).first()

        if existing_event:
            event = existing_event
            current_app.logger.info(f"Updating existing event: {session_id}")
        else:
            event = Event()
            current_app.logger.info(f"Creating new event with session ID: {session_id}")
            
            # Convert date and time for new events
            if not is_simulcast:
                date_str = row.get('Date')
                time_str = row.get('Time')
                try:
                    # Parse date like "8/12" and add current year
                    date_parts = date_str.split('/')
                    current_year = datetime.now().year
                    full_date_str = f"{date_parts[0]}/{date_parts[1]}/{current_year} {time_str}"
                    event.start_date = datetime.strptime(full_date_str, '%m/%d/%Y %I:%M %p')
                    current_app.logger.debug(f"Parsed date/time: {event.start_date}")
                except ValueError as e:
                    errors.append(f"Row {success_count + warning_count + error_count}: Date/time parsing error - {str(e)}")
                    current_app.logger.error(f"Date parsing error: {e}")

            # Set event fields
            event.title = row.get('Session Title')
            event.session_id = session_id
            event.type = EventType.VIRTUAL_SESSION
            event.status = EventStatus.map_status(row.get('Status', ''))
            event.district_partner = row.get('District')
            event.registration_link = row.get('Session Link')
            
            # Handle presenter information
            if row.get('Presenter'):
                name_parts = row.get('Presenter').strip().split(' ', 1)
                if len(name_parts) >= 2:
                    first_name, last_name = name_parts[0], name_parts[1]
                    
                    # Try to find existing volunteer
                    volunteer = Volunteer.query.filter(
                        Volunteer.first_name == first_name,
                        Volunteer.last_name == last_name
                    ).first()

                    if not volunteer:
                        # Create new volunteer
                        volunteer = Volunteer(
                            first_name=first_name,
                            last_name=last_name,
                            organization_name=row.get('Organization')
                        )
                        db.session.add(volunteer)
                        db.session.flush()
                        current_app.logger.info(f"Created new volunteer: {first_name} {last_name}")

                    # Link volunteer to event
                    if volunteer not in event.volunteers:
                        event.volunteers.append(volunteer)

            db.session.add(event)
            success_count += 1

        # Handle teacher information
        if row.get('Teacher Name'):
            name_parts = row.get('Teacher Name').strip().split(' ', 1)
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[1]
                
                # Try to find existing volunteer (teacher)
                volunteer = Volunteer.query.filter(
                    Volunteer.first_name == first_name,
                    Volunteer.last_name == last_name
                ).first()

                if not volunteer:
                    # Create new volunteer (teacher)
                    volunteer = Volunteer(
                        first_name=first_name,
                        last_name=last_name,
                        organization_name=row.get('School Name')
                    )
                    db.session.add(volunteer)
                    db.session.flush()
                    current_app.logger.info(f"Created new teacher: {first_name} {last_name}")

                # Create participation record if it doesn't exist
                existing_participation = EventParticipation.query.filter_by(
                    volunteer_id=volunteer.id,
                    event_id=event.id
                ).first()

                if not existing_participation:
                    status = row.get('Status', 'Attended')
                    if status.lower() in ['teacher no-show', 'teacher cancelation']:
                        status = 'No Show'
                    elif status.lower() == 'simulcast':
                        status = 'Simulcast'
                    elif status.lower() == 'successfully completed':
                        status = 'Attended'
                    
                    participation = EventParticipation(
                        volunteer_id=volunteer.id,
                        event_id=event.id,
                        status=status,
                        delivery_hours=event.duration / 60 if event.duration else None
                    )
                    db.session.add(participation)
                    current_app.logger.info(f"Created participation record for {first_name} {last_name}")

        db.session.commit()

    except Exception as e:
        error_count += 1
        errors.append(f"Row {success_count + warning_count + error_count}: {str(e)}")
        current_app.logger.error(f"Error processing row: {str(e)}", exc_info=True)
        db.session.rollback()

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

@virtual_bp.route('/purge', methods=['GET', 'POST'])
@login_required
def purge_virtual():
    try:
        # Only delete events that are virtual sessions
        deleted_count = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).delete()
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully purged {deleted_count} virtual sessions',
            'count': deleted_count
        })
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        current_app.logger.error("Purge failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def clean_name(name):
    """Standardize and clean name fields"""
    if not name or pd.isna(name):
        return None, None
    
    # Remove special characters and extra spaces
    name = re.sub(r'[^\w\s-]', '', str(name))
    name = ' '.join(name.split())
    
    # Split into first and last name
    parts = name.split(' ', 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), None

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
            year = datetime.now().year
            # If month is less than current month, assume next year
            if month < datetime.now().month:
                year += 1
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

@virtual_bp.route('/import-sheet', methods=['POST'])
@login_required
def import_sheet():
    try:
        sheet_id = getenv('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("Google Sheet ID not configured")
        
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url, skiprows=5)
        
        success_count = warning_count = error_count = 0
        errors = []
        
        # Group by unique events
        event_groups = df.groupby(['Session Title', 'Date', 'Time'])
        
        for (title, date_str, time_str), group in event_groups:
            try:
                with db.session.no_autoflush:
                    if pd.isna(title) or not title.strip():
                        warning_count += 1
                        errors.append(f"Skipped: Missing title for date {date_str}")
                        continue
                    
                    # Parse datetime
                    event_datetime = parse_datetime(date_str, time_str)
                    if not event_datetime:
                        warning_count += 1
                        errors.append(f"Skipped: Invalid date/time for {title}")
                        continue
                    
                    # Check for existing event
                    existing_event = Event.query.filter(
                        func.lower(Event.title) == func.lower(title.strip()),
                        func.date(Event.start_date) == event_datetime.date(),
                        Event.type == EventType.VIRTUAL_SESSION
                    ).first()
                    
                    if existing_event:
                        event = existing_event
                        event.start_date = event_datetime
                        # Add history record for update
                        history = History(
                            event_id=event.id,
                            action='UPDATE',
                            summary=f'Updated virtual session: {title}',
                            activity_type='Virtual Session Update',
                            activity_date=datetime.now(),
                            activity_status='Completed'
                        )
                        db.session.add(history)
                    else:
                        event = Event(
                            title=clean_string_value(title),
                            start_date=event_datetime,
                            type=EventType.VIRTUAL_SESSION,
                            status=EventStatus.map_status(clean_status(group.iloc[0].get('Status')))
                        )
                        db.session.add(event)
                    
                    # Process each row in group (multiple teachers/presenters)
                    for _, row in group.iterrows():
                        # Process teacher
                        if not pd.isna(row.get('Teacher Name')):
                            first_name, last_name = clean_name(row['Teacher Name'])
                            if first_name and last_name:
                                school_name = clean_string_value(row.get('School Name'))
                                district_name = clean_string_value(row.get('District'))  # Get district from data
                                
                                # Get or create school with district
                                if school_name:
                                    school = School.query.filter(
                                        func.lower(School.name) == func.lower(school_name)
                                    ).first()
                                    
                                    if not school:
                                        # Get or create district
                                        district = get_or_create_district(district_name)
                                        
                                        school = School(
                                            name=school_name,
                                            normalized_name=school_name.lower(),
                                            district_id=district.id  # Set the district_id
                                        )
                                        db.session.add(school)
                                        db.session.flush()
                                
                                # Create or update teacher
                                teacher = Teacher.query.filter(
                                    func.lower(Teacher.first_name) == func.lower(first_name),
                                    func.lower(Teacher.last_name) == func.lower(last_name)
                                ).first()
                                
                                if not teacher:
                                    teacher = Teacher(
                                        first_name=first_name,
                                        last_name=last_name,
                                        school_id=school.id if school else None
                                    )
                                    db.session.add(teacher)
                                    db.session.flush()
                        
                        # Process presenter
                        if not pd.isna(row.get('Presenter')):
                            first_name, last_name = clean_name(row['Presenter'])
                            if first_name and last_name:
                                org_name = clean_string_value(row.get('Organization'))
                                
                                # Initialize org variable
                                org = None
                                
                                # Get or create organization if name exists
                                if org_name:
                                    org = Organization.query.filter(
                                        func.lower(Organization.name) == func.lower(org_name)
                                    ).first()
                                    
                                    if not org:
                                        org = Organization(
                                            name=org_name,
                                            type='Business'
                                        )
                                        db.session.add(org)
                                        db.session.flush()  # Ensure org has ID
                                
                                # Create or update volunteer
                                volunteer = Volunteer.query.filter(
                                    func.lower(Volunteer.first_name) == func.lower(first_name),
                                    func.lower(Volunteer.last_name) == func.lower(last_name)
                                ).first()
                                
                                if not volunteer:
                                    volunteer = Volunteer(
                                        first_name=first_name,
                                        last_name=last_name
                                    )
                                    db.session.add(volunteer)
                                    db.session.flush()
                                
                                # Only create VolunteerOrganization if org exists
                                if org and volunteer:
                                    # Check if relationship already exists
                                    vol_org = VolunteerOrganization.query.filter_by(
                                        volunteer_id=volunteer.id,
                                        organization_id=org.id
                                    ).first()
                                    
                                    if not vol_org:
                                        vol_org = VolunteerOrganization(
                                            volunteer_id=volunteer.id,
                                            organization_id=org.id,
                                            role='Presenter',
                                            status='Current'
                                        )
                                        db.session.add(vol_org)
                    
                    db.session.commit()
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing {title}: {str(e)}")
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
