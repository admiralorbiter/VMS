from datetime import datetime
from models import db  # Import db from models instead of creating new instance

class DistrictYearEndReport(db.Model):
    __tablename__ = 'district_year_end_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.String(18), db.ForeignKey('district.id'), nullable=False)
    school_year = db.Column(db.String(4), nullable=False, index=True)  # Added index
    report_data = db.Column(db.JSON, nullable=False)
    events_data = db.Column(db.JSON, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    district = db.relationship('District', backref='year_end_reports')
    
    __table_args__ = (
        db.UniqueConstraint('district_id', 'school_year', name='uix_district_school_year'),
        db.Index('idx_school_year_last_updated', 'school_year', 'last_updated')  # Added composite index
    ) 