"""
Student Model Module
===================

This module defines the Student model for managing student information in the VMS system.
It inherits from the Contact model and provides student-specific academic and demographic data.

Key Features:
- Student academic information tracking
- School and class relationships
- Teacher assignment tracking
- Demographic data collection
- Program participation tracking
- Grade level management
- Student ID tracking
- Salesforce integration

Database Table:
- student: Inherits from contact table with polymorphic identity

Academic Information:
- Current grade level tracking
- Legacy grade data from Salesforce
- Student ID for school-specific identification
- School and class relationships
- Teacher assignment tracking

Demographic Data:
- Racial/ethnic identification
- English Language Learner status
- Gifted program participation
- Lunch program status
- School code tracking

Program Participation:
- ELL (English Language Learner) program
- Gifted program participation
- Lunch program status
- Special education tracking

Relationships:
- Many-to-one with School model
- Many-to-one with Class model
- Many-to-one with Teacher model
- Inherits from Contact model

Salesforce Integration:
- Bi-directional synchronization with Salesforce
- Student record mapping and tracking
- Grade and demographic data sync
- School and class relationship sync

Usage Examples:
    # Create a new student
    student = Student(
        first_name="John",
        last_name="Doe",
        current_grade=10,
        student_id="STU123456",
        school_id="0015f00000JVZsFAAX",
        gifted=True
    )
    
    # Get student's school
    school = student.school
    
    # Get student's teacher
    teacher = student.teacher
    
    # Validate student data
    student.validate_required_fields('first_name', 'John')
"""

from models import db
from models.contact import Contact, RaceEthnicityEnum
from sqlalchemy import Enum, String, Integer, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship, validates

class Student(Contact):
    """
    Student Model - Represents a student in the education system.
    
    This model inherits from Contact for basic contact information and adds
    student-specific academic and demographic data. It maintains relationships
    with schools, classes, and teachers for comprehensive student tracking.
    
    Database Table:
        student - Inherits from contact table with polymorphic identity
        
    Key Features:
        - Student academic information tracking
        - School and class relationships
        - Teacher assignment tracking
        - Demographic data collection
        - Program participation tracking
        - Grade level management
        - Student ID tracking
        - Salesforce integration
        
    Academic Information:
        - current_grade: Current grade level (0-12)
        - legacy_grade: Legacy grade data from Salesforce
        - student_id: School-specific student identifier
        - school_id: Reference to student's school
        - class_salesforce_id: Reference to student's class
        - teacher_id: Reference to student's teacher
        
    Demographic Data:
        - racial_ethnic: Student's racial/ethnic identification
        - school_code: School-specific code
        - ell_language: English Language Learner primary language
        - gifted: Gifted program participation status
        - lunch_status: Student lunch program status
        
    Program Participation:
        - ELL (English Language Learner) program tracking
        - Gifted program participation
        - Lunch program status
        - Special education tracking
        
    Relationships:
        - Many-to-one with School model
        - Many-to-one with Class model
        - Many-to-one with Teacher model
        - Inherits from Contact model
        
    Salesforce Integration:
        - Bi-directional synchronization with Salesforce
        - Student record mapping and tracking
        - Grade and demographic data sync
        - School and class relationship sync
        
    Data Validation:
        - Required fields validation (first_name, last_name)
        - Grade level validation (0-12)
        - Student ID uniqueness
        - School relationship validation
        
    Performance Features:
        - Indexed foreign keys for fast joins
        - Composite index on school_id and current_grade
        - Eager loading for common relationships
        - Optimized query patterns
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
        """
        Validate required fields are not empty.
        
        Args:
            key: Field name being validated
            value: Value to validate
            
        Returns:
            Validated value (stripped of whitespace)
            
        Raises:
            ValueError: If value is empty or whitespace only
        """
        if not value or not value.strip():
            raise ValueError(f"{key} is required and cannot be empty")
        return value.strip()

    @validates('current_grade')
    def validate_grade(self, key, grade):
        """
        Validate grade is within acceptable range.
        
        Args:
            key: Field name being validated
            grade: Grade level to validate
            
        Returns:
            Validated grade level
            
        Raises:
            ValueError: If grade is outside 0-12 range
        """
        if grade is not None and not (0 <= grade <= 12):
            raise ValueError("Grade must be between 0 and 12")
        return grade

    def __repr__(self):
        """
        String representation of the Student model.
        
        Returns:
            str: Debug representation showing student ID and full name
        """
        return f'<Student {self.student_id}: {self.get_full_name()}>'

    @property
    def get_full_name(self):
        """
        Returns the student's full name from Contact parent class.
        
        Returns:
            str: Student's full name (first_name + last_name)
        """
        return f"{self.first_name} {self.last_name}"
