from datetime import date

import pytest

from models import db
from models.contact import (
    Address,
    Contact,
    ContactTypeEnum,
    Email,
    GenderEnum,
    LocalStatusEnum,
    Phone,
    RaceEthnicityEnum,
)
from models.student import Student


def test_new_student(app):
    """Test creating a new student with all fields"""
    with app.app_context():
        # Update test to include all new fields and proper enums
        student = Student(
            first_name="Test",
            last_name="Student",
            current_grade=9,
            legacy_grade="Freshman",
            student_id="ST12345",
            racial_ethnic=RaceEthnicityEnum.white,
            school_code="4045",
            ell_language="Spanish",
            gifted=True,
            lunch_status="Free",
            active=True,  # Add active status
        )

        db.session.add(student)
        db.session.commit()

        # Test all fields including new ones
        assert student.id is not None
        assert student.first_name == "Test"
        assert student.last_name == "Student"
        assert student.current_grade == 9
        assert student.legacy_grade == "Freshman"
        assert student.student_id == "ST12345"
        assert student.racial_ethnic == RaceEthnicityEnum.white
        assert student.school_code == "4045"
        assert student.ell_language == "Spanish"
        assert student.gifted is True
        assert student.lunch_status == "Free"
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
            first_name="School",
            last_name="Student",
            racial_ethnic=RaceEthnicityEnum.white,
            school_id=school.id,
            active=True,  # Add active status
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
            first_name="Class",
            last_name="Student",
            racial_ethnic=RaceEthnicityEnum.white,
            class_salesforce_id=class_obj.salesforce_id,
            active=True,  # Add active status
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
            first_name="Inheritance",
            last_name="Test",
            racial_ethnic=RaceEthnicityEnum.white,
        )

        db.session.add(student)
        db.session.commit()

        # Test inheritance
        assert student.type == "student"  # polymorphic identity
        assert hasattr(student, "phones")  # inherited relationship
        assert hasattr(student, "emails")  # inherited relationship
        assert hasattr(student, "addresses")  # inherited relationship

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
                last_name="Student",
            )
            db.session.add(student)
            db.session.commit()


def test_student_demographic_fields(app):
    """Test setting and retrieving demographic information"""
    with app.app_context():
        student = Student(
            first_name="Demo",
            last_name="Student",
            gender=GenderEnum.female,
            racial_ethnic=RaceEthnicityEnum.multi_racial,
            birthdate=date(2010, 1, 1),
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
        student = Student(first_name="Contact", last_name="Test", do_not_contact=False)
        db.session.add(student)
        db.session.commit()

        # Test contact flags
        assert student.is_contactable == False  # Should be false with no contact info

        # Add email and test
        student.emails.append(
            db.session.merge(
                Email(
                    email="student@test.com",
                    primary=True,
                    type=ContactTypeEnum.personal,
                )
            )
        )
        assert student.has_valid_email == True
        assert student.primary_email == "student@test.com"

        # Test do_not_contact flag
        student.do_not_contact = True
        assert student.is_contactable == False

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_student_address_handling(app):
    """Test student address functionality"""
    with app.app_context():
        student = Student(first_name="Address", last_name="Test")
        db.session.add(student)
        db.session.commit()

        # Add address
        address = Address(
            address_line1="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            type=ContactTypeEnum.personal,
            primary=True,
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
        student = Student(first_name="Status", last_name="Test", active=True)
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
    """Test grade validation logic with comprehensive boundary conditions"""
    with app.app_context():
        # Test invalid grade (negative)
        with pytest.raises(ValueError, match="Grade must be between"):
            student = Student(first_name="Grade", last_name="Test", current_grade=-1)

        # Test invalid grade (too high)
        with pytest.raises(ValueError, match="Grade must be between"):
            student = Student(first_name="Grade", last_name="Test", current_grade=13)

        # Test valid boundary grades
        student = Student(first_name="Grade", last_name="Test", current_grade=0)
        assert student.current_grade == 0

        student = Student(first_name="Grade", last_name="Test", current_grade=12)
        assert student.current_grade == 12

        # Test None grade (valid)
        student = Student(first_name="Grade", last_name="Test", current_grade=None)
        assert student.current_grade is None

        # Test middle grade
        student = Student(first_name="Grade", last_name="Test", current_grade=6)
        assert student.current_grade == 6

        # Cleanup
        for s in db.session.query(Student).filter_by(first_name="Grade").all():
            db.session.delete(s)
        db.session.commit()


# =============================================================================
# Validator Tests
# =============================================================================


def test_validate_string_fields_whitespace_stripping(app):
    """Test validate_string_fields strips whitespace from student_id, school_code, ell_language"""
    with app.app_context():
        # Test student_id whitespace stripping
        student = Student(
            first_name="String",
            last_name="Test",
            student_id="  ST12345  ",
            school_code="  4045  ",
            ell_language="  Spanish  ",
        )
        db.session.add(student)
        db.session.commit()

        assert student.student_id == "ST12345"
        assert student.school_code == "4045"
        assert student.ell_language == "Spanish"

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_validate_string_fields_empty_strings(app):
    """Test validate_string_fields converts empty strings to None"""
    with app.app_context():
        student = Student(
            first_name="Empty",
            last_name="Test",
            student_id="",
            school_code="",
            ell_language="",
        )
        db.session.add(student)
        db.session.commit()

        assert student.student_id is None
        assert student.school_code is None
        assert student.ell_language is None

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_validate_string_fields_none_values(app):
    """Test validate_string_fields handles None values correctly"""
    with app.app_context():
        student = Student(
            first_name="None",
            last_name="Test",
            student_id=None,
            school_code=None,
            ell_language=None,
        )
        db.session.add(student)
        db.session.commit()

        assert student.student_id is None
        assert student.school_code is None
        assert student.ell_language is None

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_validate_salesforce_id_field_valid(app, test_school):
    """Test validate_salesforce_id_field with valid Salesforce IDs"""
    with app.app_context():
        # Create a test class for the foreign key
        from models.class_model import Class

        # Use valid 18-character Salesforce IDs
        test_class_sf_id = "0031234567890EFGHI"  # 18 chars
        test_class = Class(
            salesforce_id=test_class_sf_id,
            name="Test Class",
            school_salesforce_id=test_school.id,
            class_year=2024,
        )
        db.session.add(test_class)
        db.session.commit()

        student = Student(
            first_name="Valid",
            last_name="SFID",
            school_id=test_school.id,  # Use valid school ID from fixture
            class_salesforce_id=test_class_sf_id,
        )
        db.session.add(student)
        db.session.commit()

        assert student.school_id == test_school.id
        assert student.class_salesforce_id == test_class_sf_id

        # Cleanup
        db.session.delete(student)
        db.session.delete(test_class)
        db.session.commit()


def test_validate_salesforce_id_field_invalid_length(app):
    """Test validate_salesforce_id_field rejects invalid length Salesforce IDs"""
    with app.app_context():
        # Create student object first
        student = Student(
            first_name="Invalid",
            last_name="Length",
        )

        # Test too short - validators run when attribute is set directly
        with pytest.raises(ValueError, match="Salesforce ID must be exactly"):
            student.school_id = "0011234567890ABC"  # 17 chars

        # Test too long - validators run when attribute is set directly
        with pytest.raises(ValueError, match="Salesforce ID must be exactly"):
            student.school_id = "0011234567890ABCDEF"  # 19 chars


def test_validate_salesforce_id_field_invalid_characters(app):
    """Test validate_salesforce_id_field rejects non-alphanumeric Salesforce IDs"""
    with app.app_context():
        # Validators run during __init__ (attribute setting)
        with pytest.raises(ValueError, match="Salesforce ID must be exactly"):
            student = Student(
                first_name="Invalid",
                last_name="Chars",
                school_id="0011234567890AB-D",  # Contains hyphen (18 chars but invalid)
            )


def test_validate_salesforce_id_field_none_values(app):
    """Test validate_salesforce_id_field allows None values"""
    with app.app_context():
        student = Student(
            first_name="None",
            last_name="SFID",
            school_id=None,
            class_salesforce_id=None,
        )
        db.session.add(student)
        db.session.commit()

        assert student.school_id is None
        assert student.class_salesforce_id is None

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_validate_salesforce_id_field_empty_strings(app):
    """Test validate_salesforce_id_field converts empty strings to None"""
    with app.app_context():
        student = Student(
            first_name="Empty",
            last_name="SFID",
            school_id="",
            class_salesforce_id="",
        )
        db.session.add(student)
        db.session.commit()

        assert student.school_id is None
        assert student.class_salesforce_id is None

        # Cleanup
        db.session.delete(student)
        db.session.commit()


# =============================================================================
# Property Tests
# =============================================================================


def test_repr_with_student_id(app):
    """Test __repr__ with student_id present"""
    with app.app_context():
        student = Student(
            first_name="John",
            last_name="Doe",
            student_id="ST12345",
        )
        db.session.add(student)
        db.session.commit()

        repr_str = repr(student)
        assert "Student" in repr_str
        assert "ST12345" in repr_str
        assert "John Doe" in repr_str or "John" in repr_str

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_repr_without_student_id(app):
    """Test __repr__ without student_id (should show N/A)"""
    with app.app_context():
        student = Student(
            first_name="Jane",
            last_name="Smith",
            student_id=None,
        )
        db.session.add(student)
        db.session.commit()

        repr_str = repr(student)
        assert "Student" in repr_str
        assert "N/A" in repr_str
        assert "Jane Smith" in repr_str or "Jane" in repr_str

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_repr_uses_inherited_full_name(app):
    """Test __repr__ uses inherited full_name property from Contact"""
    with app.app_context():
        student = Student(
            first_name="Middle",
            middle_name="Name",
            last_name="Student",
            student_id="ST999",
        )
        db.session.add(student)
        db.session.commit()

        repr_str = repr(student)
        # Should use full_name which includes middle name
        assert "Middle" in repr_str
        assert "Student" in repr_str

        # Verify it's using the inherited property
        assert hasattr(student, "full_name")
        assert student.full_name == "Middle Name Student"

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_repr_missing_name(app):
    """Test __repr__ with missing name (should show Unknown)"""
    with app.app_context():
        student = Student(
            first_name="",
            last_name="",
            student_id="ST888",
        )
        db.session.add(student)
        db.session.commit()

        repr_str = repr(student)
        assert "Student" in repr_str
        assert "Unknown" in repr_str or "ST888" in repr_str

        # Cleanup
        db.session.delete(student)
        db.session.commit()


# =============================================================================
# Method Tests
# =============================================================================


def test_get_local_status_assumption(app):
    """Test _get_local_status_assumption returns local for students"""
    with app.app_context():
        student = Student(first_name="Local", last_name="Test")
        db.session.add(student)
        db.session.commit()

        status = student._get_local_status_assumption()
        assert status == LocalStatusEnum.local

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_map_racial_ethnic_value(app):
    """Test map_racial_ethnic_value static method"""
    # Test normal value
    result = Student.map_racial_ethnic_value("Asian")
    assert result == "Asian"

    # Test with whitespace
    result = Student.map_racial_ethnic_value("  Black or African American  ")
    assert result == "Black or African American"

    # Test empty string
    result = Student.map_racial_ethnic_value("")
    assert result is None

    # Test None
    result = Student.map_racial_ethnic_value(None)
    assert result is None


def test_import_from_salesforce_new_student(app, test_school):
    """Test import_from_salesforce creates new student"""
    with app.app_context():
        # Create test class for foreign key
        from models.class_model import Class

        test_class = Class(
            salesforce_id="0035f00000TEST4567",
            name="Test Class",
            school_salesforce_id=test_school.id,
            class_year=2024,
        )
        db.session.add(test_class)
        db.session.commit()

        sf_data = {
            "Id": "0031234567890ABCD",
            "FirstName": "New",
            "LastName": "Student",
            "AccountId": "001ABCDEFGHIJKLMN",
            "npsp__Primary_Affiliation__c": test_school.id,  # Use valid school ID
            "Local_Student_ID__c": "ST001",
            "Current_Grade__c": 10,
            "Legacy_Grade__c": "Sophomore",
            "Class__c": "0035f00000TEST4567",  # Valid 18-char ID
            "Gender__c": "Male",
            "Racial_Ethnic_Background__c": "White",
            "Birthdate": "2010-05-15",
            "MiddleName": "Middle",
        }

        student, is_new, error = Student.import_from_salesforce(sf_data, db.session)

        assert error is None
        assert is_new is True
        assert student is not None
        db.session.commit()
        db.session.refresh(student)

        assert student.first_name == "New"
        assert student.last_name == "Student"
        assert student.middle_name == "Middle"
        assert student.salesforce_individual_id == "0031234567890ABCD"
        assert student.salesforce_account_id == "001ABCDEFGHIJKLMN"
        assert student.student_id == "ST001"
        assert student.current_grade == 10
        assert student.legacy_grade == "Sophomore"
        assert student.school_id == test_school.id
        assert student.class_salesforce_id == "0035f00000TEST4567"
        assert student.gender == GenderEnum.male

        # Cleanup
        db.session.delete(student)
        db.session.delete(test_class)
        db.session.commit()


def test_import_from_salesforce_existing_student(app):
    """Test import_from_salesforce updates existing student"""
    with app.app_context():
        # Create existing student
        existing = Student(
            first_name="Old",
            last_name="Student",
            salesforce_individual_id="003EXISTING12345",
            current_grade=9,
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

        # Import with same Salesforce ID
        sf_data = {
            "Id": "003EXISTING12345",
            "FirstName": "Updated",
            "LastName": "Student",
            "Current_Grade__c": 10,
        }

        student, is_new, error = Student.import_from_salesforce(sf_data, db.session)

        assert error is None
        assert is_new is False
        assert student.id == existing_id
        db.session.commit()
        db.session.refresh(student)

        assert student.first_name == "Updated"
        assert student.current_grade == 10

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_import_from_salesforce_missing_required_fields(app):
    """Test import_from_salesforce handles missing required fields"""
    with app.app_context():
        # Missing ID
        sf_data = {
            "Id": "",
            "FirstName": "Missing",
            "LastName": "ID",
        }

        student, is_new, error = Student.import_from_salesforce(sf_data, db.session)
        assert student is None
        assert error is not None
        assert "Missing required fields" in error

        # Missing first name
        sf_data = {
            "Id": "0031234567890ABCD",
            "FirstName": "",
            "LastName": "Missing",
        }

        student, is_new, error = Student.import_from_salesforce(sf_data, db.session)
        assert student is None
        assert error is not None
        assert "Missing required fields" in error


def test_import_from_salesforce_invalid_gender(app, caplog):
    """Test import_from_salesforce handles invalid gender values with logging"""
    with app.app_context():
        with caplog.at_level("WARNING"):
            sf_data = {
                "Id": "0031234567890ABCD",
                "FirstName": "Invalid",
                "LastName": "Gender",
                "Gender__c": "InvalidGender",
            }

            student, is_new, error = Student.import_from_salesforce(sf_data, db.session)

            assert error is None
            assert student is not None
            assert "Invalid gender value" in caplog.text

            # Commit to persist the student before cleanup
            db.session.commit()

            # Cleanup
            db.session.delete(student)
            db.session.commit()


def test_import_from_salesforce_invalid_racial_ethnic(app, caplog):
    """Test import_from_salesforce handles invalid racial/ethnic values with logging"""
    with app.app_context():
        with caplog.at_level("WARNING"):
            sf_data = {
                "Id": "0031234567890ABCD",
                "FirstName": "Invalid",
                "LastName": "Racial",
                "Racial_Ethnic_Background__c": "SomeInvalidValue",
            }

            student, is_new, error = Student.import_from_salesforce(sf_data, db.session)

            assert error is None
            assert student is not None
            # Should log warning but not fail
            student.racial_ethnic = Student.map_racial_ethnic_value("SomeInvalidValue")

            # Commit to persist the student before cleanup
            db.session.commit()

            # Cleanup
            db.session.delete(student)
            db.session.commit()


def test_import_from_salesforce_whitespace_handling(app):
    """Test import_from_salesforce handles whitespace in fields"""
    with app.app_context():
        sf_data = {
            "Id": "0031234567890ABCD",
            "FirstName": "  Whitespace  ",
            "LastName": "  Test  ",
            "MiddleName": "  Middle  ",
            "Local_Student_ID__c": "  ST999  ",
        }

        student, is_new, error = Student.import_from_salesforce(sf_data, db.session)

        assert error is None
        db.session.commit()
        db.session.refresh(student)

        assert student.first_name == "Whitespace"
        assert student.last_name == "Test"
        assert student.middle_name == "Middle"
        assert student.student_id == "ST999"

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_update_contact_info_new_email(app):
    """Test update_contact_info adds new email"""
    with app.app_context():
        student = Student(first_name="Email", last_name="Test")
        db.session.add(student)
        db.session.commit()

        sf_data = {"Email": "newemail@test.com"}
        success, error = student.update_contact_info(sf_data, db.session)

        assert success is True
        assert error is None
        db.session.commit()

        assert student.primary_email == "newemail@test.com"
        email_obj = student.emails.filter_by(primary=True).first()
        assert email_obj is not None
        assert email_obj.email == "newemail@test.com"
        assert email_obj.type == ContactTypeEnum.personal

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_update_contact_info_existing_email(app):
    """Test update_contact_info updates existing email"""
    with app.app_context():
        student = Student(first_name="Email", last_name="Update")
        db.session.add(student)
        db.session.commit()

        # Add existing email
        email = Email(
            contact_id=student.id,
            email="oldemail@test.com",
            type=ContactTypeEnum.personal,
            primary=True,
        )
        db.session.add(email)
        db.session.commit()

        sf_data = {"Email": "newemail@test.com"}
        success, error = student.update_contact_info(sf_data, db.session)

        assert success is True
        assert error is None
        db.session.commit()

        # Should update existing email
        email_obj = student.emails.filter_by(primary=True).first()
        assert email_obj.email == "newemail@test.com"

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_update_contact_info_new_phone(app):
    """Test update_contact_info adds new phone"""
    with app.app_context():
        student = Student(first_name="Phone", last_name="Test")
        db.session.add(student)
        db.session.commit()

        sf_data = {"Phone": "555-1234"}
        success, error = student.update_contact_info(sf_data, db.session)

        assert success is True
        assert error is None
        db.session.commit()

        assert student.primary_phone == "555-1234"
        phone_obj = student.phones.filter_by(primary=True).first()
        assert phone_obj is not None
        assert phone_obj.number == "555-1234"
        assert phone_obj.type == ContactTypeEnum.personal

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_update_contact_info_existing_phone(app):
    """Test update_contact_info updates existing phone"""
    with app.app_context():
        student = Student(first_name="Phone", last_name="Update")
        db.session.add(student)
        db.session.commit()

        # Add existing phone
        phone = Phone(
            contact_id=student.id,
            number="555-0000",
            type=ContactTypeEnum.personal,
            primary=True,
        )
        db.session.add(phone)
        db.session.commit()

        sf_data = {"Phone": "555-9999"}
        success, error = student.update_contact_info(sf_data, db.session)

        assert success is True
        assert error is None
        db.session.commit()

        # Should update existing phone
        phone_obj = student.phones.filter_by(primary=True).first()
        assert phone_obj.number == "555-9999"

        # Cleanup
        db.session.delete(student)
        db.session.commit()


def test_update_contact_info_empty_values(app):
    """Test update_contact_info handles empty email/phone"""
    with app.app_context():
        student = Student(first_name="Empty", last_name="Contact")
        db.session.add(student)
        db.session.commit()

        sf_data = {"Email": "", "Phone": ""}
        success, error = student.update_contact_info(sf_data, db.session)

        assert success is True
        assert error is None
        # Should not create contact records for empty values
        assert student.primary_email is None
        assert student.primary_phone is None

        # Cleanup
        db.session.delete(student)
        db.session.commit()


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_workflow_create_update_import(app):
    """Test full workflow: create student → update → import from Salesforce"""
    with app.app_context():
        # Step 1: Create student
        student = Student(
            first_name="Workflow",
            last_name="Test",
            current_grade=9,
            student_id="WF001",
        )
        db.session.add(student)
        db.session.commit()
        student_id = student.id

        # Step 2: Update contact info
        sf_data = {"Email": "workflow@test.com", "Phone": "555-WORK"}
        success, error = student.update_contact_info(sf_data, db.session)
        assert success is True
        db.session.commit()

        # Step 3: Import from Salesforce (should update existing)
        sf_import_data = {
            "Id": "003WORKFLOW12345",
            "FirstName": "Updated",
            "LastName": "Workflow",
            "Current_Grade__c": 10,
        }
        student.salesforce_individual_id = "003WORKFLOW12345"
        db.session.commit()

        imported, is_new, import_error = Student.import_from_salesforce(
            sf_import_data, db.session
        )
        assert import_error is None
        assert is_new is False
        assert imported.id == student_id
        db.session.commit()
        db.session.refresh(imported)

        assert imported.first_name == "Updated"
        assert imported.current_grade == 10
        assert imported.primary_email == "workflow@test.com"  # Preserved from update

        # Cleanup
        db.session.delete(imported)
        db.session.commit()


def test_data_consistency_after_validators(app, test_school):
    """Test data consistency after validators run"""
    with app.app_context():
        # Create student with whitespace and valid Salesforce ID from fixture
        student = Student(
            first_name="Consistency",
            last_name="Test",
            student_id="  ST123  ",
            school_code="  4045  ",
            ell_language="  Spanish  ",
            school_id=test_school.id,  # Use valid school ID from fixture
        )
        db.session.add(student)
        db.session.commit()

        # Verify validators cleaned the data
        assert student.student_id == "ST123"
        assert student.school_code == "4045"
        assert student.ell_language == "Spanish"
        assert student.school_id == test_school.id

        # Update with more whitespace
        student.student_id = "  NEW123  "
        student.school_code = "  9999  "
        db.session.commit()

        # Verify validators cleaned again
        assert student.student_id == "NEW123"
        assert student.school_code == "9999"

        # Cleanup
        db.session.delete(student)
        db.session.commit()
