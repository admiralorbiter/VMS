import csv
import io
import os
import json
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from config import Config
from models import db
from models.volunteer import Volunteer, Skill, EventParticipation, Engagement
from models.contact import Email, ContactTypeEnum
from models.event import Event
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.contact import Contact, Address, EducationEnum, Phone, LocalStatusEnum, RaceEthnicityEnum, GenderEnum
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from forms import VolunteerForm
from sqlalchemy import or_, and_
from routes.utils import get_email_addresses, get_phone_numbers, parse_date, parse_skills

volunteers_bp = Blueprint('volunteers', __name__)

def process_volunteer_row(row, success_count, error_count, errors):
        """Process a single volunteer row from CSV data"""
        try:
            # Check if volunteer exists by salesforce_id
            volunteer = None
            if row.get('Id'):
                volunteer = Volunteer.query.filter_by(salesforce_individual_id=row['Id']).first()
            
            # If volunteer doesn't exist, create new one
            if not volunteer:
                volunteer = Volunteer()
                db.session.add(volunteer)
            
            # Update volunteer fields (handles both new and existing volunteers)
            volunteer.salesforce_individual_id = row.get('Id', '').strip()
            volunteer.salesforce_account_id = row.get('AccountId', '').strip()
            volunteer.first_name = row.get('FirstName', '').strip()
            volunteer.last_name = row.get('LastName', '').strip()
            volunteer.middle_name = row.get('MiddleName', '').strip()
            volunteer.organization_name = row.get('Primary Affiliation', '').strip()
            volunteer.title = row.get('Title', '').strip()
            volunteer.department = row.get('Department', '').strip()
            volunteer.industry = row.get('Industry', '').strip()
            
            # Handle gender enum
            gender_str = row.get('Gender', '').lower().replace(' ', '_').strip()
            if gender_str in [e.name for e in GenderEnum]:
                volunteer.gender = GenderEnum[gender_str]
            
            # Handle dates
            volunteer.birthdate = parse_date(row.get('Birthdate', ''))
            volunteer.last_mailchimp_activity_date = parse_date(row.get('Last_Mailchimp_Email_Date__c', ''))
            volunteer.last_volunteer_date = parse_date(row.get('Last_Volunteer_Date__c', ''))
            volunteer.last_email_date = parse_date(row.get('Last_Email_Message__c', ''))
            volunteer.notes = row.get('Notes', '').strip()

            # Handle emails
            new_emails = get_email_addresses(row)
            if new_emails:
                # Clear existing emails and add new ones
                volunteer.emails = new_emails

            # Handle phones
            new_phones = get_phone_numbers(row)
            if new_phones:
                # Clear existing phones and add new ones
                volunteer.phones = new_phones

            # Handle skills
            if row.get('Volunteer_Skills_Text__c') or row.get('Volunteer_Skills__c'):
                skills = parse_skills(
                    row.get('Volunteer_Skills_Text__c', ''),
                    row.get('Volunteer_Skills__c', '')
                )
                
                # Update skills
                for skill_name in skills:
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                    if skill not in volunteer.skills:
                        volunteer.skills.append(skill)

            # Add this new section to handle times_volunteered
            if row.get('Number_of_Attended_Volunteer_Sessions__c'):
                try:
                    volunteer.times_volunteered = int(float(row['Number_of_Attended_Volunteer_Sessions__c']))
                except (ValueError, TypeError):
                    volunteer.times_volunteered = 0

            return success_count + 1, error_count
                
        except Exception as e:
            db.session.rollback()
            print(f"Error processing volunteer row: {str(e)}")
            errors.append(f"Error processing row: {str(e)}")
            return success_count, error_count + 1

@volunteers_bp.route('/volunteers')
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

    # Get sort parameters
    sort_by = request.args.get('sort_by', 'last_volunteer_date')  # default sort field
    sort_direction = request.args.get('sort_direction', 'desc')  # default direction

    # Add sort parameters to current_filters
    current_filters.update({
        'sort_by': sort_by,
        'sort_direction': sort_direction
    })

    # Start with a subquery to get the attended count
    attended_count_subq = db.session.query(
        EventParticipation.volunteer_id,
        db.func.count(EventParticipation.id).label('attended_count')
    ).filter(
        EventParticipation.status == 'Attended'
    ).group_by(
        EventParticipation.volunteer_id
    ).subquery()

    # Build main query
    query = db.session.query(
        Volunteer,
        db.func.coalesce(attended_count_subq.c.attended_count, 0).label('attended_count')
    ).outerjoin(
        attended_count_subq,
        Volunteer.id == attended_count_subq.c.volunteer_id
    )

    # Apply filters
    if current_filters.get('search_name'):
        # Split search terms and remove empty strings
        search_terms = [term.strip() for term in current_filters['search_name'].split() if term.strip()]
        
        # Build dynamic search condition
        name_conditions = []
        for term in search_terms:
            search_pattern = f"%{term}%"
            name_conditions.append(or_(
                Volunteer.first_name.ilike(search_pattern),
                Volunteer.middle_name.ilike(search_pattern),
                Volunteer.last_name.ilike(search_pattern),
                # Concatenated name search using SQLite's || operator
                (Volunteer.first_name + ' ' + 
                 db.func.coalesce(Volunteer.middle_name, '') + ' ' + 
                 Volunteer.last_name).ilike(search_pattern)
            ))
        # Combine all conditions with AND (each term must match somewhere)
        if name_conditions:
            query = query.filter(and_(*name_conditions))

    if current_filters.get('org_search'):
        search_term = f"%{current_filters['org_search']}%"
        # Join with VolunteerOrganization and Organization tables
        query = query.outerjoin(
            VolunteerOrganization
        ).outerjoin(
            Organization,
            VolunteerOrganization.organization_id == Organization.id
        ).filter(or_(
            # Search direct volunteer fields
            Volunteer.organization_name.ilike(search_term),
            Volunteer.title.ilike(search_term),
            Volunteer.department.ilike(search_term),
            # Search related organization fields
            Organization.name.ilike(search_term),
            VolunteerOrganization.role.ilike(search_term)
        ))

    if current_filters.get('email_search'):
        search_term = f"%{current_filters['email_search']}%"
        query = query.join(Email).filter(Email.email.ilike(search_term))

    if current_filters.get('skill_search'):
        search_term = f"%{current_filters['skill_search']}%"
        query = query.join(Volunteer.skills).filter(Skill.name.ilike(search_term))

    if current_filters.get('local_status'):
        query = query.filter(Volunteer.local_status == current_filters['local_status'])

    # Apply sorting based on parameters
    if sort_by:
        sort_column = None
        if sort_by == 'name':
            sort_column = (Volunteer.first_name + ' ' + 
                          db.func.coalesce(Volunteer.middle_name, '') + ' ' + 
                          Volunteer.last_name)
        elif sort_by == 'times_volunteered':
            sort_column = (
                Volunteer.times_volunteered + 
                db.func.coalesce(attended_count_subq.c.attended_count, 0) + 
                Volunteer.additional_volunteer_count
            )
        
        if sort_column is not None:
            if sort_direction == 'desc':
                query = query.order_by(sort_column.desc(), Volunteer.last_name.asc())
            else:
                query = query.order_by(sort_column.asc(), Volunteer.last_name.asc())
        else:
            # Default sort
            query = query.order_by(Volunteer.last_volunteer_date.desc())

    # Apply pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Transform the results to include the attended count and organization info
    volunteers_with_counts = []
    for result in pagination.items:
        volunteer_data = {
            'volunteer': result[0],
            'attended_count': result[1] or 0,
            'organizations': []
        }
        
        # Get organization info with roles
        for vol_org in result[0].volunteer_organizations:
            org_info = {
                'organization': vol_org.organization,
                'role': vol_org.role,
                'status': vol_org.status,
                'is_primary': vol_org.is_primary
            }
            volunteer_data['organizations'].append(org_info)
        
        volunteers_with_counts.append(volunteer_data)

    return render_template('volunteers/volunteers.html',
                         volunteers=volunteers_with_counts,
                         pagination=pagination,
                         current_filters=current_filters)

@volunteers_bp.route('/volunteers/add', methods=['GET', 'POST'])
@login_required
def add_volunteer():
    if request.method == 'POST':
        try:
            # Create and add volunteer first
            volunteer = Volunteer(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                organization_name=request.form.get('organization_name'),
                title=request.form.get('title'),
                gender=GenderEnum[request.form.get('gender')] if request.form.get('gender') else None,
                local_status=LocalStatusEnum[request.form.get('local_status')] if request.form.get('local_status') else None,
                race_ethnicity=RaceEthnicityEnum[request.form.get('race_ethnicity')] if request.form.get('race_ethnicity') else None
            )
            db.session.add(volunteer)
            db.session.flush()  # This ensures volunteer has an ID before adding relationships

            # Add skills
            if request.form.get('skills'):
                skill_names = json.loads(request.form.get('skills'))
                for skill_name in set(skill_names):
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    volunteer.skills.append(skill)

            # Add email
            if request.form.get('email'):
                email = Email(
                    email=request.form.get('email'),
                    type=request.form.get('email_type', 'personal'),
                    primary=True,
                    contact_id=volunteer.id
                )
                db.session.add(email)

            # Add phone
            if request.form.get('phone'):
                phone = Phone(
                    number=request.form.get('phone'),
                    type=request.form.get('phone_type', 'personal'),
                    primary=True,
                    contact_id=volunteer.id
                )
                db.session.add(phone)

            db.session.commit()
            return redirect(url_for('volunteers.volunteers'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding volunteer: {str(e)}', 'error')
            return render_template('volunteers/add.html')

    return render_template('volunteers/add.html')

@volunteers_bp.route('/volunteers/view/<int:id>')
@login_required
def view_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)
    
    # Get participations and group by status
    participations = EventParticipation.query.filter_by(volunteer_id=id).join(
        Event, EventParticipation.event_id == Event.id
    ).all()
    
    participation_stats = {
        'Attended': [],
        'No-Show': [],
        'Cancelled': []
    }
    
    for participation in participations:
        status = participation.status
        if status in participation_stats:
            participation_stats[status].append({
                'event': participation.event,
                'delivery_hours': participation.delivery_hours,
                'date': participation.event.start_date if participation.event.start_date else participation.event.date  # Handle both date fields
            })
    
    # Sort each list by date
    for status in participation_stats:
        participation_stats[status].sort(key=lambda x: x['date'], reverse=True)
    
    # Get history records for the volunteer
    histories = History.query.filter_by(
        volunteer_id=id, 
        is_deleted=False
    ).order_by(
        History.activity_date.desc()
    ).all()
    
    # Create a dictionary of organization relationships for easy access in template
    org_relationships = {}
    for vol_org in volunteer.volunteer_organizations:
        org_relationships[vol_org.organization_id] = vol_org
    
    return render_template(
        'volunteers/view.html',
        volunteer=volunteer,
        emails=sorted(volunteer.emails, key=lambda x: x.primary, reverse=True),
        phones=sorted(volunteer.phones, key=lambda x: x.primary, reverse=True),
        participation_stats=participation_stats,
        histories=histories,
        org_relationships=org_relationships
    )

@volunteers_bp.route('/volunteers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_volunteer(id):
    volunteer = db.session.get(Volunteer, id)
    if not volunteer:
        abort(404)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            volunteer.first_name = request.form.get('first_name')
            volunteer.last_name = request.form.get('last_name')
            volunteer.organization_name = request.form.get('organization_name')
            volunteer.title = request.form.get('title')
            
            # Handle enums with proper error checking
            if request.form.get('gender'):
                try:
                    volunteer.gender = GenderEnum[request.form.get('gender')]
                except KeyError:
                    flash('Invalid gender value', 'error')
                    return redirect(url_for('volunteers.edit_volunteer', id=id))
                    
            if request.form.get('local_status'):
                try:
                    volunteer.local_status = LocalStatusEnum[request.form.get('local_status')]
                except KeyError:
                    flash('Invalid local status value', 'error')
                    return redirect(url_for('volunteers.edit_volunteer', id=id))
                    
            if request.form.get('race_ethnicity'):
                try:
                    volunteer.race_ethnicity = RaceEthnicityEnum[request.form.get('race_ethnicity')]
                except KeyError:
                    flash('Invalid race/ethnicity value', 'error')
                    return redirect(url_for('volunteers.edit_volunteer', id=id))

            # Handle skills
            if request.form.get('skills'):
                # Clear existing skills
                volunteer.skills = []
                db.session.flush()
                
                # Add new skills
                skill_names = json.loads(request.form.get('skills'))
                for skill_name in skill_names:
                    skill = Skill.query.filter_by(name=skill_name).first()
                    if not skill:
                        skill = Skill(name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    volunteer.skills.append(skill)

            # Handle email with transaction safety
            if request.form.get('email'):
                Email.query.filter_by(contact_id=volunteer.id).delete()
                email = Email(
                    contact_id=volunteer.id,
                    email=request.form.get('email'),
                    type=request.form.get('email_type', 'personal'),
                    primary=True
                )
                db.session.add(email)

            # Handle phone with transaction safety
            if request.form.get('phone'):
                Phone.query.filter_by(contact_id=volunteer.id).delete()
                phone = Phone(
                    contact_id=volunteer.id,
                    number=request.form.get('phone'),
                    type=request.form.get('phone_type', 'personal'),
                    primary=True
                )
                db.session.add(phone)

            db.session.commit()
            flash('Volunteer updated successfully', 'success')
            return redirect(url_for('volunteers.view_volunteer', id=volunteer.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating volunteer: {str(e)}', 'error')
            return redirect(url_for('volunteers.edit_volunteer', id=id))

    return render_template('volunteers/edit.html', 
                         volunteer=volunteer,
                         GenderEnum=GenderEnum,
                         RaceEthnicityEnum=RaceEthnicityEnum,
                         LocalStatusEnum=LocalStatusEnum)

@volunteers_bp.route('/volunteers/import', methods=['GET', 'POST'])
@login_required
def import_volunteers():
        if request.method == 'GET':
            return render_template('volunteers/import.html')
        
        try:
            success_count = 0
            error_count = 0
            errors = []
            print("Starting volunteer import process...")

            if request.is_json and request.json.get('quickSync'):
                print("Quick sync mode detected - using default CSV file")
                default_file_path = os.path.join('data', 'Volunteers.csv')
                if not os.path.exists(default_file_path):
                    print(f"Error: Default CSV file not found at {default_file_path}")
                    return jsonify({'error': 'Default CSV file not found'}), 404
                
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        print(f"Attempting to read file with encoding: {encoding}")
                        with open(default_file_path, 'r', encoding=encoding) as file:
                            csv_data = csv.DictReader(file)
                            for row in csv_data:
                                success_count, error_count = process_volunteer_row(
                                    row, success_count, error_count, errors
                                )
                        print(f"Successfully read file using encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        print(f"Failed to decode with {encoding}")
                        continue
                else:
                    print("Error: Could not decode file with any known encoding")
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

            else:
                print("Standard file upload mode detected")
                if 'file' not in request.files:
                    print("Error: No file uploaded")
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    print("Error: No file selected")
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    print("Error: File must be a CSV")
                    return jsonify({'error': 'File must be a CSV'}), 400

                file_content = file.read()
                
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        print(f"Attempting to decode uploaded file with encoding: {encoding}")
                        stream = io.StringIO(file_content.decode(encoding), newline=None)
                        csv_data = csv.DictReader(stream)
                        for row in csv_data:
                            success_count, error_count = process_volunteer_row(
                                row, success_count, error_count, errors
                            )
                        print(f"Successfully decoded file using encoding: {encoding}")
                        break
                    except UnicodeDecodeError:
                        print(f"Failed to decode uploaded file with {encoding}")
                        continue
                else:
                    print("Error: Could not decode uploaded file with any known encoding")
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

            try:
                db.session.commit()
                print(f"Import completed successfully:")
                print(f"- Successful imports: {success_count}")
                print(f"- Failed imports: {error_count}")
                if errors:
                    print("Errors encountered:")
                    for error in errors:
                        print(f"  - {error}")
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
            print(f"Unexpected error during import: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
@volunteers_bp.route('/volunteers/purge', methods=['POST'])
@login_required
def purge_volunteers():
    try:
        # Get all volunteer IDs first
        volunteer_ids = db.session.query(Volunteer.id).all()
        volunteer_ids = [v[0] for v in volunteer_ids]
        
        # Delete all related data for volunteers
        Email.query.filter(Email.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Phone.query.filter(Phone.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Address.query.filter(Address.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        VolunteerSkill.query.filter(VolunteerSkill.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Engagement.query.filter(Engagement.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        EventParticipation.query.filter(EventParticipation.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        History.query.filter(History.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        VolunteerOrganization.query.filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        
        # Delete volunteers first
        Volunteer.query.delete(synchronize_session=False)
        
        # Then delete the corresponding contact records
        Contact.query.filter(Contact.type == 'volunteer').delete(synchronize_session=False)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    
@volunteers_bp.route('/volunteers/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_volunteer(id):
    try:
        volunteer = db.session.get(Volunteer, id)
        if not volunteer:
            abort(404)
        
        # Delete all related records first (in correct order due to foreign key constraints)
        Email.query.filter_by(contact_id=id).delete()
        Phone.query.filter_by(contact_id=id).delete()
        Address.query.filter_by(contact_id=id).delete()
        VolunteerSkill.query.filter_by(volunteer_id=id).delete()
        History.query.filter_by(volunteer_id=id).delete()
        EventParticipation.query.filter_by(volunteer_id=id).delete()
        VolunteerOrganization.query.filter_by(volunteer_id=id).delete()
        
        # Delete the volunteer
        db.session.delete(volunteer)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Volunteer deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@volunteers_bp.route('/volunteers/import-from-salesforce', methods=['POST'])
@login_required
def import_from_salesforce():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        print("Starting volunteer import from Salesforce...")
        
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email,
               npe01__AlternateEmail__c, npe01__HomeEmail__c, 
               npe01__WorkEmail__c, npe01__Preferred_Email__c,
               HomePhone, MobilePhone, npe01__WorkPhone__c, Phone,
               npe01__PreferredPhone__c,
               npsp__Primary_Affiliation__c, Title, Department, Gender__c, 
               Birthdate, Last_Mailchimp_Email_Date__c, Last_Volunteer_Date__c, 
               Last_Email_Message__c, Volunteer_Recruitment_Notes__c, 
               Volunteer_Skills__c, Volunteer_Skills_Text__c, 
               Number_of_Attended_Volunteer_Sessions__c
        FROM Contact
        WHERE Contact_Type__c = 'Volunteer'
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

        success_count = 0
        error_count = 0
        errors = []
        processed_volunteers = []

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                # Check if volunteer exists
                volunteer = Volunteer.query.filter_by(salesforce_individual_id=row['Id']).first()
                
                if not volunteer:
                    volunteer = Volunteer()
                    volunteer.salesforce_individual_id = row['Id']
                    db.session.add(volunteer)
                
                # Update volunteer fields
                volunteer.salesforce_account_id = row['AccountId']
                volunteer.first_name = (row.get('FirstName') or '').strip()
                volunteer.last_name = (row.get('LastName') or '').strip()
                volunteer.middle_name = (row.get('MiddleName') or '').strip()
                volunteer.organization_name = (row.get('npsp__Primary_Affiliation__c') or '').strip()
                volunteer.title = (row.get('Title') or '').strip()
                volunteer.department = (row.get('Department') or '').strip()

                # Handle gender enum
                gender_str = (row.get('Gender__c') or '').lower().replace(' ', '_').strip()
                if gender_str and gender_str in [e.name for e in GenderEnum]:
                    volunteer.gender = GenderEnum[gender_str]

                # Handle dates
                volunteer.birthdate = parse_date(row.get('Birthdate'))
                volunteer.last_mailchimp_activity_date = parse_date(row.get('Last_Mailchimp_Email_Date__c'))
                volunteer.last_volunteer_date = parse_date(row.get('Last_Volunteer_Date__c'))
                volunteer.last_email_date = parse_date(row.get('Last_Email_Message__c'))
                volunteer.notes = (row.get('Volunteer_Recruitment_Notes__c') or '').strip()

                # Handle skills
                if row.get('Volunteer_Skills__c') or row.get('Volunteer_Skills_Text__c'):
                    skills = parse_skills(
                        row.get('Volunteer_Skills_Text__c', ''),
                        row.get('Volunteer_Skills__c', '')
                    )
                    
                    # Clear existing skills
                    volunteer.skills = []
                    
                    # Add new skills
                    for skill_name in skills:
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            db.session.add(skill)
                        if skill not in volunteer.skills:
                            volunteer.skills.append(skill)

                # Handle times_volunteered
                if row.get('Number_of_Attended_Volunteer_Sessions__c'):
                    try:
                        volunteer.times_volunteered = int(float(row['Number_of_Attended_Volunteer_Sessions__c']))
                    except (ValueError, TypeError):
                        volunteer.times_volunteered = 0

                # Handle emails
                email_fields = {
                    'npe01__WorkEmail__c': ContactTypeEnum.professional,
                    'Email': ContactTypeEnum.personal,
                    'npe01__HomeEmail__c': ContactTypeEnum.personal,
                    'npe01__AlternateEmail__c': ContactTypeEnum.personal
                }
                
                # Get preferred email type
                preferred_email = row.get('npe01__Preferred_Email__c', '').lower()
                
                # Process each email field
                for email_field, email_type in email_fields.items():
                    email_value = row.get(email_field)
                    if not email_value:
                        continue
                        
                    # Check if this should be the primary email based on preference
                    is_primary = False
                    if preferred_email:
                        if (preferred_email == 'work' and email_field == 'npe01__WorkEmail__c') or \
                           (preferred_email == 'personal' and email_field in ['npe01__HomeEmail__c', 'Email']) or \
                           (preferred_email == 'alternate' and email_field == 'npe01__AlternateEmail__c'):
                            is_primary = True
                    elif email_field == 'Email':  # Default to standard Email field as primary if no preference
                        is_primary = True
                    
                    # Check if email already exists
                    email = Email.query.filter_by(
                        contact_id=volunteer.id,
                        email=email_value
                    ).first()
                    
                    if not email:
                        email = Email(
                            contact_id=volunteer.id,
                            email=email_value,
                            type=email_type,
                            primary=is_primary
                        )
                        db.session.add(email)
                    else:
                        # Update existing email type and primary status
                        email.type = email_type
                        if is_primary and not email.primary:
                            # Set all other emails to non-primary
                            Email.query.filter_by(
                                contact_id=volunteer.id,
                                primary=True
                            ).update({'primary': False})
                            email.primary = True

                # Handle phone numbers
                phone_fields = {
                    'npe01__WorkPhone__c': ContactTypeEnum.professional,
                    'Phone': ContactTypeEnum.professional,  # Business Phone
                    'HomePhone': ContactTypeEnum.personal,
                    'MobilePhone': ContactTypeEnum.personal
                }
                
                # Get preferred phone type
                preferred_phone = row.get('npe01__PreferredPhone__c', '').lower()
                
                # Process each phone field
                for phone_field, phone_type in phone_fields.items():
                    phone_value = row.get(phone_field)
                    if not phone_value:
                        continue
                        
                    # Check if this should be the primary phone based on preference
                    is_primary = False
                    if preferred_phone:
                        if (preferred_phone == 'work' and phone_field in ['npe01__WorkPhone__c', 'Phone']) or \
                           (preferred_phone == 'home' and phone_field == 'HomePhone') or \
                           (preferred_phone == 'mobile' and phone_field == 'MobilePhone'):
                            is_primary = True
                    elif phone_field == 'Phone':  # Default to business Phone as primary if no preference
                        is_primary = True
                    
                    # Check if phone already exists
                    phone = Phone.query.filter_by(
                        contact_id=volunteer.id,
                        number=phone_value
                    ).first()
                    
                    if not phone:
                        phone = Phone(
                            contact_id=volunteer.id,
                            number=phone_value,
                            type=phone_type,
                            primary=is_primary
                        )
                        db.session.add(phone)
                    else:
                        # Update existing phone type and primary status
                        phone.type = phone_type
                        if is_primary and not phone.primary:
                            # Set all other phones to non-primary
                            Phone.query.filter_by(
                                contact_id=volunteer.id,
                                primary=True
                            ).update({'primary': False})
                            phone.primary = True

                success_count += 1
                processed_volunteers.append(f"{volunteer.first_name} {volunteer.last_name}")
                
            except Exception as e:
                error_count += 1
                error_detail = {
                    'name': f"{row.get('FirstName', '')} {row.get('LastName', '')}",
                    'salesforce_id': row.get('Id', ''),
                    'error': str(e)
                }
                errors.append(error_detail)
                db.session.rollback()

        # Commit all successful changes
        try:
            db.session.commit()
            print(f"\nImport complete - Created/Updated: {success_count}, Errors: {error_count}")
            if errors:
                print("\nErrors encountered:")
                for error in errors:
                    print(f"- {error['name']}: {error['error']}")

            return jsonify({
                'success': True,
                'message': f'Successfully processed {success_count} volunteers with {error_count} errors'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database commit error: {str(e)}'
            }), 500

    except SalesforceAuthenticationFailed:
        print("Error: Failed to authenticate with Salesforce")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500