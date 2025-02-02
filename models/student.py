from models import db
from models.contact import Contact, RaceEthnicityEnum
from sqlalchemy import Enum, String, Integer, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship

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
    
    # Foreign Keys - Updated to match parent table IDs
    school_id = db.Column(String(18), db.ForeignKey('school.id'))  # References School.id (Salesforce ID)
    class_salesforce_id = db.Column(String(18), db.ForeignKey('class.salesforce_id'))  # References Class.salesforce_id
    
    # Relationships
    school = db.relationship('School', backref='students')
    class_ref = db.relationship('Class', 
                              backref='students',
                              primaryjoin="Student.class_salesforce_id==Class.salesforce_id")
    
    racial_ethnic = db.Column(String(100), nullable=True)
    school_code = db.Column(String(50))
    ell_language = db.Column(String(50))
    gifted = db.Column(Boolean)
    lunch_status = db.Column(String(50))
