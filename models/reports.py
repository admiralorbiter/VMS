from datetime import datetime
from models import db  # Import db from models instead of creating new instance

class DistrictYearEndReport(db.Model):
    __tablename__ = 'district_year_end_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey('district.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    report_data = db.Column(db.JSON, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    district = db.relationship('District', backref='year_end_reports')
    
    __table_args__ = (
        db.UniqueConstraint('district_id', 'year', name='uix_district_year'),
    ) 