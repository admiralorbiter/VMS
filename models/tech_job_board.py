from models import db
from flask_sqlalchemy import SQLAlchemy
from enum import Enum

class WorkLocationType(Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"

class EntryLevelJob(db.Model):
    """
    Represents an entry-level job position in the tech job board.
    This model stores specific details about individual entry-level positions
    and is linked to a parent JobOpportunity.
    """
    __tablename__ = 'entry_level_jobs'
    
    # Primary key for unique identification of each job entry
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Foreign key linking to the parent JobOpportunity
    job_opportunity_id = db.Column(db.Integer, db.ForeignKey('job_opportunities.id'), nullable=False)
    
    # Basic job details
    title = db.Column(db.String(255), nullable=False)  # Job title cannot be empty
    description = db.Column(db.Text, nullable=True)    # Detailed job description
    address = db.Column(db.String(255), nullable=True) # Physical job location
    job_link = db.Column(db.String(2048), nullable=True)  # URL to job application/posting
    
    # Skills stored as comma-separated values (e.g., "python,javascript,sql")
    skills_needed = db.Column(db.Text, nullable=True)
    
    # Work location type (ONSITE, REMOTE, or HYBRID)
    work_location = db.Column(db.Enum(WorkLocationType), nullable=False, default=WorkLocationType.ONSITE)
    
    # Flag to mark if the job posting is still active
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationship to parent job opportunity
    job_opportunity = db.relationship('JobOpportunity', back_populates='entry_level_positions')
    
    def __repr__(self):
        """
        Returns a string representation of the job for debugging purposes
        Example: "<EntryLevelJob Software Engineer at Google>"
        """
        return f"<EntryLevelJob {self.title} at {self.job_opportunity.company_name}>"

    @property
    def skills_list(self):
        """
        Converts the comma-separated skills string into a list of individual skills.
        
        Returns:
            list: A list of skills (e.g., ["python", "javascript", "sql"])
                  Returns empty list if no skills are specified
        """
        return [skill.strip() for skill in self.skills_needed.split(',')] if self.skills_needed else []

class JobOpportunity(db.Model):
    """
    Represents a company's job opportunity profile.
    This model stores company-level information and can have multiple
    associated entry-level positions.
    """
    __tablename__ = 'job_opportunities'
    
    # Basic company and job information
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)      # Company or opportunity description
    industry = db.Column(db.String(255), nullable=False) # Industry sector
    
    # Job opening details
    current_openings = db.Column(db.Integer, default=0, nullable=False)  # Number of current openings
    opening_types = db.Column(db.String(255), nullable=True)  # Types of positions available
    location = db.Column(db.String(255), nullable=True)       # Company location
    
    # Various flags for filtering and categorization
    entry_level_available = db.Column(db.Boolean, default=False, nullable=False)
    kc_based = db.Column(db.Boolean, default=False, nullable=False)          # Kansas City based
    remote_available = db.Column(db.Boolean, default=False, nullable=False)
    
    # Additional information
    notes = db.Column(db.Text, nullable=True)
    job_link = db.Column(db.String(2048), nullable=True)  # URL to company's job page
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # One-to-many relationship with entry level positions
    entry_level_positions = db.relationship('EntryLevelJob', back_populates='job_opportunity', cascade='all, delete-orphan')
    
    def __repr__(self):
        """
        Returns a string representation of the job opportunity for debugging
        Example: "<JobOpportunity Google (Technology)>"
        """
        return f"<JobOpportunity {self.company_name} ({self.industry})>"

    @property
    def active_entry_level_positions(self):
        """
        Returns a filtered list of only active entry level positions.
        
        Returns:
            list: List of EntryLevelJob objects where is_active=True
        """
        return [pos for pos in self.entry_level_positions if pos.is_active]
