from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import current_user, login_required
from models import db
from models.bug_report import BugReport, BugReportType

bug_reports_bp = Blueprint('bug_reports', __name__)

@bug_reports_bp.route('/bug-report/form')
@login_required
def get_form():
    """Return the bug report form HTML"""
    return render_template('bug_reports/form.html')

@bug_reports_bp.route('/bug-report/submit', methods=['POST'])
@login_required
def submit_report():
    """Handle bug report submission"""
    try:
        # Get form data with defaults
        report_type = request.form.get('type', BugReportType.BUG)
        description = request.form.get('description')
        page_url = request.form.get('page_url', '')
        page_title = request.form.get('page_title', '')

        if not description:
            return jsonify({
                'success': False,
                'message': 'Description is required'
            }), 400

        # Create new bug report
        report = BugReport(
            type=int(report_type),
            description=description,
            page_url=page_url,
            page_title=page_title,
            submitted_by_id=current_user.id
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your report. We will look into this.'
        })

    except Exception as e:
        db.session.rollback()
        # Log the error for debugging (you should have proper logging set up)
        print(f"Error submitting bug report: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting your report. Please try again.'
        }), 500

@bug_reports_bp.route('/bug-reports')
@login_required
def list_reports():
    """Admin view to list all bug reports"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
        
    reports = BugReport.query.order_by(BugReport.created_at.desc()).all()
    return render_template('bug_reports/list.html', reports=reports) 