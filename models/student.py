from models import db
from models.contact import Contact
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
    student_id = db.Column(String(50))
    school_code = db.Column(String(50))
    ell_language = db.Column(String(50))
    gifted = db.Column(Boolean)
    lunch_status = db.Column(String(50))
