"""
Attendance Models Module
========================

This module defines the EventAttendanceDetail model for tracking detailed
attendance information for events in the VMS system.

Key Features:
- Detailed attendance tracking for events
- Student-to-volunteer ratio tracking
- Classroom and group management
- STEM event categorization
- Salesforce integration tracking
- External attendance system linking
- Pathway and rotation tracking

Database Table:
- event_attendance_detail: Stores detailed attendance information

Attendance Tracking:
- Total student count tracking
- Classroom/table count management
- Student-to-volunteer ratio calculation
- Group rotation information
- Pathway categorization

Event Categorization:
- STEM event identification
- Career pathway tracking
- Group rotation management
- External system integration

Salesforce Integration:
- Attendance synchronization tracking
- Data consistency validation
- Reporting integration

Usage Examples:
    # Create attendance detail for an event
    attendance = EventAttendanceDetail(
        event_id=event.id,
        total_students=25,
        num_classrooms=3,
        rotations=2,
        is_stem=True,
        pathway="STEM"
    )
    
    # Calculate students per volunteer
    students_per_volunteer = attendance.calculate_students_per_volunteer()
    
    # Check if attendance is synced to Salesforce
    if attendance.attendance_in_sf:
        print("Attendance data is in Salesforce")
    
    # Get attendance ratio
    ratio = attendance.students_per_volunteer
"""

from models import db
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import math

class EventAttendanceDetail(db.Model):
    """
    Model for storing detailed attendance information for events.
    
    This model extends the basic Event model with additional attendance-specific
    fields that are used for tracking and reporting purposes. It has a one-to-one
    relationship with the Event model.
    
    Database Table:
        event_attendance_detail - Stores detailed attendance tracking data
        
    Key Features:
        - Detailed attendance tracking for events
        - Student-to-volunteer ratio tracking
        - Classroom and group management
        - STEM event categorization
        - Salesforce integration tracking
        - External attendance system linking
        - Pathway and rotation tracking
        
    Relationships:
        - One-to-one with Event model
        - Bidirectional relationship with back_populates
        
    Attendance Metrics:
        - total_students: Total number of students who attended
        - num_classrooms: Number of classrooms or tables used
        - rotations: Number of rotations for the event
        - students_per_volunteer: Calculated students per volunteer ratio
        
    Event Categorization:
        - is_stem: Whether this is a STEM-focused event
        - pathway: Career pathway focus (e.g., STEM, Arts, etc.)
        - groups_rotations: Group rotation information
        
    Integration Features:
        - attendance_in_sf: Salesforce synchronization tracking
        - attendance_link: External attendance system URL
        
    Data Validation:
        - event_id is required and unique
        - Numeric fields support null values for incomplete data
        - Boolean flags for categorization
        - String fields for flexible categorization
    """
    __tablename__ = 'event_attendance_detail'

    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign key to Event table - one-to-one relationship
    # Each event can have only one attendance detail record
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, unique=True, index=True)
    
    # Attendance tracking fields
    num_classrooms = db.Column(db.Integer, nullable=True)  # Number of classrooms or tables used
    rotations = db.Column(db.Integer, nullable=True)  # Number of rotations for the event
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

    def calculate_students_per_volunteer(self):
        """
        Calculate students per volunteer based on the formula:
        (Total Students / Classrooms) × Rotations
        
        Returns:
            int: Calculated students per volunteer, rounded down
                 Returns None if insufficient data for calculation
        """
        if not self.total_students or not self.num_classrooms or not self.rotations:
            return None
        
        if self.num_classrooms <= 0 or self.rotations <= 0:
            return None
        
        # Calculate: (Total Students / Classrooms) × Rotations
        result = (self.total_students / self.num_classrooms) * self.rotations
        
        # Round down to nearest integer
        return math.floor(result)

    def update_students_per_volunteer(self):
        """
        Update the students_per_volunteer field with the calculated value.
        """
        calculated_value = self.calculate_students_per_volunteer()
        self.students_per_volunteer = calculated_value
        return calculated_value

    def __repr__(self):
        """
        String representation for debugging and logging.
        
        Returns:
            str: Debug representation showing event_id and total_students
        """
        return f'<EventAttendanceDetail event_id={self.event_id} total_students={self.total_students}>'

    def __str__(self):
        """
        Human-readable string representation.
        
        Returns:
            str: User-friendly description of the attendance detail
        """
        return f'AttendanceDetail for Event {self.event_id}' 