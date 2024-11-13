from models import db
from datetime import datetime

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id', ondelete="CASCADE"), index=True)
    # Remove or comment out user_id if you don't have a User model
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    action = db.Column(db.String(255))
    summary = db.Column(db.Text)  # Mapped from "Subject"
    description = db.Column(db.Text)
    activity_type = db.Column(db.String(100), index=True)
    activity_date = db.Column(db.DateTime)
    activity_status = db.Column(db.String(50), index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    last_modified_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = db.Column(db.Boolean, default=False)
    email_message_id = db.Column(db.String(255), nullable=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=True)

    # Add relationships to Event and Volunteer models
    event = db.relationship('Event', backref=db.backref('histories', lazy='dynamic'))
    volunteer = db.relationship('Volunteer', backref=db.backref('histories', lazy='dynamic'))
