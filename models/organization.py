from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models import db

class Organization(db.Model):
    __tablename__ = 'organization'
    
    id = db.Column(Integer, primary_key=True)
    salesforce_id = db.Column(String(18), unique=True, nullable=True)
    name = db.Column(String(255), nullable=False)
    type = db.Column(String(255), nullable=True)
    description = db.Column(String(255), nullable=True)
    
    # Update parent_id to reference volunteer's Salesforce ID
    volunteer_parent_id = db.Column(String(18), nullable=True)  # For Salesforce volunteer relationship
    
    # Address fields
    billing_street = db.Column(String(255), nullable=True)
    billing_city = db.Column(String(255), nullable=True)
    billing_state = db.Column(String(255), nullable=True)
    billing_postal_code = db.Column(String(255), nullable=True)
    billing_country = db.Column(String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    volunteers = relationship('Volunteer', secondary='volunteer_organization', back_populates='organizations')

    @property
    def salesforce_url(self):
        """Generate Salesforce URL if ID exists"""
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Account/{self.salesforce_id}/view"
        return None

class VolunteerOrganization(db.Model):
    __tablename__ = 'volunteer_organization'
    
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer.id'), primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), primary_key=True)
    salesforce_volunteer_id = db.Column(db.String(18), nullable=True)
    salesforce_org_id = db.Column(db.String(18), nullable=True)
    
    # Additional fields from npe5__Affiliation__c
    role = db.Column(String(255), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    is_primary = db.Column(Boolean, default=False)
    status = db.Column(String(50), default='Current')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
