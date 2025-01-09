from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime
from flask import current_app
from models.event import db, Event, EventType
import os

virtual_bp = Blueprint('virtual', __name__)

@virtual_bp.route('/virtual')
def virtual():
    return render_template('virtual/virtual.html')

def process_csv_row(row, success_count, warning_count, error_count, errors):
    try:
        db.session.rollback()
        
        # Skip rows without dates
        if not row.get('Date'):
            warning_count += 1
            errors.append(f"Row {success_count + warning_count + error_count}: Skipped - No date provided")
            return success_count, warning_count, error_count

        # Check if event already exists by session ID
        existing_event = Event.query.filter_by(
            session_id=row.get('Session ID')
        ).first()

        if existing_event:
            
            # Merge and update existing event
            existing_event.merge_duplicate(row)
            db.session.commit()

            warning_count += 1
        else:
            # Create new event
            new_event = Event()
            new_event.update_from_csv(row)
            
            db.session.add(new_event)
            db.session.commit()
            success_count += 1

    except Exception as e:
        error_count += 1
        errors.append(f"Row {success_count + warning_count + error_count}: {str(e)}")
        current_app.logger.error(f"Error processing row: {str(e)}", exc_info=True)
        db.session.rollback()

    return success_count, warning_count, error_count

@virtual_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_virtual():
    if request.method == 'GET':
        return render_template('virtual/import.html')
    
    try:
        success_count = warning_count = error_count = 0
        errors = []

        if 'file' in request.files:
            file = request.files['file']
            if not file.filename.endswith('.csv'):
                raise ValueError("Please upload a CSV file")
            
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_data = csv.DictReader(stream)
            
            for row in csv_data:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors
                )

        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Import failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/quick-sync', methods=['POST'])
@login_required
def quick_sync():
    try:
        csv_path = os.path.join('data', 'virtual.csv')
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Virtual data file not found at {csv_path}")

        success_count = warning_count = error_count = 0
        errors = []

        with open(csv_path, 'r', encoding='UTF8') as file:
            csv_data = csv.DictReader(file)
            
            for row in csv_data:
                success_count, warning_count, error_count = process_csv_row(
                    row, success_count, warning_count, error_count, errors
                )

        return jsonify({
            'success': True,
            'successCount': success_count,
            'warningCount': warning_count,
            'errorCount': error_count,
            'errors': errors
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Quick sync failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@virtual_bp.route('/purge', methods=['GET', 'POST'])
@login_required
def purge_virtual():
    try:
        # Only delete events that are virtual sessions
        deleted_count = Event.query.filter_by(
            type=EventType.VIRTUAL_SESSION
        ).delete()
        
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully purged {deleted_count} virtual sessions',
            'count': deleted_count
        })
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        current_app.logger.error("Purge failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400