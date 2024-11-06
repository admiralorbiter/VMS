from datetime import datetime
from models import db

# Define the association table first
event_volunteers = db.Table('event_volunteers',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteer.id'), primary_key=True)
)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)  # workshop, meeting, social, volunteer
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255))
    status = db.Column(db.String(50))  # upcoming, in_progress, completed, cancelled
    volunteer_needed = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    volunteers = db.relationship('Volunteer', 
                               secondary=event_volunteers,
                               backref=db.backref('events', lazy='dynamic'))

    @property
    def volunteer_count(self):
        return len(self.volunteers)