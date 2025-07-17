"""
Student Routes Module
====================

This module handles all student-related functionality including:
- Student management and viewing
- Salesforce import for students
- Student-specific operations

Key Features:
- Student listing and pagination
- Salesforce data import with chunked processing
- Student detail views
- Contact information management
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.student import Student
from models.contact import Email, Phone, GenderEnum, ContactTypeEnum
from models.school_model import School
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from config import Config
from routes.utils import parse_date
import pandas as pd

# Create Blueprint for student routes
students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
@login_required
def view_students():
    """
    Main student management page showing paginated list of students.
    
    Returns:
        Rendered template with paginated student data
    """
    # Get pagination parameters from request
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query students with pagination
    students = Student.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Calculate total counts for pagination info
    total_students = Student.query.count()
    
    return render_template(
        'students/students.html',
        students=students,
        current_page=page,
        per_page=per_page,
        total_students=total_students,
        per_page_options=[10, 25, 50, 100]
    )

@students_bp.route('/students/import-from-salesforce', methods=['POST'])
@login_required
def import_students_from_salesforce():
    """
    Import student data from Salesforce with chunked processing.
    
    This function handles large datasets by processing them in chunks
    to avoid memory issues and stay within Salesforce API limits.
    
    Args:
        chunk_size: Number of records to process per chunk (default: 2000)
        last_id: ID of last processed record for pagination
        
    Returns:
        JSON response with chunk processing results
    """
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

        # First, get total count for progress tracking
        count_query = """
        SELECT COUNT(Id) total
        FROM Contact 
        WHERE Contact_Type__c = 'Student'
        """
        result = sf.query(count_query)
        if not result or 'records' not in result or not result['records']:
            return {
                'status': 'error',
                'message': 'Failed to get total record count from Salesforce',
                'errors': ['No records returned from Salesforce count query']
            }
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
        
        # Process each student in the chunk
        for row in student_rows:
            try:
                # Use the Student model's import method
                student, is_new, error = Student.import_from_salesforce(row, db.session)
                
                if error:
                    error_count += 1
                    errors.append(error)
                    continue
                
                if not student.id:
                    db.session.add(student)
                
                # Commit each student individually to prevent large transaction blocks
                db.session.commit()

                # Handle contact info using the student's method
                try:
                    success, error = student.update_contact_info(row, db.session)
                    if not success:
                        errors.append(error)
                    else:
                        db.session.commit()
                        success_count += 1
                        processed_ids.append(row['Id'])

                except Exception as e:
                    db.session.rollback()
                    errors.append(f"Error processing contact info for {student.first_name} {student.last_name}: {str(e)}")
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

@students_bp.route('/students/view/<int:id>')
@login_required
def view_student_details(id):
    """
    View detailed information for a specific student.
    
    Args:
        id: Database ID of the student
        
    Returns:
        Rendered template with detailed student information
    """
    try:
        student = Student.query.get_or_404(id)
        
        # Get related contact information
        primary_email = student.emails.filter_by(primary=True).first()
        primary_phone = student.phones.filter_by(primary=True).first()
        primary_address = student.addresses.filter_by(primary=True).first()
        
        return render_template(
            'students/view_details.html',
            student=student,
            primary_email=primary_email,
            primary_phone=primary_phone,
            primary_address=primary_address
        )
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def load_routes(bp):
    """Load student routes into the main blueprint"""
    bp.register_blueprint(students_bp) 