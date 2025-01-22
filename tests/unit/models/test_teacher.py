import pytest
from models.teacher import Teacher
from models.contact import GenderEnum, Phone
from models import db
from datetime import date

def test_new_teacher(app):
    """Test creating a new teacher"""
    with app.app_context():
        teacher = Teacher(
            first_name='Test',
            last_name='Teacher',
            department='Science',
            school_id='0015f00000TEST123',
            active=True,
            connector_role='Lead',
            connector_active=True,
            connector_start_date=date(2024, 1, 1),
            connector_end_date=date(2024, 12, 31),
            gender=GenderEnum.female
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        # Test basic fields
        assert teacher.id is not None
        assert teacher.first_name == 'Test'
        assert teacher.last_name == 'Teacher'
        assert teacher.department == 'Science'
        assert teacher.school_id == '0015f00000TEST123'
        assert teacher.active is True
        assert teacher.connector_role == 'Lead'
        assert teacher.connector_active is True
        assert teacher.connector_start_date == date(2024, 1, 1)
        assert teacher.connector_end_date == date(2024, 12, 31)
        assert teacher.gender == GenderEnum.female
        
        # Cleanup
        db.session.delete(teacher)
        db.session.commit()

def test_update_from_csv(app):
    """Test updating teacher from CSV data"""
    with app.app_context():
        teacher = Teacher(
            first_name='Original',
            last_name='Teacher'
        )
        db.session.add(teacher)
        db.session.commit()
        
        csv_data = {
            'FirstName': 'Updated',
            'LastName': 'Name',
            'npsp__Primary_Affiliation__c': '0015f00000TEST123',
            'Gender__c': 'Female',
            'Phone': '123-456-7890',
            'Last_Email_Message__c': date(2024, 1, 1),
            'Last_Mailchimp_Email_Date__c': date(2024, 1, 2)
        }
        
        teacher.update_from_csv(csv_data)
        db.session.commit()
        
        # Test updated fields
        assert teacher.first_name == 'Updated'
        assert teacher.last_name == 'Name'
        assert teacher.school_id == '0015f00000TEST123'
        assert teacher.gender == 'Female'
        assert teacher.last_email_message == date(2024, 1, 1)
        assert teacher.last_mailchimp_date == date(2024, 1, 2)
        
        # Test phone creation
        phone = Phone.query.filter_by(contact_id=teacher.id).first()
        assert phone is not None
        assert phone.number == '123-456-7890'
        assert phone.primary is True
        
        # Test phone update (shouldn't create duplicate)
        teacher.update_from_csv(csv_data)
        db.session.commit()
        
        phone_count = Phone.query.filter_by(contact_id=teacher.id).count()
        assert phone_count == 1
        
        # Cleanup
        db.session.delete(teacher)
        db.session.commit()

def test_teacher_inheritance(app):
    """Test that Teacher inherits correctly from Contact"""
    with app.app_context():
        teacher = Teacher(
            first_name='Inheritance',
            last_name='Test',
            gender=GenderEnum.female
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        # Test inheritance
        assert teacher.type == 'teacher'  # polymorphic identity
        assert hasattr(teacher, 'phones')  # inherited relationship
        assert hasattr(teacher, 'emails')  # inherited relationship
        assert hasattr(teacher, 'addresses')  # inherited relationship
        
        # Cleanup
        db.session.delete(teacher)
        db.session.commit() 