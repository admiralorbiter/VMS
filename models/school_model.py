from models import db

class School(db.Model):
    __tablename__ = 'school'
    
    id = db.Column(db.String(18), primary_key=True)  # Salesforce ID format (e.g., '0015f00000JVZsFAAX')
    name = db.Column(db.String(255), nullable=False)  # Original school name
    district_id = db.Column(db.Integer, db.ForeignKey('district.id'), nullable=True)  # Parent/District ID
    salesforce_district_id = db.Column(db.String(18), nullable=True)  # Salesforce District ID
    normalized_name = db.Column(db.String(255))  # Normalized/standardized school name
    school_code = db.Column(db.String(20))  # School code (e.g., '4045', '48077-6080')
    
    # Updated relationship with cascade options
    district = db.relationship('District', 
                             backref=db.backref('schools', 
                                              lazy='dynamic',
                                              cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<School {self.name}>'
    