import csv
import io
import os
import json
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from config import Config
from models import db
from models.volunteer import Volunteer, Skill, EventParticipation, Engagement, VolunteerSkill, ConnectorData, ConnectorSubscriptionEnum
from models.contact import Email, ContactTypeEnum
from models.event import Event
from models.history import History
from models.organization import Organization, VolunteerOrganization
from models.contact import Contact, Address, EducationEnum, Phone, LocalStatusEnum, RaceEthnicityEnum, GenderEnum, AgeGroupEnum
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
            volunteer.first_volunteer_date = parse_date(row.get('First_Volunteer_Date__c', ''))
            volunteer.last_mailchimp_activity_date = parse_date(row.get('Last_Mailchimp_Email_Date__c', ''))
            volunteer.last_volunteer_date = parse_date(row.get('Last_Volunteer_Date__c', ''))
            volunteer.last_email_date = parse_date(row.get('Last_Email_Message__c', ''))
            volunteer.last_non_internal_email_date = parse_date(row.get('Last_Non_Internal_Email_Activity__c', ''))
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

            # Handle Connector data
            connector_data = {
                'active_subscription': (row.get('Connector_Active_Subscription__c') or '').strip().upper() or 'NONE',
                'active_subscription_name': (row.get('Connector_Active_Subscription_Name__c') or '').strip(),
                'affiliations': (row.get('Connector_Affiliations__c') or '').strip(),
                'industry': (row.get('Connector_Industry__c') or '').strip(),
                'joining_date': (row.get('Connector_Joining_Date__c') or '').strip(),
                'last_login_datetime': (row.get('Connector_Last_Login_Date_Time__c') or '').strip(),
                'last_update_date': parse_date(row.get('Connector_Last_Update_Date__c')),
                'profile_link': (row.get('Connector_Profile_Link__c') or '').strip(),
                'role': (row.get('Connector_Role__c') or '').strip(),
                'signup_role': (row.get('Connector_SignUp_Role__c') or '').strip(),
                'user_auth_id': (row.get('Connector_User_ID__c') or '').strip()
            }

            # Create or update connector data
            if not volunteer.connector:
                volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                updates.append('connector_created')

            # Update connector fields if they exist in Salesforce data
            if connector_data['active_subscription'] in [e.name for e in ConnectorSubscriptionEnum]:
                if volunteer.connector.active_subscription != ConnectorSubscriptionEnum[connector_data['active_subscription']]:
                    volunteer.connector.active_subscription = ConnectorSubscriptionEnum[connector_data['active_subscription']]
                    updates.append('connector_subscription')

            for field, value in connector_data.items():
                if field != 'active_subscription' and value:  # Skip active_subscription as it's handled above
                    current_value = getattr(volunteer.connector, field)
                    if current_value != value:
                        setattr(volunteer.connector, field, value)
                        updates.append(f'connector_{field}')

            return success_count + 1, error_count
                
        except Exception as e:
            db.session.rollback()
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
            
            if request.is_json and request.json.get('quickSync'):
                default_file_path = os.path.join('data', 'Volunteers.csv')
                if not os.path.exists(default_file_path):
                    return jsonify({'error': 'Default CSV file not found'}), 404
                
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(default_file_path, 'r', encoding=encoding) as file:
                            csv_data = csv.DictReader(file)
                            for row in csv_data:
                                success_count, error_count = process_volunteer_row(
                                    row, success_count, error_count, errors
                                )
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

            else:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    return jsonify({'error': 'File must be a CSV'}), 400

                file_content = file.read()
                
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        stream = io.StringIO(file_content.decode(encoding), newline=None)
                        csv_data = csv.DictReader(stream)
                        for row in csv_data:
                            success_count, error_count = process_volunteer_row(
                                row, success_count, error_count, errors
                            )
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

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
        # Before deleting volunteers:
        Volunteer.query.delete()  # This should trigger cascades
        # Also clean up:
        Email.query.filter(Email.contact_id.notin_(Contact.query.with_entities(Contact.id))).delete()
        Phone.query.filter(Phone.contact_id.notin_(Contact.query.with_entities(Contact.id))).delete()
        db.session.commit()
        # Clean up related records first
        EventParticipation.query.filter(EventParticipation.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        History.query.filter(History.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        VolunteerOrganization.query.filter(VolunteerOrganization.volunteer_id.in_(volunteer_ids)).delete(synchronize_session=False)
        
        # Clean up orphaned email and phone records
        Email.query.filter(Email.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        Phone.query.filter(Phone.contact_id.in_(volunteer_ids)).delete(synchronize_session=False)
        
        # Delete volunteers and their contact records
        Volunteer.query.filter(Volunteer.id.in_(volunteer_ids)).delete(synchronize_session=False)
        Contact.query.filter(Contact.id.in_(volunteer_ids)).delete(synchronize_session=False)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {len(volunteer_ids)} volunteers and associated records'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting volunteers: {str(e)}'
        }), 500
    
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
               Number_of_Attended_Volunteer_Sessions__c,
               Racial_Ethnic_Background__c,
               Last_Activity_Date__c,
               First_Volunteer_Date__c,
               Last_Non_Internal_Email_Activity__c,
               Description, Highest_Level_of_Educational__c, Age_Group__c,
               DoNotCall, npsp__Do_Not_Contact__c, HasOptedOutOfEmail,
               EmailBouncedDate,
               MailingAddress, npe01__Home_Address__c, npe01__Work_Address__c,
               npe01__Other_Address__c, npe01__Primary_Address_Type__c,
               npe01__Secondary_Address_Type__c,
               Connector_Active_Subscription__c,
               Connector_Active_Subscription_Name__c,
               Connector_Affiliations__c,
               Connector_Industry__c,
               Connector_Joining_Date__c,
               Connector_Last_Login_Date_Time__c,
               Connector_Last_Update_Date__c,
               Connector_Profile_Link__c,
               Connector_Role__c,
               Connector_SignUp_Role__c,
               Connector_User_ID__c
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
                is_new = False
                updates = []
                
                if not volunteer:
                    volunteer = Volunteer()
                    volunteer.salesforce_individual_id = row['Id']
                    db.session.add(volunteer)
                    is_new = True
                    updates.append('Created new volunteer')
                
                # Update volunteer fields only if they've changed
                if volunteer.salesforce_account_id != row['AccountId']:
                    volunteer.salesforce_account_id = row['AccountId']
                    updates.append('account_id')
                
                new_first_name = (row.get('FirstName') or '').strip()
                if volunteer.first_name != new_first_name:
                    volunteer.first_name = new_first_name
                    updates.append('first_name')
                
                new_last_name = (row.get('LastName') or '').strip()
                if volunteer.last_name != new_last_name:
                    volunteer.last_name = new_last_name
                    updates.append('last_name')
                
                new_middle_name = (row.get('MiddleName') or '').strip()
                if volunteer.middle_name != new_middle_name:
                    volunteer.middle_name = new_middle_name
                    updates.append('middle_name')
                
                new_org_name = (row.get('npsp__Primary_Affiliation__c') or '').strip()
                if volunteer.organization_name != new_org_name:
                    volunteer.organization_name = new_org_name
                    updates.append('organization')
                
                new_title = (row.get('Title') or '').strip()
                if volunteer.title != new_title:
                    volunteer.title = new_title
                    updates.append('title')
                
                new_department = (row.get('Department') or '').strip()
                if volunteer.department != new_department:
                    volunteer.department = new_department
                    updates.append('department')

                # Handle gender enum
                gender_str = (row.get('Gender__c') or '').lower().replace(' ', '_').strip()
                if gender_str and gender_str in [e.name for e in GenderEnum]:
                    if not volunteer.gender or volunteer.gender.name != gender_str:
                        volunteer.gender = GenderEnum[gender_str]
                        updates.append('gender')

                # Handle race/ethnicity
                race_ethnicity_map = {
                    'Bi-racial/Multi-racial/Multicultural': 'bi_multi_racial',
                    'Black': 'black_african',
                    'Black/African American': 'black',
                    'Prefer not to answer': 'prefer_not_to_say',
                    'Native American/Alaska Native/First Nation': 'native_american',
                    'White/Caucasian/European American': 'white_caucasian',
                    'Hispanic American/Latino': 'hispanic_american',
                    'Other POC': 'other_poc',
                    'Asian American/Pacific Islander': 'asian_pacific_islander'
                }
                
                # Set default mappings for common cases
                default_mapping = {
                    'Other POC': 'other',
                    'White/Caucasian/European American': 'white',
                    'Black': 'black',
                    'Bi-racial/Multi-racial/Multicultural': 'multi_racial'
                }
                
                race_ethnicity_str = row.get('Racial_Ethnic_Background__c')
                
                if race_ethnicity_str and race_ethnicity_str != 'None':
                    # Clean the string for comparison
                    cleaned_str = race_ethnicity_str.strip()
                    if 'AggregateResult' in cleaned_str:
                        cleaned_str = cleaned_str.replace('AggregateResult', '').strip()
                    
                    # Try primary mapping first
                    enum_value = race_ethnicity_map.get(cleaned_str)
                    
                    if enum_value and enum_value in [e.name for e in RaceEthnicityEnum]:
                        if not volunteer.race_ethnicity or volunteer.race_ethnicity.name != enum_value:
                            volunteer.race_ethnicity = RaceEthnicityEnum[enum_value]
                            updates.append('race_ethnicity')
                    else:
                        # Try default mapping if primary fails
                        default_value = default_mapping.get(cleaned_str)
                        if default_value and default_value in [e.name for e in RaceEthnicityEnum]:
                            if not volunteer.race_ethnicity or volunteer.race_ethnicity.name != default_value:
                                volunteer.race_ethnicity = RaceEthnicityEnum[default_value]
                                updates.append('race_ethnicity')
                elif volunteer.race_ethnicity != RaceEthnicityEnum.unknown:
                    volunteer.race_ethnicity = RaceEthnicityEnum.unknown
                    updates.append('race_ethnicity')

                # Handle dates
                new_birthdate = parse_date(row.get('Birthdate'))
                if volunteer.birthdate != new_birthdate:
                    volunteer.birthdate = new_birthdate
                    updates.append('birthdate')
                
                new_first_volunteer_date = parse_date(row.get('First_Volunteer_Date__c'))
                if volunteer.first_volunteer_date != new_first_volunteer_date:
                    volunteer.first_volunteer_date = new_first_volunteer_date
                    updates.append('first_volunteer_date')
                
                new_mailchimp_date = parse_date(row.get('Last_Mailchimp_Email_Date__c'))
                if volunteer.last_mailchimp_activity_date != new_mailchimp_date:
                    volunteer.last_mailchimp_activity_date = new_mailchimp_date
                    updates.append('mailchimp_date')
                
                new_volunteer_date = parse_date(row.get('Last_Volunteer_Date__c'))
                if volunteer.last_volunteer_date != new_volunteer_date:
                    volunteer.last_volunteer_date = new_volunteer_date
                    updates.append('volunteer_date')

                new_activity_date = parse_date(row.get('Last_Activity_Date__c'))
                if volunteer.last_activity_date != new_activity_date:
                    volunteer.last_activity_date = new_activity_date
                    updates.append('activity_date')
                
                new_email_date = parse_date(row.get('Last_Email_Message__c'))
                if volunteer.last_email_date != new_email_date:
                    volunteer.last_email_date = new_email_date
                    updates.append('email_date')
                
                new_non_internal_email_date = parse_date(row.get('Last_Non_Internal_Email_Activity__c'))
                if volunteer.last_non_internal_email_date != new_non_internal_email_date:
                    volunteer.last_non_internal_email_date = new_non_internal_email_date
                    updates.append('non_internal_email_date')
                
                new_notes = (row.get('Volunteer_Recruitment_Notes__c') or '').strip()
                if volunteer.notes != new_notes:
                    volunteer.notes = new_notes
                    updates.append('notes')

                # Handle description
                new_description = (row.get('Description') or '').strip()
                if volunteer.description != new_description:
                    volunteer.description = new_description
                    updates.append('description')

                # Handle education level
                education_str = (row.get('Highest_Level_of_Educational__c') or '').strip()
                if education_str:
                    # Map Salesforce education values to our enum
                    education_map = {
                        'High School': EducationEnum.HIGH_SCHOOL,
                        'Some College': EducationEnum.SOME_COLLEGE,
                        'Associates Degree': EducationEnum.ASSOCIATES,
                        'Bachelors Degree': EducationEnum.BACHELORS,
                        'Masters Degree': EducationEnum.MASTERS,
                        'Doctorate': EducationEnum.DOCTORATE,
                        'Professional Degree': EducationEnum.PROFESSIONAL,
                        'Other': EducationEnum.OTHER
                    }
                    new_education = education_map.get(education_str, EducationEnum.UNKNOWN)
                    if volunteer.education_level != new_education:
                        volunteer.education_level = new_education
                        updates.append('education_level')

                # Handle age group
                age_str = (row.get('Age_Group__c') or '').strip()
                if age_str:
                    # Map Salesforce age groups to our enum
                    age_map = {
                        'Under 18': AgeGroupEnum.UNDER_18,
                        '18-24': AgeGroupEnum.AGE_18_24,
                        '25-34': AgeGroupEnum.AGE_25_34,
                        '35-44': AgeGroupEnum.AGE_35_44,
                        '45-54': AgeGroupEnum.AGE_45_54,
                        '55-64': AgeGroupEnum.AGE_55_64,
                        '65+': AgeGroupEnum.AGE_65_PLUS
                    }
                    new_age_group = age_map.get(age_str, AgeGroupEnum.UNKNOWN)
                    if volunteer.age_group != new_age_group:
                        volunteer.age_group = new_age_group
                        updates.append('age_group')

                # Handle skills - only update if there are changes
                if row.get('Volunteer_Skills__c') or row.get('Volunteer_Skills_Text__c'):
                    new_skills = parse_skills(
                        row.get('Volunteer_Skills_Text__c', ''),
                        row.get('Volunteer_Skills__c', '')
                    )
                    current_skills = {skill.name for skill in volunteer.skills}
                    if set(new_skills) != current_skills:
                        # Clear existing skills
                        volunteer.skills = []
                        # Add new skills
                        for skill_name in new_skills:
                            skill = Skill.query.filter_by(name=skill_name).first()
                            if not skill:
                                skill = Skill(name=skill_name)
                                db.session.add(skill)
                            if skill not in volunteer.skills:
                                volunteer.skills.append(skill)
                        updates.append('skills')

                # Handle times_volunteered
                if row.get('Number_of_Attended_Volunteer_Sessions__c'):
                    try:
                        new_times = int(float(row['Number_of_Attended_Volunteer_Sessions__c']))
                        if volunteer.times_volunteered != new_times:
                            volunteer.times_volunteered = new_times
                            updates.append('times_volunteered')
                    except (ValueError, TypeError):
                        if volunteer.times_volunteered != 0:
                            volunteer.times_volunteered = 0
                            updates.append('times_volunteered')
                
                # Handle contact preferences
                new_do_not_call = bool(row.get('DoNotCall'))
                if volunteer.do_not_call != new_do_not_call:
                    volunteer.do_not_call = new_do_not_call
                    updates.append('do_not_call')

                new_do_not_contact = bool(row.get('npsp__Do_Not_Contact__c'))
                if volunteer.do_not_contact != new_do_not_contact:
                    volunteer.do_not_contact = new_do_not_contact
                    updates.append('do_not_contact')

                new_email_opt_out = bool(row.get('HasOptedOutOfEmail'))
                if volunteer.email_opt_out != new_email_opt_out:
                    volunteer.email_opt_out = new_email_opt_out
                    updates.append('email_opt_out')

                # Handle email bounce date
                new_bounce_date = parse_date(row.get('EmailBouncedDate'))
                if volunteer.email_bounced_date != new_bounce_date:
                    volunteer.email_bounced_date = new_bounce_date
                    updates.append('email_bounced_date')

                # Handle emails
                email_fields = {
                    'npe01__WorkEmail__c': ContactTypeEnum.professional,
                    'Email': ContactTypeEnum.personal,
                    'npe01__HomeEmail__c': ContactTypeEnum.personal,
                    'npe01__AlternateEmail__c': ContactTypeEnum.personal
                }
                
                # Get preferred email type
                preferred_email = row.get('npe01__Preferred_Email__c', '').lower()
                email_changes = False
                
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
                        email_changes = True
                    else:
                        # Update existing email type and primary status if changed
                        if email.type != email_type:
                            email.type = email_type
                            email_changes = True
                        if is_primary and not email.primary:
                            # Set all other emails to non-primary
                            Email.query.filter_by(
                                contact_id=volunteer.id,
                                primary=True
                            ).update({'primary': False})
                            email.primary = True
                            email_changes = True

                if email_changes:
                    updates.append('emails')

                # Handle phone numbers
                phone_fields = {
                    'npe01__WorkPhone__c': ContactTypeEnum.professional,
                    'Phone': ContactTypeEnum.professional,  # Business Phone
                    'HomePhone': ContactTypeEnum.personal,
                    'MobilePhone': ContactTypeEnum.personal
                }
                
                # Get preferred phone type
                preferred_phone = row.get('npe01__PreferredPhone__c', '').lower()
                phone_changes = False
                
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
                        phone_changes = True
                    else:
                        # Update existing phone type and primary status if changed
                        if phone.type != phone_type:
                            phone.type = phone_type
                            phone_changes = True
                        if is_primary and not phone.primary:
                            # Set all other phones to non-primary
                            Phone.query.filter_by(
                                contact_id=volunteer.id,
                                primary=True
                            ).update({'primary': False})
                            phone.primary = True
                            phone_changes = True

                if phone_changes:
                    updates.append('phones')

                # Handle addresses
                mailing_address = row.get('MailingAddress', {})
                if isinstance(mailing_address, dict):
                    # Find or create mailing address
                    mailing = next((addr for addr in volunteer.addresses 
                                  if addr.type == ContactTypeEnum.personal and addr.primary), None)
                    if not mailing:
                        mailing = Address(contact_id=volunteer.id, 
                                        type=ContactTypeEnum.personal,
                                        primary=True)
                        volunteer.addresses.append(mailing)
                        updates.append('mailing_address_created')

                    # Update mailing address fields
                    if mailing.address_line1 != mailing_address.get('street', ''):
                        mailing.address_line1 = mailing_address.get('street', '')
                        updates.append('mailing_street')
                    if mailing.city != mailing_address.get('city', ''):
                        mailing.city = mailing_address.get('city', '')
                        updates.append('mailing_city')
                    if mailing.state != mailing_address.get('state', ''):
                        mailing.state = mailing_address.get('state', '')
                        updates.append('mailing_state')
                    if mailing.zip_code != mailing_address.get('postalCode', ''):
                        mailing.zip_code = mailing_address.get('postalCode', '')
                        updates.append('mailing_zip')
                    if mailing.country != mailing_address.get('country', ''):
                        mailing.country = mailing_address.get('country', '')
                        updates.append('mailing_country')

                # Handle work address if present
                work_address = row.get('npe01__Work_Address__c', '')
                if work_address:
                    work = next((addr for addr in volunteer.addresses 
                               if addr.type == ContactTypeEnum.professional), None)
                    if not work:
                        work = Address(contact_id=volunteer.id,
                                     type=ContactTypeEnum.professional)
                        volunteer.addresses.append(work)
                        updates.append('work_address_created')
                    
                    # Parse work address string
                    try:
                        parts = work_address.split(',')
                        if len(parts) >= 1:
                            work.address_line1 = parts[0].strip()
                        if len(parts) >= 2:
                            work.city = parts[1].strip()
                        if len(parts) >= 3:
                            state_zip = parts[2].strip().split()
                            if len(state_zip) >= 1:
                                work.state = state_zip[0]
                            if len(state_zip) >= 2:
                                work.zip_code = state_zip[1]
                        updates.append('work_address_updated')
                    except Exception as e:
                        print(f"Error parsing work address for {volunteer.first_name} {volunteer.last_name}: {str(e)}")

                # Set address types based on primary/secondary preferences
                primary_type = (row.get('npe01__Primary_Address_Type__c') or '').lower()
                secondary_type = (row.get('npe01__Secondary_Address_Type__c') or '').lower()
                
                for addr in volunteer.addresses:
                    is_home = addr.type == ContactTypeEnum.personal
                    is_work = addr.type == ContactTypeEnum.professional
                    
                    # Set primary based on preference
                    if (primary_type == 'home' and is_home) or (primary_type == 'work' and is_work):
                        addr.primary = True
                    elif (secondary_type == 'home' and is_home) or (secondary_type == 'work' and is_work):
                        addr.primary = False

                # Handle Connector data
                connector_data = {
                    'active_subscription': (row.get('Connector_Active_Subscription__c') or '').strip().upper() or 'NONE',
                    'active_subscription_name': (row.get('Connector_Active_Subscription_Name__c') or '').strip(),
                    'affiliations': (row.get('Connector_Affiliations__c') or '').strip(),
                    'industry': (row.get('Connector_Industry__c') or '').strip(),
                    'joining_date': (row.get('Connector_Joining_Date__c') or '').strip(),
                    'last_login_datetime': (row.get('Connector_Last_Login_Date_Time__c') or '').strip(),
                    'last_update_date': parse_date(row.get('Connector_Last_Update_Date__c')),
                    'profile_link': (row.get('Connector_Profile_Link__c') or '').strip(),
                    'role': (row.get('Connector_Role__c') or '').strip(),
                    'signup_role': (row.get('Connector_SignUp_Role__c') or '').strip(),
                    'user_auth_id': (row.get('Connector_User_ID__c') or '').strip()
                }

                # Create or update connector data
                if not volunteer.connector:
                    volunteer.connector = ConnectorData(volunteer_id=volunteer.id)
                    updates.append('connector_created')

                # Update connector fields if they exist in Salesforce data
                if connector_data['active_subscription'] in [e.name for e in ConnectorSubscriptionEnum]:
                    if volunteer.connector.active_subscription != ConnectorSubscriptionEnum[connector_data['active_subscription']]:
                        volunteer.connector.active_subscription = ConnectorSubscriptionEnum[connector_data['active_subscription']]
                        updates.append('connector_subscription')

                for field, value in connector_data.items():
                    if field != 'active_subscription' and value:  # Skip active_subscription as it's handled above
                        current_value = getattr(volunteer.connector, field)
                        if current_value != value:
                            setattr(volunteer.connector, field, value)
                            updates.append(f'connector_{field}')

                success_count += 1
                status = 'Created' if is_new else 'Updated'
                if updates:
                    processed_volunteers.append(f"{volunteer.first_name} {volunteer.last_name} ({status}: {', '.join(updates)})")
                
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

            if processed_volunteers:
                print("\nVolunteers with changes:")
                for volunteer in processed_volunteers:
                    print(f"- {volunteer}")

            return jsonify({
                'success': True,
                'message': f'Successfully processed {success_count} volunteers ({len(processed_volunteers)} with changes) with {error_count} errors'
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Database commit error: {str(e)}'
            }), 500

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500