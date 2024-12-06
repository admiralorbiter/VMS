import csv
import os
from flask import Blueprint, app, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required
from config import Config
from models import db
from models.event import Event, EventType, EventStatus
from models.volunteer import EventParticipation, Skill, Volunteer
from datetime import datetime, timedelta
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy.sql import func

from routes.utils import DISTRICT_MAPPINGS, get_or_create_district, map_cancellation_reason, map_event_format, map_session_type, parse_date, parse_event_skills

events_bp = Blueprint('events', __name__)

def process_event_row(row, success_count, error_count, errors):
    """Process a single event row from CSV/Salesforce data"""
    try:
        # Check if event exists by salesforce_id
        event = None
        if row.get('Id'):
            event = Event.query.filter_by(salesforce_id=row['Id']).first()
        
        # Track if this is an update or new record
        is_new = event is None
        
        # If event doesn't exist, create new one
        if not event:
            event = Event()
            db.session.add(event)
        
        # Update event fields (handles both new and existing events)
        event.salesforce_id = row.get('Id', '').strip()
        event.title = row.get('Name', '').strip()
        event.type = map_session_type(row.get('Session_Type__c', ''))
        event.format = map_event_format(row.get('Format__c', ''))
        event.start_date = parse_date(row.get('Start_Date_and_Time__c')) or datetime(2000, 1, 1)
        event.end_date = parse_date(row.get('End_Date_and_Time__c')) or datetime(2000, 1, 1)
        event.status = row.get('Session_Status__c', 'Draft')
        event.location = row.get('Location_Information__c', '')
        event.description = row.get('Description__c', '')
        event.cancellation_reason = map_cancellation_reason(row.get('Cancellation_Reason__c'))
        event.participant_count = int(row.get('Participant_Count_0__c', 0))
        event.last_sync_date = datetime.now()  # Add this field to track last sync

        # Handle district
        district_name = row.get('District__c')
        if district_name and district_name in DISTRICT_MAPPINGS:
            district = get_or_create_district(DISTRICT_MAPPINGS[district_name])
            if district not in event.districts:
                event.districts.append(district)

        # Handle skills
        skills_covered = parse_event_skills(row.get('Legacy_Skill_Covered_for_the_Session__c', ''))
        skills_needed = parse_event_skills(row.get('Legacy_Skills_Needed__c', ''))
        requested_skills = parse_event_skills(row.get('Requested_Skills__c', ''))
        
        # Combine all skills
        all_skills = set(skills_covered + skills_needed + requested_skills)
        
        # Clear existing skills and add new ones
        event.skills = []
        for skill_name in all_skills:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.session.add(skill)
            event.skills.append(skill)

        return success_count + (1 if is_new else 0), error_count
            
    except Exception as e:
        db.session.rollback()
        print(f"Error processing event row: {str(e)}")
        errors.append(f"Error processing row: {str(e)}")
        return success_count, error_count + 1
    
def process_participation_row(row, success_count, error_count, errors):
    """Process a single participation row from CSV data"""
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
        print(f"Successfully added participation: {row['Id']}")  # Debug log
        return success_count + 1, error_count

    except Exception as e:
        error_msg = f"Error processing participation row: {str(e)}"
        print(error_msg)  # Debug log
        db.session.rollback()
        errors.append(error_msg)
        return success_count, error_count + 1

@events_bp.route('/events')
@login_required
def events():
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
    if request.method == 'POST':
        try:
            # Create new event from form data
            status = request.form.get('status', EventStatus.DRAFT)
            event = Event(
                title=request.form.get('title'),
                type=EventType[request.form.get('type').upper()],
                start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M'),
                end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M'),
                location=request.form.get('location'),
                status=status
            )
            
            # Add and commit to database
            db.session.add(event)
            db.session.commit()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('events.events'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            return redirect(url_for('events.add_event'))
    
    # For GET request, use EventType enum for dropdown options
    event_types = [(t.value, t.value.replace('_', ' ').title()) for t in EventType]
    statuses = [(status.value, status.value) for status in EventStatus]
    
    return render_template(
        'events/add_event.html',
        event_types=event_types,
        statuses=statuses
    )

@events_bp.route('/events/view/<int:id>')
@login_required
def view_event(id):
    event = Event.query.get_or_404(id)
    # Get participations with volunteers
    participations = EventParticipation.query.filter_by(event_id=id).all()
    
    # Group participations by status
    participation_stats = {
        'Attended': [],
        'No-Show': [],
        'Cancelled': []
    }
    
    for participation in participations:
        status = participation.status
        if status in participation_stats:
            participation_stats[status].append({
                'volunteer': participation.volunteer,
                'delivery_hours': participation.delivery_hours
            })
    
    return render_template(
        'events/view.html',
        event=event,
        volunteer_count=len(event.volunteers),
        participation_stats=participation_stats,
        volunteers=event.volunteers  # Keep existing volunteer list for backward compatibility
    )

@events_bp.route('/events/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_event(id):
    event = Event.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update event from form data
            event.title = request.form.get('title')
            event.type = EventType[request.form.get('type').upper()]
            event.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
            event.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
            event.location = request.form.get('location')
            event.status = request.form.get('status', event.status)
            event.volunteer_needed = request.form.get('volunteer_needed', type=int)
            event.description = request.form.get('description')
            
            # Update skills
            skill_ids = request.form.getlist('skills[]')
            skills = Skill.query.filter(Skill.id.in_(skill_ids)).all()
            event.skills = skills
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('events.view_event', id=event.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating event: {str(e)}', 'danger')
            return redirect(url_for('events.edit_event', id=id))
    
    # Use EventType enum for dropdown options
    event_types = [(t.value, t.value.replace('_', ' ').title()) for t in EventType]
    statuses = [(status.value, status.value) for status in EventStatus]
    
    return render_template(
        'events/edit.html',
        event=event,
        event_types=event_types,
        statuses=statuses
    )
    
@events_bp.route('/events/import', methods=['GET', 'POST'])
@login_required
def import_events():
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
                        Description__c, Cancellation_Reason__c, Participant_Count_0__c, 
                        District__c, Legacy_Skill_Covered_for_the_Session__c, 
                        Legacy_Skills_Needed__c, Requested_Skills__c
                FROM Session__c
                WHERE CreatedDate >= LAST_N_MONTHS:120
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
    try:
        # First delete all event participations
        EventParticipation.query.delete()
        
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
    try:
        event = Event.query.get_or_404(id)
        
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
