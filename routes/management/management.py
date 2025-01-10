from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from models import db
from config import Config
from models.class_model import Class
from models.school_model import School

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
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, Name, School__c, Class_Year_Number__c
        FROM Class__c
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

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                # Check if class exists
                existing_class = Class.query.filter_by(salesforce_id=row['Id']).first()
                
                if existing_class:
                    # Update existing class
                    existing_class.name = row['Name']
                    existing_class.school_salesforce_id = row['School__c']
                    existing_class.class_year = int(row['Class_Year_Number__c'])
                else:
                    # Create new class
                    new_class = Class(
                        salesforce_id=row['Id'],
                        name=row['Name'],
                        school_salesforce_id=row['School__c'],
                        class_year=int(row['Class_Year_Number__c'])
                    )
                    db.session.add(new_class)
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing class {row.get('Name')}: {str(e)}")

        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} classes with {error_count} errors',
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@management_bp.route('/management/import-schools', methods=['POST'])
@login_required
def import_schools():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School'
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

        # Process each row from Salesforce
        for row in sf_rows:
            try:
                # Check if school exists
                existing_school = School.query.filter_by(id=row['Id']).first()
                
                if existing_school:
                    # Update existing school
                    existing_school.name = row['Name']
                    existing_school.district_id = row['ParentId']
                    existing_school.normalized_name = row['Connector_Account_Name__c']
                    existing_school.school_code = row['School_Code_External_ID__c']
                else:
                    # Create new school
                    new_school = School(
                        id=row['Id'],
                        name=row['Name'],
                        district_id=row['ParentId'],
                        normalized_name=row['Connector_Account_Name__c'],
                        school_code=row['School_Code_External_ID__c']
                    )
                    db.session.add(new_school)
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing school {row.get('Name')}: {str(e)}")

        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} schools with {error_count} errors',
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

