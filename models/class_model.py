from models import db
from datetime import datetime

class Class(db.Model):
    __tablename__ = 'class'
    
    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    school_salesforce_id = db.Column(db.String(18), nullable=False)  # School__c
    class_year = db.Column(db.Integer, nullable=False)  # Class_Year_Number__c
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Class {self.name}>' 