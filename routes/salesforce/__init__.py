"""
Salesforce Import Routes Package
================================

This package consolidates all Salesforce import routes into a single location.
Each module handles import operations for a specific domain.

Modules:
- routes: Salesforce admin dashboard (sync status, controls)
- volunteer_import: Volunteer data import
- teacher_import: Teacher data import
- student_import: Student data import
- organization_import: Organization and affiliation import
- history_import: Activity history import
- event_import: Event and participation import

All blueprints are exported for registration in the main routes configuration.
"""

from routes.salesforce.event_import import event_import_bp
from routes.salesforce.history_import import history_import_bp
from routes.salesforce.organization_import import organization_import_bp
from routes.salesforce.routes import salesforce_bp
from routes.salesforce.school_import import school_import_bp
from routes.salesforce.student_import import sf_student_import_bp
from routes.salesforce.teacher_import import sf_teacher_import_bp
from routes.salesforce.volunteer_import import salesforce_import_bp

__all__ = [
    "salesforce_bp",
    "salesforce_import_bp",
    "event_import_bp",
    "history_import_bp",
    "organization_import_bp",
    "school_import_bp",
    "sf_student_import_bp",
    "sf_teacher_import_bp",
]
