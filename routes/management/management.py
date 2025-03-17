from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from models import db
from config import Config
from models.class_model import Class
from models.school_model import School
from models.district_model import District
from models.bug_report import BugReport, BugReportType
from datetime import datetime, timezone
from models.client_project_model import ClientProject, ProjectStatus

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
        print("Starting class import process...")
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
        
        print(f"Class import complete: {success_count} successes, {error_count} errors")
        if errors:
            print("Class import errors:")
            for error in errors:
                print(f"  - {error}")
        
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
        print("Starting school import process...")
        # First, import districts
        district_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School District'
        """

        # Connect to Salesforce
        sf = Salesforce(
            username=Config.SF_USERNAME,
            password=Config.SF_PASSWORD,
            security_token=Config.SF_SECURITY_TOKEN,
            domain='login'
        )

        # Execute district query first
        district_result = sf.query_all(district_query)
        district_rows = district_result.get('records', [])

        district_success = 0
        district_errors = []

        # Process districts
        for row in district_rows:
            try:
                existing_district = District.query.filter_by(salesforce_id=row['Id']).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.name = row['Name']
                    existing_district.district_code = row['School_Code_External_ID__c']
                else:
                    # Create new district
                    new_district = District(
                        salesforce_id=row['Id'],
                        name=row['Name'],
                        district_code=row['School_Code_External_ID__c']
                    )
                    db.session.add(new_district)
                
                district_success += 1
            except Exception as e:
                district_errors.append(f"Error processing district {row.get('Name')}: {str(e)}")

        # Commit district changes
        db.session.commit()
        
        print(f"District import complete: {district_success} successes, {len(district_errors)} errors")
        if district_errors:
            print("District errors:")
            for error in district_errors:
                print(f"  - {error}")

        # Now proceed with school import
        school_query = """
        SELECT Id, Name, ParentId, Connector_Account_Name__c, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School'
        """

        # Execute school query
        school_result = sf.query_all(school_query)
        school_rows = school_result.get('records', [])

        school_success = 0
        school_errors = []

        # Process schools
        for row in school_rows:
            try:
                existing_school = School.query.filter_by(id=row['Id']).first()
                
                # Find the district using salesforce_id
                district = District.query.filter_by(salesforce_id=row['ParentId']).first()
                
                if existing_school:
                    # Update existing school
                    existing_school.name = row['Name']
                    existing_school.district_id = district.id if district else None
                    existing_school.salesforce_district_id = row['ParentId']
                    existing_school.normalized_name = row['Connector_Account_Name__c']
                    existing_school.school_code = row['School_Code_External_ID__c']
                else:
                    # Create new school
                    new_school = School(
                        id=row['Id'],
                        name=row['Name'],
                        district_id=district.id if district else None,
                        salesforce_district_id=row['ParentId'],
                        normalized_name=row['Connector_Account_Name__c'],
                        school_code=row['School_Code_External_ID__c']
                    )
                    db.session.add(new_school)
                
                school_success += 1
            except Exception as e:
                school_errors.append(f"Error processing school {row.get('Name')}: {str(e)}")

        # Commit school changes
        db.session.commit()
        
        print(f"School import complete: {school_success} successes, {len(school_errors)} errors")
        if school_errors:
            print("School errors:")
            for error in school_errors:
                print(f"  - {error}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {district_success} districts and {school_success} schools',
            'district_errors': district_errors,
            'school_errors': school_errors
        })

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@management_bp.route('/management/import-districts', methods=['POST'])
@login_required
def import_districts():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Define Salesforce query
        salesforce_query = """
        SELECT Id, Name, School_Code_External_ID__c
        FROM Account 
        WHERE Type = 'School District'
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
                # Check if district exists
                existing_district = District.query.filter_by(salesforce_id=row['Id']).first()
                
                if existing_district:
                    # Update existing district
                    existing_district.name = row['Name']
                    existing_district.district_code = row['School_Code_External_ID__c']
                else:
                    # Create new district
                    new_district = District(
                        salesforce_id=row['Id'],
                        name=row['Name'],
                        district_code=row['School_Code_External_ID__c']
                    )
                    db.session.add(new_district)
                
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Error processing district {row.get('Name')}: {str(e)}")

        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} districts with {error_count} errors',
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

@management_bp.route('/schools')
@login_required
def schools():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    districts = District.query.order_by(District.name).all()
    schools = School.query.order_by(School.name).all()
    return render_template('management/schools.html', districts=districts, schools=schools)

@management_bp.route('/management/schools/<school_id>', methods=['DELETE'])
@login_required
def delete_school(school_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        school = School.query.get_or_404(school_id)
        db.session.delete(school)
        db.session.commit()
        return jsonify({'success': True, 'message': 'School deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@management_bp.route('/management/districts/<district_id>', methods=['DELETE'])
@login_required
def delete_district(district_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        district = District.query.get_or_404(district_id)
        db.session.delete(district)  # This will cascade delete associated schools
        db.session.commit()
        return jsonify({'success': True, 'message': 'District and associated schools deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@management_bp.route('/bug-reports')
@login_required
def bug_reports():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all bug reports, newest first
    reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    return render_template('management/bug_reports.html', reports=reports, BugReportType=BugReportType)

@management_bp.route('/bug-reports/<int:report_id>/resolve', methods=['POST'])
@login_required
def resolve_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        report = BugReport.query.get_or_404(report_id)
        report.resolved = True
        report.resolved_by_id = current_user.id
        report.resolved_at = datetime.now(timezone.utc)
        report.resolution_notes = request.form.get('notes', '')
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@management_bp.route('/bug-reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_bug_report(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        report = BugReport.query.get_or_404(report_id)
        db.session.delete(report)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@management_bp.route('/bug-reports/<int:report_id>/resolve-form')
@login_required
def get_resolve_form(report_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('management/resolve_form.html', report_id=report_id)

@management_bp.route('/client-connected-projects')
@login_required
def client_connected_projects():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
    return render_template('management/client_connected_projects.html', 
                         projects=projects,
                         ProjectStatus=ProjectStatus)

@management_bp.route('/management/client-projects/form')
@login_required
def client_project_form():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('management/client_project_form.html',
                         form_title='Add New Project',
                         form_action='/management/client-projects/create',
                         project=None,
                         ProjectStatus=ProjectStatus)

@management_bp.route('/management/client-projects/create', methods=['POST'])
@login_required
def create_client_project():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Process contact information
        contact_names = request.form.getlist('contact_names[]')
        contact_hours = request.form.getlist('contact_hours[]')
        contacts = [{'name': name, 'hours': hours} 
                   for name, hours in zip(contact_names, contact_hours)]

        # Create new project
        project = ClientProject(
            status=request.form['status'],
            teacher=request.form['teacher'],
            district=request.form['district'],
            organization=request.form['organization'],
            project_title=request.form['project_title'],
            project_description=request.form['project_description'],
            project_dates=request.form['project_dates'],
            number_of_students=int(request.form['number_of_students']),
            primary_contacts=contacts
        )
        
        db.session.add(project)
        db.session.commit()
        
        return redirect(url_for('management.client_connected_projects'))
    
    except Exception as e:
        db.session.rollback()
        return f'Error: {str(e)}', 500

@management_bp.route('/management/client-projects/<int:project_id>/edit')
@login_required
def edit_client_project_form(project_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    project = ClientProject.query.get_or_404(project_id)
    return render_template('management/client_project_form.html',
                         form_title='Edit Project',
                         form_action=f'/management/client-projects/{project_id}/update',
                         project=project,
                         ProjectStatus=ProjectStatus)

@management_bp.route('/management/client-projects/<int:project_id>/update', methods=['POST'])
@login_required
def update_client_project(project_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        project = ClientProject.query.get_or_404(project_id)
        
        # Process contact information
        contact_names = request.form.getlist('contact_names[]')
        contact_hours = request.form.getlist('contact_hours[]')
        contacts = [{'name': name, 'hours': hours} 
                   for name, hours in zip(contact_names, contact_hours)]

        # Update project
        project.status = request.form['status']
        project.teacher = request.form['teacher']
        project.district = request.form['district']
        project.organization = request.form['organization']
        project.project_title = request.form['project_title']
        project.project_description = request.form['project_description']
        project.project_dates = request.form['project_dates']
        project.number_of_students = int(request.form['number_of_students'])
        project.primary_contacts = contacts
        
        db.session.commit()
        
        return redirect(url_for('management.client_connected_projects'))
    
    except Exception as e:
        db.session.rollback()
        return f'Error: {str(e)}', 500

@management_bp.route('/management/client-projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_client_project(project_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        project = ClientProject.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@management_bp.route('/management/client-projects/cancel')
@login_required
def cancel_client_project_form():
    return ''  # Returns empty content to clear the form