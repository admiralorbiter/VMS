from models import db
from flask_sqlalchemy import SQLAlchemy


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
    
    def __repr__(self):
        return f"<JobOpportunity {self.company_name} ({self.industry})>"
