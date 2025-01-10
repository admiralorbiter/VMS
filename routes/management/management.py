from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from models import db
from config import Config
from models.class_model import Class

management_bp = Blueprint('management', __name__)

@management_bp.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    return render_template('management/admin.html')

@management_bp.route('/admin/import', methods=['POST'])
@login_required
def import_data():
    if not current_user.is_admin:
        return {'error': 'Unauthorized'}, 403
    
    if 'import_file' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('management.admin'))
    
    file = request.files['import_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('management.admin'))

    # TODO: Process the file and import data
    # This will be implemented after creating the model
    
    flash('Import started successfully', 'success')
    return redirect(url_for('management.admin'))

@management_bp.route('/management/import-classes', methods=['POST'])
@login_required
def import_classes():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        print("Starting class import...")  # Debug log
        
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, Name, School__c, Class_Year_Number__c
        FROM Class__c
        """

        print("Connecting to Salesforce...")  # Debug log
        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        print("Executing Salesforce query...")  # Debug log
        # Execute the query
        result = sf.query_all(salesforce_query)
        sf_rows = result.get('records', [])
        print(f"Retrieved {len(sf_rows)} records from Salesforce")  # Debug log

        success_count = 0
        error_count = 0
        errors = []

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                print(f"Processing row: {row.get('Name')}")  # Debug log
                # Check if class exists
                existing_class = Class.query.filter_by(salesforce_id=row['Id']).first()
                
                if existing_class:
                    # Update existing class
                    existing_class.name = row['Name']
                    existing_class.school_salesforce_id = row['School__c']
                    existing_class.class_year = int(row['Class_Year_Number__c'])
                    print(f"Updated existing class: {row['Name']}")  # Debug log
                else:
                    # Create new class
                    new_class = Class(
                        salesforce_id=row['Id'],
                        name=row['Name'],
                        school_salesforce_id=row['School__c'],
                        class_year=int(row['Class_Year_Number__c'])
                    )
                    db.session.add(new_class)
                    print(f"Created new class: {row['Name']}")  # Debug log
                
                success_count += 1
            except Exception as e:
                error_count += 1
                error_msg = f"Error processing class {row.get('Name')}: {str(e)}"
                print(f"Error: {error_msg}")  # Debug log
                errors.append(error_msg)

        print("Committing changes to database...")  # Debug log
        # Commit changes
        db.session.commit()
        
        print("Import completed successfully")  # Debug log
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} classes with {error_count} errors',
            'errors': errors
        })

    except SalesforceAuthenticationFailed as sf_error:
        print(f"Salesforce authentication failed: {str(sf_error)}")  # Debug log
        return jsonify({
            'success': False,
            'message': f'Failed to authenticate with Salesforce: {str(sf_error)}'
        }), 401
    except Exception as e:
        print(f"Unexpected error during import: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': f'Import error: {str(e)}'}), 500

