from models import db
from models.contact import Contact, RaceEthnicityEnum
from sqlalchemy import Enum, String, Integer, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship, validates

class Student(Contact):
    """
    Student Model - Represents a student in the education system.
    Inherits from Contact model for basic contact information.
    
    Key Features:
    - Tracks academic information (grade, student ID)
    - Maintains relationships with School, Class, and Teacher
    - Stores demographic and program participation data
    """
    __tablename__ = 'student'
    
    id = db.Column(Integer, ForeignKey('contact.id'), primary_key=True)
    active = db.Column(db.Boolean, default=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'student',
    }
    
    # Academic Information
    current_grade = db.Column(Integer, 
                            nullable=True,
                            comment='Current grade level of the student')
    legacy_grade = db.Column(String(50),
                           comment='Legacy Grade__C from Salesforce')
    student_id = db.Column(String(50), 
                          index=True,  # Add index for faster lookups
                          comment='Local_Student_ID__c - School-specific identifier')
    
    # Institutional Relationships
    school_id = db.Column(String(18), 
                         db.ForeignKey('school.id', ondelete='SET NULL'),
                         index=True,  # Add index for foreign key
                         comment='References School.id (Salesforce ID)')
    
    class_salesforce_id = db.Column(String(18), 
                                   db.ForeignKey('class.salesforce_id', ondelete='SET NULL'),
                                   index=True,  # Add index for foreign key
                                   comment='References Class.salesforce_id')
    
    teacher_id = db.Column(Integer, 
                          ForeignKey('teacher.id', ondelete='SET NULL'),
                          nullable=True,
                          index=True,  # Add index for foreign key
                          comment='References Teacher.id')
    
    # Relationship definitions with explicit join conditions
    teacher = db.relationship(
        'Teacher', 
        backref=db.backref('students', 
                          lazy='dynamic',
                          cascade='all, delete-orphan'),
        foreign_keys=[teacher_id],
        lazy='joined'  # Optimize common queries by eager loading
    )
    
    school = db.relationship(
        'School', 
        backref=db.backref('students', lazy='dynamic'),
        lazy='joined'
    )
    
    class_ref = db.relationship(
        'Class', 
        backref=db.backref('students', lazy='dynamic'),
        primaryjoin="Student.class_salesforce_id==Class.salesforce_id",
        lazy='joined'
    )
    
    # Demographics and Program Participation
    racial_ethnic = db.Column(String(100), 
                            nullable=True,
                            comment='Student\'s racial/ethnic identification')
    
    school_code = db.Column(String(50),
                           index=True,  # Add index for common lookups
                           comment='School-specific code')
    
    ell_language = db.Column(String(50),
                            nullable=True,
                            comment='English Language Learner primary language')
    
    gifted = db.Column(Boolean,
                      default=False,
                      nullable=False,
                      comment='Gifted program participation status')
    
    lunch_status = db.Column(String(50),
                            nullable=True,
                            comment='Student lunch program status')

    __table_args__ = (
        db.Index('idx_student_school_grade', 'school_id', 'current_grade'),
    )

    @validates('first_name', 'last_name')
    def validate_required_fields(self, key, value):
        """Validate required fields are not empty"""
        if not value or not value.strip():
            raise ValueError(f"{key} is required and cannot be empty")
        return value.strip()

    @validates('current_grade')
    def validate_grade(self, key, grade):
        """Validate grade is within acceptable range"""
        if grade is not None and not (0 <= grade <= 12):
            raise ValueError("Grade must be between 0 and 12")
        return grade

    def __repr__(self):
        """String representation of the Student model"""
        return f'<Student {self.student_id}: {self.get_full_name()}>'

    @property
    def get_full_name(self):
        """Returns the student's full name from Contact parent class"""
        return f"{self.first_name} {self.last_name}"
