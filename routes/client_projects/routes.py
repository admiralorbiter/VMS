import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db
from models.client_project_model import ClientProject, ProjectStatus
import pandas as pd
import re
from os import getenv
from flask import current_app

client_projects_bp = Blueprint('client_projects', __name__, url_prefix='/management/client-projects')

@client_projects_bp.route('/')
@login_required
def index():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
    return render_template('client_connected_projects/client_connected_projects.html', 
                         projects=projects,
                         ProjectStatus=ProjectStatus,
                         config={'CLIENT_PROJECTS_SHEET_ID': getenv('CLIENT_PROJECTS_SHEET_ID')})

@client_projects_bp.route('/form')
@login_required
def form():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return render_template('client_connected_projects/client_project_form.html',
                         form_title='Add New Project',
                         form_action='/management/client-projects/create',
                         project=None,
                         ProjectStatus=ProjectStatus)

@client_projects_bp.route('/create', methods=['POST'])
@login_required
def create():
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
        
        # Return just the table partial
        projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
        return render_template('client_connected_projects/partials/project_table.html', 
                             projects=projects,
                             ProjectStatus=ProjectStatus)
    
    except Exception as e:
        db.session.rollback()
        return f'Error: {str(e)}', 500

@client_projects_bp.route('/<int:project_id>/edit')
@login_required
def edit_form(project_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    project = ClientProject.query.get_or_404(project_id)
    return render_template('client_connected_projects/client_project_form.html',
                         form_title='Edit Project',
                         form_action=f'/management/client-projects/{project_id}/update',
                         project=project,
                         ProjectStatus=ProjectStatus)

@client_projects_bp.route('/<int:project_id>/update', methods=['POST'])
@login_required
def update(project_id):
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
        
        # Return just the table partial
        projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
        return render_template('client_connected_projects/partials/project_table.html', 
                             projects=projects,
                             ProjectStatus=ProjectStatus)
    
    except Exception as e:
        db.session.rollback()
        return f'Error: {str(e)}', 500

@client_projects_bp.route('/<int:project_id>', methods=['DELETE'])
@login_required
def delete(project_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        project = ClientProject.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
        # Instead of returning empty response, return a trigger to remove the row
        return "", 200, {"HX-Trigger": "projectDeleted"}
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@client_projects_bp.route('/cancel')
@login_required
def cancel_form():
    return ''  # Returns empty content to clear the form

@client_projects_bp.route('/import-sheet', methods=['POST'])
@login_required
def import_sheet():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        sheet_id = os.getenv('CLIENT_PROJECTS_SHEET_ID')
        if not sheet_id:
            raise ValueError("Google Sheet ID not configured")
        
        # Modified URL format with gviz/tq
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
        
        current_app.logger.info(f"Attempting to fetch sheet with ID: {sheet_id}")
        current_app.logger.info(f"URL: {csv_url}")
        
        try:
            df = pd.read_csv(csv_url)
        except Exception as e:
            current_app.logger.error(f"Failed to read CSV: {str(e)}")
            # Try alternative URL format
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
            df = pd.read_csv(csv_url)
        
        success_count = warning_count = error_count = 0
        errors = []
        
        for _, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row['Status']) or pd.isna(row['Teacher']):
                    continue

                # Process contact information
                contacts_str = str(row.get('Primary Org Contacts (with volunteer hours)', ''))
                contacts = []
                
                # Split contacts by newline and process each one
                for contact in contacts_str.split('\n'):
                    contact = contact.strip()
                    if contact:
                        # Extract name and hours using regex
                        match = re.match(r'(.*?)\s*\((\d+)\s*hours?\)', contact)
                        if match:
                            name, hours = match.groups()
                            contacts.append({
                                'name': name.strip(),
                                'hours': hours.strip()
                            })
                        else:
                            # Handle cases without hours specified
                            contacts.append({
                                'name': contact.split('(')[0].strip(),
                                'hours': '0'
                            })

                # Create new project
                project = ClientProject(
                    status=row['Status'].strip(),
                    teacher=row['Teacher'].strip(),
                    district=row['District'].strip(),
                    organization=row['Organization'].strip(),
                    primary_contacts=contacts,
                    project_description=row.get('Project Description', '').strip(),
                    project_title=extract_title(row.get('Project Description', '')),
                    project_dates=row.get('Project Dates', '').strip(),
                    number_of_students=parse_student_number(row.get('Number of Students', 0))
                )
                
                db.session.add(project)
                db.session.commit()
                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing row: {str(e)}")
                db.session.rollback()
                current_app.logger.error(f"Import error: {e}", exc_info=True)
        
        # After successful import, get updated projects
        projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
        
        # Return both the success data and the updated table HTML
        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors,
            'html': render_template('client_connected_projects/partials/project_table.html', 
                                 projects=projects,
                                 ProjectStatus=ProjectStatus)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Sheet import failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def extract_title(description):
    """Extract title from project description if it exists"""
    if not description:
        return None
    
    # Look for "Title:" in the description
    title_match = re.search(r'Title:\s*(.+?)(?:\n|$)', description)
    if title_match:
        return title_match.group(1).strip()
    
    # If no explicit title, use first line or first X characters
    first_line = description.split('\n')[0].strip()
    return first_line[:200]  # Limit to 200 characters as per model

def parse_student_number(value):
    """Parse student number from various formats"""
    if pd.isna(value):
        return 0
    
    value = str(value).lower().strip()
    
    # Handle "About X" format
    if value.startswith('about '):
        value = value.replace('about ', '')
    
    # Extract first number found
    match = re.search(r'\d+', value)
    if match:
        return int(match.group())
    
    return 0