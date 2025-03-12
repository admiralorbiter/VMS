import pytest
from models.student import Student
from models.contact import RaceEthnicityEnum, GenderEnum, Contact, Address, Email, Phone, ContactTypeEnum
from models import db
from datetime import date

def test_new_student(app):
    """Test creating a new student with all fields"""
    with app.app_context():
        # Update test to include all new fields and proper enums
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
            lunch_status='Free',
            active=True  # Add active status
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Test all fields including new ones
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
        assert student.active is True
        
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
            school_id=school.id,
            active=True  # Add active status
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Test relationships with fresh instances
        student = db.session.get(Student, student.id)
        school = db.session.get(school.__class__, school.id)
        
        # Test bidirectional relationship
        assert student.school_id == school.id
        assert student in school.students
        assert student.school == school
        
        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_class_relationship(app, test_class):
    """Test relationship between Student and Class"""
    with app.app_context():
        # Get a fresh instance of test_class
        class_obj = db.session.get(test_class.__class__, test_class.id)
        
        student = Student(
            first_name='Class',
            last_name='Student',
            racial_ethnic=RaceEthnicityEnum.white,
            class_salesforce_id=class_obj.salesforce_id,
            active=True  # Add active status
        )
        
        db.session.add(student)
        db.session.commit()
        
        # Test relationships with fresh instances
        student = db.session.get(Student, student.id)
        class_obj = db.session.get(class_obj.__class__, class_obj.id)
        
        # Test bidirectional relationship
        assert student.class_salesforce_id == class_obj.salesforce_id
        assert student in class_obj.students
        assert student.class_ref == class_obj
        
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

def test_student_required_fields(app):
    """Test validation of required fields"""
    with app.app_context():
        # Test creating with None values - will fail at database level
        with pytest.raises(Exception):
            student = Student(
                first_name=None,  # None triggers SQLAlchemy's nullable check
                last_name='Student'
            )
            db.session.add(student)
            db.session.commit()

def test_student_demographic_fields(app):
    """Test setting and retrieving demographic information"""
    with app.app_context():
        student = Student(
            first_name='Demo',
            last_name='Student',
            gender=GenderEnum.female,
            racial_ethnic=RaceEthnicityEnum.multi_racial,
            birthdate=date(2010, 1, 1)
        )
        db.session.add(student)
        db.session.commit()

        # Test demographic getters
        assert student.gender == GenderEnum.female
        assert student.racial_ethnic == RaceEthnicityEnum.multi_racial
        assert student.age == date.today().year - 2010

        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_contact_methods(app):
    """Test student contact information methods"""
    with app.app_context():
        student = Student(
            first_name='Contact',
            last_name='Test',
            do_not_contact=False
        )
        db.session.add(student)
        db.session.commit()

        # Test contact flags
        assert student.is_contactable == False  # Should be false with no contact info
        
        # Add email and test
        student.emails.append(db.session.merge(Email(
            email='student@test.com',
            primary=True,
            type=ContactTypeEnum.personal
        )))
        assert student.has_valid_email == True
        assert student.primary_email == 'student@test.com'

        # Test do_not_contact flag
        student.do_not_contact = True
        assert student.is_contactable == False

        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_address_handling(app):
    """Test student address functionality"""
    with app.app_context():
        student = Student(
            first_name='Address',
            last_name='Test'
        )
        db.session.add(student)
        db.session.commit()

        # Add address
        address = Address(
            address_line1='123 Test St',
            city='Test City',
            state='TS',
            zip_code='12345',
            type=ContactTypeEnum.personal,
            primary=True
        )
        student.addresses.append(db.session.merge(address))
        
        # Test address retrieval
        assert student.primary_address is not None
        assert student.formatted_primary_address == "123 Test St\nTest City, TS 12345"

        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_student_active_status(app):
    """Test student active status functionality"""
    with app.app_context():
        student = Student(
            first_name='Status',
            last_name='Test',
            active=True
        )
        db.session.add(student)
        db.session.commit()

        assert student.active == True
        
        # Test deactivation
        student.active = False
        db.session.commit()
        assert student.active == False

        # Cleanup
        db.session.delete(student)
        db.session.commit()

def test_grade_validation(app):
    """Test grade validation logic"""
    with app.app_context():
        # Test invalid grade (negative)
        with pytest.raises(ValueError):
            student = Student(
                first_name='Grade',
                last_name='Test',
                current_grade=-1
            )
            
        # Test invalid grade (too high)
        with pytest.raises(ValueError):
            student = Student(
                first_name='Grade',
                last_name='Test',
                current_grade=13
            )
            
        # Test valid grade
        student = Student(
            first_name='Grade',
            last_name='Test',
            current_grade=12
        )
        assert student.current_grade == 12 