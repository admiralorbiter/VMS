from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import pandas as pd
import os
from models import db
from models.student import Student
from models.teacher import Teacher
from models.contact import Email

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
                # Check if student already exists
                student = Student.query.filter_by(student_id=str(row.get('Local_Student_ID__c', ''))).first()
                
                if not student:
                    student = Student()

                # Update student fields
                student.first_name = row.get('FirstName', '')
                student.last_name = row.get('LastName', '')
                student.email = row.get('Email', '')
                student.current_grade = int(row.get('Current_Grade__c', 0)) if pd.notna(row.get('Current_Grade__c')) else None
                student.student_id = str(row.get('Local_Student_ID__c', ''))
                student.school_code = str(row.get('AttendingSchoolCode__c', ''))
                student.ell_language = row.get('ELL_Language__c', '')
                student.gifted = bool(row.get('Gifted__c', False))
                student.lunch_status = row.get('Lunch_Status__c', '')

                db.session.add(student)
                success_count += 1

            except Exception as e:
                errors.append(f"Error processing student {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}")

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
                    errors.append(f"Teacher {row.get('FirstName', '')} {row.get('LastName', '')}: Missing required fields: {', '.join(missing_fields)}")
                    continue

                # Get email (optional but needed for lookup)
                email_address = str(row.get('Email', '')).strip()

                # First check if a teacher exists with this email
                teacher = None
                if email_address:
                    email = Email.query.filter_by(email=email_address).first()
                    if email:
                        teacher = Teacher.query.get(email.contact_id)

                if not teacher:
                    # Create new teacher with required fields
                    teacher = Teacher(
                        first_name=first_name,
                        last_name=last_name,
                        type='teacher'
                    )
                    db.session.add(teacher)
                    db.session.flush()
                    
                    # Create email record if provided
                    if email_address:
                        email = Email(
                            contact_id=teacher.id,
                            email=email_address,
                            type='professional',
                            primary=True
                        )
                        db.session.add(email)

                # Update optional teacher fields
                teacher.department = str(row.get('Department', '')).strip() or None
                teacher.school_code = str(row.get('AccountId', '')).strip() or None
                teacher.active = True
                teacher.connector_role = str(row.get('Title', '')).strip() or None

                success_count += 1
                
                # Commit every 100 records
                if success_count % 100 == 0:
                    db.session.commit()

            except Exception as e:
                errors.append(f"Error processing teacher {row.get('FirstName', '')} {row.get('LastName', '')}: {str(e)}")

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