import traceback
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime
from flask import current_app
from models.district_model import District
from models.event import db, Event, EventType
from models.organization import Organization
from models.school_model import School
from models.teacher import Teacher
from models.volunteer import Volunteer, EventParticipation
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs
from os import getenv

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
            event.status = row.get('Status', 'Draft')
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

@virtual_bp.route('/import-sheet', methods=['POST'])
@login_required
def import_sheet():
    try:
        sheet_id = getenv('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("Google Sheet ID not configured")
        
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        # Skip the first 5 rows which contain color coding information
        df = pd.read_csv(csv_url, skiprows=5)

        success_count = 0
        warning_count = 0
        error_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                row_dict = row.to_dict()
                
                # Skip completely empty rows
                if pd.isna(row_dict.get('Status')) and pd.isna(row_dict.get('Date')):
                    continue

                # Create Event object for each row
                event = Event()
                event.type = EventType.VIRTUAL_SESSION

                # Handle status
                status = str(row_dict.get('Status', '')).lower().strip()
                if status in ['teacher no-show', 'teacher cancelation']:
                    event.status = 'No Show'
                elif status == 'simulcast':
                    event.status = 'Simulcast'
                elif status == 'successfully completed':
                    event.status = 'Completed'
                else:
                    event.status = 'Draft'

                # Set basic event details
                event.title = row_dict.get('Session Title')
                event.district_partner = row_dict.get('District')
                event.registration_link = row_dict.get('Session Link')

                # Parse date and time if available
                date_str = str(row_dict.get('Date', '')).strip()
                time_str = str(row_dict.get('Time', '')).strip()
                if date_str and time_str and status != 'simulcast':
                    try:
                        date_parts = date_str.split('/')
                        current_year = datetime.now().year
                        full_date_str = f"{date_parts[0]}/{date_parts[1]}/{current_year} {time_str}"
                        event.start_date = datetime.strptime(full_date_str, '%m/%d/%Y %I:%M %p')
                    except Exception as e:
                        errors.append(f"Row {index + 2}: Date/time parsing error - {str(e)}")
                        continue

                # Handle presenter
                presenter_name = row_dict.get('Presenter', '').strip()
                if presenter_name:
                    name_parts = presenter_name.split(' ', 1)
                    if len(name_parts) >= 2:
                        first_name, last_name = name_parts[0], name_parts[1]
                        volunteer = Volunteer.query.filter(
                            Volunteer.first_name == first_name,
                            Volunteer.last_name == last_name
                        ).first() or Volunteer(
                            first_name=first_name,
                            last_name=last_name,
                            organization_name=row_dict.get('Organization')
                        )
                        if volunteer not in event.volunteers:
                            event.volunteers.append(volunteer)

                # Handle teacher
                teacher_name = row_dict.get('Teacher Name', '').strip()
                if teacher_name:
                    name_parts = teacher_name.split(' ', 1)
                    if len(name_parts) >= 2:
                        first_name, last_name = name_parts[0], name_parts[1]
                        teacher = Volunteer.query.filter(
                            Volunteer.first_name == first_name,
                            Volunteer.last_name == last_name
                        ).first() or Volunteer(
                            first_name=first_name,
                            last_name=last_name,
                            organization_name=row_dict.get('School Name')
                        )
                        
                        # Create participation record
                        participation = EventParticipation(
                            volunteer=teacher,
                            event=event,
                            status=event.status
                        )
                        db.session.add(participation)

                db.session.add(event)
                success_count += 1
                
                # Commit after each successful row
                db.session.commit()

            except Exception as row_error:
                error_count += 1
                errors.append(f"Row {index + 2}: Error processing row: {str(row_error)}")
                db.session.rollback()
                continue

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