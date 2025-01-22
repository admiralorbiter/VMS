from models import db
from sqlalchemy.sql import text

class District(db.Model):
    __tablename__ = 'district'
    
    id = db.Column(db.String(18), primary_key=True, 
                  nullable=False, 
                  server_default=text('NULL'))  # Explicitly state that server doesn't generate this, generated from Salesforce
    name = db.Column(db.String(255), nullable=False)  # Original district name
    district_code = db.Column(db.String(20))  # District code (e.g., '4045', '48077-6080')
    
    def __repr__(self):
        return f'<District {self.name}>'
