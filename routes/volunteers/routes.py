import csv
import io
import os
import json
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required
from models import Volunteer, db
from forms import VolunteerForm
from sqlalchemy import or_, and_

from models.history import History
from models.volunteer import Address, EducationEnum, Engagement, EventParticipation, GenderEnum, RaceEthnicityEnum, SalutationEnum, Skill, SuffixEnum, VolunteerSkill, Email, Phone, LocalStatusEnum
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

    # Apply sorting based on parameters
    if sort_by:
        sort_column = None
        if sort_by == 'name':
            sort_column = (Volunteer.first_name + ' ' + 
                          db.func.coalesce(Volunteer.middle_name, '') + ' ' + 
                          Volunteer.last_name)
        elif sort_by == 'organization':
            sort_column = Volunteer.organization_name
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
    form = VolunteerForm()
    if request.method == 'POST':
        print("Form data:", form.data)  # Debug form data
        print("Form errors:", form.errors)  # Debug validation errors
        print("Is submitted:", form.is_submitted())  # Debug submission status
        print("Is validated:", form.validate())  # Debug validation status
        
        try:
            volunteer = Volunteer(
                salutation=form.salutation.data,
                first_name=form.first_name.data,
                middle_name=form.middle_name.data or '',
                last_name=form.last_name.data,
                suffix=form.suffix.data or None,
                organization_name=form.organization_name.data or '',
                title=form.title.data or '',
                department=form.department.data or '',
                industry=form.industry.data or '',
                local_status=form.local_status.data,
                gender=form.gender.data if form.gender.data else None,
                race_ethnicity=form.race_ethnicity.data if form.race_ethnicity.data else None,
                notes=form.notes.data or ''
            )

            # Add email with type
            if form.email.data:  # Check if email exists
                email = Email(
                    email=form.email.data,
                    type=form.email_type.data or 'personal',  # Default to personal if not set
                    primary=True
                )
                volunteer.emails.append(email)

            # Add phone if provided
            if form.phone.data:
                phone = Phone(
                    number=form.phone.data,
                    type=form.phone_type.data or 'personal',  # Default to personal if not set
                    primary=True
                )
                volunteer.phones.append(phone)

            # Add skills - Fixed section
            if form.skills.data:
                # Parse the JSON string into a Python list
                skill_names = json.loads(form.skills.data)
                # Use a set to prevent duplicates
                unique_skill_names = set(skill_names)
                for skill_name in unique_skill_names:
                    if skill_name:
                        skill = Skill.query.filter_by(name=skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            db.session.add(skill)
                        volunteer.skills.append(skill)

            db.session.add(volunteer)
            db.session.commit()
            flash('Volunteer added successfully!', 'success')
            return redirect(url_for('volunteers.volunteers'))
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")  # Debug database errors
            flash(f'Error adding volunteer: {str(e)}', 'error')
            return render_template('/volunteers/add_volunteer.html', form=form)

    return render_template('/volunteers/add_volunteer.html', form=form)

@volunteers_bp.route('/volunteers/view/<int:id>')
@login_required
def view_volunteer(id):
    volunteer = Volunteer.query.get_or_404(id)
    
    # Get participations and group by status
    participations = EventParticipation.query.filter_by(volunteer_id=id).all()
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
                'date': participation.event.start_date
            })
    
    # Get history records for the volunteer
    histories = History.query.filter_by(
        volunteer_id=id, 
        is_deleted=False
    ).order_by(
        History.activity_date.desc()
    ).all()
    
    # Sort each list by date
    for status in participation_stats:
        participation_stats[status].sort(key=lambda x: x['date'], reverse=True)
    
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
        org_relationships=org_relationships  # Pass the relationships to the template
    )

@volunteers_bp.route('/volunteers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_volunteer(id):
    volunteer = Volunteer.query.get_or_404(id)
    form = VolunteerForm(obj=volunteer)
    
    if request.method == 'POST':
        try:
            # Convert empty strings to None for enum fields
            volunteer.salutation = None if form.salutation.data == 'none' else form.salutation.data
            volunteer.suffix = None if form.suffix.data == 'none' else form.suffix.data
            
            # Update basic information
            volunteer.first_name = form.first_name.data
            volunteer.middle_name = form.middle_name.data or None
            volunteer.last_name = form.last_name.data
            volunteer.organization_name = form.organization_name.data or None
            volunteer.title = form.title.data or None
            volunteer.department = form.department.data or None
            volunteer.industry = form.industry.data or None
            
            # Add new demographic fields
            volunteer.gender = form.gender.data if form.gender.data else None
            volunteer.race_ethnicity = form.race_ethnicity.data if form.race_ethnicity.data else None
            volunteer.education = form.education.data if form.education.data else None
            volunteer.local_status = form.local_status.data
            volunteer.notes = form.notes.data or None

            # Handle emails
            emails_data = json.loads(request.form.get('emails', '[]'))
            
            # Remove all existing emails
            for email in volunteer.emails:
                db.session.delete(email)
            
            # Add new emails
            for email_data in emails_data:
                email = Email(
                    email=email_data['email'],
                    type=email_data['type'],
                    primary=email_data['primary'],
                    volunteer=volunteer
                )
                db.session.add(email)

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
            
            # Handle skills
            skills_data = json.loads(request.form.get('skills', '[]'))
            
            # Remove all existing skills
            volunteer.skills = []
            
            # Add new skills
            for skill_name in skills_data:
                # Get or create skill
                skill = Skill.query.filter_by(name=skill_name).first()
                if not skill:
                    skill = Skill(name=skill_name)
                    db.session.add(skill)
                volunteer.skills.append(skill)
            
            db.session.commit()
            flash('Volunteer updated successfully!', 'success')
            return redirect(url_for('volunteers.view_volunteer', id=id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating volunteer: {str(e)}', 'error')
    
    return render_template('volunteers/edit.html', 
                         form=form, 
                         volunteer=volunteer,
                         GenderEnum=GenderEnum,
                         LocalStatusEnum=LocalStatusEnum,
                         RaceEthnicityEnum=RaceEthnicityEnum,
                         SalutationEnum=SalutationEnum,
                         SuffixEnum=SuffixEnum,
                         EducationEnum=EducationEnum)

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
                # Handle quickSync with different encodings
                default_file_path = os.path.join('data', 'Volunteers.csv')
                if not os.path.exists(default_file_path):
                    return jsonify({'error': 'Default CSV file not found'}), 404
                
                # Try different encodings
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(default_file_path, 'r', encoding=encoding) as file:
                            csv_data = csv.DictReader(file)
                            for row in csv_data:
                                success_count, error_count = process_volunteer_row(
                                    row, success_count, error_count, errors
                                )
                        break  # If successful, exit the encoding loop
                    except UnicodeDecodeError:
                        continue
                else:
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

            else:
                # Handle regular file upload with different encodings
                if 'file' not in request.files:
                    return jsonify({'error': 'No file uploaded'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not file.filename.endswith('.csv'):
                    return jsonify({'error': 'File must be a CSV'}), 400

                # Read the file content once
                file_content = file.read()
                
                # Try different encodings
                encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        stream = io.StringIO(file_content.decode(encoding), newline=None)
                        csv_data = csv.DictReader(stream)
                        for row in csv_data:
                            success_count, error_count = process_volunteer_row(
                                row, success_count, error_count, errors
                            )
                        break  # If successful, exit the encoding loop
                    except UnicodeDecodeError:
                        continue
                else:
                    return jsonify({'error': 'Could not decode file with any known encoding'}), 400

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

@volunteers_bp.route('/volunteers/purge', methods=['POST'])
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
    