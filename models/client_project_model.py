from models import db
from datetime import datetime
from enum import Enum

class ProjectStatus(Enum):
    IN_PROGRESS = "In Progress"
    PLANNING = "Planning"
    COMPLETED = "Completed"

class ClientProject(db.Model):
    __tablename__ = 'client_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    teacher = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200), nullable=False)
    
    # Store contacts as JSON array of objects with name and hours
    primary_contacts = db.Column(db.JSON)
    
    project_description = db.Column(db.Text)
    project_title = db.Column(db.String(200))
    project_dates = db.Column(db.String(100))
    number_of_students = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'teacher': self.teacher,
            'district': self.district,
            'organization': self.organization,
            'primary_contacts': self.primary_contacts,
            'project_description': self.project_description,
            'project_title': self.project_title,
            'project_dates': self.project_dates,
            'number_of_students': self.number_of_students
        } 