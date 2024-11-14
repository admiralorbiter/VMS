from models import db
from datetime import datetime

class VolunteerOrganization(db.Model):
    __tablename__ = 'volunteer_organization'
    
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id'), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), primary_key=True)
    salesforce_volunteer_id = db.Column(db.String(18), nullable=True)
    salesforce_org_id = db.Column(db.String(18), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 