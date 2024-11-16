from models import db
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

class WorkLocationType(Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"

class EntryLevelJob(db.Model):
    __tablename__ = 'entry_level_jobs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_opportunity_id = db.Column(db.Integer, db.ForeignKey('job_opportunities.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    job_link = db.Column(db.String(2048), nullable=True)
    skills_needed = db.Column(db.Text, nullable=True)  # Store as comma-separated values
    work_location = db.Column(db.Enum(WorkLocationType), nullable=False, default=WorkLocationType.ONSITE)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationship to parent job opportunity
    job_opportunity = db.relationship('JobOpportunity', back_populates='entry_level_positions')
    
    def __repr__(self):
        return f"<EntryLevelJob {self.title} at {self.job_opportunity.company_name}>"

    @property
    def skills_list(self):
        """Return skills as a list"""
        return [skill.strip() for skill in self.skills_needed.split(',')] if self.skills_needed else []

class JobOpportunity(db.Model):
    __tablename__ = 'job_opportunities'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(255), nullable=False)
    current_openings = db.Column(db.Integer, default=0, nullable=False)
    opening_types = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    entry_level_available = db.Column(db.Boolean, default=False, nullable=False)
    kc_based = db.Column(db.Boolean, default=False, nullable=False)
    remote_available = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    job_link = db.Column(db.String(2048), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationship to entry level positions
    entry_level_positions = db.relationship('EntryLevelJob', back_populates='job_opportunity', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<JobOpportunity {self.company_name} ({self.industry})>"

    @property
    def active_entry_level_positions(self):
        """Return only active entry level positions"""
        return [pos for pos in self.entry_level_positions if pos.is_active]
