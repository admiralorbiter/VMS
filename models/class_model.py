from models import db
from datetime import datetime
from sqlalchemy import Index
from sqlalchemy.orm import relationship

class Class(db.Model):
    """Class model representing school classes/cohorts in the system.
    
    This model maintains relationships between schools and their classes,
    storing both internal and Salesforce-related identifiers.
    
    Important Dependencies:
    - Referenced by Student model via class_salesforce_id
    - Must maintain salesforce_id uniqueness for data sync
    - School relationship relies on school_salesforce_id matching School.id
    
    Key Relationships:
    - students: One-to-many relationship with Student model (defined in Student model)
    - school: Explicit relationship through school_salesforce_id
    """
    __tablename__ = 'class'
    
    # Primary key and external identifiers
    id = db.Column(db.Integer, primary_key=True)
    salesforce_id = db.Column(db.String(18), unique=True, nullable=False, index=True)  # Added index for faster lookups
    
    # Core class information
    name = db.Column(db.String(255), nullable=False, index=True)  # Added index for name searches
    school_salesforce_id = db.Column(db.String(18), db.ForeignKey('school.id'), nullable=False, index=True)  # Added ForeignKey constraint
    class_year = db.Column(db.Integer, nullable=False)  # Academic year number
    
    # Audit timestamps
    # WARNING: These fields are used by data sync processes - do not modify timestamp behavior
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Explicit relationship with School model
    school = db.relationship(
        'School',
        backref=db.backref('classes', lazy='dynamic'),
        foreign_keys=[school_salesforce_id]
    )

    # Explicitly define the students relationship here
    students = relationship(
        'Student',
        primaryjoin="Student.class_salesforce_id == Class.salesforce_id",
        lazy='dynamic',  # Ensures count() works
        viewonly=True    # Since it's also defined in Student model
    )

    # Composite index for common queries
    __table_args__ = (
        Index('idx_class_year_school', class_year, school_salesforce_id),
    )

    def __repr__(self):
        """String representation for debugging and logging"""
        return f'<Class {self.name} ({self.class_year})>'

    @property
    def student_count(self):
        """Returns the count of students in this class"""
        try:
            return self.students.count() if self.students else 0
        except Exception:
            return 0  # Fallback for any issues

    @property
    def salesforce_url(self):
        """Generate Salesforce URL for this class"""
        if self.salesforce_id:
            return f"https://prep-kc.lightning.force.com/lightning/r/Class__c/{self.salesforce_id}/view"
        return None

    def to_dict(self):
        """Convert class to dictionary for API responses"""
        try:
            student_count = self.student_count
        except Exception:
            student_count = 0

        return {
            'id': self.id,
            'salesforce_id': self.salesforce_id,
            'name': self.name,
            'school_salesforce_id': self.school_salesforce_id,
            'class_year': self.class_year,
            'student_count': student_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    # TODO: Consider adding relationships:
    # - Back reference to students (currently defined in Student model) 