from flask import Blueprint, render_template
from flask_login import login_required

attendance = Blueprint('attendance', __name__)

@attendance.route('/attendance')
@login_required
def view_attendance():
    return render_template('attendance/attendance.html')

@attendance.route('/attendance/import')
@login_required
def import_attendance():
    return render_template('attendance/import.html')

@attendance.route('/attendance/purge', methods=['POST'])
@login_required
def purge_attendance():
    # TODO: Implement purge logic
    return {'status': 'success', 'message': 'Attendance records purged successfully'}