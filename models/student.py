from models import db
from models.contact import Contact, RaceEthnicityEnum
from sqlalchemy import Enum, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declared_attr

class Student(Contact):
    __tablename__ = 'student'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'student',
    }
    
    # Student-specific fields
    current_grade = db.Column(Integer)
    legacy_grade = db.Column(String(50))  # Legacy Grade__C
    student_id = db.Column(String(50))    # Local_Student_ID__c
    school_id = db.Column(String(50))     # npsp__Primary_Affiliation__c
    class_id = db.Column(String(50), db.ForeignKey('class.salesforce_id'))
    racial_ethnic = db.Column(Enum(RaceEthnicityEnum))  # Racial_Ethnic_Background__c
    
    # Add relationship to Class
    class_ref = db.relationship('Class', foreign_keys=[class_id], backref='students')
    
    # Existing fields
    school_code = db.Column(String(50))
    ell_language = db.Column(String(50))
    gifted = db.Column(Boolean)
    lunch_status = db.Column(String(50))
