"""
Events Routes Module
===================

This module provides all the route handlers for event management in the VMS system.
It includes functionality for listing, creating, editing, viewing, and importing events,
as well as syncing data with Salesforce.

Key Features:
- Event CRUD operations (Create, Read, Update, Delete)
- Advanced filtering and sorting of events
- Salesforce integration for data synchronization
- CSV import functionality for bulk data loading
- Volunteer and student participation tracking
- Skills management and association

Main Endpoints:
- /events: List all events with filtering and pagination
- /events/add: Create new events
- /events/view/<id>: View detailed event information
- /events/edit/<id>: Edit existing events
- /events/import: Import events from CSV or Salesforce
- /events/sync-*: Various sync endpoints for Salesforce data

Dependencies:
- Salesforce API integration via simple_salesforce
- Event, Student, School, District, Skill, and Volunteer models
- Various utility functions from routes.utils
"""

import csv
import os
from flask import Blueprint, app, jsonify, request, render_template, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from config import Config
from forms import EventForm
from models import db
from models.district_model import District
from models.event import Event, EventType, EventStatus, EventFormat
from models.volunteer import EventParticipation, Skill, Volunteer
from datetime import datetime, timedelta
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload

from routes.utils import DISTRICT_MAPPINGS, map_cancellation_reason, map_event_format, map_session_type, parse_date, parse_event_skills
from models.school_model import School
from models.event import EventTeacher
from models.student import Student
from models.event import EventStudentParticipation
from models.teacher import Teacher
from models.pathways import pathway_events

# Create blueprint for events functionality
events_bp = Blueprint('events', __name__)

def process_event_row(row, success_count, error_count, errors):
    """
    Process a single event row from CSV/Salesforce data
    
    This function handles the processing of individual event records from
    either CSV files or Salesforce API responses. It validates required
    fields, creates or updates Event objects, and handles relationships
    with districts, schools, and skills.
    
    Args:
        row (dict): Event data from CSV or Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages
        
    Returns:
        tuple: Updated (success_count, error_count)
    """
    try:
        # Get initial data to check
        parent_account = row.get('Parent_Account__c')
        district_name = row.get('District__c')
        school_id = row.get('School__c')
        
        # Skip events missing all three identifiers
        if not any([parent_account, district_name, school_id]):
            event_id = row.get('Id', 'unknown')
            event_name = row.get('Name', 'unknown')
            errors.append(f"Skipping event {event_id} ({event_name}): Missing all required identifiers (Parent_Account__c, District__c, and School__c)")
            return success_count, error_count + 1

        # Get or create event
        event_id = row.get('Id')
        event = Event.query.filter_by(salesforce_id=event_id).first()
        is_new = event is None
        
        if not event:
            # Ensure required fields for new events
            if not row.get('Name'):  # Title is required by validation
                raise ValueError("Event name/title is required")
                
            event = Event(
                title=row.get('Name', '').strip(),  # Ensure title is not empty
                salesforce_id=event_id
            )
            db.session.add(event)
        
        # Update event fields
        if row.get('Name'):  # Only update if name exists
            event.title = row.get('Name').strip()
        
        # Update basic event fields
        event.type = map_session_type(row.get('Session_Type__c', ''))
        event.format = map_event_format(row.get('Format__c', ''))
        event.start_date = parse_date(row.get('Start_Date_and_Time__c')) or datetime(2000, 1, 1)
        event.end_date = parse_date(row.get('End_Date_and_Time__c')) or datetime(2000, 1, 1)
        event.status = row.get('Session_Status__c', 'Draft')
        event.location = row.get('Location_Information__c', '')
        event.description = row.get('Description__c', '')
        event.cancellation_reason = map_cancellation_reason(row.get('Cancellation_Reason__c'))
        event.participant_count = int(float(row.get('Non_Scheduled_Students_Count__c', 0)) if row.get('Non_Scheduled_Students_Count__c') is not None else 0)
        event.additional_information = row.get('Additional_Information__c', '')
        event.session_host = row.get('Session_Host__c', '')
        
        # Handle numeric fields
        def safe_convert_to_int(value, default=0):
            if value is None:
                return default
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default

        event.total_requested_volunteer_jobs = safe_convert_to_int(row.get('Total_Requested_Volunteer_Jobs__c'))
        event.available_slots = safe_convert_to_int(row.get('Available_Slots__c'))
        
        # Handle School relationship (using Salesforce ID)
        school_district = None
        if school_id:
            school = School.query.get(school_id)
            if school:
                event.school = school_id  # Store the Salesforce ID
                school_district = school.district

        # Handle District relationship
        # If District__c is empty, use Parent_Account__c instead
        if not district_name and parent_account:
            district_name = parent_account

        # Try to get the district
        district = None
        if district_name and district_name in DISTRICT_MAPPINGS:
            mapped_name = DISTRICT_MAPPINGS[district_name]
            district = District.query.filter_by(name=mapped_name).first()

        # Clear and reassign districts if we have a valid district to assign
        if district or school_district:
            event.districts = []  # Clear existing districts
            if school_district:
                event.districts.append(school_district)
            if district and district not in event.districts:
                event.districts.append(district)

        # Store original district name for reference
        event.district_partner = district_name if district_name else None

        # Handle skills
        skills_covered = parse_event_skills(row.get('Legacy_Skill_Covered_for_the_Session__c', ''))
        skills_needed = parse_event_skills(row.get('Legacy_Skills_Needed__c', ''))
        requested_skills = parse_event_skills(row.get('Requested_Skills__c', ''))
        
        # Combine all skills and remove duplicates
        all_skills = set(skills_covered + skills_needed + requested_skills)
        
        # Get existing skills to avoid duplicates
        existing_skill_names = {skill.name for skill in event.skills}
        
        # Only process new skills
        new_skill_names = all_skills - existing_skill_names
        for skill_name in new_skill_names:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.session.add(skill)
            if skill not in event.skills:
                event.skills.append(skill)

        db.session.flush()  # Flush to catch validation errors early
        return success_count + (1 if is_new else 0), error_count
            
    except Exception as e:
        db.session.rollback()
        errors.append(f"Error processing event {row.get('Id', 'unknown')}: {str(e)}")
        return success_count, error_count + 1
    
def process_participation_row(row, success_count, error_count, errors):
    """
    Process a single participation row from CSV data
    
    This function handles volunteer participation records from CSV imports
    or Salesforce sync operations. It creates EventParticipation records
    linking volunteers to events with status and delivery hours.
    
    Args:
        row (dict): Participation data from CSV or Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages
        
    Returns:
        tuple: Updated (success_count, error_count)
    """
    try:
        # Check if participation already exists
        existing = EventParticipation.query.filter_by(salesforce_id=row['Id']).first()
        if existing:
            return success_count, error_count  # Skip existing records
        
        # Find the volunteer and event by their Salesforce IDs
        volunteer = Volunteer.query.filter_by(salesforce_individual_id=row['Contact__c']).first()
        event = Event.query.filter_by(salesforce_id=row['Session__c']).first()
                    
        if not volunteer or not event:
            error_msg = f"Could not find volunteer or event for participation {row['Id']}"
            errors.append(error_msg)
            return success_count, error_count + 1
        
        # Create new participation record
        participation = EventParticipation(
            volunteer_id=volunteer.id,
            event_id=event.id,
            status=row['Status__c'],
            delivery_hours=float(row['Delivery_Hours__c']) if row['Delivery_Hours__c'] else None,
            salesforce_id=row['Id']
        )
        
        db.session.add(participation)
        # print(f"Successfully added participation: {row['Id']}")  # Debug log
        return success_count + 1, error_count

    except Exception as e:
        error_msg = f"Error processing participation row: {str(e)}"
        print(error_msg)  # Debug log
        db.session.rollback()
        errors.append(error_msg)
        return success_count, error_count + 1

def process_student_participation_row(row, success_count, error_count, errors):
    """
    Process a single student participation row from Salesforce data
    
    This function handles student participation records from Salesforce sync
    operations. It creates EventStudentParticipation records linking students
    to events with status, delivery hours, and age group information.
    
    Args:
        row (dict): Student participation data from Salesforce
        success_count (int): Running count of successful operations
        error_count (int): Running count of failed operations
        errors (list): List to collect error messages
        
    Returns:
        tuple: Updated (success_count, error_count)
    """
    try:
        event_sf_id = row.get('Session__c')
        student_contact_sf_id = row.get('Contact__c') # Salesforce Contact ID for the student
        participation_sf_id = row.get('Id') # Salesforce Session_Participant__c ID
        status = row.get('Status__c')
        delivery_hours_str = row.get('Delivery_Hours__c')
        age_group = row.get('Age_Group__c')

        # Validate required Salesforce IDs
        if not all([event_sf_id, student_contact_sf_id, participation_sf_id]):
             errors.append(f"Skipping student participation {participation_sf_id or 'unknown'}: Missing required Salesforce IDs (Session__c, Contact__c, Id)")
             return success_count, error_count + 1

        # --- Find Event ---
        event = Event.query.filter_by(salesforce_id=event_sf_id).first()
        if not event:
            errors.append(f"Event with Salesforce ID {event_sf_id} not found for participation {participation_sf_id}")
            return success_count, error_count + 1

        # --- Find Student ---
        # Student inherits from Contact, so we query Student via Contact's salesforce_individual_id
        student = Student.query.filter(Student.salesforce_individual_id == student_contact_sf_id).first()
        if not student:
             # If a student record doesn't exist in your DB for the given SF Contact ID,
             # we log an error. You could enhance this later to create the student if needed.
             errors.append(f"Student with Salesforce Contact ID {student_contact_sf_id} not found for participation {participation_sf_id}")
             return success_count, error_count + 1

        # --- Check for existing participation record ---
        existing_participation = EventStudentParticipation.query.filter_by(salesforce_id=participation_sf_id).first()

        if existing_participation:
            # Skip if this specific Salesforce participation record already exists in the DB
            # Optionally, you could add logic here to update the existing record if needed.
            return success_count, error_count
        else:
            # --- Create New Participation Record ---
            try:
                delivery_hours = float(delivery_hours_str) if delivery_hours_str else None
            except (ValueError, TypeError):
                delivery_hours = None # Gracefully handle non-numeric delivery hours

            new_participation = EventStudentParticipation(
                event_id=event.id,
                student_id=student.id, # Use the primary key of the found student
                status=status,
                delivery_hours=delivery_hours,
                age_group=age_group,
                salesforce_id=participation_sf_id # Store the unique SF participation ID
            )
            db.session.add(new_participation)
            # You could add db.session.flush() here if you want to catch potential DB errors immediately
            # print(f"Successfully queued addition of student participation: SF ID {participation_sf_id} for Event {event.id}, Student {student.id}")
            return success_count + 1, error_count

    except Exception as e:
        db.session.rollback() # Rollback the transaction for this row on error
        errors.append(f"Error processing student participation {row.get('Id', 'unknown')}: {str(e)}")
        # Consider logging the full traceback for debugging complex errors
        # import traceback
        # print(traceback.format_exc())
        return success_count, error_count + 1

@events_bp.route('/events')
@login_required
def events():
    """
    List all events with filtering, sorting, and pagination
    
    This endpoint provides a comprehensive view of all events in the system
    with advanced filtering capabilities, sorting options, and pagination.
    
    Query Parameters:
    - page: Page number for pagination
    - per_page: Items per page (10, 25, 50, 100)
    - search_title: Text search in event titles
    - event_type: Filter by event type
    - status: Filter by event status
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - sort_by: Column to sort by (title, type, start_date)
    - sort_direction: Sort direction (asc, desc)
    
    Returns:
        Rendered template with filtered and paginated events
    """
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Validate per_page value
    allowed_per_page = [10, 25, 50, 100]
    if per_page not in allowed_per_page:
        per_page = 25  # fallback to default if invalid value

    # Create current_filters dictionary
    current_filters = {
        'search_title': request.args.get('search_title', '').strip(),
        'event_type': request.args.get('event_type', ''),
        'status': request.args.get('status', ''),
        'start_date': request.args.get('start_date', ''),
        'end_date': request.args.get('end_date', ''),
        'per_page': per_page
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Get sort parameters
    sort_by = request.args.get('sort_by', 'start_date')  # default sort by start_date
    sort_direction = request.args.get('sort_direction', 'desc')  # default direction
    
    # Add sort parameters to current_filters
    current_filters['sort_by'] = sort_by
    current_filters['sort_direction'] = sort_direction

    # Build query
    query = Event.query

    # Apply filters
    if current_filters.get('search_title'):
        search_term = f"%{current_filters['search_title']}%"
        query = query.filter(Event.title.ilike(search_term))

    if current_filters.get('event_type'):
        try:
            event_type = EventType[current_filters['event_type'].upper()]
            query = query.filter(Event.type == event_type)
        except KeyError:
            flash(f"Invalid event type: {current_filters['event_type']}", 'warning')

    if current_filters.get('status'):
        status = current_filters['status']
        # Handle case where imported status doesn't match enum
        status_mapping = {
            'Completed': 'COMPLETED',
            'Confirmed': 'CONFIRMED',
            'Cancelled': 'CANCELLED',
            'Requested': 'REQUESTED',
            'Draft': 'DRAFT',
            'Published': 'PUBLISHED'
        }
        query = query.filter(Event.status == status)

    if current_filters.get('start_date'):
        try:
            start_date = datetime.strptime(current_filters['start_date'], '%Y-%m-%d')
            query = query.filter(Event.start_date >= start_date)
        except ValueError:
            flash('Invalid start date format', 'warning')

    if current_filters.get('end_date'):
        try:
            end_date = datetime.strptime(current_filters['end_date'], '%Y-%m-%d')
            # Add 23:59:59 to include the entire end date
            end_date = end_date + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(Event.start_date <= end_date)
        except ValueError:
            flash('Invalid end date format', 'warning')

    # Apply sorting
    sort_column = getattr(Event, sort_by, Event.start_date)
    if sort_direction == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Get all event types for the dropdown
    event_types = [(t.name.lower(), t.name.replace('_', ' ').title()) 
                  for t in EventType]

    # Define valid statuses (matching exactly what's in the database)
    statuses = [
        ('Completed', 'Completed'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Requested', 'Requested'),
        ('Draft', 'Draft'),
        ('Published', 'Published')
    ]

    return render_template('events/events.html',
                         events=pagination.items,
                         pagination=pagination,
                         current_filters=current_filters,
                         event_types=event_types,
                         statuses=statuses)

@events_bp.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    """
    Create a new event
    
    GET: Display the event creation form
    POST: Process form submission and create new event
    
    Returns:
        GET: Rendered form template
        POST: Redirect to event view page on success
    """
    form = EventForm()
    
    if form.validate_on_submit():
        try:
            print("Form validation successful")  # Debug
            print(f"Form data: {form.data}")  # Debug
            
            # Create new event from form data
            event = Event(
                title=form.title.data,
                type=EventType(form.type.data),
                format=EventFormat(form.format.data),
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                location=form.location.data or '',
                status=EventStatus(form.status.data),
                description=form.description.data or '',
                volunteers_needed=form.volunteers_needed.data or 0
            )
            
            print(f"Created event: {event}")  # Debug
            
            db.session.add(event)
            db.session.commit()
            
            flash('Event added successfully!', 'success')
            return redirect(url_for('events.view_event', id=event.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding event: {str(e)}")  # Debug
            flash(f'Error adding event: {str(e)}', 'danger')
    else:
        # Print form validation errors for debugging
        if request.method == 'POST':
            print(f"Form validation failed: {form.errors}")  # Debug
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
    
    return render_template('events/add_event.html', form=form)

@events_bp.route('/events/view/<int:id>')
@login_required
def view_event(id):
    """
    View detailed information about a specific event
    
    This endpoint displays comprehensive event information including
    participation details, skills, and related data.
    
    Args:
        id (int): Event ID to view
        
    Returns:
        Rendered template with event details
        
    Raises:
        404: If event not found
    """
    event = db.session.get(Event, id)
    if not event:
        abort(404)
    
    # Set default dates if None
    if event.start_date is None:
        event.start_date = datetime.now()
    if event.end_date is None:
        event.end_date = datetime.now()
    
    # Get volunteer participations with volunteers
    # Use joinedload to efficiently load volunteers
    volunteer_participations = EventParticipation.query.options(
        joinedload(EventParticipation.volunteer)
    ).filter_by(event_id=id).all()

    # Get all event teachers with their statuses
    # Use joinedload to efficiently load teachers
    event_teachers = EventTeacher.query.options(
        joinedload(EventTeacher.teacher).joinedload(Teacher.school)
    ).filter_by(event_id=id).all()

    # --- NEW: Get student participations with students ---
    # Use joinedload to efficiently load students
    student_participations = EventStudentParticipation.query.options(
        joinedload(EventStudentParticipation.student)
    ).filter_by(event_id=id).all()
    # --- End NEW ---

    # Group volunteer participations by status
    participation_stats = {
        'Registered': [],
        'Attended': [],
        'No Show': [],
        'Cancelled': []
    }
    
    for participation in volunteer_participations:
        # Ensure volunteer exists before processing
        if participation.volunteer:
            status = participation.status
            if status in participation_stats:
                participation_stats[status].append({
                    'volunteer': participation.volunteer,
                    'delivery_hours': participation.delivery_hours
                })
    
    return render_template(
        'events/view.html',
        event=event,
        volunteer_count=len(event.volunteers), # This might be slightly inaccurate if participations exist for deleted volunteers
        participation_stats=participation_stats,
        # volunteers=event.volunteers, # volunteers association might not be needed if using participation_stats
        event_teachers=event_teachers,
        student_participations=student_participations # Pass student data to template
    )

@events_bp.route('/events/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_event(id):
    """
    Edit an existing event
    
    GET: Display the event edit form pre-populated with current data
    POST: Process form submission and update event
    
    Args:
        id (int): Event ID to edit
        
    Returns:
        GET: Rendered form template
        POST: Redirect to event view page on success
        
    Raises:
        404: If event not found
    """
    event = db.session.get(Event, id)
    if not event:
        abort(404)
    
    form = EventForm()
    
    if form.validate_on_submit():
        try:
            print("Edit form validation successful")  # Debug
            print(f"Form data: {form.data}")  # Debug
            
            # Update event from form data
            form.populate_obj(event)
            
            # Handle enum conversions
            event.type = EventType(form.type.data)
            event.format = EventFormat(form.format.data)
            event.status = EventStatus(form.status.data)
            
            print(f"Updated event: {event}")  # Debug
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('events.view_event', id=event.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating event: {str(e)}")  # Debug
            flash(f'Error updating event: {str(e)}', 'danger')
    else:
        # Pre-populate form with event data for GET requests
        if request.method == 'GET':
            form.title.data = event.title
            form.type.data = event.type.value if event.type else ''
            form.format.data = event.format.value if event.format else ''
            form.start_date.data = event.start_date
            form.end_date.data = event.end_date
            form.location.data = event.location
            form.status.data = event.status.value if event.status else ''
            form.description.data = event.description
            form.volunteers_needed.data = event.volunteers_needed
        
        # Print form validation errors for debugging
        if request.method == 'POST':
            print(f"Form validation failed: {form.errors}")  # Debug
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
    
    return render_template('events/edit.html', event=event, form=form)
    
@events_bp.route('/events/import', methods=['GET', 'POST'])
@login_required
def import_events():
    """
    Import events from CSV files or Salesforce
    
    This endpoint handles both file uploads and Salesforce synchronization.
    It supports importing events and participation data with progress
    tracking and error reporting.
    
    GET: Display import interface
    POST: Process import (CSV file or Salesforce sync)
    
    Returns:
        GET: Rendered import template
        POST: JSON response with import results
    """
    if request.method == 'GET':
        return render_template('events/import.html')

    try:
        success_count = 0
        error_count = 0
        errors = []

        # Determine import type
        import_type = request.json.get('importType', 'events') if request.is_json else request.form.get('importType', 'events')

        # Select the appropriate process function
        process_func = process_event_row if import_type == 'events' else process_participation_row

        # Handle quickSync from Salesforce
        if request.is_json and request.json.get('quickSync'):
            try:
                print("Fetching data from Salesforce...")

                # Define Salesforce query
                salesforce_query = """
                SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c, 
                        End_Date_and_Time__c, Session_Status__c, Location_Information__c, 
                        Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c, 
                        District__c, Legacy_Skill_Covered_for_the_Session__c, 
                        Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
                        Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c,
                        Session_Host__c
                FROM Session__c
                ORDER BY Start_Date_and_Time__c ASC
                """

                # Connect to Salesforce
                sf = Salesforce(
                    username=Config.SF_USERNAME,
                    password=Config.SF_PASSWORD,
                    security_token=Config.SF_SECURITY_TOKEN,
                    domain='login'
                )

                # Execute the query
                result = sf.query_all(salesforce_query)
                sf_rows = result.get('records', [])

                # Process each row from Salesforce
                for row in sf_rows:
                    success_count, error_count = process_func(
                        row, success_count, error_count, errors
                    )
            except SalesforceAuthenticationFailed:
                return jsonify({
                    'success': False,
                    'message': 'Failed to authenticate with Salesforce'
                }), 401
            except Exception as e:
                print(f"Salesforce sync error: {str(e)}")
                return jsonify({'error': f'Salesforce sync error: {str(e)}'}), 500

        else:
            # Handle file upload as fallback
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be a CSV'}), 400

            # Read and process the CSV file
            content = file.stream.read().decode("UTF8", errors='replace').replace('\0', '')
            csv_data = csv.DictReader(content.splitlines())
            for row in csv_data:
                success_count, error_count = process_func(
                    row, success_count, error_count, errors
                )

        # Commit changes to the database
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'successCount': success_count,
                'errorCount': error_count,
                'errors': errors
            })
        except Exception as e:
            db.session.rollback()
            print(f"Database commit error: {str(e)}")
            return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        print(f"Import error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@events_bp.route('/events/purge', methods=['POST'])
@login_required
def purge_events():
    """
    Purge all events and related data (Admin only)
    
    This endpoint completely removes all events and related data from the database.
    It should only be used for testing or complete data reset scenarios.
    
    Returns:
        JSON response indicating success or failure
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # First delete all event participations
        EventParticipation.query.delete()
        
        # Delete student participations
        EventStudentParticipation.query.delete()
        
        # Delete event-teacher associations
        EventTeacher.query.delete()
        
        # Delete pathway-event associations
        db.session.execute(pathway_events.delete())
        
        # Delete event-district associations
        db.session.execute(db.text('DELETE FROM event_districts'))
        
        # Delete event-skill associations
        db.session.execute(db.text('DELETE FROM event_skills'))
        
        # Then delete all events
        Event.query.delete()
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    
@events_bp.route('/events/sync-participants')
@login_required
def sync_participants():
    """
    Sync participant data from CSV file
    
    This endpoint reads participant data from a CSV file and creates
    EventParticipation records linking volunteers to events.
    
    Returns:
        JSON response with sync results
    """
    try:
        csv_file = os.path.join('data', 'Session_Participant__c - volunteers.csv')
        if not os.path.exists(csv_file):
            return jsonify({'error': f'CSV file not found: {csv_file}'}), 404

        success_count = 0
        error_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                success_count, error_count = process_participation_row(
                    row, success_count, error_count, errors
                )

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} participants with {error_count} errors',
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in sync_participants: {str(e)}")
        return jsonify({'error': str(e)}), 500

@events_bp.route('/events/sync-events', methods=['POST'])
@login_required
def sync_events():
    """
    Sync events from CSV file
    
    This endpoint reads event data from a CSV file and creates or updates
    Event records in the database.
    
    Returns:
        JSON response with sync results
    """
    try:
        # Get absolute path using application root
        csv_file = os.path.join(app.root_path, 'data', 'Sessions.csv')
        print(f"CSV file path: {csv_file}")
        if not os.path.exists(csv_file):
            return jsonify({'error': f'CSV file not found: {csv_file}'}), 404

        success_count = 0
        error_count = 0
        errors = []

        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                success_count, error_count = process_event_row(row, success_count, error_count, errors)

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} events with {error_count} errors',
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in sync_events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@events_bp.route('/events/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_event(id):
    """
    Delete an event (Admin only)
    
    This endpoint removes an event and all its associated data from the database.
    
    Args:
        id (int): Event ID to delete
        
    Returns:
        JSON response indicating success or failure
        
    Raises:
        404: If event not found
    """
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        event = db.session.get(Event, id)
        if not event:
            abort(404)
        
        # First delete all participations
        EventParticipation.query.filter_by(event_id=id).delete()
        
        # Then delete the event
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@events_bp.route('/api/skills/find-or-create', methods=['POST'])
@login_required
def find_or_create_skill():
    """
    Find or create a skill by name
    
    This endpoint provides an API for finding existing skills or creating
    new ones. It's typically used by the frontend for dynamic skill management.
    
    Returns:
        JSON response with skill information
    """
    try:
        data = request.get_json()
        skill_name = data.get('name').strip()
        
        # Look for existing skill
        skill = Skill.query.filter(func.lower(Skill.name) == func.lower(skill_name)).first()
        
        # Create new skill if it doesn't exist
        if not skill:
            skill = Skill(name=skill_name)
            db.session.add(skill)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'skill': {
                'id': skill.id,
                'name': skill.name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@events_bp.route('/events/import-from-salesforce', methods=['POST'])
@login_required
def import_events_from_salesforce():
    """
    Import events and participants from Salesforce
    
    This endpoint performs a comprehensive import of both events and
    participant data from Salesforce. It handles authentication, data
    processing, and error reporting.
    
    Returns:
        JSON response with import results and statistics
    """
    try:
        print("Fetching data from Salesforce...")
        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # First query: Get events
        events_query = """
        SELECT Id, Name, Session_Type__c, Format__c, Start_Date_and_Time__c, 
            End_Date_and_Time__c, Session_Status__c, Location_Information__c, 
            Description__c, Cancellation_Reason__c, Non_Scheduled_Students_Count__c, 
            District__c, School__c, Legacy_Skill_Covered_for_the_Session__c, 
            Legacy_Skills_Needed__c, Requested_Skills__c, Additional_Information__c,
            Total_Requested_Volunteer_Jobs__c, Available_Slots__c, Parent_Account__c,
            Session_Host__c
        FROM Session__c
        WHERE Session_Status__c != 'Draft' AND Session_Type__c != 'Connector Session'
        ORDER BY Start_Date_and_Time__c DESC
        """

        # Execute events query
        events_result = sf.query_all(events_query)
        events_rows = events_result.get('records', [])

        status_counts = {}
        
        # Process events
        for row in events_rows:
            status = row.get('Session_Status__c', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            success_count, error_count = process_event_row(
                row, success_count, error_count, errors
            )
        
        print("\nEvents by status:")
        for status, count in status_counts.items():
            print(f"{status}: {count}")

        # Second query: Get participants
        participants_query = """
        SELECT 
            Id,
            Name,
            Contact__c,
            Session__c,
            Status__c,
            Delivery_Hours__c,
            Age_Group__c,
            Email__c,
            Title__c
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Volunteer'
        """

        # Execute participants query
        participants_result = sf.query_all(participants_query)
        participant_rows = participants_result.get('records', [])

        # Process participants
        participant_success = 0
        participant_error = 0
        for row in participant_rows:
            participant_success, participant_error = process_participation_row(
                row, participant_success, participant_error, errors
            )

        # Commit all changes
        db.session.commit()
        
        # Print summary and errors
        print(f"\nSuccessfully processed {success_count} events and {participant_success} participants with {error_count + participant_error} total errors")
        if errors:
            print("\nErrors encountered:")
            for error in errors[:50]:  # Only print first 50 errors
                print(f"- {error}")
        
        # Truncate errors list to 50 items
        truncated_errors = errors[:50]
        if len(errors) > 50:
            truncated_errors.append(f"... and {len(errors) - 50} more errors")

        return jsonify({
            'success': True,
            'message': (f'Successfully processed {success_count} events and '
                       f'{participant_success} participants with '
                       f'{error_count + participant_error} total errors'),
            'errors': truncated_errors
        })

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@events_bp.route('/events/sync-student-participants', methods=['POST'])
@login_required
def sync_student_participants():
    """
    Sync student participation data from Salesforce
    
    This endpoint fetches student participation data from Salesforce and
    creates EventStudentParticipation records in the local database.
    
    Returns:
        JSON response with sync results and statistics
    """
    try:
        print("Fetching student participation data from Salesforce...")
        success_count = 0
        error_count = 0
        errors = []

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # Query for Student participants
        participants_query = """
        SELECT
            Id,
            Name,
            Contact__c,
            Session__c,
            Status__c,
            Delivery_Hours__c,
            Age_Group__c,
            Email__c,
            Title__c
        FROM Session_Participant__c
        WHERE Participant_Type__c = 'Student'
        ORDER BY Session__c, Name
        """

        # Execute participants query
        participants_result = sf.query_all(participants_query)
        participant_rows = participants_result.get('records', [])

        print(f"Found {len(participant_rows)} student participation records in Salesforce.")

        # Process participants
        for row in participant_rows:
            success_count, error_count = process_student_participation_row(
                row, success_count, error_count, errors
            )

        # Commit changes (will only commit if association logic is added and adds to session)
        db.session.commit()

        # Print summary and errors
        print(f"\nSuccessfully processed {success_count} student participations with {error_count} total errors")
        if errors:
            print("\nErrors encountered:")
            for error in errors[:50]:  # Only print first 50 errors
                print(f"- {error}")

        return jsonify({
            'success': True,
            'message': f'Processed {success_count} student participations with {error_count} errors.',
            'successCount': success_count,
            'errorCount': error_count,
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Error in sync_student_participants: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
