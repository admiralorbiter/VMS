from models import db
from sqlalchemy.sql import text

class District(db.Model):
    """District model representing school districts in the system.
    
    This model stores core information about school districts and maintains
    a one-to-many relationship with schools. Each district can have multiple
    schools associated with it.
    
    Note: The relationship with schools is defined in the School model to avoid
    circular references. See models/school_model.py for the relationship definition.
    """
    __tablename__ = 'district'
    
    # Primary key - Auto-incrementing integer for internal references
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Salesforce integration field - Used to sync with Salesforce records
    # indexed=True improves query performance when looking up by salesforce_id
    salesforce_id = db.Column(db.String(18), unique=True, nullable=True, index=True)
    
    # Core district information
    name = db.Column(db.String(255), nullable=False)  # Required field - District's official name
    district_code = db.Column(db.String(20), nullable=True)  # Optional external reference code
    
    def __repr__(self):
        """String representation of the district for debugging and logging"""
        return f'<District {self.name}>'
