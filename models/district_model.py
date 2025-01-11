from models import db

class District(db.Model):
    __tablename__ = 'district'
    
    id = db.Column(db.String(18), primary_key=True)  # Salesforce ID format (e.g., '0015f00000JVZsFAAX')
    name = db.Column(db.String(255), nullable=False)  # Original district name
    district_code = db.Column(db.String(20))  # District code (e.g., '4045', '48077-6080')
    
    def __repr__(self):
        return f'<District {self.name}>'
