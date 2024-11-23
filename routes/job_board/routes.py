import csv
from datetime import datetime
from io import StringIO
import os
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from models import db
from models.tech_job_board import EntryLevelJob, JobOpportunity, WorkLocationType

job_board_bp = Blueprint('job_board', __name__)

@job_board_bp.route('/tech_jobs')
@login_required
def tech_jobs():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    # Create current_filters dictionary
    current_filters = {
        'search_company': request.args.get('search_company', '').strip(),
        'industry': request.args.get('industry', ''),
        'location': request.args.get('location', ''),
        'entry_level': request.args.get('entry_level', ''),  # Add entry level filter
        'per_page': per_page
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Build query
    query = JobOpportunity.query.filter_by(is_active=True)

    # Apply filters
    if current_filters.get('search_company'):
        search_term = f"%{current_filters['search_company']}%"
        query = query.filter(JobOpportunity.company_name.ilike(search_term))

    if current_filters.get('industry'):
        query = query.filter(JobOpportunity.industry == current_filters['industry'])

    if current_filters.get('location'):
        if current_filters['location'] == 'kc_based':
            query = query.filter(JobOpportunity.kc_based == True)
        elif current_filters['location'] == 'remote':
            query = query.filter(JobOpportunity.remote_available == True)

    # Add entry level filter
    if current_filters.get('entry_level'):
        if current_filters['entry_level'] == 'yes':
            query = query.filter(JobOpportunity.entry_level_available == True)
        elif current_filters['entry_level'] == 'no':
            query = query.filter(JobOpportunity.entry_level_available == False)

    # Apply pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Get unique industries for dropdown
    industries = db.session.query(JobOpportunity.industry)\
        .distinct()\
        .order_by(JobOpportunity.industry)\
        .all()
    industries = [i[0] for i in industries if i[0]]  # Flatten and remove empty

    return render_template(
        'job_board/tech.html',
        jobs=pagination.items,
        pagination=pagination,
        current_filters=current_filters,
        industries=industries
    )

@job_board_bp.route('/tech_jobs/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        try:
            job = JobOpportunity(
                company_name=request.form.get('company_name'),
                industry=request.form.get('industry'),
                current_openings=request.form.get('current_openings', type=int),
                location=request.form.get('location'),
                kc_based=request.form.get('kc_based') == 'true',
                remote_available=request.form.get('remote_available') == 'true',
                entry_level_available=request.form.get('entry_level_available') == 'true',
                job_link=request.form.get('job_link'),
                description=request.form.get('description')
            )
            db.session.add(job)
            db.session.commit()
            flash('Job added successfully!', 'success')
            return redirect(url_for('tech_jobs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding job: {str(e)}', 'danger')
            return redirect(url_for('add_job'))

    return render_template('job_board/add_job.html')

@job_board_bp.route('/tech_jobs/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_job(id):
    job = JobOpportunity.query.get_or_404(id)
    if request.method == 'POST':
        try:
            job.company_name = request.form.get('company_name')
            job.industry = request.form.get('industry')
            job.current_openings = request.form.get('current_openings', type=int)
            job.location = request.form.get('location')
            job.kc_based = request.form.get('kc_based') == 'true'
            job.remote_available = request.form.get('remote_available') == 'true'
            job.entry_level_available = request.form.get('entry_level_available') == 'true'
            job.job_link = request.form.get('job_link')
            job.description = request.form.get('description')
            
            db.session.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('view_job', id=job.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating job: {str(e)}', 'danger')
            return redirect(url_for('edit_job', id=id))

    return render_template('job_board/edit_job.html', job=job)

@job_board_bp.route('/tech_jobs/view/<int:id>')
def view_job(id):
    job = JobOpportunity.query.get_or_404(id)
    return render_template('job_board/view_job.html', job=job)

@job_board_bp.route('/tech_jobs/sync', methods=['POST'])
@login_required
def sync_jobs():
    """Sync jobs from external source"""
    try:
        # Add your sync logic here
        return jsonify({'success': True, 'message': 'Jobs synced successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@job_board_bp.route('/tech_jobs/purge', methods=['POST'])
@login_required
def purge_jobs():
    """Purge old/inactive jobs"""
    try:
        # Add your purge logic here
        return jsonify({'success': True, 'message': 'Old jobs purged successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@job_board_bp.route('/tech_jobs/import', methods=['GET', 'POST'])
@login_required
def import_tech_jobs():
    if request.method == 'GET':
        return render_template('job_board/import.html')
    
    try:
        success_count = 0
        error_count = 0
        errors = []
        
        # Set default file path
        default_file_path = os.path.join('data', 'KC Tech Jobs.csv')
        
        if request.is_json and request.json.get('quickSync'):
            # Handle quickSync
            if not os.path.exists(default_file_path):
                return jsonify({'error': 'Default CSV file not found'}), 404
                
            with open(default_file_path, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read().replace('\0', '')
                csv_data = csv.DictReader(content.splitlines())
                for row in csv_data:
                    try:
                        job = JobOpportunity.query.filter_by(
                            company_name=row.get('Name'),
                            description=row.get('Description')
                        ).first()
                        
                        if not job:
                            job = JobOpportunity()
                            db.session.add(job)
                        
                        # Update job fields
                        job.company_name = row.get('Name', '')
                        job.description = row.get('Description', '')
                        job.industry = row.get('Industry', '')
                        job.current_openings = int(row.get('Current Local Openings', 0))
                        job.opening_types = row.get('Type of Openings', '')
                        job.location = row.get('Location', '')
                        job.entry_level_available = row.get('Entry Avaible?', '').lower() == 'yes'
                        job.kc_based = row.get('KC Based', '').lower() == 'yes'
                        job.notes = row.get('Notes', '')
                        job.job_link = row.get('Link to Jobs', '')
                        job.is_active = True
                        
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error processing row: {str(e)}")
                        continue

        else:
            # Handle file upload
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'File must be a CSV'}), 400

            content = file.stream.read().decode("UTF8", errors='replace').replace('\0', '')
            csv_data = csv.DictReader(content.splitlines())
            
            # Process the uploaded file using the same logic as above
            for row in csv_data:
                try:
                    # Same processing logic as above
                    job = JobOpportunity.query.filter_by(
                        company_name=row.get('Name'),
                        description=row.get('Description')
                    ).first()
                    
                    if not job:
                        job = JobOpportunity()
                        db.session.add(job)
                    
                    # Update job fields
                    job.company_name = row.get('Name', '')
                    job.description = row.get('Description', '')
                    job.industry = row.get('Industry', '')
                    job.current_openings = int(row.get('Current Local Openings', 0))
                    job.opening_types = row.get('Type of Openings', '')
                    job.location = row.get('Location', '')
                    job.entry_level_available = row.get('Entry Avaible?', '').lower() == 'yes'
                    job.kc_based = row.get('KC Based', '').lower() == 'yes'
                    job.notes = row.get('Notes', '')
                    job.job_link = row.get('Link to Jobs', '')
                    job.is_active = True
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing row: {str(e)}")
                    continue

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
            return jsonify({'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@job_board_bp.route('/tech_jobs/import/quick', methods=['POST'])
@login_required
def quick_import_tech_jobs():
    import_type = request.args.get('type', 'tech_jobs')
    try:
        success_count = 0
        error_count = 0
        errors = []

        if import_type == 'tech_jobs':
            csv_path = 'data/KC Tech Jobs.csv'
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_data = csv.DictReader(file)
                # First, deactivate all existing jobs
                JobOpportunity.query.update({JobOpportunity.is_active: False})
                
                for row in csv_data:
                    try:
                        # Skip empty rows
                        if not row['Name']:
                            continue
                        
                        # Map CSV data to model fields
                        job = JobOpportunity.query.filter_by(company_name=row['Name']).first()
                        if not job:
                            job = JobOpportunity()
                        
                        job.company_name = row['Name']
                        job.description = row['Description']
                        job.industry = row['Industry']
                        job.current_openings = int(row['Current Local Openings']) if row['Current Local Openings'] else 0
                        job.opening_types = row['Type of Openings']
                        job.location = row['Location']
                        
                        # Convert Yes/No/One to boolean
                        job.entry_level_available = row['Entry Avaible?'].lower() in ['yes', 'one']
                        job.kc_based = row['KC Based'].lower() == 'yes'
                        
                        # Check for remote in location
                        job.remote_available = 'remote' in row['Location'].lower() if row['Location'] else False
                        
                        job.notes = row['Notes']
                        job.job_link = row['Link to Jobs']
                        job.is_active = True
                        
                        db.session.add(job)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error processing {row.get('Name', 'Unknown')}: {str(e)}")
                        continue
                
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
                    return jsonify({'error': f'Database error: {str(e)}'}), 500
                    
        elif import_type == 'entry_level':
            csv_path = 'data/entry_level_jobs.csv'
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_data = csv.DictReader(file)
                
                for row in csv_data:
                    try:
                        # Find parent job opportunity
                        job = JobOpportunity.query.filter_by(
                            company_name=row['Company Name'],
                            is_active=True
                        ).first()
                        
                        if not job:
                            error_count += 1
                            errors.append(f"Parent job not found for {row['Company Name']}")
                            continue
                        
                        # Check for existing entry level job
                        entry_job = EntryLevelJob.query.filter_by(
                            job_opportunity_id=job.id,
                            title=row['Position Title']
                        ).first()
                        
                        if not entry_job:
                            entry_job = EntryLevelJob()
                        
                        # Update entry job fields
                        entry_job.job_opportunity_id = job.id
                        entry_job.title = row['Position Title']
                        entry_job.description = row['Description']
                        entry_job.address = row['Address']
                        entry_job.job_link = row['Job Link']
                        entry_job.skills_needed = row['Skills Needed']
                        entry_job.work_location = WorkLocationType(row['Work Location'].lower())
                        entry_job.is_active = True
                        
                        db.session.add(entry_job)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error processing {row.get('Position Title', 'Unknown')}: {str(e)}")
                        continue
                
        db.session.commit()
        
        return jsonify({
            'success': True,
            'successCount': success_count,
            'errorCount': error_count,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@job_board_bp.route('/tech_jobs/entry_level/add/<int:job_id>', methods=['GET', 'POST'])
@login_required
def add_entry_level_job(job_id):
    job = JobOpportunity.query.get_or_404(job_id)
    
    if request.method == 'POST':
        try:
            entry_job = EntryLevelJob(
                job_opportunity_id=job_id,
                title=request.form.get('title'),
                description=request.form.get('description'),
                address=request.form.get('address'),
                job_link=request.form.get('job_link'),
                skills_needed=request.form.get('skills_needed'),
                work_location=WorkLocationType(request.form.get('work_location')),
                is_active=True
            )
            
            db.session.add(entry_job)
            db.session.commit()
            
            flash('Entry level position added successfully!', 'success')
            return redirect(url_for('view_job', id=job_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding entry level position: {str(e)}', 'danger')
    
    return render_template('job_board/entry_level_form.html', 
                            job=job, 
                            entry_job=None,
                            work_locations=WorkLocationType)

@job_board_bp.route('/tech_jobs/entry_level/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_entry_level_job(id):
    entry_job = EntryLevelJob.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            entry_job.title = request.form.get('title')
            entry_job.description = request.form.get('description')
            entry_job.address = request.form.get('address')
            entry_job.job_link = request.form.get('job_link')
            entry_job.skills_needed = request.form.get('skills_needed')
            entry_job.work_location = WorkLocationType(request.form.get('work_location'))
            
            db.session.commit()
            flash('Entry level position updated successfully!', 'success')
            return redirect(url_for('view_job', id=entry_job.job_opportunity_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating entry level position: {str(e)}', 'danger')
    
    return render_template('job_board/entry_level_form.html', 
                            job=entry_job.job_opportunity,
                            entry_job=entry_job,
                            work_locations=WorkLocationType)

@job_board_bp.route('/tech_jobs/export')
@login_required
def export_tech_jobs():
    try:
        # Create in-memory string buffers for our CSV files
        tech_jobs_buffer = StringIO()
        entry_jobs_buffer = StringIO()
        
        # Create CSV writers
        tech_jobs_writer = csv.writer(tech_jobs_buffer)
        entry_jobs_writer = csv.writer(entry_jobs_buffer)
        
        # Write headers for tech jobs CSV (matching import format)
        tech_jobs_writer.writerow([
            'Name', 'Industry Type', 'Industry', 'Current Local Openings',
            'Type of Openings', 'Location', 'Entry Avaible?', 'KC Based',
            'Notes', 'Link to Jobs'
        ])
        
        # Write headers for entry level positions CSV
        entry_jobs_writer.writerow([
            'Company Name', 'Position Title', 'Description', 'Address',
            'Work Location', 'Skills Needed', 'Job Link', 'Is Active'
        ])
        
        # Get all active job opportunities
        jobs = JobOpportunity.query.filter_by(is_active=True).all()
        
        # Write job opportunities data
        for job in jobs:
            tech_jobs_writer.writerow([
                job.company_name,
                '',  # Industry Type (not in current model)
                job.industry,
                job.current_openings,
                job.opening_types,
                job.location,
                'Yes' if job.entry_level_available else 'No',
                'Yes' if job.kc_based else 'No',
                job.notes,
                job.job_link
            ])
            
            # Write entry level positions data
            for position in job.entry_level_positions:
                if position.is_active:
                    entry_jobs_writer.writerow([
                        job.company_name,
                        position.title,
                        position.description,
                        position.address,
                        position.work_location.value,
                        position.skills_needed,
                        position.job_link,
                        'Yes' if position.is_active else 'No'
                    ])
        
        # Create a zip file containing both CSVs
        import zipfile
        from io import BytesIO
        
        # Create zip buffer
        zip_buffer = BytesIO()
        
        # Create zip file
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add tech jobs CSV
            tech_jobs_buffer.seek(0)
            zip_file.writestr('tech_jobs.csv', tech_jobs_buffer.getvalue())
            
            # Add entry level jobs CSV
            entry_jobs_buffer.seek(0)
            zip_file.writestr('entry_level_jobs.csv', entry_jobs_buffer.getvalue())
        
        # Prepare zip file for download
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'tech_jobs_export_{timestamp}.zip'
        )
        
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'danger')
        return redirect(url_for('tech_jobs'))
