from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import login_required
import pandas as pd
import os
from models import db
from models.student import Student
from models.teacher import Teacher, TeacherStatus
from models.contact import Email, Phone, GenderEnum, RaceEthnicityEnum
from models.class_model import Class
from models.school_model import School
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from config import Config
from routes.utils import parse_date
from models.event import Event, EventType
from models.attendance import EventAttendanceDetail
from datetime import datetime, date, timedelta
from sqlalchemy import func

attendance = Blueprint('attendance', __name__)

@attendance.route('/attendance')
@login_required
def view_attendance():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query with pagination
    students = Student.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    teachers = Teacher.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Calculate total pages for both tables
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    
    return render_template(
        'attendance/attendance.html',
        students=students,
        teachers=teachers,
        current_page=page,
        per_page=per_page,
        total_students=total_students,
        total_teachers=total_teachers,
        per_page_options=[10, 25, 50, 100]
    )

@attendance.route('/attendance/import')
@login_required
def import_attendance():
    return render_template('attendance/import.html')

@attendance.route('/attendance/quick-import/<type>', methods=['POST'])
@login_required
def quick_import(type):
    try:
        # Define file paths
        data_folder = os.path.join(current_app.root_path, 'data')
        filename = 'Students.csv' if type == 'students' else 'Teachers.csv'
        file_path = os.path.join(data_folder, filename)

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            return jsonify({'status': 'error', 'message': 'Unable to read file with supported encodings'})

        # Clean the data
        for column in df.columns:
            if df[column].dtype == 'object':
                df[column] = df[column].apply(lambda x: str(x).strip() if pd.notnull(x) else '')

        # Process the data based on type
        if type == 'students':
            results = process_student_data(df)
        else:
            results = process_teacher_data(df)

        return jsonify(results)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@attendance.route('/attendance/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'})

        file = request.files['file']
        type = request.form.get('type', 'students')

        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'})

        if not file.filename.endswith('.csv'):
            return jsonify({'status': 'error', 'message': 'Only CSV files are allowed'})

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file, encoding=encoding, low_memory=False)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            return jsonify({'status': 'error', 'message': 'Unable to read file with supported encodings'})

        # Clean the data
        for column in df.columns:
            if df[column].dtype == 'object':
                df[column] = df[column].apply(lambda x: str(x).strip() if pd.notnull(x) else '')
        
        # Process the data based on type
        if type == 'students':
            results = process_student_data(df)
        else:
            results = process_teacher_data(df)

        return jsonify(results)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def process_student_data(df):
    success_count = 0
    errors = []

    try:
        for index, row in df.iterrows():
            try:
                # Get required fields
                first_name = str(row.get('FirstName', '')).strip()
                last_name = str(row.get('LastName', '')).strip()
                
                if not first_name or not last_name:
                    errors.append(f"Missing required name fields for student: {first_name} {last_name}")
                    continue

                # Check if student exists
                existing_student = Student.query.filter_by(
                    salesforce_individual_id=row['Id']
                ).first()

                if existing_student:
                    # Update existing student
                    existing_student.first_name = first_name
                    existing_student.last_name = last_name
                    student = existing_student
                else:
                    # Create new student with required fields first
                    student = Student(
                        first_name=first_name,
                        last_name=last_name
                    )
                
                # Now set additional fields
                student.student_id = str(row.get('Local_Student_ID__c', '')).strip() or None
                student.school_id = str(row.get('npsp__Primary_Affiliation__c', '')).strip() or None
                student.legacy_grade = str(row.get('Legacy_Grade__c', '')).strip() or None
                student.current_grade = int(row.get('Current_Grade__c', 0)) if pd.notna(row.get('Current_Grade__c')) else None
                
                # Handle birthdate
                if row.get('Birthdate'):
                    student.birthdate = pd.to_datetime(row['Birthdate']).date()

                # Handle gender using GenderEnum
                gender_value = row.get('Gender__c')
                if gender_value:
                    gender_key = gender_value.lower().replace(' ', '_')
                    try:
                        student.gender = GenderEnum[gender_key]
                    except KeyError:
                        errors.append(f"Student {first_name} {last_name}: Invalid gender value: {gender_value}")

                # Handle racial/ethnic background
                racial_ethnic = row.get('Racial_Ethnic_Background__c')
                if racial_ethnic:
                    try:
                        student.racial_ethnic = map_racial_ethnic_value(racial_ethnic)
                    except Exception as e:
                        errors.append(f"Student {first_name} {last_name}: Error processing racial/ethnic value: {racial_ethnic} - {str(e)}")

                # Handle class relationship
                class_salesforce_id = str(row.get('Class__c', '')).strip()
                if class_salesforce_id:
                    # Check if the class exists
                    class_obj = Class.query.filter_by(salesforce_id=class_salesforce_id).first()
                    if class_obj:
                        student.class_id = class_salesforce_id
                    else:
                        errors.append(f"Student {first_name} {last_name}: Referenced class {class_salesforce_id} not found")

                # Add school relationship handling
                school_salesforce_id = str(row.get('npsp__Primary_Affiliation__c', '')).strip()
                if school_salesforce_id:
                    school = School.query.get(school_salesforce_id)
                    if school:
                        student.school_id = school_salesforce_id
                    else:
                        errors.append(f"Student {first_name} {last_name}: Referenced school {school_salesforce_id} not found")

                if not existing_student:
                    db.session.add(student)
                
                db.session.flush()

                # Handle email after student is saved
                email_address = str(row.get('Email', '')).strip()
                if email_address:
                    existing_email = Email.query.filter_by(
                        contact_id=student.id,
                        email=email_address,
                        primary=True
                    ).first()
                    
                    if not existing_email:
                        email = Email(
                            contact_id=student.id,
                            email=email_address,
                            type='personal',
                            primary=True
                        )
                        db.session.add(email)

                # Handle phone after student is saved
                phone_number = str(row.get('Phone', '')).strip()
                if phone_number:
                    existing_phone = Phone.query.filter_by(
                        contact_id=student.id,
                        number=phone_number,
                        primary=True
                    ).first()
                    
                    if not existing_phone:
                        phone = Phone(
                            contact_id=student.id,
                            number=phone_number,
                            type='personal',
                            primary=True
                        )
                        db.session.add(phone)

                success_count += 1

            except Exception as e:
                errors.append(f"Error processing student {first_name} {last_name}: {str(e)}")
                db.session.rollback()
                continue

        db.session.commit()
        print(f"Import complete - Created/Updated: {success_count}, Errors: {len(errors)}")
        return {
            'status': 'success', 
            'message': f'Processed {success_count + len(errors)} students ({success_count} successful, {len(errors)} errors)',
            'errors': errors
        }

    except Exception as e:
        db.session.rollback()
        return {
            'status': 'error', 
            'message': str(e), 
            'errors': errors
        }

def process_teacher_data(df):
    success_count = 0
    errors = []

    try:
        for _, row in df.iterrows():
            try:
                # Get required fields
                first_name = str(row.get('FirstName', '')).strip()
                last_name = str(row.get('LastName', '')).strip()
                
                # Track missing fields
                missing_fields = []
                if not first_name:
                    missing_fields.append('FirstName')
                if not last_name:
                    missing_fields.append('LastName')

                if missing_fields:
                    errors.append(f"Teacher {first_name} {last_name}: Missing required fields: {', '.join(missing_fields)}")
                    continue

                # Get email (optional but needed for lookup)
                email_address = str(row.get('Email', '')).strip()

                # First check if a teacher exists with this email
                teacher = None
                if email_address:
                    email = Email.query.filter_by(email=email_address).first()
                    if email:
                        teacher = Teacher.query.get(email.contact_id)

                # If no teacher found by email, create new one
                if not teacher:
                    teacher = Teacher(
                        first_name=first_name,
                        last_name=last_name,
                        middle_name='',  # Explicitly set empty string
                        type='teacher'
                    )
                    db.session.add(teacher)
                    db.session.flush()  # Get ID for relationships
                    
                    # Create email record if provided
                    if email_address:
                        email = Email(
                            contact_id=teacher.id,
                            email=email_address,
                            type='professional',
                            primary=True
                        )
                        db.session.add(email)

                # Update teacher fields
                teacher.salesforce_individual_id = row['Id']
                teacher.salesforce_account_id = row.get('AccountId')
                teacher.first_name = row.get('FirstName', '')
                teacher.last_name = row.get('LastName', '')
                teacher.school_id = row.get('npsp__Primary_Affiliation__c')
                teacher.department = row.get('Department')

                # Set default status for new teachers
                if not teacher.status:
                    teacher.status = TeacherStatus.ACTIVE

                # Handle gender using GenderEnum
                gender_value = row.get('Gender__c')
                if gender_value:
                    # Convert to lowercase and replace spaces with underscores for enum matching
                    gender_key = gender_value.lower().replace(' ', '_')
                    try:
                        teacher.gender = GenderEnum[gender_key]
                    except KeyError:
                        errors.append(f"Teacher {first_name} {last_name}: Invalid gender value: {gender_value}")
                
                # Phone handling
                phone_number = str(row.get('Phone', '')).strip()
                if phone_number:
                    existing_phone = Phone.query.filter_by(
                        contact_id=teacher.id,
                        number=phone_number,
                        primary=True
                    ).first()
                    
                    if not existing_phone:
                        phone = Phone(
                            contact_id=teacher.id,
                            number=phone_number,
                            type='professional',
                            primary=True
                        )
                        db.session.add(phone)

                # Email tracking
                if row.get('Last_Email_Message__c'):
                    teacher.last_email_message = pd.to_datetime(row['Last_Email_Message__c']).date()
                if row.get('Last_Mailchimp_Email_Date__c'):
                    teacher.last_mailchimp_date = pd.to_datetime(row['Last_Mailchimp_Email_Date__c']).date()

                success_count += 1

            except Exception as e:
                errors.append(f"Error processing teacher {first_name} {last_name}: {str(e)}")

        db.session.commit()
        return {'status': 'success', 'success': success_count, 'errors': errors}

    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e), 'errors': errors}

def map_racial_ethnic_value(value):
    """Clean and standardize racial/ethnic values from Salesforce."""
    if not value:
        return None
        
    # Clean the input
    value = value.strip()
    
    # Return the cleaned value directly
    return value

@attendance.route('/attendance/purge', methods=['POST'])
@login_required
def purge_attendance():
    try:
        # Get the type from request, default to 'all'
        purge_type = request.json.get('type', 'all')
        
        if purge_type == 'students' or purge_type == 'all':
            # Delete all students
            Student.query.delete()
            db.session.commit()
            
        if purge_type == 'teachers' or purge_type == 'all':
            # Delete all teachers
            Teacher.query.delete()
            db.session.commit()
            
        return jsonify({
            'status': 'success', 
            'message': f'Successfully purged {purge_type} data'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@attendance.route('/attendance/view/<type>/<int:id>')
@login_required
def view_details(type, id):
    try:
        if type == 'student':
            contact = Student.query.get_or_404(id)
        elif type == 'teacher':
            contact = Teacher.query.get_or_404(id)
        else:
            return jsonify({'status': 'error', 'message': 'Invalid type'})
        
        # Get related data
        primary_email = contact.emails.filter_by(primary=True).first()
        primary_phone = contact.phones.filter_by(primary=True).first()
        primary_address = contact.addresses.filter_by(primary=True).first()
        
        return render_template(
            'attendance/view_details.html',
            contact=contact,
            type=type,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address
        )
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@attendance.route('/attendance/import-from-salesforce', methods=['POST'])
@login_required
def import_teachers_from_salesforce():
    try:
        print("Starting teacher import from Salesforce...")
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

        # Query for teachers
        teacher_query = """
        SELECT Id, AccountId, FirstName, LastName, Email, 
               npsp__Primary_Affiliation__c, Department, Gender__c, 
               Phone, Last_Email_Message__c, Last_Mailchimp_Email_Date__c
        FROM Contact
        WHERE Contact_Type__c = 'Teacher'
        """

        # Execute query
        result = sf.query_all(teacher_query)
        teacher_rows = result.get('records', [])

        # Process each teacher
        for row in teacher_rows:
            try:
                # Check if teacher exists
                teacher = Teacher.query.filter_by(salesforce_individual_id=row['Id']).first()
                if not teacher:
                    teacher = Teacher()
                    db.session.add(teacher)

                # Update teacher fields
                teacher.salesforce_individual_id = row['Id']
                teacher.salesforce_account_id = row.get('AccountId')
                teacher.first_name = row.get('FirstName', '')
                teacher.last_name = row.get('LastName', '')
                teacher.school_id = row.get('npsp__Primary_Affiliation__c')
                teacher.department = row.get('Department')

                # Set default status for new teachers
                if not teacher.status:
                    teacher.status = TeacherStatus.ACTIVE

                # Handle gender using GenderEnum
                gender_value = row.get('Gender__c')
                if gender_value:
                    gender_key = gender_value.lower().replace(' ', '_')
                    try:
                        teacher.gender = GenderEnum[gender_key]
                    except KeyError:
                        errors.append(f"Teacher {teacher.first_name} {teacher.last_name}: Invalid gender value: {gender_value}")

                # Handle dates
                if row.get('Last_Email_Message__c'):
                    teacher.last_email_message = parse_date(row['Last_Email_Message__c'])
                if row.get('Last_Mailchimp_Email_Date__c'):
                    teacher.last_mailchimp_date = parse_date(row['Last_Mailchimp_Email_Date__c'])

                success_count += 1
                
                # Save the teacher first to get the ID
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    error_count += 1
                    errors.append(f"Error saving teacher {teacher.first_name} {teacher.last_name}: {str(e)}")
                    continue

                # Now handle email and phone in a new transaction
                try:
                    # Handle email after teacher is saved
                    email_address = row.get('Email')
                    if email_address and isinstance(email_address, str):
                        email_address = email_address.strip()
                        if email_address:  # Check if non-empty after stripping
                            existing_email = Email.query.filter_by(
                                contact_id=teacher.id,
                                email=email_address,
                                primary=True
                            ).first()
                            
                            if not existing_email:
                                email = Email(
                                    contact_id=teacher.id,
                                    email=email_address,
                                    type='professional',
                                    primary=True
                                )
                                db.session.add(email)

                    # Handle phone after teacher is saved
                    phone_number = row.get('Phone')
                    if phone_number and isinstance(phone_number, str):
                        phone_number = phone_number.strip()
                        if phone_number:  # Check if non-empty after stripping
                            existing_phone = Phone.query.filter_by(
                                contact_id=teacher.id,
                                number=phone_number,
                                primary=True
                            ).first()
                            
                            if not existing_phone:
                                phone = Phone(
                                    contact_id=teacher.id,
                                    number=phone_number,
                                    type='professional',
                                    primary=True
                                )
                                db.session.add(phone)

                    # Commit email and phone changes
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Error saving contact info for teacher {teacher.first_name} {teacher.last_name}: {str(e)}")
                    # Don't increment error_count since the teacher was saved successfully

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing teacher {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}")
                continue

        print(f"Teacher import complete: {success_count} successes, {error_count} errors")
        if errors:
            print("Teacher import errors:")
            for error in errors:
                print(f"  - {error}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} teachers with {error_count} errors',
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        print("Salesforce authentication failed")
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Teacher import failed with error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@attendance.route('/attendance/import-students-from-salesforce', methods=['POST'])
@login_required
def import_students_from_salesforce():
    try:
        chunk_size = request.json.get('chunk_size', 2000)  # Reduced to 2000 to stay within limits
        last_id = request.json.get('last_id', None)  # Use ID-based pagination instead of offset
        
        print(f"Starting student import from Salesforce (chunk_size: {chunk_size}, last_id: {last_id})...")
        
        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # First, get total count
        count_query = """
        SELECT COUNT(Id) total
        FROM Contact 
        WHERE Contact_Type__c = 'Student'
        """
        result = sf.query(count_query)
        total_records = result['records'][0]['total']
        
        # Query for students using ID-based pagination
        base_query = """
        SELECT Id, AccountId, FirstName, LastName, MiddleName, Email, Phone,
               Local_Student_ID__c, Birthdate, Gender__c, Racial_Ethnic_Background__c,
               npsp__Primary_Affiliation__c, Class__c, Legacy_Grade__c, Current_Grade__c
        FROM Contact
        WHERE Contact_Type__c = 'Student'
        {where_clause}
        ORDER BY Id
        LIMIT {limit}
        """

        # Add WHERE clause for ID-based pagination
        where_clause = f"AND Id > '{last_id}'" if last_id else ""
        query = base_query.format(where_clause=where_clause, limit=chunk_size)
        
        print(f"Fetching students from Salesforce (chunk_size: {chunk_size}, last_id: {last_id})...")
        result = sf.query(query)
        student_rows = result.get('records', [])
        
        success_count = 0
        error_count = 0
        errors = []
        processed_ids = []
        
        # Process chunk
        for row in student_rows:
            try:
                # Get required fields
                first_name = str(row.get('FirstName', '')).strip()
                last_name = str(row.get('LastName', '')).strip()
                sf_id = row['Id']

                if not first_name or not last_name:
                    error_count += 1
                    errors.append(f"Missing required name fields for student with Salesforce ID {sf_id}")
                    continue

                # Check if student exists by Salesforce ID
                student = Student.query.filter_by(
                    salesforce_individual_id=sf_id
                ).first()

                if not student:
                    student = Student()
                    student.salesforce_individual_id = sf_id
                    student.salesforce_account_id = row.get('AccountId')

                # Update student fields
                student.first_name = first_name
                student.last_name = last_name
                student.middle_name = str(row.get('MiddleName', '')).strip() or None
                student.birthdate = pd.to_datetime(row['Birthdate']).date() if row.get('Birthdate') else None
                student.student_id = str(row.get('Local_Student_ID__c', '')).strip() or None
                student.school_id = str(row.get('npsp__Primary_Affiliation__c', '')).strip() or None
                student.class_id = str(row.get('Class__c', '')).strip() or None
                student.legacy_grade = str(row.get('Legacy_Grade__c', '')).strip() or None
                student.current_grade = int(row.get('Current_Grade__c', 0)) if pd.notna(row.get('Current_Grade__c')) else None

                # Handle gender
                gender_value = row.get('Gender__c')
                if gender_value:
                    gender_key = gender_value.lower().replace(' ', '_')
                    try:
                        student.gender = GenderEnum[gender_key]
                    except KeyError:
                        errors.append(f"Invalid gender value for {first_name} {last_name}: {gender_value}")

                # Handle racial/ethnic background
                racial_ethnic = row.get('Racial_Ethnic_Background__c')
                if racial_ethnic:
                    try:
                        student.racial_ethnic = map_racial_ethnic_value(racial_ethnic)
                    except Exception as e:
                        errors.append(f"Error processing racial/ethnic value for {first_name} {last_name}: {racial_ethnic}")

                if not student.id:
                    db.session.add(student)
                
                # Commit each student individually to prevent large transaction blocks
                db.session.commit()

                # Handle contact info
                try:
                    # Handle email
                    email_address = str(row.get('Email', '')).strip()
                    if email_address:
                        existing_email = Email.query.filter_by(
                            contact_id=student.id,
                            type='personal'
                        ).first()
                        
                        if existing_email:
                            existing_email.email = email_address
                        else:
                            email_record = Email(
                                contact_id=student.id,
                                email=email_address,
                                type='personal',
                                primary=True
                            )
                            db.session.add(email_record)

                    # Handle phone
                    phone_number = str(row.get('Phone', '')).strip()
                    if phone_number:
                        existing_phone = Phone.query.filter_by(
                            contact_id=student.id,
                            type='personal'
                        ).first()
                        
                        if existing_phone:
                            existing_phone.number = phone_number
                        else:
                            phone_record = Phone(
                                contact_id=student.id,
                                number=phone_number,
                                type='personal',
                                primary=True
                            )
                            db.session.add(phone_record)

                    # Commit contact info
                    db.session.commit()
                    success_count += 1
                    processed_ids.append(sf_id)

                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Error processing contact info for {first_name} {last_name}: {str(e)}")
                    error_count += 1

            except Exception as e:
                db.session.rollback()
                errors.append(f"Error processing student {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}")
                error_count += 1
                continue

        # Get the last processed ID for the next chunk
        next_id = processed_ids[-1] if processed_ids else None
        is_complete = len(student_rows) < chunk_size  # If we got fewer records than chunk_size, we're done

        print(f"\nChunk complete - Created/Updated: {success_count}, Errors: {error_count}")
        if errors:
            print("\nErrors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"- {error}")
                
        return {
            'status': 'success',
            'message': f'Processed chunk of {len(student_rows)} students ({success_count} successful, {error_count} errors)',
            'total_records': total_records,
            'processed_count': len(processed_ids),
            'next_id': next_id if not is_complete else None,
            'is_complete': is_complete,
            'errors': errors[:100],  # Limit error list size in response
            'processed_ids': processed_ids
        }

    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        print(f"Error: {error_msg}")
        return {
            'status': 'error',
            'message': error_msg,
            'errors': [str(e)]
        }

def get_academic_year_range(today=None):
    today = today or date.today()
    year = today.year
    if today.month < 8:
        start = date(year-1, 8, 1)
        end = date(year, 7, 31)
    else:
        start = date(year, 8, 1)
        end = date(year+1, 7, 31)
    return start, end

@attendance.route('/attendance/impact')
@login_required
def attendance_impact():
    year_param = request.args.get('year', type=int)
    today = date.today()
    current_year = today.year if today.month >= 8 else today.year - 1
    academic_years = [current_year - i for i in range(5)]
    academic_years.sort(reverse=True)
    selected_year = year_param or current_year
    start = date(selected_year, 8, 1)
    end = date(selected_year + 1, 7, 31)
    events = Event.query.filter(Event.start_date >= start, Event.start_date <= end).order_by(Event.start_date).all()
    # Get unique event types for this year, as value/label dicts
    event_types = (
        db.session.query(Event.type)
        .filter(Event.start_date >= start, Event.start_date <= end)
        .distinct()
        .all()
    )
    event_types = [et[0] for et in event_types if et[0]]
    event_types = [
        {'value': et.value, 'label': et.value.replace('_', ' ').title()} for et in event_types
    ]
    event_types = sorted(event_types, key=lambda x: x['label'])
    return render_template('attendance/impact.html', events=events, academic_years=academic_years, selected_year=selected_year, event_types=event_types)

@attendance.route('/attendance/impact/events_json')
@login_required
def attendance_impact_events_json():
    year = request.args.get('year', type=int)
    types = request.args.getlist('types[]')
    start = date(year, 8, 1)
    end = date(year + 1, 7, 31)
    q = Event.query.filter(Event.start_date >= start, Event.start_date <= end)
    if types:
        # Convert string values to Enum
        enum_types = [EventType(t) for t in types if t in EventType.__members__.values() or t in [e.value for e in EventType]]
        q = q.filter(Event.type.in_(enum_types))
    events = q.order_by(Event.start_date).all()
    def event_to_dict(event):
        d = {
            'id': event.id,
            'title': event.title,
            'start_date': event.start_date.strftime('%Y-%m-%d') if event.start_date else '',
            'type': event.type.value if event.type else '',
            'attendance_detail': None
        }
        if event.attendance_detail:
            ad = event.attendance_detail
            d['attendance_detail'] = {
                'num_classrooms': ad.num_classrooms,
                'students_per_volunteer': ad.students_per_volunteer,
                'total_students': ad.total_students,
                'attendance_in_sf': ad.attendance_in_sf,
                'pathway': ad.pathway,
                'groups_rotations': ad.groups_rotations,
                'is_stem': ad.is_stem,
                'attendance_link': ad.attendance_link
            }
        return d
    return jsonify([event_to_dict(e) for e in events])

@attendance.route('/attendance/impact/<int:event_id>/detail', methods=['GET'])
@login_required
def get_attendance_detail(event_id):
    event = Event.query.get_or_404(event_id)
    detail = event.attendance_detail
    if not detail:
        # Return empty/default values if not set
        return jsonify({
            'num_classrooms': '',
            'students_per_volunteer': '',
            'total_students': '',
            'attendance_in_sf': False,
            'pathway': '',
            'groups_rotations': '',
            'is_stem': False,
            'attendance_link': ''
        })
    return jsonify({
        'num_classrooms': detail.num_classrooms,
        'students_per_volunteer': detail.students_per_volunteer,
        'total_students': detail.total_students,
        'attendance_in_sf': detail.attendance_in_sf,
        'pathway': detail.pathway,
        'groups_rotations': detail.groups_rotations,
        'is_stem': detail.is_stem,
        'attendance_link': detail.attendance_link
    })

@attendance.route('/attendance/impact/<int:event_id>/detail', methods=['POST'])
@login_required
def update_attendance_detail(event_id):
    event = Event.query.get_or_404(event_id)
    data = request.json
    detail = event.attendance_detail
    if not detail:
        detail = EventAttendanceDetail(event_id=event.id)
        db.session.add(detail)
    detail.num_classrooms = data.get('num_classrooms')
    detail.students_per_volunteer = data.get('students_per_volunteer')
    detail.total_students = data.get('total_students')
    detail.attendance_in_sf = data.get('attendance_in_sf', False)
    detail.pathway = data.get('pathway')
    detail.groups_rotations = data.get('groups_rotations')
    detail.is_stem = data.get('is_stem', False)
    detail.attendance_link = data.get('attendance_link')
    db.session.commit()
    return jsonify({'success': True})