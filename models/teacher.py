from models import db
from models.contact import Contact
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declared_attr

class Teacher(Contact):
    __tablename__ = 'teacher'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'teacher',
    }
    
    # Teacher-specific fields
    department = db.Column(String(50))
    school_code = db.Column(String(50))
    active = db.Column(Boolean, default=True)
    connector_role = db.Column(String(50))
