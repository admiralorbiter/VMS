from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import pandas as pd
import os
from models import db
from models.student import Student
from models.teacher import Teacher
from models.contact import Email, Phone, GenderEnum, RaceEthnicityEnum

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
                    errors.append(f"Student {first_name} {last_name}: Missing required fields: {', '.join(missing_fields)}")
                    continue

                # Check if student already exists by Salesforce ID or student ID
                student = None
                salesforce_id = str(row.get('Id', '')).strip()
                student_id = str(row.get('Local_Student_ID__c', '')).strip()
                
                if salesforce_id:
                    student = Student.query.filter_by(salesforce_individual_id=salesforce_id).first()
                if not student and student_id:
                    student = Student.query.filter_by(student_id=student_id).first()
                
                if not student:
                    student = Student()

                # Update basic Contact fields
                student.salesforce_individual_id = salesforce_id
                student.salesforce_account_id = str(row.get('AccountId', '')).strip() or None
                student.first_name = first_name
                student.middle_name = str(row.get('MiddleName', '')).strip() or None
                student.last_name = last_name
                
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
                    racial_key = racial_ethnic.lower().replace(' ', '_').replace('/', '_')
                    try:
                        student.racial_ethnic = RaceEthnicityEnum[racial_key]
                    except KeyError:
                        errors.append(f"Student {first_name} {last_name}: Invalid racial/ethnic value: {racial_ethnic}")

                # Update student-specific fields
                student.student_id = student_id
                student.school_id = str(row.get('npsp__Primary_Affiliation__c', '')).strip() or None
                student.class_id = str(row.get('Class__c', '')).strip() or None
                student.legacy_grade = str(row.get('Legacy_Grade__c', '')).strip() or None
                student.current_grade = int(row.get('Current_Grade__c', 0)) if pd.notna(row.get('Current_Grade__c')) else None

                # Save the student first to get an ID
                db.session.add(student)
                db.session.flush()  # This will assign an ID to the student

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
                db.session.rollback()  # Rollback on error
                continue

        db.session.commit()
        return {'status': 'success', 'success': success_count, 'errors': errors}

    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e), 'errors': errors}

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
                teacher.school_id = str(row.get('npsp__Primary_Affiliation__c', '')).strip() or None
                teacher.department = str(row.get('Department', '')).strip() or None
                
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