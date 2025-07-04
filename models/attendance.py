from models import db
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class EventAttendanceDetail(db.Model):
    """
    Model for storing detailed attendance information for events.
    
    This model extends the basic Event model with additional attendance-specific
    fields that are used for tracking and reporting purposes. It has a one-to-one
    relationship with the Event model.
    """
    __tablename__ = 'event_attendance_detail'

    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key to Event table - one-to-one relationship
    # Each event can have only one attendance detail record
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, unique=True, index=True)
    
    # Attendance tracking fields
    num_classrooms = db.Column(db.Integer, nullable=True)  # Number of classrooms or tables used
    students_per_volunteer = db.Column(db.Integer, nullable=True)  # Average students per volunteer ratio
    total_students = db.Column(db.Integer, nullable=True)  # Total number of students who attended
    
    # Salesforce integration flag
    attendance_in_sf = db.Column(db.Boolean, default=False)  # Whether attendance was recorded in Salesforce
    
    # Event categorization fields
    pathway = db.Column(db.String(128), nullable=True)  # Career pathway focus (e.g., STEM, Arts, etc.)
    groups_rotations = db.Column(db.String(128), nullable=True)  # Group rotation information
    
    # STEM-specific flag
    is_stem = db.Column(db.Boolean, default=False)  # Whether this is a STEM-focused event
    
    # External link to attendance tracking system
    attendance_link = db.Column(db.String(512), nullable=True)  # URL to external attendance system

    # Relationship to Event model - back_populates creates bidirectional relationship
    event = relationship('Event', back_populates='attendance_detail')

    def __repr__(self):
        """String representation for debugging and logging."""
        return f'<EventAttendanceDetail event_id={self.event_id} total_students={self.total_students}>'

    def __str__(self):
        """Human-readable string representation."""
        return f'AttendanceDetail for Event {self.event_id}' 