from datetime import datetime, timezone
from . import db
from enum import IntEnum

class BugReportType(IntEnum):
    BUG = 0        # Something not working correctly
    DATA_ERROR = 1 # Incorrect information displayed
    OTHER = 2      # Other issues

class BugReport(db.Model):
    __tablename__ = 'bug_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, default=BugReportType.BUG)
    description = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(500), nullable=False)  # Store which page it was reported from
    page_title = db.Column(db.String(200))  # Store the page title for better context
    
    # User who submitted the report
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submitted_by = db.relationship(
        'User',
        foreign_keys=[submitted_by_id],
        backref=db.backref('bug_reports', lazy=True)
    )
    
    # Admin fields
    resolved = db.Column(db.Boolean, default=False)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_by = db.relationship(
        'User',
        foreign_keys=[resolved_by_id],
        backref=db.backref('resolved_bug_reports', lazy=True)
    )
    resolution_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime)
