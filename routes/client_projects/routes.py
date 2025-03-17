from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db
from models.client_project_model import ClientProject, ProjectStatus

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
                         ProjectStatus=ProjectStatus)

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