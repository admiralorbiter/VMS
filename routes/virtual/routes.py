from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import csv
from io import StringIO
from datetime import datetime
from flask import current_app
from models.event import db, Event

virtual_bp = Blueprint('virtual', __name__)

@virtual_bp.route('/virtual')
def virtual():
    return render_template('virtual/virtual.html')

@virtual_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_virtual():
    if request.method == 'GET':
        return render_template('virtual/import.html')
    
    try:
        success_count = 0
        warning_count = 0
        error_count = 0
        errors = []

        if 'file' in request.files:
            file = request.files['file']
            if not file.filename.endswith('.csv'):
                raise ValueError("Please upload a CSV file")
            
            # Read CSV file
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_data = csv.DictReader(stream)
            
            # Process CSV data
            for row in csv_data:
                try:
                    # Rollback any pending transactions
                    db.session.rollback()
                    
                    # Check if event already exists
                    existing_event = Event.query.filter_by(
                        session_id=row.get('Session ID')
                    ).first()

                    # Convert date string to datetime object
                    date_str = row.get('Date')
                    if date_str:
                        try:
                            start_date = datetime.strptime(date_str, '%m/%d/%Y')
                        except ValueError:
                            raise ValueError(f"Invalid date format: {date_str}")
                    else:
                        raise ValueError("Date is required")

                    if existing_event:
                        # Update existing event
                        existing_event.update_from_csv(row)
                        warning_count += 1
                    else:
                        # Create new event
                        new_event = Event()
                        new_event.update_from_csv(row)
                        db.session.add(new_event)
                        success_count += 1

                    # Commit each record individually
                    db.session.commit()

                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {success_count + warning_count + error_count}: {str(e)}")
                    current_app.logger.error(f"Error processing row: {row}", exc_info=True)
                    # Rollback on error
                    db.session.rollback()
                    continue

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

@virtual_bp.route('/purge', methods=['POST'])
@login_required
def purge_virtual():
    # Add your purge logic here
    pass
