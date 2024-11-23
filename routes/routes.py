from flask import flash, redirect, render_template, url_for, request, jsonify, send_file
from flask_login import current_user, login_required, login_user, logout_user
from config import Config
from forms import LoginForm, VolunteerForm
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.upcoming_events import UpcomingEvent
from models.user import User, db
from models.event import CancellationReason, District, Event, EventType, EventFormat, EventStatus
from werkzeug.security import check_password_hash, generate_password_hash
from models.volunteer import Address, ContactTypeEnum, Email, Engagement, EventParticipation, GenderEnum, LocalStatusEnum, Phone, Skill, SkillSourceEnum, Volunteer , VolunteerSkill
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import io
import csv
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from sqlalchemy import or_
from models.tech_job_board import JobOpportunity, EntryLevelJob, WorkLocationType
from io import StringIO
import zipfile
from io import BytesIO
from routes.auth.routes import auth_bp
from routes.history.routes import history_bp
from routes.volunteers.routes import volunteers_bp
from routes.organizations.routes import organizations_bp
from routes.utils import parse_date

DISTRICT_MAPPINGS = {
    'KANSAS CITY USD 500': 'KANSAS CITY USD 500',
    'HICKMAN MILLS C-1': 'HICKMAN MILLS C-1',
    'GRANDVIEW C-4': 'GRANDVIEW C-4',
    'NORTH KANSAS CITY 74': 'NORTH KANSAS CITY 74',
    'REPUBLIC R-III': 'REPUBLIC R-III',
    'KANSAS CITY PUBLIC SCHOOL DISTRICT': 'KANSAS CITY PUBLIC SCHOOL DISTRICT',
    'INDEPENDENCE 30': 'INDEPENDENCE 30',
    'HOGAN PREPARATORY ACADEMY': 'HOGAN PREPARATORY ACADEMY',
    'PIPER-KANSAS CITY': 'PIPER-KANSAS CITY',
    'BELTON 124': 'BELTON 124',
    'CROSSROADS ACADEMY OF KANSAS CITY': 'CROSSROADS ACADEMY OF KANSAS CITY',
    'CENTER SCHOOL DISTRICT': 'CENTER SCHOOL DISTRICT',
    'GUADALUPE CENTERS SCHOOLS': 'GUADALUPE CENTERS SCHOOLS',
    'BLUE VALLEY': 'BLUE VALLEY',
    'BASEHOR-LINWOOD': 'BASEHOR-LINWOOD',
    'ALLEN VILLAGE': 'ALLEN VILLAGE',
    'SPRINGFIELD R-XII': 'SPRINGFIELD R-XII',
    'DE SOTO': 'DE SOTO',
    'INDEPENDENT': 'INDEPENDENT',
    'CENTER 58 SCHOOL DISTRICT': 'CENTER 58 SCHOOL DISTRICT'
}

def get_or_create_district(district_name):
    """Get existing district or create new one"""
    district = District.query.filter_by(name=district_name).first()
    if not district:
        district = District(name=district_name)
        db.session.add(district)
    return district

def init_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(organizations_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/events')
    @login_required
    def events():
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

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

        # Default sort by start_date desc
        query = query.order_by(Event.start_date.desc())

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
    
    @app.route('/sync_upcoming_events', methods=['POST'])
    def sync_upcoming_events():
        try:
            today = datetime.now().date()
            
            # 1. Remove past events AND filled/overfilled events
            deleted_count = UpcomingEvent.query.filter(
                or_(
                    UpcomingEvent.start_date <= today,
                    UpcomingEvent.filled_volunteer_jobs >= UpcomingEvent.available_slots  # Compare filled vs needed
                )
            ).delete()
            db.session.commit()

            # 2. Connect to Salesforce and query
            sf = Salesforce(
                username=Config.SF_USERNAME,
                password=Config.SF_PASSWORD,
                security_token=Config.SF_SECURITY_TOKEN,
                domain='login'
            )

            query = """
                SELECT Id, Name, Available_slots__c, Filled_Volunteer_Jobs__c, 
                Date_and_Time_for_Cal__c, Session_Type__c, Registration_Link__c, 
                Display_on_Website__c, Start_Date__c 
                FROM Session__c 
                WHERE Start_Date__c > TODAY 
                AND Available_slots__c > Filled_Volunteer_Jobs__c  # Modified to compare slots
                ORDER BY Start_Date__c ASC
            """
            result = sf.query(query)
            events = result.get('records', [])

            # 3. Update database with new events
            new_count, updated_count = UpcomingEvent.upsert_from_salesforce(events)
            
            return jsonify({
                'success': True,
                'new_count': new_count,
                'updated_count': updated_count,
                'deleted_count': deleted_count,
                'message': f'Successfully synced: {new_count} new, {updated_count} updated, {deleted_count} removed (past or filled)'
            })

        except SalesforceAuthenticationFailed as e:
            return jsonify({
                'success': False,
                'message': 'Failed to authenticate with Salesforce'
            }), 401

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'An unexpected error occurred: {str(e)}'
            }), 500
    
    @app.route('/events/add', methods=['GET', 'POST'])
    @login_required
    def add_event():
        if request.method == 'POST':
            try:
                # Create new event from form data
                status = request.form.get('status', EventStatus.DRAFT)
                event = Event(
                    title=request.form.get('title'),
                    type=request.form.get('type'),
                    start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M'),
                    end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M'),
                    location=request.form.get('location'),
                    status=status
                )
                
                # Add and commit to database
                db.session.add(event)
                db.session.commit()
                
                flash('Event created successfully!', 'success')
                return redirect(url_for('events'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating event: {str(e)}', 'danger')
                return redirect(url_for('add_event'))
        
        # For GET request, render the form template
        event_types = [
            ('workshop', 'Workshop'),
            ('meeting', 'Meeting'),
            ('social', 'Social Event'),
            ('volunteer', 'Volunteer Session')
        ]
        
        statuses = [(status.value, status.value) for status in EventStatus]
        
        return render_template(
            'events/add_event.html',
            event_types=event_types,
            statuses=statuses
        )
    
    @app.route('/events/view/<int:id>')
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
    
    @app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_event(id):
        event = Event.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                # Update event from form data
                event.title = request.form.get('title')
                event.type = request.form.get('type')
                event.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
                event.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
                event.location = request.form.get('location')
                event.status = request.form.get('status', event.status)
                event.volunteer_needed = request.form.get('volunteer_needed', type=int)
                event.description = request.form.get('description')
                
                db.session.commit()
                flash('Event updated successfully!', 'success')
                return redirect(url_for('view_event', id=event.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating event: {str(e)}', 'danger')
                return redirect(url_for('edit_event', id=id))
        
        event_types = [
            ('workshop', 'Workshop'),
            ('meeting', 'Meeting'),
            ('social', 'Social Event'),
            ('volunteer', 'Volunteer Session')
        ]
        
        statuses = [(status.value, status.value) for status in EventStatus]
        
        return render_template(
            'events/edit.html',
            event=event,
            event_types=event_types,
            statuses=statuses
        )
    
    @app.route('/volunteer_signup')
    def volunteer_signup():
        # Get initial events from database where display_on_website is True, ordered by date
        events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]
        return render_template('events/signup.html', initial_events=events)
    
    @app.route('/volunteer_signup_api')
    def volunteer_signup_api():
        # Get initial events from database where display_on_website is True, ordered by date
        events = [event.to_dict() for event in UpcomingEvent.query.filter_by(display_on_website=True).order_by(UpcomingEvent.start_date).all()]
    
        # Return JSON response directly
        return jsonify(events)
    
    @app.route('/toggle-event-visibility', methods=['POST'])
    @login_required
    def toggle_event_visibility():
        try:
            data = request.get_json()
            event_id = data.get('event_id')
            visible = data.get('visible')
            
            print(f"Toggling event {event_id} to visibility: {visible}")  # Debug log
            
            event = UpcomingEvent.query.filter_by(salesforce_id=event_id).first()
            if not event:
                print(f"Event not found with ID: {event_id}")  # Debug log
                return jsonify({
                    'success': False,
                    'message': 'Event not found'
                }), 404
            
            # Print before state
            print(f"Before update - Event {event_id} visibility: {event.display_on_website}")
            
            event.display_on_website = visible
            db.session.commit()
            
            # Verify the update
            db.session.refresh(event)
            print(f"After update - Event {event_id} visibility: {event.display_on_website}")
            
            return jsonify({
                'success': True,
                'message': f'Event visibility {"enabled" if visible else "disabled"}',
                'current_state': event.display_on_website
            })
            
        except Exception as e:
            print(f"Error in toggle_event_visibility: {str(e)}")  # Debug log
            db.session.rollback()  # Roll back on error
            return jsonify({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }), 500

    @app.route('/upcoming_event_management')
    @login_required
    def upcoming_event_management():
        # Get initial events from database and convert to dict
        events = [event.to_dict() for event in UpcomingEvent.query.all()]
        return render_template('events/upcoming_event_management.html', initial_events=events)
    
    def map_session_type(salesforce_type):
        """Map Salesforce session types to EventType enum values"""
        mapping = {
            'Connector Session': EventType.CONNECTOR_SESSION,
            'Career Jumping': EventType.CAREER_JUMPING,
            'Career Speaker': EventType.CAREER_SPEAKER,
            'Employability Skills': EventType.EMPLOYABILITY_SKILLS,
            'IGNITE': EventType.IGNITE,
            'Career Fair': EventType.CAREER_FAIR,
            'Client Connected Project': EventType.CLIENT_CONNECTED_PROJECT,
            'Pathway Campus Visits': EventType.PATHWAY_CAMPUS_VISITS,
            'Workplace Visit': EventType.WORKPLACE_VISIT,
            'Pathway Workplace Visits': EventType.PATHWAY_WORKPLACE_VISITS,
            'College Options': EventType.COLLEGE_OPTIONS,
            'DIA - Classroom Speaker': EventType.DIA_CLASSROOM_SPEAKER,
            'DIA': EventType.DIA,
            'Campus Visit': EventType.CAMPUS_VISIT,
            'Advisory Sessions': EventType.ADVISORY_SESSIONS,
            'Volunteer Orientation': EventType.VOLUNTEER_ORIENTATION,
            'Volunteer Engagement': EventType.VOLUNTEER_ENGAGEMENT,
            'Mentoring': EventType.MENTORING,
            'Financial Literacy': EventType.FINANCIAL_LITERACY,
            'Math Relays': EventType.MATH_RELAYS,
            'Classroom Speaker': EventType.CLASSROOM_SPEAKER,
            'Internship': EventType.INTERNSHIP,
            'College Application Fair': EventType.COLLEGE_APPLICATION_FAIR,
            'FAFSA': EventType.FAFSA,
            'Classroom Activity': EventType.CLASSROOM_ACTIVITY,
            'Historical, Not Yet Updated': EventType.HISTORICAL,
            'DataViz': EventType.DATA_VIZ
        }
        return mapping.get(salesforce_type, EventType.CLASSROOM_ACTIVITY)  # default to CLASSROOM_ACTIVITY if not found

    def map_cancellation_reason(reason):
        """Map cancellation reasons to CancellationReason enum values"""
        if reason == 'Inclement Weather Cancellation':
            return CancellationReason.WEATHER
        return None

    def map_event_format(format_str):
        """Map Salesforce format to EventFormat enum values"""
        format_mapping = {
            'In-Person': EventFormat.IN_PERSON,
            'Virtual': EventFormat.VIRTUAL
        }
        return format_mapping.get(format_str, EventFormat.IN_PERSON)  # Default to in-person if not found

    def parse_event_skills(skills_str, is_needed=False):
        """Parse skills from Legacy_Skill_Covered_for_the_Session__c or Legacy_Skills_Needed__c"""
        if not skills_str:
            return []
        
        # Split by commas and clean up each skill
        skills = []
        raw_skills = [s.strip() for s in skills_str.split(',')]
        
        for skill in raw_skills:
            # Remove quotes if present
            skill = skill.strip('"')
            
            # Skip empty skills
            if not skill:
                continue
                
            # Map common prefixes to standardized categories
            if skill.startswith('PWY-'):
                skill = skill.replace('PWY-', 'Pathway: ')
            elif skill.startswith('Skills-'):
                skill = skill.replace('Skills-', 'Skill: ')
            elif skill.startswith('CCE-'):
                skill = skill.replace('CCE-', 'Career/College: ')
            elif skill.startswith('CSCs-'):
                skill = skill.replace('CSCs-', 'Core Skill: ')
            elif skill.startswith('ACT-'):
                skill = skill.replace('ACT-', 'Activity: ')
            
            # Add "(Required)" suffix for needed skills
            if is_needed:
                skill = f"{skill} (Required)"
                
            skills.append(skill)
        
        return skills

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

    @app.route('/events/import', methods=['GET', 'POST'])
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


    @app.route('/events/purge', methods=['POST'])
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
        

    @app.template_filter('format_date')
    def format_date(date):
        if date:
            return date.strftime('%B %d, %Y')
        return ''
    
    @app.route('/admin')
    @login_required
    def admin():
        users = User.query.all()
        return render_template('management/admin.html', users=users)

    @app.route('/admin/users', methods=['POST'])
    @login_required
    def create_user():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
        
        return redirect(url_for('admin'))

    @app.route('/admin/users/<int:id>', methods=['DELETE'])
    @login_required
    def delete_user(id):
        print(f"Delete request received for user {id}")  # Add this line
        if current_user.id == id:
            return jsonify({'error': 'Cannot delete yourself'}), 400
        
        user = User.query.get_or_404(id)
        try:
            db.session.delete(user)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error deleting user: {str(e)}")  # Add this line
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @app.route('/change_password', methods=['POST'])
    @login_required
    def change_password():
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verify all fields are provided
        if not all([new_password, confirm_password]):
            flash('Both password fields are required', 'danger')
            return redirect(url_for('admin'))
        
        # Verify new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('admin'))
        
        try:
            # Update password
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Password updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating password: {str(e)}', 'danger')
        
        return redirect(url_for('admin'))

    @app.route('/tech_jobs')
    @login_required
    def tech_jobs():
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

        # Create current_filters dictionary
        current_filters = {
            'search_company': request.args.get('search_company', '').strip(),
            'industry': request.args.get('industry', ''),
            'location': request.args.get('location', ''),
            'entry_level': request.args.get('entry_level', ''),  # Add entry level filter
            'per_page': per_page
        }

        # Remove empty filters
        current_filters = {k: v for k, v in current_filters.items() if v}

        # Build query
        query = JobOpportunity.query.filter_by(is_active=True)

        # Apply filters
        if current_filters.get('search_company'):
            search_term = f"%{current_filters['search_company']}%"
            query = query.filter(JobOpportunity.company_name.ilike(search_term))

        if current_filters.get('industry'):
            query = query.filter(JobOpportunity.industry == current_filters['industry'])

        if current_filters.get('location'):
            if current_filters['location'] == 'kc_based':
                query = query.filter(JobOpportunity.kc_based == True)
            elif current_filters['location'] == 'remote':
                query = query.filter(JobOpportunity.remote_available == True)

        # Add entry level filter
        if current_filters.get('entry_level'):
            if current_filters['entry_level'] == 'yes':
                query = query.filter(JobOpportunity.entry_level_available == True)
            elif current_filters['entry_level'] == 'no':
                query = query.filter(JobOpportunity.entry_level_available == False)

        # Apply pagination
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Get unique industries for dropdown
        industries = db.session.query(JobOpportunity.industry)\
            .distinct()\
            .order_by(JobOpportunity.industry)\
            .all()
        industries = [i[0] for i in industries if i[0]]  # Flatten and remove empty

        return render_template(
            'job_board/tech.html',
            jobs=pagination.items,
            pagination=pagination,
            current_filters=current_filters,
            industries=industries
        )

    @app.route('/tech_jobs/add', methods=['GET', 'POST'])
    @login_required
    def add_job():
        if request.method == 'POST':
            try:
                job = JobOpportunity(
                    company_name=request.form.get('company_name'),
                    industry=request.form.get('industry'),
                    current_openings=request.form.get('current_openings', type=int),
                    location=request.form.get('location'),
                    kc_based=request.form.get('kc_based') == 'true',
                    remote_available=request.form.get('remote_available') == 'true',
                    entry_level_available=request.form.get('entry_level_available') == 'true',
                    job_link=request.form.get('job_link'),
                    description=request.form.get('description')
                )
                db.session.add(job)
                db.session.commit()
                flash('Job added successfully!', 'success')
                return redirect(url_for('tech_jobs'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding job: {str(e)}', 'danger')
                return redirect(url_for('add_job'))

        return render_template('job_board/add_job.html')

    @app.route('/tech_jobs/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_job(id):
        job = JobOpportunity.query.get_or_404(id)
        if request.method == 'POST':
            try:
                job.company_name = request.form.get('company_name')
                job.industry = request.form.get('industry')
                job.current_openings = request.form.get('current_openings', type=int)
                job.location = request.form.get('location')
                job.kc_based = request.form.get('kc_based') == 'true'
                job.remote_available = request.form.get('remote_available') == 'true'
                job.entry_level_available = request.form.get('entry_level_available') == 'true'
                job.job_link = request.form.get('job_link')
                job.description = request.form.get('description')
                
                db.session.commit()
                flash('Job updated successfully!', 'success')
                return redirect(url_for('view_job', id=job.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating job: {str(e)}', 'danger')
                return redirect(url_for('edit_job', id=id))

        return render_template('job_board/edit_job.html', job=job)

    @app.route('/tech_jobs/view/<int:id>')
    def view_job(id):
        job = JobOpportunity.query.get_or_404(id)
        return render_template('job_board/view_job.html', job=job)

    @app.route('/tech_jobs/sync', methods=['POST'])
    @login_required
    def sync_jobs():
        """Sync jobs from external source"""
        try:
            # Add your sync logic here
            return jsonify({'success': True, 'message': 'Jobs synced successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/tech_jobs/purge', methods=['POST'])
    @login_required
    def purge_jobs():
        """Purge old/inactive jobs"""
        try:
            # Add your purge logic here
            return jsonify({'success': True, 'message': 'Old jobs purged successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/tech_jobs/import', methods=['GET', 'POST'])
    @login_required
    def import_tech_jobs():
        if request.method == 'GET':
            return render_template('job_board/import.html')
        
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            # Set default file path
            default_file_path = os.path.join('data', 'KC Tech Jobs.csv')
            
            if request.is_json and request.json.get('quickSync'):
                # Handle quickSync
                if not os.path.exists(default_file_path):
                    return jsonify({'error': 'Default CSV file not found'}), 404
                    
                with open(default_file_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read().replace('\0', '')
                    csv_data = csv.DictReader(content.splitlines())
                    for row in csv_data:
                        try:
                            job = JobOpportunity.query.filter_by(
                                company_name=row.get('Name'),
                                description=row.get('Description')
                            ).first()
                            
                            if not job:
                                job = JobOpportunity()
                                db.session.add(job)
                            
                            # Update job fields
                            job.company_name = row.get('Name', '')
                            job.description = row.get('Description', '')
                            job.industry = row.get('Industry', '')
                            job.current_openings = int(row.get('Current Local Openings', 0))
                            job.opening_types = row.get('Type of Openings', '')
                            job.location = row.get('Location', '')
                            job.entry_level_available = row.get('Entry Avaible?', '').lower() == 'yes'
                            job.kc_based = row.get('KC Based', '').lower() == 'yes'
                            job.notes = row.get('Notes', '')
                            job.job_link = row.get('Link to Jobs', '')
                            job.is_active = True
                            
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing row: {str(e)}")
                            continue

            else:
                # Handle file upload
                if 'file' not in request.files:
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    return jsonify({'error': 'File must be a CSV'}), 400

                content = file.stream.read().decode("UTF8", errors='replace').replace('\0', '')
                csv_data = csv.DictReader(content.splitlines())
                
                # Process the uploaded file using the same logic as above
                for row in csv_data:
                    try:
                        # Same processing logic as above
                        job = JobOpportunity.query.filter_by(
                            company_name=row.get('Name'),
                            description=row.get('Description')
                        ).first()
                        
                        if not job:
                            job = JobOpportunity()
                            db.session.add(job)
                        
                        # Update job fields
                        job.company_name = row.get('Name', '')
                        job.description = row.get('Description', '')
                        job.industry = row.get('Industry', '')
                        job.current_openings = int(row.get('Current Local Openings', 0))
                        job.opening_types = row.get('Type of Openings', '')
                        job.location = row.get('Location', '')
                        job.entry_level_available = row.get('Entry Avaible?', '').lower() == 'yes'
                        job.kc_based = row.get('KC Based', '').lower() == 'yes'
                        job.notes = row.get('Notes', '')
                        job.job_link = row.get('Link to Jobs', '')
                        job.is_active = True
                        
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error processing row: {str(e)}")
                        continue

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
                return jsonify({'error': f'Database error: {str(e)}'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/tech_jobs/import/quick', methods=['POST'])
    @login_required
    def quick_import_tech_jobs():
        import_type = request.args.get('type', 'tech_jobs')
        try:
            success_count = 0
            error_count = 0
            errors = []

            if import_type == 'tech_jobs':
                csv_path = 'data/KC Tech Jobs.csv'
                with open(csv_path, 'r', encoding='utf-8') as file:
                    csv_data = csv.DictReader(file)
                    # First, deactivate all existing jobs
                    JobOpportunity.query.update({JobOpportunity.is_active: False})
                    
                    for row in csv_data:
                        try:
                            # Skip empty rows
                            if not row['Name']:
                                continue
                            
                            # Map CSV data to model fields
                            job = JobOpportunity.query.filter_by(company_name=row['Name']).first()
                            if not job:
                                job = JobOpportunity()
                            
                            job.company_name = row['Name']
                            job.description = row['Description']
                            job.industry = row['Industry']
                            job.current_openings = int(row['Current Local Openings']) if row['Current Local Openings'] else 0
                            job.opening_types = row['Type of Openings']
                            job.location = row['Location']
                            
                            # Convert Yes/No/One to boolean
                            job.entry_level_available = row['Entry Avaible?'].lower() in ['yes', 'one']
                            job.kc_based = row['KC Based'].lower() == 'yes'
                            
                            # Check for remote in location
                            job.remote_available = 'remote' in row['Location'].lower() if row['Location'] else False
                            
                            job.notes = row['Notes']
                            job.job_link = row['Link to Jobs']
                            job.is_active = True
                            
                            db.session.add(job)
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing {row.get('Name', 'Unknown')}: {str(e)}")
                            continue
                    
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
                        return jsonify({'error': f'Database error: {str(e)}'}), 500
                        
            elif import_type == 'entry_level':
                csv_path = 'data/entry_level_jobs.csv'
                with open(csv_path, 'r', encoding='utf-8') as file:
                    csv_data = csv.DictReader(file)
                    
                    for row in csv_data:
                        try:
                            # Find parent job opportunity
                            job = JobOpportunity.query.filter_by(
                                company_name=row['Company Name'],
                                is_active=True
                            ).first()
                            
                            if not job:
                                error_count += 1
                                errors.append(f"Parent job not found for {row['Company Name']}")
                                continue
                            
                            # Check for existing entry level job
                            entry_job = EntryLevelJob.query.filter_by(
                                job_opportunity_id=job.id,
                                title=row['Position Title']
                            ).first()
                            
                            if not entry_job:
                                entry_job = EntryLevelJob()
                            
                            # Update entry job fields
                            entry_job.job_opportunity_id = job.id
                            entry_job.title = row['Position Title']
                            entry_job.description = row['Description']
                            entry_job.address = row['Address']
                            entry_job.job_link = row['Job Link']
                            entry_job.skills_needed = row['Skills Needed']
                            entry_job.work_location = WorkLocationType(row['Work Location'].lower())
                            entry_job.is_active = True
                            
                            db.session.add(entry_job)
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing {row.get('Position Title', 'Unknown')}: {str(e)}")
                            continue
                    
            db.session.commit()
            
            return jsonify({
                'success': True,
                'successCount': success_count,
                'errorCount': error_count,
                'errors': errors
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.template_filter('nl2br')
    def nl2br_filter(text):
        if not text:
            return ""
        return text.replace('\n', '<br>')

    @app.route('/tech_jobs/entry_level/add/<int:job_id>', methods=['GET', 'POST'])
    @login_required
    def add_entry_level_job(job_id):
        job = JobOpportunity.query.get_or_404(job_id)
        
        if request.method == 'POST':
            try:
                entry_job = EntryLevelJob(
                    job_opportunity_id=job_id,
                    title=request.form.get('title'),
                    description=request.form.get('description'),
                    address=request.form.get('address'),
                    job_link=request.form.get('job_link'),
                    skills_needed=request.form.get('skills_needed'),
                    work_location=WorkLocationType(request.form.get('work_location')),
                    is_active=True
                )
                
                db.session.add(entry_job)
                db.session.commit()
                
                flash('Entry level position added successfully!', 'success')
                return redirect(url_for('view_job', id=job_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding entry level position: {str(e)}', 'danger')
        
        return render_template('job_board/entry_level_form.html', 
                             job=job, 
                             entry_job=None,
                             work_locations=WorkLocationType)

    @app.route('/tech_jobs/entry_level/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_entry_level_job(id):
        entry_job = EntryLevelJob.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                entry_job.title = request.form.get('title')
                entry_job.description = request.form.get('description')
                entry_job.address = request.form.get('address')
                entry_job.job_link = request.form.get('job_link')
                entry_job.skills_needed = request.form.get('skills_needed')
                entry_job.work_location = WorkLocationType(request.form.get('work_location'))
                
                db.session.commit()
                flash('Entry level position updated successfully!', 'success')
                return redirect(url_for('view_job', id=entry_job.job_opportunity_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating entry level position: {str(e)}', 'danger')
        
        return render_template('job_board/entry_level_form.html', 
                             job=entry_job.job_opportunity,
                             entry_job=entry_job,
                             work_locations=WorkLocationType)

    @app.route('/tech_jobs/export')
    @login_required
    def export_tech_jobs():
        try:
            # Create in-memory string buffers for our CSV files
            tech_jobs_buffer = StringIO()
            entry_jobs_buffer = StringIO()
            
            # Create CSV writers
            tech_jobs_writer = csv.writer(tech_jobs_buffer)
            entry_jobs_writer = csv.writer(entry_jobs_buffer)
            
            # Write headers for tech jobs CSV (matching import format)
            tech_jobs_writer.writerow([
                'Name', 'Industry Type', 'Industry', 'Current Local Openings',
                'Type of Openings', 'Location', 'Entry Avaible?', 'KC Based',
                'Notes', 'Link to Jobs'
            ])
            
            # Write headers for entry level positions CSV
            entry_jobs_writer.writerow([
                'Company Name', 'Position Title', 'Description', 'Address',
                'Work Location', 'Skills Needed', 'Job Link', 'Is Active'
            ])
            
            # Get all active job opportunities
            jobs = JobOpportunity.query.filter_by(is_active=True).all()
            
            # Write job opportunities data
            for job in jobs:
                tech_jobs_writer.writerow([
                    job.company_name,
                    '',  # Industry Type (not in current model)
                    job.industry,
                    job.current_openings,
                    job.opening_types,
                    job.location,
                    'Yes' if job.entry_level_available else 'No',
                    'Yes' if job.kc_based else 'No',
                    job.notes,
                    job.job_link
                ])
                
                # Write entry level positions data
                for position in job.entry_level_positions:
                    if position.is_active:
                        entry_jobs_writer.writerow([
                            job.company_name,
                            position.title,
                            position.description,
                            position.address,
                            position.work_location.value,
                            position.skills_needed,
                            position.job_link,
                            'Yes' if position.is_active else 'No'
                        ])
            
            # Create a zip file containing both CSVs
            import zipfile
            from io import BytesIO
            
            # Create zip buffer
            zip_buffer = BytesIO()
            
            # Create zip file
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add tech jobs CSV
                tech_jobs_buffer.seek(0)
                zip_file.writestr('tech_jobs.csv', tech_jobs_buffer.getvalue())
                
                # Add entry level jobs CSV
                entry_jobs_buffer.seek(0)
                zip_file.writestr('entry_level_jobs.csv', entry_jobs_buffer.getvalue())
            
            # Prepare zip file for download
            zip_buffer.seek(0)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'tech_jobs_export_{timestamp}.zip'
            )
            
        except Exception as e:
            flash(f'Error exporting data: {str(e)}', 'danger')
            return redirect(url_for('tech_jobs'))
        
    @app.route('/sync/events', methods=['POST'])
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

    @app.route('/sync/participants', methods=['POST'])
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
