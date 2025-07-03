from models import db
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class EventAttendanceDetail(db.Model):
    __tablename__ = 'event_attendance_detail'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, unique=True, index=True)
    num_classrooms = db.Column(db.Integer, nullable=True)
    students_per_volunteer = db.Column(db.Integer, nullable=True)
    total_students = db.Column(db.Integer, nullable=True)
    attendance_in_sf = db.Column(db.Boolean, default=False)
    pathway = db.Column(db.String(128), nullable=True)
    groups_rotations = db.Column(db.String(128), nullable=True)
    is_stem = db.Column(db.Boolean, default=False)
    attendance_link = db.Column(db.String(512), nullable=True)

    # Relationship to Event
    event = relationship('Event', back_populates='attendance_detail')

    def __repr__(self):
        return f'<EventAttendanceDetail event_id={self.event_id} total_students={self.total_students}>'

    def __str__(self):
        return f'AttendanceDetail for Event {self.event_id}' 