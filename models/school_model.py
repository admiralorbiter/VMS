from models import db

class School(db.Model):
    """School model representing individual schools in the system.
    
    This model maintains the relationship between schools and their districts,
    storing both internal and Salesforce-related identifiers. The model supports
    bi-directional relationships, allowing navigation from schools to districts
    and vice versa.
    
    Key Relationships:
    - district: Many-to-one relationship with District model
    """
    __tablename__ = 'school'
    
    # Primary key - Using Salesforce ID format for direct mapping
    id = db.Column(db.String(255), primary_key=True)  # Salesforce ID format (e.g., '0015f00000JVZsFAAX')
    
    # Core school information
    name = db.Column(db.String(255), nullable=False)  # Required field - School's official name
    
    # District relationship fields
    district_id = db.Column(db.Integer, db.ForeignKey('district.id'))  # Internal district reference
    salesforce_district_id = db.Column(db.String(255))  # External district reference
    
    # Additional school information
    normalized_name = db.Column(db.String(255))  # Standardized name for consistent searching
    school_code = db.Column(db.String(255))  # External reference code
    
    # Relationship definition for both models
    # - backref creates a 'schools' property on District model
    # - lazy='dynamic' makes district.schools return a query object instead of a list
    #   allowing for further filtering and efficient counting
    district = db.relationship(
        'District',
        backref=db.backref('schools', lazy='dynamic')
    )
    
    def __repr__(self):
        """String representation of the school for debugging and logging"""
        return f'<School {self.name}>'
    