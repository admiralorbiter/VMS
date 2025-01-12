import csv
import os
from flask import Blueprint, request, flash, render_template, jsonify
from flask_login import login_required
from models.event import Event
from models.history import History
from models import db
from sqlalchemy import or_
from datetime import datetime, timedelta
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from config import Config

from models.volunteer import Volunteer
from routes.utils import parse_date

history_bp = Blueprint('history', __name__)

@history_bp.route('/history_table')
@login_required
def history_table():
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    # Create current_filters dictionary
    current_filters = {
        'search_summary': request.args.get('search_summary', '').strip(),
        'activity_type': request.args.get('activity_type', ''),
        'activity_status': request.args.get('activity_status', ''),
        'start_date': request.args.get('start_date', ''),
        'end_date': request.args.get('end_date', ''),
        'per_page': per_page
    }

    # Remove empty filters
    current_filters = {k: v for k, v in current_filters.items() if v}

    # Build query
    query = History.query.filter_by(is_deleted=False)

    # Apply filters
    if current_filters.get('search_summary'):
        search_term = f"%{current_filters['search_summary']}%"
        query = query.filter(or_(
            History.summary.ilike(search_term),
            History.description.ilike(search_term)
        ))

    if current_filters.get('activity_type'):
        query = query.filter(History.activity_type == current_filters['activity_type'])

    if current_filters.get('activity_status'):
        query = query.filter(History.activity_status == current_filters['activity_status'])

    if current_filters.get('start_date'):
        try:
            start_date = datetime.strptime(current_filters['start_date'], '%Y-%m-%d')
            query = query.filter(History.activity_date >= start_date)
        except ValueError:
            flash('Invalid start date format', 'warning')

    if current_filters.get('end_date'):
        try:
            end_date = datetime.strptime(current_filters['end_date'], '%Y-%m-%d')
            # Add 23:59:59 to include the entire end date
            end_date = end_date + timedelta(days=1) - timedelta(seconds=1)
            query = query.filter(History.activity_date <= end_date)
        except ValueError:
            flash('Invalid end date format', 'warning')

    # Default sort by activity_date desc
    query = query.order_by(History.activity_date.desc())

    # Apply pagination
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Get unique activity types and statuses for filters
    activity_types = db.session.query(History.activity_type)\
        .filter(History.is_deleted == False)\
        .distinct()\
        .order_by(History.activity_type)\
        .all()
    activity_types = [t[0] for t in activity_types if t[0]]  # Remove None values

    activity_statuses = db.session.query(History.activity_status)\
        .filter(History.is_deleted == False)\
        .distinct()\
        .order_by(History.activity_status)\
        .all()
    activity_statuses = [s[0] for s in activity_statuses if s[0]]  # Remove None values

    return render_template('history/history.html',
                            history=pagination.items,
                            pagination=pagination,
                            current_filters=current_filters,
                            activity_types=activity_types,
                            activity_statuses=activity_statuses)

@history_bp.route('/history/view/<int:id>')
@login_required
def view_history(id):
    history_item = History.query.get_or_404(id)
    return render_template(
        'history/view.html',
        history=history_item
    )

@history_bp.route('/history/add', methods=['POST'])
@login_required
def add_history():
    """Add a new history entry"""
    try:
        data = request.get_json()
        
        history = History(
            event_id=data.get('event_id'),
            volunteer_id=data.get('volunteer_id'),
            action=data.get('action'),
            summary=data.get('summary'),
            description=data.get('description'),
            activity_type=data.get('activity_type'),
            activity_date=datetime.now(),
            activity_status=data.get('activity_status', 'Completed'),
            completed_at=datetime.now() if data.get('activity_status') == 'Completed' else None,
            email_message_id=data.get('email_message_id')
        )
        
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'History entry added successfully',
            'history_id': history.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error adding history entry: {str(e)}'
        }), 500

@history_bp.route('/history/delete/<int:id>', methods=['POST'])
@login_required
def delete_history(id):
    """Soft delete a history entry"""
    try:
        history = History.query.get_or_404(id)
        history.is_deleted = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'History entry deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting history entry: {str(e)}'
        }), 500

@history_bp.route('/history/import', methods=['GET', 'POST'])
@login_required
def import_history():
    if request.method == 'GET':
        return render_template('history/import.html')
    
    try:
        success_count = 0
        error_count = 0
        errors = []

        if request.is_json and request.json.get('quickSync'):
            # Handle quickSync
            default_file_path = os.path.join('data', 'Task.csv')
            if not os.path.exists(default_file_path):
                return jsonify({'error': 'Default CSV file not found'}), 404
                
            try:
                with open(default_file_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read().replace('\0', '')  # Remove null bytes
                    csv_data = csv.DictReader(content.splitlines())
                    
                    for row in csv_data:
                        try:
                            # Process history row
                            history = History.query.filter_by(salesforce_id=row.get('Id')).first()
                            if not history:
                                history = History()
                                db.session.add(history)
                            
                            # Update history fields
                            history.salesforce_id = row.get('Id')
                            history.summary = row.get('Subject', '')
                            history.description = row.get('Description', '')
                            history.activity_type = row.get('Type', '')
                            history.activity_status = row.get('Status', '')
                            history.activity_date = parse_date(row.get('ActivityDate')) or datetime.now()
                            history.email_message_id = row.get('EmailMessageId')
                            
                            # Handle volunteer relationship
                            if row.get('WhoId'):
                                volunteer = Volunteer.query.filter_by(
                                    salesforce_individual_id=row['WhoId']
                                ).first()
                                if volunteer:
                                    history.volunteer_id = volunteer.id

                            # Handle event relationship
                            if row.get('WhatId'):
                                event = Event.query.filter_by(
                                    salesforce_id=row['WhatId']
                                ).first()
                                if event:
                                    history.event_id = event.id
                            
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Error processing row: {str(e)}")
                            continue

            except Exception as e:
                return jsonify({'error': f'Error reading file: {str(e)}'}), 500

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
                    # Process history row
                    history = History.query.filter_by(salesforce_id=row.get('Id')).first()
                    if not history:
                        history = History()
                        db.session.add(history)
                    
                    # Update history fields
                    history.salesforce_id = row.get('Id')
                    history.summary = row.get('Subject', '')
                    history.description = row.get('Description', '')
                    history.activity_type = row.get('Type', '')
                    history.activity_status = row.get('Status', '')
                    history.activity_date = parse_date(row.get('ActivityDate')) or datetime.now()
                    history.email_message_id = row.get('EmailMessageId')
                    
                    # Handle volunteer relationship
                    if row.get('WhoId'):
                        volunteer = Volunteer.query.filter_by(
                            salesforce_individual_id=row['WhoId']
                        ).first()
                        if volunteer:
                            history.volunteer_id = volunteer.id

                    # Handle event relationship
                    if row.get('WhatId'):
                        event = Event.query.filter_by(
                            salesforce_id=row['WhatId']
                        ).first()
                        if event:
                            history.event_id = event.id
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing row: {str(e)}")
                    continue

        # Commit all changes
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
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@history_bp.route('/history/import-from-salesforce', methods=['POST'])
@login_required
def import_history_from_salesforce():
    try:
        print("Fetching history from Salesforce...")
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

        # Query for history
        history_query = """
        SELECT Id, Subject, Description, Type, Status, ActivityDate, WhoId, WhatId
        FROM Task
        """

        # Execute query
        result = sf.query_all(history_query)
        history_rows = result.get('records', [])

        # Process each history record
        for row in history_rows:
            try:
                # Check if history exists
                history = History.query.filter_by(salesforce_id=row['Id']).first()
                if not history:
                    history = History()
                    db.session.add(history)

                # Update history fields
                history.salesforce_id = row['Id']
                history.summary = row.get('Subject', '')
                history.description = row.get('Description', '')
                history.activity_type = row.get('Type', '')
                history.activity_status = row.get('Status', '')
                
                # Handle activity date
                if row.get('ActivityDate'):
                    history.activity_date = parse_date(row['ActivityDate'])
                else:
                    history.activity_date = datetime.now()

                # Handle volunteer relationship
                if row.get('WhoId'):
                    volunteer = Volunteer.query.filter_by(
                        salesforce_individual_id=row['WhoId']
                    ).first()
                    if volunteer:
                        history.volunteer_id = volunteer.id

                # Handle event relationship
                if row.get('WhatId'):
                    event = Event.query.filter_by(
                        salesforce_id=row['WhatId']
                    ).first()
                    if event:
                        history.event_id = event.id

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing history record {row.get('Subject', 'Unknown')}: {str(e)}")
                continue

        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {success_count} history records with {error_count} errors',
            'errors': errors
        })

    except SalesforceAuthenticationFailed:
        return jsonify({
            'success': False,
            'message': 'Failed to authenticate with Salesforce'
        }), 401
    except Exception as e:
        db.session.rollback()
        print(f"Salesforce sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500