from flask import Blueprint, render_template
from flask_login import login_required

# Create blueprint
attendance_bp = Blueprint('reports_attendance', __name__)

def load_routes(bp):
    @bp.route('/reports/attendance')
    @login_required
    def attendance_report():
        # TODO: Add data fetching logic here
        # This will be implemented in the next phase
        return render_template('reports/attendance_report.html')
