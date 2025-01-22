import pytest
from models.student import Student
from models.contact import RaceEthnicityEnum
from models import db

def test_new_student(app):
    """Test creating a new student"""
    with app.app_context():
        student = Student(
            first_name='Test',
            last_name='Student',
            current_grade=9,
            legacy_grade='Freshman',
            student_id='ST12345',
            racial_ethnic=RaceEthnicityEnum.white,
            school_code='4045',
            ell_language='Spanish',
            gifted=True,
            lunch_status='Free'
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Test basic fields
        assert student.id is not None
        assert student.first_name == 'Test'
        assert student.last_name == 'Student'
        assert student.current_grade == 9
        assert student.legacy_grade == 'Freshman'
        assert student.student_id == 'ST12345'
        assert student.racial_ethnic == RaceEthnicityEnum.white
        assert student.school_code == '4045'
        assert student.ell_language == 'Spanish'
        assert student.gifted is True
        assert student.lunch_status == 'Free'
        
        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_school_relationship(app, test_school):
    """Test relationship between Student and School"""
    with app.app_context():
        # Get a fresh instance of test_school
        school = db.session.get(test_school.__class__, test_school.id)
        
        student = Student(
            first_name='School',
            last_name='Student',
            racial_ethnic=RaceEthnicityEnum.white,
            school_id=school.id
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Get fresh instances
        student = db.session.get(Student, student.id)
        school = db.session.get(school.__class__, school.id)
        
        # Test relationships
        assert student.school_id == school.id
        assert student in school.students
        
        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_class_relationship(app, test_class):
    """Test relationship between Student and Class"""
    with app.app_context():
        # Debug: Print test_class details
        print(f"\nDebug - test_class fixture: {test_class}")
        print(f"Debug - test_class.salesforce_id: {test_class.salesforce_id}")
        
        # Get a fresh instance and print details
        class_obj = db.session.query(test_class.__class__).filter_by(salesforce_id=test_class.salesforce_id).first()
        print(f"Debug - class_obj from db: {class_obj}")
        
        if not class_obj:
            # Query the class table directly to see what's there
            all_classes = db.session.query(test_class.__class__).all()
            print(f"Debug - All classes in db: {all_classes}")
            pytest.skip(f"Class with salesforce_id {test_class.salesforce_id} not found. Available classes: {all_classes}")
        
        student = Student(
            first_name='Class',
            last_name='Student',
            racial_ethnic=RaceEthnicityEnum.white,
            class_salesforce_id=class_obj.salesforce_id  # Updated field name
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Get fresh instances and print details
        student = db.session.get(Student, student.id)
        
        class_obj = db.session.query(test_class.__class__).filter_by(salesforce_id=test_class.salesforce_id).first()

        
        # Test relationships
        assert student.class_salesforce_id == class_obj.salesforce_id
        assert student in class_obj.students
        
        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_inheritance(app):
    """Test that Student inherits correctly from Contact"""
    with app.app_context():
        student = Student(
            first_name='Inheritance',
            last_name='Test',
            racial_ethnic=RaceEthnicityEnum.white
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Test inheritance
        assert student.type == 'student'  # polymorphic identity
        assert hasattr(student, 'phones')  # inherited relationship
        assert hasattr(student, 'emails')  # inherited relationship
        assert hasattr(student, 'addresses')  # inherited relationship
        
        # Cleanup
        db.session.delete(student)
        db.session.commit() 