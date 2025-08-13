from datetime import date, datetime

import pytest

from models import db
from models.contact import Address, ContactTypeEnum, Email, GenderEnum, Phone
from models.teacher import Teacher


def test_new_teacher(app):
    """Test creating a new teacher with all fields"""
    with app.app_context():
        teacher = Teacher(
            first_name="Test",
            last_name="Teacher",
            department="Science",
            school_id="0015f00000TEST123",
            active=True,
            connector_role="Lead",
            connector_active=True,
            connector_start_date=date(2024, 1, 1),
            connector_end_date=date(2024, 12, 31),
            gender=GenderEnum.female,
            description="Test teacher description",
            birthdate=date(1990, 1, 1),
            do_not_call=False,
            do_not_contact=False,
            email_opt_out=False,
        )

        db.session.add(teacher)
        db.session.commit()

        # Test basic fields
        assert teacher.id is not None
        assert teacher.first_name == "Test"
        assert teacher.last_name == "Teacher"
        assert teacher.department == "Science"
        assert teacher.school_id == "0015f00000TEST123"
        assert teacher.active is True
        assert teacher.type == "teacher"  # Check polymorphic identity

        # Test connector fields
        assert teacher.connector_role == "Lead"
        assert teacher.connector_active is True
        assert teacher.connector_start_date == date(2024, 1, 1)
        assert teacher.connector_end_date == date(2024, 12, 31)

        # Test inherited fields
        assert teacher.gender == GenderEnum.female
        assert teacher.description == "Test teacher description"
        assert teacher.birthdate == date(1990, 1, 1)
        assert teacher.do_not_call is False
        assert teacher.do_not_contact is False
        assert teacher.email_opt_out is False

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_teacher_contact_info(app):
    """Test teacher contact information management (phones, emails, addresses)"""
    with app.app_context():
        teacher = Teacher(first_name="Contact", last_name="Test")

        # Add phone
        phone = Phone(
            number="123-456-7890", type=ContactTypeEnum.personal, primary=True
        )
        teacher.phones.append(phone)

        # Add email
        email = Email(
            email="teacher@test.com", type=ContactTypeEnum.personal, primary=True
        )
        teacher.emails.append(email)

        # Add address
        address = Address(
            address_line1="123 School St",
            city="Test City",
            state="TS",
            zip_code="12345",
            type=ContactTypeEnum.personal,
            primary=True,
        )
        teacher.addresses.append(address)

        db.session.add(teacher)
        db.session.commit()

        # Test contact info
        assert teacher.primary_phone == "123-456-7890"
        assert teacher.primary_email == "teacher@test.com"
        assert teacher.primary_address is not None
        assert teacher.formatted_primary_address == "123 School St\nTest City, TS 12345"

        # Test contact validation methods
        assert teacher.has_valid_phone is True
        assert teacher.has_valid_email is True
        assert teacher.is_contactable is True

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_update_from_csv(app):
    """Test updating teacher from CSV data"""
    with app.app_context():
        teacher = Teacher(first_name="Original", last_name="Teacher")
        db.session.add(teacher)
        db.session.commit()

        csv_data = {
            "FirstName": "Updated",
            "LastName": "Name",
            "npsp__Primary_Affiliation__c": "0015f00000TEST123",
            "Gender__c": "Female",
            "Phone": "123-456-7890",
            "Email": "updated@test.com",
            "Department": "Math",
            "Active__c": True,
            "Connector_Role__c": "Support",
            "Connector_Active__c": True,
            "Connector_Start_Date__c": date(2024, 1, 1),
            "Connector_End_Date__c": date(2024, 12, 31),
            "Last_Email_Message__c": date(2024, 1, 1),
            "Last_Mailchimp_Email_Date__c": date(2024, 1, 2),
        }

        teacher.update_from_csv(csv_data)
        db.session.commit()

        # Test updated fields
        assert teacher.first_name == "Updated"
        assert teacher.last_name == "Name"
        assert teacher.school_id == "0015f00000TEST123"
        assert teacher.gender == GenderEnum.female
        assert teacher.department == "Math"
        assert teacher.active is True
        assert teacher.connector_role == "Support"
        assert teacher.connector_active is True
        assert teacher.connector_start_date == date(2024, 1, 1)
        assert teacher.connector_end_date == date(2024, 12, 31)
        assert teacher.last_email_message == date(2024, 1, 1)
        assert teacher.last_mailchimp_date == date(2024, 1, 2)

        # Test contact info creation
        assert teacher.primary_phone == "123-456-7890"
        assert teacher.primary_email == "updated@test.com"

        # Test duplicate prevention
        teacher.update_from_csv(csv_data)
        db.session.commit()

        # Verify no duplicates were created
        assert Phone.query.filter_by(contact_id=teacher.id).count() == 1
        assert Email.query.filter_by(contact_id=teacher.id).count() == 1

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()


def test_teacher_inheritance(app):
    """Test that Teacher inherits correctly from Contact"""
    with app.app_context():
        teacher = Teacher(first_name="Inheritance", last_name="Test")

        # Add email to properly test has_valid_email
        email = Email(
            email="test@example.com", type=ContactTypeEnum.personal, primary=True
        )
        teacher.emails.append(email)

        db.session.add(teacher)
        db.session.commit()

        # Test inheritance
        assert teacher.type == "teacher"  # polymorphic identity
        assert hasattr(teacher, "phones")  # inherited relationship
        assert hasattr(teacher, "emails")  # inherited relationship
        assert hasattr(teacher, "addresses")  # inherited relationship
        assert hasattr(teacher, "gender")  # inherited field
        assert hasattr(teacher, "birthdate")  # inherited field
        assert hasattr(teacher, "do_not_call")  # inherited field

        # Test inherited methods
        assert teacher.has_valid_email is True  # inherited method
        assert teacher.is_contactable is True  # inherited method
        assert teacher.primary_phone is None  # inherited property

        # Cleanup
        db.session.delete(teacher)
        db.session.commit()
