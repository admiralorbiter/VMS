from datetime import datetime
from . import db
from enum import Enum

class ContactMethod(str, Enum):
    EMAIL = 'email'
    PHONE = 'phone'
    BOTH = 'both'

class EmergencyContactAssignment(db.Model):
    __tablename__ = 'emergency_contact_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id'), nullable=False)
    contact_method = db.Column(db.Enum(ContactMethod), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = db.relationship('Event', backref=db.backref('emergency_contacts', lazy='dynamic'))
    assigned_user = db.relationship('User', backref=db.backref('emergency_contact_assignments', lazy='dynamic'))
    volunteer = db.relationship('Volunteer', backref=db.backref('emergency_assignment', uselist=False))