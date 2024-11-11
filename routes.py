from flask import flash, redirect, render_template, url_for, request, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from config import Config
from forms import LoginForm, VolunteerForm
from models.upcoming_events import UpcomingEvent
from models.user import User, db
from models.event import CancellationReason, District, Event, EventType, EventFormat
from werkzeug.security import check_password_hash, generate_password_hash
from models.volunteer import Address, ContactTypeEnum, Email, Engagement, GenderEnum, LocalStatusEnum, Phone, Skill, SkillSourceEnum, Volunteer , VolunteerSkill
from sqlalchemy import or_
from datetime import datetime, timedelta
import io
import csv
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

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
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')
        return render_template('login.html', form=form)
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))
    
    @app.route('/volunteers')
    @login_required
    def volunteers():
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

        # Create a dict of current filters, including pagination params
        current_filters = {
            'search_name': request.args.get('search_name', '').strip(),
            'org_search': request.args.get('org_search', '').strip(),
            'email_search': request.args.get('email_search', '').strip(),
            'skill_search': request.args.get('skill_search', '').strip(),
            'local_status': request.args.get('local_status', ''),
            'per_page': per_page
        }

        # Remove empty filters
        current_filters = {k: v for k, v in current_filters.items() if v}

        # Build query
        query = Volunteer.query

        if current_filters.get('search_name'):
            search_term = f"%{current_filters['search_name']}%"
            query = query.filter(or_(
                Volunteer.first_name.ilike(search_term),
                Volunteer.last_name.ilike(search_term),
                Volunteer.middle_name.ilike(search_term)
            ))

        if current_filters.get('org_search'):
            search_term = f"%{current_filters['org_search']}%"
            query = query.filter(or_(
                Volunteer.organization_name.ilike(search_term),
                Volunteer.title.ilike(search_term),
                Volunteer.department.ilike(search_term)
            ))

        if current_filters.get('email_search'):
            search_term = f"%{current_filters['email_search']}%"
            query = query.join(Email).filter(Email.email.ilike(search_term))

        if current_filters.get('skill_search'):
            search_term = f"%{current_filters['skill_search']}%"
            query = query.join(Volunteer.skills).filter(Skill.name.ilike(search_term))

        if current_filters.get('local_status'):
            query = query.filter(Volunteer.local_status == current_filters['local_status'])

        # Default sort by last_volunteer_date desc
        query = query.order_by(Volunteer.last_volunteer_date.desc())

        # Apply pagination
        paginated_volunteers = query.paginate(
            page=page, 
            per_page=per_page,
            error_out=False
        )

        return render_template('volunteers/volunteers.html',
                             volunteers=paginated_volunteers.items,
                             pagination=paginated_volunteers,
                             current_filters=current_filters)
    
    @app.route('/volunteers/add', methods=['GET', 'POST'])
    @login_required
    def add_volunteer():
        form = VolunteerForm()
        if form.validate_on_submit():
            volunteer = Volunteer(
                salutation=form.salutation.data,
                first_name=form.first_name.data,
                middle_name=form.middle_name.data,
                last_name=form.last_name.data,
                suffix=form.suffix.data,
                organization_name=form.organization_name.data,
                title=form.title.data,
                department=form.department.data,
                industry=form.industry.data,
                local_status=form.local_status.data,
                notes=form.notes.data
            )

            # Add email with type
            email = Email(
                email=form.email.data,
                type=form.email_type.data
            )
            volunteer.emails.append(email)

            # Add phone if provided
            if form.phone.data:
                phone = Phone(
                    number=form.phone.data,
                    type=form.phone_type.data
                )
                volunteer.phones.append(phone)

            # Add skills
            if form.skills.data:
                for skill_name in form.skills.data:
                    if skill_name:
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                        volunteer.skills.append(skill)

            db.session.add(volunteer)
            db.session.commit()
            flash('Volunteer added successfully!', 'success')
            return redirect(url_for('volunteers'))

        return render_template('/volunteers/add_volunteer.html', form=form)
    
    @app.route('/volunteers/view/<int:id>')
    @login_required
    def view_volunteer(id):
        volunteer = Volunteer.query.get_or_404(id)
        
        # Ensure emails are ordered with primary first
        emails = sorted(volunteer.emails, key=lambda x: x.primary, reverse=True)
        
        # Ensure phones are ordered with primary first
        phones = sorted(volunteer.phones, key=lambda x: x.primary, reverse=True)
        
        # Sort engagements by date descending
        engagements = sorted(
            volunteer.engagements, 
            key=lambda x: x.engagement_date or datetime.min, 
            reverse=True
        )
        
        # Calculate volunteer statistics
        stats = {
            'total_times_volunteered': len(engagements),
            'first_volunteer_date': min([e.engagement_date for e in engagements]) if engagements else None,
            'last_volunteer_date': max([e.engagement_date for e in engagements]) if engagements else None
        }
        
        return render_template(
            'volunteers/view.html',
            volunteer=volunteer,
            emails=emails,
            phones=phones,
            engagements=engagements,
            stats=stats
        )
    
    @app.route('/volunteers/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_volunteer(id):
        volunteer = Volunteer.query.get_or_404(id)
        form = VolunteerForm()
        
        if form.validate_on_submit():
            # Update basic information
            form.populate_obj(volunteer)
            
            # Handle email updates
            if form.email.data:
                if volunteer.emails:
                    primary_email = next((e for e in volunteer.emails if e.primary), None)
                    if primary_email:
                        primary_email.email = form.email.data
                        primary_email.type = form.email_type.data
                    else:
                        email = Email(email=form.email.data, type=form.email_type.data, primary=True)
                        volunteer.emails.append(email)
                else:
                    email = Email(email=form.email.data, type=form.email_type.data, primary=True)
                    volunteer.emails.append(email)
            
            # Handle phone updates
            if form.phone.data:
                if volunteer.phones:
                    primary_phone = next((p for p in volunteer.phones if p.primary), None)
                    if primary_phone:
                        primary_phone.number = form.phone.data
                        primary_phone.type = form.phone_type.data
                    else:
                        phone = Phone(number=form.phone.data, type=form.phone_type.data, primary=True)
                        volunteer.phones.append(phone)
                else:
                    phone = Phone(number=form.phone.data, type=form.phone_type.data, primary=True)
                    volunteer.phones.append(phone)
            
            # Update skills
            if form.skills.data:
                volunteer.skills = []
                for skill_name in form.skills.data:
                    if skill_name:
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                        volunteer.skills.append(skill)
            
            db.session.commit()
            flash('Volunteer updated successfully!', 'success')
            return redirect(url_for('view_volunteer', id=volunteer.id))
        
        # Pre-populate form fields
        form.salutation.data = volunteer.salutation
        form.first_name.data = volunteer.first_name
        form.middle_name.data = volunteer.middle_name
        form.last_name.data = volunteer.last_name
        form.suffix.data = volunteer.suffix
        form.organization_name.data = volunteer.organization_name
        form.title.data = volunteer.title
        form.department.data = volunteer.department
        form.industry.data = volunteer.industry
        form.local_status.data = volunteer.local_status
        form.notes.data = volunteer.notes
        
        if volunteer.emails:
            primary_email = next((e for e in volunteer.emails if e.primary), None)
            if primary_email:
                form.email.data = primary_email.email
                form.email_type.data = primary_email.type
        
        if volunteer.phones:
            primary_phone = next((p for p in volunteer.phones if p.primary), None)
            if primary_phone:
                form.phone.data = primary_phone.number
                form.phone_type.data = primary_phone.type
        
        # Don't set skills.data directly, they will be displayed from volunteer.skills in the template
        
        return render_template('volunteers/edit.html', form=form, volunteer=volunteer)
    
    def get_phone_numbers(row):
        """Extract and format phone numbers from a CSV row."""
        phones = []
        seen_numbers = set()  # Track unique numbers
        preferred_type = row.get('npe01__PreferredPhone__c', '').lower()
        
        # Map of CSV columns to phone types
        phone_mappings = {
            'Phone': ('phone', ContactTypeEnum.personal),
            'MobilePhone': ('mobile', ContactTypeEnum.personal),
            'HomePhone': ('home', ContactTypeEnum.personal),
            'npe01__WorkPhone__c': ('work', ContactTypeEnum.professional)
        }
        
        for column, (phone_type, contact_type) in phone_mappings.items():
            number = row.get(column, '').strip()
            # Standardize the number format (remove any non-digit characters)
            cleaned_number = ''.join(filter(str.isdigit, number))
            
            if number and cleaned_number not in seen_numbers:
                # Determine if this phone should be primary based on preferred_type
                is_primary = (
                    preferred_type == phone_type.lower() or
                    (preferred_type == 'mobile' and phone_type == 'phone') or  # Handle generic 'Phone' column
                    (not preferred_type and phone_type == 'mobile')  # Default to mobile if no preference
                )
                
                phones.append(Phone(
                    number=number,
                    type=contact_type,
                    primary=is_primary
                ))
                seen_numbers.add(cleaned_number)
        
        return phones

    def process_volunteer_row(row, success_count, error_count, errors):
        """Process a single volunteer row from CSV data"""
        try:
            # Check if volunteer already exists
            existing_volunteer = Volunteer.query.filter_by(
                first_name=row.get('FirstName', '').strip(),
                last_name=row.get('LastName', '').strip()
            ).first()
            
            if existing_volunteer:
                errors.append(f"Volunteer already exists: {row.get('FirstName')} {row.get('LastName')}")
                return success_count, error_count + 1
            
            # Create new volunteer with proper enum handling
            volunteer = Volunteer(
                salesforce_individual_id=row.get('Id', '').strip(),
                salesforce_account_id=row.get('AccountId', '').strip(),
                first_name=row.get('FirstName', '').strip(),
                last_name=row.get('LastName', '').strip(),
                middle_name=row.get('MiddleName', '').strip(),
                organization_name=row.get('Primary Affiliation', '').strip(),
                title=row.get('Title', '').strip(),
                department=row.get('Department', '').strip(),
                industry=row.get('Industry', '').strip(),
                gender=(
                    GenderEnum[row.get('Gender', '').lower().replace(' ', '_').strip()]
                    if row.get('Gender', '').lower().replace(' ', '_').strip() in [e.name for e in GenderEnum]
                    else None
                ),
                birthdate=parse_date(row.get('Birthdate', '')),
                last_mailchimp_activity_date=parse_date(row.get('Last_Mailchimp_Email_Date__c', '')),
                last_volunteer_date=parse_date(row.get('Last_Volunteer_Date__c', '')),
                last_email_date=parse_date(row.get('Last_Email_Message__c', '')),
                notes=row.get('Notes', '').strip()
            )

            # Add emails and phones
            volunteer.emails.extend(get_email_addresses(row))
            volunteer.phones.extend(get_phone_numbers(row))

            # Add volunteer and get ID
            db.session.add(volunteer)
            db.session.flush()

            # Handle skills
            if row.get('Volunteer_Skills_Text__c') or row.get('Volunteer_Skills__c'):
                skills = parse_skills(
                    row.get('Volunteer_Skills_Text__c', ''),
                    row.get('Volunteer_Skills__c', '')
                )
                
                for skill_name in skills:
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    
                    volunteer_skill = VolunteerSkill(
                        volunteer_id=volunteer.id,
                        skill_id=skill.id,
                        source=SkillSourceEnum.user_selected
                    )
                    db.session.add(volunteer_skill)

            return success_count + 1, error_count
            
        except Exception as e:
            db.session.rollback()
            print(f"Error processing row: {str(e)}")
            errors.append(f"Error processing row: {str(e)}")
            return success_count, error_count + 1

    @app.route('/volunteers/import', methods=['GET', 'POST'])
    @login_required
    def import_volunteers():
        if request.method == 'GET':
            return render_template('volunteers/import.html')
        
        try:
            success_count = 0
            error_count = 0
            errors = []

            if request.is_json and request.json.get('quickSync'):
                # Handle quickSync
                default_file_path = os.path.join('data', 'Volunteers.csv')
                if not os.path.exists(default_file_path):
                    return jsonify({'error': 'Default CSV file not found'}), 404
                    
                with open(default_file_path, 'r', encoding='utf-8') as file:
                    csv_data = csv.DictReader(file)
                    for row in csv_data:
                        success_count, error_count = process_volunteer_row(
                            row, success_count, error_count, errors
                        )

            else:
                # Handle regular file upload
                if 'file' not in request.files:
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    return jsonify({'error': 'File must be a CSV'}), 400

                # Process uploaded file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_data = csv.DictReader(stream)
                for row in csv_data:
                    success_count, error_count = process_volunteer_row(
                        row, success_count, error_count, errors
                    )

            # Commit all changes
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
            return jsonify({'error': str(e)}), 500
    
    @app.route('/volunteers/purge', methods=['POST'])
    @login_required
    def purge_volunteers():
        try:
            # Delete all related data first due to foreign key constraints
            Email.query.delete()
            Phone.query.delete()
            VolunteerSkill.query.delete()
            Engagement.query.delete()
            Address.query.delete()
            
            # Finally delete all volunteers
            Volunteer.query.delete()
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})
    
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
            query = query.filter(Event.type == current_filters['event_type'])

        if current_filters.get('status'):
            query = query.filter(Event.status == current_filters['status'])

        if current_filters.get('start_date'):
            query = query.filter(Event.start_date >= current_filters['start_date'])

        if current_filters.get('end_date'):
            query = query.filter(Event.end_date <= current_filters['end_date'])

        # Default sort by start_date desc
        query = query.order_by(Event.start_date.desc())

        # Apply pagination
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return render_template('events/events.html',
                             events=pagination.items,
                             pagination=pagination,
                             current_filters=current_filters)
    
    @app.route('/sync_upcoming_events', methods=['POST'])
    def sync_upcoming_events():
        # Check if request is from automated script (using token)
        token = request.args.get('token')
        # Check if request is from logged-in user
        is_authenticated = current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
        
        # Verify either token or user authentication
        if not (token == os.getenv('SYNC_AUTH_TOKEN') or is_authenticated):
            return jsonify({'message': 'Unauthorized'}), 401
        
        try:
            print(f"Attempting to connect with: {Config.SF_USERNAME}")
            
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
                WHERE Start_Date__c > TODAY and Available_Slots__c > 0 
                ORDER BY Start_Date__c ASC
            """
            result = sf.query(query)
            events = result.get('records', [])

            # Store the data using the upsert method from your model
            new_count, updated_count = UpcomingEvent.upsert_from_salesforce(events)
            
            return jsonify({
                'success': True,
                'new_count': new_count,
                'updated_count': updated_count,
                'message': f'Successfully synced: {new_count} new, {updated_count} updated'
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
                event = Event(
                    title=request.form.get('title'),
                    type=request.form.get('type'),
                    start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M'),
                    end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M'),
                    location=request.form.get('location'),
                    status=request.form.get('status', 'upcoming')  # Default to upcoming if not specified
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
        
        statuses = [
            ('upcoming', 'Upcoming'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ]
        
        return render_template(
            'events/add_event.html',
            event_types=event_types,
            statuses=statuses
        )
    
    @app.route('/events/view/<int:id>')
    @login_required
    def view_event(id):
        event = Event.query.get_or_404(id)
        volunteer_count = len(event.volunteers)
        return render_template(
            'events/view.html',
            event=event,
            volunteer_count=volunteer_count,
            # ... other template variables ...
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
                event.status = request.form.get('status')
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
        
        statuses = [
            ('upcoming', 'Upcoming'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ]
        
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
        return render_template('management/upcoming_event_management.html', initial_events=events)
    
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
        """Process a single event row from CSV data"""
        try:
            # Get and validate event name
            event_name = row.get('Name', '').strip()
            if not event_name:
                return success_count, error_count  # Skip empty names silently
            
            # Check if event already exists by salesforce_id
            existing_event = None
            if row.get('Id'):
                existing_event = Event.query.filter_by(salesforce_id=row.get('Id')).first()
            
            if existing_event:
                event = existing_event
                # Update existing event fields
                event.title = event_name
                event.type = map_session_type(row.get('Session_Type__c', ''))
                event.format = map_event_format(row.get('Format__c', ''))
                event.start_date = parse_date(row.get('Start_Date__c')) or datetime.now()
                event.end_date = parse_date(row.get('End_Date__c')) or datetime.now() + timedelta(hours=1)
                event.status = row.get('Status__c', 'upcoming')
                event.location = row.get('Location_Information__c', '')
                event.description = row.get('Description__c', '')
                event.volunteer_needed = int(row.get('Volunteers_Needed__c', 0))
                event.cancellation_reason = map_cancellation_reason(row.get('Cancellation_Reason__c'))
            else:
                # Create new event
                event = Event(
                    salesforce_id=row.get('Id', '').strip(),
                    title=event_name,
                    type=map_session_type(row.get('Session_Type__c', '')),
                    format=map_event_format(row.get('Format__c', '')),
                    start_date=parse_date(row.get('Start_Date__c')) or datetime.now(),
                    end_date=parse_date(row.get('End_Date__c')) or datetime.now() + timedelta(hours=1),
                    status=row.get('Status__c', 'upcoming'),
                    location=row.get('Location_Information__c', ''),
                    description=row.get('Description__c', ''),
                    volunteer_needed=int(row.get('Volunteers_Needed__c', 0)),
                    cancellation_reason=map_cancellation_reason(row.get('Cancellation_Reason__c'))
                )
                db.session.add(event)
                db.session.flush()  # Get the event ID
            
            # Handle district
            district_name = row.get('District__c')
            if district_name and district_name in DISTRICT_MAPPINGS:
                district = get_or_create_district(DISTRICT_MAPPINGS[district_name])
                # Check if district is already associated
                if district not in event.districts:
                    event.districts.append(district)
            
            # Handle both covered skills and needed skills
            skills_covered = parse_event_skills(row.get('Legacy_Skill_Covered_for_the_Session__c', ''))
            skills_needed = parse_event_skills(row.get('Legacy_Skills_Needed__c', ''))
            
            # Combine all skills (removing duplicates automatically since it's a set)
            all_skills = set(skills_covered + skills_needed)
            
            for skill_name in all_skills:
                # Get or create skill
                skill = Skill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                    db.session.flush()
                
                # Check if skill is already associated
                if skill not in event.skills:
                    event.skills.append(skill)
            
            return success_count + 1, error_count
                
        except Exception as e:
            db.session.rollback()
            print(f"Error processing event row: {str(e)}")
            errors.append(f"Error processing row: {str(e)}")
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

            if request.is_json and request.json.get('quickSync'):
                # Handle quickSync
                default_file_path = os.path.join('data', 'Sessions.csv')
                if not os.path.exists(default_file_path):
                    return jsonify({'error': 'Default CSV file not found'}), 404
                    
                # Read and process the default file
                with open(default_file_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read().replace('\0', '')  # Remove NUL bytes
                    csv_data = csv.DictReader(content.splitlines())
                    for row in csv_data:
                        success_count, error_count = process_event_row(
                            row, success_count, error_count, errors
                        )

            else:
                # Handle regular file upload
                if 'file' not in request.files:
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    return jsonify({'error': 'File must be a CSV'}), 400

                # Process uploaded file
                content = file.stream.read().decode("UTF8", errors='replace').replace('\0', '')
                csv_data = csv.DictReader(content.splitlines())
                for row in csv_data:
                    success_count, error_count = process_event_row(
                        row, success_count, error_count, errors
                    )

            # Commit all changes
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
            # Delete all events
            Event.query.delete()
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

def parse_date(date_str):
    """Helper function to parse dates from the CSV"""
    if not date_str:
        return None
    try:
        # Try parsing different date formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None

def clean_skill_name(skill_name):
    """Standardize skill name format"""
    return skill_name.strip().lower().capitalize()

def parse_skills(text_skills, comma_skills):
    """Parse and combine skills from both columns, removing duplicates"""
    skills = set()
    
    # Parse semicolon-separated skills
    if text_skills:
        skills.update(clean_skill_name(s) for s in text_skills.split(';') if s.strip())
    
    # Parse comma-separated skills
    if comma_skills:
        skills.update(clean_skill_name(s) for s in comma_skills.split(',') if s.strip())
    
    return list(skills)

def get_email_addresses(row):
    """Extract and format email addresses from a CSV row."""
    emails = []
    seen_emails = set()  # Track unique emails
    preferred_type = row.get('npe01__Preferred_Email__c', '').lower()
    
    # Map of CSV columns to email types
    email_mappings = {
        'Email': ('personal', ContactTypeEnum.personal),  # Changed 'email' to 'personal' to match data
        'npe01__HomeEmail__c': ('home', ContactTypeEnum.personal),
        'npe01__AlternateEmail__c': ('alternate', ContactTypeEnum.personal),
        'npe01__WorkEmail__c': ('work', ContactTypeEnum.professional)
    }

    for column, (email_type, contact_type) in email_mappings.items():
        email = row.get(column, '').strip().lower()
        if email and email not in seen_emails:
            # Set primary based on the preferred email type from the CSV
            is_primary = False
            if preferred_type:
                is_primary = (preferred_type == email_type)
            else:
                # If no preferred type is specified, make the 'Email' column primary
                is_primary = (column == 'Email')
            
            emails.append(Email(
                email=email,
                type=contact_type,
                primary=is_primary
            ))
            seen_emails.add(email)
    
    return emails