from models import db

class School(db.Model):
    __tablename__ = 'school'
    
    id = db.Column(db.String(18), primary_key=True)  # Salesforce ID format (e.g., '0015f00000JVZsFAAX')
    name = db.Column(db.String(255), nullable=False)  # Original school name
    district_id = db.Column(db.String(18), db.ForeignKey('district.id'), nullable=True)  # Parent/District ID
    normalized_name = db.Column(db.String(255))  # Normalized/standardized school name
    school_code = db.Column(db.String(20))  # School code (e.g., '4045', '48077-6080')
    
    # Relationship to district (assuming you have a District model)
    district = db.relationship('District', backref='schools')
    
    def __repr__(self):
        return f'<School {self.name}>'
    