from models import db
from models.contact import Contact, Phone, GenderEnum
from sqlalchemy import String, Integer, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship, declared_attr

class Teacher(Contact):
    __tablename__ = 'teacher'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'teacher',
    }
    
    # Teacher-specific fields
    department = db.Column(String(50))
    school_id = db.Column(String(255))  # This is npsp__Primary_Affiliation__c
    active = db.Column(Boolean, default=True)
    
    # Connector fields
    connector_role = db.Column(String(50))
    connector_active = db.Column(Boolean, default=False)
    connector_start_date = db.Column(Date)
    connector_end_date = db.Column(Date)
    
    # Email tracking fields
    last_email_message = db.Column(Date)
    last_mailchimp_date = db.Column(Date)

    def update_from_csv(self, data):
        """Update teacher from CSV data"""
        # Basic info
        self.first_name = data.get('FirstName', '').strip()
        self.last_name = data.get('LastName', '').strip()
        self.middle_name = ''  # Explicitly set to empty string
        self.school_id = data.get('npsp__Primary_Affiliation__c', '')
        self.gender = data.get('Gender__c', None)
        
        # Phone
        phone_number = data.get('Phone')
        if phone_number:
            # Check if phone already exists
            existing_phone = Phone.query.filter_by(
                contact_id=self.id,
                number=phone_number,
                primary=True
            ).first()
            
            if not existing_phone:
                phone = Phone(
                    contact_id=self.id,
                    number=phone_number,
                    primary=True
                )
                db.session.add(phone)
        
        # Email tracking
        if data.get('Last_Email_Message__c'):
            self.last_email_message = data.get('Last_Email_Message__c')
        if data.get('Last_Mailchimp_Email_Date__c'):
            self.last_mailchimp_date = data.get('Last_Mailchimp_Email_Date__c')
